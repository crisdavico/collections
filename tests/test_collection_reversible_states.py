# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Every voucher and sheet can go back to a state where it can change or go.

Back to Draft undoes a voucher validation (giving replaced cash back), and
Reset to Open brings a later sheet back to Open, where it can be corrected,
amended or deleted, and then run forward again.
"""

from datetime import date

from odoo.exceptions import AccessError, UserError
from odoo.fields import Command
from odoo.tests import TransactionCase

from .test_collection_payment import (
    create_collection_user,
    dummy_customer_partner,
    ensure_enabled_seller,
)


class TestCollectionReversibleStates(TransactionCase):
    def setUp(self):
        super().setUp()
        self.seller = ensure_enabled_seller(self.env)
        catalog = self.env.ref("collection.document_type_seller_commission")
        self.env.company.write(
            {"allowed_document_type_ids": [Command.link(catalog.id)]}
        )
        self.sheet = self.env["collection.sheet"].create({"seller_id": self.seller.id})
        partner = dummy_customer_partner(self.env, customer="REVERSIBLE")
        self.cash = self.env["collection.voucher"].create(
            {
                "partner_id": partner.id,
                "document_type": "cash",
                "seller_id": self.seller.id,
                "sheet_id": self.sheet.id,
                "amount": 400.0,
            }
        )
        self.allocation = self.env["collection.allocation"].create(
            {
                "sheet_id": self.sheet.id,
                "partner_id": partner.id,
                "voucher_ids": [Command.set(self.cash.ids)],
                "line_ids": [
                    Command.create(
                        {
                            "external_invoice_id": "INV-REVERSIBLE",
                            "invoice_number": "INV-REVERSIBLE",
                            "due_date": date(2026, 1, 31),
                            "invoice_balance": 400.0,
                            "amount_applied": 400.0,
                        }
                    )
                ],
            }
        )
        self.receipt = self.allocation._receipt_get_or_create("invoice")
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

    def _value_of(self, voucher):
        return sum(voucher.receipt_value_ids.mapped("amount"))

    def _confirm(self, withheld=300.0):
        self.sheet.action_declare_cash(commission_withheld=withheld)
        self.sheet.action_confirm()
        self.assertEqual(self.cash.replaced_amount, withheld)
        return self._commission()

    def _reinstated_commission(self):
        commission = self._confirm()
        self.sheet.action_cancel()
        self.sheet.action_reinstate()
        return commission

    # Back to Draft ------------------------------------------------------

    def test_validated_cash_goes_back_to_draft_and_can_be_deleted(self):
        self.cash.action_back_to_draft()
        self.assertEqual(self.cash.state, "draft")
        self.assertFalse(self.cash.reviewed_by)
        self.cash.unlink()
        self.assertFalse(self.cash.exists())
        self.assertFalse(self.receipt.value_ids)
        self.assertEqual(self.allocation.total_vouchers, 0.0)

    def test_commission_back_to_draft_gives_the_cash_back(self):
        commission = self._reinstated_commission()
        commission.action_back_to_draft()
        self.assertEqual(commission.state, "draft")
        self.assertEqual(self.cash.replaced_amount, 0.0)
        self.assertEqual(self._value_of(self.cash), 400.0)
        self.assertEqual(self._value_of(commission), 0.0)
        self.assertEqual(self.receipt.total_values, 400.0)
        commission.unlink()
        self.assertFalse(commission.exists())

    def test_replaced_cash_waits_for_its_replacing_voucher(self):
        commission = self._reinstated_commission()
        with self.assertRaisesRegex(UserError, "replaced by a seller deposit"):
            self.cash.action_back_to_draft()
        self.assertEqual(self.cash.state, "validated_seller")
        self.assertEqual(self.cash.replaced_amount, 300.0)
        (commission | self.cash).action_back_to_draft()
        self.assertEqual(self.cash.state, "draft")

    def test_back_to_draft_is_refused_past_submitted(self):
        self._confirm()
        with self.assertRaisesRegex(UserError, "Reset the sheet to open first"):
            self.cash.action_back_to_draft()
        self.assertEqual(self.cash.state, "validated_seller")

    def test_back_to_draft_of_a_draft_voucher_is_refused(self):
        self.cash.action_back_to_draft()
        with self.assertRaisesRegex(UserError, "Only validated vouchers"):
            self.cash.action_back_to_draft()

    def test_back_to_draft_needs_a_collections_user(self):
        plain = self.env["res.users"].create(
            {
                "name": "Plain Internal",
                "login": "plain_reversible",
                "group_ids": [Command.link(self.env.ref("base.group_user").id)],
            }
        )
        with self.assertRaises(AccessError):
            self.cash.with_user(plain).action_back_to_draft()
        self.assertEqual(self.cash.state, "validated_seller")

    def test_raw_draft_write_keeping_the_proof_gives_the_cash_back(self):
        commission = self._reinstated_commission()
        commission.write(
            {
                "state": "draft",
                "message_main_attachment_id": commission.message_main_attachment_id.id,
            }
        )
        self.assertEqual(commission.state, "draft")
        self.assertEqual(self.cash.replaced_amount, 0.0)
        self.assertEqual(self._value_of(self.cash), 400.0)

    # Reset to Open ------------------------------------------------------

    def test_closed_marked_sheet_resets_to_open_and_can_be_deleted(self):
        commission = self._confirm()
        self.sheet.action_close()
        self.sheet.action_mark_erp_entered()
        self.sheet.action_reset_to_open()
        self.assertEqual(self.sheet.state, "open")
        self.assertFalse(self.sheet.erp_entered_date)
        self.assertEqual(self.allocation.state, "draft")
        self.assertEqual(self.receipt.state, "draft")
        self.assertFalse(commission.exists())
        self.assertEqual(self.cash.replaced_amount, 0.0)
        self.assertEqual(self._value_of(self.cash), 400.0)
        self.assertEqual(self.sheet.commission_withheld, 0.0)
        self.assertFalse(self.sheet.cash_declared_at)
        self.sheet.unlink()
        self.assertFalse(self.sheet.exists())
        self.assertFalse(self.allocation.exists())

    def test_every_later_state_resets_to_open(self):
        for step in ("submitted", "proposal", "cancelled"):
            with self.subTest(step=step):
                if step != "submitted":
                    self._confirm()
                if step == "cancelled":
                    self.sheet.action_cancel()
                self.assertEqual(self.sheet.state, step)
                self.sheet.action_reset_to_open()
                self.assertEqual(self.sheet.state, "open")
                self.assertFalse(self._commission())
                self.sheet.action_seller_close()

    def test_reset_is_refused_while_the_seller_has_another_open_sheet(self):
        other = self.env["collection.sheet"].create({"seller_id": self.seller.id})
        with self.assertRaisesRegex(
            UserError,
            f"The seller already has an open sheet: {other.name}. Close or "
            "delete it first.",
        ):
            self.sheet.action_reset_to_open()
        self.assertEqual(self.sheet.state, "submitted")

    def test_reset_needs_a_manager(self):
        user = create_collection_user(self.env, "reversible_user")
        with self.assertRaises(AccessError):
            self.sheet.with_user(user).action_reset_to_open()
        self.assertEqual(self.sheet.state, "submitted")
        manager = create_collection_user(self.env, "reversible_mgr", manager=True)
        self.sheet.with_user(manager).action_reset_to_open()
        self.assertEqual(self.sheet.state, "open")

    def test_open_sheet_cannot_be_reset(self):
        self.sheet.action_reset_to_open()
        with self.assertRaisesRegex(UserError, "can be reset to open"):
            self.sheet.action_reset_to_open()

    def test_raw_state_write_to_open_resets_the_sheet(self):
        self.sheet.write({"state": "open"})
        self.assertEqual(self.sheet.state, "open")

    def test_reset_sheet_runs_the_forward_flow_again(self):
        self._confirm()
        self.sheet.action_reset_to_open()
        self.sheet.action_seller_close()
        self.sheet.action_declare_cash(commission_withheld=100.0)
        self.sheet.action_confirm()
        commission = self._commission()
        self.assertEqual(commission.amount, 100.0)
        self.assertEqual(self.cash.replaced_amount, 100.0)
        self.assertEqual(self._value_of(self.cash), 300.0)
        self.sheet.action_close()
        self.assertEqual(self.sheet.state, "closed")
