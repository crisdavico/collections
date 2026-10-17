# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import inspect
from datetime import date

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import TransactionCase

from odoo.addons.collection.models.collection_common import privileged

from .test_collection_payment import (
    dummy_customer_partner,
    ensure_enabled_seller,
    second_active_currency,
)


class TestCollectionCashReplacement(TransactionCase):
    """Exact-cent cash replacement primitives and replaced-cash counters."""

    def _seller(self):
        return ensure_enabled_seller(self.env)

    def _partner(self, label="REPL-CUST"):
        return dummy_customer_partner(self.env, customer=label)

    def _create_sheet(self):
        seller = self._seller()
        return self.env["collection.sheet"].create({"seller_id": seller.id})

    def _enable_seller_deposit_type(self):
        catalog = self.env.ref("collection.document_type_seller_deposit")
        self.env.company.write(
            {"allowed_document_type_ids": [Command.link(catalog.id)]}
        )
        return catalog

    def _funded_invoice_receipt(
        self, cash_amount=100.0, applied=70.0, deposit_amount=None
    ):
        partner = self._partner()
        sheet = self._create_sheet()
        cash = self.env["collection.voucher"].create(
            {
                "partner_id": partner.id,
                "document_type": "cash",
                "seller_id": sheet.seller_id.id,
                "sheet_id": sheet.id,
                "amount": cash_amount,
            }
        )
        allocation = self.env["collection.allocation"].create(
            {
                "sheet_id": sheet.id,
                "partner_id": partner.id,
                "voucher_ids": [Command.set(cash.ids)],
                "line_ids": [
                    Command.create(
                        {
                            "external_invoice_id": "INV-REPL",
                            "invoice_number": "R-1",
                            "issue_date": date(2026, 1, 1),
                            "due_date": date(2026, 1, 31),
                            # The document owes at least what is applied:
                            # a line cannot apply above its balance.
                            "invoice_amount": max(cash_amount, applied),
                            "invoice_balance": max(cash_amount, applied),
                            "invoice_state": "open",
                            "amount_applied": applied,
                            "document_kind": "invoice",
                        }
                    )
                ],
            }
        )
        receipt = self.env["collection.receipt"].create(
            {
                "allocation_id": allocation.id,
                "document_kind": "invoice",
            }
        )
        cash_value = self.env["collection.receipt.value"].create(
            {
                "receipt_id": receipt.id,
                "voucher_id": cash.id,
                "amount": cash_amount,
            }
        )
        self._enable_seller_deposit_type()
        if deposit_amount is None:
            deposit_amount = cash_amount
        deposit = self.env["collection.voucher"].create(
            {
                "document_type": "seller_deposit",
                "seller_id": sheet.seller_id.id,
                "sheet_id": sheet.id,
                "amount": deposit_amount,
                "voucher_number": "SD-REPL",
                "voucher_date": date(2026, 9, 8),
            }
        )
        return receipt, cash, deposit, cash_value

    def _validate_seller(self, *records):
        vouchers = records[0]
        for extra in records[1:]:
            vouchers |= extra
        drafts = vouchers.filtered(lambda voucher: voucher.state == "draft")
        if drafts:
            drafts.action_validate_seller()
        return vouchers

    def _submit(self, sheet, *vouchers):
        self._validate_seller(*vouchers)
        sheet.action_seller_close()
        return sheet

    def _validate_collections(self, vouchers):
        with privileged("collection_audited_state"):
            return vouchers.write({"state": "validated_collections"})

    def _cash_receipt(
        self,
        sheet,
        partner,
        amount,
        document_kind,
        due_date,
        invoice_number,
    ):
        cash = self.env["collection.voucher"].create(
            {
                "partner_id": partner.id,
                "document_type": "cash",
                "seller_id": sheet.seller_id.id,
                "sheet_id": sheet.id,
                "amount": amount,
            }
        )
        allocation = self.env["collection.allocation"].create(
            {
                "sheet_id": sheet.id,
                "partner_id": partner.id,
                "voucher_ids": [Command.set(cash.ids)],
                "line_ids": [
                    Command.create(
                        {
                            "external_invoice_id": invoice_number,
                            "invoice_number": invoice_number,
                            "issue_date": date(2026, 1, 1),
                            "due_date": due_date,
                            "invoice_amount": amount,
                            "invoice_balance": amount,
                            "invoice_state": "open",
                            "amount_applied": amount,
                            "document_kind": document_kind,
                        }
                    )
                ],
            }
        )
        receipt = self.env["collection.receipt"].create(
            {
                "allocation_id": allocation.id,
                "document_kind": document_kind,
            }
        )
        value = self.env["collection.receipt.value"].create(
            {
                "receipt_id": receipt.id,
                "voucher_id": cash.id,
                "amount": amount,
            }
        )
        return receipt, cash, value

    def _create_deposit(self, sheet, amount, number="SD-ORD"):
        self._enable_seller_deposit_type()
        return self.env["collection.voucher"].create(
            {
                "document_type": "seller_deposit",
                "seller_id": sheet.seller_id.id,
                "sheet_id": sheet.id,
                "amount": amount,
                "voucher_number": number,
                "voucher_date": date(2026, 9, 8),
            }
        )

    def _enable_seller_commission_type(self):
        catalog = self.env.ref("collection.document_type_seller_commission")
        self.env.company.write(
            {"allowed_document_type_ids": [Command.link(catalog.id)]}
        )
        return catalog

    def _create_commission(self, sheet, amount):
        self._enable_seller_commission_type()
        return self.env["collection.voucher"].create(
            {
                "document_type": "seller_commission",
                "seller_id": sheet.seller_id.id,
                "sheet_id": sheet.id,
                "amount": amount,
            }
        )

    def _funded_cash_invoice_receipt(self, cash_amount=100.0, applied=70.0):
        partner = self._partner()
        sheet = self._create_sheet()
        cash = self.env["collection.voucher"].create(
            {
                "partner_id": partner.id,
                "document_type": "cash",
                "seller_id": sheet.seller_id.id,
                "sheet_id": sheet.id,
                "amount": cash_amount,
            }
        )
        allocation = self.env["collection.allocation"].create(
            {
                "sheet_id": sheet.id,
                "partner_id": partner.id,
                "voucher_ids": [Command.set(cash.ids)],
                "line_ids": [
                    Command.create(
                        {
                            "external_invoice_id": "INV-COMM",
                            "invoice_number": "C-1",
                            "issue_date": date(2026, 1, 1),
                            "due_date": date(2026, 1, 31),
                            # The document owes at least what is applied:
                            # a line cannot apply above its balance.
                            "invoice_amount": max(cash_amount, applied),
                            "invoice_balance": max(cash_amount, applied),
                            "invoice_state": "open",
                            "amount_applied": applied,
                            "document_kind": "invoice",
                        }
                    )
                ],
            }
        )
        receipt = self.env["collection.receipt"].create(
            {
                "allocation_id": allocation.id,
                "document_kind": "invoice",
            }
        )
        cash_value = self.env["collection.receipt.value"].create(
            {
                "receipt_id": receipt.id,
                "voucher_id": cash.id,
                "amount": cash_amount,
            }
        )
        return receipt, cash, cash_value

    def _mark_issued(self, receipt, external_id):
        with privileged("collection_receipt_issuing"):
            receipt.write(
                {
                    "state": "issued",
                    "external_receipt_id": external_id,
                }
            )
        return receipt

    def _stamp_create_date(self, voucher, stamped):
        self.env.cr.execute(
            "UPDATE collection_voucher SET create_date = %s WHERE id = %s",
            [stamped, voucher.id],
        )
        voucher.invalidate_recordset(["create_date"])

    def _held(self, voucher, receipt=None):
        values = voucher.receipt_value_ids
        if receipt is not None:
            values = values.filtered(lambda value: value.receipt_id == receipt)
        return sum(values.mapped("amount"))

    def _cash_replace(self, receipt, cash, deposit, amount):
        return self.env["collection.receipt.value"]._cash_replace(
            receipt, cash, deposit, amount
        )

    def test_zero_slice_skipped(self):
        """A slice that rounds to 0.00 MUST skip without raising or persisting."""
        receipt, cash, deposit, cash_value = self._funded_invoice_receipt()
        before_values = receipt.total_values
        result = self._cash_replace(receipt, cash, deposit, 0.0)
        self.assertFalse(result)
        self.assertAlmostEqual(cash.replaced_amount, 0.0, places=2)
        self.assertAlmostEqual(cash_value.amount, 100.0, places=2)
        self.assertAlmostEqual(receipt.total_values, before_values, places=2)
        tiny = self._cash_replace(receipt, cash, deposit, 0.001)
        self.assertFalse(tiny)
        self.assertAlmostEqual(cash.replaced_amount, 0.0, places=2)
        self.assertAlmostEqual(cash_value.amount, 100.0, places=2)

    def test_currency_mismatch_refused(self):
        """Cash, deposit, and receipt currencies MUST agree or nothing persists."""
        receipt, cash, deposit, cash_value = self._funded_invoice_receipt()
        other = second_active_currency(self.env, cash.currency_id)
        self.assertTrue(other, "need a second currency for mismatch")
        cash.write({"currency_id": other.id})
        with self.assertRaises(UserError):
            self._cash_replace(receipt, cash, deposit, 40.0)
        self.assertAlmostEqual(cash.replaced_amount, 0.0)
        self.assertAlmostEqual(cash_value.amount, 100.0, places=2)
        self.assertFalse(
            receipt.value_ids.filtered(lambda value: value.voucher_id == deposit)
        )

    def test_same_receipt_totals_unchanged(self):
        """Replacing 40 of cash 100 with applied 70 MUST keep totals 100 / 70."""
        receipt, cash, deposit, cash_value = self._funded_invoice_receipt()
        self.assertAlmostEqual(receipt.total_values, 100.0, places=2)
        self.assertAlmostEqual(receipt.total_applied, 70.0, places=2)
        moved = self._cash_replace(receipt, cash, deposit, 40.0)
        self.assertAlmostEqual(moved, 40.0, places=2)
        self.assertAlmostEqual(cash.replaced_amount, 40.0, places=2)
        self.assertAlmostEqual(deposit.replacing_amount, 40.0, places=2)
        self.assertAlmostEqual(receipt.total_values, 100.0, places=2)
        self.assertAlmostEqual(receipt.total_applied, 70.0, places=2)
        self.assertAlmostEqual(cash_value.amount, 60.0, places=2)
        deposit_value = receipt.value_ids.filtered(
            lambda value: value.voucher_id == deposit
        )
        self.assertEqual(len(deposit_value), 1)
        self.assertAlmostEqual(deposit_value.amount, 40.0, places=2)

    def test_full_slice_unlinks_cash_value(self):
        """A slice equal to the cash value MUST unlink it and grow the deposit."""
        receipt, cash, deposit, cash_value = self._funded_invoice_receipt(
            cash_amount=100.0, applied=70.0
        )
        cash_value_id = cash_value.id
        moved = self._cash_replace(receipt, cash, deposit, 100.0)
        self.assertAlmostEqual(moved, 100.0, places=2)
        self.assertFalse(
            self.env["collection.receipt.value"].browse(cash_value_id).exists()
        )
        self.assertAlmostEqual(receipt.total_values, 100.0, places=2)
        self.assertAlmostEqual(receipt.total_applied, 70.0, places=2)
        deposit_value = receipt.value_ids.filtered(
            lambda value: value.voucher_id == deposit
        )
        self.assertAlmostEqual(deposit_value.amount, 100.0, places=2)

    def test_sub_cent_remainder_skipped(self):
        """Shrink MUST skip when the remainder would be under one cent."""
        receipt, cash, deposit, cash_value = self._funded_invoice_receipt()
        result = self._cash_replace(receipt, cash, deposit, 150.0)
        self.assertFalse(result)
        self.assertAlmostEqual(cash.replaced_amount, 0.0, places=2)
        self.assertAlmostEqual(cash_value.amount, 100.0, places=2)
        self.assertAlmostEqual(receipt.total_values, 100.0, places=2)

    def test_replaced_amount_books_the_replace(self):
        """A replace MUST book the slice on the cash and the replacing voucher."""
        receipt, cash, deposit, _cash_value = self._funded_invoice_receipt()
        self.assertIn("replaced_amount", cash._fields)
        self.assertAlmostEqual(cash.replaced_amount, 0.0, places=2)
        self._cash_replace(receipt, cash, deposit, 40.0)
        self.assertAlmostEqual(cash.replaced_amount, 40.0, places=2)
        self.assertAlmostEqual(deposit.replaced_amount, 0.0, places=2)
        self.assertAlmostEqual(deposit.replacing_amount, 40.0, places=2)
        self.assertAlmostEqual(cash.replacing_amount, 0.0, places=2)

    def test_replaced_amount_subtracts_reverse(self):
        """A reverse MUST reduce replaced_amount on both vouchers."""
        receipt, cash, deposit, _cash_value = self._funded_invoice_receipt()
        self._cash_replace(receipt, cash, deposit, 40.0)
        moved = self.env["collection.receipt.value"]._cash_reverse(
            receipt, cash, deposit, 10.0
        )
        self.assertAlmostEqual(moved, 10.0, places=2)
        self.assertAlmostEqual(cash.replaced_amount, 30.0, places=2)
        self.assertAlmostEqual(deposit.replacing_amount, 30.0, places=2)
        self.assertAlmostEqual(receipt.total_values, 100.0, places=2)
        self.assertAlmostEqual(receipt.total_applied, 70.0, places=2)

    def test_receipt_get_or_create_reuses_then_creates(self):
        """Allocation _receipt_get_or_create MUST reuse then create per kind."""
        receipt, _cash, _deposit, _value = self._funded_invoice_receipt()
        allocation = receipt.allocation_id
        self.assertEqual(allocation._receipt_get_or_create("invoice"), receipt)
        quotation = allocation._receipt_get_or_create("quotation")
        self.assertTrue(quotation.id)
        self.assertEqual(quotation.document_kind, "quotation")
        self.assertEqual(quotation.allocation_id, allocation)
        self.assertEqual(allocation._receipt_get_or_create("quotation"), quotation)

    def test_cancel_does_not_call_cash_reverse(self):
        """Reverse API MUST exist; Cancel MUST NOT call it."""
        self.assertTrue(callable(self.env["collection.receipt.value"]._cash_reverse))
        source = inspect.getsource(type(self.env["collection.sheet"]).action_cancel)
        self.assertNotIn("_cash_reverse", source)
        self.assertNotIn("_cash_replace", source)

    def test_deposit_validation_replaces_cash(self):
        """Writing seller_deposit to validated_collections MUST replace cash."""
        receipt, cash, deposit, cash_value = self._funded_invoice_receipt(
            cash_amount=100.0, applied=70.0, deposit_amount=40.0
        )
        line = receipt.allocation_id.line_ids
        self._submit(receipt.sheet_id, cash, deposit)
        self.assertEqual(receipt.sheet_id.state, "submitted")
        self.assertEqual(deposit.state, "validated_seller")
        self._validate_collections(deposit)
        self.assertAlmostEqual(cash.replaced_amount, 40.0, places=2)
        self.assertAlmostEqual(deposit.replacing_amount, 40.0, places=2)
        self.assertAlmostEqual(self._held(deposit, receipt), 40.0, places=2)
        self.assertAlmostEqual(receipt.total_values, 100.0, places=2)
        self.assertAlmostEqual(receipt.total_applied, 70.0, places=2)
        self.assertAlmostEqual(line.amount_applied, 70.0, places=2)
        self.assertAlmostEqual(cash_value.amount, 60.0, places=2)

    def test_review_off_companies_still_replace(self):
        """Document Review OFF MUST still replace on validated_collections write."""
        self.env.company.write({"document_review_enabled": False})
        self.assertFalse(self.env.company.document_review_enabled)
        receipt, cash, deposit, _cash_value = self._funded_invoice_receipt(
            cash_amount=100.0, applied=70.0, deposit_amount=40.0
        )
        self._submit(receipt.sheet_id, cash, deposit)
        self._validate_collections(deposit)
        self.assertAlmostEqual(cash.replaced_amount, 40.0, places=2)
        self.assertAlmostEqual(receipt.total_applied, 70.0, places=2)

    def test_non_transition_write_does_not_re_replace(self):
        """A later non-transition write MUST NOT create another replacement."""
        receipt, cash, deposit, _cash_value = self._funded_invoice_receipt(
            cash_amount=100.0, applied=70.0, deposit_amount=40.0
        )
        self._submit(receipt.sheet_id, cash, deposit)
        self._validate_collections(deposit)
        self.assertAlmostEqual(cash.replaced_amount, 40.0, places=2)
        # Money fields of an approved deposit are locked, so the later write
        # touches a display field only.
        deposit.write({"attachment_rotation": 90})
        self._validate_collections(deposit)
        self.assertAlmostEqual(cash.replaced_amount, 40.0, places=2)
        self.assertAlmostEqual(deposit.replacing_amount, 40.0, places=2)
        self.assertEqual(deposit.attachment_rotation, 90)

    def test_no_allocations_is_a_no_op(self):
        """A deposit with zero allocations MUST persist replacing nothing."""
        sheet = self._create_sheet()
        self._enable_seller_deposit_type()
        deposit = self.env["collection.voucher"].create(
            {
                "document_type": "seller_deposit",
                "seller_id": sheet.seller_id.id,
                "sheet_id": sheet.id,
                "amount": 80.0,
                "voucher_number": "SD-NONE",
                "voucher_date": date(2026, 9, 8),
            }
        )
        self._submit(sheet, deposit)
        self._validate_collections(deposit)
        self.assertTrue(deposit.exists())
        self.assertEqual(deposit.state, "validated_collections")
        self.assertFalse(sheet.allocation_ids)
        self.assertAlmostEqual(deposit.replacing_amount, 0.0, places=2)

    def test_cancel_then_reinstate_does_not_reverse(self):
        """Cancel then Reinstate MUST keep the replaced cash and MUST NOT reverse."""
        receipt, cash, deposit, _cash_value = self._funded_invoice_receipt(
            cash_amount=100.0, applied=70.0, deposit_amount=40.0
        )
        sheet = receipt.sheet_id
        self._submit(sheet, cash, deposit)
        self._validate_collections(deposit)
        self.assertAlmostEqual(cash.replaced_amount, 40.0, places=2)
        sheet.action_cancel()
        sheet.action_reinstate()
        self.assertAlmostEqual(cash.replaced_amount, 40.0, places=2)
        self.assertAlmostEqual(deposit.replacing_amount, 40.0, places=2)
        self.assertAlmostEqual(self._held(deposit), 40.0, places=2)

    def test_quotation_before_invoice(self):
        """A deposit smaller than combined cash MUST replace quotation cash first."""
        sheet = self._create_sheet()
        partner = self._partner("Q-THEN-I")
        invoice, cash_invoice, _ivalue = self._cash_receipt(
            sheet,
            partner,
            60.0,
            "invoice",
            date(2026, 1, 31),
            "INV-AFTER",
        )
        quotation, cash_quotation, qvalue = self._cash_receipt(
            sheet,
            self._partner("Q-THEN-I-Q"),
            40.0,
            "quotation",
            date(2026, 6, 30),
            "PRE-FIRST",
        )
        self.assertLess(invoice.id, quotation.id)
        deposit = self._create_deposit(sheet, 50.0)
        self._submit(sheet, cash_invoice, cash_quotation, deposit)
        self._validate_collections(deposit)
        self.assertFalse(qvalue.exists())
        self.assertAlmostEqual(cash_quotation.replaced_amount, 40.0, places=2)
        self.assertAlmostEqual(cash_invoice.replaced_amount, 10.0, places=2)
        invoice_cash = invoice.value_ids.filtered(
            lambda value: value.voucher_id == cash_invoice
        )
        self.assertAlmostEqual(invoice_cash.amount, 50.0, places=2)
        self.assertAlmostEqual(invoice.total_applied, 60.0, places=2)
        self.assertAlmostEqual(quotation.total_applied, 40.0, places=2)
        self.assertAlmostEqual(invoice.total_values, 60.0, places=2)
        self.assertAlmostEqual(quotation.total_values, 40.0, places=2)

    def test_within_kind_uses_proposal_fifo_key(self):
        """Within a kind, earliest due_date then invoice_number goes first."""
        sheet = self._create_sheet()
        later, cash_later, lvalue = self._cash_receipt(
            sheet,
            self._partner("FIFO-LATE"),
            40.0,
            "invoice",
            date(2026, 3, 1),
            "Z-LATE",
        )
        earlier, cash_earlier, evalue = self._cash_receipt(
            sheet,
            self._partner("FIFO-EARLY"),
            60.0,
            "invoice",
            date(2026, 1, 1),
            "A-EARLY",
        )
        self.assertLess(later.id, earlier.id)
        deposit = self._create_deposit(sheet, 50.0, number="SD-FIFO")
        self._submit(sheet, cash_later, cash_earlier, deposit)
        self._validate_collections(deposit)
        self.assertAlmostEqual(cash_earlier.replaced_amount, 50.0, places=2)
        self.assertAlmostEqual(cash_later.replaced_amount, 0.0, places=2)
        self.assertTrue(lvalue.exists())
        self.assertAlmostEqual(lvalue.amount, 40.0, places=2)
        self.assertTrue(evalue.exists())
        self.assertAlmostEqual(evalue.amount, 10.0, places=2)
        self.assertAlmostEqual(later.total_applied, 40.0, places=2)
        self.assertAlmostEqual(earlier.total_applied, 60.0, places=2)

    def test_within_bucket_oldest_cash_create_date(self):
        """Within one receipt, oldest-uploaded cash MUST be consumed first."""
        receipt, cash_new, deposit, new_value = self._funded_invoice_receipt(
            cash_amount=40.0, applied=70.0, deposit_amount=30.0
        )
        partner = cash_new.partner_id
        sheet = receipt.sheet_id
        cash_old = self.env["collection.voucher"].create(
            {
                "partner_id": partner.id,
                "document_type": "cash",
                "seller_id": sheet.seller_id.id,
                "sheet_id": sheet.id,
                "amount": 40.0,
            }
        )
        old_value = self.env["collection.receipt.value"].create(
            {
                "receipt_id": receipt.id,
                "voucher_id": cash_old.id,
                "amount": 40.0,
            }
        )
        receipt.allocation_id.write({"voucher_ids": [Command.link(cash_old.id)]})
        self.assertLess(cash_new.id, cash_old.id)
        self._stamp_create_date(cash_new, "2026-09-08 12:00:00")
        self._stamp_create_date(cash_old, "2026-01-01 08:00:00")
        self._submit(sheet, cash_new, cash_old, deposit)
        self._validate_collections(deposit)
        self.assertAlmostEqual(cash_old.replaced_amount, 30.0, places=2)
        self.assertAlmostEqual(cash_new.replaced_amount, 0.0, places=2)
        self.assertTrue(new_value.exists())
        self.assertAlmostEqual(new_value.amount, 40.0, places=2)
        self.assertAlmostEqual(old_value.amount, 10.0, places=2)
        self.assertAlmostEqual(receipt.total_applied, 70.0, places=2)
        self.assertAlmostEqual(receipt.total_values, 80.0, places=2)

    def test_issued_receipt_skipped_not_aborted(self):
        """Issued cash MUST stay put while draft cash is replaced, without raising."""
        sheet = self._create_sheet()
        issued, cash_issued, issued_value = self._cash_receipt(
            sheet,
            self._partner("ISSUED-CASH"),
            50.0,
            "invoice",
            date(2026, 1, 1),
            "ISS-EARLY",
        )
        draft, cash_draft, draft_value = self._cash_receipt(
            sheet,
            self._partner("DRAFT-CASH"),
            40.0,
            "invoice",
            date(2026, 6, 1),
            "DFT-LATE",
        )
        self._mark_issued(issued, "ERP-SKIP-ISSUED")
        self.assertEqual(issued.state, "issued")
        self.assertEqual(draft.state, "draft")
        deposit = self._create_deposit(sheet, 40.0, number="SD-SKIP-ISS")
        self._submit(sheet, cash_issued, cash_draft, deposit)
        self._validate_collections(deposit)
        self.assertEqual(deposit.state, "validated_collections")
        self.assertAlmostEqual(self._held(deposit, draft), 40.0, places=2)
        self.assertEqual(issued.state, "issued")
        self.assertTrue(issued_value.exists())
        self.assertAlmostEqual(issued_value.amount, 50.0, places=2)
        self.assertFalse(
            issued.value_ids.filtered(lambda value: value.voucher_id == deposit)
        )
        self.assertAlmostEqual(cash_issued.replaced_amount, 0.0, places=2)
        self.assertAlmostEqual(cash_draft.replaced_amount, 40.0, places=2)
        self.assertFalse(draft_value.exists())
        self.assertAlmostEqual(issued.total_values, 50.0, places=2)
        self.assertAlmostEqual(draft.total_values, 40.0, places=2)

    def test_issued_only_cash_is_silent_no_op(self):
        """A sheet whose only cash sits on issued receipts MUST not raise or replace."""
        sheet = self._create_sheet()
        issued, cash_issued, issued_value = self._cash_receipt(
            sheet,
            self._partner("ISSUED-ONLY"),
            50.0,
            "invoice",
            date(2026, 1, 15),
            "ISS-ONLY",
        )
        self._mark_issued(issued, "ERP-SKIP-ONLY")
        deposit = self._create_deposit(sheet, 50.0, number="SD-ISS-ONLY")
        self._submit(sheet, cash_issued, deposit)
        self._validate_collections(deposit)
        self.assertEqual(deposit.state, "validated_collections")
        self.assertAlmostEqual(deposit.replacing_amount, 0.0, places=2)
        self.assertEqual(issued.state, "issued")
        self.assertTrue(issued_value.exists())
        self.assertAlmostEqual(issued_value.amount, 50.0, places=2)
        self.assertAlmostEqual(cash_issued.replaced_amount, 0.0, places=2)

    def test_commission_replaces_cash_preserving_totals(self):
        """Promoting seller_commission MUST replace cash FIFO and keep totals."""
        receipt, cash, cash_value = self._funded_cash_invoice_receipt(
            cash_amount=100.0, applied=70.0
        )
        line = receipt.allocation_id.line_ids
        commission = self._create_commission(receipt.sheet_id, 30.0)
        self._submit(receipt.sheet_id, cash, commission)
        self._validate_collections(commission)
        self.assertAlmostEqual(receipt.total_values, 100.0, places=2)
        self.assertAlmostEqual(receipt.total_applied, 70.0, places=2)
        self.assertAlmostEqual(line.amount_applied, 70.0, places=2)
        self.assertAlmostEqual(cash_value.amount, 70.0, places=2)
        self.assertAlmostEqual(cash.replaced_amount, 30.0, places=2)
        self.assertAlmostEqual(commission.replacing_amount, 30.0, places=2)
        self.assertAlmostEqual(self._held(commission, receipt), 30.0, places=2)

    def test_deposit_and_commission_share_one_cash_pool(self):
        """A deposit and a commission MUST consume one cash pool, never twice."""
        receipt, cash, deposit, cash_value = self._funded_invoice_receipt(
            cash_amount=100.0, applied=70.0, deposit_amount=70.0
        )
        commission = self._create_commission(receipt.sheet_id, 30.0)
        self._submit(receipt.sheet_id, cash, deposit, commission)
        self._validate_collections(deposit | commission)
        self.assertTrue(deposit.replacing_amount)
        self.assertTrue(commission.replacing_amount)
        replaced = deposit.replacing_amount + commission.replacing_amount
        self.assertAlmostEqual(replaced, 100.0, places=2)
        self.assertAlmostEqual(cash.replaced_amount, 100.0, places=2)
        self.assertFalse(cash_value.exists())

    def test_over_declared_commission_raises(self):
        """A commission larger than replaceable cash MUST raise UserError."""
        receipt, cash, _cash_value = self._funded_cash_invoice_receipt(
            cash_amount=50.0, applied=50.0
        )
        commission = self._create_commission(receipt.sheet_id, 80.0)
        self._submit(receipt.sheet_id, cash, commission)
        with self.assertRaises(UserError) as ctx:
            self._validate_collections(commission)
        self.assertIn("commission", str(ctx.exception).lower())

    def test_excess_deposit_still_silently_drops(self):
        """An excess seller_deposit MUST still replace available cash and not raise."""
        receipt, cash, deposit, cash_value = self._funded_invoice_receipt(
            cash_amount=50.0, applied=50.0, deposit_amount=80.0
        )
        self._submit(receipt.sheet_id, cash, deposit)
        self._validate_collections(deposit)
        self.assertEqual(deposit.state, "validated_collections")
        self.assertAlmostEqual(deposit.replacing_amount, 50.0, places=2)
        self.assertFalse(cash_value.exists())
        self.assertAlmostEqual(cash.replaced_amount, 50.0, places=2)

    def test_reverse_gives_each_receipt_its_cash_back(self):
        """Undoing a swap MUST put back each receipt's cash, without a ledger."""
        sheet = self._create_sheet()
        invoice, cash_invoice, _invoice_value = self._cash_receipt(
            sheet,
            self._partner("REV-INVOICE"),
            60.0,
            "invoice",
            date(2026, 1, 31),
            "REV-INV",
        )
        quotation, cash_quotation, _quotation_value = self._cash_receipt(
            sheet,
            self._partner("REV-QUOTATION"),
            40.0,
            "quotation",
            date(2026, 2, 28),
            "REV-QUO",
        )
        deposit = self._create_deposit(sheet, 80.0, number="SD-REV-BOTH")
        self._submit(sheet, cash_invoice, cash_quotation, deposit)
        self._validate_collections(deposit)
        # Quotation cash first, then invoice cash.
        self.assertAlmostEqual(self._held(cash_quotation), 0.0, places=2)
        self.assertAlmostEqual(self._held(cash_invoice), 20.0, places=2)
        self.assertAlmostEqual(self._held(deposit, quotation), 40.0, places=2)
        self.assertAlmostEqual(self._held(deposit, invoice), 40.0, places=2)
        deposit._reverse_cash_replacement()
        self.assertAlmostEqual(self._held(cash_invoice, invoice), 60.0, places=2)
        self.assertAlmostEqual(self._held(cash_quotation, quotation), 40.0, places=2)
        self.assertFalse(deposit.receipt_value_ids)
        self.assertAlmostEqual(cash_invoice.replaced_amount, 0.0, places=2)
        self.assertAlmostEqual(cash_quotation.replaced_amount, 0.0, places=2)
        self.assertAlmostEqual(deposit.replacing_amount, 0.0, places=2)
        self.assertAlmostEqual(invoice.total_values, 60.0, places=2)
        self.assertAlmostEqual(quotation.total_values, 40.0, places=2)

    def test_validated_commission_cannot_unlink(self):
        """A validated seller_commission MUST refuse unlink (draft-only delete)."""
        receipt, cash, cash_value = self._funded_cash_invoice_receipt(
            cash_amount=100.0, applied=70.0
        )
        commission = self._create_commission(receipt.sheet_id, 30.0)
        self._submit(receipt.sheet_id, cash, commission)
        self._validate_collections(commission)
        with self.assertRaises(UserError):
            commission.unlink()
        self.assertTrue(commission.exists())
        self.assertTrue(cash_value.exists())

    def test_replaced_cash_counters_refuse_direct_writes(self):
        """Only the replacement flow MUST book replaced cash."""
        _receipt, cash, deposit, _cash_value = self._funded_invoice_receipt()
        with self.assertRaises(UserError):
            cash.write({"replaced_amount": 10.0})
        with self.assertRaises(UserError):
            deposit.write({"replacing_amount": 10.0})
        self.assertAlmostEqual(cash.replaced_amount, 0.0)
        self.assertAlmostEqual(deposit.replacing_amount, 0.0)

    def test_cash_replacer_helpers_use_replacement_types(self):
        """Enter/run helpers MUST be the type-set names, not deposit-only."""
        voucher_cls = type(self.env["collection.voucher"])
        self.assertTrue(
            hasattr(voucher_cls, "_cash_replacers_entering_validated_collections")
        )
        self.assertTrue(hasattr(voucher_cls, "_run_cash_replacement"))
        self.assertFalse(
            hasattr(voucher_cls, "_seller_deposits_entering_validated_collections")
        )
        self.assertFalse(hasattr(voucher_cls, "_run_seller_deposit_cash_replacement"))
        write_source = inspect.getsource(voucher_cls.write)
        self.assertIn("_cash_replacers_entering_validated_collections", write_source)
        self.assertIn("_run_cash_replacement", write_source)
        run_source = inspect.getsource(voucher_cls._run_cash_replacement)
        self.assertIn("CASH_REPLACEMENT_TYPES", run_source)
        enter_source = inspect.getsource(
            voucher_cls._cash_replacers_entering_validated_collections
        )
        self.assertIn("CASH_REPLACEMENT_TYPES", enter_source)
