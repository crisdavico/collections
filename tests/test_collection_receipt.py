# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import inspect
from datetime import date
from pathlib import Path
from unittest.mock import patch

from psycopg2 import IntegrityError

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from .common_connector import confirm_sheet, install_bound_test_connector
from .test_collection_payment import (
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
)


class TestCollectionReceipt(TransactionCase):
    """Receipt uniqueness, values, totals, freeze, closed, local Close, ACL."""

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

    _CREATE_RECEIPT = (
        "odoo.addons.collection.models.collection_connector."
        "CollectionConnector.create_receipt"
    )

    def _close_locally(self, sheet):
        """Close with no connector; fail if ``create_receipt`` runs."""
        self.env.company.write({"collection_connector_id": False})
        with patch(self._CREATE_RECEIPT) as mocked:
            mocked.side_effect = AssertionError("create_receipt must not run")
            sheet.action_close()
            mocked.assert_not_called()
        return sheet

    def _enable_seller_deposit_type(self):
        catalog = self.env.ref("collection.document_type_seller_deposit")
        self.env.company.write(
            {"allowed_document_type_ids": [Command.link(catalog.id)]}
        )
        return catalog

    def _create_replacement(self, receipt, cash, deposit, amount=10.0, **extra):
        vals = {
            "receipt_id": receipt.id,
            "cash_voucher_id": cash.id,
            "deposit_voucher_id": deposit.id,
            "amount": amount,
            "direction": extra.pop("direction", "replace"),
            "created_by": extra.pop("created_by", self.env.user.id),
            "created_at": extra.pop("created_at", "2026-09-01 12:00:00"),
        }
        vals.update(extra)
        return (
            self.env["collection.cash.replacement"]
            .with_context(collection_cash_replacement=True)
            .create(vals)
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

    def test_reverse_relation_lists_values_on_receipt_value_ids(self):
        """Voucher receipt_value_ids MUST list every value of that voucher."""
        allocation, voucher, _sheet, _partner = self._balanced_allocation(amount=100.0)
        invoice = self._create_receipt(allocation, "invoice")
        quotation = self._create_receipt(allocation, "quotation")
        value_invoice = self._create_value(invoice, voucher, 40.0)
        value_quotation = self._create_value(quotation, voucher, 60.0)
        self.assertIn("receipt_value_ids", voucher._fields)
        self.assertEqual(
            set(voucher.receipt_value_ids.ids),
            {value_invoice.id, value_quotation.id},
        )
        self.assertEqual(voucher.receipt_value_ids.mapped("amount"), [40.0, 60.0])

    def test_reverse_relation_empty_when_voucher_has_no_values(self):
        """A voucher with no receipt values MUST have an empty receipt_value_ids."""
        _allocation, voucher, _sheet, _partner = self._balanced_allocation(amount=100.0)
        self.assertIn("receipt_value_ids", voucher._fields)
        self.assertFalse(voucher.receipt_value_ids)

    def test_over_split_on_one_allocation_zero_or_duplicate_refused(self):
        """Over-split, amount <= 0, or duplicate (receipt, voucher) MUST refuse."""
        allocation, voucher, _sheet, _partner = self._balanced_allocation(amount=100.0)
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

    def test_cross_customer_same_sheet_accepted(self):
        """Values 40 on A and 60 on B of the same sheet MUST persist."""
        allocation, voucher, sheet, _partner = self._balanced_allocation(amount=100.0)
        other_partner = self._partner("RCPT-CUST-B")
        other_voucher = self._create_voucher(
            other_partner, sheet, amount=50.0, document_id="RCPT-CROSS-B"
        )
        other_alloc = self._create_allocation(
            sheet,
            other_partner,
            vouchers=other_voucher,
            lines=[
                self._line_vals(
                    amount_applied=50.0,
                    invoice_balance=50.0,
                    external_invoice_id="INV-CROSS-B",
                )
            ],
        )
        receipt_a = self._create_receipt(allocation, "invoice")
        receipt_b = self._create_receipt(other_alloc, "invoice")
        value_a = self._create_value(receipt_a, voucher, 40.0)
        value_b = self._create_value(receipt_b, voucher, 60.0)
        self.assertEqual(value_a.amount, 40.0)
        self.assertEqual(value_b.amount, 60.0)
        self.assertEqual(value_a.voucher_id, voucher)
        self.assertEqual(value_b.voucher_id, voucher)
        self.assertEqual(value_a.receipt_id.sheet_id, sheet)
        self.assertEqual(value_b.receipt_id.sheet_id, sheet)
        self.assertNotEqual(
            value_a.receipt_id.allocation_id, value_b.receipt_id.allocation_id
        )

    def test_cross_sheet_refused(self):
        """A value linking a voucher on S1 to a receipt on S2 MUST refuse."""
        allocation, voucher, _sheet, _partner = self._balanced_allocation(amount=100.0)
        other_seller = create_internal_seller(self.env, login="rcpt-sheet-b")
        other_sheet = self._create_sheet(seller_id=other_seller.id, force_new=True)
        other_partner = self._partner("RCPT-SHEET-B")
        other_voucher = self._create_voucher(
            other_partner, other_sheet, amount=50.0, document_id="RCPT-SHEET-B-V"
        )
        other_alloc = self._create_allocation(
            other_sheet,
            other_partner,
            vouchers=other_voucher,
            lines=[
                self._line_vals(
                    amount_applied=50.0,
                    invoice_balance=50.0,
                    external_invoice_id="INV-SHEET-B",
                )
            ],
        )
        other_receipt = self._create_receipt(other_alloc, "invoice")
        Value = self.env["collection.receipt.value"]
        before_ids = set(Value.search([]).ids)
        with self.assertRaises(ValidationError):
            self._create_value(other_receipt, voucher, 10.0)
        self.assertEqual(set(Value.search([]).ids), before_ids)
        self.assertFalse(Value.search([("voucher_id", "=", voucher.id)]))

    def test_over_cap_across_customers_refused(self):
        """40 on A + 50 on B + 20 on C MUST refuse because 110 exceeds 100."""
        allocation, voucher, sheet, _partner = self._balanced_allocation(amount=100.0)
        partner_b = self._partner("RCPT-CAP-B")
        partner_c = self._partner("RCPT-CAP-C")
        voucher_b = self._create_voucher(
            partner_b, sheet, amount=50.0, document_id="RCPT-CAP-B-V"
        )
        voucher_c = self._create_voucher(
            partner_c, sheet, amount=50.0, document_id="RCPT-CAP-C-V"
        )
        alloc_b = self._create_allocation(
            sheet,
            partner_b,
            vouchers=voucher_b,
            lines=[
                self._line_vals(
                    amount_applied=50.0,
                    invoice_balance=50.0,
                    external_invoice_id="INV-CAP-B",
                )
            ],
        )
        alloc_c = self._create_allocation(
            sheet,
            partner_c,
            vouchers=voucher_c,
            lines=[
                self._line_vals(
                    amount_applied=50.0,
                    invoice_balance=50.0,
                    external_invoice_id="INV-CAP-C",
                )
            ],
        )
        receipt_a = self._create_receipt(allocation, "invoice")
        receipt_b = self._create_receipt(alloc_b, "invoice")
        receipt_c = self._create_receipt(alloc_c, "invoice")
        first = self._create_value(receipt_a, voucher, 40.0)
        second = self._create_value(receipt_b, voucher, 50.0)
        with self.assertRaises(ValidationError):
            self._create_value(receipt_c, voucher, 20.0)
        self.assertEqual(first.amount, 40.0)
        self.assertEqual(second.amount, 50.0)
        self.assertFalse(
            self.env["collection.receipt.value"].search(
                [("receipt_id", "=", receipt_c.id)]
            )
        )

    def test_at_cap_allowed(self):
        """40 on A and 60 on B MUST persist when they sum to the voucher amount."""
        allocation, voucher, sheet, _partner = self._balanced_allocation(amount=100.0)
        other_partner = self._partner("RCPT-AT-CAP-B")
        other_voucher = self._create_voucher(
            other_partner, sheet, amount=50.0, document_id="RCPT-AT-CAP-B-V"
        )
        other_alloc = self._create_allocation(
            sheet,
            other_partner,
            vouchers=other_voucher,
            lines=[
                self._line_vals(
                    amount_applied=50.0,
                    invoice_balance=50.0,
                    external_invoice_id="INV-AT-CAP-B",
                )
            ],
        )
        receipt_a = self._create_receipt(allocation, "invoice")
        receipt_b = self._create_receipt(other_alloc, "invoice")
        value_a = self._create_value(receipt_a, voucher, 40.0)
        value_b = self._create_value(receipt_b, voucher, 60.0)
        self.assertEqual(value_a.amount, 40.0)
        self.assertEqual(value_b.amount, 60.0)
        self.assertEqual(value_a.voucher_id, voucher)
        self.assertEqual(value_b.voucher_id, voucher)

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

    def test_existing_applied_write_recomputes(self):
        """Writing an existing line amount_applied MUST recompute without SQL error."""
        allocation, voucher, _sheet, _partner = self._balanced_allocation(
            amount=100.0,
            lines=[
                self._line_vals(
                    amount_applied=70.0,
                    invoice_balance=100.0,
                    external_invoice_id="INV-REWRITE",
                )
            ],
        )
        receipt = self._create_receipt(allocation, "invoice")
        self._create_value(receipt, voucher, 100.0)
        self.assertEqual(receipt.total_values, 100.0)
        self.assertEqual(receipt.total_applied, 70.0)
        self.assertEqual(receipt.amount_on_account, 30.0)
        line = allocation.line_ids.filtered(
            lambda rec: rec.external_invoice_id == "INV-REWRITE"
        )
        self.assertEqual(len(line), 1)
        line.write({"amount_applied": 40.0})
        receipt.invalidate_recordset(
            ["total_applied", "total_values", "amount_on_account", "line_ids"]
        )
        self.assertEqual(receipt.total_values, 100.0)
        self.assertEqual(receipt.total_applied, 40.0)
        self.assertEqual(receipt.amount_on_account, 60.0)

    def test_existing_applied_write_to_zero_drops_from_totals(self):
        """Triangulation: writing amount_applied to 0 MUST drop the line from totals."""
        allocation, voucher, _sheet, _partner = self._balanced_allocation(
            amount=100.0,
            lines=[
                self._line_vals(
                    amount_applied=70.0,
                    invoice_balance=100.0,
                    external_invoice_id="INV-ZERO-APPLIED",
                )
            ],
        )
        receipt = self._create_receipt(allocation, "invoice")
        self._create_value(receipt, voucher, 100.0)
        line = allocation.line_ids.filtered(
            lambda rec: rec.external_invoice_id == "INV-ZERO-APPLIED"
        )
        self.assertEqual(len(line), 1)
        line.write({"amount_applied": 0.0})
        receipt.invalidate_recordset(
            ["total_applied", "total_values", "amount_on_account", "line_ids"]
        )
        self.assertEqual(receipt.total_values, 100.0)
        self.assertEqual(receipt.total_applied, 0.0)
        self.assertEqual(receipt.amount_on_account, 100.0)
        self.assertFalse(receipt.line_ids)

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
        confirm_sheet(sheet)
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
        confirm_sheet(sheet)
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
        with self.assertRaises(UserError):
            self._create_receipt(allocation, "quotation")
        self.assertEqual(allocation.receipt_ids, receipt)

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
        """Explicit receipt value 70 on a 100 voucher MUST persist that amount."""
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
            [
                {
                    "document_kind": "invoice",
                    "values": [
                        {"document_id": voucher.document_id, "amount": 70.0},
                    ],
                    "applications": [
                        {
                            "external_document_id": "INV-FIFO",
                            "amount_applied": 70.0,
                            "balance_seen": 70.0,
                        }
                    ],
                }
            ],
        )
        receipts = allocation.receipt_ids
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts.document_kind, "invoice")
        self.assertEqual(len(receipts.value_ids), 1)
        self.assertEqual(receipts.value_ids.amount, 70.0)
        self.assertEqual(receipts.value_ids.voucher_id, voucher)
        self.assertEqual(receipts.total_values, 70.0)

    def test_empty_invoices_rebuild_creates_zero_receipts(self):
        """Empty receipt rows MUST leave the allocation with zero receipts."""
        allocation, voucher, _sheet, _partner = self._balanced_allocation()
        mixin = self.env["muk_mcp.mixin"]
        mixin._collection_allocation_rebuild_receipts(allocation, voucher, [])
        self.assertFalse(allocation.receipt_ids)

    def test_close_issues_draft_receipts(self):
        """Close MUST set draft receipts to closed locally with no connector."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        receipt = self._create_receipt(allocation, "invoice")
        self._create_value(receipt, voucher, 100.0)
        self.assertEqual(receipt.state, "draft")
        self.assertFalse(receipt.external_receipt_id)
        self._mark_validated(voucher)
        confirm_sheet(sheet)
        self.assertEqual(sheet.state, "proposal")
        self._close_locally(sheet)
        self.assertEqual(sheet.state, "closed")
        self.assertEqual(allocation.state, "confirmed")
        self.assertEqual(receipt.state, "closed")
        self.assertFalse(receipt.external_receipt_id)
        states = {key for key, _label in receipt._fields["state"].selection}
        self.assertEqual(states, {"draft", "closed", "issued"})

    def test_close_issues_quotation_receipt_with_matching_stub(self):
        """Triangulation: invoice and quotation drafts MUST both close locally."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        invoice = self._create_receipt(allocation, "invoice")
        quotation = self._create_receipt(allocation, "quotation")
        self._create_value(invoice, voucher, 40.0)
        self._create_value(quotation, voucher, 60.0)
        self._mark_validated(voucher)
        confirm_sheet(sheet)
        self._close_locally(sheet)
        self.assertEqual(invoice.state, "closed")
        self.assertEqual(quotation.state, "closed")
        self.assertFalse(invoice.external_receipt_id)
        self.assertFalse(quotation.external_receipt_id)

    def test_close_with_zero_receipts_still_closes(self):
        """Close MUST confirm allocations with zero receipts and MUST NOT dispatch."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        self.assertFalse(allocation.receipt_ids)
        self._mark_validated(voucher)
        confirm_sheet(sheet)
        self._close_locally(sheet)
        self.assertEqual(sheet.state, "closed")
        self.assertEqual(allocation.state, "confirmed")
        self.assertFalse(allocation.receipt_ids)

    def test_close_skips_zero_value_receipts(self):
        """Empty draft receipts MUST still become closed; Close MUST NOT dispatch."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        empty = self._create_receipt(allocation, "invoice")
        self.assertFalse(empty.value_ids)
        self._mark_validated(voucher)
        confirm_sheet(sheet)
        self._close_locally(sheet)
        self.assertEqual(sheet.state, "closed")
        self.assertEqual(empty.state, "closed")
        self.assertFalse(empty.external_receipt_id)

    def test_close_missing_connector_rolls_back(self):
        """Close MUST succeed with no connector and MUST NOT call create_receipt."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        receipt = self._create_receipt(allocation, "invoice")
        self._create_value(receipt, voucher, 100.0)
        self._mark_validated(voucher)
        confirm_sheet(sheet)
        self._close_locally(sheet)
        self.assertEqual(sheet.state, "closed")
        self.assertEqual(allocation.state, "confirmed")
        self.assertEqual(receipt.state, "closed")
        self.assertFalse(receipt.external_receipt_id)

    def test_close_does_not_rewrite_issued_receipts(self):
        """Historical issued receipts MUST keep issued and their external id."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        issued = self._create_receipt(allocation, "invoice")
        self._create_value(issued, voucher, 100.0)
        issued.with_context(collection_receipt_issuing=True).write(
            {"state": "issued", "external_receipt_id": "ERP-KEEP"}
        )
        self._mark_validated(voucher)
        confirm_sheet(sheet)
        self._close_locally(sheet)
        self.assertEqual(issued.state, "issued")
        self.assertEqual(issued.external_receipt_id, "ERP-KEEP")

    def test_raw_receipt_state_write_rejected(self):
        """Raw receipt state writes MUST UserError except audited Close/Cancel."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        receipt = self._create_receipt(allocation, "invoice")
        self._create_value(receipt, voucher, 100.0)
        with self.assertRaises(UserError):
            receipt.write({"state": "issued"})
        self.assertEqual(receipt.state, "draft")
        self._mark_validated(voucher)
        confirm_sheet(sheet)
        self._close_locally(sheet)
        self.assertEqual(receipt.state, "closed")
        with self.assertRaises(UserError):
            receipt.write({"state": "draft"})
        with self.assertRaises(UserError):
            receipt.write({"state": "issued"})
        self.assertEqual(receipt.state, "closed")
        self.assertFalse(receipt.external_receipt_id)

    def test_audited_receipt_helpers_cycle_draft_closed(self):
        """Audited helpers MUST close drafts and reopen closed, skipping issued."""
        allocation, voucher, _sheet, _partner = self._balanced_allocation()
        draft = self._create_receipt(allocation, "invoice")
        issued = self._create_receipt(allocation, "quotation")
        self._create_value(draft, voucher, 40.0)
        self._create_value(issued, voucher, 60.0)
        issued.with_context(collection_receipt_issuing=True).write(
            {"state": "issued", "external_receipt_id": "ERP-HELPER"}
        )
        states = {key for key, _label in draft._fields["state"].selection}
        self.assertEqual(states, {"draft", "closed", "issued"})
        (draft | issued)._action_mark_closed()
        self.assertEqual(draft.state, "closed")
        self.assertFalse(draft.external_receipt_id)
        self.assertEqual(issued.state, "issued")
        self.assertEqual(issued.external_receipt_id, "ERP-HELPER")
        with self.assertRaises(UserError):
            draft.write({"state": "draft"})
        with self.assertRaises(UserError):
            draft.write({"state": "issued"})
        (draft | issued)._action_reopen_closed()
        self.assertEqual(draft.state, "draft")
        self.assertFalse(draft.external_receipt_id)
        self.assertEqual(issued.state, "issued")
        self.assertEqual(issued.external_receipt_id, "ERP-HELPER")

    def test_cancel_reopens_closed_receipts_not_issued(self):
        """Cancel from closed MUST reopen local closed receipts and skip issued."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        local = self._create_receipt(allocation, "invoice")
        issued = self._create_receipt(allocation, "quotation")
        self._create_value(local, voucher, 40.0)
        self._create_value(issued, voucher, 60.0)
        issued.with_context(collection_receipt_issuing=True).write(
            {"state": "issued", "external_receipt_id": "ERP-KEEP-CAN"}
        )
        self._mark_validated(voucher)
        confirm_sheet(sheet)
        self._close_locally(sheet)
        self.assertEqual(local.state, "closed")
        sheet.action_cancel()
        self.assertEqual(sheet.state, "cancelled")
        self.assertEqual(local.state, "draft")
        self.assertFalse(local.external_receipt_id)
        self.assertEqual(issued.state, "issued")
        self.assertEqual(issued.external_receipt_id, "ERP-KEEP-CAN")
        with self.assertRaises(UserError):
            local.write({"document_kind": "quotation"})
        with self.assertRaises(UserError):
            self._create_receipt(allocation, "invoice")

    def test_frozen_sheet_refuses_receipt_and_value_create(self):
        """Closed and cancelled sheets MUST refuse receipt and value create."""
        allocation, voucher, sheet, _partner = self._balanced_allocation()
        self._mark_validated(voucher)
        confirm_sheet(sheet)
        self._close_locally(sheet)
        self.assertEqual(sheet.state, "closed")
        with self.assertRaises(UserError):
            self._create_receipt(allocation, "invoice")
        self.assertFalse(allocation.receipt_ids)
        sheet.action_cancel()
        self.assertEqual(sheet.state, "cancelled")
        with self.assertRaises(UserError):
            self._create_receipt(allocation, "quotation")
        self.assertFalse(allocation.receipt_ids)
        sheet.action_reinstate()
        self.assertEqual(sheet.state, "submitted")
        receipt = self._create_receipt(allocation, "invoice")
        self.assertTrue(receipt.id)
        self.assertEqual(receipt.state, "draft")
        value = self._create_value(receipt, voucher, 100.0)
        self.assertTrue(value.id)

    def test_frozen_sheet_refuses_replacement_create(self):
        """Closed sheets MUST refuse cash replacement create even with the gate."""
        allocation, voucher, sheet, partner = self._balanced_allocation()
        cash = self._create_voucher(
            partner, sheet, amount=50.0, document_type="cash", document_id="RCPT-CASH"
        )
        allocation.write({"voucher_ids": [Command.link(cash.id)]})
        receipt = self._create_receipt(allocation, "invoice")
        self._enable_seller_deposit_type()
        self.env.company.write({"auto_create_sheet": False})
        deposit = self.env["collection.voucher"].create(
            {
                "document_type": "seller_deposit",
                "seller_id": sheet.seller_id.id,
                "company_id": sheet.company_id.id,
                "amount": 50.0,
                "voucher_number": "SD-RCPT-FRZ",
                "voucher_date": "2026-09-08",
            }
        )
        self.assertFalse(deposit.sheet_id)
        self._mark_validated(voucher, cash)
        sheet.action_seller_close()
        sheet.action_declare_cash(commission_withheld=0.0)
        sheet.action_confirm()
        self._close_locally(sheet)
        with self.assertRaises(UserError):
            self._create_replacement(receipt, cash, deposit)
        self.assertFalse(
            self.env["collection.cash.replacement"].search(
                [("receipt_id", "=", receipt.id)]
            )
        )

    def test_cancel_does_not_create_reverse_replacements(self):
        """Cancel then Reinstate MUST NOT create reverse replacements."""
        allocation, voucher, sheet, partner = self._balanced_allocation()
        cash = self._create_voucher(
            partner, sheet, amount=50.0, document_type="cash", document_id="RCPT-CASH-R"
        )
        allocation.write({"voucher_ids": [Command.link(cash.id)]})
        receipt = self._create_receipt(allocation, "invoice")
        self._create_value(receipt, voucher, 50.0)
        self._enable_seller_deposit_type()
        self.env.company.write({"auto_create_sheet": False})
        deposit = self.env["collection.voucher"].create(
            {
                "document_type": "seller_deposit",
                "seller_id": sheet.seller_id.id,
                "company_id": sheet.company_id.id,
                "amount": 50.0,
                "voucher_number": "SD-RCPT-REV",
                "voucher_date": "2026-09-08",
            }
        )
        self.assertFalse(deposit.sheet_id)
        row = self._create_replacement(receipt, cash, deposit, amount=10.0)
        self.assertEqual(row.direction, "replace")
        self._mark_validated(voucher, cash)
        sheet.action_seller_close()
        sheet.action_declare_cash(commission_withheld=0.0)
        sheet.action_confirm()
        self._close_locally(sheet)
        sheet.action_cancel()
        sheet.action_reinstate()
        leftovers = self.env["collection.cash.replacement"].search(
            [("receipt_id", "=", receipt.id)]
        )
        self.assertEqual(leftovers, row)
        self.assertEqual(leftovers.direction, "replace")
        self.assertFalse(leftovers.filtered(lambda rec: rec.direction == "reverse"))
