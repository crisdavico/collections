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
    """RED: allocation constraints, freeze, sanitizer, residual, validate/reject."""

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

    def test_unique_sheet_partner_rejected(self):
        """UNIQUE(sheet_id, partner_id) MUST reject a second header."""
        allocation, _voucher, sheet, partner = self._balanced_allocation()
        self.assertEqual(allocation.state, "confirmed")
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

    def test_freeze_rejects_writes_when_not_confirmed(self):
        allocation, voucher, sheet, partner = self._balanced_allocation()
        allocation.action_validate()
        self.assertEqual(allocation.state, "validated")
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

    def test_confirmed_allocation_allows_membership_writes(self):
        """Triangulation: confirmed allocations MAY still change frozen fields."""
        allocation, voucher, sheet, partner = self._balanced_allocation(amount=80.0)
        extra = self._create_voucher(
            partner, sheet, amount=20.0, document_id="ALLOC-CONF-EXTRA"
        )
        allocation.write(
            {
                "voucher_ids": [Command.link(extra.id)],
                "residual_reason": "on_account",
            }
        )
        self.assertIn(extra, allocation.voucher_ids)
        self.assertIn(voucher, allocation.voucher_ids)

    def test_delete_command_unassigns_without_destroying_voucher(self):
        partner = self._partner("ALLOC-DELCMD")
        sheet = self._create_sheet()
        voucher = self._create_voucher(partner, sheet, amount=0.0)
        allocation = self._create_allocation(sheet, partner, vouchers=voucher)
        allocation.write({"voucher_ids": [Command.delete(voucher.id)]})
        self.assertTrue(voucher.exists())
        self.assertFalse(voucher.allocation_id)
        self.assertFalse(allocation.voucher_ids)

    def test_residual_zero_confirmed_ok(self):
        allocation, voucher, _sheet, _partner = self._balanced_allocation(amount=100.0)
        self.assertEqual(allocation.state, "confirmed")
        self.assertEqual(allocation.total_vouchers, 100.0)
        self.assertEqual(allocation.total_applied, 100.0)
        self.assertEqual(allocation.residual, 0.0)
        self.assertFalse(allocation.residual_reason)
        self.assertEqual(voucher.allocation_id, allocation)

    def test_residual_positive_requires_reason_only_when_confirmed(self):
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
        self.assertEqual(allocation.residual, 60.0)
        self.assertEqual(allocation.residual_reason, "on_account")

    def test_residual_negative_rejected_only_while_confirmed(self):
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
        allocation.action_validate()
        voucher.write({"amount": 10.0})
        self.assertEqual(allocation.state, "validated")
        self.assertLess(allocation.residual, 0.0)

    def test_validate_and_reject_use_context_gate(self):
        allocation, _voucher, _sheet, _partner = self._balanced_allocation()
        allocation.action_validate()
        self.assertEqual(allocation.state, "validated")
        self.assertEqual(allocation.reviewed_by, self.env.user)
        self.assertTrue(allocation.reviewed_at)

        other, _v, _s, _p = self._balanced_allocation(
            amount=25.0, partner=self._partner("ALLOC-REJ")
        )
        other.write({"state": "rejected"})
        self.assertEqual(other.state, "rejected")
        self.assertEqual(other.reviewed_by, self.env.user)

        with self.assertRaises(UserError):
            allocation.action_validate()
        with self.assertRaises(UserError):
            other.action_reject()

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

    def test_unlink_with_revisions_refused(self):
        allocation, voucher, _sheet, _partner = self._balanced_allocation()
        self._create_revision(allocation, request_id="req-keep")
        allocation_id = allocation.id
        with self.assertRaises(UserError):
            allocation.unlink()
        self.assertTrue(
            self.env["collection.allocation"].browse(allocation_id).exists()
        )
        self.assertEqual(voucher.allocation_id, allocation)

    def test_unlink_without_revisions_allowed(self):
        allocation, voucher, _sheet, _partner = self._balanced_allocation()
        allocation_id = allocation.id
        allocation.unlink()
        self.assertFalse(
            self.env["collection.allocation"].browse(allocation_id).exists()
        )
        self.assertFalse(voucher.allocation_id)
        self.assertTrue(voucher.exists())

    def test_allocation_id_write_only_when_both_confirmed_or_unset(self):
        partner = self._partner("ALLOC-WRITE")
        sheet = self._create_sheet()
        voucher = self._create_voucher(partner, sheet, amount=40.0)
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            residual_reason="on_account",
        )
        voucher.write({"allocation_id": False})
        self.assertFalse(voucher.allocation_id)
        voucher.write({"allocation_id": allocation.id})
        self.assertEqual(voucher.allocation_id, allocation)

        allocation.action_validate()
        with self.assertRaises(UserError):
            voucher.write({"allocation_id": False})
        self.assertEqual(voucher.allocation_id, allocation)

        pending = self._create_voucher(
            self._partner("ALLOC-WRITE-P2"),
            allocation.sheet_id,
            amount=15.0,
            document_id="ALLOC-WRITE-PEND",
        )
        with self.assertRaises(UserError):
            pending.write({"allocation_id": allocation.id})
        self.assertFalse(pending.allocation_id)

    def test_allocated_voucher_unlink_refused_including_pending(self):
        _allocation, voucher, _sheet, _partner = self._balanced_allocation()
        self.assertEqual(voucher.state, "pending")
        self.assertTrue(voucher.allocation_id)
        voucher_id = voucher.id
        with self.assertRaises(UserError):
            voucher.unlink()
        leftover = self.env["collection.voucher"].browse(voucher_id)
        self.assertTrue(leftover.exists())
        self.assertTrue(leftover.allocation_id)

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
        """Fully applied confirmed allocation MUST refuse a voucher partner move."""
        allocation, voucher, _sheet, partner = self._balanced_allocation()
        other = self._partner("ALLOC-DETACH-Q")
        with self.assertRaises(UserError):
            voucher.write({"partner_id": other.id})
        self.assertEqual(allocation.voucher_ids, voucher)
        self.assertEqual(voucher.partner_id, partner)
        self.assertEqual(voucher.allocation_id, allocation)

    def test_projected_residual_less_than_amount_detach_refused(self):
        """Projected residual below the voucher amount MUST refuse detach."""
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
        """Same-vals partner Q + allocation B MUST keep partner match."""
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
