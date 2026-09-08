# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date
from unittest.mock import patch

from psycopg2 import IntegrityError

from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from .common_connector import confirm_sheet, force_sheet_state
from .test_collection_payment import (
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
)


class TestCollectionSheet(TransactionCase):
    """RED/GREEN: collection.sheet sequence, frozen seller, four-state lifecycle."""

    def _other_internal_seller(self):
        return create_internal_seller(self.env, f"other_{self._testMethodName}")

    def _ensure_enabled_seller(self, seller=None):
        seller = seller or self.env.ref("base.user_admin")
        company = self.env.company
        if seller not in company.enabled_seller_ids:
            company.write({"enabled_seller_ids": [Command.link(seller.id)]})
            if seller not in company.enabled_seller_ids:
                self.env.cr.execute(
                    """
                    INSERT INTO res_company_collection_enabled_seller_rel
                        (company_id, user_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (company.id, seller.id),
                )
                company.invalidate_recordset(["enabled_seller_ids"])
        return seller

    def _seller(self):
        return self._ensure_enabled_seller()

    def _create_sheet(self, **extra):
        seller_id = extra.get("seller_id", self._seller().id)
        self._ensure_enabled_seller(self.env["res.users"].browse(seller_id))
        vals = {"seller_id": seller_id, **extra}
        return self.env["collection.sheet"].create(vals)

    def _create_voucher(self, customer=None, **extra):
        null_seller = extra.get("seller_id") is False
        if null_seller:
            extra = {key: value for key, value in extra.items() if key != "seller_id"}
            if not extra.get("sheet_id"):
                existing_open = self.env["collection.sheet"].search(
                    [
                        ("seller_id", "=", self._seller().id),
                        ("state", "=", "open"),
                    ],
                    limit=1,
                )
                if existing_open:
                    extra["sheet_id"] = existing_open.id
        seller_id = extra.get("seller_id", self._seller().id)
        if seller_id:
            self._ensure_enabled_seller(self.env["res.users"].browse(seller_id))
        partner = dummy_customer_partner(
            self.env, customer=customer, extra=extra, default="CUST-SHEET"
        )
        vals = {
            "partner_id": partner.id,
            "document_type": "unsupported",
            "seller_id": seller_id or self._seller().id,
        }
        vals.update(extra)
        before_sheets = self.env["collection.sheet"].browse(
            self.env["collection.sheet"].search([]).ids
        )
        voucher = self.env["collection.voucher"].create(vals)
        if null_seller:
            leftover_sheet = voucher.sheet_id
            self.env.cr.execute(
                """
                UPDATE collection_voucher
                   SET seller_id = NULL, sheet_id = NULL
                 WHERE id = %s
                """,
                (voucher.id,),
            )
            voucher.invalidate_recordset(["seller_id", "sheet_id"])
            leftover_sheet.invalidate_recordset(["voucher_ids"])
            if (
                leftover_sheet
                and leftover_sheet not in before_sheets
                and not leftover_sheet.voucher_ids
            ):
                leftover_sheet.unlink()
        return voucher

    def _create_balanced_allocation(self, sheet, voucher, invoice_id="INV-SHEET"):
        amount = voucher.amount or 0.0
        return self.env["collection.allocation"].create(
            {
                "sheet_id": sheet.id,
                "partner_id": voucher.partner_id.id,
                "voucher_ids": [Command.set(voucher.ids)],
                "line_ids": [
                    Command.create(
                        {
                            "external_invoice_id": invoice_id,
                            "invoice_number": invoice_id,
                            "invoice_balance": amount,
                            "amount_applied": amount,
                        }
                    )
                ],
            }
        )

    def _force_confirmed_and_closed(self, sheet, allocations):
        allocations.with_context(collection_allocation_audited_state=True).write(
            {"state": "confirmed"}
        )
        force_sheet_state(sheet, "closed")

    def _mark_validated_collections(self, vouchers):
        vouchers.with_context(collection_audited_state=True).write(
            {"state": "validated_collections"}
        )
        return vouchers

    def _second_open_via_audited(self):
        """Leave two open sheets for the same seller (bypasses one-open)."""
        first = self._create_sheet()
        force_sheet_state(first, "closed")
        leftover = self._create_sheet()
        force_sheet_state(first, "open")
        return first, leftover

    def _sheet_count(self):
        return self.env["collection.sheet"].search_count([])

    def _assert_sheet_assign_rejected(self, voucher, sheet):
        with mute_logger("odoo.sql_db"):
            try:
                voucher.write({"sheet_id": sheet.id})
            except (UserError, ValidationError, IntegrityError):
                return
        self.fail("Assigning this voucher to the sheet must be rejected")

    def test_sequence_assigned_on_create(self):
        year = date.today().year
        sheet = self._create_sheet()
        self.assertRegex(
            sheet.name,
            rf"^CS/{year}/\d{{4,}}$",
            "Sheet name must match CS/<year>/<padded number>",
        )
        self.assertEqual(sheet.state, "open")
        state_field = self.env["collection.sheet"]._fields["state"]
        state_keys = {key for key, _label in state_field.selection}
        self.assertEqual(
            state_keys, {"open", "submitted", "proposal", "closed", "cancelled"}
        )
        self.assertFalse(hasattr(type(sheet), "action_reopen"))
        self.assertFalse(hasattr(type(sheet), "action_open"))

    def test_sequence_names_are_unique(self):
        first = self._create_sheet()
        confirm_sheet(first)
        first.action_close()
        second = self._create_sheet()
        self.assertNotEqual(first.name, second.name)
        self.assertRegex(first.name, r"^CS/\d{4}/\d{4,}$")
        self.assertRegex(second.name, r"^CS/\d{4}/\d{4,}$")
        self.assertEqual(first.state, "closed")
        self.assertEqual(second.state, "open")
        self.assertEqual(first.seller_id, second.seller_id)

    def test_action_confirm_empty_members_pass(self):
        """Empty member set MUST pass Confirm and MUST NOT confirm allocations."""
        sheet = self._create_sheet()
        self.assertEqual(sheet.state, "open")
        self.assertFalse(sheet.voucher_ids)
        self.assertFalse(sheet.allocation_ids)
        sheet.action_seller_close()
        self.assertEqual(sheet.state, "submitted")
        sheet.action_confirm()
        self.assertEqual(sheet.state, "proposal")
        self.assertFalse(sheet.allocation_ids)

    def test_confirm_from_open_refused(self):
        """Confirm MUST refuse an open sheet even when every member is validated."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-CONF-OPEN-REFUSE",
            sheet_id=sheet.id,
            amount=25.0,
        )
        self._create_balanced_allocation(
            sheet, voucher, invoice_id="INV-CONF-OPEN-REFUSE"
        )
        self._mark_validated_collections(voucher)
        self.assertEqual(sheet.state, "open")
        self.assertEqual(voucher.state, "validated_collections")
        with self.assertRaises(UserError):
            sheet.action_confirm()
        self.assertEqual(sheet.state, "open")
        self.assertEqual(voucher.state, "validated_collections")

    def test_confirm_from_submitted_reaches_proposal(self):
        """Confirm from submitted MUST reach proposal."""
        sheet = self._create_sheet()
        force_sheet_state(sheet, "submitted")
        self.assertEqual(sheet.state, "submitted")
        self.assertFalse(sheet.voucher_ids)
        confirm_sheet(sheet)
        self.assertEqual(sheet.state, "proposal")
        self.assertFalse(sheet.allocation_ids)

    def test_action_confirm_all_members_validated_collections(self):
        """Confirm MUST set proposal and leave allocations draft."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-CONF-1",
            sheet_id=sheet.id,
            amount=25.0,
        )
        allocation = self._create_balanced_allocation(
            sheet, voucher, invoice_id="INV-CONF-1"
        )
        self._mark_validated_collections(voucher)
        self.assertEqual(voucher.state, "validated_collections")
        self.assertEqual(allocation.state, "draft")
        sheet.action_seller_close()
        sheet.action_confirm()
        self.assertEqual(sheet.state, "proposal")
        self.assertEqual(allocation.state, "draft")
        allocation._check_sheet_state_iff()

    def test_action_confirm_unreviewed_member_blocks(self):
        """Any member not validated_collections MUST UserError and stay submitted."""
        sheet = self._create_sheet()
        reviewed = self._create_voucher(
            customer_identification="CUST-CONF-OK",
            sheet_id=sheet.id,
            amount=10.0,
        )
        unreviewed = self._create_voucher(
            customer_identification="CUST-CONF-BLOCK",
            sheet_id=sheet.id,
            amount=15.0,
        )
        self._mark_validated_collections(reviewed)
        self.assertEqual(unreviewed.state, "draft")
        force_sheet_state(sheet, "submitted")
        with self.assertRaises(UserError) as error:
            sheet.action_confirm()
        self.assertIn("validated", str(error.exception).lower())
        self.assertEqual(sheet.state, "submitted")
        self.assertEqual(reviewed.state, "validated_collections")
        self.assertEqual(unreviewed.state, "draft")

    def test_action_confirm_seller_validated_member_blocks(self):
        """Triangulation: validated_seller (not collections) MUST also block Confirm."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-CONF-SELLER",
            sheet_id=sheet.id,
            amount=12.0,
        )
        voucher.action_validate_seller()
        self.assertEqual(voucher.state, "validated_seller")
        sheet.action_seller_close()
        self.assertEqual(sheet.state, "submitted")
        with self.assertRaises(UserError):
            sheet.action_confirm()
        self.assertEqual(sheet.state, "submitted")
        self.assertEqual(voucher.state, "validated_seller")

    def test_action_seller_close_empty_members_pass(self):
        """Empty member set MUST pass Seller Close to submitted."""
        sheet = self._create_sheet()
        self.assertEqual(sheet.state, "open")
        self.assertFalse(sheet.voucher_ids)
        sheet.action_seller_close()
        self.assertEqual(sheet.state, "submitted")
        self.assertFalse(sheet.allocation_ids)

    def test_action_seller_close_draft_members_name_offenders(self):
        """Draft members MUST UserError listing those vouchers and stay open."""
        sheet = self._create_sheet()
        first = self._create_voucher(
            customer_identification="CUST-SC-DRAFT-A",
            sheet_id=sheet.id,
            amount=10.0,
        )
        second = self._create_voucher(
            customer_identification="CUST-SC-DRAFT-B",
            sheet_id=sheet.id,
            amount=15.0,
        )
        self.assertEqual(first.state, "draft")
        self.assertEqual(second.state, "draft")
        with self.assertRaises(UserError) as error:
            sheet.action_seller_close()
        message = str(error.exception)
        self.assertIn(first.name, message)
        self.assertIn(second.name, message)
        self.assertEqual(sheet.state, "open")

    def test_action_seller_close_validated_collections_member_passes(self):
        """validated_collections members MUST pass; allocations stay draft."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-SC-VC",
            sheet_id=sheet.id,
            amount=25.0,
        )
        allocation = self._create_balanced_allocation(
            sheet, voucher, invoice_id="INV-SC-VC"
        )
        self._mark_validated_collections(voucher)
        before_cash = sheet.cash_on_hand
        before_withheld = sheet.commission_withheld
        sheet.action_seller_close()
        self.assertEqual(sheet.state, "submitted")
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(sheet.cash_on_hand, before_cash)
        self.assertEqual(sheet.commission_withheld, before_withheld)

    def test_action_seller_close_without_amounts(self):
        """Seller Close MUST write submitted without declaration amounts."""
        sheet = self._create_sheet()
        before_cash = sheet.cash_on_hand
        before_withheld = sheet.commission_withheld
        sheet.action_seller_close()
        self.assertEqual(sheet.state, "submitted")
        self.assertEqual(sheet.cash_on_hand, before_cash)
        self.assertEqual(sheet.commission_withheld, before_withheld)

    def test_action_seller_close_ignores_amount_kwargs(self):
        """Kwargs on Seller Close MUST NOT persist cash_on_hand or withheld."""
        sheet = self._create_sheet()
        before_cash = sheet.cash_on_hand
        before_withheld = sheet.commission_withheld
        sheet.action_seller_close(cash_on_hand=40.0, commission_withheld=5.0)
        self.assertEqual(sheet.state, "submitted")
        self.assertEqual(sheet.cash_on_hand, before_cash)
        self.assertEqual(sheet.commission_withheld, before_withheld)
        self.assertNotEqual(sheet.cash_on_hand, 40.0)

    def test_action_seller_close_validated_seller_member_passes(self):
        """Triangulation: validated_seller MUST pass Seller Close (unlike Confirm)."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-SC-VS",
            sheet_id=sheet.id,
            amount=12.0,
        )
        voucher.action_validate_seller()
        self.assertEqual(voucher.state, "validated_seller")
        sheet.action_seller_close()
        self.assertEqual(sheet.state, "submitted")
        self.assertEqual(voucher.state, "validated_seller")

    def test_action_seller_close_refused_from_every_non_open_state(self):
        """Seller Close from submitted, proposal, closed, or cancelled MUST refuse."""
        for state in ("submitted", "proposal", "closed", "cancelled"):
            sheet = self._create_sheet()
            force_sheet_state(sheet, state)
            with self.assertRaises(UserError):
                sheet.action_seller_close()
            self.assertEqual(sheet.state, state)

    def test_action_seller_close_is_recordset_capable(self):
        """Seller Close MUST run on a recordset (no ensure_one)."""
        first = self._create_sheet()
        other = self._other_internal_seller()
        second = self._create_sheet(seller_id=other.id)
        (first | second).action_seller_close()
        self.assertEqual(first.state, "submitted")
        self.assertEqual(second.state, "submitted")

    def test_submitted_sheet_accepts_declare_cash(self):
        """Declare Cash MUST persist amounts and stamp declared_at/by on submitted."""
        sheet = self._create_sheet()
        sheet.action_seller_close()
        sheet.action_declare_cash(cash_on_hand=12.5, commission_withheld=1.25)
        self.assertEqual(sheet.state, "submitted")
        self.assertEqual(sheet.cash_on_hand, 12.5)
        self.assertEqual(sheet.commission_withheld, 1.25)
        self.assertTrue(sheet.cash_declared_at)
        self.assertEqual(sheet.cash_declared_by, self.env.user)

    def test_declare_cash_is_rerunnable(self):
        """A later Declare Cash MUST replace amounts and restamp declared_at/by."""
        sheet = self._create_sheet()
        sheet.action_seller_close()
        sheet.action_declare_cash(cash_on_hand=10.0, commission_withheld=1.0)
        first_at = sheet.cash_declared_at
        sheet.action_declare_cash(cash_on_hand=20.0, commission_withheld=2.0)
        self.assertEqual(sheet.state, "submitted")
        self.assertEqual(sheet.cash_on_hand, 20.0)
        self.assertEqual(sheet.commission_withheld, 2.0)
        self.assertTrue(sheet.cash_declared_at)
        self.assertGreaterEqual(sheet.cash_declared_at, first_at)

    def test_non_submitted_declare_cash_refused(self):
        """Declare Cash from open, proposal, closed, or cancelled MUST refuse."""
        for state in ("open", "proposal", "closed", "cancelled"):
            sheet = self._create_sheet()
            if state != "open":
                force_sheet_state(sheet, state)
            before_cash = sheet.cash_on_hand
            with self.assertRaises(UserError):
                sheet.action_declare_cash(cash_on_hand=99.0, commission_withheld=9.0)
            self.assertEqual(sheet.state, state)
            self.assertEqual(sheet.cash_on_hand, before_cash)
            self.assertFalse(sheet.cash_declared_at)
            force_sheet_state(sheet, "cancelled")

    def test_disabled_seller_may_still_declare_cash(self):
        """A later-disabled seller MUST still Declare Cash on a submitted sheet."""
        sheet = self._create_sheet()
        sheet.action_seller_close()
        self._clear_enabled_sellers()
        sheet.action_declare_cash(cash_on_hand=8.0, commission_withheld=0.5)
        self.assertEqual(sheet.state, "submitted")
        self.assertEqual(sheet.cash_on_hand, 8.0)
        self.assertEqual(sheet.commission_withheld, 0.5)
        self.assertTrue(sheet.cash_declared_at)

    def test_undeclared_cash_blocks_confirm(self):
        """Confirm MUST refuse when collected cash > 0 and cash_declared_at is unset."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-CASH-BLOCK",
            sheet_id=sheet.id,
            amount=40.0,
            document_type="cash",
        )
        self._mark_validated_collections(voucher)
        sheet.action_seller_close()
        self.assertFalse(sheet.cash_declared_at)
        with self.assertRaises(UserError):
            sheet.action_confirm()
        self.assertEqual(sheet.state, "submitted")
        self.assertFalse(
            sheet.allocation_ids.filtered(lambda rec: rec.state != "draft")
        )

    def test_zero_cash_confirm_without_declaration(self):
        """Confirm MUST pass without Declare Cash when collected cash is zero."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-ZERO-CASH",
            sheet_id=sheet.id,
            amount=25.0,
            document_type="bank_transfer",
        )
        self._create_balanced_allocation(sheet, voucher, invoice_id="INV-ZERO-CASH")
        self._mark_validated_collections(voucher)
        sheet.action_seller_close()
        self.assertFalse(sheet.cash_declared_at)
        sheet.action_confirm()
        self.assertEqual(sheet.state, "proposal")

    def test_declared_cash_allows_confirm(self):
        """Confirm MUST reach proposal after Declare Cash when collected cash > 0."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-CASH-OK",
            sheet_id=sheet.id,
            amount=40.0,
            document_type="cash",
        )
        self._create_balanced_allocation(sheet, voucher, invoice_id="INV-CASH-OK")
        self._mark_validated_collections(voucher)
        sheet.action_seller_close()
        sheet.action_declare_cash(cash_on_hand=40.0, commission_withheld=0.0)
        sheet.action_confirm()
        self.assertEqual(sheet.state, "proposal")

    def test_illegal_close_cancel_open_from_open_refused(self):
        """Close, Cancel, or Reinstate from open MUST refuse and leave state open."""
        sheet = self._create_sheet()
        with self.assertRaises(UserError):
            sheet.action_close()
        with self.assertRaises(UserError):
            sheet.action_cancel()
        with self.assertRaises(UserError):
            sheet.action_reinstate()
        self.assertEqual(sheet.state, "open")

    def test_action_close_from_proposal_confirms_then_closes(self):
        """Close MUST succeed only from proposal and confirm every allocation."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-CLOSE-1",
            sheet_id=sheet.id,
            amount=25.0,
        )
        allocation = self._create_balanced_allocation(
            sheet, voucher, invoice_id="INV-CLOSE-1"
        )
        self._mark_validated_collections(voucher)
        confirm_sheet(sheet)
        self.assertEqual(sheet.state, "proposal")
        self.assertEqual(allocation.state, "draft")
        sheet.action_close()
        self.assertEqual(sheet.state, "closed")
        self.assertEqual(allocation.state, "confirmed")
        allocation._check_sheet_state_iff()

    def test_action_close_confirms_every_allocation(self):
        """Triangulation: Close MUST confirm all allocations on the sheet."""
        sheet = self._create_sheet()
        first_voucher = self._create_voucher(
            customer_identification="CUST-CLOSE-A",
            sheet_id=sheet.id,
            amount=10.0,
        )
        second_voucher = self._create_voucher(
            customer_identification="CUST-CLOSE-B",
            sheet_id=sheet.id,
            amount=15.0,
        )
        first = self._create_balanced_allocation(
            sheet, first_voucher, invoice_id="INV-CLOSE-A"
        )
        second = self._create_balanced_allocation(
            sheet, second_voucher, invoice_id="INV-CLOSE-B"
        )
        self._mark_validated_collections(first_voucher | second_voucher)
        confirm_sheet(sheet)
        sheet.action_close()
        self.assertEqual(sheet.state, "closed")
        self.assertEqual(first.state, "confirmed")
        self.assertEqual(second.state, "confirmed")
        (first | second)._check_sheet_state_iff()

    def test_action_close_without_connector_succeeds(self):
        """Close from proposal MUST succeed with no connector and MUST NOT dispatch."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-CLOSE-NOERP",
            sheet_id=sheet.id,
            amount=25.0,
        )
        allocation = self._create_balanced_allocation(
            sheet, voucher, invoice_id="INV-CLOSE-NOERP"
        )
        receipt = self.env["collection.receipt"].create(
            {"allocation_id": allocation.id, "document_kind": "invoice"}
        )
        self.env["collection.receipt.value"].create(
            {
                "receipt_id": receipt.id,
                "voucher_id": voucher.id,
                "amount": 25.0,
            }
        )
        self._mark_validated_collections(voucher)
        confirm_sheet(sheet)
        self.env.company.write({"collection_connector_id": False})
        create_receipt = (
            "odoo.addons.collection.models.collection_connector."
            "CollectionConnector.create_receipt"
        )
        with patch(create_receipt) as mocked:
            mocked.side_effect = AssertionError("create_receipt must not run")
            sheet.action_close()
            mocked.assert_not_called()
        self.assertEqual(sheet.state, "closed")
        self.assertEqual(allocation.state, "confirmed")
        self.assertEqual(receipt.state, "closed")
        self.assertFalse(receipt.external_receipt_id)

    def test_action_close_with_zero_receipts_still_closes(self):
        """Close MUST confirm allocations with zero receipts and MUST NOT dispatch."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-CLOSE-ZERO",
            sheet_id=sheet.id,
            amount=18.0,
        )
        allocation = self._create_balanced_allocation(
            sheet, voucher, invoice_id="INV-CLOSE-ZERO"
        )
        self.assertFalse(allocation.receipt_ids)
        self._mark_validated_collections(voucher)
        confirm_sheet(sheet)
        create_receipt = (
            "odoo.addons.collection.models.collection_connector."
            "CollectionConnector.create_receipt"
        )
        with patch(create_receipt) as mocked:
            mocked.side_effect = AssertionError("create_receipt must not run")
            sheet.action_close()
            mocked.assert_not_called()
        self.assertEqual(sheet.state, "closed")
        self.assertEqual(allocation.state, "confirmed")
        self.assertFalse(allocation.receipt_ids)

    def test_action_close_keeps_voucher_validated_collections(self):
        """Close MUST leave member vouchers in validated_collections."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-CLOSE-VOUCHER",
            sheet_id=sheet.id,
            amount=12.0,
        )
        self._create_balanced_allocation(sheet, voucher, invoice_id="INV-CLOSE-VOUCHER")
        self._mark_validated_collections(voucher)
        confirm_sheet(sheet)
        self.assertEqual(voucher.state, "validated_collections")
        sheet.action_close()
        self.assertEqual(sheet.state, "closed")
        self.assertEqual(voucher.state, "validated_collections")

    def test_action_close_rejected_when_already_closed(self):
        sheet = self._create_sheet()
        confirm_sheet(sheet)
        sheet.action_close()
        with self.assertRaises(UserError):
            sheet.action_close()
        self.assertEqual(sheet.state, "closed")

    def test_action_cancel_from_proposal_drafts_allocations(self):
        """Cancel from proposal MUST set cancelled and leave allocations draft."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-CAN-P",
            sheet_id=sheet.id,
            amount=30.0,
        )
        allocation = self._create_balanced_allocation(
            sheet, voucher, invoice_id="INV-CAN-P"
        )
        self._mark_validated_collections(voucher)
        confirm_sheet(sheet)
        self.assertEqual(allocation.state, "draft")
        sheet.action_cancel()
        self.assertEqual(sheet.state, "cancelled")
        self.assertEqual(allocation.state, "draft")
        allocation._check_sheet_state_iff()

    def test_action_cancel_from_closed_drafts_allocations(self):
        """Triangulation: Cancel from closed MUST draft every confirmed allocation."""
        sheet = self._create_sheet()
        first_voucher = self._create_voucher(
            customer_identification="CUST-CAN-A",
            sheet_id=sheet.id,
            amount=8.0,
        )
        second_voucher = self._create_voucher(
            customer_identification="CUST-CAN-B",
            sheet_id=sheet.id,
            amount=12.0,
        )
        first = self._create_balanced_allocation(
            sheet, first_voucher, invoice_id="INV-CAN-A"
        )
        second = self._create_balanced_allocation(
            sheet, second_voucher, invoice_id="INV-CAN-B"
        )
        self._mark_validated_collections(first_voucher | second_voucher)
        confirm_sheet(sheet)
        sheet.action_close()
        self.assertEqual(first.state, "confirmed")
        self.assertEqual(second.state, "confirmed")
        sheet.action_cancel()
        self.assertEqual(sheet.state, "cancelled")
        self.assertEqual(first.state, "draft")
        self.assertEqual(second.state, "draft")
        (first | second)._check_sheet_state_iff()

    def test_action_cancel_from_submitted_drafts_allocations(self):
        """Cancel from submitted MUST set cancelled and leave allocations draft."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-CAN-S",
            sheet_id=sheet.id,
            amount=22.0,
        )
        allocation = self._create_balanced_allocation(
            sheet, voucher, invoice_id="INV-CAN-S"
        )
        self._mark_validated_collections(voucher)
        sheet.action_seller_close()
        self.assertEqual(sheet.state, "submitted")
        self.assertEqual(allocation.state, "draft")
        sheet.action_cancel()
        self.assertEqual(sheet.state, "cancelled")
        self.assertEqual(allocation.state, "draft")
        allocation._check_sheet_state_iff()

    def test_action_cancel_from_submitted_empty_members(self):
        """Triangulation: an empty submitted sheet MUST still Cancel."""
        sheet = self._create_sheet()
        sheet.action_seller_close()
        self.assertEqual(sheet.state, "submitted")
        self.assertFalse(sheet.voucher_ids)
        sheet.action_cancel()
        self.assertEqual(sheet.state, "cancelled")

    def test_cancel_closed_then_reinstate_to_submitted(self):
        """Cancel from closed MUST freeze until Reinstate writes submitted."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-CAN-CYCLE",
            sheet_id=sheet.id,
            amount=20.0,
        )
        allocation = self._create_balanced_allocation(
            sheet, voucher, invoice_id="INV-CAN-CYCLE"
        )
        receipt = self.env["collection.receipt"].create(
            {"allocation_id": allocation.id, "document_kind": "invoice"}
        )
        self.env["collection.receipt.value"].create(
            {
                "receipt_id": receipt.id,
                "voucher_id": voucher.id,
                "amount": 20.0,
            }
        )
        self._mark_validated_collections(voucher)
        confirm_sheet(sheet)
        self.env.company.write({"collection_connector_id": False})
        create_receipt = (
            "odoo.addons.collection.models.collection_connector."
            "CollectionConnector.create_receipt"
        )
        with patch(create_receipt) as mocked:
            mocked.side_effect = AssertionError("create_receipt must not run")
            sheet.action_close()
            mocked.assert_not_called()
        sheet.action_cancel()
        self.assertEqual(sheet.state, "cancelled")
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(receipt.state, "draft")
        with self.assertRaises(UserError):
            voucher.write({"sheet_id": False})
        self.assertEqual(voucher.sheet_id, sheet)
        sheet.action_reinstate()
        self.assertEqual(sheet.state, "submitted")
        self.assertEqual(allocation.state, "draft")
        allocation._check_sheet_state_iff()

    def test_reinstate_succeeds_while_seller_has_a_new_open_sheet(self):
        """Reinstate MUST write submitted even when another open sheet exists."""
        cancelled = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-REINSTATE",
            sheet_id=cancelled.id,
            amount=16.0,
        )
        allocation = self._create_balanced_allocation(
            cancelled, voucher, invoice_id="INV-REINSTATE"
        )
        self._mark_validated_collections(voucher)
        confirm_sheet(cancelled)
        cancelled.action_cancel()
        self.assertEqual(cancelled.state, "cancelled")
        current = self._create_sheet()
        self.assertEqual(current.state, "open")
        cancelled.action_reinstate()
        self.assertEqual(cancelled.state, "submitted")
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(current.state, "open")
        allocation._check_sheet_state_iff()

    def test_submitted_cannot_return_to_open(self):
        """Open or a raw write of state open MUST refuse on a submitted sheet."""
        sheet = self._create_sheet()
        sheet.action_seller_close()
        self.assertEqual(sheet.state, "submitted")
        self.assertFalse(hasattr(type(sheet), "action_open"))
        with self.assertRaises(UserError):
            sheet.write({"state": "open"})
        self.assertEqual(sheet.state, "submitted")

    def test_cancelled_cannot_return_to_open(self):
        """Open or a raw write of state open MUST refuse; Reinstate writes submitted."""
        sheet = self._create_sheet()
        confirm_sheet(sheet)
        sheet.action_cancel()
        self.assertEqual(sheet.state, "cancelled")
        self.assertFalse(hasattr(type(sheet), "action_open"))
        with self.assertRaises(UserError):
            sheet.write({"state": "open"})
        self.assertEqual(sheet.state, "cancelled")
        sheet.action_reinstate()
        self.assertEqual(sheet.state, "submitted")
        self.assertNotEqual(sheet.state, "open")

    def test_action_open_from_cancelled_leaves_draft(self):
        """Reinstate from cancelled MUST set submitted and leave allocations draft."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-OPEN-1",
            sheet_id=sheet.id,
            amount=18.0,
        )
        allocation = self._create_balanced_allocation(
            sheet, voucher, invoice_id="INV-OPEN-1"
        )
        self._mark_validated_collections(voucher)
        confirm_sheet(sheet)
        sheet.action_cancel()
        self.assertEqual(sheet.state, "cancelled")
        self.assertEqual(allocation.state, "draft")
        sheet.action_reinstate()
        self.assertEqual(sheet.state, "submitted")
        self.assertEqual(allocation.state, "draft")
        allocation._check_sheet_state_iff()

    def test_action_open_rejected_when_already_open(self):
        sheet = self._create_sheet()
        with self.assertRaises(UserError):
            sheet.action_reinstate()
        self.assertEqual(sheet.state, "open")

    def test_raw_state_write_routes_to_audited_actions(self):
        """Raw write({state}) dispatches Seller Close, Confirm, Close, or Cancel."""
        sheet = self._create_sheet()
        sheet.write({"state": "submitted"})
        self.assertEqual(sheet.state, "submitted")
        sheet.write({"state": "proposal"})
        self.assertEqual(sheet.state, "proposal")
        sheet.write({"state": "closed"})
        self.assertEqual(sheet.state, "closed")
        sheet.write({"state": "cancelled"})
        self.assertEqual(sheet.state, "cancelled")
        with self.assertRaises(UserError) as error:
            sheet.write({"state": "open"})
        message = str(error.exception)
        self.assertIn("Seller Close", message)
        self.assertIn("Reinstate", message)
        self.assertEqual(sheet.state, "cancelled")

    def test_raw_state_write_invalid_transition_rejected(self):
        """Intercepted write still enforces Confirm/Close/Cancel/Open preconditions."""
        sheet = self._create_sheet()
        with self.assertRaises(UserError):
            sheet.write({"state": "open"})
        self.assertEqual(sheet.state, "open")
        with self.assertRaises(UserError):
            sheet.write({"state": "closed"})
        self.assertEqual(sheet.state, "open")
        with self.assertRaises(UserError):
            sheet.write({"state": "cancelled"})
        self.assertEqual(sheet.state, "open")
        confirm_sheet(sheet)
        with self.assertRaises(UserError):
            sheet.write({"state": "proposal"})
        self.assertEqual(sheet.state, "proposal")

    def test_audited_state_write_allowed_with_context(self):
        """collection_sheet_audited_state allows the write used by audited actions."""
        sheet = self._create_sheet()
        force_sheet_state(sheet, "proposal")
        self.assertEqual(sheet.state, "proposal")
        force_sheet_state(sheet, "closed")
        self.assertEqual(sheet.state, "closed")
        force_sheet_state(sheet, "cancelled")
        self.assertEqual(sheet.state, "cancelled")
        force_sheet_state(sheet, "open")
        self.assertEqual(sheet.state, "open")

    def test_non_open_create_rejected(self):
        """Create MUST persist open and MUST reject any other state."""
        before = self._sheet_count()
        for state in ("submitted", "proposal", "closed", "cancelled"):
            with self.subTest(state=state):
                with self.assertRaises(UserError):
                    self._create_sheet(state=state)
                self.assertEqual(self._sheet_count(), before)

    def test_create_second_open_rejected(self):
        first = self._create_sheet()
        before = self._sheet_count()
        with self.assertRaises(UserError):
            self._create_sheet()
        self.assertEqual(self._sheet_count(), before)
        self.assertEqual(first.state, "open")
        other = self._other_internal_seller()
        other_sheet = self._create_sheet(seller_id=other.id)
        self.assertEqual(other_sheet.state, "open")
        self.assertEqual(other_sheet.seller_id, other)

    def test_proposal_does_not_occupy_one_open(self):
        """A proposal sheet MUST NOT count toward the one-open limit."""
        proposal = self._create_sheet()
        confirm_sheet(proposal)
        self.assertEqual(proposal.state, "proposal")
        second = self._create_sheet()
        self.assertEqual(second.state, "open")
        self.assertEqual(proposal.state, "proposal")
        self.assertEqual(second.seller_id, proposal.seller_id)

    def test_open_rejected_if_another_open_exists(self):
        """Create of a second open sheet is still refused; Reinstate is not."""
        first = self._create_sheet()
        force_sheet_state(first, "closed")
        cancelled = self._create_sheet()
        confirm_sheet(cancelled)
        cancelled.action_cancel()
        force_sheet_state(first, "open")
        cancelled.action_reinstate()
        self.assertEqual(cancelled.state, "submitted")
        self.assertEqual(first.state, "open")

    def test_blocked_open_keeps_allocations_draft(self):
        """Reinstate with another open sheet MUST leave allocations draft."""
        cancelled = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-OPEN-BLOCK",
            sheet_id=cancelled.id,
            amount=20.0,
        )
        allocation = self._create_balanced_allocation(
            cancelled, voucher, invoice_id="INV-OPEN-BLOCK"
        )
        self._mark_validated_collections(voucher)
        confirm_sheet(cancelled)
        cancelled.action_cancel()
        first = self._create_sheet()
        cancelled.action_reinstate()
        self.assertEqual(cancelled.state, "submitted")
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(first.state, "open")
        allocation._check_sheet_state_iff()

    def test_leftover_open_extras_cannot_confirm(self):
        """Leftover open extras MUST refuse Confirm; they MAY still Seller Close."""
        first, leftover = self._second_open_via_audited()
        self.assertEqual(first.state, "open")
        self.assertEqual(leftover.state, "open")
        with self.assertRaises(UserError):
            leftover.action_confirm()
        self.assertEqual(leftover.state, "open")
        leftover.action_seller_close()
        self.assertEqual(leftover.state, "submitted")
        with self.assertRaises(UserError):
            first.action_confirm()
        self.assertEqual(first.state, "open")

    def test_leftover_multiple_opens_reject_new_ops(self):
        first, leftover = self._second_open_via_audited()
        before = self._sheet_count()
        with self.assertRaises(UserError):
            self._create_sheet()
        force_sheet_state(first, "cancelled")
        first.action_reinstate()
        self.assertEqual(first.state, "submitted")
        voucher = self._create_voucher(
            customer_identification="CUST-LEFT-ACT", seller_id=False
        )
        voucher.write({"seller_id": self._seller().id})
        with self.assertRaises(UserError):
            voucher.action_create_collection_sheet()
        self.assertEqual(self._sheet_count(), before)
        self.assertFalse(voucher.sheet_id)
        self.assertEqual(leftover.state, "open")

    def test_create_without_seller_is_rejected(self):
        with mute_logger("odoo.sql_db"):
            try:
                self.env["collection.sheet"].create({})
            except (IntegrityError, ValidationError, UserError):
                return
        self.fail("Creating a sheet without seller_id must be rejected")

    def test_seller_is_not_copied_from_create_uid(self):
        seller = self._other_internal_seller()
        sheet = self._create_sheet(seller_id=seller.id)
        self.assertEqual(sheet.seller_id, seller)
        self.assertNotEqual(sheet.seller_id, sheet.create_uid)
        self.assertEqual(sheet.create_uid, self.env.user)

    def test_post_create_seller_write_is_rejected(self):
        sheet = self._create_sheet()
        original = sheet.seller_id
        other = self._other_internal_seller()
        with self.assertRaises(UserError):
            sheet.write({"seller_id": other.id})
        self.assertEqual(sheet.seller_id, original)

    def test_post_create_same_seller_write_is_rejected(self):
        sheet = self._create_sheet()
        with self.assertRaises(UserError):
            sheet.write({"seller_id": sheet.seller_id.id})
        self.assertEqual(sheet.seller_id, self._seller())

    def test_action_creates_sheet_for_unassigned_same_seller_any_state(self):
        pending = self._create_voucher(
            customer_identification="CUST-ACT-P", seller_id=False
        )
        approved = self._create_voucher(
            customer_identification="CUST-ACT-A", seller_id=False
        )
        pending.write({"seller_id": self._seller().id})
        approved.write({"seller_id": self._seller().id})
        approved.action_validate_seller()
        before = self._sheet_count()
        action = (pending | approved).action_create_collection_sheet()
        self.assertEqual(self._sheet_count(), before + 1)
        sheet = self.env["collection.sheet"].browse(action["res_id"])
        self.assertEqual(sheet.seller_id, self._seller())
        self.assertEqual(set(sheet.voucher_ids.ids), {pending.id, approved.id})
        self.assertEqual(pending.sheet_id, sheet)
        self.assertEqual(approved.sheet_id, sheet)
        self.assertEqual(action["res_model"], "collection.sheet")

    def test_action_rejects_ineligible_selection(self):
        other = self._other_internal_seller()
        self._ensure_enabled_seller(other)
        mixed_a = self._create_voucher(
            customer_identification="CUST-MIX-A", seller_id=False
        )
        mixed_b = self._create_voucher(
            customer_identification="CUST-MIX-B", seller_id=False
        )
        assigned = self._create_voucher(
            customer_identification="CUST-ASG", seller_id=False
        )
        mixed_a.write({"seller_id": self._seller().id})
        mixed_b.write({"seller_id": other.id})
        assigned.write({"seller_id": self._seller().id})
        sheet = self._create_sheet()
        assigned.sheet_id = sheet.id
        before = self._sheet_count()
        with self.assertRaises(UserError):
            (mixed_a | mixed_b).action_create_collection_sheet()
        with self.assertRaises(UserError):
            assigned.action_create_collection_sheet()
        with self.assertRaises(UserError):
            self.env["collection.voucher"].browse().action_create_collection_sheet()
        self.assertEqual(self._sheet_count(), before)

    def test_action_rejects_null_seller_selection(self):
        voucher = self._create_voucher(
            customer_identification="CUST-NULL-S", seller_id=False
        )
        self.assertFalse(voucher.seller_id)
        before = self._sheet_count()
        with self.assertRaises(UserError):
            voucher.action_create_collection_sheet()
        self.assertEqual(self._sheet_count(), before)
        self.assertFalse(voucher.sheet_id)

    def test_action_rejected_when_open_sheet_exists(self):
        open_sheet = self._create_sheet()
        pending = self._create_voucher(
            customer_identification="CUST-ACT-OPEN-P", seller_id=False
        )
        approved = self._create_voucher(
            customer_identification="CUST-ACT-OPEN-A", seller_id=False
        )
        pending.write({"seller_id": self._seller().id})
        approved.write({"seller_id": self._seller().id})
        approved.action_validate_seller()
        before = self._sheet_count()
        with self.assertRaises(UserError):
            (pending | approved).action_create_collection_sheet()
        self.assertEqual(self._sheet_count(), before)
        self.assertFalse(pending.sheet_id)
        self.assertFalse(approved.sheet_id)
        self.assertEqual(open_sheet.state, "open")

    def test_mixed_or_null_seller_assign_rejected(self):
        sheet = self._create_sheet()
        other = self._other_internal_seller()
        mixed = self._create_voucher(
            customer_identification="CUST-ASN-MIX", seller_id=other.id
        )
        null = self._create_voucher(
            customer_identification="CUST-ASN-NULL", seller_id=False
        )
        self._assert_sheet_assign_rejected(mixed, sheet)
        self._assert_sheet_assign_rejected(null, sheet)

    def test_reassign_moves_voucher_to_sheet_b_only(self):
        sheet_a = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-REASG", sheet_id=sheet_a.id
        )
        voucher.write({"sheet_id": False})
        confirm_sheet(sheet_a)
        sheet_b = self._create_sheet()
        voucher.write({"sheet_id": sheet_b.id})
        self.assertEqual(voucher.sheet_id, sheet_b)
        self.assertNotIn(voucher, sheet_a.voucher_ids)
        self.assertIn(voucher, sheet_b.voucher_ids)

    def test_empty_sheet_dates_false_and_no_received_date(self):
        sheet = self._create_sheet()
        self.assertFalse(sheet.date_from)
        self.assertFalse(sheet.date_to)
        self.assertNotIn("received_date", self.env["collection.sheet"]._fields)
        self.assertNotIn("received_date", self.env["collection.voucher"]._fields)

    def test_dates_from_utc_member_create_date(self):
        first = self._create_voucher(
            customer_identification="CUST-DT-1", seller_id=False
        )
        second = self._create_voucher(
            customer_identification="CUST-DT-2", seller_id=False
        )
        self.env.cr.execute(
            "UPDATE collection_voucher SET create_date = %s WHERE id = %s",
            ["2026-08-16 23:30:00", first.id],
        )
        self.env.cr.execute(
            "UPDATE collection_voucher SET create_date = %s WHERE id = %s",
            ["2026-08-17 00:30:00", second.id],
        )
        self.env.invalidate_all()
        sheet = self._create_sheet()
        (first | second).write({"seller_id": self._seller().id, "sheet_id": sheet.id})
        self.assertEqual(sheet.date_from, date(2026, 8, 16))
        self.assertEqual(sheet.date_to, date(2026, 8, 17))

    def test_unlink_sheet_unassigns_vouchers(self):
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-UNL", sheet_id=sheet.id
        )
        self.assertFalse(sheet.allocation_ids)
        voucher_id = voucher.id
        sheet.unlink()
        leftover = self.env["collection.voucher"].browse(voucher_id)
        self.assertTrue(leftover.exists())
        self.assertFalse(leftover.sheet_id)

    def test_unlink_closed_empty_refused(self):
        """Unlink of a closed sheet MUST fail even with no allocations or members."""
        sheet = self._create_sheet()
        confirm_sheet(sheet)
        sheet.action_close()
        self.assertFalse(sheet.allocation_ids)
        self.assertFalse(sheet.voucher_ids)
        sheet_id = sheet.id
        with self.assertRaises(UserError):
            sheet.unlink()
        leftover = self.env["collection.sheet"].browse(sheet_id)
        self.assertTrue(leftover.exists())
        self.assertEqual(leftover.state, "closed")

    def test_unlink_closed_with_members_refused(self):
        """Triangulation: closed unlink with members MUST fail; members stay
        assigned.
        """
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-UNL-CL", sheet_id=sheet.id
        )
        self.assertFalse(sheet.allocation_ids)
        self._mark_validated_collections(voucher)
        confirm_sheet(sheet)
        sheet.action_close()
        sheet_id = sheet.id
        voucher_id = voucher.id
        with self.assertRaises(UserError):
            sheet.unlink()
        leftover_sheet = self.env["collection.sheet"].browse(sheet_id)
        leftover_voucher = self.env["collection.voucher"].browse(voucher_id)
        self.assertTrue(leftover_sheet.exists())
        self.assertEqual(leftover_sheet.state, "closed")
        self.assertTrue(leftover_voucher.exists())
        self.assertEqual(leftover_voucher.sheet_id, leftover_sheet)

    def test_unlink_open_cascades_draft_allocations(self):
        """Open unlink MUST delete draft allocations; vouchers persist unassigned."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-UNL-ALLOC",
            sheet_id=sheet.id,
            amount=25.0,
        )
        allocation = self._create_balanced_allocation(
            sheet, voucher, invoice_id="INV-UNL"
        )
        self.assertEqual(allocation.state, "draft")
        sheet_id = sheet.id
        allocation_id = allocation.id
        voucher_id = voucher.id
        sheet.unlink()
        self.assertFalse(self.env["collection.sheet"].browse(sheet_id).exists())
        self.assertFalse(
            self.env["collection.allocation"].browse(allocation_id).exists()
        )
        leftover_voucher = self.env["collection.voucher"].browse(voucher_id)
        self.assertTrue(leftover_voucher.exists())
        self.assertFalse(leftover_voucher.sheet_id)
        self.assertFalse(leftover_voucher.allocation_id)

    def test_unlink_open_cascades_every_draft_allocation(self):
        """Triangulation: open unlink MUST cascade every draft allocation."""
        sheet = self._create_sheet()
        first_voucher = self._create_voucher(
            customer_identification="CUST-UNL-A",
            sheet_id=sheet.id,
            amount=11.0,
        )
        second_voucher = self._create_voucher(
            customer_identification="CUST-UNL-B",
            sheet_id=sheet.id,
            amount=14.0,
        )
        first = self._create_balanced_allocation(
            sheet, first_voucher, invoice_id="INV-UNL-A"
        )
        second = self._create_balanced_allocation(
            sheet, second_voucher, invoice_id="INV-UNL-B"
        )
        first_id, second_id = first.id, second.id
        first_voucher_id, second_voucher_id = first_voucher.id, second_voucher.id
        sheet.unlink()
        self.assertFalse(self.env["collection.allocation"].browse(first_id).exists())
        self.assertFalse(self.env["collection.allocation"].browse(second_id).exists())
        leftover_first = self.env["collection.voucher"].browse(first_voucher_id)
        leftover_second = self.env["collection.voucher"].browse(second_voucher_id)
        self.assertTrue(leftover_first.exists())
        self.assertTrue(leftover_second.exists())
        self.assertFalse(leftover_first.sheet_id)
        self.assertFalse(leftover_second.sheet_id)
        self.assertFalse(leftover_first.allocation_id)
        self.assertFalse(leftover_second.allocation_id)

    def test_unlink_closed_with_allocations_refused(self):
        """Closed unlink with confirmed allocations MUST fail; members stay assigned."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-UNL-CL-ALLOC",
            sheet_id=sheet.id,
            amount=25.0,
        )
        allocation = self._create_balanced_allocation(
            sheet, voucher, invoice_id="INV-UNL-CL"
        )
        self._force_confirmed_and_closed(sheet, allocation)
        sheet_id = sheet.id
        allocation_id = allocation.id
        voucher_id = voucher.id
        with self.assertRaises(UserError):
            sheet.unlink()
        leftover_sheet = self.env["collection.sheet"].browse(sheet_id)
        leftover_allocation = self.env["collection.allocation"].browse(allocation_id)
        leftover_voucher = self.env["collection.voucher"].browse(voucher_id)
        self.assertTrue(leftover_sheet.exists())
        self.assertEqual(leftover_sheet.state, "closed")
        self.assertTrue(leftover_allocation.exists())
        self.assertEqual(leftover_allocation.state, "confirmed")
        self.assertTrue(leftover_voucher.exists())
        self.assertEqual(leftover_voucher.sheet_id, leftover_sheet)
        self.assertEqual(leftover_voucher.allocation_id, leftover_allocation)

    def test_unlink_proposal_refused(self):
        """Unlink of a proposal sheet MUST fail even when empty."""
        sheet = self._create_sheet()
        confirm_sheet(sheet)
        self.assertEqual(sheet.state, "proposal")
        sheet_id = sheet.id
        with self.assertRaises(UserError):
            sheet.unlink()
        leftover = self.env["collection.sheet"].browse(sheet_id)
        self.assertTrue(leftover.exists())
        self.assertEqual(leftover.state, "proposal")

    def test_unlink_submitted_refused(self):
        """Unlink of a submitted sheet MUST fail even when empty."""
        sheet = self._create_sheet()
        sheet.action_seller_close()
        self.assertEqual(sheet.state, "submitted")
        sheet_id = sheet.id
        with self.assertRaises(UserError):
            sheet.unlink()
        leftover = self.env["collection.sheet"].browse(sheet_id)
        self.assertTrue(leftover.exists())
        self.assertEqual(leftover.state, "submitted")

    def test_unlink_cancelled_refused(self):
        """Triangulation: unlink of a cancelled sheet MUST fail and remain cancelled."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-UNL-CAN",
            sheet_id=sheet.id,
            amount=9.0,
        )
        self._mark_validated_collections(voucher)
        confirm_sheet(sheet)
        sheet.action_cancel()
        sheet_id = sheet.id
        voucher_id = voucher.id
        with self.assertRaises(UserError):
            sheet.unlink()
        leftover_sheet = self.env["collection.sheet"].browse(sheet_id)
        leftover_voucher = self.env["collection.voucher"].browse(voucher_id)
        self.assertTrue(leftover_sheet.exists())
        self.assertEqual(leftover_sheet.state, "cancelled")
        self.assertTrue(leftover_voucher.exists())
        self.assertEqual(leftover_voucher.sheet_id, leftover_sheet)

    def test_delete_command_unassigns_without_destroying_voucher(self):
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-DELCMD", sheet_id=sheet.id
        )
        sheet.write({"voucher_ids": [Command.delete(voucher.id)]})
        self.assertTrue(voucher.exists())
        self.assertFalse(voucher.sheet_id)
        self.assertFalse(sheet.voucher_ids)

    def test_freeze_rejects_add_remove_and_reassign(self):
        sheet = self._create_sheet()
        member = self._create_voucher(
            customer_identification="CUST-FRZ-MEM", sheet_id=sheet.id
        )
        outsider = self._create_voucher(
            customer_identification="CUST-FRZ-OUT", seller_id=False
        )
        outsider.write({"seller_id": self._seller().id})
        self._mark_validated_collections(member)
        confirm_sheet(sheet)
        sheet.action_close()
        with self.assertRaises(UserError):
            outsider.write({"sheet_id": sheet.id})
        with self.assertRaises(UserError):
            sheet.write({"voucher_ids": [Command.link(outsider.id)]})
        with self.assertRaises(UserError):
            member.write({"sheet_id": False})
        with self.assertRaises(UserError):
            sheet.write({"voucher_ids": [Command.unlink(member.id)]})
        with self.assertRaises(UserError):
            sheet.write({"voucher_ids": [Command.delete(member.id)]})
        target = self._create_sheet()
        with self.assertRaises(UserError):
            member.write({"sheet_id": target.id})
        with self.assertRaises(UserError):
            self._create_voucher(
                customer_identification="CUST-FRZ-CRT", sheet_id=sheet.id
            )
        self.assertEqual(member.sheet_id, sheet)
        self.assertFalse(outsider.sheet_id)
        self.assertEqual(sheet.voucher_ids, member)
        self.assertTrue(member.exists())

    def test_freeze_rejects_closed_partner_id_with_membership_error(self):
        """Closed sheets MUST reuse the membership UserError on partner_id write."""
        sheet = self._create_sheet()
        member = self._create_voucher(
            customer_identification="CUST-FRZ-PARTNER", sheet_id=sheet.id
        )
        other = dummy_customer_partner(self.env, customer="CUST-FRZ-OTHER")
        original = member.partner_id
        self._mark_validated_collections(member)
        confirm_sheet(sheet)
        sheet.action_close()
        with self.assertRaises(UserError) as error:
            member.write({"partner_id": other.id})
        self.assertEqual(
            str(error.exception),
            "Closed collection sheets cannot change membership. Reopen first.",
        )
        self.assertEqual(member.partner_id, original)

    def test_freeze_rejects_membership_on_proposal(self):
        """Proposal sheets MUST freeze membership via sheet voucher_ids writes."""
        sheet = self._create_sheet()
        member = self._create_voucher(
            customer_identification="CUST-FRZ-PROP", sheet_id=sheet.id
        )
        outsider = self._create_voucher(
            customer_identification="CUST-FRZ-PROP-OUT", seller_id=False
        )
        outsider.write({"seller_id": self._seller().id})
        self._mark_validated_collections(member)
        confirm_sheet(sheet)
        self.assertEqual(sheet.state, "proposal")
        with self.assertRaises(UserError):
            sheet.write({"voucher_ids": [Command.link(outsider.id)]})
        with self.assertRaises(UserError):
            sheet.write({"voucher_ids": [Command.unlink(member.id)]})
        with self.assertRaises(UserError):
            sheet.write({"voucher_ids": [Command.delete(member.id)]})
        self.assertEqual(sheet.voucher_ids, member)
        self.assertFalse(outsider.sheet_id)

    def test_freeze_rejects_membership_on_cancelled(self):
        """Triangulation: cancelled sheets MUST also freeze membership writes."""
        sheet = self._create_sheet()
        member = self._create_voucher(
            customer_identification="CUST-FRZ-CAN", sheet_id=sheet.id
        )
        outsider = self._create_voucher(
            customer_identification="CUST-FRZ-CAN-OUT", seller_id=False
        )
        outsider.write({"seller_id": self._seller().id})
        self._mark_validated_collections(member)
        confirm_sheet(sheet)
        sheet.action_cancel()
        self.assertEqual(sheet.state, "cancelled")
        with self.assertRaises(UserError):
            sheet.write({"voucher_ids": [Command.link(outsider.id)]})
        with self.assertRaises(UserError):
            sheet.write({"voucher_ids": [Command.unlink(member.id)]})
        self.assertEqual(sheet.voucher_ids, member)
        self.assertFalse(outsider.sheet_id)
        action = self.env.ref("collection.action_create_collection_sheet")
        self.assertEqual(action.type, "ir.actions.server")
        self.assertEqual(action.binding_view_types, "list")
        self.assertEqual(action.binding_model_id.model, "collection.voucher")

    def test_submitted_membership_add_and_remove(self):
        """Submitted sheets MUST persist lawful membership add and remove."""
        sheet = self._create_sheet()
        member = self._create_voucher(
            customer_identification="CUST-SUB-MEM", sheet_id=sheet.id
        )
        outsider = self._create_voucher(
            customer_identification="CUST-SUB-OUT", seller_id=False
        )
        outsider.write({"seller_id": self._seller().id})
        force_sheet_state(sheet, "submitted")
        self.assertEqual(sheet.state, "submitted")
        outsider.write({"sheet_id": sheet.id})
        self.assertEqual(outsider.sheet_id, sheet)
        self.assertIn(outsider, sheet.voucher_ids)
        member.write({"sheet_id": False})
        self.assertFalse(member.sheet_id)
        self.assertNotIn(member, sheet.voucher_ids)
        sheet.write({"voucher_ids": [Command.link(member.id)]})
        self.assertEqual(member.sheet_id, sheet)
        sheet.write({"voucher_ids": [Command.unlink(outsider.id)]})
        self.assertFalse(outsider.sheet_id)
        self.assertEqual(sheet.voucher_ids, member)

    def test_submitted_partner_reassign_persists(self):
        """Submitted sheets MUST allow voucher partner_id reassignment."""
        sheet = self._create_sheet()
        member = self._create_voucher(
            customer_identification="CUST-SUB-PARTNER", sheet_id=sheet.id
        )
        other = dummy_customer_partner(self.env, customer="CUST-SUB-OTHER")
        force_sheet_state(sheet, "submitted")
        member.write({"partner_id": other.id})
        self.assertEqual(member.partner_id, other)
        self.assertEqual(sheet.state, "submitted")

    def test_action_open_document_review_returns_client_action_with_sheet_id(self):
        """Saved sheet + flag ON must open Document Review with that sheet_id."""
        self.env.company.write({"document_review_enabled": True})
        sheet = self._create_sheet()
        self.assertIsInstance(sheet.id, int)
        self.assertGreater(sheet.id, 0)
        action = sheet.action_open_document_review()
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "collection.document_review")
        self.assertEqual(action["params"]["sheet_id"], sheet.id)

    def test_action_open_document_review_params_match_each_saved_sheet(self):
        """Triangulation: params.sheet_id is the invoked sheet, not a constant."""
        self.env.company.write({"document_review_enabled": True})
        sheet_a = self._create_sheet()
        sheet_b = self._create_sheet(seller_id=self._other_internal_seller().id)
        self.assertNotEqual(sheet_a.id, sheet_b.id)
        action_a = sheet_a.action_open_document_review()
        action_b = sheet_b.action_open_document_review()
        self.assertEqual(action_a["params"]["sheet_id"], sheet_a.id)
        self.assertEqual(action_b["params"]["sheet_id"], sheet_b.id)
        self.assertEqual(action_a["tag"], "collection.document_review")
        self.assertEqual(action_b["tag"], "collection.document_review")

    def test_action_open_document_review_refused_when_flag_off(self):
        """Saved sheet + flag OFF must raise the voucher Document Review UserError."""
        self.env.company.write({"document_review_enabled": False})
        sheet = self._create_sheet()
        with self.assertRaises(UserError) as error:
            sheet.action_open_document_review()
        self.assertEqual(str(error.exception), "Document Review is not enabled.")

    def test_action_open_document_review_refused_on_new_id(self):
        """Unsaved .new() records (NewId) must not open Document Review."""
        self.env.company.write({"document_review_enabled": True})
        unsaved = self.env["collection.sheet"].new({"seller_id": self._seller().id})
        self.assertFalse(isinstance(unsaved.id, int))
        self.assertFalse(unsaved.id)
        with self.assertRaises(UserError):
            unsaved.action_open_document_review()

    def test_action_open_document_review_refused_when_not_open(self):
        """Saved proposal, closed, or cancelled sheets MUST refuse Document Review."""
        self.env.company.write({"document_review_enabled": True})
        for state in ("proposal", "closed", "cancelled"):
            with self.subTest(state=state):
                sheet = self._create_sheet(
                    seller_id=self._other_internal_seller().id,
                )
                force_sheet_state(sheet, state)
                with self.assertRaises(UserError):
                    sheet.action_open_document_review()
                self.assertEqual(sheet.state, state)

    def test_action_open_document_review_succeeds_when_submitted(self):
        """Saved submitted sheet + flag ON MUST open Document Review."""
        self.env.company.write({"document_review_enabled": True})
        sheet = self._create_sheet()
        force_sheet_state(sheet, "submitted")
        action = sheet.action_open_document_review()
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "collection.document_review")
        self.assertEqual(action["params"]["sheet_id"], sheet.id)
        self.assertEqual(sheet.state, "submitted")

    def test_empty_sheet_voucher_count_is_zero(self):
        """A sheet with no members MUST report non-stored voucher_count 0."""
        field = self.env["collection.sheet"]._fields["voucher_count"]
        self.assertTrue(field.compute)
        self.assertFalse(field.store)
        sheet = self._create_sheet()
        self.assertFalse(sheet.voucher_ids)
        self.assertEqual(sheet.voucher_count, 0)

    def test_voucher_count_matches_member_count(self):
        """Triangulation: voucher_count MUST equal the number of sheet members."""
        sheet = self._create_sheet()
        first = self._create_voucher(
            customer_identification="CUST-VC-1", sheet_id=sheet.id
        )
        second = self._create_voucher(
            customer_identification="CUST-VC-2", sheet_id=sheet.id
        )
        self.assertEqual(sheet.voucher_ids, first | second)
        self.assertEqual(sheet.voucher_count, 2)

    def test_action_open_vouchers_returns_filtered_act_window(self):
        """Saved sheet MUST open vouchers for that sheet only (no menu path)."""
        sheet = self._create_sheet()
        self.assertIsInstance(sheet.id, int)
        self.assertGreater(sheet.id, 0)
        action = sheet.action_open_vouchers()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "collection.voucher")
        self.assertEqual(action["view_mode"], "list,kanban,form")
        self.assertEqual(action["domain"], [("sheet_id", "=", sheet.id)])
        self.assertEqual(action["context"]["default_sheet_id"], sheet.id)
        self.assertEqual(action["context"]["default_seller_id"], sheet.seller_id.id)
        self.assertFalse(action.get("path"))

    def test_action_open_vouchers_domain_matches_each_saved_sheet(self):
        """Triangulation: domain and defaults bind to the invoked sheet."""
        sheet_a = self._create_sheet()
        sheet_b = self._create_sheet(seller_id=self._other_internal_seller().id)
        self.assertNotEqual(sheet_a.id, sheet_b.id)
        action_a = sheet_a.action_open_vouchers()
        action_b = sheet_b.action_open_vouchers()
        self.assertEqual(action_a["domain"], [("sheet_id", "=", sheet_a.id)])
        self.assertEqual(action_b["domain"], [("sheet_id", "=", sheet_b.id)])
        self.assertEqual(action_a["context"]["default_seller_id"], sheet_a.seller_id.id)
        self.assertEqual(action_b["context"]["default_seller_id"], sheet_b.seller_id.id)
        self.assertEqual(action_a["view_mode"], "list,kanban,form")
        self.assertEqual(action_b["view_mode"], "list,kanban,form")

    def test_action_open_vouchers_refused_on_new_id(self):
        """Unsaved .new() records (NewId) must not open vouchers."""
        unsaved = self.env["collection.sheet"].new({"seller_id": self._seller().id})
        self.assertFalse(isinstance(unsaved.id, int))
        self.assertFalse(unsaved.id)
        with self.assertRaises(UserError):
            unsaved.action_open_vouchers()

    def test_action_open_voucher_reassign_removed(self):
        """Saved sheets MUST NOT expose action_open_voucher_reassign."""
        sheet = self._create_sheet()
        self.assertFalse(
            hasattr(type(sheet), "action_open_voucher_reassign"),
            "action_open_voucher_reassign MUST be dropped with Reassign kanban",
        )
        self.assertFalse(
            self.env.ref(
                "collection.view_collection_voucher_reassign_kanban",
                raise_if_not_found=False,
            ),
            "reassign kanban XMLID MUST be gone",
        )

    def test_action_open_voucher_reassign_removed_on_new_record(self):
        """Triangulation: unsaved sheets also have no reassign action."""
        unsaved = self.env["collection.sheet"].new({"seller_id": self._seller().id})
        self.assertFalse(isinstance(unsaved.id, int))
        self.assertFalse(
            hasattr(type(unsaved), "action_open_voucher_reassign"),
            "unsaved sheets MUST NOT inherit a reassign action",
        )

    def test_document_review_enabled_helper_is_non_stored_and_follows_flag(self):
        """Non-stored helper mirrors company._document_review_enabled() (no DDL)."""
        field = self.env["collection.sheet"]._fields["document_review_enabled"]
        self.assertTrue(field.compute)
        self.assertFalse(field.store)
        self.env.company.write({"document_review_enabled": True})
        on_sheet = self._create_sheet()
        self.assertTrue(on_sheet.document_review_enabled)
        confirm_sheet(on_sheet)
        self.env.company.write({"document_review_enabled": False})
        off_sheet = self._create_sheet()
        self.assertFalse(off_sheet.document_review_enabled)

    def test_create_with_seller_assigns_unique_open_sheet(self):
        """Unique open sheet MUST receive vouchers created with that seller."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(customer_identification="CUST-AA-UNIQ")
        self.assertEqual(voucher.sheet_id, sheet)
        self.assertEqual(sheet.voucher_ids, voucher)

    def test_create_with_seller_creates_open_sheet_when_none(self):
        """Zero opens MUST create one open sheet and assign the voucher."""
        before = self._sheet_count()
        voucher = self._create_voucher(customer_identification="CUST-AA-NONE")
        self.assertEqual(self._sheet_count(), before + 1)
        self.assertTrue(voucher.sheet_id)
        self.assertEqual(voucher.sheet_id.seller_id, self._seller())
        self.assertEqual(voucher.sheet_id.state, "open")
        self.assertIn(voucher, voucher.sheet_id.voucher_ids)

    def test_create_with_seller_rejected_when_multiple_opens(self):
        """More than one open MUST raise UserError with no voucher written."""
        first, leftover = self._second_open_via_audited()
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_sheets = self._sheet_count()
        with self.assertRaises(UserError):
            self._create_voucher(customer_identification="CUST-AA-MULTI")
        self.assertEqual(
            self.env["collection.voucher"].search_count([]), before_vouchers
        )
        self.assertEqual(self._sheet_count(), before_sheets)
        self.assertEqual(first.state, "open")
        self.assertEqual(leftover.state, "open")

    def test_create_honors_explicit_open_sheet_id(self):
        """Explicit open same-seller sheet_id MUST be used instead of resolving."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-AA-EXPL", sheet_id=sheet.id
        )
        self.assertEqual(voucher.sheet_id, sheet)
        falsey = self._create_voucher(
            customer_identification="CUST-AA-FALSEY", sheet_id=False
        )
        self.assertEqual(falsey.sheet_id, sheet)

    def test_create_honors_explicit_submitted_sheet_id(self):
        """Explicit submitted same-seller sheet_id MUST be used instead of resolving."""
        sheet = self._create_sheet()
        sheet.action_seller_close()
        self.assertEqual(sheet.state, "submitted")
        voucher = self._create_voucher(
            customer_identification="CUST-AA-SUB-EXPL", sheet_id=sheet.id
        )
        self.assertEqual(voucher.sheet_id, sheet)
        self.assertEqual(sheet.state, "submitted")

    def test_create_with_closed_sheet_id_fails(self):
        """Assigning a closed sheet on create MUST fail (Phase 2 freeze)."""
        sheet = self._create_sheet()
        confirm_sheet(sheet)
        sheet.action_close()
        before = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError):
            self._create_voucher(
                customer_identification="CUST-AA-CLOSED", sheet_id=sheet.id
            )
        self.assertEqual(self.env["collection.voucher"].search_count([]), before)
        self.assertFalse(sheet.voucher_ids)

    def test_create_without_seller_stays_unassigned(self):
        """Null seller_id MUST leave the voucher unassigned even if an open exists."""
        sheet = self._create_sheet()
        before = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError):
            self.env["collection.voucher"].create(
                {
                    "partner_id": dummy_customer_partner(
                        self.env, customer="CUST-AA-OMIT"
                    ).id,
                    "document_type": "unsupported",
                }
            )
        self.assertEqual(self.env["collection.voucher"].search_count([]), before)

        historical = self._create_voucher(
            customer_identification="CUST-AA-HIST-NULL", seller_id=False
        )
        self.env.cr.execute(
            """
            UPDATE collection_voucher
               SET seller_id = NULL, sheet_id = NULL
             WHERE id = %s
            """,
            (historical.id,),
        )
        historical.invalidate_recordset(["seller_id", "sheet_id"])
        self.assertFalse(historical.seller_id)
        self.assertFalse(historical.sheet_id)
        self.assertNotIn(historical, sheet.voucher_ids)

    def test_later_seller_write_does_not_auto_assign(self):
        """Writing seller_id on an existing voucher MUST NOT auto-assign."""
        sheet = self._create_sheet()
        omitted = self._create_voucher(
            customer_identification="CUST-AA-WRITE-OMIT",
            sheet_id=sheet.id,
        )
        omitted.write({"sheet_id": False})
        omitted.write({"seller_id": self._seller().id})
        self.assertFalse(omitted.sheet_id)

        member = self._create_voucher(
            customer_identification="CUST-AA-WRITE-UNASG", sheet_id=sheet.id
        )
        member.write({"sheet_id": False})
        self.assertFalse(member.sheet_id)
        member.write({"seller_id": self._seller().id})
        self.assertFalse(member.sheet_id)

        other = self._other_internal_seller()
        other_sheet = self._create_sheet(seller_id=other.id)
        linked = self._create_voucher(
            customer_identification="CUST-AA-WRITE-UNL",
            seller_id=other.id,
            sheet_id=other_sheet.id,
        )
        other_sheet.unlink()
        self.assertFalse(linked.sheet_id)
        linked.write({"seller_id": other.id})
        self.assertFalse(linked.sheet_id)
        self.assertEqual(sheet.state, "open")
        self.assertNotIn(omitted, sheet.voucher_ids)
        self.assertNotIn(member, sheet.voucher_ids)

    def test_batch_create_resolves_one_open_per_seller(self):
        """Batch create MUST resolve once per seller and share that sheet."""
        seller = self._seller()
        other = self._other_internal_seller()
        self._ensure_enabled_seller(other)
        confirm_sheet(
            self.env["collection.sheet"].search(
                [
                    ("seller_id", "in", [seller.id, other.id]),
                    ("state", "=", "open"),
                ]
            )
        )
        before = self._sheet_count()
        vouchers = self.env["collection.voucher"].create(
            [
                {
                    "partner_id": dummy_customer_partner(
                        self.env, customer="CUST-AA-BATCH-A"
                    ).id,
                    "document_type": "unsupported",
                    "seller_id": seller.id,
                },
                {
                    "partner_id": dummy_customer_partner(
                        self.env, customer="CUST-AA-BATCH-B"
                    ).id,
                    "document_type": "unsupported",
                    "seller_id": seller.id,
                },
                {
                    "partner_id": dummy_customer_partner(
                        self.env, customer="CUST-AA-BATCH-C"
                    ).id,
                    "document_type": "unsupported",
                    "seller_id": other.id,
                },
            ]
        )
        self.assertEqual(self._sheet_count(), before + 2)
        first, second, third = vouchers
        self.assertTrue(first.sheet_id)
        self.assertEqual(first.sheet_id, second.sheet_id)
        self.assertEqual(first.sheet_id.seller_id, seller)
        self.assertEqual(first.sheet_id.state, "open")
        self.assertNotEqual(third.sheet_id, first.sheet_id)
        self.assertEqual(third.sheet_id.seller_id, other)
        self.assertEqual(third.sheet_id.state, "open")

    def _enable_sellers(self, *sellers):
        self.env.company.write(
            {"enabled_seller_ids": [Command.set([seller.id for seller in sellers])]}
        )

    def _clear_enabled_sellers(self):
        self.env.company.write({"enabled_seller_ids": [Command.clear()]})

    def test_sheet_create_empty_enabled_sellers_rejected(self):
        """NEW sheet create MUST reject a seller when the enabled list is empty."""
        seller = self.env.ref("base.user_admin")
        self._clear_enabled_sellers()
        before = self._sheet_count()
        with self.assertRaises(UserError):
            self.env["collection.sheet"].create({"seller_id": seller.id})
        self.assertEqual(self._sheet_count(), before)

    def test_sheet_create_disabled_seller_rejected(self):
        """Triangulation: a seller missing from the enabled list MUST be rejected."""
        enabled = self.env.ref("base.user_admin")
        disabled = create_internal_seller(self.env, "sheet_disabled_seller")
        self._enable_sellers(enabled)
        before = self._sheet_count()
        with self.assertRaises(UserError):
            self.env["collection.sheet"].create({"seller_id": disabled.id})
        self.assertEqual(self._sheet_count(), before)

    def test_disabled_seller_sheet_stays_visible_and_confirmable(self):
        seller = self.env.ref("base.user_admin")
        self._enable_sellers(seller)
        sheet = self.env["collection.sheet"].create({"seller_id": seller.id})
        self._clear_enabled_sellers()
        found = self.env["collection.sheet"].search([("id", "=", sheet.id)])
        self.assertEqual(found, sheet, "disabled-seller sheet must stay listed")
        confirm_sheet(sheet)
        self.assertEqual(sheet.state, "proposal")
        self.assertTrue(sheet.exists())

    def test_disabled_seller_open_sheet_remains_closeable(self):
        """A later-disabled seller MUST still Seller Close an existing open sheet."""
        seller = self.env.ref("base.user_admin")
        self._enable_sellers(seller)
        sheet = self.env["collection.sheet"].create({"seller_id": seller.id})
        self._clear_enabled_sellers()
        sheet.action_seller_close()
        self.assertEqual(sheet.state, "submitted")
        self.assertTrue(sheet.exists())

    def test_disabled_seller_sheet_open_skips_helper(self):
        """Triangulation: Open from cancelled MUST skip the new-work helper."""
        seller = self.env.ref("base.user_admin")
        self._enable_sellers(seller)
        sheet = self.env["collection.sheet"].create({"seller_id": seller.id})
        confirm_sheet(sheet)
        sheet.action_cancel()
        self._clear_enabled_sellers()
        sheet.action_reinstate()
        self.assertEqual(sheet.state, "submitted")
        self.assertTrue(sheet.exists())

    def _partner_has_autopost_bills_column(self):
        self.env.cr.execute(
            """
            SELECT 1
              FROM information_schema.columns
             WHERE table_name = 'res_partner'
               AND column_name = 'autopost_bills'
            """
        )
        return bool(self.env.cr.fetchone())

    def _create_company(self, name):
        """Persist a second company; satisfy partner.autopost_bills when present."""
        Partner = self.env["res.partner"].with_context(
            tracking_disable=True,
            mail_create_nolog=True,
            mail_notrack=True,
            mail_create_nosubscribe=True,
        )
        partner_vals = {"name": name, "is_company": True}
        if "autopost_bills" in Partner._fields:
            partner_vals["autopost_bills"] = "ask"
            partner = Partner.create(partner_vals)
        elif self._partner_has_autopost_bills_column():
            self.env.cr.execute(
                """
                INSERT INTO res_partner (
                    name, email, active, complete_name, type, is_company,
                    autopost_bills, create_uid, write_uid, create_date, write_date
                )
                VALUES (
                    %s, %s, true, %s, 'contact', true, 'ask',
                    1, 1,
                    (now() AT TIME ZONE 'UTC'),
                    (now() AT TIME ZONE 'UTC')
                )
                RETURNING id
                """,
                (name, f"{name}@example.com", name),
            )
            partner = Partner.browse(self.env.cr.fetchone()[0])
        else:
            partner = Partner.create(partner_vals)
        return self.env["res.company"].create(
            {
                "name": name,
                "partner_id": partner.id,
            }
        )

    def test_auto_create_off_skips_create_and_assign(self):
        """OFF + omitted sheet_id MUST persist unassigned and not create a sheet."""
        self.env.company.write({"auto_create_sheet": False})
        before = self._sheet_count()
        voucher = self._create_voucher(customer_identification="CUST-AA-OFF")
        self.assertFalse(voucher.sheet_id)
        self.assertEqual(self._sheet_count(), before)

    def test_auto_create_off_skips_assign_when_open_exists(self):
        """Triangulation: OFF MUST skip assign even when an open sheet exists."""
        sheet = self._create_sheet()
        self.env.company.write({"auto_create_sheet": False})
        before = self._sheet_count()
        voucher = self._create_voucher(customer_identification="CUST-AA-OFF-OPEN")
        self.assertFalse(voucher.sheet_id)
        self.assertNotIn(voucher, sheet.voucher_ids)
        self.assertEqual(self._sheet_count(), before)
        self.assertEqual(sheet.state, "open")

    def test_action_creates_sheet_when_auto_create_off(self):
        """List Action MUST still create one open sheet when auto-create is OFF."""
        self.env.company.write({"auto_create_sheet": False})
        before = self._sheet_count()
        voucher = self._create_voucher(customer_identification="CUST-ACT-OFF")
        self.assertFalse(voucher.sheet_id)
        self.assertEqual(self._sheet_count(), before)
        action = voucher.action_create_collection_sheet()
        self.assertEqual(self._sheet_count(), before + 1)
        sheet = self.env["collection.sheet"].browse(action["res_id"])
        self.assertEqual(sheet.seller_id, self._seller())
        self.assertEqual(sheet.company_id, voucher.company_id)
        self.assertEqual(sheet.state, "open")
        self.assertEqual(voucher.sheet_id, sheet)

    def test_action_rejected_for_disabled_seller(self):
        """List Action MUST reject after the seller is removed from the enabled list."""
        self.env.company.write({"auto_create_sheet": False})
        seller = self._seller()
        voucher = self._create_voucher(customer_identification="CUST-ACT-DISABLED")
        self.assertEqual(voucher.seller_id, seller)
        self.assertFalse(voucher.sheet_id)
        other = self._other_internal_seller()
        self._enable_sellers(other)
        self.assertNotIn(seller, self.env.company.enabled_seller_ids)
        before = self._sheet_count()
        with self.assertRaises(UserError) as err:
            voucher.action_create_collection_sheet()
        self.assertIn("seller", str(err.exception).lower())
        self.assertEqual(self._sheet_count(), before)
        self.assertFalse(voucher.sheet_id)

    def test_same_seller_may_be_open_in_two_companies(self):
        """One-open is per (company, seller): A and B MAY both have one open."""
        seller = self._seller()
        sheet_a = self._create_sheet()
        company_b = self._create_company("One Open Co B")
        ensure_enabled_seller(self.env, seller, company_b)
        sheet_b = self.env["collection.sheet"].create(
            {
                "seller_id": seller.id,
                "company_id": company_b.id,
            }
        )
        self.assertEqual(sheet_a.state, "open")
        self.assertEqual(sheet_b.state, "open")
        self.assertEqual(sheet_a.company_id, self.env.company)
        self.assertEqual(sheet_b.company_id, company_b)
        self.assertEqual(sheet_a.seller_id, seller)
        self.assertEqual(sheet_b.seller_id, seller)
        with self.assertRaises(UserError):
            self._create_sheet()
        self.assertEqual(sheet_a.state, "open")
        self.assertEqual(sheet_b.state, "open")

    def test_auto_assign_creates_open_in_voucher_company(self):
        """ON auto-assign MUST resolve open sheets in the voucher company only."""
        seller = self._seller()
        sheet_a = self._create_sheet()
        company_b = self._create_company("Auto Assign Co B")
        ensure_enabled_seller(self.env, seller, company_b)
        voucher = self.env["collection.voucher"].create(
            {
                "partner_id": dummy_customer_partner(
                    self.env, customer="CUST-AA-COB"
                ).id,
                "document_type": "unsupported",
                "seller_id": seller.id,
                "company_id": company_b.id,
            }
        )
        self.assertEqual(voucher.company_id, company_b)
        self.assertTrue(voucher.sheet_id)
        self.assertEqual(voucher.sheet_id.company_id, company_b)
        self.assertEqual(voucher.sheet_id.seller_id, seller)
        self.assertEqual(voucher.sheet_id.state, "open")
        self.assertNotEqual(voucher.sheet_id, sheet_a)
        self.assertEqual(sheet_a.state, "open")

    def test_action_creates_sheet_in_selection_company(self):
        """List Action MUST stamp the vouchers' company, not env.company."""
        company_b = self._create_company("Action Co B")
        seller = self._seller()
        ensure_enabled_seller(self.env, seller, company_b)
        voucher = self._create_voucher(
            customer_identification="CUST-ACT-COB",
            seller_id=False,
            company_id=company_b.id,
        )
        voucher.write({"seller_id": seller.id})
        self.assertFalse(voucher.sheet_id)
        action = voucher.action_create_collection_sheet()
        sheet = self.env["collection.sheet"].browse(action["res_id"])
        self.assertEqual(sheet.company_id, company_b)
        self.assertEqual(sheet.seller_id, seller)
        self.assertEqual(voucher.sheet_id, sheet)

    def test_action_allowed_when_seller_open_in_other_company(self):
        """Triangulation: an open sheet in B MUST NOT block the Action in A."""
        seller = self._seller()
        company_b = self._create_company("Action Other Co")
        ensure_enabled_seller(self.env, seller, company_b)
        sheet_b = self.env["collection.sheet"].create(
            {
                "seller_id": seller.id,
                "company_id": company_b.id,
            }
        )
        voucher = self._create_voucher(
            customer_identification="CUST-ACT-OTHER", seller_id=False
        )
        voucher.write({"seller_id": seller.id})
        action = voucher.action_create_collection_sheet()
        sheet_a = self.env["collection.sheet"].browse(action["res_id"])
        self.assertEqual(sheet_a.company_id, self.env.company)
        self.assertEqual(sheet_a.seller_id, seller)
        self.assertEqual(voucher.sheet_id, sheet_a)
        self.assertEqual(sheet_b.state, "open")
        self.assertNotEqual(sheet_a, sheet_b)
