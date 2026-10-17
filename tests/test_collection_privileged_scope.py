# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Workflow guards trust an in-process scope, never a client context key.

JSON-RPC ``call_kw`` and muk_mcp both merge a caller-supplied ``context`` into
the environment, so each test plays a Collections User who forges one of the
old guard keys and expects the guard to hold anyway.
"""

from datetime import date

from odoo.exceptions import AccessError, UserError
from odoo.fields import Command
from odoo.tests import TransactionCase

from odoo.addons.collection.models import collection_common

from .common_connector import advance_sheet_to
from .test_collection_payment import (
    create_collection_user,
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
)


class TestCollectionPrivilegedScope(TransactionCase):
    """Forged context keys MUST NOT open any collection workflow guard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.seller = create_internal_seller(cls.env, "scope_seller")
        cls.operator = create_collection_user(cls.env, "scope_operator")
        ensure_enabled_seller(cls.env, cls.seller)
        for code in ("cash", "seller_deposit", "seller_commission"):
            catalog = cls.env.ref(f"collection.document_type_{code}")
            cls.env.company.write(
                {"allowed_document_type_ids": [Command.link(catalog.id)]}
            )

    def _forged(self, records, key):
        """``records`` as the operator, carrying a client-forged context key."""
        return records.with_user(self.operator).with_context(**{key: True})

    def _sheet(self):
        return self.env["collection.sheet"].create({"seller_id": self.seller.id})

    def _voucher(self, sheet, partner, amount=100.0, **extra):
        vals = {
            "partner_id": partner.id,
            "document_type": "bank_transfer",
            "seller_id": self.seller.id,
            "sheet_id": sheet.id,
            "amount": amount,
        }
        vals.update(extra)
        return self.env["collection.voucher"].create(vals)

    def _allocation(self, sheet, partner, vouchers, amount=100.0):
        return self.env["collection.allocation"].create(
            {
                "sheet_id": sheet.id,
                "partner_id": partner.id,
                "voucher_ids": [Command.set(vouchers.ids)],
                "line_ids": [
                    Command.create(
                        {
                            # One ERP document per customer: a shared id would
                            # over-apply it across the ledgers of one test.
                            "external_invoice_id": f"SCOPE-INV-{partner.id}",
                            "invoice_number": "A-SCOPE-1",
                            "due_date": date(2026, 1, 31),
                            "invoice_amount": amount,
                            "invoice_balance": amount,
                            "invoice_state": "open",
                            "amount_applied": amount,
                        }
                    )
                ],
            }
        )

    def _ledger(self, state="open", document_type="bank_transfer"):
        """Sheet, voucher, allocation, invoice receipt and one value at ``state``."""
        sheet = self._sheet()
        partner = dummy_customer_partner(self.env, customer=f"SCOPE-{state}")
        voucher = self._voucher(sheet, partner, document_type=document_type)
        allocation = self._allocation(sheet, partner, voucher)
        receipt = self.env["collection.receipt"].create(
            {"allocation_id": allocation.id, "document_kind": "invoice"}
        )
        value = self.env["collection.receipt.value"].create(
            {"receipt_id": receipt.id, "voucher_id": voucher.id, "amount": 100.0}
        )
        advance_sheet_to(sheet, state)
        return sheet, voucher, allocation, receipt, value

    def test_privileged_scope_nests_and_resets_after_an_exception(self):
        privileged = collection_common.privileged
        is_privileged = collection_common.is_privileged
        self.assertFalse(is_privileged("outer"))
        with privileged("outer"):
            self.assertTrue(is_privileged("outer"))
            self.assertFalse(is_privileged("inner"))
            with privileged("inner", "extra"):
                self.assertTrue(is_privileged("outer"))
                self.assertTrue(is_privileged("inner"))
                self.assertTrue(is_privileged("extra"))
            self.assertFalse(is_privileged("inner"))
            self.assertFalse(is_privileged("extra"))
            with self.assertRaises(RuntimeError), privileged("inner"):
                raise RuntimeError("boom")
            self.assertFalse(is_privileged("inner"))
            self.assertTrue(is_privileged("outer"))
        self.assertFalse(is_privileged("outer"))

    def test_forged_audited_state_cannot_skip_document_review(self):
        sheet = self._sheet()
        partner = dummy_customer_partner(self.env, customer="SCOPE-REVIEW")
        voucher = self._voucher(sheet, partner)
        voucher.with_user(self.operator).action_validate_seller()
        self.assertEqual(voucher.state, "validated_seller")
        with self.assertRaises(UserError):
            self._forged(voucher, "collection_audited_state").write(
                {"state": "validated_collections"}
            )
        self.assertEqual(voucher.state, "validated_seller")

    def test_forged_sheet_audited_state_cannot_close_cancel_or_reinstate(self):
        proposal, *_rest = self._ledger("proposal")
        forged = self._forged(proposal, "collection_sheet_audited_state")
        for target in ("closed", "cancelled"):
            with self.subTest(target=target):
                with self.assertRaises(AccessError):
                    forged.write({"state": target})
                self.assertEqual(proposal.state, "proposal")
        cancelled, *_rest = self._ledger("cancelled")
        with self.assertRaises(AccessError):
            self._forged(cancelled, "collection_sheet_audited_state").write(
                {"state": "submitted"}
            )
        self.assertEqual(cancelled.state, "cancelled")

    def test_forged_allocation_audited_state_cannot_change_allocation_state(self):
        _sheet, _voucher, allocation, _receipt, _value = self._ledger("open")
        with self.assertRaises(UserError):
            self._forged(allocation, "collection_allocation_audited_state").write(
                {"state": "confirmed"}
            )
        self.assertEqual(allocation.state, "draft")

    def test_forged_receipt_keys_cannot_change_receipt_state(self):
        _sheet, _voucher, _allocation, receipt, _value = self._ledger("open")
        cases = (
            ("collection_receipt_audited_state", {"state": "closed"}),
            (
                "collection_receipt_issuing",
                {"state": "issued", "external_receipt_id": "FORGED-1"},
            ),
        )
        for key, vals in cases:
            with self.subTest(key=key):
                with self.assertRaises(UserError):
                    self._forged(receipt, key).write(vals)
                self.assertEqual(receipt.state, "draft")
                self.assertFalse(receipt.external_receipt_id)

    def test_forged_keys_cannot_edit_a_closed_sheet_ledger(self):
        _sheet, _voucher, _allocation, receipt, value = self._ledger("closed")
        self.assertEqual(receipt.state, "closed")
        with self.assertRaises(UserError):
            self._forged(value, "collection_receipt_issuing").write({"amount": 50.0})
        with self.assertRaises(UserError):
            self._forged(receipt, "collection_receipt_audited_state").write(
                {"document_kind": "quotation"}
            )
        self.assertEqual(value.amount, 100.0)
        self.assertEqual(receipt.document_kind, "invoice")

    def test_forged_parent_unlink_cannot_delete_frozen_ledger_rows(self):
        _sheet, _voucher, allocation, receipt, value = self._ledger("closed")
        for record in (allocation.line_ids, value, receipt):
            with self.subTest(model=record._name):
                with self.assertRaises(UserError):
                    self._forged(record, "collection_allocation_parent_unlink").unlink()
                self.assertTrue(record.exists())

    def test_forged_keys_cannot_write_request_or_replaced_cash(self):
        """Each refusal MUST come from the model's own scope guard.

        A bare ``UserError`` would also accept an ACL refusal (``AccessError``
        is one) or an unrelated validation, and so pass with the guard gone.
        """
        _sheet, voucher, allocation, _receipt, _value = self._ledger("open")
        cases = (
            (
                allocation,
                "collection_allocation_request",
                "Allocation request fields can only be written by the agent flow.",
                {"request_id": "scope-forged-request"},
            ),
            (
                voucher,
                "collection_cash_replacement",
                "Replaced cash can only be changed by the cash replacement flow.",
                {"replaced_amount": 10.0},
            ),
        )
        for record, key, message, vals in cases:
            with self.subTest(model=record._name):
                with self.assertRaises(UserError) as error:
                    self._forged(record, key).write(vals)
                self.assertNotIsInstance(error.exception, AccessError)
                self.assertEqual(str(error.exception), message)
        self.assertFalse(allocation.request_id)
        self.assertFalse(voucher.replaced_amount)

    def test_forged_commission_mint_cannot_skip_the_new_work_gate(self):
        sheet = self._sheet()
        self.env.company.write({"enabled_seller_ids": [Command.clear()]})
        Voucher = self._forged(
            self.env["collection.voucher"], "collection_seller_commission_mint"
        )
        with self.assertRaises(UserError) as error:
            Voucher.create(
                {
                    "document_type": "seller_commission",
                    "seller_id": self.seller.id,
                    "sheet_id": sheet.id,
                    "amount": 10.0,
                    "document_id": "sc-scope-forged",
                }
            )
        self.assertIn("not enabled", str(error.exception).lower())
        self.assertFalse(sheet.voucher_ids)

    def test_forged_sheet_unlinking_cannot_move_vouchers_off_a_closed_sheet(self):
        sheet = self._sheet()
        partner = dummy_customer_partner(self.env, customer="SCOPE-LOOSE")
        loose = self._voucher(sheet, partner)
        advance_sheet_to(sheet, "closed")
        with self.assertRaises(UserError):
            self._forged(loose, "collection_sheet_unlinking").write({"sheet_id": False})
        self.assertEqual(loose.sheet_id, sheet)
        with self.assertRaises(UserError):
            self._forged(sheet, "collection_sheet_unlinking").write(
                {"voucher_ids": [Command.unlink(loose.id)]}
            )
        self.assertIn(loose, sheet.voucher_ids)
