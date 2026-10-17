# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import inspect
from datetime import date
from re import fullmatch
from unittest.mock import patch

from psycopg2 import IntegrityError

from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.collection.models.collection_common import privileged

from .common_connector import (
    confirm_sheet,
    force_sheet_state,
    install_bound_test_connector,
    install_test_connector_type,
)
from .test_collection_payment import (
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
)

ERP_CUSTOMER_IDENT = "20-11111111-1"
ERP_OUTSTANDING_IDS = frozenset({"inv-bound-overdue", "inv-bound-open"})


class TestCollectionAllocation(TransactionCase):
    """RED: draft default, freeze iff confirmed, residual both, drop validate/reject."""

    def _seller(self):
        return ensure_enabled_seller(self.env)

    def _partner(self, label="ALLOC-CUST"):
        return dummy_customer_partner(self.env, customer=label)

    def _create_sheet(self, *, force_new=False, **extra):
        seller = extra.pop("seller_id", None)
        seller = self.env["res.users"].browse(seller) if seller else self._seller()
        company = self.env["res.company"].browse(
            extra.get("company_id") or self.env.company.id
        )
        ensure_enabled_seller(self.env, seller, company=company)
        if not force_new and "company_id" not in extra:
            existing = self.env["collection.sheet"].search(
                [
                    ("seller_id", "=", seller.id),
                    ("company_id", "=", company.id),
                    ("state", "=", "open"),
                ],
                limit=1,
            )
            if existing:
                return existing
        vals = {"seller_id": seller.id, **extra}
        return self.env["collection.sheet"].create(vals)

    def _create_voucher(self, partner, sheet, amount=100.0, **extra):
        ensure_enabled_seller(self.env, sheet.seller_id, company=sheet.company_id)
        vals = {
            "partner_id": partner.id,
            "document_type": "bank_transfer",
            "seller_id": sheet.seller_id.id,
            "sheet_id": sheet.id,
            "company_id": sheet.company_id.id,
            "amount": amount,
        }
        vals.update(extra)
        return self.env["collection.voucher"].create(vals)

    def _line_vals(self, amount_applied=100.0, invoice_balance=100.0, **extra):
        vals = {
            "external_invoice_id": extra.pop("external_invoice_id", "INV-1"),
            "invoice_number": extra.pop("invoice_number", "A-1"),
            "issue_date": extra.pop("issue_date", date(2026, 1, 1)),
            "due_date": extra.pop("due_date", date(2026, 1, 31)),
            "invoice_amount": extra.pop("invoice_amount", invoice_balance),
            "invoice_balance": invoice_balance,
            "invoice_state": extra.pop("invoice_state", "open"),
            "amount_applied": amount_applied,
        }
        vals.update(extra)
        return vals

    def _create_allocation(self, sheet, partner, vouchers=None, lines=None, **extra):
        vals = {
            "sheet_id": sheet.id,
            "partner_id": partner.id,
        }
        if vouchers:
            vals["voucher_ids"] = [Command.set(vouchers.ids)]
        if lines is not None:
            vals["line_ids"] = [Command.create(line) for line in lines]
        extra.pop("residual_reason", None)
        vals.update(extra)
        return self.env["collection.allocation"].create(vals)

    def _balanced_allocation(self, amount=100.0, **extra):
        partner = extra.pop("partner", None) or self._partner()
        sheet = extra.pop("sheet", None) or self._create_sheet()
        voucher = extra.pop("voucher", None) or self._create_voucher(
            partner, sheet, amount=amount
        )
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[self._line_vals(amount_applied=amount, invoice_balance=amount)],
        )
        return allocation, voucher, sheet, partner

    def _record_agent_request(self, allocation, request_id):
        """Record an agent request on the allocation, as the MCP tool does."""
        with privileged("collection_allocation_request"):
            allocation.write(
                {
                    "request_id": request_id,
                    "content_hash": "abc123",
                    "request_log": {request_id: {"revision": allocation.revision}},
                }
            )

    def _create_receipt(self, allocation, document_kind="invoice", **extra):
        vals = {
            "allocation_id": allocation.id,
            "document_kind": document_kind,
        }
        vals.update(extra)
        return self.env["collection.receipt"].create(vals)

    def _create_value(self, receipt, voucher, amount):
        return self.env["collection.receipt.value"].create(
            {
                "receipt_id": receipt.id,
                "voucher_id": voucher.id,
                "amount": amount,
            }
        )

    def _confirm(self, allocation):
        with privileged("collection_allocation_audited_state"):
            allocation.write({"state": "confirmed"})
        return allocation

    def _mark_validated(self, *vouchers):
        records = vouchers[0]
        for voucher in vouchers[1:]:
            records |= voucher
        with privileged("collection_audited_state"):
            records.write({"state": "validated_collections"})
        return records

    def _bind_erp_customer(self, partner, seller, identification=ERP_CUSTOMER_IDENT):
        install_test_connector_type(self)
        connector = install_bound_test_connector(self, seller)
        Binding = self.env["collection.connector.customer.binding"]
        existing = Binding.search(
            [
                ("connector_id", "=", connector.id),
                ("partner_id", "=", partner.id),
            ],
            limit=1,
        )
        if existing:
            return connector, existing
        binding = Binding.create(
            {
                "connector_id": connector.id,
                "external_customer_id": f"cust-{partner.id}",
                "identification": identification,
                "partner_id": partner.id,
                "customer_code": "C-BOUND-1",
            }
        )
        return connector, binding

    def test_unique_sheet_partner_rejected(self):
        """UNIQUE(sheet_id, partner_id) MUST reject a second header."""
        allocation, _voucher, sheet, partner = self._balanced_allocation()
        self.assertEqual(allocation.state, "draft")
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self._create_allocation(sheet, partner)

    def test_unique_sheet_partner_allows_other_partner_or_sheet(self):
        """Triangulation: other partner on same sheet, or same partner other sheet."""
        _allocation, _voucher, sheet, partner = self._balanced_allocation(amount=50.0)
        other_partner = self._partner("ALLOC-CUST-B")
        other_voucher = self._create_voucher(other_partner, sheet, amount=50.0)
        other_alloc = self._create_allocation(
            sheet,
            other_partner,
            vouchers=other_voucher,
            lines=[
                self._line_vals(
                    amount_applied=50.0,
                    invoice_balance=50.0,
                    external_invoice_id="INV-OTHER-PARTNER",
                )
            ],
        )
        self.assertTrue(other_alloc.id)
        self.assertEqual(other_alloc.partner_id, other_partner)

        with privileged("collection_audited_state"):
            (other_voucher | _voucher).write({"state": "validated_collections"})
        confirm_sheet(sheet)
        sheet_b = self._create_sheet(force_new=True)
        voucher_b = self._create_voucher(partner, sheet_b, amount=25.0)
        alloc_b = self._create_allocation(
            sheet_b,
            partner,
            vouchers=voucher_b,
            lines=[
                self._line_vals(
                    amount_applied=25.0,
                    invoice_balance=25.0,
                    external_invoice_id="INV-OTHER-SHEET",
                )
            ],
        )
        self.assertTrue(alloc_b.id)
        self.assertEqual(alloc_b.sheet_id, sheet_b)

    def test_sequence_name_matches_ca_year(self):
        allocation, _voucher, _sheet, _partner = self._balanced_allocation()
        year = date.today().year
        self.assertTrue(
            fullmatch(rf"CA/{year}/\d{{4,}}", allocation.name),
            f"Allocation name {allocation.name!r} must match CA/<year>/<padded>",
        )

    def test_create_defaults_to_draft(self):
        """ORM create MUST persist draft; selection MUST be draft/confirmed only."""
        allocation, _voucher, sheet, _partner = self._balanced_allocation()
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(sheet.state, "open")
        states = {key for key, _label in allocation._fields["state"].selection}
        self.assertEqual(states, {"draft", "confirmed"})
        untitled = self.env["collection.allocation"].new({})
        self.assertEqual(untitled.state, "draft")

    def test_freeze_rejects_writes_when_confirmed(self):
        allocation, voucher, sheet, partner = self._balanced_allocation()
        self._confirm(allocation)
        self.assertEqual(allocation.state, "confirmed")
        outsider = self._create_voucher(
            partner, sheet, amount=10.0, document_id="ALLOC-FREEZE-OUT"
        )
        with self.assertRaises(UserError):
            allocation.write({"voucher_ids": [Command.link(outsider.id)]})
        with self.assertRaises(UserError):
            allocation.write({"partner_id": self._partner("ALLOC-FREEZE-P").id})
        other_seller = create_internal_seller(self.env, "alloc_freeze_other")
        other_sheet = self._create_sheet(seller_id=other_seller.id, force_new=True)
        with self.assertRaises(UserError):
            allocation.write({"sheet_id": other_sheet.id})
        with self.assertRaises(UserError):
            allocation.write(
                {
                    "line_ids": [
                        Command.create(
                            self._line_vals(
                                amount_applied=1.0,
                                invoice_balance=1.0,
                                external_invoice_id="INV-FREEZE",
                            )
                        )
                    ]
                }
            )
        with self.assertRaises(UserError):
            allocation.write({"voucher_ids": [Command.delete(voucher.id)]})
        self.assertTrue(voucher.exists())
        self.assertEqual(allocation.voucher_ids, voucher)
        self.assertEqual(allocation.partner_id, partner)
        self.assertEqual(allocation.sheet_id, sheet)
        self.assertEqual(voucher.allocation_id, allocation)

    def test_draft_allocation_allows_membership_writes(self):
        """Triangulation: draft allocations MAY still change frozen fields."""
        allocation, voucher, sheet, partner = self._balanced_allocation(amount=80.0)
        extra = self._create_voucher(
            partner, sheet, amount=20.0, document_id="ALLOC-DRAFT-EXTRA"
        )
        self.assertEqual(allocation.state, "draft")
        allocation.write({"voucher_ids": [Command.link(extra.id)]})
        self.assertIn(extra, allocation.voucher_ids)
        self.assertIn(voucher, allocation.voucher_ids)
        extra_line = self._line_vals(
            amount_applied=1.0,
            invoice_balance=1.0,
            external_invoice_id="INV-DRAFT-LINE",
        )
        allocation.write({"line_ids": [Command.create(extra_line)]})
        self.assertTrue(
            allocation.line_ids.filtered(
                lambda line: line.external_invoice_id == "INV-DRAFT-LINE"
            )
        )

    def test_delete_command_unassigns_without_destroying_voucher(self):
        partner = self._partner("ALLOC-DELCMD")
        sheet = self._create_sheet()
        voucher = self._create_voucher(partner, sheet, amount=10.0)
        allocation = self._create_allocation(sheet, partner, vouchers=voucher)
        allocation.write({"voucher_ids": [Command.delete(voucher.id)]})
        self.assertTrue(voucher.exists())
        self.assertFalse(voucher.allocation_id)
        self.assertFalse(allocation.voucher_ids)

    def test_residual_zero_ok_on_draft_and_confirmed(self):
        allocation, voucher, _sheet, _partner = self._balanced_allocation(amount=100.0)
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(allocation.total_vouchers, 100.0)
        self.assertEqual(allocation.total_applied, 100.0)
        self.assertEqual(allocation.total_debt, 100.0)
        self.assertEqual(allocation.residual, 0.0)
        self.assertNotIn("residual_reason", allocation._fields)
        self.assertEqual(voucher.allocation_id, allocation)
        self._confirm(allocation)
        self.assertEqual(allocation.state, "confirmed")
        self.assertEqual(allocation.residual, 0.0)

    def test_residual_is_debt_minus_applied(self):
        """Residual MUST be total_debt − total_applied (150 − 40 = 110)."""
        partner = self._partner("ALLOC-RES")
        sheet = self._create_sheet()
        voucher = self._create_voucher(partner, sheet, amount=100.0)
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[self._line_vals(amount_applied=40.0, invoice_balance=150.0)],
        )
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(allocation.total_debt, 150.0)
        self.assertEqual(allocation.total_applied, 40.0)
        self.assertEqual(allocation.total_invoices, 150.0)
        self.assertEqual(allocation.total_quotations, 0.0)
        self.assertEqual(allocation.residual, 110.0)
        self.assertNotIn("residual_reason", allocation._fields)
        self._confirm(allocation)
        self.assertEqual(allocation.state, "confirmed")
        self.assertEqual(allocation.residual, 110.0)

    def test_applying_above_the_debt_is_refused_residual_stays_flat(self):
        """Applied exceeding the debt MUST be refused; a full apply leaves 0.

        This used to persist a negative residual. A document cannot be
        applied above its balance any more, so residual bottoms out at zero.
        """
        partner = self._partner("ALLOC-NEG")
        sheet = self._create_sheet()
        with self.assertRaises(ValidationError):
            self._create_allocation(
                sheet,
                partner,
                lines=[self._line_vals(amount_applied=80.0, invoice_balance=40.0)],
            )
        allocation = self._create_allocation(
            sheet,
            partner,
            lines=[self._line_vals(amount_applied=40.0, invoice_balance=40.0)],
        )
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(allocation.total_debt, 40.0)
        self.assertEqual(allocation.total_applied, 40.0)
        self.assertEqual(allocation.residual, 0.0)
        self.assertNotIn("residual_reason", allocation._fields)
        self._confirm(allocation)
        self.assertEqual(allocation.state, "confirmed")
        self.assertEqual(allocation.residual, 0.0)

    def test_totals_split_invoices_and_quotations(self):
        """total_invoices / total_quotations MUST split invoice_balance by kind."""
        partner = self._partner("ALLOC-KIND-TOT")
        sheet = self._create_sheet()
        allocation = self._create_allocation(
            sheet,
            partner,
            lines=[
                self._line_vals(
                    amount_applied=10.0,
                    invoice_balance=100.0,
                    document_kind="invoice",
                ),
                self._line_vals(
                    amount_applied=20.0,
                    invoice_balance=50.0,
                    document_kind="quotation",
                    external_invoice_id="QUO-1",
                    invoice_number="Q-1",
                ),
            ],
        )
        self.assertEqual(allocation.total_invoices, 100.0)
        self.assertEqual(allocation.total_quotations, 50.0)
        self.assertEqual(allocation.total_debt, 150.0)
        self.assertEqual(allocation.total_applied, 30.0)
        self.assertEqual(allocation.residual, 120.0)

    def test_validate_and_reject_are_gone(self):
        allocation, _voucher, _sheet, _partner = self._balanced_allocation()
        Alloc = type(self.env["collection.allocation"])
        self.assertFalse(hasattr(Alloc, "action_validate"))
        self.assertFalse(hasattr(Alloc, "action_reject"))
        states = {key for key, _label in allocation._fields["state"].selection}
        self.assertEqual(states, {"draft", "confirmed"})
        with self.assertRaises(UserError):
            allocation.write({"state": "confirmed"})
        self.assertEqual(allocation.state, "draft")
        with self.assertRaises(UserError):
            allocation.write({"state": "validated"})
        self.assertEqual(allocation.state, "draft")

    def test_request_fields_gated_and_request_id_unique(self):
        allocation, _voucher, sheet, _partner = self._balanced_allocation()
        with self.assertRaises(UserError):
            allocation.write({"request_id": "req-plain"})
        self._record_agent_request(allocation, "req-unique-1")
        self.assertEqual(allocation.request_id, "req-unique-1")
        other = self._create_allocation(sheet, self._partner("ALLOC-REQ-UNIQUE"))
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self._record_agent_request(other, "req-unique-1")
                other.flush_recordset()

    def test_draft_unlink_with_agent_request_unassigns_vouchers(self):
        """An agent-written draft allocation MUST delete like any other."""
        allocation, voucher, _sheet, _partner = self._balanced_allocation()
        line_ids = allocation.line_ids.ids
        self._record_agent_request(allocation, "req-draft-unlink")
        self.assertEqual(allocation.state, "draft")
        allocation.unlink()
        self.assertFalse(allocation.exists())
        self.assertFalse(
            self.env["collection.allocation.line"].browse(line_ids).exists()
        )
        self.assertFalse(voucher.allocation_id)

    def test_draft_unlink_unassigns_vouchers(self):
        """Triangulation: a plain draft allocation deletes too."""
        allocation, voucher, _sheet, _partner = self._balanced_allocation()
        line_ids = allocation.line_ids.ids
        allocation_id = allocation.id
        voucher_id = voucher.id
        allocation.unlink()
        self.assertFalse(
            self.env["collection.allocation"].browse(allocation_id).exists()
        )
        self.assertFalse(
            self.env["collection.allocation.line"].browse(line_ids).exists()
        )
        leftover = self.env["collection.voucher"].browse(voucher_id)
        self.assertTrue(leftover.exists())
        self.assertFalse(leftover.allocation_id)

    def test_confirmed_unlink_refused(self):
        allocation, voucher, _sheet, _partner = self._balanced_allocation()
        self._confirm(allocation)
        allocation_id = allocation.id
        with self.assertRaises(UserError):
            allocation.unlink()
        leftover = self.env["collection.allocation"].browse(allocation_id)
        self.assertTrue(leftover.exists())
        self.assertEqual(leftover.state, "confirmed")
        self.assertEqual(voucher.allocation_id, leftover)

    def test_iff_constraint_skips_under_audited_context(self):
        allocation, _voucher, sheet, _partner = self._balanced_allocation()
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(sheet.state, "open")
        with self.assertRaises(UserError):
            allocation.write({"state": "confirmed"})
        self.assertEqual(allocation.state, "draft")
        self._confirm(allocation)
        self.assertEqual(allocation.state, "confirmed")
        self.assertEqual(sheet.state, "open")
        with self.assertRaises(ValidationError):
            allocation._check_sheet_state_iff()
        force_sheet_state(sheet, "closed")
        allocation._check_sheet_state_iff()
        self.assertEqual(allocation.state, "confirmed")
        self.assertEqual(sheet.state, "closed")

    def test_iff_matching_draft_on_open_passes(self):
        """Triangulation: draft on an open sheet MUST satisfy the iff constrain."""
        allocation, _voucher, sheet, _partner = self._balanced_allocation()
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(sheet.state, "open")
        allocation._check_sheet_state_iff()

    def test_iff_draft_on_proposal_passes(self):
        """draft MUST hold iff the sheet is open, proposal, or cancelled."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        with privileged("collection_audited_state"):
            voucher.write({"state": "validated_collections"})
        confirm_sheet(sheet)
        self.assertEqual(sheet.state, "proposal")
        self.assertEqual(allocation.state, "draft")
        allocation._check_sheet_state_iff()

    def test_iff_draft_on_submitted_passes(self):
        """draft MUST hold iff the sheet is open, submitted, proposal, or cancelled."""
        allocation, _voucher, sheet, _partner = self._balanced_allocation()
        force_sheet_state(sheet, "submitted")
        self.assertEqual(sheet.state, "submitted")
        self.assertEqual(allocation.state, "draft")
        allocation._check_sheet_state_iff()

    def test_create_draft_allocation_on_submitted(self):
        """Triangulation: ORM create on a submitted sheet MUST persist draft."""
        partner = self._partner("ALLOC-SUB-CRT")
        sheet = self._create_sheet()
        voucher = self._create_voucher(partner, sheet, amount=60.0)
        force_sheet_state(sheet, "submitted")
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[self._line_vals(amount_applied=60.0, invoice_balance=60.0)],
        )
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(sheet.state, "submitted")
        allocation._check_sheet_state_iff()

    def test_draft_state_error_names_submitted(self):
        """A draft-versus-confirmed pairing error MUST name submitted."""
        allocation, _voucher, sheet, _partner = self._balanced_allocation()
        force_sheet_state(sheet, "closed")
        self.assertEqual(allocation.state, "draft")
        with self.assertRaises(ValidationError) as error:
            allocation._check_sheet_state_iff()
        self.assertIn("submitted", str(error.exception))

    def test_iff_draft_on_cancelled_passes(self):
        """Triangulation: draft on cancelled MUST satisfy the iff constraint."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        with privileged("collection_audited_state"):
            voucher.write({"state": "validated_collections"})
        confirm_sheet(sheet)
        sheet.action_cancel()
        self.assertEqual(sheet.state, "cancelled")
        self.assertEqual(allocation.state, "draft")
        allocation._check_sheet_state_iff()

    def test_close_from_proposal_confirms_then_closes(self):
        """Close MUST confirm every allocation then close the sheet."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        with privileged("collection_audited_state"):
            voucher.write({"state": "validated_collections"})
        confirm_sheet(sheet)
        self.assertEqual(allocation.state, "draft")
        sheet.action_close()
        self.assertEqual(sheet.state, "closed")
        self.assertEqual(allocation.state, "confirmed")
        allocation._check_sheet_state_iff()

    def test_cancel_from_proposal_drafts_allocations(self):
        """Cancel MUST return every allocation to draft (no-op if already draft)."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        with privileged("collection_audited_state"):
            voucher.write({"state": "validated_collections"})
        confirm_sheet(sheet)
        sheet.action_cancel()
        self.assertEqual(sheet.state, "cancelled")
        self.assertEqual(allocation.state, "draft")
        allocation._check_sheet_state_iff()

    def test_cancel_from_closed_drafts_allocations(self):
        """Triangulation: Cancel from closed MUST draft confirmed allocations."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        with privileged("collection_audited_state"):
            voucher.write({"state": "validated_collections"})
        confirm_sheet(sheet)
        sheet.action_close()
        self.assertEqual(allocation.state, "confirmed")
        sheet.action_cancel()
        self.assertEqual(sheet.state, "cancelled")
        self.assertEqual(allocation.state, "draft")
        allocation._check_sheet_state_iff()

    def test_open_from_cancelled_leaves_draft(self):
        """Open from cancelled MUST leave allocations draft."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        with privileged("collection_audited_state"):
            voucher.write({"state": "validated_collections"})
        confirm_sheet(sheet)
        sheet.action_cancel()
        sheet.action_reinstate()
        self.assertEqual(sheet.state, "submitted")
        self.assertEqual(allocation.state, "draft")
        allocation._check_sheet_state_iff()

    def test_confirm_does_not_confirm_allocations(self):
        """Confirm MUST NOT change allocation state."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        with privileged("collection_audited_state"):
            voucher.write({"state": "validated_collections"})
        self.assertEqual(allocation.state, "draft")
        confirm_sheet(sheet)
        self.assertEqual(sheet.state, "proposal")
        self.assertEqual(allocation.state, "draft")
        allocation._check_sheet_state_iff()

    def test_allocation_id_write_on_draft_or_unset(self):
        """Write of allocation_id MUST succeed when current and target are draft
        or unset.
        """
        partner = self._partner("ALLOC-WRITE")
        sheet = self._create_sheet()
        voucher = self._create_voucher(partner, sheet, amount=40.0)
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            residual_reason="on_account",
        )
        self.assertEqual(allocation.state, "draft")
        voucher.write({"allocation_id": False})
        self.assertFalse(voucher.allocation_id)
        voucher.write({"allocation_id": allocation.id})
        self.assertEqual(voucher.allocation_id, allocation)

    def test_confirmed_membership_write_refused(self):
        """Write of allocation_id MUST be refused when current or target is
        confirmed.
        """
        partner = self._partner("ALLOC-WRITE-CONF")
        sheet = self._create_sheet()
        voucher = self._create_voucher(partner, sheet, amount=40.0)
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            residual_reason="on_account",
        )
        self._confirm(allocation)
        stored = voucher.allocation_id
        with self.assertRaises(UserError):
            voucher.write({"allocation_id": False})
        self.assertEqual(voucher.allocation_id, stored)
        outsider = self._create_voucher(
            partner, sheet, amount=10.0, document_id="ALLOC-WRITE-OUT"
        )
        with self.assertRaises(UserError):
            outsider.write({"allocation_id": allocation.id})
        self.assertFalse(outsider.allocation_id)

    def test_pending_unlink_on_draft_allowed_when_residual_holds(self):
        """Pending unlink on draft MUST succeed when projected residual stays ≥ 0."""
        partner = self._partner("ALLOC-UNL-DRAFT")
        sheet = self._create_sheet()
        voucher = self._create_voucher(partner, sheet, amount=40.0)
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[self._line_vals(amount_applied=0.0, invoice_balance=40.0)],
        )
        self.assertEqual(voucher.state, "draft")
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(allocation.residual, 40.0)
        voucher_id = voucher.id
        voucher.unlink()
        self.assertFalse(self.env["collection.voucher"].browse(voucher_id).exists())
        self.assertFalse(allocation.voucher_ids)

    def test_pending_unlink_on_confirmed_refused(self):
        """Pending plus confirmed MUST refuse unlink; voucher and allocation remain."""
        allocation, voucher, _sheet, _partner = self._balanced_allocation()
        self._confirm(allocation)
        self.assertEqual(voucher.state, "draft")
        voucher_id = voucher.id
        with self.assertRaises(UserError):
            voucher.unlink()
        leftover = self.env["collection.voucher"].browse(voucher_id)
        self.assertTrue(leftover.exists())
        self.assertEqual(leftover.allocation_id, allocation)

    def test_pending_unlink_on_draft_at_residual_zero_succeeds(self):
        """Draft unlink at residual 0 MUST succeed; lines and residual stay."""
        allocation, voucher, _sheet, _partner = self._balanced_allocation()
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(allocation.residual, 0.0)
        line_before = [
            (line.id, line.amount_applied, line.external_invoice_id)
            for line in allocation.line_ids
        ]
        self.assertTrue(line_before)
        voucher_id = voucher.id
        voucher.unlink()
        self.assertFalse(self.env["collection.voucher"].browse(voucher_id).exists())
        self.assertFalse(allocation.voucher_ids)
        self.assertEqual(allocation.residual, 0.0)
        allocation.invalidate_recordset(["line_ids"])
        self.assertEqual(
            [
                (line.id, line.amount_applied, line.external_invoice_id)
                for line in allocation.line_ids
            ],
            line_before,
        )

    def test_unallocated_pending_voucher_unlink_still_allowed(self):
        partner = self._partner("ALLOC-UNL-OK")
        sheet = self._create_sheet()
        voucher = self._create_voucher(partner, sheet, amount=12.0)
        self.assertFalse(voucher.allocation_id)
        voucher_id = voucher.id
        voucher.unlink()
        self.assertFalse(self.env["collection.voucher"].browse(voucher_id).exists())

    def test_zero_applied_line_persists(self):
        """amount_applied 0 MUST persist; residual stays the invoice balance."""
        partner = self._partner("ALLOC-LINE")
        sheet = self._create_sheet()
        allocation = self._create_allocation(
            sheet,
            partner,
            lines=[self._line_vals(amount_applied=0.0, invoice_balance=10.0)],
        )
        self.assertEqual(len(allocation.line_ids), 1)
        self.assertEqual(allocation.line_ids.amount_applied, 0.0)
        self.assertEqual(allocation.total_debt, 10.0)
        self.assertEqual(allocation.total_applied, 0.0)
        self.assertEqual(allocation.residual, 10.0)
        omitted = self._line_vals(
            invoice_balance=5.0,
            external_invoice_id="INV-DEFAULT-0",
        )
        omitted.pop("amount_applied")
        defaulted = self._create_allocation(
            sheet,
            self._partner("ALLOC-LINE-DEF"),
            lines=[omitted],
        )
        self.assertEqual(defaulted.line_ids.amount_applied, 0.0)

    def test_negative_amount_applied_rejected(self):
        """CHECK amount_applied >= 0 MUST reject a negative applied amount."""
        partner = self._partner("ALLOC-LINE-NEG")
        sheet = self._create_sheet()
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self._create_allocation(
                    sheet,
                    partner,
                    lines=[self._line_vals(amount_applied=-1.0, invoice_balance=10.0)],
                )

    def test_related_stored_currency_and_company_on_line(self):
        allocation, _voucher, sheet, _partner = self._balanced_allocation()
        line = allocation.line_ids
        self.assertEqual(line.currency_id, allocation.currency_id)
        self.assertEqual(line.company_id, sheet.company_id)
        line_company = self.env["collection.allocation.line"]._fields["company_id"]
        self.assertTrue(line_company.store)
        self.assertTrue(line_company.required)
        self.assertTrue(line_company.precompute)

    def test_fully_applied_source_detach_via_partner_write_succeeds(self):
        """Allocated partner write MUST refuse even when residual is 0."""
        allocation, voucher, _sheet, partner = self._balanced_allocation()
        other = self._partner("ALLOC-DETACH-Q")
        self.assertEqual(allocation.residual, 0.0)
        with self.assertRaises(UserError) as err:
            voucher.write({"partner_id": other.id})
        self.assertIn("must match the allocation customer", str(err.exception))
        self.assertEqual(voucher.partner_id, partner)
        self.assertEqual(voucher.allocation_id, allocation)
        self.assertEqual(allocation.residual, 0.0)
        self.assertIn(voucher, allocation.voucher_ids)

    def test_leftover_less_than_amount_detach_succeeds(self):
        """Allocated partner write MUST refuse when residual is below the voucher."""
        partner = self._partner("ALLOC-PROJ-P")
        sheet = self._create_sheet()
        voucher = self._create_voucher(partner, sheet, amount=100.0)
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[self._line_vals(amount_applied=60.0, invoice_balance=100.0)],
        )
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(allocation.residual, 40.0)
        residual_before = allocation.residual
        other = self._partner("ALLOC-PROJ-Q")
        with self.assertRaises(UserError) as err:
            voucher.write({"partner_id": other.id})
        self.assertIn("must match the allocation customer", str(err.exception))
        self.assertEqual(allocation.residual, residual_before)
        self.assertEqual(voucher.allocation_id, allocation)
        self.assertEqual(voucher.partner_id, partner)
        self.assertIn(voucher, allocation.voucher_ids)

    def test_voucher_partner_write_mismatch_without_matching_allocation_refused(self):
        """Partner Q with the source allocation still in vals MUST refuse."""
        allocation, voucher, _sheet, partner = self._balanced_allocation()
        other = self._partner("ALLOC-MISMATCH-Q")
        with self.assertRaises(UserError):
            voucher.write({"partner_id": other.id, "allocation_id": allocation.id})
        self.assertEqual(voucher.partner_id, partner)
        self.assertEqual(voucher.allocation_id, allocation)

    def test_same_write_matching_partner_and_allocation_holds(self):
        """Same-vals partner Q + draft allocation B MUST keep partner match."""
        partner_p = self._partner("ALLOC-SAME-P")
        partner_q = self._partner("ALLOC-SAME-Q")
        sheet = self._create_sheet()
        voucher = self._create_voucher(partner_p, sheet, amount=50.0)
        allocation_a = self._create_allocation(
            sheet,
            partner_p,
            vouchers=voucher,
            lines=[self._line_vals(amount_applied=0.0, invoice_balance=50.0)],
        )
        allocation_b = self._create_allocation(
            sheet,
            partner_q,
            lines=[
                self._line_vals(
                    amount_applied=0.0,
                    invoice_balance=50.0,
                    external_invoice_id="INV-B",
                )
            ],
        )
        voucher.write({"partner_id": partner_q.id, "allocation_id": allocation_b.id})
        self.assertEqual(voucher.partner_id, partner_q)
        self.assertEqual(voucher.allocation_id, allocation_b)
        self.assertIn(voucher, allocation_b.voucher_ids)
        self.assertNotIn(voucher, allocation_a.voucher_ids)

    def test_confirmed_source_partner_write_refused(self):
        """Confirmed source MUST refuse partner_id write with no field change."""
        allocation, voucher, _sheet, partner = self._balanced_allocation()
        self._confirm(allocation)
        other = self._partner("ALLOC-CONF-SRC-Q")
        with self.assertRaises(UserError):
            voucher.write({"partner_id": other.id})
        self.assertEqual(voucher.partner_id, partner)
        self.assertEqual(voucher.allocation_id, allocation)

    def test_prepare_customer_debt_lines_snapshots_outstanding_zeros(self):
        """Helper MUST map every outstanding ERP invoice with amount_applied 0."""
        seller = self._seller()
        partner = dummy_customer_partner(self.env, customer=ERP_CUSTOMER_IDENT)
        sheet = self._create_sheet(seller_id=seller.id)
        self._bind_erp_customer(partner, seller)
        Allocation = self.env["collection.allocation"]
        rows = Allocation._prepare_customer_debt_lines(sheet, partner)
        self.assertEqual(
            {row["external_invoice_id"] for row in rows},
            ERP_OUTSTANDING_IDS,
        )
        self.assertGreaterEqual(len(rows), 2)
        for row in rows:
            self.assertEqual(row["amount_applied"], 0.0)
            self.assertEqual(row["document_kind"], "invoice")
            self.assertTrue(row["invoice_number"])
            self.assertGreater(row["invoice_balance"], 0.0)

    def test_prepare_customer_debt_lines_empty_without_connector(self):
        """Missing connector MUST yield empty lines and MUST NOT raise UserError."""
        seller = self._seller()
        partner = dummy_customer_partner(self.env, customer="ALLOC-NO-CONN")
        sheet = self._create_sheet(seller_id=seller.id)
        self.env.company.write({"collection_connector_id": False})
        Allocation = self.env["collection.allocation"]
        rows = Allocation._prepare_customer_debt_lines(sheet, partner)
        self.assertEqual(rows, [])

    def test_prepare_customer_debt_lines_empty_without_binding(self):
        """Missing customer binding MUST yield empty lines and MUST NOT raise."""
        seller = self._seller()
        partner = dummy_customer_partner(self.env, customer="ALLOC-NO-BIND")
        sheet = self._create_sheet(seller_id=seller.id)
        install_test_connector_type(self)
        install_bound_test_connector(self, seller)
        Allocation = self.env["collection.allocation"]
        rows = Allocation._prepare_customer_debt_lines(sheet, partner)
        self.assertEqual(rows, [])

    def test_prepare_customer_debt_lines_swallows_erp_usererror(self):
        """ERP UserError from get_customer_debt MUST become empty lines."""
        seller = self._seller()
        partner = dummy_customer_partner(self.env, customer="ALLOC-ERP-ERR")
        sheet = self._create_sheet(seller_id=seller.id)
        self._bind_erp_customer(partner, seller, identification="NO-SUCH-CUSTOMER")
        Allocation = self.env["collection.allocation"]
        rows = Allocation._prepare_customer_debt_lines(sheet, partner)
        self.assertEqual(rows, [])

    def test_prepare_customer_debt_lines_never_calls_active_connector(self):
        """Helper MUST NOT call _collection_active_connector()."""
        seller = self._seller()
        partner = dummy_customer_partner(self.env, customer=ERP_CUSTOMER_IDENT)
        sheet = self._create_sheet(seller_id=seller.id)
        self._bind_erp_customer(partner, seller)
        Allocation = self.env["collection.allocation"]
        source = inspect.getsource(Allocation._prepare_customer_debt_lines)
        self.assertNotIn("_collection_active_connector", source)
        with patch.object(
            type(self.env.company),
            "_collection_active_connector",
            side_effect=AssertionError("must not call _collection_active_connector"),
        ):
            rows = Allocation._prepare_customer_debt_lines(sheet, partner)
        self.assertEqual(
            {row["external_invoice_id"] for row in rows},
            ERP_OUTSTANDING_IDS,
        )

    def test_onchange_replaces_lines_on_draft(self):
        """Draft Customer/Sheet onchange MUST replace line_ids with the snapshot."""
        seller = self._seller()
        partner = dummy_customer_partner(self.env, customer=ERP_CUSTOMER_IDENT)
        sheet = self._create_sheet(seller_id=seller.id)
        self._bind_erp_customer(partner, seller)
        record = self.env["collection.allocation"].new(
            {
                "sheet_id": sheet.id,
                "partner_id": partner.id,
                "state": "draft",
                "line_ids": [
                    Command.create(
                        self._line_vals(
                            external_invoice_id="OLD-LINE",
                            amount_applied=0,
                        )
                    )
                ],
            }
        )
        self.assertEqual(record.line_ids.external_invoice_id, "OLD-LINE")
        record._onchange_customer_debt_lines()
        self.assertEqual(
            set(record.line_ids.mapped("external_invoice_id")),
            ERP_OUTSTANDING_IDS,
        )
        self.assertTrue(
            all(line.amount_applied == 0.0 for line in record.line_ids),
        )

    def test_onchange_skips_when_confirmed(self):
        """Confirmed onchange MUST leave line_ids unchanged."""
        seller = self._seller()
        partner = dummy_customer_partner(self.env, customer=ERP_CUSTOMER_IDENT)
        sheet = self._create_sheet(seller_id=seller.id)
        self._bind_erp_customer(partner, seller)
        record = self.env["collection.allocation"].new(
            {
                "sheet_id": sheet.id,
                "partner_id": partner.id,
                "state": "confirmed",
                "line_ids": [
                    Command.create(
                        self._line_vals(
                            external_invoice_id="KEEP-LINE",
                            amount_applied=5,
                        )
                    )
                ],
            }
        )
        record._onchange_customer_debt_lines()
        self.assertEqual(record.line_ids.external_invoice_id, "KEEP-LINE")
        self.assertEqual(record.line_ids.amount_applied, 5.0)

    def test_onchange_empty_when_unbound_partner(self):
        """Draft onchange with no binding MUST clear lines without UserError."""
        seller = self._seller()
        partner = dummy_customer_partner(self.env, customer="ALLOC-ONC-UNBOUND")
        sheet = self._create_sheet(seller_id=seller.id)
        install_test_connector_type(self)
        install_bound_test_connector(self, seller)
        record = self.env["collection.allocation"].new(
            {
                "sheet_id": sheet.id,
                "partner_id": partner.id,
                "state": "draft",
                "line_ids": [
                    Command.create(
                        self._line_vals(
                            external_invoice_id="WIPE-ME",
                            amount_applied=0,
                        )
                    )
                ],
            }
        )
        record._onchange_customer_debt_lines()
        self.assertFalse(record.line_ids)

    def test_create_omitted_line_ids_snapshots(self):
        """create MUST snapshot outstanding debt when line_ids is omitted."""
        seller = self._seller()
        partner = dummy_customer_partner(self.env, customer=ERP_CUSTOMER_IDENT)
        sheet = self._create_sheet(seller_id=seller.id)
        self._bind_erp_customer(partner, seller)
        allocation = self.env["collection.allocation"].create(
            {
                "sheet_id": sheet.id,
                "partner_id": partner.id,
            }
        )
        self.assertEqual(
            set(allocation.line_ids.mapped("external_invoice_id")),
            ERP_OUTSTANDING_IDS,
        )
        self.assertTrue(
            all(line.amount_applied == 0.0 for line in allocation.line_ids),
        )
        self.assertTrue(
            all(line.document_kind == "invoice" for line in allocation.line_ids),
        )

    def test_create_supplied_line_ids_skips_snapshot(self):
        """create MUST persist supplied lines without a second ERP fetch."""
        seller = self._seller()
        partner = dummy_customer_partner(self.env, customer=ERP_CUSTOMER_IDENT)
        sheet = self._create_sheet(seller_id=seller.id)
        self._bind_erp_customer(partner, seller)
        allocation = self._create_allocation(
            sheet,
            partner,
            lines=[
                self._line_vals(
                    external_invoice_id="SUPPLIED-ONLY",
                    invoice_number="S-1",
                    amount_applied=0.0,
                    invoice_balance=9.0,
                )
            ],
        )
        self.assertEqual(len(allocation.line_ids), 1)
        self.assertEqual(allocation.line_ids.external_invoice_id, "SUPPLIED-ONLY")
        self.assertNotIn(
            "inv-bound-overdue",
            allocation.line_ids.mapped("external_invoice_id"),
        )

    def test_voucher_count_matches_linked_vouchers(self):
        """voucher_count MUST be a non-stored count of allocation.voucher_ids."""
        field = self.env["collection.allocation"]._fields["voucher_count"]
        self.assertTrue(field.compute)
        self.assertFalse(field.store)
        allocation, voucher, sheet, partner = self._balanced_allocation(amount=40.0)
        self.assertEqual(allocation.voucher_count, 1)
        extra = self._create_voucher(
            partner, sheet, amount=10.0, document_id="ALLOC-VC-EXTRA"
        )
        extra.write({"allocation_id": allocation.id})
        self.assertEqual(allocation.voucher_count, 2)
        empty = self._create_allocation(
            sheet,
            self._partner("ALLOC-VC-EMPTY"),
            lines=[self._line_vals(amount_applied=0.0, invoice_balance=1.0)],
        )
        self.assertEqual(empty.voucher_count, 0)

    def test_action_open_vouchers_domain_is_allocation_id(self):
        """Saved allocation MUST open vouchers filtered by allocation_id."""
        allocation, _voucher, _sheet, _partner = self._balanced_allocation()
        action = allocation.action_open_vouchers()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "collection.voucher")
        self.assertEqual(action["view_mode"], "list,kanban,form")
        self.assertEqual(action["domain"], [("allocation_id", "=", allocation.id)])
        self.assertFalse(action.get("path"))
        other = self._create_allocation(
            allocation.sheet_id,
            self._partner("ALLOC-BTN-B"),
            lines=[
                self._line_vals(
                    amount_applied=0.0,
                    invoice_balance=1.0,
                    external_invoice_id="INV-BTN-B",
                )
            ],
        )
        self.assertEqual(
            other.action_open_vouchers()["domain"],
            [("allocation_id", "=", other.id)],
        )

    def test_action_open_vouchers_refused_on_new_id(self):
        """Unsaved allocation NewId MUST refuse action_open_vouchers."""
        unsaved = self.env["collection.allocation"].new(
            {
                "sheet_id": self._create_sheet().id,
                "partner_id": self._partner("ALLOC-UNSAVED").id,
            }
        )
        self.assertFalse(isinstance(unsaved.id, int))
        with self.assertRaises(UserError):
            unsaved.action_open_vouchers()

    def test_line_related_stored_sheet_id_and_partner_id(self):
        """Allocation lines MUST store related sheet_id and readonly partner_id."""
        allocation, _voucher, sheet, partner = self._balanced_allocation()
        line = allocation.line_ids
        self.assertEqual(len(line), 1)
        self.assertEqual(line.sheet_id, sheet)
        self.assertEqual(line.partner_id, partner)
        sheet_field = line._fields["sheet_id"]
        partner_field = line._fields["partner_id"]
        self.assertTrue(sheet_field.store)
        self.assertTrue(partner_field.store)
        self.assertEqual(sheet_field.related, "allocation_id.sheet_id")
        self.assertEqual(partner_field.related, "allocation_id.partner_id")
        self.assertTrue(partner_field.readonly)
        self.assertIn(line, sheet.debt_line_ids)

    def test_line_relateds_follow_second_partner(self):
        """Triangulation: a second allocation's lines MUST keep that partner/sheet."""
        _first, _voucher, sheet, _partner = self._balanced_allocation(amount=50.0)
        other_partner = self._partner("ALLOC-LINE-REL-B")
        other_voucher = self._create_voucher(other_partner, sheet, amount=25.0)
        other = self._create_allocation(
            sheet,
            other_partner,
            vouchers=other_voucher,
            lines=[
                self._line_vals(
                    amount_applied=25.0,
                    invoice_balance=25.0,
                    external_invoice_id="INV-LINE-REL-B",
                )
            ],
        )
        line = other.line_ids.filtered(
            lambda row: row.external_invoice_id == "INV-LINE-REL-B"
        )
        self.assertEqual(len(line), 1)
        self.assertEqual(line.sheet_id, sheet)
        self.assertEqual(line.partner_id, other_partner)
        self.assertIn(line, sheet.debt_line_ids)
        self.assertEqual(
            set(sheet.debt_line_ids.partner_id.ids),
            set(sheet.allocation_ids.partner_id.ids),
        )

    def test_cancelled_draft_line_write_refused(self):
        """Cancelled draft lines MUST refuse amount_applied writes."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        self._mark_validated(voucher)
        confirm_sheet(sheet)
        sheet.action_cancel()
        self.assertEqual(sheet.state, "cancelled")
        self.assertEqual(allocation.state, "draft")
        line = allocation.line_ids
        original = line.amount_applied
        with self.assertRaises(UserError):
            line.write({"amount_applied": original + 1.0})
        self.assertEqual(line.amount_applied, original)
        with self.assertRaises(UserError):
            allocation.write(
                {
                    "line_ids": [
                        Command.update(line.id, {"amount_applied": original + 1.0})
                    ]
                }
            )
        self.assertEqual(line.amount_applied, original)

    def test_closed_allocation_writes_refused(self):
        """Closed sheets MUST refuse line, voucher, partner, and sheet writes."""
        allocation, voucher, sheet, partner = self._balanced_allocation()
        outsider = self._create_voucher(
            partner, sheet, amount=10.0, document_id="ALLOC-CLOSED-OUT"
        )
        self._mark_validated(voucher, outsider)
        confirm_sheet(sheet)
        sheet.action_close()
        self.assertEqual(sheet.state, "closed")
        self.assertEqual(allocation.state, "confirmed")
        line = allocation.line_ids
        original = line.amount_applied
        with self.assertRaises(UserError):
            line.write({"amount_applied": original + 1.0})
        self.assertEqual(line.amount_applied, original)
        with self.assertRaises(UserError):
            allocation.write({"voucher_ids": [Command.link(outsider.id)]})
        with self.assertRaises(UserError):
            allocation.write({"partner_id": self._partner("ALLOC-CLOSED-P").id})
        other_seller = create_internal_seller(self.env, "alloc_closed_other")
        other_sheet = self._create_sheet(seller_id=other_seller.id, force_new=True)
        with self.assertRaises(UserError):
            allocation.write({"sheet_id": other_sheet.id})
        self.assertEqual(allocation.voucher_ids, voucher)
        self.assertEqual(allocation.partner_id, partner)
        self.assertEqual(allocation.sheet_id, sheet)
        self.assertEqual(line.amount_applied, original)

    def test_frozen_sheet_refuses_allocation_create(self):
        """Closed and cancelled sheets MUST refuse allocation create with no persist."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        self._mark_validated(voucher)
        confirm_sheet(sheet)
        sheet.action_close()
        self.assertEqual(sheet.state, "closed")
        other = self._partner("ALLOC-FRZ-CREATE")
        with self.assertRaises(UserError):
            self._create_allocation(sheet, other)
        leftover = self.env["collection.allocation"].search(
            [("sheet_id", "=", sheet.id), ("partner_id", "=", other.id)]
        )
        self.assertFalse(leftover)
        sheet.action_cancel()
        self.assertEqual(sheet.state, "cancelled")
        cancelled_partner = self._partner("ALLOC-FRZ-CAN")
        with self.assertRaises(UserError):
            self._create_allocation(sheet, cancelled_partner)
        self.assertFalse(
            self.env["collection.allocation"].search(
                [("sheet_id", "=", sheet.id), ("partner_id", "=", cancelled_partner.id)]
            )
        )
        self.assertEqual(allocation.sheet_id, sheet)

    def test_frozen_sheet_refuses_line_create(self):
        """Closed sheets MUST refuse allocation line create with no persist."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        self._mark_validated(voucher)
        confirm_sheet(sheet)
        sheet.action_close()
        before = allocation.line_ids
        line_vals = self._line_vals(
            amount_applied=1.0,
            invoice_balance=1.0,
            external_invoice_id="INV-FRZ-CREATE",
        )
        line_vals["allocation_id"] = allocation.id
        with self.assertRaises(UserError):
            self.env["collection.allocation.line"].create(line_vals)
        allocation.invalidate_recordset(["line_ids"])
        self.assertEqual(allocation.line_ids, before)

    def test_proposal_still_allows_allocation_create(self):
        """Proposal sheets MUST still persist a lawful allocation create."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        other = self._partner("ALLOC-PROP-CREATE")
        extra_voucher = self._create_voucher(
            other, sheet, amount=15.0, document_id="ALLOC-PROP-CREATE-V"
        )
        self._mark_validated(voucher, extra_voucher)
        confirm_sheet(sheet)
        self.assertEqual(sheet.state, "proposal")
        extra = self._create_allocation(
            sheet,
            other,
            vouchers=extra_voucher,
            lines=[
                self._line_vals(
                    amount_applied=15.0,
                    invoice_balance=15.0,
                    external_invoice_id="INV-PROP-CREATE",
                )
            ],
        )
        self.assertTrue(extra.id)
        self.assertEqual(extra.state, "draft")
        self.assertEqual(extra.sheet_id, sheet)
        self.assertEqual(allocation.state, "draft")

    def test_proposal_draft_line_and_voucher_writes_persist(self):
        """Triangulation: proposal draft allocations MUST remain writable."""
        allocation, voucher, sheet, partner = self._balanced_allocation(amount=80.0)
        extra = self._create_voucher(
            partner, sheet, amount=20.0, document_id="ALLOC-PROP-EXTRA"
        )
        self._mark_validated(voucher, extra)
        confirm_sheet(sheet)
        self.assertEqual(sheet.state, "proposal")
        self.assertEqual(allocation.state, "draft")
        line = allocation.line_ids
        line.write({"amount_applied": 40.0})
        self.assertEqual(line.amount_applied, 40.0)
        allocation.write({"voucher_ids": [Command.link(extra.id)]})
        self.assertIn(extra, allocation.voucher_ids)
        self.assertIn(voucher, allocation.voucher_ids)

    def test_submitted_draft_line_and_voucher_writes_persist(self):
        """Submitted draft allocations MUST remain writable."""
        allocation, voucher, sheet, partner = self._balanced_allocation(amount=80.0)
        extra = self._create_voucher(
            partner, sheet, amount=20.0, document_id="ALLOC-SUB-EXTRA"
        )
        self._mark_validated(voucher, extra)
        sheet.action_seller_close()
        self.assertEqual(sheet.state, "submitted")
        self.assertEqual(allocation.state, "draft")
        line = allocation.line_ids
        line.write({"amount_applied": 40.0})
        self.assertEqual(line.amount_applied, 40.0)
        allocation.write({"voucher_ids": [Command.link(extra.id)]})
        self.assertIn(extra, allocation.voucher_ids)
        self.assertIn(voucher, allocation.voucher_ids)

    def test_cancelled_line_unlink_refused(self):
        """Debt lines on a cancelled sheet MUST refuse unlink."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        self._mark_validated(voucher)
        confirm_sheet(sheet)
        sheet.action_cancel()
        self.assertEqual(sheet.state, "cancelled")
        line = allocation.line_ids
        line_id = line.id
        with self.assertRaises(UserError):
            line.unlink()
        leftover = self.env["collection.allocation.line"].browse(line_id)
        self.assertTrue(leftover.exists())
        self.assertEqual(leftover.allocation_id, allocation)

    def test_closed_line_unlink_refused(self):
        """Triangulation: debt lines on a closed sheet MUST refuse unlink."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        self._mark_validated(voucher)
        confirm_sheet(sheet)
        sheet.action_close()
        self.assertEqual(sheet.state, "closed")
        line = allocation.line_ids
        line_id = line.id
        with self.assertRaises(UserError):
            line.unlink()
        leftover = self.env["collection.allocation.line"].browse(line_id)
        self.assertTrue(leftover.exists())
        self.assertEqual(leftover.allocation_id, allocation)

    def test_freeze_rejects_receipt_ids_when_confirmed(self):
        """Confirmed allocations MUST refuse receipt_ids create and unlink."""
        allocation, voucher, _sheet, _partner = self._balanced_allocation()
        receipt = self._create_receipt(allocation, "invoice")
        self._create_value(receipt, voucher, 100.0)
        self._confirm(allocation)
        self.assertEqual(allocation.state, "confirmed")
        receipt_id = receipt.id
        with self.assertRaises(UserError):
            allocation.write(
                {"receipt_ids": [Command.create({"document_kind": "quotation"})]}
            )
        with self.assertRaises(UserError):
            allocation.write({"receipt_ids": [Command.unlink(receipt.id)]})
        leftover_receipt = self.env["collection.receipt"].browse(receipt_id)
        self.assertTrue(leftover_receipt.exists())
        self.assertEqual(allocation.receipt_ids, leftover_receipt)
        self.assertEqual(leftover_receipt.document_kind, "invoice")
        self.assertEqual(len(leftover_receipt.value_ids), 1)

    def test_draft_allocation_allows_receipt_ids_writes(self):
        """Triangulation: draft allocations MAY still write receipt_ids."""
        allocation, voucher, _sheet, _partner = self._balanced_allocation()
        self.assertEqual(allocation.state, "draft")
        allocation.write(
            {"receipt_ids": [Command.create({"document_kind": "invoice"})]}
        )
        receipt = allocation.receipt_ids
        self.assertEqual(len(receipt), 1)
        self.assertEqual(receipt.document_kind, "invoice")
        self._create_value(receipt, voucher, 100.0)
        allocation.write({"receipt_ids": [Command.delete(receipt.id)]})
        self.assertFalse(allocation.receipt_ids)
        self.assertFalse(receipt.exists())

    def test_closed_allocation_receipt_ids_writes_refused(self):
        """Closed sheets MUST refuse receipt_ids writes; stored receipts stay."""
        seller = self._seller()
        install_test_connector_type(self)
        install_bound_test_connector(self, seller)
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        receipt = self._create_receipt(allocation, "invoice")
        self._create_value(receipt, voucher, 100.0)
        self._mark_validated(voucher)
        confirm_sheet(sheet)
        sheet.action_close()
        self.assertEqual(sheet.state, "closed")
        self.assertEqual(allocation.state, "confirmed")
        receipt_id = receipt.id
        with self.assertRaises(UserError):
            allocation.write(
                {"receipt_ids": [Command.create({"document_kind": "quotation"})]}
            )
        with self.assertRaises(UserError):
            allocation.write({"receipt_ids": [Command.unlink(receipt.id)]})
        leftover_receipt = self.env["collection.receipt"].browse(receipt_id)
        self.assertTrue(leftover_receipt.exists())
        self.assertEqual(allocation.receipt_ids, leftover_receipt)
        self.assertEqual(leftover_receipt.document_kind, "invoice")

    def test_cancelled_allocation_receipt_ids_writes_refused(self):
        """Triangulation: cancelled draft allocations MUST refuse receipt_ids."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        receipt = self._create_receipt(allocation, "invoice")
        self._create_value(receipt, voucher, 100.0)
        self._mark_validated(voucher)
        confirm_sheet(sheet)
        sheet.action_cancel()
        self.assertEqual(sheet.state, "cancelled")
        self.assertEqual(allocation.state, "draft")
        receipt_id = receipt.id
        with self.assertRaises(UserError):
            allocation.write(
                {"receipt_ids": [Command.create({"document_kind": "quotation"})]}
            )
        with self.assertRaises(UserError):
            allocation.write({"receipt_ids": [Command.unlink(receipt.id)]})
        leftover_receipt = self.env["collection.receipt"].browse(receipt_id)
        self.assertTrue(leftover_receipt.exists())
        self.assertEqual(allocation.receipt_ids, leftover_receipt)
        self.assertEqual(leftover_receipt.document_kind, "invoice")

    def test_proposal_draft_allows_receipt_ids_writes(self):
        """Proposal draft allocations MUST remain writable for receipt_ids."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        self._mark_validated(voucher)
        confirm_sheet(sheet)
        self.assertEqual(sheet.state, "proposal")
        self.assertEqual(allocation.state, "draft")
        allocation.write(
            {"receipt_ids": [Command.create({"document_kind": "invoice"})]}
        )
        receipt = allocation.receipt_ids
        self.assertEqual(len(receipt), 1)
        self.assertEqual(receipt.document_kind, "invoice")
        self._create_value(receipt, voucher, 100.0)
        self.assertEqual(receipt.value_ids.amount, 100.0)

    def test_draft_unlink_cascades_receipts_and_values(self):
        """Draft unlink MUST remove draft receipts and values, unassign vouchers."""
        allocation, voucher, _sheet, _partner = self._balanced_allocation()
        receipt = self._create_receipt(allocation, "invoice")
        value = self._create_value(receipt, voucher, 100.0)
        receipt_id = receipt.id
        value_id = value.id
        voucher_id = voucher.id
        allocation_id = allocation.id
        line_ids = allocation.line_ids.ids
        allocation.unlink()
        self.assertFalse(
            self.env["collection.allocation"].browse(allocation_id).exists()
        )
        self.assertFalse(self.env["collection.receipt"].browse(receipt_id).exists())
        self.assertFalse(self.env["collection.receipt.value"].browse(value_id).exists())
        self.assertFalse(
            self.env["collection.allocation.line"].browse(line_ids).exists()
        )
        leftover_voucher = self.env["collection.voucher"].browse(voucher_id)
        self.assertTrue(leftover_voucher.exists())
        self.assertFalse(leftover_voucher.allocation_id)

    def test_confirmed_unlink_keeps_receipts(self):
        """Triangulation: confirmed unlink MUST keep receipts, values, vouchers."""
        allocation, voucher, _sheet, _partner = self._balanced_allocation()
        receipt = self._create_receipt(allocation, "invoice")
        value = self._create_value(receipt, voucher, 100.0)
        self._confirm(allocation)
        receipt_id = receipt.id
        value_id = value.id
        allocation_id = allocation.id
        with self.assertRaises(UserError):
            allocation.unlink()
        leftover = self.env["collection.allocation"].browse(allocation_id)
        self.assertTrue(leftover.exists())
        leftover_receipt = self.env["collection.receipt"].browse(receipt_id)
        leftover_value = self.env["collection.receipt.value"].browse(value_id)
        self.assertTrue(leftover_receipt.exists())
        self.assertTrue(leftover_value.exists())
        self.assertEqual(leftover_receipt.allocation_id, leftover)
        self.assertEqual(voucher.allocation_id, leftover)
