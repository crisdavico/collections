# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Replacing an approved voucher's proof sends it back to Document Review.

For a ``seller_deposit`` that also means giving back the cash its approval
replaced, so approving it again replaces from scratch. The proof of a voucher
on a closed or cancelled sheet does not change at all.
"""

from base64 import b64decode
from datetime import date

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import TransactionCase

from .test_collection_payment import (
    PDF_B64,
    PNG_B64,
    dummy_customer_partner,
    ensure_enabled_seller,
    post_voucher_proof,
)


class TestCollectionDepositProofSwap(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.company.write({"document_review_enabled": True})
        catalog = self.env.ref("collection.document_type_seller_deposit")
        self.env.company.write(
            {"allowed_document_type_ids": [Command.link(catalog.id)]}
        )
        seller = ensure_enabled_seller(self.env)
        self.sheet = self.env["collection.sheet"].create({"seller_id": seller.id})
        self.partner = dummy_customer_partner(self.env, customer="PROOF-SWAP")
        self.cash = self._voucher("cash", 100.0)
        allocation = self.env["collection.allocation"].create(
            {
                "sheet_id": self.sheet.id,
                "partner_id": self.partner.id,
                "voucher_ids": [Command.set(self.cash.ids)],
                "line_ids": [
                    Command.create(
                        {
                            "external_invoice_id": "INV-PROOF-SWAP",
                            "invoice_number": "INV-PROOF-SWAP",
                            "due_date": date(2026, 1, 31),
                            "invoice_balance": 100.0,
                            "amount_applied": 100.0,
                        }
                    )
                ],
            }
        )
        receipt = allocation._receipt_get_or_create("invoice")
        self.env["collection.receipt.value"].create(
            {"receipt_id": receipt.id, "voucher_id": self.cash.id, "amount": 100.0}
        )
        self.deposit = self.env["collection.voucher"].create(
            {
                "document_type": "seller_deposit",
                "seller_id": seller.id,
                "sheet_id": self.sheet.id,
                "amount": 60.0,
                "voucher_number": "SD-PROOF-SWAP",
                "voucher_date": date(2026, 9, 8),
            }
        )
        post_voucher_proof(self.deposit, "slip.png", PNG_B64)
        (self.cash | self.deposit).action_validate_seller()
        self.sheet.action_seller_close(commission_withheld=0.0)

    def _voucher(self, document_type, amount, **extra):
        vals = {
            "partner_id": self.partner.id,
            "document_type": document_type,
            "seller_id": self.sheet.seller_id.id,
            "sheet_id": self.sheet.id,
            "amount": amount,
        }
        vals.update(extra)
        return self.env["collection.voucher"].create(vals)

    def _approve(self, voucher):
        voucher.action_review_approve(self.sheet.id, {})
        self.assertEqual(voucher.state, "validated_collections")

    def _new_proof(self, voucher, name="slip-2.pdf"):
        return self.env["ir.attachment"].create(
            {
                "name": name,
                "raw": b64decode(PDF_B64),
                "res_model": "collection.voucher",
                "res_id": voucher.id,
            }
        )

    def _held(self, voucher):
        return sum(voucher.receipt_value_ids.mapped("amount"))

    def _assert_replaced(self, amount):
        self.assertEqual(self._held(self.deposit), amount)
        self.assertEqual(self.cash.replaced_amount, amount)
        self.assertEqual(self._held(self.cash), 100.0 - amount)

    def _close(self):
        self.sheet.action_declare_cash(commission_withheld=0.0)
        self.sheet.action_confirm()
        self.sheet.action_close()
        self.assertEqual(self.sheet.state, "closed")

    def test_swap_gives_the_replaced_cash_back(self):
        self._approve(self.deposit)
        self._assert_replaced(60.0)
        self.deposit.write(
            {"message_main_attachment_id": self._new_proof(self.deposit).id}
        )
        self.assertEqual(self.deposit.state, "validated_seller")
        self.assertFalse(self.deposit.reviewed_by)
        self._assert_replaced(0.0)

    def test_swapped_deposit_can_be_approved_and_confirmed_again(self):
        self._approve(self.deposit)
        self.deposit.write(
            {"message_main_attachment_id": self._new_proof(self.deposit).id}
        )
        self._approve(self.deposit)
        self._assert_replaced(60.0)
        self.sheet.action_declare_cash(commission_withheld=0.0)
        self.sheet.action_confirm()
        self.assertEqual(self.sheet.state, "proposal")

    def test_review_can_lower_a_swapped_deposit(self):
        """The new slip shows 50: the reviewer corrects the amount and approves."""
        self._approve(self.deposit)
        self.deposit.write(
            {"message_main_attachment_id": self._new_proof(self.deposit).id}
        )
        self.deposit.action_review_approve(self.sheet.id, {"amount": 50.0})
        self.assertEqual(self.deposit.amount, 50.0)
        self._assert_replaced(50.0)

    def test_swap_and_new_amount_in_one_write(self):
        """The cash goes back before the lower amount is written."""
        self._approve(self.deposit)
        self.deposit.write(
            {
                "message_main_attachment_id": self._new_proof(self.deposit).id,
                "amount": 40.0,
            }
        )
        self.assertEqual(self.deposit.state, "validated_seller")
        self.assertEqual(self.deposit.amount, 40.0)
        self._assert_replaced(0.0)

    def test_delete_then_upload_reopens_review_like_a_swap(self):
        self._approve(self.deposit)
        self.deposit.message_main_attachment_id.unlink()
        self.assertFalse(self.deposit.message_main_attachment_id)
        self.assertEqual(self.deposit.state, "validated_collections")
        post_voucher_proof(self.deposit, "slip-3.pdf", PDF_B64)
        self.assertTrue(self.deposit.message_main_attachment_id)
        self.assertEqual(self.deposit.state, "validated_seller")
        self._assert_replaced(0.0)
        self._approve(self.deposit)
        self._assert_replaced(60.0)

    def test_delete_then_upload_reopens_any_reviewed_voucher(self):
        transfer = self._voucher("bank_transfer", 10.0, voucher_number="BT-SWAP")
        post_voucher_proof(transfer, "transfer.png", PNG_B64)
        transfer.action_validate_seller()
        self._approve(transfer)
        transfer.message_main_attachment_id.unlink()
        post_voucher_proof(transfer, "transfer-2.pdf", PDF_B64)
        self.assertEqual(transfer.state, "validated_seller")
        self.assertFalse(transfer.reviewed_by)

    def test_proof_is_frozen_on_closed_and_cancelled_sheets(self):
        self._approve(self.deposit)
        self._close()
        for state in ("closed", "cancelled"):
            if state == "cancelled":
                self.sheet.action_cancel()
            proof = self.deposit.message_main_attachment_id
            with self.subTest(state=state):
                with self.assertRaises(UserError):
                    self.deposit.write(
                        {"message_main_attachment_id": self._new_proof(self.deposit).id}
                    )
                with self.assertRaises(UserError):
                    proof.unlink()
                self.assertEqual(self.deposit.state, "validated_collections")
                self.assertEqual(self.deposit.message_main_attachment_id, proof)
                self._assert_replaced(60.0)

    def test_approved_proof_cannot_go_back_to_review_in_proposal(self):
        """Document Review does not run past submitted, so nothing reopens."""
        self._approve(self.deposit)
        self.sheet.action_declare_cash(commission_withheld=0.0)
        self.sheet.action_confirm()
        with self.assertRaises(UserError):
            self.deposit.write(
                {"message_main_attachment_id": self._new_proof(self.deposit).id}
            )
        self.assertEqual(self.deposit.state, "validated_collections")
        self._assert_replaced(60.0)

    def test_a_first_proof_on_a_closed_cash_voucher_still_posts(self):
        """Chatter keeps working where a proof reopens nothing."""
        self._approve(self.deposit)
        self._close()
        self.assertFalse(self.cash.message_main_attachment_id)
        post_voucher_proof(self.cash, "cash.png", PNG_B64)
        self.assertTrue(self.cash.message_main_attachment_id)
        self.assertEqual(self.cash.state, "validated_seller")

    def test_a_share_left_in_the_pool_is_given_back_too(self):
        """The board returned part of the deposit to the unassigned pool.

        That part is on no receipt, so no value can move back to cash; the
        reversal still gives it back in the ledger, or approving again would
        replace more cash than the deposit holds.
        """
        self._approve(self.deposit)
        self.deposit.receipt_value_ids.amount = 40.0
        self.deposit.write(
            {"message_main_attachment_id": self._new_proof(self.deposit).id}
        )
        self.assertEqual(self.cash.replaced_amount, 0.0)
        self.assertEqual(self._held(self.cash), 80.0)
        self._approve(self.deposit)
        self.assertEqual(self.cash.replaced_amount, 60.0)
        self.assertEqual(self._held(self.deposit), 60.0)
        self.assertEqual(self._held(self.cash), 20.0)

    def test_approved_proof_cannot_be_deleted_in_proposal(self):
        """Deleting it would leave an approved voucher with no evidence.

        Past submitted no new proof can be reviewed, so the delete half of
        delete-then-upload is refused as the swap is.
        """
        self._approve(self.deposit)
        self.sheet.action_declare_cash(commission_withheld=0.0)
        self.sheet.action_confirm()
        proof = self.deposit.message_main_attachment_id
        with self.assertRaises(UserError):
            proof.unlink()
        self.assertTrue(proof.exists())
        self.assertEqual(self.deposit.message_main_attachment_id, proof)
        self.assertEqual(self.deposit.state, "validated_collections")
        self._assert_replaced(60.0)

    def test_a_commission_proof_swap_keeps_its_replacement(self):
        """A commission has no proof to review, so a new file reopens nothing.

        Reopening it gave the replaced cash back, and nothing replaced it
        again: Confirm only re-syncs an amount that changed, and a commission
        needs no review to pass Confirm.
        """
        catalog = self.env.ref("collection.document_type_seller_commission")
        self.env.company.write(
            {"allowed_document_type_ids": [Command.link(catalog.id)]}
        )
        self._approve(self.deposit)
        self.sheet.action_declare_cash(commission_withheld=30.0)
        self.sheet.action_confirm()
        commission = self.sheet.voucher_ids.filtered(
            lambda voucher: voucher.document_type == "seller_commission"
        )
        self.sheet.action_cancel()
        self.sheet.action_reinstate()
        self.assertEqual(self._held(commission), 30.0)
        self.assertEqual(self.cash.replaced_amount, 90.0)
        post_voucher_proof(commission, "commission.png", PNG_B64)
        commission.write({"message_main_attachment_id": self._new_proof(commission).id})
        self.assertEqual(commission.state, "validated_collections")
        self.assertEqual(self._held(commission), 30.0)
        self.assertEqual(self.cash.replaced_amount, 90.0)
        self.sheet.action_declare_cash(commission_withheld=30.0)
        self.sheet.action_confirm()
        self.assertEqual(self.cash.replaced_amount, 90.0)

    def test_a_swapped_sheet_is_deleted_only_after_the_swap_is_undone(self):
        self._approve(self.deposit)
        self._close()
        self.sheet.action_reset_to_open()
        with self.assertRaisesRegex(UserError, "part of a cash swap"):
            self.sheet.unlink()
        self.assertTrue(self.sheet.exists())
        self.assertEqual(self.deposit.sheet_id, self.sheet)
        self._assert_replaced(60.0)
        self.deposit.action_back_to_draft()
        self._assert_replaced(0.0)
        self.sheet.unlink()
        (self.cash | self.deposit).filtered(
            lambda voucher: voucher.state != "draft"
        ).action_back_to_draft()
        (self.cash | self.deposit).unlink()
        self.assertFalse((self.cash | self.deposit).exists())

    def test_swapped_vouchers_cannot_leave_their_sheet(self):
        self._approve(self.deposit)
        for voucher in (self.deposit, self.cash):
            with self.assertRaisesRegex(UserError, "part of a cash swap"):
                voucher.write({"sheet_id": False})
            self.assertEqual(voucher.sheet_id, self.sheet)
