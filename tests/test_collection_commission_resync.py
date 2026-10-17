# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""The commission voucher follows the declared commission, never the reverse.

Confirm mints one ``seller_commission`` from ``commission_withheld``. After
Cancel and Reinstate the seller may declare again, and the voucher, the cash
it replaced and ``cash_on_hand`` must agree with the new declaration.
"""

import json
from datetime import date

from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import TransactionCase

from odoo.addons.collection.tools.collection_voucher import (
    _collection_normalize_amount,
)

from .test_collection_payment import (
    create_collection_user,
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
)


class TestCollectionCommissionResync(TransactionCase):
    def setUp(self):
        super().setUp()
        seller = ensure_enabled_seller(self.env)
        catalog = self.env.ref("collection.document_type_seller_commission")
        self.env.company.write(
            {"allowed_document_type_ids": [Command.link(catalog.id)]}
        )
        self.sheet = self.env["collection.sheet"].create({"seller_id": seller.id})
        partner = dummy_customer_partner(self.env, customer="COMM-RESYNC")
        self.cash = self.env["collection.voucher"].create(
            {
                "partner_id": partner.id,
                "document_type": "cash",
                "seller_id": seller.id,
                "sheet_id": self.sheet.id,
                "amount": 400.0,
            }
        )
        allocation = self.env["collection.allocation"].create(
            {
                "sheet_id": self.sheet.id,
                "partner_id": partner.id,
                "voucher_ids": [Command.set(self.cash.ids)],
                "line_ids": [
                    Command.create(
                        {
                            "external_invoice_id": "INV-COMM-RESYNC",
                            "invoice_number": "INV-COMM-RESYNC",
                            "due_date": date(2026, 1, 31),
                            "invoice_balance": 400.0,
                            "amount_applied": 400.0,
                        }
                    )
                ],
            }
        )
        self.receipt = allocation._receipt_get_or_create("invoice")
        self.env["collection.receipt.value"].create(
            {
                "receipt_id": self.receipt.id,
                "voucher_id": self.cash.id,
                "amount": 400.0,
            }
        )
        self.cash.action_validate_seller()
        self.sheet.action_seller_close()

    def _commission(self):
        return self.sheet.voucher_ids.filtered(
            lambda voucher: voucher.document_type == "seller_commission"
        )

    def _confirmed_then_reinstated(self, withheld=300.0):
        self.sheet.action_declare_cash(commission_withheld=withheld)
        self.sheet.action_confirm()
        commission = self._commission()
        self.assertEqual(commission.amount, withheld)
        self.sheet.action_cancel()
        self.sheet.action_reinstate()
        self.assertEqual(self.sheet.state, "submitted")
        return commission

    def _value_of(self, voucher):
        return sum(voucher.receipt_value_ids.mapped("amount"))

    def _assert_in_step(self, commission, withheld):
        self.assertEqual(commission.amount, withheld)
        self.assertEqual(self._value_of(commission), withheld)
        self.assertEqual(self.cash.replaced_amount, withheld)
        self.assertEqual(self._value_of(self.cash), 400.0 - withheld)
        self.assertEqual(self.receipt.total_values, 400.0)
        self.assertEqual(self.sheet.cash_on_hand, 400.0 - withheld)

    def test_raised_commission_re_replaces_cash(self):
        commission = self._confirmed_then_reinstated(300.0)
        self.sheet.action_declare_cash(commission_withheld=350.0)
        self._assert_in_step(commission, 350.0)
        self.sheet.action_confirm()
        self.assertEqual(self._commission(), commission)
        self._assert_in_step(commission, 350.0)

    def test_lowered_commission_gives_cash_back(self):
        commission = self._confirmed_then_reinstated(300.0)
        self.sheet.action_declare_cash(commission_withheld=100.0)
        self._assert_in_step(commission, 100.0)
        self.assertEqual(commission.replacing_amount, 100.0)

    def test_zero_commission_voids_the_voucher(self):
        commission = self._confirmed_then_reinstated(300.0)
        self.sheet.action_declare_cash(commission_withheld=0.0)
        self.assertEqual(commission.amount, 0.0)
        self.assertFalse(commission.receipt_value_ids)
        self.assertEqual(self.cash.replaced_amount, 0.0)
        self.assertEqual(self._value_of(self.cash), 400.0)
        self.assertEqual(self.sheet.cash_on_hand, 400.0)
        self.sheet.action_confirm()
        self.assertEqual(self._commission(), commission)
        self.assertEqual(commission.amount, 0.0)

    def test_voided_commission_comes_back_when_declared_again(self):
        commission = self._confirmed_then_reinstated(300.0)
        self.sheet.action_declare_cash(commission_withheld=0.0)
        self.sheet.action_declare_cash(commission_withheld=200.0)
        self._assert_in_step(commission, 200.0)

    def test_share_moved_by_the_board_is_given_back_too(self):
        """A commission share moved to another receipt still comes back."""
        self.sheet.action_declare_cash(commission_withheld=300.0)
        self.sheet.action_confirm()
        commission = self._commission()
        partner = dummy_customer_partner(self.env, customer="COMM-RESYNC-B")
        other = self.env["collection.allocation"].create(
            {"sheet_id": self.sheet.id, "partner_id": partner.id, "line_ids": []}
        )
        moved = other._receipt_get_or_create("invoice")
        commission.receipt_value_ids.amount = 200.0
        self.env["collection.receipt.value"].create(
            {"receipt_id": moved.id, "voucher_id": commission.id, "amount": 100.0}
        )
        self.sheet.action_cancel()
        self.sheet.action_reinstate()
        # Below the moved share: only taking that share back too lets the
        # amount fall under the values the voucher held.
        self.sheet.action_declare_cash(commission_withheld=50.0)
        self.assertEqual(commission.amount, 50.0)
        self.assertEqual(self._value_of(commission), 50.0)
        self.assertEqual(self.cash.replaced_amount, 50.0)
        self.assertEqual(self._value_of(self.cash), 350.0)
        self.assertEqual(self.receipt.total_values + moved.total_values, 400.0)
        self.assertEqual(other.total_vouchers, 100.0)

    def test_share_returned_to_the_pool_is_given_back_too(self):
        """The board returned part of the commission to the unassigned pool.

        That share is on no receipt, so the reversal records it without moving
        a value: cash keeps it as free money and the new amount replaces cash
        only once.
        """
        self.sheet.action_declare_cash(commission_withheld=300.0)
        self.sheet.action_confirm()
        commission = self._commission()
        commission.receipt_value_ids.amount = 100.0
        self.sheet.action_cancel()
        self.sheet.action_reinstate()
        self.sheet.action_declare_cash(commission_withheld=50.0)
        self.assertEqual(commission.amount, 50.0)
        self.assertEqual(self._value_of(commission), 50.0)
        self.assertEqual(self.cash.replaced_amount, 50.0)
        self.assertEqual(self._value_of(self.cash), 150.0)
        self.assertEqual(self.receipt.total_values, 200.0)
        self.assertEqual(self.sheet.cash_on_hand, 350.0)

    def test_commission_above_replaceable_cash_is_refused(self):
        commission = self._confirmed_then_reinstated(300.0)
        with self.assertRaises(UserError):
            self.sheet.action_declare_cash(commission_withheld=500.0)
        self._assert_in_step(commission, 300.0)

    def test_a_new_zero_amount_commission_is_still_refused(self):
        with self.assertRaises(ValidationError):
            self.env["collection.voucher"].create(
                {
                    "document_type": "seller_commission",
                    "seller_id": self.sheet.seller_id.id,
                    "amount": 0.0,
                }
            )

    def test_negative_withheld_commission_is_refused(self):
        with self.assertRaises(ValidationError):
            self.sheet.action_declare_cash(commission_withheld=-5.0)
        with self.assertRaises(ValidationError):
            self.sheet.write({"commission_withheld": -0.01})
        self.assertFalse(self.sheet.commission_withheld)
        self.assertFalse(self.sheet.cash_declared_at)


class TestCollectionCommissionDeclareTool(TransactionCase):
    def setUp(self):
        super().setUp()
        self.operator = create_collection_user(self.env, "comm_resync_tool_user")
        self.seller = create_internal_seller(self.env, "comm_resync_tool_seller")
        ensure_enabled_seller(self.env, self.seller)
        self.sheet = self.env["collection.sheet"].create({"seller_id": self.seller.id})
        self.sheet.action_seller_close()

    def _call(self, withheld):
        text, _info = self.env["muk_mcp.tool"]._call(
            "declare_collection_cash",
            {"seller_id": self.seller.id, "commission_withheld": withheld},
            self.env(user=self.operator),
        )
        return json.loads(text)

    def test_numeric_zero_commission_is_declared(self):
        for withheld in (0, 0.0, "0"):
            with self.subTest(withheld=withheld):
                self._call(withheld)
                self.assertEqual(self.sheet.commission_withheld, 0.0)
                self.assertTrue(self.sheet.cash_declared_at)

    def test_negative_commission_is_refused_with_a_generic_message(self):
        for withheld in (-1, -0.01, "-3"):
            with self.subTest(withheld=withheld):
                with self.assertRaises(UserError) as ctx:
                    self._call(withheld)
                self.assertNotIsInstance(ctx.exception, ValidationError)
                self.assertIn("commission_withheld", str(ctx.exception))
                self.assertFalse(self.sheet.cash_declared_at)

    def test_missing_commission_is_still_refused(self):
        for withheld in (None, "", False, "abc"):
            with self.subTest(withheld=withheld):
                with self.assertRaises(UserError):
                    self._call(withheld)
                self.assertFalse(self.sheet.cash_declared_at)

    def test_amount_parser_accepts_zero_and_refuses_blanks(self):
        self.assertEqual(_collection_normalize_amount(0), 0.0)
        self.assertEqual(_collection_normalize_amount(0.0), 0.0)
        for value in (None, False, True, "", "  "):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    _collection_normalize_amount(value)
