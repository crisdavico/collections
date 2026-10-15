# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import inspect
from datetime import date
from pathlib import Path
from uuid import uuid4

from psycopg2 import IntegrityError

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.collection.models.collection_common import privileged

from .common_connector import (
    advance_sheet_to,
    force_sheet_state,
    install_bound_test_connector,
)
from .test_collection_payment import (
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
)

PAYLOAD_KEYS = (
    "company",
    "printed_on",
    "reference",
    "state_label",
    "seller_name",
    "date_from",
    "date_to",
    "customer_count",
    "voucher_count",
    "commission_percent",
    "customers",
    "customer_totals",
    "document_blocks",
    "applied_total",
    "voucher_blocks",
    "collected_total",
    "cash_banked",
    "tendered",
    "recon",
    "mismatch",
    "sheet",
    "currency",
    "currency_name",
)
_PRIMITIVES = (str, float, int, bool, date, type(None))
_REPORT_SOURCE = (
    Path(__file__).resolve().parents[1] / "models" / "collection_sheet_report.py"
)
_PRIVATE_HELPERS = (
    "_collection_report_customer_codes",
    "_collection_report_document_blocks",
    "_collection_report_voucher_blocks",
    "_collection_report_voucher_row",
    "_collection_report_recon",
    "_seller_commission_rates",
    "_prepare_seller_commission_percent",
)
_RECON_FIELDS = ("commission_percent", "cash_on_hand", "commission_withheld")


