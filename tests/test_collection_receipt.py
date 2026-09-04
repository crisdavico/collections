# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import inspect
from datetime import date
from pathlib import Path

from psycopg2 import IntegrityError

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from .common_connector import install_bound_test_connector
from .test_collection_payment import (
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
)


class TestCollectionReceipt(TransactionCase):
    """Receipt uniqueness, values, derived apps, totals, freeze, issued, ACL."""

    def _seller(self):
        return ensure_enabled_seller(self.env)

    def _partner(self, label="RCPT-CUST"):
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
            "document_kind": extra.pop("document_kind", "invoice"),
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
        vals.update(extra)
        return self.env["collection.allocation"].create(vals)

    def _balanced_allocation(self, amount=100.0, **extra):
        partner = extra.pop("partner", None) or self._partner()
        sheet = extra.pop("sheet", None) or self._create_sheet()
        voucher = extra.pop("voucher", None) or self._create_voucher(
            partner, sheet, amount=amount
        )
        lines = extra.pop("lines", None)
        if lines is None:
            lines = [self._line_vals(amount_applied=amount, invoice_balance=amount)]
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=lines,
        )
        return allocation, voucher, sheet, partner

    def _install_test_connector(self):
        return install_bound_test_connector(self, self._seller())

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

    def test_unique_kind_per_allocation(self):
        """UNIQUE(allocation_id, document_kind) MUST refuse a second invoice."""
        allocation, _voucher, _sheet, _partner = self._balanced_allocation()
        invoice = self._create_receipt(allocation, "invoice")
        self.assertEqual(invoice.document_kind, "invoice")
        self.assertEqual(invoice.allocation_id, allocation)
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self._create_receipt(allocation, "invoice")
        quotation = self._create_receipt(allocation, "quotation")
        self.assertTrue(quotation.id)
        self.assertEqual(quotation.document_kind, "quotation")
        self.assertEqual(quotation.allocation_id, allocation)

    def test_kind_omitted_defaults_invoice_invalid_refused(self):
        """Omitted document_kind MUST default invoice; other values MUST refuse."""
        allocation, _voucher, _sheet, _partner = self._balanced_allocation()
        omitted = self.env["collection.receipt"].create(
            {"allocation_id": allocation.id}
        )
        self.assertEqual(omitted.document_kind, "invoice")
        kinds = {key for key, _label in omitted._fields["document_kind"].selection}
        self.assertEqual(kinds, {"invoice", "quotation"})
        with self.assertRaises(ValueError):
            self.env["collection.receipt"].create(
                {"allocation_id": allocation.id, "document_kind": "cash"}
            )

    def test_split_values_across_two_receipts(self):
        """Voucher 100 MAY split 40 invoice + 60 quotation on the same allocation."""
        allocation, voucher, _sheet, _partner = self._balanced_allocation(amount=100.0)
        invoice = self._create_receipt(allocation, "invoice")
        quotation = self._create_receipt(allocation, "quotation")
        invoice_value = self._create_value(invoice, voucher, 40.0)
        quotation_value = self._create_value(quotation, voucher, 60.0)
        self.assertEqual(invoice_value.amount, 40.0)
        self.assertEqual(quotation_value.amount, 60.0)
        self.assertEqual(invoice_value.voucher_id, voucher)
        self.assertEqual(quotation_value.voucher_id, voucher)

    def test_over_split_zero_duplicate_or_mismatched_allocation_refused(self):
        """Over-split, amount <= 0, duplicate (receipt, voucher), or mismatch."""
        allocation, voucher, sheet, partner = self._balanced_allocation(amount=100.0)
        invoice = self._create_receipt(allocation, "invoice")
        self._create_value(invoice, voucher, 100.0)
        with self.assertRaises(ValidationError):
            quotation = self._create_receipt(allocation, "quotation")
            self._create_value(quotation, voucher, 1.0)
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self._create_value(invoice, voucher, 0.0)
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self._create_value(invoice, voucher, -5.0)
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self._create_value(invoice, voucher, 10.0)
        other_partner = self._partner("RCPT-CUST-B")
        other_voucher = self._create_voucher(
            other_partner, sheet, amount=50.0, document_id="RCPT-OTHER-V"
        )
        other_alloc = self._create_allocation(
            sheet,
            other_partner,
            vouchers=other_voucher,
            lines=[self._line_vals(amount_applied=50.0, invoice_balance=50.0)],
        )
        other_receipt = self._create_receipt(other_alloc, "invoice")
        with self.assertRaises(ValidationError):
            self._create_value(other_receipt, voucher, 10.0)

    def test_derived_applications_from_applied_same_kind_lines(self):
        """Invoice receipt apps MUST be same-kind lines with amount_applied > 0."""
        partner = self._partner("RCPT-DERIVED")
        sheet = self._create_sheet()
        voucher = self._create_voucher(partner, sheet, amount=70.0)
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[
                self._line_vals(
                    amount_applied=50.0,
                    invoice_balance=50.0,
                    external_invoice_id="INV-APPLIED",
                    document_kind="invoice",
                ),
                self._line_vals(
                    amount_applied=0.0,
                    invoice_balance=30.0,
                    external_invoice_id="INV-ZERO",
                    document_kind="invoice",
                ),
                self._line_vals(
                    amount_applied=20.0,
                    invoice_balance=20.0,
                    external_invoice_id="QT-APPLIED",
                    document_kind="quotation",
                ),
            ],
        )
        invoice = self._create_receipt(allocation, "invoice")
        applied = invoice.line_ids
        self.assertEqual(len(applied), 1)
        self.assertEqual(applied.external_invoice_id, "INV-APPLIED")
        self.assertEqual(applied.amount_applied, 50.0)
        self.assertEqual(applied.document_kind, "invoice")
        self.assertFalse(
            self.env["ir.model"].search([("model", "=", "collection.receipt.line")])
        )
        self.assertNotIn("receipt_id", allocation.line_ids._fields)

    def test_summary_counts_and_numbers_per_kind(self):
        """Summary MUST count and name only same-kind lines with applied > 0."""
        partner = self._partner("RCPT-SUMMARY")
        sheet = self._create_sheet()
        voucher = self._create_voucher(partner, sheet, amount=70.0)
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[
                self._line_vals(
                    amount_applied=50.0,
                    invoice_balance=50.0,
                    external_invoice_id="INV-SUM-APPLIED",
                    invoice_number="A-0001-00000050",
                    document_kind="invoice",
                ),
                self._line_vals(
                    amount_applied=0.0,
                    invoice_balance=30.0,
                    external_invoice_id="INV-SUM-ZERO",
                    invoice_number="A-0001-00000030",
                    document_kind="invoice",
                ),
                self._line_vals(
                    amount_applied=20.0,
                    invoice_balance=20.0,
                    external_invoice_id="QT-SUM-APPLIED",
                    invoice_number="P-0001-00000020",
                    document_kind="quotation",
                ),
            ],
        )
        invoice = self._create_receipt(allocation, "invoice")
        quotation = self._create_receipt(allocation, "quotation")
        self.assertEqual(invoice.document_count, 1)
        self.assertEqual(invoice.document_numbers, "A-0001-00000050")
        self.assertEqual(quotation.document_count, 1)
        self.assertEqual(quotation.document_numbers, "P-0001-00000020")

    def test_document_numbers_joins_applied_lines_by_due_date(self):
        """Two applied lines MUST join comma-separated, oldest due date first."""
        partner = self._partner("RCPT-JOIN")
        sheet = self._create_sheet()
        voucher = self._create_voucher(partner, sheet, amount=60.0)
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[
                self._line_vals(
                    amount_applied=20.0,
                    invoice_balance=20.0,
                    external_invoice_id="INV-JOIN-LATE",
                    invoice_number="A-LATE",
                    due_date=date(2026, 3, 31),
                ),
                self._line_vals(
                    amount_applied=40.0,
                    invoice_balance=40.0,
                    external_invoice_id="INV-JOIN-EARLY",
                    invoice_number="A-EARLY",
                    due_date=date(2026, 2, 28),
                ),
            ],
        )
        receipt = self._create_receipt(allocation, "invoice")
        self.assertEqual(receipt.document_count, 2)
        self.assertEqual(receipt.document_numbers, "A-EARLY, A-LATE")

    def test_document_numbers_falls_back_to_external_invoice_id(self):
        """A line without invoice_number MUST fall back to external_invoice_id."""
        allocation, _voucher, _sheet, _partner = self._balanced_allocation(
            amount=40.0,
            lines=[
                self._line_vals(
                    amount_applied=40.0,
                    invoice_balance=40.0,
                    external_invoice_id="INV-NO-NUMBER",
                    invoice_number=False,
                )
            ],
        )
        receipt = self._create_receipt(allocation, "invoice")
        self.assertEqual(receipt.document_numbers, "INV-NO-NUMBER")
        self.assertNotIn(", ,", receipt.document_numbers)

    def test_voucher_count_matches_value_rows(self):
        """voucher_count MUST equal the number of value rows on the receipt."""
        partner = self._partner("RCPT-VCOUNT")
        sheet = self._create_sheet()
        first = self._create_voucher(partner, sheet, amount=30.0)
        second = self._create_voucher(partner, sheet, amount=20.0)
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=first | second,
            lines=[
                self._line_vals(
                    amount_applied=50.0,
                    invoice_balance=50.0,
                    external_invoice_id="INV-VCOUNT",
                )
            ],
        )
        receipt = self._create_receipt(allocation, "invoice")
        self.assertEqual(receipt.voucher_count, 0)
        self._create_value(receipt, first, 30.0)
        self._create_value(receipt, second, 20.0)
        self.assertEqual(receipt.voucher_count, 2)
        self.assertEqual(len(receipt.value_ids), 2)

    def test_summary_recomputes_when_lines_change(self):
        """Applying a zero line or renumbering it MUST refresh the summary."""
        partner = self._partner("RCPT-RECOMPUTE")
        sheet = self._create_sheet()
        voucher = self._create_voucher(partner, sheet, amount=80.0)
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[
                self._line_vals(
                    amount_applied=50.0,
                    invoice_balance=50.0,
                    external_invoice_id="INV-RC-APPLIED",
                    invoice_number="A-APPLIED",
                    due_date=date(2026, 1, 31),
                ),
                self._line_vals(
                    amount_applied=0.0,
                    invoice_balance=30.0,
                    external_invoice_id="INV-RC-ZERO",
                    invoice_number="A-ZERO",
                    due_date=date(2026, 2, 28),
                ),
            ],
        )
        receipt = self._create_receipt(allocation, "invoice")
        self.assertEqual(receipt.document_count, 1)
        self.assertEqual(receipt.document_numbers, "A-APPLIED")
        zero_line = allocation.line_ids.filtered(
            lambda line: line.external_invoice_id == "INV-RC-ZERO"
        )
        zero_line.write({"amount_applied": 30.0})
        self.assertEqual(receipt.document_count, 2)
        self.assertEqual(receipt.document_numbers, "A-APPLIED, A-ZERO")
        zero_line.write({"invoice_number": "A-RENUMBERED"})
        self.assertEqual(receipt.document_numbers, "A-APPLIED, A-RENUMBERED")
        zero_line.write({"amount_applied": 0.0})
        self.assertEqual(receipt.document_count, 1)
        self.assertEqual(receipt.document_numbers, "A-APPLIED")

    def test_document_numbers_is_stored_and_searchable(self):
        """document_numbers MUST be stored so receipts search by document number."""
        allocation, _voucher, _sheet, _partner = self._balanced_allocation(
            amount=25.0,
            lines=[
                self._line_vals(
                    amount_applied=25.0,
                    invoice_balance=25.0,
                    external_invoice_id="INV-SEARCH",
                    invoice_number="A-0001-00099999",
                )
            ],
        )
        receipt = self._create_receipt(allocation, "invoice")
        field = self.env["collection.receipt"]._fields["document_numbers"]
        self.assertTrue(field.store, "document_numbers MUST be stored")
        found = self.env["collection.receipt"].search(
            [("document_numbers", "ilike", "00099999")]
        )
        self.assertIn(receipt, found)

    def test_summary_empty_without_applied_lines(self):
        """A receipt over unapplied lines MUST report zero documents and no numbers."""
        allocation, _voucher, _sheet, _partner = self._balanced_allocation(
            amount=15.0,
            lines=[
                self._line_vals(
                    amount_applied=0.0,
                    invoice_balance=15.0,
                    external_invoice_id="INV-EMPTY",
                    invoice_number="A-EMPTY",
                )
            ],
        )
        receipt = self._create_receipt(allocation, "invoice")
        self.assertEqual(receipt.document_count, 0)
        self.assertFalse(receipt.document_numbers)

    def test_surplus_on_account_totals(self):
        """total_values 100, total_applied 70 → amount_on_account 30."""
        allocation, voucher, _sheet, _partner = self._balanced_allocation(
            amount=100.0,
            lines=[
                self._line_vals(
                    amount_applied=70.0,
                    invoice_balance=70.0,
                    external_invoice_id="INV-SURPLUS",
                )
            ],
        )
        receipt = self._create_receipt(allocation, "invoice")
        self._create_value(receipt, voucher, 100.0)
        self.assertEqual(receipt.total_values, 100.0)
        self.assertEqual(receipt.total_applied, 70.0)
        self.assertEqual(receipt.amount_on_account, 30.0)

    def test_equal_totals_amount_on_account_zero(self):
        """Triangulation: values 50 and applied 50 MUST persist with on-account 0."""
        allocation, voucher, _sheet, _partner = self._balanced_allocation(
            amount=50.0,
            lines=[
                self._line_vals(
                    amount_applied=50.0,
                    invoice_balance=50.0,
                    external_invoice_id="INV-EQUAL",
                )
            ],
        )
        receipt = self._create_receipt(allocation, "invoice")
        self._create_value(receipt, voucher, 50.0)
        self.assertEqual(receipt.total_values, 50.0)
        self.assertEqual(receipt.total_applied, 50.0)
        self.assertEqual(receipt.amount_on_account, 0.0)
        self.assertTrue(receipt.exists())
        self.assertTrue(receipt.value_ids)

    def _mark_validated(self, *vouchers):
        records = vouchers[0]
        for voucher in vouchers[1:]:
            records |= voucher
        records.with_context(collection_audited_state=True).write(
            {"state": "validated_collections"}
        )
        return records

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

    def _create_user(self, login, group_xmlid):
        partner_vals = {
            "name": login,
            "email": f"{login}@example.com",
        }
        Partner = self.env["res.partner"].with_context(
            tracking_disable=True,
            mail_create_nolog=True,
            mail_notrack=True,
            mail_create_nosubscribe=True,
        )
        if "autopost_bills" in Partner._fields:
            partner_vals["autopost_bills"] = "ask"
            partner = Partner.create(partner_vals)
        elif self._partner_has_autopost_bills_column():
            self.env.cr.execute(
                """
                INSERT INTO res_partner (
                    name, email, active, complete_name, type, autopost_bills,
                    create_uid, write_uid, create_date, write_date
                )
                VALUES (
                    %s, %s, true, %s, 'contact', 'ask',
                    1, 1,
                    (now() AT TIME ZONE 'UTC'),
                    (now() AT TIME ZONE 'UTC')
                )
                RETURNING id
                """,
                (login, partner_vals["email"], login),
            )
            partner = Partner.browse(self.env.cr.fetchone()[0])
        else:
            partner = Partner.create(partner_vals)
        return (
            self.env["res.users"]
            .with_context(no_reset_password=True, tracking_disable=True)
            .create(
                {
                    "name": login,
                    "login": login,
                    "email": partner_vals["email"],
                    "partner_id": partner.id,
                    "group_ids": [(6, 0, [self.env.ref(group_xmlid).id])],
                }
            )
        )

    def _create_company(self, name):
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

    def _assert_global_company_rule(self, model_name):
        rules = self.env["ir.rule"].search([("model_id.model", "=", model_name)])
        self.assertEqual(
            len(rules), 1, f"{model_name} must have exactly one record rule"
        )
        self.assertFalse(rules.groups, f"{model_name} company rule must be global")
        compact = "".join(rules.domain_force.split())
        self.assertEqual(
            compact,
            "[('company_id','in',company_ids)]",
            f"{model_name} rule must hide companies outside company_ids",
        )

    def _assert_hidden_from_user(self, user, record, read_fields):
        Model = self.env[record._name].with_user(user)
        self.assertFalse(
            Model.search([("id", "=", record.id)]),
            f"{record._name} {record.id} must not be searchable from the other company",
        )
        with self.assertRaises(AccessError):
            Model.browse(record.id).read(read_fields)
        self.assertEqual(
            Model.search_read([("id", "=", record.id)], read_fields),
            [],
        )

    def _assert_acl(self, model_name, perms):
        acls = self.env["ir.model.access"].search([("model_id.model", "=", model_name)])
        self.assertEqual(len(acls), 1, f"{model_name} must have one ACL row")
        self.assertEqual(acls.group_id, self.env.ref("base.group_user"))
        self.assertEqual(bool(acls.perm_read), perms[0])
        self.assertEqual(bool(acls.perm_write), perms[1])
        self.assertEqual(bool(acls.perm_create), perms[2])
        self.assertEqual(bool(acls.perm_unlink), perms[3])

    def test_closed_sheet_refuses_receipt_and_value_write_unlink(self):
        """Closed sheets MUST refuse receipt and value write and unlink."""
        self._install_test_connector()
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        receipt = self._create_receipt(allocation, "invoice")
        value = self._create_value(receipt, voucher, 100.0)
        self._mark_validated(voucher)
        sheet.action_confirm()
        sheet.action_close()
        self.assertEqual(sheet.state, "closed")
        self.assertIn("receipt_ids", allocation._fields)
        with self.assertRaises(UserError):
            receipt.write({"document_kind": "quotation"})
        with self.assertRaises(UserError):
            value.write({"amount": 90.0})
        receipt_id = receipt.id
        value_id = value.id
        with self.assertRaises(UserError):
            value.unlink()
        with self.assertRaises(UserError):
            receipt.unlink()
        leftover_receipt = self.env["collection.receipt"].browse(receipt_id)
        leftover_value = self.env["collection.receipt.value"].browse(value_id)
        self.assertTrue(leftover_receipt.exists())
        self.assertTrue(leftover_value.exists())
        self.assertEqual(leftover_receipt.document_kind, "invoice")
        self.assertEqual(leftover_value.amount, 100.0)

    def test_cancelled_sheet_refuses_receipt_and_value_write_unlink(self):
        """Triangulation: cancelled sheets MUST also freeze receipts and values."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        receipt = self._create_receipt(allocation, "invoice")
        value = self._create_value(receipt, voucher, 100.0)
        self._mark_validated(voucher)
        sheet.action_confirm()
        sheet.action_cancel()
        self.assertEqual(sheet.state, "cancelled")
        with self.assertRaises(UserError):
            receipt.write({"document_kind": "quotation"})
        with self.assertRaises(UserError):
            value.write({"amount": 80.0})
        value_id = value.id
        receipt_id = receipt.id
        with self.assertRaises(UserError):
            value.unlink()
        with self.assertRaises(UserError):
            receipt.unlink()
        self.assertTrue(self.env["collection.receipt"].browse(receipt_id).exists())
        leftover_value = self.env["collection.receipt.value"].browse(value_id)
        self.assertTrue(leftover_value.exists())
        self.assertEqual(leftover_value.amount, 100.0)

    def test_issued_receipt_is_immutable(self):
        """Issued receipts MUST refuse write and unlink even on a draft allocation."""
        allocation, voucher, _sheet, _partner = self._balanced_allocation()
        receipt = self._create_receipt(allocation, "invoice")
        self._create_value(receipt, voucher, 100.0)
        receipt.with_context(collection_receipt_issuing=True).write(
            {
                "state": "issued",
                "external_receipt_id": "ERP-1",
            }
        )
        self.assertEqual(receipt.state, "issued")
        self.assertEqual(receipt.external_receipt_id, "ERP-1")
        with self.assertRaises(UserError):
            receipt.write({"external_receipt_id": "ERP-2"})
        receipt_id = receipt.id
        with self.assertRaises(UserError):
            receipt.unlink()
        leftover = self.env["collection.receipt"].browse(receipt_id)
        self.assertTrue(leftover.exists())
        self.assertEqual(leftover.state, "issued")
        self.assertEqual(leftover.external_receipt_id, "ERP-1")

    def test_unique_external_receipt_id_allows_multiple_nulls(self):
        """UNIQUE(external_receipt_id) MUST refuse duplicates; nulls MAY repeat."""
        allocation, _voucher, _sheet, _partner = self._balanced_allocation()
        first = self._create_receipt(allocation, "invoice", external_receipt_id="EXT-A")
        self.assertEqual(first.external_receipt_id, "EXT-A")
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self._create_receipt(
                    allocation, "quotation", external_receipt_id="EXT-A"
                )
        other = self._create_receipt(allocation, "quotation")
        self.assertFalse(other.external_receipt_id)
        other_seller = create_internal_seller(self.env, "rcpt_null_other")
        other_sheet = self._create_sheet(seller_id=other_seller.id, force_new=True)
        other_partner = self._partner("RCPT-NULL-B")
        other_voucher = self._create_voucher(other_partner, other_sheet, amount=10.0)
        other_alloc = self._create_allocation(
            other_sheet,
            other_partner,
            vouchers=other_voucher,
            lines=[self._line_vals(amount_applied=10.0, invoice_balance=10.0)],
        )
        second_null = self._create_receipt(other_alloc, "invoice")
        self.assertFalse(second_null.external_receipt_id)
        self.assertTrue(second_null.id)

    def test_draft_unlink_cascades_receipts_keeps_vouchers(self):
        """Draft allocation unlink MUST drop receipts/values and unassign vouchers."""
        allocation, voucher, _sheet, _partner = self._balanced_allocation()
        receipt = self._create_receipt(allocation, "invoice")
        value = self._create_value(receipt, voucher, 100.0)
        self.assertIn("receipt_ids", allocation._fields)
        self.assertIn(receipt, allocation.receipt_ids)
        receipt_id = receipt.id
        value_id = value.id
        voucher_id = voucher.id
        allocation_id = allocation.id
        allocation.unlink()
        self.assertFalse(
            self.env["collection.allocation"].browse(allocation_id).exists()
        )
        self.assertFalse(self.env["collection.receipt"].browse(receipt_id).exists())
        self.assertFalse(self.env["collection.receipt.value"].browse(value_id).exists())
        leftover = self.env["collection.voucher"].browse(voucher_id)
        self.assertTrue(leftover.exists())
        self.assertFalse(leftover.allocation_id)

    def test_receipt_and_value_acl_full_crud_without_sudo(self):
        """Internal users MUST have 1,1,1,1 on receipt and value without sudo()."""
        self._assert_acl("collection.receipt", (1, 1, 1, 1))
        self._assert_acl("collection.receipt.value", (1, 1, 1, 1))
        self.assertFalse(
            self.env["res.groups"].search([("name", "ilike", "Collection Receipt")])
        )
        user = self._create_user("rcpt_acl_internal", "base.group_user")
        allocation, voucher, _sheet, _partner = self._balanced_allocation()
        Receipt = self.env["collection.receipt"].with_user(user)
        receipt = Receipt.create(
            {
                "allocation_id": allocation.id,
                "document_kind": "invoice",
            }
        )
        self.assertTrue(receipt.id)
        self.assertEqual(receipt.state, "draft")
        Value = self.env["collection.receipt.value"].with_user(user)
        value = Value.create(
            {
                "receipt_id": receipt.id,
                "voucher_id": voucher.id,
                "amount": 100.0,
            }
        )
        self.assertTrue(value.id)
        value.write({"amount": 90.0})
        self.assertEqual(value.amount, 90.0)
        value.unlink()
        self.assertFalse(value.exists())
        receipt_id = receipt.id
        receipt.unlink()
        self.assertFalse(Receipt.browse(receipt_id).exists())

    def test_other_company_receipts_hidden_by_ir_rule(self):
        """Receipts in a company outside company_ids MUST NOT be visible."""
        self._assert_global_company_rule("collection.receipt")
        self._assert_global_company_rule("collection.receipt.value")
        user = self._create_user("rcpt_acl_home", "base.group_user")
        user.write(
            {
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
            }
        )
        allocation, voucher, _sheet, _partner = self._balanced_allocation()
        visible = self._create_receipt(allocation, "invoice")
        visible_value = self._create_value(visible, voucher, 100.0)

        company_b = self._create_company("Receipt Hidden Co")
        seller_b = self._create_user("rcpt_acl_seller_b", "base.group_user")
        seller_b.write(
            {
                "company_id": company_b.id,
                "company_ids": [(6, 0, [company_b.id])],
            }
        )
        partner_b = self._partner("RCPT-HID")
        sheet_b = self._create_sheet(seller_id=seller_b.id, company_id=company_b.id)
        voucher_b = self._create_voucher(partner_b, sheet_b, amount=25.0)
        hidden_alloc = self._create_allocation(
            sheet_b,
            partner_b,
            vouchers=voucher_b,
            lines=[self._line_vals(amount_applied=25.0, invoice_balance=25.0)],
        )
        hidden = self._create_receipt(hidden_alloc, "invoice")
        hidden_value = self._create_value(hidden, voucher_b, 25.0)

        Receipt = self.env["collection.receipt"].with_user(user)
        self.assertTrue(Receipt.search([("id", "=", visible.id)]))
        self._assert_hidden_from_user(user, hidden, ["document_kind"])
        self._assert_hidden_from_user(user, hidden_value, ["amount"])
        self.assertEqual(visible.company_id, self.env.company)
        self.assertEqual(visible_value.company_id, self.env.company)
        receipt_field = self.env["collection.receipt"]._fields["company_id"]
        self.assertEqual(receipt_field.related, "allocation_id.company_id")
        self.assertTrue(receipt_field.store)
        self.assertTrue(receipt_field.required)
        self.assertTrue(receipt_field.precompute)
        self.assertTrue(receipt_field.index)
        value_field = self.env["collection.receipt.value"]._fields["company_id"]
        self.assertEqual(value_field.related, "receipt_id.company_id")
        self.assertTrue(value_field.store)
        self.assertTrue(value_field.required)
        self.assertTrue(value_field.precompute)
        self.assertTrue(value_field.index)

    def test_receipt_models_have_no_sudo(self):
        models_root = Path(__file__).resolve().parents[1] / "models"
        sources = [
            (models_root / name).read_text(encoding="utf-8")
            for name in (
                "collection_receipt.py",
                "collection_receipt_value.py",
                "collection_allocation.py",
            )
        ]
        receipt_cls = type(self.env["collection.receipt"])
        value_cls = type(self.env["collection.receipt.value"])
        sources.extend(
            [
                inspect.getsource(receipt_cls.write),
                inspect.getsource(value_cls.write),
            ]
        )
        for source in sources:
            code_lines = [
                line
                for line in source.splitlines()
                if not line.lstrip().startswith("#")
            ]
            code = "\n".join(code_lines)
            self.assertNotIn(".sudo(", code)
            self.assertNotIn("sudo()", code)

    def test_compat_fifo_one_invoice_receipt_unsplit_remainder(self):
        """No splits + applied 70 on voucher 100 MUST persist one invoice value 70."""
        allocation, voucher, _sheet, _partner = self._balanced_allocation(
            amount=100.0,
            lines=[
                self._line_vals(
                    amount_applied=70.0,
                    invoice_balance=70.0,
                    external_invoice_id="INV-FIFO",
                )
            ],
        )
        mixin = self.env["muk_mcp.mixin"]
        mixin._collection_allocation_rebuild_receipts(
            allocation,
            voucher,
            [{"external_invoice_id": "INV-FIFO", "amount_applied": 70.0}],
            [],
        )
        receipts = allocation.receipt_ids
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts.document_kind, "invoice")
        self.assertEqual(len(receipts.value_ids), 1)
        self.assertEqual(receipts.value_ids.amount, 70.0)
        self.assertEqual(receipts.value_ids.voucher_id, voucher)
        self.assertEqual(receipts.total_values, 70.0)

    def test_empty_invoices_rebuild_creates_zero_receipts(self):
        """Empty invoices and no splits MUST leave the allocation with zero receipts."""
        allocation, voucher, _sheet, _partner = self._balanced_allocation()
        mixin = self.env["muk_mcp.mixin"]
        mixin._collection_allocation_rebuild_receipts(allocation, voucher, [], [])
        self.assertFalse(allocation.receipt_ids)

    def test_close_issues_draft_receipts(self):
        """Close MUST dispatch create_receipt and stamp issued with the stub id."""
        self._install_test_connector()
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        receipt = self._create_receipt(allocation, "invoice")
        self._create_value(receipt, voucher, 100.0)
        self.assertEqual(receipt.state, "draft")
        self.assertFalse(receipt.external_receipt_id)
        self._mark_validated(voucher)
        sheet.action_confirm()
        self.assertEqual(sheet.state, "proposal")
        sheet.action_close()
        self.assertEqual(sheet.state, "closed")
        self.assertEqual(allocation.state, "confirmed")
        self.assertEqual(receipt.state, "issued")
        self.assertEqual(receipt.external_receipt_id, f"stub-{receipt.id}")

    def test_close_issues_quotation_receipt_with_matching_stub(self):
        """Triangulation: quotation receipts MUST also issue with stub-{id}."""
        self._install_test_connector()
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        invoice = self._create_receipt(allocation, "invoice")
        quotation = self._create_receipt(allocation, "quotation")
        self._create_value(invoice, voucher, 40.0)
        self._create_value(quotation, voucher, 60.0)
        self._mark_validated(voucher)
        sheet.action_confirm()
        sheet.action_close()
        self.assertEqual(invoice.state, "issued")
        self.assertEqual(quotation.state, "issued")
        self.assertEqual(invoice.external_receipt_id, f"stub-{invoice.id}")
        self.assertEqual(quotation.external_receipt_id, f"stub-{quotation.id}")
        self.assertNotEqual(invoice.external_receipt_id, quotation.external_receipt_id)

    def test_close_with_zero_receipts_still_closes(self):
        """Close MUST confirm allocations with zero receipts and MUST NOT dispatch."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        self.assertFalse(allocation.receipt_ids)
        self._mark_validated(voucher)
        sheet.action_confirm()
        sheet.action_close()
        self.assertEqual(sheet.state, "closed")
        self.assertEqual(allocation.state, "confirmed")
        self.assertFalse(allocation.receipt_ids)

    def test_close_skips_zero_value_receipts(self):
        """Draft receipts with no values MUST stay draft; Close MUST still succeed."""
        self._install_test_connector()
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        empty = self._create_receipt(allocation, "invoice")
        self.assertFalse(empty.value_ids)
        self._mark_validated(voucher)
        sheet.action_confirm()
        sheet.action_close()
        self.assertEqual(sheet.state, "closed")
        self.assertEqual(empty.state, "draft")
        self.assertFalse(empty.external_receipt_id)

    def test_close_missing_connector_rolls_back(self):
        """Missing connector MUST raise and MUST NOT close or issue receipts."""
        self.env.company.write({"collection_connector_id": False})
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        receipt = self._create_receipt(allocation, "invoice")
        self._create_value(receipt, voucher, 100.0)
        self._mark_validated(voucher)
        sheet.action_confirm()
        with self.assertRaises(UserError):
            sheet.action_close()
        self.assertEqual(sheet.state, "proposal")
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(receipt.state, "draft")
        self.assertFalse(receipt.external_receipt_id)
