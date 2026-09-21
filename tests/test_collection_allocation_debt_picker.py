# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import TransactionCase

from .common_connector import (
    TEST_INVOICES,
    confirm_sheet,
    install_bound_test_connector,
    install_test_connector_type,
)
from .test_collection_payment import dummy_customer_partner, ensure_enabled_seller

ERP_CUSTOMER_IDENT = "20-11111111-1"
ERP_OUTSTANDING_IDS = frozenset({"inv-bound-overdue", "inv-bound-open"})


class TestCollectionAllocationDebtPicker(TransactionCase):
    """Missing-debt picker excludes existing lines and inserts snapshots."""

    def _seller(self):
        return ensure_enabled_seller(self.env)

    def _partner(self, label="ALLOC-PICK-CUST"):
        return dummy_customer_partner(self.env, customer=label)

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

    def _line_vals(self, amount_applied=0.0, invoice_balance=100.0, **extra):
        vals = {
            "external_invoice_id": extra.pop("external_invoice_id", "INV-1"),
            "invoice_number": extra.pop("invoice_number", "A-1"),
            "invoice_amount": extra.pop("invoice_amount", invoice_balance),
            "invoice_balance": invoice_balance,
            "invoice_state": extra.pop("invoice_state", "open"),
            "amount_applied": amount_applied,
        }
        vals.update(extra)
        return vals

    def _create_allocation(self, sheet, partner, lines=None, **extra):
        vals = {
            "sheet_id": sheet.id,
            "partner_id": partner.id,
        }
        if lines is not None:
            vals["line_ids"] = [Command.create(line) for line in lines]
        vals.update(extra)
        return self.env["collection.allocation"].create(vals)

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
                "external_customer_id": "cust-bound-active",
                "identification": identification,
                "partner_id": partner.id,
                "customer_code": "C-BOUND-1",
            }
        )
        return connector, binding

    def _partial_allocation(self, **extra):
        seller = extra.pop("seller", None) or self._seller()
        partner = extra.pop("partner", None) or self._partner(ERP_CUSTOMER_IDENT)
        sheet = extra.pop("sheet", None) or self._create_sheet(seller_id=seller.id)
        self._bind_erp_customer(partner, seller)
        allocation = self._create_allocation(
            sheet,
            partner,
            lines=[
                self._line_vals(
                    external_invoice_id="inv-bound-overdue",
                    invoice_number="A-0001",
                    amount_applied=40.0,
                    invoice_balance=100.0,
                )
            ],
        )
        return allocation, sheet, partner, seller

    def _attach_covering_voucher(self, sheet, partner, seller, allocation, amount):
        """Attach a validated bank_transfer voucher covering ``amount``.

        Confirm now refuses an allocation whose ``total_applied`` exceeds the
        money its vouchers actually collected (``allocation.total_vouchers``,
        summed from vouchers whose ``allocation_id`` points at it). Only the
        tests that Confirm (or Confirm+Close) a ``_partial_allocation`` sheet
        need this; it is opt-in so the picker tests that never leave
        ``draft``/``open`` stay untouched.
        """
        voucher = self.env["collection.voucher"].create(
            {
                "document_type": "bank_transfer",
                "partner_id": partner.id,
                "seller_id": seller.id,
                "sheet_id": sheet.id,
                "allocation_id": allocation.id,
                "company_id": sheet.company_id.id,
                "amount": amount,
                "document_id": f"picker-cover-{sheet.id}",
            }
        )
        voucher.with_context(collection_audited_state=True).write(
            {"state": "validated_collections"}
        )
        return voucher

    def _open_picker(self, allocation):
        action = allocation.action_open_debt_picker()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "collection.allocation.debt.picker")
        self.assertEqual(action["view_mode"], "form")
        self.assertEqual(action["target"], "new")
        self.assertTrue(action.get("name"))
        return self.env["collection.allocation.debt.picker"].browse(action["res_id"])

    def test_missing_lines_exclude_existing_external_ids(self):
        """Picker candidates MUST omit external_invoice_id values already on lines."""
        allocation, _sheet, _partner, _seller = self._partial_allocation()
        missing = allocation._missing_customer_debt_lines()
        self.assertEqual(
            {row["external_invoice_id"] for row in missing},
            {"inv-bound-open"},
        )
        picker = self._open_picker(allocation)
        self.assertEqual(picker.allocation_id, allocation)
        self.assertEqual(
            set(picker.candidate_ids.mapped("external_invoice_id")),
            {"inv-bound-open"},
        )
        self.assertNotIn(
            "inv-bound-overdue",
            picker.candidate_ids.mapped("external_invoice_id"),
        )

    def test_multi_select_inserts_zero_applied_and_keeps_existing(self):
        """Selected debts MUST append as snapshots with amount_applied 0."""
        allocation, _sheet, _partner, _seller = self._partial_allocation()
        overdue = allocation.line_ids.filtered(
            lambda line: line.external_invoice_id == "inv-bound-overdue"
        )
        self.assertEqual(overdue.amount_applied, 40.0)
        picker = self._open_picker(allocation)
        picker.selected_ids = picker.candidate_ids
        result = picker.action_add_debts()
        self.assertEqual(result["type"], "ir.actions.act_window_close")
        self.assertEqual(
            set(allocation.line_ids.mapped("external_invoice_id")),
            ERP_OUTSTANDING_IDS,
        )
        overdue.invalidate_recordset(["amount_applied"])
        self.assertEqual(overdue.amount_applied, 40.0)
        opened = allocation.line_ids.filtered(
            lambda line: line.external_invoice_id == "inv-bound-open"
        )
        self.assertEqual(opened.amount_applied, 0.0)
        self.assertEqual(opened.invoice_balance, 50.0)
        self.assertEqual(opened.document_kind, "invoice")

    def test_empty_without_connector_opens_with_no_candidates(self):
        """Missing connector MUST open an empty picker and MUST NOT raise."""
        seller = self._seller()
        partner = self._partner("ALLOC-PICK-NO-CONN")
        sheet = self._create_sheet(seller_id=seller.id)
        allocation = self._create_allocation(
            sheet,
            partner,
            lines=[self._line_vals(amount_applied=0.0, invoice_balance=1.0)],
        )
        self.env.company.write({"collection_connector_id": False})
        picker = self._open_picker(allocation)
        self.assertFalse(picker.candidate_ids)
        picker.action_add_debts()
        self.assertEqual(len(allocation.line_ids), 1)

    def test_empty_without_binding_opens_with_no_candidates(self):
        """Missing customer binding MUST open an empty picker and MUST NOT raise."""
        seller = self._seller()
        partner = self._partner("ALLOC-PICK-NO-BIND")
        sheet = self._create_sheet(seller_id=seller.id)
        install_test_connector_type(self)
        install_bound_test_connector(self, seller)
        allocation = self._create_allocation(
            sheet,
            partner,
            lines=[self._line_vals(amount_applied=0.0, invoice_balance=1.0)],
        )
        picker = self._open_picker(allocation)
        self.assertFalse(picker.candidate_ids)

    def test_unsaved_allocation_refuses_picker(self):
        """Unsaved allocation NewId MUST refuse Add Debt."""
        unsaved = self.env["collection.allocation"].new(
            {
                "sheet_id": self._create_sheet().id,
                "partner_id": self._partner("ALLOC-PICK-UNSAVED").id,
            }
        )
        self.assertFalse(isinstance(unsaved.id, int))
        with self.assertRaises(UserError) as err:
            unsaved.action_open_debt_picker()
        self.assertIn("saved collection allocation", str(err.exception))

    def test_cancelled_sheet_refuses_picker(self):
        """Cancelled draft allocations MUST refuse the picker."""
        allocation, sheet, partner, seller = self._partial_allocation()
        self._attach_covering_voucher(sheet, partner, seller, allocation, 40.0)
        confirm_sheet(sheet)
        sheet.action_cancel()
        self.assertEqual(sheet.state, "cancelled")
        self.assertEqual(allocation.state, "draft")
        with self.assertRaises(UserError) as err:
            allocation.action_open_debt_picker()
        self.assertIn("cannot change allocation membership", str(err.exception))
        overdue = allocation.line_ids.filtered(
            lambda line: line.external_invoice_id == "inv-bound-overdue"
        )
        self.assertEqual(overdue.amount_applied, 40.0)

    def test_closed_allocation_refuses_picker(self):
        """Closed/confirmed allocations MUST refuse the picker."""
        allocation, sheet, partner, seller = self._partial_allocation()
        self._attach_covering_voucher(sheet, partner, seller, allocation, 40.0)
        confirm_sheet(sheet)
        sheet.action_close()
        self.assertEqual(sheet.state, "closed")
        self.assertEqual(allocation.state, "confirmed")
        with self.assertRaises(UserError) as err:
            allocation.action_open_debt_picker()
        self.assertIn(
            "Confirmed allocations cannot change membership",
            str(err.exception),
        )

    def test_picker_uses_allocation_company_connector(self):
        """Picker MUST read the allocation company connector, not env.company."""
        allocation, _sheet, _partner, seller = self._partial_allocation()
        company_b = self._create_company("Picker Other Co")
        seller.write({"company_ids": [Command.link(company_b.id)]})
        picker = self._open_picker(allocation.with_company(company_b))
        self.assertEqual(
            set(picker.candidate_ids.mapped("external_invoice_id")),
            {"inv-bound-open"},
        )
        self.assertEqual(picker.company_id, allocation.company_id)
        self.assertNotEqual(picker.company_id, company_b)

    def test_picker_preserves_connector_document_kind(self):
        """Inserted lines MUST keep connector document_kind including quotation."""
        invoices = []
        for row in TEST_INVOICES:
            copied = dict(row)
            if copied.get("id") == "inv-bound-open":
                copied["document_kind"] = "quotation"
            invoices.append(copied)
        seller = self._seller()
        partner = self._partner(ERP_CUSTOMER_IDENT)
        sheet = self._create_sheet(seller_id=seller.id)
        self._bind_erp_customer(partner, seller)
        Allocation = self.env["collection.allocation"].with_context(
            collection_test_invoices=invoices
        )
        allocation = Allocation.create(
            {
                "sheet_id": sheet.id,
                "partner_id": partner.id,
                "line_ids": [
                    Command.create(
                        self._line_vals(
                            external_invoice_id="inv-bound-overdue",
                            invoice_number="A-0001",
                            amount_applied=15.0,
                            invoice_balance=100.0,
                        )
                    )
                ],
            }
        )
        picker = self._open_picker(allocation)
        open_candidate = picker.candidate_ids.filtered(
            lambda rec: rec.external_invoice_id == "inv-bound-open"
        )
        self.assertEqual(open_candidate.document_kind, "quotation")
        picker.selected_ids = open_candidate
        picker.action_add_debts()
        opened = allocation.line_ids.filtered(
            lambda line: line.external_invoice_id == "inv-bound-open"
        )
        self.assertEqual(opened.document_kind, "quotation")
        self.assertEqual(opened.amount_applied, 0.0)
        overdue = allocation.line_ids.filtered(
            lambda line: line.external_invoice_id == "inv-bound-overdue"
        )
        self.assertEqual(overdue.amount_applied, 15.0)

    def test_selected_ids_are_existing_only_many2many(self):
        """Wizard selected_ids MUST be existing-only many2many of candidates."""
        field = self.env["collection.allocation.debt.picker"]._fields["selected_ids"]
        self.assertEqual(field.type, "many2many")
        self.assertEqual(field.comodel_name, "collection.allocation.debt.candidate")
        self.assertEqual(
            field.relation,
            "collection_allocation_debt_picker_selected_rel",
        )
        form = self.env.ref("collection.view_collection_allocation_debt_picker_form")
        self.assertIn("no_create", form.arch)
        self.assertIn("no_create_edit", form.arch)
        self.assertIn('widget="many2many"', form.arch)
        candidate_list = self.env.ref(
            "collection.view_collection_allocation_debt_candidate_list"
        )
        self.assertIn('create="false"', candidate_list.arch)