class TestCollectionSheetReportData(TransactionCase):
    """RED: sheet recon inputs and shared `_collection_report_data()` payload."""

    def setUp(self):
        super().setUp()
        self._doc_seq = 0
        self.seller = ensure_enabled_seller(self.env)
        self.connector = install_bound_test_connector(self, self.seller)

    def _next_document_id(self, prefix="RPT"):
        self._doc_seq += 1
        return f"{prefix}-{self._testMethodName}-{self._doc_seq}"

    def _create_sheet(self, *, seller=None, force_new=False, **extra):
        seller = seller or self.seller
        ensure_enabled_seller(self.env, seller)
        if not force_new:
            existing = self.env["collection.sheet"].search(
                [
                    ("seller_id", "=", seller.id),
                    ("company_id", "=", self.env.company.id),
                    ("state", "=", "open"),
                ],
                limit=1,
            )
            if existing:
                return existing
        return self.env["collection.sheet"].create(
            {"seller_id": seller.id, "company_id": self.env.company.id, **extra}
        )

    def _create_voucher(self, partner, sheet, amount=100.0, **extra):
        ensure_enabled_seller(self.env, sheet.seller_id, company=sheet.company_id)
        vals = {
            "partner_id": partner.id,
            "document_type": extra.pop("document_type", "bank_transfer"),
            "document_id": extra.pop("document_id", self._next_document_id()),
            "seller_id": sheet.seller_id.id,
            "sheet_id": sheet.id,
            "company_id": sheet.company_id.id,
            "amount": amount,
        }
        vals.update(extra)
        if (
            vals.get("document_type")
            in (
                "check",
                "echeck",
            )
            and "check_number" not in extra
        ):
            # check_number is mandatory at save for check/echeck
            # (_check_check_number_required); a random default keeps
            # existing fixtures unique enough to dodge
            # _check_check_number_unique without spelling one out.
            vals["check_number"] = f"CHK-{uuid4().hex[:10]}"
        return self.env["collection.voucher"].create(vals)

    def _enable_seller_deposit_type(self, company=None):
        catalog = self.env.ref("collection.document_type_seller_deposit")
        (company or self.env.company).write(
            {"allowed_document_type_ids": [Command.link(catalog.id)]}
        )
        return catalog

    def _enable_seller_commission_type(self, company=None):
        catalog = self.env.ref("collection.document_type_seller_commission")
        (company or self.env.company).write(
            {"allowed_document_type_ids": [Command.link(catalog.id)]}
        )
        return catalog

    def _funded_cash_receipt(self, allocation, cash, amount=None):
        """Attach a replaceable cash receipt value covering Confirm commission mint."""
        amount = cash.amount if amount is None else amount
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
                "amount": amount,
            }
        )
        return receipt, cash_value

    def _create_seller_deposit(self, sheet, amount=80.0, **extra):
        """Create an unallocated remittance voucher on ``sheet`` (sentinel partner)."""
        self._enable_seller_deposit_type(company=sheet.company_id)
        ensure_enabled_seller(self.env, sheet.seller_id, company=sheet.company_id)
        vals = {
            "document_type": "seller_deposit",
            "document_id": extra.pop("document_id", self._next_document_id("SD")),
            "seller_id": sheet.seller_id.id,
            "sheet_id": sheet.id,
            "company_id": sheet.company_id.id,
            "amount": amount,
            "voucher_number": extra.pop("voucher_number", "SD-1"),
            "voucher_date": extra.pop("voucher_date", date(2026, 9, 8)),
        }
        vals.update(extra)
        return self.env["collection.voucher"].create(vals)

    def _create_seller_commission(self, sheet, amount=30.0, **extra):
        """Create an unallocated seller_commission voucher on ``sheet``."""
        self._enable_seller_commission_type(company=sheet.company_id)
        ensure_enabled_seller(self.env, sheet.seller_id, company=sheet.company_id)
        vals = {
            "document_type": "seller_commission",
            "document_id": extra.pop("document_id", self._next_document_id("SC")),
            "seller_id": sheet.seller_id.id,
            "sheet_id": sheet.id,
            "company_id": sheet.company_id.id,
            "amount": amount,
        }
        vals.update(extra)
        return self.env["collection.voucher"].create(vals)

    def _commission_vouchers(self, sheet):
        return sheet.voucher_ids.filtered(
            lambda voucher: voucher.document_type == "seller_commission"
        )

    def _submit_declared_cash(self, sheet, withheld):
        """Seller-close and declare withheld; members must already pass Confirm."""
        sheet.action_seller_close()
        sheet.action_declare_cash(commission_withheld=withheld)
        return sheet

    def _mark_issued(self, receipt, external_id):
        with privileged("collection_receipt_issuing"):
            receipt.write(
                {
                    "state": "issued",
                    "external_receipt_id": external_id,
                }
            )
        return receipt

    def _line_vals(self, amount_applied=100.0, invoice_balance=100.0, **extra):
        vals = {
            "external_invoice_id": extra.pop(
                "external_invoice_id", self._next_document_id("INV")
            ),
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

    def _balanced(self, amount=100.0, *, sheet=None, partner=None, **extra):
        partner = partner or dummy_customer_partner(
            self.env, customer=extra.pop("customer", "RPT-CUST")
        )
        sheet = sheet or self._create_sheet()
        voucher = extra.pop("voucher", None) or self._create_voucher(
            partner, sheet, amount=amount, **extra.pop("voucher_extra", {})
        )
        document_kind = extra.pop("document_kind", "invoice")
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[
                self._line_vals(
                    amount_applied=amount,
                    invoice_balance=amount,
                    document_kind=document_kind,
                    **extra.pop("line_extra", {}),
                )
            ],
            **extra,
        )
        return allocation, voucher, sheet, partner

    def _bind_customer(self, partner, code, identification=None):
        identification = identification or partner.vat or partner.name
        return self.env["collection.connector.customer.binding"].create(
            {
                "connector_id": self.connector.id,
                "external_customer_id": f"ext-{partner.id}",
                "identification": identification,
                "partner_id": partner.id,
                "customer_code": code,
            }
        )

    def _mark_validated_collections(self, vouchers):
        if vouchers:
            with privileged("collection_audited_state"):
                vouchers.write({"state": "validated_collections"})
        return vouchers

    def _drive_sheet(self, sheet, target):
        return advance_sheet_to(sheet, target)

    def _assert_seller_declaration_write_refused(self, sheet):
        before = sheet.commission_withheld
        with self.assertRaises(UserError):
            sheet.write({"commission_withheld": 99.0})
        sheet.invalidate_recordset(_RECON_FIELDS)
        self.assertEqual(sheet.commission_withheld, before)

    def _assert_cash_on_hand_write_refused(self, sheet):
        """cash_on_hand is computed: a raw write MUST refuse in every state."""
        before = sheet.cash_on_hand
        with self.assertRaises(UserError) as error:
            sheet.write({"cash_on_hand": 99.0})
        self.assertIn("computed", str(error.exception))
        sheet.invalidate_recordset(_RECON_FIELDS)
        self.assertEqual(sheet.cash_on_hand, before)

    def _assert_admin_rate_write_refused(self, sheet):
        before = sheet.commission_percent
        with self.assertRaises(UserError) as error:
            sheet.write({"commission_percent": 9.0})
        self.assertEqual(
            str(error.exception),
            "Closed collection sheets cannot change the reconciliation inputs.",
        )
        sheet.invalidate_recordset(["commission_percent"])
        self.assertEqual(sheet.commission_percent, before)

    def _assert_recon_write_refused(self, sheet):
        self._assert_seller_declaration_write_refused(sheet)
        self._assert_cash_on_hand_write_refused(sheet)
        self._assert_admin_rate_write_refused(sheet)

    def _assert_nested_primitives(self, value, path="payload"):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in ("sheet", "currency"):
                    self.assertTrue(
                        hasattr(item, "_name"),
                        f"{path}.{key} MUST be a recordset for QWeb",
                    )
                    continue
                self._assert_nested_primitives(item, f"{path}.{key}")
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                self._assert_nested_primitives(item, f"{path}[{index}]")
            return
        self.assertIsInstance(
            value,
            _PRIMITIVES,
            f"{path}={value!r} MUST be a primitive, not {type(value)!r}",
        )

    def _seller_binding(self, seller=None, connector=None):
        return self.env["collection.connector.seller.binding"].search(
            [
                ("connector_id", "=", (connector or self.connector).id),
                ("user_id", "=", (seller or self.seller).id),
            ],
            limit=1,
        )

    def test_create_seeds_commission_percent_from_seller_binding(self):
        """New sheets MUST copy the seller connector binding commission percent."""
        self._seller_binding().write({"commission_percent": 7.5})
        sheet = self._create_sheet(force_new=True)
        self.assertEqual(sheet.commission_percent, 7.5)

    def test_seeded_commission_percent_stays_editable(self):
        """The seeded rate MUST remain a plain editable value, not a compute."""
        self._seller_binding().write({"commission_percent": 7.5})
        sheet = self._create_sheet(force_new=True)
        sheet.write({"commission_percent": 3.0})
        sheet.invalidate_recordset(["commission_percent"])
        self.assertEqual(sheet.commission_percent, 3.0)

    def test_explicit_commission_percent_on_create_wins(self):
        """A non-zero percent in create vals MUST NOT be replaced by the binding."""
        self._seller_binding().write({"commission_percent": 7.5})
        sheet = self._create_sheet(force_new=True, commission_percent=2.5)
        self.assertEqual(sheet.commission_percent, 2.5)

    def test_binding_rate_change_leaves_existing_sheet_alone(self):
        """Re-import MUST NOT rewrite the create-time snapshot on an open sheet."""
        binding = self._seller_binding()
        binding.write({"commission_percent": 7.5})
        sheet = self._create_sheet(force_new=True)
        sheet.write({"commission_percent": 3.0})
        binding.write({"commission_percent": 9.0})
        sheet.invalidate_recordset(["commission_percent"])
        self.assertEqual(sheet.commission_percent, 3.0)

    def test_create_without_seller_binding_seeds_zero(self):
        """A seller with no binding MUST create at 0.0 without raising."""
        other = create_internal_seller(self.env, "rpt-unbound-seller")
        ensure_enabled_seller(self.env, other)
        self.assertFalse(self._seller_binding(seller=other))
        sheet = self._create_sheet(seller=other, force_new=True)
        self.assertEqual(sheet.commission_percent, 0.0)

    def test_create_without_active_connector_seeds_zero(self):
        """No company connector MUST create at 0.0 without raising."""
        self._seller_binding().write({"commission_percent": 7.5})
        self.env.company.write({"collection_connector_id": False})
        sheet = self._create_sheet(force_new=True)
        self.assertEqual(sheet.commission_percent, 0.0)

    def test_create_with_archived_connector_seeds_zero(self):
        """Triangulation: an archived connector MUST create at 0.0."""
        self._seller_binding().write({"commission_percent": 7.5})
        self.connector.write({"active": False})
        sheet = self._create_sheet(force_new=True)
        self.assertEqual(sheet.commission_percent, 0.0)

    def test_auto_created_sheet_seeds_commission_percent(self):
        """The voucher auto-create path MUST seed the rate too."""
        self._seller_binding().write({"commission_percent": 5.0})
        self.env.company.write({"auto_create_sheet": True})
        partner = dummy_customer_partner(self.env, customer="RPT-AUTO-RATE")
        voucher = self.env["collection.voucher"].create(
            {
                "partner_id": partner.id,
                "document_type": "bank_transfer",
                "document_id": self._next_document_id("AUTO"),
                "seller_id": self.seller.id,
                "company_id": self.env.company.id,
                "amount": 100.0,
            }
        )
        self.assertTrue(voucher.sheet_id)
        self.assertEqual(voucher.sheet_id.commission_percent, 5.0)

    def test_onchange_seller_fills_commission_percent(self):
        """Picking the seller on a new sheet MUST show the rate before saving."""
        self._seller_binding().write({"commission_percent": 7.5})
        draft = self.env["collection.sheet"].new(
            {"company_id": self.env.company.id, "seller_id": self.seller.id}
        )
        draft._onchange_seller_commission_percent()
        self.assertEqual(draft.commission_percent, 7.5)

    def test_percent_range_persists_bounds(self):
        """Open sheet MUST persist commission_percent 0 and 100."""
        sheet = self._create_sheet()
        sheet.write({"commission_percent": 0.0})
        self.assertEqual(sheet.commission_percent, 0.0)
        sheet.write({"commission_percent": 100.0})
        self.assertEqual(sheet.commission_percent, 100.0)

    def test_percent_outside_range_raises(self):
        """Outside 0–100 MUST raise and MUST NOT persist."""
        sheet = self._create_sheet()
        sheet.write({"commission_percent": 12.5})
        for bad in (-0.01, 100.01):
            with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
                with self.env.cr.savepoint():
                    sheet.write({"commission_percent": bad})
                    sheet.flush_recordset(["commission_percent"])
            sheet.invalidate_recordset(["commission_percent"])
            self.assertEqual(sheet.commission_percent, 12.5)

    def test_closed_write_guard(self):
        """Closed sheets MUST refuse recon-input writes without persisting."""
        allocation, _voucher, sheet, _partner = self._balanced()
        self._mark_validated_collections(sheet.voucher_ids)
        sheet.action_seller_close()
        sheet.write({"commission_percent": 8.0, "commission_withheld": 0.0})
        sheet.action_confirm()
        sheet.action_close()
        self.assertEqual(sheet.state, "closed")
        self.assertEqual(allocation.state, "confirmed")
        self._assert_recon_write_refused(sheet)

    def test_cancelled_write_guard(self):
        """Cancelled sheets MUST refuse recon-input writes without persisting."""
        _allocation, _voucher, sheet, _partner = self._balanced()
        self._mark_validated_collections(sheet.voucher_ids)
        sheet.action_seller_close()
        sheet.write({"commission_percent": 8.0, "commission_withheld": 0.0})
        self._drive_sheet(sheet, "cancelled")
        self.assertEqual(sheet.state, "cancelled")
        self._assert_recon_write_refused(sheet)

    def test_proposal_recon_remains_editable(self):
        """Proposal sheets MAY persist commission_percent; seller decls MUST refuse."""
        _allocation, _voucher, sheet, _partner = self._balanced()
        self._drive_sheet(sheet, "proposal")
        self.assertEqual(sheet.state, "proposal")
        sheet.write({"commission_percent": 7.5})
        sheet.invalidate_recordset(["commission_percent"])
        self.assertEqual(sheet.commission_percent, 7.5)
        self._assert_seller_declaration_write_refused(sheet)

    def test_submitted_accepts_seller_declarations(self):
        """Submitted MUST persist withheld; cash_on_hand MUST follow by compute."""
        _allocation, _voucher, sheet, _partner = self._balanced(
            amount=28.0, voucher_extra={"document_type": "cash"}
        )
        force_sheet_state(sheet, "submitted")
        self.assertEqual(sheet.state, "submitted")
        sheet.write({"commission_percent": 6.5})
        sheet.write({"commission_withheld": 3.0})
        sheet.invalidate_recordset(_RECON_FIELDS)
        self.assertEqual(sheet.commission_percent, 6.5)
        self.assertEqual(sheet.commission_withheld, 3.0)
        self.assertEqual(sheet.cash_on_hand, 25.0)
        self._assert_cash_on_hand_write_refused(sheet)

    def test_open_freezes_seller_declarations(self):
        """Open sheets MUST refuse the seller-declared withheld commission."""
        sheet = self._create_sheet(force_new=True)
        self.assertEqual(sheet.state, "open")
        sheet.write({"commission_percent": 4.0})
        self.assertEqual(sheet.commission_percent, 4.0)
        self._assert_seller_declaration_write_refused(sheet)
        self._assert_cash_on_hand_write_refused(sheet)

    def test_raw_combined_declaration_and_submitted_write_refused(self):
        """Raw decls plus state submitted MUST refuse: decls require submitted first."""
        sheet = self._create_sheet(force_new=True)
        self.assertEqual(sheet.state, "open")
        before_cash = sheet.cash_on_hand
        before_withheld = sheet.commission_withheld
        with self.assertRaises(UserError) as error:
            sheet.write({"commission_withheld": 3.0, "state": "submitted"})
        self.assertIn("submitted collection sheet", str(error.exception))
        sheet.invalidate_recordset(["state", "cash_on_hand", "commission_withheld"])
        self.assertEqual(sheet.state, "open")
        self.assertEqual(sheet.cash_on_hand, before_cash)
        self.assertEqual(sheet.commission_withheld, before_withheld)

    def test_open_from_cancelled_keeps_recon_values(self):
        """Confirm then Cancel then Reinstate MUST keep stored recon inputs."""
        allocation, voucher, sheet, _partner = self._balanced(
            amount=45.5, voucher_extra={"document_type": "cash"}
        )
        self._enable_seller_commission_type(company=sheet.company_id)
        self._funded_cash_receipt(allocation, voucher)
        self._mark_validated_collections(sheet.voucher_ids)
        sheet.action_seller_close()
        sheet.write({"commission_percent": 12.5})
        sheet.action_declare_cash(commission_withheld=5.5)
        self._drive_sheet(sheet, "cancelled")
        sheet.action_reinstate()
        self.assertEqual(sheet.state, "submitted")
        self.assertEqual(sheet.commission_percent, 12.5)
        self.assertEqual(sheet.commission_withheld, 5.5)
        self.assertEqual(sheet.cash_on_hand, 40.0)

    def test_payload_in_all_five_states(self):
        """PDF payload MUST build in every sheet state without a state UserError."""
        _allocation, _voucher, sheet, _partner = self._balanced(amount=80.0)
        reference = sheet.name
        self._mark_validated_collections(sheet.voucher_ids)
        advances = (
            ("open", lambda: None),
            ("submitted", sheet.action_seller_close),
            ("proposal", sheet.action_confirm),
            ("closed", sheet.action_close),
            ("cancelled", sheet.action_cancel),
        )
        labels = []
        for target, advance in advances:
            with self.subTest(state=target):
                advance()
                self.assertEqual(sheet.state, target)
                payload = sheet._collection_report_data()
                self.assertEqual(set(payload), set(PAYLOAD_KEYS))
                self.assertEqual(payload["collected_total"], 80.0)
                self.assertEqual(payload["reference"], reference)
                self.assertEqual(payload["voucher_count"], 1)
                labels.append(payload["state_label"])
        self.assertEqual(len(set(labels)), 5)

    def test_payload_keys_and_primitives(self):
        """Payload MUST expose listed keys with primitive nested row values."""
        allocation, voucher, sheet, partner = self._balanced(amount=80.0)
        self._bind_customer(partner, "C-BOUND-1")
        payload = sheet._collection_report_data()
        self.assertEqual(set(payload), set(PAYLOAD_KEYS))
        self._assert_nested_primitives(payload)
        self.assertEqual(payload["reference"], sheet.name)
        self.assertEqual(payload["seller_name"], sheet.seller_id.name)
        self.assertEqual(payload["customer_count"], 1)
        self.assertEqual(payload["voucher_count"], 1)
        self.assertEqual(payload["customers"][0]["debt"], allocation.total_debt)
        self.assertEqual(
            payload["customers"][0]["collected"], allocation.total_vouchers
        )
        self.assertEqual(payload["customers"][0]["applied"], allocation.total_applied)
        self.assertEqual(payload["customers"][0]["residual"], allocation.residual)
        self.assertEqual(payload["customers"][0]["residual_reason"], "")
        self.assertEqual(payload["customer_totals"]["debt"], allocation.total_debt)
        self.assertEqual(
            payload["customer_totals"]["collected"], allocation.total_vouchers
        )
        self.assertEqual(payload["collected_total"], voucher.amount)
        self.assertIs(payload["sheet"], sheet)
        self.assertEqual(payload["currency"], sheet.currency_id)

    def test_payload_residual_reason_is_empty_without_field_read(self):
        """Report MUST emit residual_reason '' without reading the dropped field."""
        allocation, _voucher, sheet, _partner = self._balanced(amount=80.0)
        payload = sheet._collection_report_data()
        self.assertEqual(payload["customers"][0]["residual_reason"], "")
        self.assertNotIn("residual_reason", allocation._fields)
        source = inspect.getsource(type(sheet)._collection_report_customers)
        self.assertNotIn('_fields["residual_reason"]', source)
        self.assertNotIn("_fields['residual_reason']", source)
        self.assertNotIn("allocation.residual_reason", source)
        self.assertIn('"residual_reason": ""', source)

    def test_payload_residual_reason_empty_for_each_customer(self):
        """Every customer row MUST carry residual_reason as empty string."""
        sheet = self._create_sheet()
        first_partner = dummy_customer_partner(self.env, customer="RPT-REASON-A")
        second_partner = dummy_customer_partner(self.env, customer="RPT-REASON-B")
        first = self._create_voucher(first_partner, sheet, amount=10.0)
        second = self._create_voucher(second_partner, sheet, amount=20.0)
        self._create_allocation(
            sheet,
            first_partner,
            vouchers=first,
            lines=[self._line_vals(amount_applied=10.0, invoice_balance=10.0)],
        )
        self._create_allocation(
            sheet,
            second_partner,
            vouchers=second,
            lines=[self._line_vals(amount_applied=5.0, invoice_balance=20.0)],
        )
        payload = sheet._collection_report_data()
        self.assertEqual(len(payload["customers"]), 2)
        reasons = [row["residual_reason"] for row in payload["customers"]]
        self.assertEqual(reasons, ["", ""])

    def test_open_sheet_prints_drafts(self):
        """Open-sheet payload MUST include draft allocations and mixed vouchers."""
        sheet = self._create_sheet()
        draft_partner = dummy_customer_partner(self.env, customer="RPT-DRAFT")
        seller_partner = dummy_customer_partner(self.env, customer="RPT-SELLER")
        collections_partner = dummy_customer_partner(
            self.env, customer="RPT-COLLECTIONS"
        )
        draft = self._create_voucher(draft_partner, sheet, amount=10.0)
        seller = self._create_voucher(seller_partner, sheet, amount=20.0)
        collections = self._create_voucher(collections_partner, sheet, amount=30.0)
        seller.action_validate_seller()
        with privileged("collection_audited_state"):
            collections.write({"state": "validated_collections"})
        first = self._create_allocation(
            sheet,
            draft_partner,
            vouchers=draft,
            lines=[self._line_vals(amount_applied=10.0, invoice_balance=10.0)],
        )
        second = self._create_allocation(
            sheet,
            seller_partner,
            vouchers=seller,
            lines=[self._line_vals(amount_applied=20.0, invoice_balance=20.0)],
        )
        self.assertEqual(first.state, "draft")
        self.assertEqual(second.state, "draft")
        self.assertEqual(sheet.state, "open")
        payload = sheet._collection_report_data()
        customer_names = {row["name"] for row in payload["customers"]}
        self.assertEqual(
            customer_names,
            {draft_partner.name, seller_partner.name},
        )
        voucher_amounts = sorted(
            row["amount"]
            for block in payload["voucher_blocks"]
            for row in block["rows"]
        )
        self.assertEqual(voucher_amounts, [10.0, 20.0, 30.0])
        voucher_states = {
            row["state"] for block in payload["voucher_blocks"] for row in block["rows"]
        }
        self.assertEqual(
            voucher_states,
            {"draft", "validated_seller", "validated_collections"},
        )
        self.assertNotIn("pending", voucher_states)
        self.assertNotIn("approved", voucher_states)
        self.assertNotIn("rejected", voucher_states)
        self.assertEqual(payload["voucher_count"], 3)
        self.assertEqual(payload["collected_total"], 60.0)
        self.assertEqual(collections.state, "validated_collections")
        self.assertEqual(seller.state, "validated_seller")
        self.assertEqual(draft.state, "draft")

    def test_binding_code_vs_blank_last(self):
        """Bound customer code MUST print; unbound blank code MUST sort last."""
        sheet = self._create_sheet()
        bound = dummy_customer_partner(self.env, customer="Alpha Bound")
        unbound = dummy_customer_partner(self.env, customer="Zulu Unbound")
        self._bind_customer(bound, "C-BOUND-1")
        self._balanced(amount=40.0, sheet=sheet, partner=bound)
        self._balanced(amount=60.0, sheet=sheet, partner=unbound)
        payload = sheet._collection_report_data()
        customers = payload["customers"]
        self.assertEqual(len(customers), 2)
        self.assertEqual(customers[0]["code"], "C-BOUND-1")
        self.assertEqual(customers[0]["name"], bound.name)
        self.assertEqual(customers[1]["code"], "")
        self.assertEqual(customers[1]["name"], unbound.name)

    def test_kind_split_drops_empty(self):
        """Invoice lines MUST form a block; empty quotation block MUST be absent."""
        self._balanced(amount=70.0, document_kind="invoice")
        sheet = self._create_sheet()
        payload = sheet._collection_report_data()
        kinds = [block["kind"] for block in payload["document_blocks"]]
        self.assertEqual(kinds, ["invoice"])
        self.assertNotIn("quotation", kinds)
        self.assertGreater(payload["document_blocks"][0]["subtotal_applied"], 0)

    def test_round_per_row_then_sum(self):
        """Block commission MUST be the sum of rounded row commissions."""
        sheet = self._create_sheet()
        sheet.write({"commission_percent": 3.0})
        partner = dummy_customer_partner(self.env, customer="RPT-ROUND")
        voucher = self._create_voucher(partner, sheet, amount=2.22)
        self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[
                self._line_vals(
                    amount_applied=1.11,
                    invoice_balance=1.11,
                    invoice_number="R-1",
                    due_date=date(2026, 2, 1),
                ),
                self._line_vals(
                    amount_applied=1.11,
                    invoice_balance=1.11,
                    invoice_number="R-2",
                    due_date=date(2026, 3, 1),
                ),
            ],
        )
        payload = sheet._collection_report_data()
        invoice_block = payload["document_blocks"][0]
        self.assertEqual(invoice_block["kind"], "invoice")
        currency = payload["currency"]
        row_commissions = [row["commission"] for row in invoice_block["rows"]]
        self.assertEqual(len(row_commissions), 2)
        expected_sum = sum(row_commissions)
        naive = currency.round(invoice_block["subtotal_applied"] * 3.0 / 100.0)
        self.assertEqual(invoice_block["subtotal_commission"], expected_sum)
        self.assertNotEqual(invoice_block["subtotal_commission"], naive)
        self.assertEqual(row_commissions[0], currency.round(1.11 * 3.0 / 100.0))

    def test_zero_percent(self):
        """Percent 0 MUST yield zero row and block commissions."""
        sheet = self._create_sheet()
        sheet.write({"commission_percent": 0.0})
        self._balanced(amount=90.0, sheet=sheet)
        payload = sheet._collection_report_data()
        self.assertEqual(payload["commission_percent"], 0.0)
        for block in payload["document_blocks"]:
            self.assertEqual(block["subtotal_commission"], 0.0)
            self.assertGreater(len(block["rows"]), 0)
            for row in block["rows"]:
                self.assertEqual(row["commission"], 0.0)

    def test_catalog_order_and_empty_drop(self):
        """Voucher blocks MUST be check then cash; empty types dropped."""
        sheet = self._create_sheet()
        partner = dummy_customer_partner(self.env, customer="RPT-VOUCHERS")
        check = self._create_voucher(partner, sheet, amount=15.0, document_type="check")
        other = self._create_voucher(partner, sheet, amount=25.0, document_type="cash")
        self._create_allocation(
            sheet,
            partner,
            vouchers=check | other,
            lines=[self._line_vals(amount_applied=40.0, invoice_balance=40.0)],
        )
        payload = sheet._collection_report_data()
        codes = [block["code"] for block in payload["voucher_blocks"]]
        self.assertEqual(codes, ["check", "cash"])
        self.assertNotIn("bank_transfer", codes)
        self.assertNotIn("cash_deposit", codes)
        check_type = self.env["collection.document.type"].search(
            [("code", "=", "check")], limit=1
        )
        self.assertEqual(payload["voucher_blocks"][0]["label"], "Cheque")
        self.assertEqual(payload["voucher_blocks"][1]["label"], "Cash")
        self.assertEqual(check_type.name, "Check")
        self.assertEqual(
            payload["collected_total"],
            sum(block["subtotal"] for block in payload["voucher_blocks"]),
        )

    def test_tendered_includes_cash_on_hand(self):
        """tendered.cash MUST equal cash_on_hand and be included in tendered.total."""
        sheet = self._create_sheet()
        self._create_voucher(
            dummy_customer_partner(self.env, customer="RPT-TENDERED-CASH"),
            sheet,
            amount=17.5,
            document_type="cash",
        )
        self._balanced(
            amount=100.0, sheet=sheet, voucher_extra={"document_type": "check"}
        )
        self.assertEqual(sheet.cash_on_hand, 17.5)
        payload = sheet._collection_report_data()
        tendered = payload["tendered"]
        self.assertEqual(tendered["cash"], 17.5)
        self.assertEqual(tendered["checks"], 100.0)
        self.assertEqual(
            tendered["total"],
            tendered["cash"]
            + tendered["deposits"]
            + tendered["checks"]
            + tendered["transfers"],
        )
        self.assertGreater(tendered["total"], tendered["cash"])
        self.assertIn(17.5, (tendered["cash"], tendered["total"]))

    def test_remittance_excluded_from_collected(self):
        """seller_deposit MUST NOT inflate collected_total or voucher blocks."""
        sheet = self._create_sheet()
        self._balanced(
            amount=50.0,
            sheet=sheet,
            customer="RPT-CASH-COLLECTED",
            voucher_extra={"document_type": "cash"},
        )
        remittance = self._create_seller_deposit(sheet, amount=80.0)
        self.assertFalse(remittance.allocation_id)
        payload = sheet._collection_report_data()
        codes = [block["code"] for block in payload["voucher_blocks"]]
        self.assertEqual(payload["collected_total"], 50.0)
        self.assertNotIn("seller_deposit", codes)
        self.assertNotEqual(payload["collected_total"], 50.0 + remittance.amount)

    def test_cash_banked_sums_seller_deposit_only(self):
        """cash_banked MUST sum seller_deposit and MUST NOT include cash_deposit."""
        sheet = self._create_sheet()
        self._balanced(
            amount=20.0,
            sheet=sheet,
            customer="RPT-BANK-DEP",
            voucher_extra={"document_type": "cash_deposit"},
        )
        remittance = self._create_seller_deposit(sheet, amount=80.0)
        payload = sheet._collection_report_data()
        self.assertEqual(payload["cash_banked"], 80.0)
        self.assertEqual(sheet.cash_banked, 80.0)
        self.assertEqual(payload["cash_banked"], remittance.amount)
        self.assertNotEqual(payload["cash_banked"], 20.0)
        self.assertAlmostEqual(sheet.cash_collected, 0.0, places=2)

    def test_excess_deposit_still_banks(self):
        """seller_deposit beyond replaceable cash MUST still bank the full deposit."""
        sheet = self._create_sheet()
        self._balanced(
            amount=50.0,
            sheet=sheet,
            customer="RPT-BANK-EXCESS",
            voucher_extra={"document_type": "cash"},
        )
        remittance = self._create_seller_deposit(sheet, amount=80.0)
        payload = sheet._collection_report_data()
        self.assertEqual(payload["cash_banked"], 80.0)
        self.assertEqual(sheet.cash_banked, remittance.amount)
        self.assertAlmostEqual(sheet.cash_collected, 50.0, places=2)
        self.assertNotEqual(payload["cash_banked"], 50.0)

    def test_no_allocations_still_banks_from_vouchers(self):
        """Zero allocations MUST still bank cash_banked from deposit vouchers."""
        sheet = self._create_sheet()
        remittance = self._create_seller_deposit(sheet, amount=80.0)
        remittance.action_validate_seller()
        sheet.action_seller_close()
        self.assertEqual(sheet.state, "submitted")
        self.assertFalse(sheet.allocation_ids)
        payload = sheet._collection_report_data()
        self.assertEqual(payload["cash_banked"], remittance.amount)
        self.assertEqual(sheet.cash_banked, 80.0)
        self.assertFalse(
            self.env["collection.cash.replacement"].search(
                [("deposit_voucher_id", "=", remittance.id)]
            )
        )

    def test_cash_on_hand_is_cash_minus_deposits_minus_withheld(self):
        """cash_on_hand MUST equal cash − seller_deposit − commission_withheld."""
        sheet = self._create_sheet()
        partner = dummy_customer_partner(self.env, customer="RPT-COH")
        self._create_voucher(partner, sheet, amount=500.0, document_type="cash")
        self._create_voucher(partner, sheet, amount=120.0, document_type="cash")
        self._create_seller_deposit(sheet, amount=200.0)
        self.assertEqual(sheet.cash_on_hand, 420.0)
        force_sheet_state(sheet, "submitted")
        sheet.action_declare_cash(commission_withheld=70.0)
        self.assertEqual(sheet.cash_collected, 620.0)
        self.assertEqual(sheet.cash_banked, 200.0)
        self.assertEqual(sheet.cash_on_hand, 350.0)

    def test_cash_on_hand_ignores_other_document_types(self):
        """Only cash and seller_deposit MUST move cash_on_hand."""
        sheet = self._create_sheet()
        partner = dummy_customer_partner(self.env, customer="RPT-COH-OTHER")
        for document_type in (
            "bank_transfer",
            "check",
            "cash_deposit",
            "echeck",
            "retention_certificate",
        ):
            self._create_voucher(
                partner, sheet, amount=90.0, document_type=document_type
            )
        self.assertEqual(sheet.cash_on_hand, 0.0)
        self._create_voucher(partner, sheet, amount=25.0, document_type="cash")
        self.assertEqual(sheet.cash_on_hand, 25.0)

    def test_cash_on_hand_recomputes_on_voucher_membership_change(self):
        """Adding, retyping, or removing a voucher MUST move stored cash_on_hand."""
        sheet = self._create_sheet()
        partner = dummy_customer_partner(self.env, customer="RPT-COH-MOVE")
        voucher = self._create_voucher(
            partner, sheet, amount=60.0, document_type="cash"
        )
        self.assertEqual(sheet.cash_on_hand, 60.0)
        voucher.write({"amount": 90.0})
        self.assertEqual(sheet.cash_on_hand, 90.0)
        voucher.write({"document_type": "bank_transfer"})
        self.assertEqual(sheet.cash_on_hand, 0.0)
        voucher.write({"document_type": "cash"})
        voucher.unlink()
        self.assertEqual(sheet.cash_on_hand, 0.0)

    def test_cash_on_hand_is_stored_and_searchable(self):
        """The computed cash_on_hand MUST be stored so search and read_group work."""
        field = self.env["collection.sheet"]._fields["cash_on_hand"]
        self.assertTrue(field.store)
        self.assertTrue(field.compute)
        self.assertTrue(field.readonly)
        sheet = self._create_sheet(force_new=True, seller=self.seller)
        self._create_voucher(
            dummy_customer_partner(self.env, customer="RPT-COH-SEARCH"),
            sheet,
            amount=77.0,
            document_type="cash",
        )
        sheet.flush_recordset(["cash_on_hand"])
        found = self.env["collection.sheet"].search(
            [("id", "=", sheet.id), ("cash_on_hand", "=", 77.0)]
        )
        self.assertEqual(found, sheet)

    def test_cash_on_hand_goes_negative_when_deposits_exceed_cash(self):
        """Remitting more than the collected cash MUST leave cash_on_hand negative."""
        sheet = self._create_sheet()
        self._create_voucher(
            dummy_customer_partner(self.env, customer="RPT-COH-NEG"),
            sheet,
            amount=30.0,
            document_type="cash",
        )
        self._create_seller_deposit(sheet, amount=100.0)
        self.assertEqual(sheet.cash_on_hand, -70.0)

    def test_cash_on_hand_create_write_refused(self):
        """Passing cash_on_hand to create MUST refuse; the value stays derived."""
        seller = create_internal_seller(self.env, "rpt-coh-create")
        ensure_enabled_seller(self.env, seller)
        with self.assertRaises(UserError) as error:
            self.env["collection.sheet"].create(
                {
                    "seller_id": seller.id,
                    "company_id": self.env.company.id,
                    "cash_on_hand": 42.0,
                }
            )
        self.assertIn("computed", str(error.exception))
        self.assertFalse(
            self.env["collection.sheet"].search([("seller_id", "=", seller.id)])
        )

    def test_cash_deposit_still_collected_when_remittance_present(self):
        """cash_deposit MUST stay in collected; only seller_deposit is skipped."""
        sheet = self._create_sheet()
        self._balanced(
            amount=20.0,
            sheet=sheet,
            customer="RPT-CASH-DEP",
            voucher_extra={"document_type": "cash_deposit"},
        )
        self._create_seller_deposit(sheet, amount=80.0)
        payload = sheet._collection_report_data()
        codes = [block["code"] for block in payload["voucher_blocks"]]
        self.assertEqual(payload["collected_total"], 20.0)
        self.assertIn("cash_deposit", codes)
        self.assertNotIn("seller_deposit", codes)

    def test_tendered_includes_remittance_echeck_and_retention(self):
        """tendered MUST include seller_deposits, echecks, and retentions."""
        sheet = self._create_sheet()
        partner = dummy_customer_partner(self.env, customer="RPT-TENDERED-NEW")
        echeck = self._create_voucher(
            partner, sheet, amount=30.0, document_type="echeck"
        )
        retention = self._create_voucher(
            partner,
            sheet,
            amount=12.0,
            document_type="retention_certificate",
        )
        remittance = self._create_seller_deposit(sheet, amount=80.0)
        self._create_allocation(
            sheet,
            partner,
            vouchers=echeck | retention,
            lines=[self._line_vals(amount_applied=42.0, invoice_balance=42.0)],
        )
        payload = sheet._collection_report_data()
        tendered = payload["tendered"]
        self.assertEqual(tendered["echecks"], echeck.amount)
        self.assertEqual(tendered["retentions"], retention.amount)
        self.assertEqual(tendered["seller_deposits"], remittance.amount)
        self.assertEqual(
            tendered["total"],
            tendered["cash"]
            + tendered["deposits"]
            + tendered["checks"]
            + tendered["transfers"]
            + tendered["echecks"]
            + tendered["retentions"]
            + tendered["seller_deposits"],
        )
        # The remittance raises tendered.seller_deposits and lowers the derived
        # cash_on_hand by the same amount, so it nets out of the total.
        self.assertEqual(tendered["cash"], -remittance.amount)
        self.assertEqual(tendered["total"], echeck.amount + retention.amount)

    def test_tendered_keeps_existing_keys_and_recon_algebra(self):
        """Existing tendered keys stay; net_due/difference algebra is untouched."""
        sheet = self._create_sheet()
        self._balanced(
            amount=100.0,
            sheet=sheet,
            customer="RPT-TENDERED-KEYS",
            voucher_extra={"document_type": "bank_transfer"},
        )
        self._create_voucher(
            dummy_customer_partner(self.env, customer="RPT-TENDERED-KEYS-CASH"),
            sheet,
            amount=40.0,
            document_type="cash",
        )
        self._create_seller_deposit(sheet, amount=25.0)
        force_sheet_state(sheet, "submitted")
        sheet.write({"commission_withheld": 5.0})
        self.assertEqual(sheet.cash_on_hand, 10.0)
        payload = sheet._collection_report_data()
        tendered = payload["tendered"]
        for key in (
            "cash",
            "deposits",
            "checks",
            "transfers",
            "echecks",
            "retentions",
            "seller_deposits",
            "total",
        ):
            self.assertIn(key, tendered)
        self.assertEqual(tendered["cash"], 10.0)
        self.assertEqual(tendered["transfers"], 100.0)
        self.assertEqual(tendered["seller_deposits"], 25.0)
        self.assertEqual(tendered["total"], 10.0 + 100.0 + 25.0)
        recon = payload["recon"]
        self.assertEqual(recon["collected"], payload["collected_total"])
        self.assertEqual(recon["withheld"], 5.0)
        self.assertEqual(recon["net_due"], payload["collected_total"] - 5.0)
        self.assertEqual(recon["tendered"], tendered["total"])
        self.assertEqual(recon["difference"], tendered["total"] - recon["net_due"])

    def test_tendered_cash_deposit_is_not_seller_deposits(self):
        """cash_deposit MUST stay in deposits, never seller_deposits."""
        sheet = self._create_sheet()
        self._balanced(
            amount=20.0,
            sheet=sheet,
            customer="RPT-DEP-NOT-SD",
            voucher_extra={"document_type": "cash_deposit"},
        )
        remittance = self._create_seller_deposit(sheet, amount=80.0)
        tendered = sheet._collection_report_data()["tendered"]
        self.assertEqual(tendered["deposits"], 20.0)
        self.assertEqual(tendered["seller_deposits"], remittance.amount)
        self.assertNotEqual(tendered["seller_deposits"], tendered["deposits"])

    def test_recon_reachable_states(self):
        """Computed cash makes the sheet balance.

        ``in_favor`` and ``outstanding`` are unreachable once ``cash_on_hand`` is
        derived: the cash the seller brings is defined as the remainder, and
        every collected type is tendered. Both branches are covered directly
        below.
        """
        statuses = []
        # balanced: transfer 100, no cash, withheld 0 → tendered 100, net_due 100
        seller_a = create_internal_seller(self.env, "rpt-recon-a")
        sheet_a = self._create_sheet(seller=seller_a, force_new=True)
        self._balanced(
            amount=100.0,
            sheet=sheet_a,
            customer="RPT-BAL",
            voucher_extra={"document_type": "bank_transfer"},
        )
        statuses.append(sheet_a._collection_report_data()["recon"]["status"])

        # balanced with cash: cash 50 collected, none remitted, nothing withheld
        seller_b = create_internal_seller(self.env, "rpt-recon-b")
        sheet_b = self._create_sheet(seller=seller_b, force_new=True)
        self._balanced(
            amount=50.0,
            sheet=sheet_b,
            customer="RPT-CASH-BAL",
            voucher_extra={"document_type": "cash"},
        )
        self.assertEqual(sheet_b.cash_on_hand, 50.0)
        statuses.append(sheet_b._collection_report_data()["recon"]["status"])

        self.assertEqual(statuses, ["balanced", "balanced"])
        recon = sheet_b._collection_report_data()["recon"]
        for key in (
            "collected",
            "withheld",
            "net_due",
            "tendered",
            "difference",
            "status",
            "status_message",
        ):
            self.assertIn(key, recon)
        self.assertTrue(recon["status_message"])

    def test_recon_in_favor_branch(self):
        """A tendered total above net due MUST still map to in_favor."""
        _allocation, _voucher, sheet, _partner = self._balanced(
            amount=100.0,
            customer="RPT-FAVOR",
            voucher_extra={"document_type": "bank_transfer"},
        )
        tendered = dict(sheet._collection_report_tendered(), total=150.0)
        recon = sheet._collection_report_recon(100.0, tendered)
        self.assertEqual(recon["difference"], 50.0)
        self.assertEqual(recon["status"], "in_favor")

    def test_recon_outstanding_branch(self):
        """A tendered total below net due MUST still map to outstanding."""
        _allocation, _voucher, sheet, _partner = self._balanced(
            amount=100.0,
            customer="RPT-OUTSTANDING",
            voucher_extra={"document_type": "bank_transfer"},
        )
        tendered = dict(sheet._collection_report_tendered(), total=60.0)
        recon = sheet._collection_report_recon(100.0, tendered)
        self.assertEqual(recon["difference"], -40.0)
        self.assertEqual(recon["status"], "outstanding")

    def test_unallocated_voucher_mismatch(self):
        """Unallocated sheet voucher MUST set mismatch and still count in collected."""
        allocation, allocated, sheet, _partner = self._balanced(amount=40.0)
        stray_partner = dummy_customer_partner(self.env, customer="RPT-STRAY")
        stray = self._create_voucher(stray_partner, sheet, amount=15.0)
        self.assertFalse(stray.allocation_id)
        payload = sheet._collection_report_data()
        self.assertTrue(payload["mismatch"])
        self.assertEqual(payload["collected_total"], allocated.amount + stray.amount)
        self.assertEqual(
            payload["customer_totals"]["collected"], allocation.total_vouchers
        )
        self.assertNotEqual(
            payload["collected_total"], payload["customer_totals"]["collected"]
        )

    def test_unallocated_remittance_does_not_mismatch(self):
        """Unallocated seller_deposit MUST NOT set mismatch or inflate collected."""
        allocation, allocated, sheet, _partner = self._balanced(amount=40.0)
        remittance = self._create_seller_deposit(sheet, amount=80.0)
        self.assertFalse(remittance.allocation_id)
        payload = sheet._collection_report_data()
        self.assertFalse(payload["mismatch"])
        self.assertEqual(payload["collected_total"], allocated.amount)
        self.assertEqual(
            payload["customer_totals"]["collected"], allocation.total_vouchers
        )
        self.assertEqual(
            payload["collected_total"],
            payload["customer_totals"]["collected"],
        )

    def test_unallocated_remittance_does_not_hide_stray_mismatch(self):
        """A stray non-remittance voucher MUST still mismatch beside remittance."""
        _allocation, allocated, sheet, _partner = self._balanced(amount=40.0)
        stray_partner = dummy_customer_partner(self.env, customer="RPT-STRAY-CASH")
        stray = self._create_voucher(
            stray_partner, sheet, amount=15.0, document_type="cash"
        )
        remittance = self._create_seller_deposit(sheet, amount=80.0)
        self.assertFalse(stray.allocation_id)
        self.assertFalse(remittance.allocation_id)
        payload = sheet._collection_report_data()
        self.assertTrue(payload["mismatch"])
        self.assertEqual(payload["collected_total"], allocated.amount + stray.amount)
        self.assertNotEqual(
            payload["collected_total"],
            allocated.amount + stray.amount + remittance.amount,
        )

    def test_unsaved_sheet_refused(self):
        """Unsaved (NewId) sheets MUST raise UserError and return no payload."""
        ensure_enabled_seller(self.env, self.seller)
        sheet = self.env["collection.sheet"].new(
            {"seller_id": self.seller.id, "company_id": self.env.company.id}
        )
        with self.assertRaises(UserError) as error:
            sheet._collection_report_data()
        self.assertIn("saved", str(error.exception).lower())

    def test_mixed_currency_refused(self):
        """Mixed allocation currencies MUST raise UserError with no payload."""
        sheet = self._create_sheet()
        usd = self.env.ref("base.USD")
        eur = self.env.ref("base.EUR")
        self.assertNotEqual(usd, eur)
        first_partner = dummy_customer_partner(self.env, customer="RPT-USD")
        second_partner = dummy_customer_partner(self.env, customer="RPT-EUR")
        first_voucher = self._create_voucher(first_partner, sheet, amount=10.0)
        second_voucher = self._create_voucher(second_partner, sheet, amount=20.0)
        self._create_allocation(
            sheet,
            first_partner,
            vouchers=first_voucher,
            lines=[self._line_vals(amount_applied=10.0, invoice_balance=10.0)],
            currency_id=usd.id,
        )
        self._create_allocation(
            sheet,
            second_partner,
            vouchers=second_voucher,
            lines=[self._line_vals(amount_applied=20.0, invoice_balance=20.0)],
            currency_id=eur.id,
        )
        with self.assertRaises(UserError) as error:
            sheet._collection_report_data()
        self.assertIn("currenc", str(error.exception).lower())

    def test_report_source_has_no_sudo(self):
        """Report inherit MUST NOT call sudo() and helpers MUST be private."""
        self.assertTrue(_REPORT_SOURCE.is_file(), _REPORT_SOURCE)
        source = _REPORT_SOURCE.read_text(encoding="utf-8")
        code = "\n".join(
            line for line in source.splitlines() if not line.lstrip().startswith("#")
        )
        self.assertNotIn(".sudo(", code)
        self.assertNotIn("sudo()", code)
        self.assertNotIn("_collection_active_connector", code)
        sheet = self._create_sheet()
        method = type(sheet)._collection_report_data
        self.assertTrue(callable(method))
        for name in _PRIVATE_HELPERS:
            helper = getattr(type(sheet), name)
            self.assertTrue(callable(helper), name)
            self.assertTrue(
                getattr(helper, "_api_private", False),
                f"{name} MUST be @api.private",
            )
        write_src = inspect.getsource(type(sheet).write)
        self.assertIn("super().write", write_src)

    def test_payload_currency_name_and_invoice_balance(self):
        """Header currency and Facturas saldo MUST come from payload primitives."""
        partner = dummy_customer_partner(self.env, customer="RPT-SALDO")
        sheet = self._create_sheet()
        voucher = self._create_voucher(partner, sheet, amount=80.0)
        self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[
                self._line_vals(
                    amount_applied=80.0,
                    invoice_balance=321.5,
                    invoice_number="FAC-SALDO",
                )
            ],
        )
        payload = sheet._collection_report_data()
        self.assertEqual(payload["currency_name"], sheet.currency_id.name)
        self.assertTrue(payload["currency_name"])
        row = payload["document_blocks"][0]["rows"][0]
        self.assertEqual(row["invoice_balance"], 321.5)
        self.assertEqual(row["amount_applied"], 80.0)
        self.assertEqual(payload["customers"][0]["debt"], 321.5)
        self.assertEqual(payload["customers"][0]["collected"], 80.0)
        self.assertEqual(payload["customers"][0]["applied"], 80.0)
        self.assertEqual(payload["customers"][0]["residual"], 241.5)
        self.assertEqual(payload["customer_totals"]["debt"], 321.5)

    def test_payload_voucher_numbers_and_check_details(self):
        """Transfers print voucher_number; checks print check fields or blanks."""
        sheet = self._create_sheet()
        partner = dummy_customer_partner(self.env, customer="RPT-COMP")
        transfer = self._create_voucher(
            partner,
            sheet,
            amount=10.0,
            document_type="bank_transfer",
            voucher_number="TRF-123",
        )
        check = self._create_voucher(
            partner,
            sheet,
            amount=20.0,
            document_type="check",
            check_number="CHK-456",
            check_bank="Banco Nación",
            check_type="deferred",
            check_issue_date=date(2026, 3, 1),
            check_payment_date=date(2026, 4, 15),
        )
        blank_check = self._create_voucher(
            partner,
            sheet,
            amount=5.0,
            document_type="check",
            check_number="CHK-PRE-BLANK",
        )
        # Blank check_number can no longer be created through the ORM
        # (_check_check_number_required); simulate a legacy/pre-existing
        # record with no check_number so the report's blank-rendering path
        # (still reachable for old data) stays covered.
        self.env.cr.execute(
            "UPDATE collection_voucher SET check_number = '' WHERE id = %s",
            (blank_check.id,),
        )
        self.env.invalidate_all()
        self._create_allocation(
            sheet,
            partner,
            vouchers=transfer | check | blank_check,
            lines=[self._line_vals(amount_applied=35.0, invoice_balance=35.0)],
        )
        payload = sheet._collection_report_data()
        by_code = {block["code"]: block["rows"] for block in payload["voucher_blocks"]}
        transfer_row = by_code["bank_transfer"][0]
        self.assertEqual(transfer_row["number"], "TRF-123")
        self.assertNotEqual(transfer_row["number"], transfer.name)
        check_rows = {row["number"]: row for row in by_code["check"]}
        filled = check_rows["CHK-456"]
        self.assertNotEqual(filled["number"], check.name)
        self.assertEqual(filled["check_bank"], "Banco Nación")
        self.assertEqual(filled["check_type"], "Diferido")
        self.assertEqual(filled["date"], date(2026, 3, 1))
        self.assertEqual(filled["check_payment_date"], date(2026, 4, 15))
        blank = check_rows[""]
        self.assertEqual(blank["number"], "")
        self.assertNotEqual(blank_check.name, "")
        self.assertEqual(blank["check_bank"], "")
        self.assertEqual(blank["check_type"], "")
        self.assertFalse(blank["date"])
        self.assertFalse(blank["check_payment_date"])

    def test_payload_spanish_argentina_labels(self):
        """Report labels and recon copy MUST be Spanish Argentina, not English."""
        sheet = self._create_sheet()
        self._balanced(amount=40.0, sheet=sheet)
        payload = sheet._collection_report_data()
        self.assertEqual(payload["state_label"], "Abierta")
        self.assertNotIn("Open", payload["state_label"])
        labels = {block["code"]: block["label"] for block in payload["voucher_blocks"]}
        self.assertEqual(labels["bank_transfer"], "Transferencia bancaria")
        recon = payload["recon"]
        self.assertEqual(recon["status"], "balanced")
        self.assertEqual(recon["status_message"], "Cuadrada")
        self.assertNotIn("Balanced", recon["status_message"])
        self.assertNotIn("In favor", recon["status_message"])
        self.assertNotIn("Outstanding", recon["status_message"])

    def test_commission_excluded_from_collected_and_tendered(self):
        """seller_commission MUST stay out of collected_total, tendered, and blocks."""
        allocation, cash, sheet, _partner = self._balanced(
            amount=500.0,
            customer="RPT-SC-COLLECTED",
            voucher_extra={"document_type": "cash"},
        )
        self._enable_seller_commission_type(company=sheet.company_id)
        self._funded_cash_receipt(allocation, cash)
        self._mark_validated_collections(sheet.voucher_ids)
        self._submit_declared_cash(sheet, 300.0)
        sheet.action_confirm()
        commissions = self._commission_vouchers(sheet)
        self.assertEqual(len(commissions), 1)
        self.assertAlmostEqual(commissions.amount, 300.0, places=2)
        payload = sheet._collection_report_data()
        codes = [block["code"] for block in payload["voucher_blocks"]]
        self.assertGreater(len(payload["voucher_blocks"]), 0)
        self.assertEqual(payload["collected_total"], 500.0)
        self.assertNotIn("seller_commission", codes)
        self.assertNotEqual(payload["collected_total"], 500.0 + commissions.amount)
        self.assertAlmostEqual(payload["tendered"]["total"], 200.0, places=2)
        self.assertNotEqual(
            payload["tendered"]["total"],
            200.0 + commissions.amount,
        )
        self.assertNotIn("seller_commission", payload["tendered"])
        self.assertNotIn("seller_commissions", payload["tendered"])

    def test_commission_excluded_from_collected_triangulation(self):
        """A different cash/withheld pair MUST still drop the minted commission."""
        allocation, cash, sheet, _partner = self._balanced(
            amount=100.0,
            customer="RPT-SC-COLLECTED-TRI",
            voucher_extra={"document_type": "cash"},
        )
        self._enable_seller_commission_type(company=sheet.company_id)
        self._funded_cash_receipt(allocation, cash)
        self._mark_validated_collections(sheet.voucher_ids)
        self._submit_declared_cash(sheet, 60.0)
        sheet.action_confirm()
        payload = sheet._collection_report_data()
        codes = [block["code"] for block in payload["voucher_blocks"]]
        self.assertEqual(payload["collected_total"], 100.0)
        self.assertNotIn("seller_commission", codes)
        self.assertAlmostEqual(payload["tendered"]["total"], 40.0, places=2)

    def test_recon_unchanged_by_commission_mint(self):
        """Minting seller_commission MUST leave every recon key unchanged."""
        allocation, cash, sheet, _partner = self._balanced(
            amount=500.0,
            customer="RPT-SC-RECON-CASH",
            voucher_extra={"document_type": "cash"},
        )
        self._enable_seller_commission_type(company=sheet.company_id)
        self._funded_cash_receipt(allocation, cash)
        self._mark_validated_collections(sheet.voucher_ids)
        self._submit_declared_cash(sheet, 300.0)
        before = dict(sheet._collection_report_data()["recon"])
        self.assertAlmostEqual(before["difference"], 0.0, places=2)
        self.assertEqual(before["status"], "balanced")
        sheet.action_confirm()
        self.assertEqual(len(self._commission_vouchers(sheet)), 1)
        after = sheet._collection_report_data()["recon"]
        self.assertEqual(set(after), set(before))
        for key, value in before.items():
            self.assertEqual(after[key], value, key)
        self.assertAlmostEqual(after["difference"], 0.0, places=2)

    def test_cash_banked_excludes_seller_commission(self):
        """cash_banked MUST sum seller_deposit only, never seller_commission."""
        sheet = self._create_sheet()
        self._balanced(
            amount=20.0,
            sheet=sheet,
            customer="RPT-BANK-SC",
            voucher_extra={"document_type": "cash_deposit"},
        )
        remittance = self._create_seller_deposit(sheet, amount=80.0)
        commission = self._create_seller_commission(sheet, amount=30.0)
        payload = sheet._collection_report_data()
        self.assertEqual(payload["cash_banked"], 80.0)
        self.assertEqual(sheet.cash_banked, remittance.amount)
        self.assertNotEqual(
            payload["cash_banked"], remittance.amount + commission.amount
        )
        self.assertNotEqual(payload["cash_banked"], commission.amount)

    def test_tendered_explicitly_excludes_seller_commission(self):
        """tendered MUST name seller_commission so exclusion is not fall-through."""
        sheet = self._create_sheet()
        source = inspect.getsource(type(sheet)._collection_report_tendered)
        self.assertIn("seller_commission", source)
        blocks = inspect.getsource(type(sheet)._collection_report_voucher_blocks)
        self.assertIn("seller_commission", blocks)

    def test_residual_cash_value_total_from_cash_receipt_values(self):
        """residual_cash_value_total MUST equal leftover cash receipt values."""
        allocation, cash, sheet, _partner = self._balanced(
            amount=100.0,
            customer="RPT-RESIDUAL-40",
            voucher_extra={"document_type": "cash"},
        )
        self._enable_seller_commission_type(company=sheet.company_id)
        _receipt, cash_value = self._funded_cash_receipt(allocation, cash)
        self._mark_validated_collections(sheet.voucher_ids)
        self._submit_declared_cash(sheet, 60.0)
        sheet.action_confirm()
        self.assertEqual(sheet.state, "proposal")
        self.assertAlmostEqual(cash_value.amount, 40.0, places=2)
        self.assertAlmostEqual(sheet.residual_cash_value_total, 40.0, places=2)
        self.assertNotEqual(sheet.residual_cash_value_total, 0.0)
        self.assertNotEqual(sheet.residual_cash_value_total, 100.0)

    def test_residual_includes_issued_cash_values(self):
        """Issued cash receipt values MUST still count toward residual cash."""
        allocation, cash, sheet, _partner = self._balanced(
            amount=40.0,
            customer="RPT-RESIDUAL-ISSUED",
            voucher_extra={"document_type": "cash"},
        )
        receipt, cash_value = self._funded_cash_receipt(allocation, cash)
        self._mark_issued(receipt, "ERP-RESIDUAL-ISSUED")
        self.assertEqual(receipt.state, "issued")
        self.assertAlmostEqual(cash_value.amount, 40.0, places=2)
        self.assertAlmostEqual(sheet.residual_cash_value_total, 40.0, places=2)

    def test_residual_computes_while_submitted_but_is_not_enforced(self):
        """Submitted residual MUST still compute; Confirm is not blocked by it."""
        allocation, cash, sheet, _partner = self._balanced(
            amount=80.0,
            customer="RPT-RESIDUAL-SUBMITTED",
            voucher_extra={"document_type": "cash"},
        )
        self._enable_seller_commission_type(company=sheet.company_id)
        self._funded_cash_receipt(allocation, cash)
        self._mark_validated_collections(sheet.voucher_ids)
        self._submit_declared_cash(sheet, 25.0)
        self.assertEqual(sheet.state, "submitted")
        self.assertAlmostEqual(sheet.residual_cash_value_total, 80.0, places=2)
        sheet.action_confirm()
        self.assertEqual(sheet.state, "proposal")
        self.assertAlmostEqual(sheet.residual_cash_value_total, 55.0, places=2)

    def test_residual_never_blocks_close(self):
        """Non-zero residual_cash_value_total MUST NOT block Close."""
        allocation, cash, sheet, _partner = self._balanced(
            amount=100.0,
            customer="RPT-RESIDUAL-CLOSE",
            voucher_extra={"document_type": "cash"},
        )
        self._enable_seller_commission_type(company=sheet.company_id)
        self._funded_cash_receipt(allocation, cash)
        self._mark_validated_collections(sheet.voucher_ids)
        self._submit_declared_cash(sheet, 60.0)
        sheet.action_confirm()
        self.assertGreater(sheet.residual_cash_value_total, 0.0)
        sheet.action_close()
        self.assertEqual(sheet.state, "closed")
        self.assertAlmostEqual(sheet.residual_cash_value_total, 40.0, places=2)

    def test_residual_is_outside_recon_algebra(self):
        """residual_cash_value_total MUST NOT feed recon or tendered.total."""
        allocation, cash, sheet, _partner = self._balanced(
            amount=100.0,
            customer="RPT-RESIDUAL-RECON",
            voucher_extra={"document_type": "cash"},
        )
        self._enable_seller_commission_type(company=sheet.company_id)
        self._funded_cash_receipt(allocation, cash)
        self._mark_validated_collections(sheet.voucher_ids)
        self._submit_declared_cash(sheet, 60.0)
        before = sheet._collection_report_data()
        before_tendered = before["tendered"]["total"]
        before_recon = dict(before["recon"])
        sheet.action_confirm()
        self.assertGreater(sheet.residual_cash_value_total, 0.0)
        payload = sheet._collection_report_data()
        self.assertNotIn("residual_cash_value_total", payload)
        self.assertNotIn("residual_cash_value_total", payload["recon"])
        self.assertEqual(payload["tendered"]["total"], before_tendered)
        self.assertEqual(payload["recon"], before_recon)
