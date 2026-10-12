# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tests import TransactionCase

from odoo.addons.collection.models.collection_common import privileged

from .common_connector import confirm_sheet
from .test_collection_payment import (
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
)


class TestCollectionAppliedCaps(TransactionCase):
    """``amount_applied`` is capped on every path, not only by the MCP tool."""

    def setUp(self):
        super().setUp()
        self.seller = ensure_enabled_seller(self.env)
        self.sheet = self._sheet(self.seller)
        self.partner = dummy_customer_partner(self.env, customer="CUST-CAPS")

    def _sheet(self, seller):
        ensure_enabled_seller(self.env, seller)
        return self.env["collection.sheet"].create({"seller_id": seller.id})

    def _voucher(self, sheet, amount):
        return self.env["collection.voucher"].create(
            {
                "partner_id": self.partner.id,
                "document_type": "bank_transfer",
                "amount": amount,
                "seller_id": sheet.seller_id.id,
                "sheet_id": sheet.id,
            }
        )

    def _line(self, applied, balance=100.0, invoice="INV-CAPS", **extra):
        vals = {
            "external_invoice_id": invoice,
            "invoice_number": invoice,
            "invoice_balance": balance,
            "amount_applied": applied,
        }
        vals.update(extra)
        return vals

    def _allocation(self, sheet, lines, vouchers=None):
        vals = {
            "sheet_id": sheet.id,
            "partner_id": self.partner.id,
            "line_ids": [Command.create(line) for line in lines],
        }
        if vouchers:
            vals["voucher_ids"] = [Command.set(vouchers.ids)]
        return self.env["collection.allocation"].create(vals)

    def _funded(self, value_amount, kind="invoice", applied=0.0, balance=100.0):
        voucher = self._voucher(self.sheet, 100.0)
        allocation = self._allocation(
            self.sheet,
            [self._line(applied, balance=balance, document_kind=kind)],
            vouchers=voucher,
        )
        receipt = self.env["collection.receipt"].create(
            {"allocation_id": allocation.id, "document_kind": kind}
        )
        value = self.env["collection.receipt.value"].create(
            {"receipt_id": receipt.id, "voucher_id": voucher.id, "amount": value_amount}
        )
        return allocation, receipt, value

    # (a) one line never applies more than its invoice balance

    def test_line_applied_above_its_invoice_balance_is_refused(self):
        with self.assertRaises(ValidationError) as error:
            self._allocation(self.sheet, [self._line(150.0, balance=100.0)])
        self.assertIn("invoice balance", str(error.exception))
        allocation = self._allocation(self.sheet, [self._line(50.0)])
        with self.assertRaises(ValidationError):
            allocation.line_ids.amount_applied = 100.01
        self.assertEqual(allocation.line_ids.amount_applied, 50.0)

    def test_line_applied_up_to_its_invoice_balance_passes(self):
        allocation = self._allocation(self.sheet, [self._line(100.0, balance=100.0)])
        self.assertEqual(allocation.total_applied, 100.0)

    def test_unapplied_line_with_a_credit_balance_passes(self):
        """A zero application never trips the cap, whatever the snapshot says."""
        allocation = self._allocation(self.sheet, [self._line(0.0, balance=-20.0)])
        self.assertEqual(allocation.line_ids.amount_applied, 0.0)

    # (b) one invoice is never over-applied across allocations and sheets

    def test_same_invoice_over_applied_across_sheets_is_refused(self):
        self._allocation(self.sheet, [self._line(70.0)])
        other_sheet = self._sheet(create_internal_seller(self.env, "caps-seller-b"))
        with self.assertRaises(ValidationError) as error:
            self._allocation(other_sheet, [self._line(50.0)])
        self.assertIn("available invoice balance", str(error.exception))
        other = self._allocation(other_sheet, [self._line(30.0)])
        with self.assertRaises(ValidationError):
            other.line_ids.amount_applied = 30.01
        self.assertEqual(other.line_ids.amount_applied, 30.0)

    def test_zero_line_on_an_over_applied_invoice_still_saves(self):
        """Snapshotting a document with nothing applied MUST NOT be blocked."""
        self._allocation(self.sheet, [self._line(100.0)])
        other_sheet = self._sheet(create_internal_seller(self.env, "caps-seller-z"))
        allocation = self._allocation(other_sheet, [self._line(0.0, balance=40.0)])
        self.assertEqual(allocation.line_ids.amount_applied, 0.0)

    def test_drafts_of_a_cancelled_sheet_do_not_count(self):
        """A cancelled sheet frees the invoice; Reinstate re-checks it."""
        voucher = self._voucher(self.sheet, 70.0)
        self._allocation(self.sheet, [self._line(70.0)], vouchers=voucher)
        with privileged("collection_audited_state"):
            voucher.write({"state": "validated_collections"})
        confirm_sheet(self.sheet)
        self.sheet.action_cancel()
        other_sheet = self._sheet(create_internal_seller(self.env, "caps-seller-c"))
        other = self._allocation(other_sheet, [self._line(50.0)])
        self.assertEqual(other.line_ids.amount_applied, 50.0)
        with self.assertRaises(ValidationError):
            self.sheet.action_reinstate()
        self.assertEqual(self.sheet.state, "cancelled")

    # (c) a receipt never applies more than its values fund

    def test_line_applied_above_its_receipt_values_is_refused(self):
        allocation, _receipt, _value = self._funded(60.0)
        with self.assertRaises(ValidationError) as error:
            allocation.line_ids.amount_applied = 80.0
        self.assertIn("funded values", str(error.exception))
        self.assertEqual(allocation.line_ids.amount_applied, 0.0)

    def test_line_applied_up_to_its_receipt_values_passes(self):
        allocation, _receipt, _value = self._funded(60.0)
        allocation.line_ids.amount_applied = 60.0
        self.assertEqual(allocation.total_applied, 60.0)

    def test_an_overdrawn_receipt_may_only_shrink_its_applications(self):
        """Values may shrink first (the board does); applications then only fall."""
        allocation, _receipt, value = self._funded(100.0, applied=100.0)
        value.amount = 40.0
        allocation.line_ids.amount_applied = 70.0
        self.assertEqual(allocation.line_ids.amount_applied, 70.0)
        with self.assertRaises(ValidationError):
            allocation.line_ids.amount_applied = 90.0
        self.assertEqual(allocation.line_ids.amount_applied, 70.0)

    def test_moving_a_line_to_an_underfunded_circuit_is_refused(self):
        allocation, _receipt, _value = self._funded(100.0, applied=50.0)
        quotation = self.env["collection.receipt"].create(
            {"allocation_id": allocation.id, "document_kind": "quotation"}
        )
        self.assertFalse(quotation.value_ids)
        with self.assertRaises(ValidationError):
            allocation.line_ids.document_kind = "quotation"
        self.assertEqual(allocation.line_ids.document_kind, "invoice")

    def test_applications_without_a_receipt_are_not_capped_here(self):
        """No receipt for that circuit yet: the Confirm gate still applies."""
        voucher = self._voucher(self.sheet, 100.0)
        allocation = self._allocation(self.sheet, [self._line(80.0)], vouchers=voucher)
        self.assertFalse(allocation.receipt_ids)
        self.assertEqual(allocation.total_applied, 80.0)
