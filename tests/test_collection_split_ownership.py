# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Collected money follows receipt values, not the voucher's allocation pointer.

``voucher.allocation_id`` names one owner, so a voucher split across two
customers (the receipt-proposal board) or a remittance placed on a customer's
receipt cannot be counted through it. The Close gate and the Planilla read one
figure, ``allocation.total_vouchers``.
"""

from datetime import date

from odoo.fields import Command
from odoo.tests import TransactionCase

from odoo.addons.collection.models.collection_common import privileged

from .test_collection_payment import dummy_customer_partner, ensure_enabled_seller


class TestCollectionSplitOwnership(TransactionCase):
    def setUp(self):
        super().setUp()
        seller = ensure_enabled_seller(self.env)
        self.sheet = self.env["collection.sheet"].create({"seller_id": seller.id})

    def _partner(self, label):
        return dummy_customer_partner(self.env, customer=label)

    def _voucher(self, partner, amount, document_type="bank_transfer"):
        return self.env["collection.voucher"].create(
            {
                "partner_id": partner.id,
                "document_type": document_type,
                "seller_id": self.sheet.seller_id.id,
                "sheet_id": self.sheet.id,
                "amount": amount,
            }
        )

    def _deposit(self, amount):
        catalog = self.env.ref("collection.document_type_seller_deposit")
        self.env.company.write(
            {"allowed_document_type_ids": [Command.link(catalog.id)]}
        )
        return self.env["collection.voucher"].create(
            {
                "document_type": "seller_deposit",
                "seller_id": self.sheet.seller_id.id,
                "sheet_id": self.sheet.id,
                "amount": amount,
                "voucher_number": "SD-SPLIT",
                "voucher_date": date(2026, 9, 8),
            }
        )

    def _allocation(self, partner, applied, vouchers=None, balance=100.0):
        vals = {
            "sheet_id": self.sheet.id,
            "partner_id": partner.id,
            "line_ids": [
                Command.create(
                    {
                        "external_invoice_id": f"INV-{partner.name}",
                        "invoice_number": f"INV-{partner.name}",
                        "due_date": date(2026, 1, 31),
                        "invoice_balance": balance,
                        "amount_applied": applied,
                    }
                )
            ],
        }
        if vouchers:
            vals["voucher_ids"] = [Command.set(vouchers.ids)]
        return self.env["collection.allocation"].create(vals)

    def _value(self, allocation, voucher, amount):
        receipt = allocation._receipt_get_or_create("invoice")
        return self.env["collection.receipt.value"].create(
            {"receipt_id": receipt.id, "voucher_id": voucher.id, "amount": amount}
        )

    def _approve(self, vouchers):
        with privileged("collection_audited_state"):
            vouchers.write({"state": "validated_collections"})

    def _collected(self):
        customers = self.sheet._collection_report_data()["customers"]
        return {row["name"]: row["collected"] for row in customers}

    def _split_sheet(self):
        """V=100 of A, 40 of it on B's receipt; a 30 remittance on C's receipt."""
        partner_a = self._partner("SPLIT-A")
        partner_b = self._partner("SPLIT-B")
        partner_c = self._partner("SPLIT-C")
        voucher = self._voucher(partner_a, 100.0)
        deposit = self._deposit(30.0)
        allocation_a = self._allocation(partner_a, 60.0, vouchers=voucher)
        allocation_b = self._allocation(partner_b, 0.0)
        allocation_c = self._allocation(partner_c, 0.0)
        self._value(allocation_a, voucher, 60.0)
        self._value(allocation_b, voucher, 40.0)
        self._value(allocation_c, deposit, 30.0)
        allocation_b.line_ids.amount_applied = 40.0
        allocation_c.line_ids.amount_applied = 30.0
        self._approve(voucher | deposit)
        return allocation_a, allocation_b, allocation_c

    def test_split_voucher_counts_on_each_customer_it_pays(self):
        allocation_a, allocation_b, allocation_c = self._split_sheet()
        self.assertEqual(allocation_a.total_vouchers, 60.0)
        self.assertEqual(allocation_b.total_vouchers, 40.0)
        self.assertEqual(allocation_c.total_vouchers, 30.0)

    def test_split_sheet_confirms_and_closes(self):
        allocation_a, _allocation_b, _allocation_c = self._split_sheet()
        self.sheet.action_seller_close()
        self.sheet.action_confirm()
        self.sheet.action_close()
        self.assertEqual(self.sheet.state, "closed")
        self.assertEqual(allocation_a.state, "confirmed")

    def test_planilla_prints_each_customer_share(self):
        self._split_sheet()
        self.assertEqual(
            self._collected(), {"SPLIT-A": 60.0, "SPLIT-B": 40.0, "SPLIT-C": 30.0}
        )
        payload = self.sheet._collection_report_data()
        self.assertEqual(payload["customer_totals"]["collected"], 130.0)

    def test_moving_a_share_moves_the_collected_money(self):
        allocation_a, allocation_b, _allocation_c = self._split_sheet()
        share_b = allocation_b.receipt_ids.value_ids
        share_b.amount = 25.0
        allocation_a.receipt_ids.value_ids.amount = 75.0
        self.assertEqual(allocation_a.total_vouchers, 75.0)
        self.assertEqual(allocation_b.total_vouchers, 25.0)

    def test_voucher_without_receipt_values_counts_on_its_allocation(self):
        """Before receipts exist (UI allocations) the pointer still decides."""
        partner = self._partner("SPLIT-PTR")
        voucher = self._voucher(partner, 80.0)
        allocation = self._allocation(partner, 80.0, vouchers=voucher)
        self.assertFalse(allocation.receipt_ids)
        self.assertEqual(allocation.total_vouchers, 80.0)

    def test_unvalued_voucher_beside_receipt_values_still_counts(self):
        partner = self._partner("SPLIT-MIX")
        valued = self._voucher(partner, 50.0)
        unvalued = self._voucher(partner, 20.0)
        allocation = self._allocation(partner, 50.0, vouchers=valued | unvalued)
        self._value(allocation, valued, 50.0)
        self.assertEqual(allocation.total_vouchers, 70.0)

    def test_partly_valued_voucher_counts_only_its_values(self):
        """Money left off every receipt is unassigned, not collected."""
        partner = self._partner("SPLIT-PART")
        voucher = self._voucher(partner, 100.0)
        allocation = self._allocation(partner, 30.0, vouchers=voucher)
        self._value(allocation, voucher, 30.0)
        self.assertEqual(allocation.total_vouchers, 30.0)

    def test_fully_replaced_cash_is_not_counted_twice(self):
        partner = self._partner("SPLIT-CASH")
        cash = self._voucher(partner, 100.0, document_type="cash")
        allocation = self._allocation(partner, 100.0, vouchers=cash)
        receipt = allocation._receipt_get_or_create("invoice")
        self._value(allocation, cash, 100.0)
        deposit = self._deposit(100.0)
        self.env["collection.receipt.value"]._cash_replace(
            receipt, cash, deposit, 100.0
        )
        self.assertFalse(cash.receipt_value_ids)
        self.assertEqual(cash.allocation_id, allocation)
        self.assertEqual(allocation.total_vouchers, 100.0)
