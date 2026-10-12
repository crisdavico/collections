# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import TransactionCase

from .test_collection_payment import (
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
    insert_company_like,
)


class TestCollectionConsistency(TransactionCase):
    """Writes on one model MUST NOT break another model's invariants."""

    def setUp(self):
        super().setUp()
        self.seller = ensure_enabled_seller(self.env)
        self.sheet = self._sheet(self.seller)
        self.partner = dummy_customer_partner(self.env, customer="CUST-CONSIST")

    def _sheet(self, seller, company=None):
        company = company or self.env.company
        ensure_enabled_seller(self.env, seller, company=company)
        return self.env["collection.sheet"].create(
            {"seller_id": seller.id, "company_id": company.id}
        )

    def _voucher(self, partner=None, amount=100.0, sheet=None, **extra):
        sheet = sheet or self.sheet
        vals = {
            "partner_id": (partner or self.partner).id,
            "document_type": "bank_transfer",
            "amount": amount,
            "seller_id": sheet.seller_id.id,
            "sheet_id": sheet.id,
        }
        vals.update(extra)
        return self.env["collection.voucher"].create(vals)

    def _allocation(self, partner, vouchers, invoice):
        return self.env["collection.allocation"].create(
            {
                "sheet_id": self.sheet.id,
                "partner_id": partner.id,
                "voucher_ids": [Command.set(vouchers.ids)],
                "line_ids": [
                    Command.create(
                        {
                            "external_invoice_id": invoice,
                            "invoice_number": invoice,
                            "invoice_balance": 100.0,
                            "amount_applied": 0.0,
                        }
                    )
                ],
            }
        )

    def _company_b(self):
        partner = dummy_customer_partner(self.env, customer="CONSIST-COMPANY-B")
        company = insert_company_like(self.env, "Consistency Co B", partner.id)
        company._collection_copy_sequences()
        company._collection_enable_all_document_types()
        return company

    def test_an_allocated_voucher_cannot_leave_its_allocation_sheet(self):
        """The allocation's sheet rule MUST hold when the voucher side moves."""
        voucher = self._voucher()
        allocation = self._allocation(self.partner, voucher, "INV-CONSIST-1")
        voucher.action_validate_seller()
        with self.assertRaises(ValidationError):
            voucher.write({"sheet_id": False})
        self.assertEqual(voucher.sheet_id, self.sheet)
        self.sheet.action_seller_close()
        next_sheet = self._sheet(self.seller)
        with self.assertRaises(ValidationError):
            voucher.write({"sheet_id": next_sheet.id})
        self.assertEqual(voucher.sheet_id, self.sheet)
        self.assertEqual(voucher.allocation_id, allocation)

    def test_an_unallocated_voucher_still_moves_freely(self):
        """Triangulation: no allocation, no values, the move is fine."""
        voucher = self._voucher()
        voucher.write({"sheet_id": False})
        self.assertFalse(voucher.sheet_id)

    def test_a_voucher_with_receipt_values_cannot_leave_their_sheet(self):
        """A value's voucher MUST stay on the receipt's sheet afterwards too."""
        other_partner = dummy_customer_partner(self.env, customer="CUST-CONSIST-2")
        owner_voucher = self._voucher(other_partner, amount=50.0)
        allocation = self._allocation(other_partner, owner_voucher, "INV-CONSIST-2")
        receipt = self.env["collection.receipt"].create(
            {"allocation_id": allocation.id, "document_kind": "invoice"}
        )
        loose = self._voucher(amount=40.0)
        self.assertFalse(loose.allocation_id)
        self.env["collection.receipt.value"].create(
            {"receipt_id": receipt.id, "voucher_id": loose.id, "amount": 40.0}
        )
        with self.assertRaises(ValidationError):
            loose.write({"sheet_id": False})
        self.assertEqual(loose.sheet_id, self.sheet)

    def test_a_voucher_cannot_join_another_company_sheet(self):
        """``check_company`` MUST be enforced, not only offered by the UI."""
        company_b = self._company_b()
        sheet_b = self._sheet(create_internal_seller(self.env, "consist-b"), company_b)
        with self.assertRaises(UserError):
            self._voucher(sheet=sheet_b, company_id=self.env.company.id)

    def test_sheet_company_is_locked_once_it_has_members(self):
        """Allocations follow the sheet company; vouchers keep their own."""
        company_b = self._company_b()
        empty = self._sheet(create_internal_seller(self.env, "consist-empty"))
        empty.write({"company_id": company_b.id})
        self.assertEqual(empty.company_id, company_b)
        self._voucher()
        with self.assertRaises(UserError):
            self.sheet.write({"company_id": company_b.id})
        self.assertEqual(self.sheet.company_id, self.env.company)

    def test_company_consistency_is_checked_on_the_collection_models(self):
        models_ = (
            "collection.voucher",
            "collection.receipt.value",
            "collection.cash.replacement",
            "collection.connector.seller.binding",
            "collection.connector.customer.binding",
        )
        for name in models_:
            with self.subTest(model=name):
                self.assertTrue(self.env[name]._check_company_auto)
        checked = (
            ("collection.voucher", "sheet_id"),
            ("collection.voucher", "allocation_id"),
            ("collection.receipt.value", "voucher_id"),
            ("collection.cash.replacement", "cash_voucher_id"),
            ("collection.cash.replacement", "deposit_voucher_id"),
        )
        for name, field in checked:
            with self.subTest(model=name, field=field):
                self.assertTrue(self.env[name]._fields[field].check_company)
