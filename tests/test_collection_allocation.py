# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date
from re import fullmatch

from psycopg2 import IntegrityError

from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from .test_collection_payment import (
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
)


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
        if extra.get("residual_reason"):
            vals["residual_reason"] = extra.pop("residual_reason")
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

    def _create_revision(self, allocation, **extra):
        vals = {
            "allocation_id": allocation.id,
            "revision": extra.pop("revision", allocation.revision),
            "request_id": extra.pop("request_id", f"req-{allocation.id}"),
            "content_hash": extra.pop("content_hash", "abc123"),
            "confirmed_by": extra.pop("confirmed_by", self.env.user.id),
            "confirmed_at": extra.pop("confirmed_at", "2026-09-01 12:00:00"),
            "total_vouchers": extra.pop("total_vouchers", allocation.total_vouchers),
            "total_applied": extra.pop("total_applied", allocation.total_applied),
            "total_debt": extra.pop("total_debt", allocation.total_debt),
            "residual": extra.pop("residual", allocation.residual),
            "residual_reason": extra.pop("residual_reason", allocation.residual_reason),
        }
        vals.update(extra)
        return (
            self.env["collection.allocation.revision"]
            .with_context(collection_allocation_revision=True)
            .create(vals)
        )

    def _confirm(self, allocation):
        allocation.with_context(collection_allocation_audited_state=True).write(
            {"state": "confirmed"}
        )
        return allocation

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
            lines=[self._line_vals(amount_applied=50.0, invoice_balance=50.0)],
        )
        self.assertTrue(other_alloc.id)
        self.assertEqual(other_alloc.partner_id, other_partner)

        sheet.action_close()
        sheet_b = self._create_sheet(force_new=True)
        voucher_b = self._create_voucher(partner, sheet_b, amount=25.0)
        alloc_b = self._create_allocation(
            sheet_b,
            partner,
            vouchers=voucher_b,
            lines=[self._line_vals(amount_applied=25.0, invoice_balance=25.0)],
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
        allocation.write(
            {
                "voucher_ids": [Command.link(extra.id)],
                "residual_reason": "on_account",
            }
        )
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
        voucher = self._create_voucher(partner, sheet, amount=0.0)
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
        self.assertEqual(allocation.residual, 0.0)
        self.assertFalse(allocation.residual_reason)
        self.assertEqual(voucher.allocation_id, allocation)
        self._confirm(allocation)
        self.assertEqual(allocation.state, "confirmed")
        self.assertEqual(allocation.residual, 0.0)

    def test_residual_positive_requires_reason_on_draft_and_confirmed(self):
        partner = self._partner("ALLOC-RES")
        sheet = self._create_sheet()
        voucher = self._create_voucher(partner, sheet, amount=100.0)
        with self.assertRaises(ValidationError):
            self._create_allocation(
                sheet,
                partner,
                vouchers=voucher,
                lines=[self._line_vals(amount_applied=40.0, invoice_balance=40.0)],
            )
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[self._line_vals(amount_applied=40.0, invoice_balance=40.0)],
            residual_reason="on_account",
        )
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(allocation.residual, 60.0)
        self.assertEqual(allocation.residual_reason, "on_account")
        self._confirm(allocation)
        self.assertEqual(allocation.state, "confirmed")
        self.assertEqual(allocation.residual, 60.0)
        self.assertEqual(allocation.residual_reason, "on_account")

    def test_residual_negative_rejected_on_draft_and_confirmed(self):
        partner = self._partner("ALLOC-NEG")
        sheet = self._create_sheet()
        voucher = self._create_voucher(partner, sheet, amount=50.0)
        with self.assertRaises(ValidationError):
            self._create_allocation(
                sheet,
                partner,
                vouchers=voucher,
                lines=[self._line_vals(amount_applied=80.0, invoice_balance=80.0)],
            )
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[self._line_vals(amount_applied=50.0, invoice_balance=50.0)],
        )
        self.assertEqual(allocation.state, "draft")
        with self.assertRaises(ValidationError):
            voucher.write({"amount": 10.0})
        self.assertEqual(allocation.residual, 0.0)
        voucher.write({"amount": 50.0})
        self._confirm(allocation)
        self.assertEqual(allocation.state, "confirmed")
        with self.assertRaises(ValidationError):
            voucher.write({"amount": 10.0})
        self.assertEqual(allocation.residual, 0.0)

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

    def test_revision_immutable_and_request_id_unique(self):
        allocation, _voucher, _sheet, _partner = self._balanced_allocation()
        Revision = self.env["collection.allocation.revision"]
        with self.assertRaises(UserError):
            Revision.create(
                {
                    "allocation_id": allocation.id,
                    "revision": 1,
                    "request_id": "req-plain",
                    "content_hash": "h",
                    "confirmed_by": self.env.user.id,
                    "confirmed_at": "2026-09-01 12:00:00",
                }
            )
        first = self._create_revision(allocation, request_id="req-unique-1")
        self.assertEqual(first.revision, 1)
        with self.assertRaises(UserError):
            first.write({"content_hash": "changed"})
        with self.assertRaises(UserError):
            first.unlink()
        self.assertTrue(first.exists())
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self._create_revision(allocation, revision=2, request_id="req-unique-1")
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self._create_revision(
                    allocation, revision=1, request_id="req-unique-rev-dup"
                )

    def test_draft_unlink_with_revisions_unassigns_vouchers(self):
        allocation, voucher, _sheet, _partner = self._balanced_allocation()
        line_ids = allocation.line_ids.ids
        revision = self._create_revision(allocation, request_id="req-draft-unlink")
        revision_id = revision.id
        allocation_id = allocation.id
        voucher_id = voucher.id
        self.assertEqual(allocation.state, "draft")
        allocation.unlink()
        self.assertFalse(
            self.env["collection.allocation"].browse(allocation_id).exists()
        )
        self.assertFalse(
            self.env["collection.allocation.revision"].browse(revision_id).exists()
        )
        self.assertFalse(
            self.env["collection.allocation.line"].browse(line_ids).exists()
        )
        leftover = self.env["collection.voucher"].browse(voucher_id)
        self.assertTrue(leftover.exists())
        self.assertFalse(leftover.allocation_id)

    def test_confirmed_unlink_refused_without_revisions(self):
        allocation, voucher, _sheet, _partner = self._balanced_allocation()
        self._confirm(allocation)
        allocation_id = allocation.id
        with self.assertRaises(UserError):
            allocation.unlink()
        leftover = self.env["collection.allocation"].browse(allocation_id)
        self.assertTrue(leftover.exists())
        self.assertEqual(leftover.state, "confirmed")
        self.assertEqual(voucher.allocation_id, leftover)

    def test_confirmed_unlink_refused_with_revisions(self):
        allocation, voucher, _sheet, _partner = self._balanced_allocation()
        revision = self._create_revision(allocation, request_id="req-keep-confirmed")
        self._confirm(allocation)
        allocation_id = allocation.id
        revision_id = revision.id
        with self.assertRaises(UserError):
            allocation.unlink()
        leftover = self.env["collection.allocation"].browse(allocation_id)
        self.assertTrue(leftover.exists())
        self.assertTrue(
            self.env["collection.allocation.revision"].browse(revision_id).exists()
        )
        self.assertEqual(voucher.allocation_id, leftover)

    def test_direct_revision_unlink_still_forbidden_on_draft(self):
        allocation, _voucher, _sheet, _partner = self._balanced_allocation()
        revision = self._create_revision(allocation, request_id="req-direct-unlink")
        with self.assertRaises(UserError):
            revision.unlink()
        self.assertTrue(revision.exists())
        self.assertTrue(allocation.exists())
        self.assertEqual(allocation.state, "draft")

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
        sheet.action_close()
        allocation._check_sheet_state_iff()
        self.assertEqual(allocation.state, "confirmed")
        self.assertEqual(sheet.state, "closed")

    def test_iff_matching_draft_on_open_passes(self):
        """Triangulation: draft on an open sheet MUST satisfy the iff constrain."""
        allocation, _voucher, sheet, _partner = self._balanced_allocation()
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(sheet.state, "open")
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
            residual_reason="on_account",
        )
        self.assertEqual(voucher.state, "pending")
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
        self.assertEqual(voucher.state, "pending")
        voucher_id = voucher.id
        with self.assertRaises(UserError):
            voucher.unlink()
        leftover = self.env["collection.voucher"].browse(voucher_id)
        self.assertTrue(leftover.exists())
        self.assertEqual(leftover.allocation_id, allocation)

    def test_pending_unlink_on_draft_negative_residual_refused(self):
        """Draft residual underflow MUST refuse pending unlink without editing lines."""
        allocation, voucher, _sheet, _partner = self._balanced_allocation()
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(allocation.residual, 0.0)
        line_before = [
            (line.id, line.amount_applied, line.external_invoice_id)
            for line in allocation.line_ids
        ]
        self.assertTrue(line_before)
        voucher_id = voucher.id
        with self.assertRaises(UserError):
            voucher.unlink()
        leftover = self.env["collection.voucher"].browse(voucher_id)
        self.assertTrue(leftover.exists())
        self.assertEqual(leftover.allocation_id, allocation)
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

    def test_line_amount_applied_must_be_positive_and_lte_balance(self):
        partner = self._partner("ALLOC-LINE")
        sheet = self._create_sheet()
        voucher = self._create_voucher(partner, sheet, amount=10.0)
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self._create_allocation(
                    sheet,
                    partner,
                    vouchers=voucher,
                    lines=[self._line_vals(amount_applied=0.0, invoice_balance=10.0)],
                    residual_reason="on_account",
                )
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self._create_allocation(
                    sheet,
                    partner,
                    vouchers=voucher,
                    lines=[self._line_vals(amount_applied=20.0, invoice_balance=10.0)],
                )

    def test_related_stored_currency_and_company_on_line_and_revision(self):
        allocation, _voucher, sheet, _partner = self._balanced_allocation()
        line = allocation.line_ids
        self.assertEqual(line.currency_id, allocation.currency_id)
        self.assertEqual(line.company_id, sheet.company_id)
        line_company = self.env["collection.allocation.line"]._fields["company_id"]
        self.assertTrue(line_company.store)
        self.assertTrue(line_company.required)
        self.assertTrue(line_company.precompute)
        rev = self._create_revision(allocation, request_id="req-related")
        self.assertEqual(rev.company_id, sheet.company_id)
        self.assertEqual(rev.currency_id, allocation.currency_id)
        rev_company = self.env["collection.allocation.revision"]._fields["company_id"]
        self.assertTrue(rev_company.store)
        self.assertTrue(rev_company.required)
        self.assertTrue(rev_company.precompute)

    def test_fully_applied_source_detach_via_partner_write_refused(self):
        """Fully applied draft allocation MUST refuse a voucher partner move."""
        allocation, voucher, _sheet, partner = self._balanced_allocation()
        other = self._partner("ALLOC-DETACH-Q")
        with self.assertRaises(UserError):
            voucher.write({"partner_id": other.id})
        self.assertEqual(allocation.voucher_ids, voucher)
        self.assertEqual(voucher.partner_id, partner)
        self.assertEqual(voucher.allocation_id, allocation)

    def test_projected_residual_less_than_amount_detach_refused(self):
        """Draft projected residual below the voucher amount MUST refuse detach."""
        partner = self._partner("ALLOC-PROJ-P")
        sheet = self._create_sheet()
        voucher = self._create_voucher(partner, sheet, amount=100.0)
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[self._line_vals(amount_applied=60.0, invoice_balance=60.0)],
            residual_reason="on_account",
        )
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(allocation.residual, 40.0)
        residual_before = allocation.residual
        other = self._partner("ALLOC-PROJ-Q")
        with self.assertRaises(UserError):
            voucher.write({"partner_id": other.id})
        self.assertEqual(allocation.residual, residual_before)
        self.assertEqual(voucher.allocation_id, allocation)
        self.assertEqual(voucher.partner_id, partner)

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
            sheet, partner_p, vouchers=voucher, residual_reason="on_account"
        )
        allocation_b = self._create_allocation(
            sheet, partner_q, residual_reason="on_account"
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
