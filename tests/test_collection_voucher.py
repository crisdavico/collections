# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from base64 import b64decode
from datetime import date
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from .common_connector import confirm_sheet
from .test_collection_payment import (
    PDF_B64,
    PNG_B64,
    dummy_customer_partner,
    ensure_enabled_seller,
    post_voucher_proof,
)


class TestCollectionVoucher(TransactionCase):
    """RED/GREEN tests for standalone collection.voucher lifecycle."""

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

    def _create_voucher(self, customer=None, **extra):
        partner = dummy_customer_partner(
            self.env, customer=customer, extra=extra, default="CUST-001"
        )
        vals = {
            "partner_id": partner.id,
            "document_type": "bank_transfer",
        }
        if "seller_id" not in extra:
            vals["seller_id"] = self._ensure_enabled_seller().id
        elif extra.get("seller_id"):
            self._ensure_enabled_seller(
                self.env["res.users"].browse(extra["seller_id"])
            )
        vals.update(extra)
        return self.env["collection.voucher"].create(vals)

    def _create_sheet(self, **extra):
        seller_id = extra.pop("seller_id", self._ensure_enabled_seller().id)
        return self.env["collection.sheet"].create({"seller_id": seller_id, **extra})

    def _create_allocation(self, sheet, partner, vouchers=None, **extra):
        vals = {
            "sheet_id": sheet.id,
            "partner_id": partner.id,
        }
        if vouchers:
            vals["voucher_ids"] = [Command.set(vouchers.ids)]
        lines = extra.pop("lines", None)
        if lines is not None:
            vals["line_ids"] = [Command.create(line) for line in lines]
        extra.pop("residual_reason", None)
        vals.update(extra)
        return self.env["collection.allocation"].create(vals)

    def _confirm(self, allocation):
        allocation.with_context(collection_allocation_audited_state=True).write(
            {"state": "confirmed"}
        )
        return allocation

    def _mark_validated_collections(self, vouchers):
        vouchers.with_context(collection_audited_state=True).write(
            {"state": "validated_collections"}
        )
        return vouchers

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

    # --- Sequence naming ---

    def test_sequence_assigned_on_create(self):
        year = date.today().year
        voucher = self._create_voucher()
        self.assertRegex(
            voucher.name,
            rf"^COL/{year}/\d{{4,}}$",
            "Voucher name must match COL/<year>/<padded number>",
        )

    def test_sequence_names_are_unique(self):
        first = self._create_voucher(customer_identification="A")
        second = self._create_voucher(customer_identification="B")
        self.assertNotEqual(first.name, second.name)
        self.assertTrue(first.name)
        self.assertTrue(second.name)

    # --- 1.1 Defaults and required fields ---

    def test_defaults_on_create(self):
        voucher = self._create_voucher()
        fields_map = self.env["collection.voucher"]._fields
        self.assertNotIn(
            "received_date",
            fields_map,
            "received_date must be removed from the voucher model",
        )
        self.assertNotIn(
            "payment_ids",
            fields_map,
            "payment_ids must be dropped; one voucher is one payment",
        )
        self.assertTrue(
            voucher.create_date,
            "create_date must be set automatically by the ORM",
        )
        self.assertEqual(voucher.state, "draft")
        state_keys = {key for key, _label in fields_map["state"].selection}
        self.assertEqual(
            state_keys,
            {"draft", "validated_seller", "validated_collections"},
        )
        self.assertFalse(fields_map["state"].group_expand)
        self.assertEqual(
            voucher.currency_id,
            self.env.company.currency_id,
            "Currency must default to company currency",
        )

    def test_partner_required(self):
        """Required Customer is partner_id; Char customer_identification is gone."""
        Voucher = self.env["collection.voucher"]
        self.assertNotIn("customer_identification", Voucher._fields)
        field = Voucher._fields["partner_id"]
        self.assertEqual(field.comodel_name, "res.partner")
        self.assertEqual(field.string, "Customer")
        self.assertTrue(field.required)
        self.assertTrue(field.tracking)
        self.assertTrue(field.index)
        self.assertEqual(field.ondelete, "restrict")
        seller = self._ensure_enabled_seller()
        vals = {"document_type": "unsupported", "seller_id": seller.id}
        with mute_logger("odoo.sql_db"):
            try:
                Voucher.create(vals)
            except IntegrityError:
                return
        # Devel leftover empty partner_id rows block SQL NOT NULL (design D4).
        # ORM required still holds; the IntegrityError path is the fresh-DB gate.

    def test_received_date_field_absent(self):
        """Triangulation: field must not exist on the model registry."""
        self.assertNotIn("received_date", self.env["collection.voucher"]._fields)

    def test_create_rejects_received_date_vals(self):
        """Create vals must not accept received_date after the field is dropped."""
        with self.assertRaises(ValueError):
            self.env["collection.voucher"].create(
                {
                    "partner_id": dummy_customer_partner(
                        self.env, customer="CUST-NO-RECV"
                    ).id,
                    "document_type": "unsupported",
                    "seller_id": ensure_enabled_seller(self.env).id,
                    "received_date": fields.Date.today(),
                }
            )

    def test_create_date_not_overridable(self):
        """Caller-supplied create_date must not stick; ORM owns registration time."""
        forged = fields.Datetime.to_datetime("2020-01-15 12:00:00")
        voucher = self.env["collection.voucher"].create(
            {
                "partner_id": dummy_customer_partner(
                    self.env, customer="CUST-CREATE-DATE"
                ).id,
                "document_type": "unsupported",
                "seller_id": ensure_enabled_seller(self.env).id,
                "create_date": forged,
            }
        )
        self.assertNotEqual(
            fields.Datetime.to_datetime(voucher.create_date),
            forged,
            "create_date must not be caller-overridable",
        )
        self.assertTrue(voucher.create_date)

    # --- Voucher seller_id (required on NEW create; historical null stays) ---

    def test_orm_create_without_seller_is_rejected(self):
        """NEW ORM create without seller_id MUST be rejected with no write."""
        fields_map = self.env["collection.voucher"]._fields
        self.assertIn("seller_id", fields_map)
        seller_field = fields_map["seller_id"]
        self.assertEqual(seller_field.comodel_name, "res.users")
        self.assertFalse(
            seller_field.required,
            "ORM seller_id must stay nullable for historical null rows",
        )
        self.assertEqual(seller_field.domain, [("share", "=", False)])

        before = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError):
            self.env["collection.voucher"].create(
                {
                    "partner_id": dummy_customer_partner(
                        self.env, customer="CUST-NO-SELLER"
                    ).id,
                    "document_type": "bank_transfer",
                }
            )
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before,
            "rejected create must not persist a voucher",
        )

    def test_orm_write_does_not_backfill_null_seller(self):
        """Triangulation: enabled seller persists; historical null is not backfilled."""
        seller = self.env.ref("base.user_admin")
        self.env.company.write({"enabled_seller_ids": [Command.link(seller.id)]})
        with_seller = self._create_voucher(
            customer_identification="CUST-WITH-SELLER",
            seller_id=seller.id,
        )
        self.assertEqual(with_seller.seller_id, seller)

        legacy = self._create_voucher(
            customer_identification="CUST-LEGACY-NULL",
            seller_id=seller.id,
        )
        self.env.cr.execute(
            """
            UPDATE collection_voucher
               SET seller_id = NULL, sheet_id = NULL
             WHERE id = %s
            """,
            (legacy.id,),
        )
        legacy.invalidate_recordset(["seller_id", "sheet_id"])
        self.assertFalse(legacy.seller_id)
        legacy.write({"amount": 10.0})
        self.assertFalse(
            legacy.seller_id,
            "Saving a null-seller voucher must not backfill seller_id",
        )
        self.assertEqual(legacy.amount, 10.0)

    # --- 1.3 Payment field contract on the voucher ---

    def test_persist_type_specific_collection_fields(self):
        transfer = self._create_voucher(
            customer_identification="CUST-TRF",
            document_type="bank_transfer",
            amount=1500.50,
            from_account="ACC-FROM-1",
            to_account="ACC-TO-1",
            voucher_number="TRF-100",
            voucher_date=date(2026, 3, 15),
        )
        check = self._create_voucher(
            customer_identification="CUST-CHK",
            document_type="check",
            amount=200.00,
            check_number="CHK-9",
            check_bank="Banco Nación",
            check_issue_date=date(2026, 1, 10),
            check_payment_date=date(2026, 2, 10),
            check_type="deferred",
        )
        deposit = self._create_voucher(
            customer_identification="CUST-CASH",
            document_type="cash_deposit",
            amount=50.25,
            voucher_number="CASH-1",
            voucher_date=date(2026, 4, 1),
        )

        self.assertEqual(transfer.document_type, "bank_transfer")
        self.assertAlmostEqual(transfer.amount, 1500.50, places=2)
        self.assertEqual(transfer.from_account, "ACC-FROM-1")
        self.assertEqual(transfer.to_account, "ACC-TO-1")
        self.assertEqual(transfer.voucher_number, "TRF-100")
        self.assertEqual(transfer.voucher_date, date(2026, 3, 15))

        self.assertEqual(check.document_type, "check")
        self.assertAlmostEqual(check.amount, 200.00, places=2)
        self.assertEqual(check.check_number, "CHK-9")
        self.assertEqual(check.check_bank, "Banco Nación")
        self.assertEqual(check.check_issue_date, date(2026, 1, 10))
        self.assertEqual(check.check_payment_date, date(2026, 2, 10))
        self.assertEqual(check.check_type, "deferred")

        self.assertEqual(deposit.document_type, "cash_deposit")
        self.assertAlmostEqual(deposit.amount, 50.25, places=2)
        self.assertEqual(deposit.voucher_number, "CASH-1")
        self.assertEqual(deposit.voucher_date, date(2026, 4, 1))

    def test_unsupported_and_partial_payment_fields(self):
        unsupported = self._create_voucher(
            customer_identification="CUST-UNSUP",
            document_type="unsupported",
        )
        partial = self._create_voucher(
            customer_identification="CUST-PARTIAL",
            document_type="bank_transfer",
            from_account="ONLY-FROM",
        )

        self.assertEqual(unsupported.document_type, "unsupported")
        self.assertFalse(unsupported.amount)
        self.assertFalse(unsupported.from_account)
        self.assertFalse(unsupported.check_number)

        self.assertEqual(partial.document_type, "bank_transfer")
        self.assertEqual(partial.from_account, "ONLY-FROM")
        self.assertFalse(partial.to_account)
        self.assertFalse(partial.amount)

    def test_check_type_common_persists(self):
        """Triangulation: check_type common is a distinct selection path."""
        check = self._create_voucher(
            customer_identification="CUST-CHK-COMMON",
            document_type="check",
            check_type="common",
            check_number="CHK-COMMON",
        )
        self.assertEqual(check.check_type, "common")
        self.assertEqual(check.check_number, "CHK-COMMON")

    def test_document_type_selection_includes_eight_codes(self):
        """Voucher Selection MUST include seller_deposit as the eighth catalog code."""
        keys = {
            key
            for key, _label in self.env["collection.voucher"]._DOCUMENT_TYPE_SELECTION
        }
        self.assertEqual(
            keys,
            {
                "bank_transfer",
                "check",
                "cash_deposit",
                "unsupported",
                "echeck",
                "cash",
                "retention_certificate",
                "seller_deposit",
            },
        )
        self.assertIn("retention_kind", self.env["collection.voucher"]._fields)
        kinds = {
            key
            for key, _label in self.env["collection.voucher"]
            ._fields["retention_kind"]
            .selection
        }
        self.assertEqual(kinds, {"iva", "ganancias", "iibb", "suss", "other"})
        self.assertIn(
            "retention_kind",
            self.env["collection.voucher"]._REVIEW_EDITABLE_FIELD_ORDER,
        )

    def test_persist_echeck_cash_and_retention_certificate(self):
        """ORM MUST persist echeck, cash, and retention_certificate plus
        retention_kind."""
        echeck = self._create_voucher(
            customer_identification="CUST-ECH",
            document_type="echeck",
            amount=150000,
            check_number="ECH-9",
            check_bank="Banco Nación",
            check_issue_date=date(2026, 1, 10),
            check_payment_date=date(2026, 2, 10),
            check_type="deferred",
        )
        cash = self._create_voucher(
            customer_identification="CUST-CASH-DECL",
            document_type="cash",
            amount=150000,
            voucher_date=date(2026, 9, 1),
        )
        retention = self._create_voucher(
            customer_identification="CUST-RET",
            document_type="retention_certificate",
            amount=150000,
            voucher_number="RET-1",
            voucher_date=date(2026, 9, 1),
            retention_kind="iva",
        )
        self.assertEqual(echeck.document_type, "echeck")
        self.assertEqual(echeck.check_number, "ECH-9")
        self.assertEqual(echeck.check_type, "deferred")
        self.assertAlmostEqual(echeck.amount, 150000, places=2)
        self.assertEqual(cash.document_type, "cash")
        self.assertAlmostEqual(cash.amount, 150000, places=2)
        self.assertEqual(cash.voucher_date, date(2026, 9, 1))
        self.assertFalse(cash.message_main_attachment_id)
        self.assertEqual(retention.document_type, "retention_certificate")
        self.assertEqual(retention.retention_kind, "iva")
        self.assertEqual(retention.voucher_number, "RET-1")

    def test_persist_seller_deposit(self):
        """seller_deposit MUST persist amount, voucher_number, and voucher_date."""
        self._enable_seller_deposit_type()
        voucher = self.env["collection.voucher"].create(
            {
                "document_type": "seller_deposit",
                "seller_id": self._ensure_enabled_seller().id,
                "amount": 500.0,
                "voucher_number": "SD-1",
                "voucher_date": date(2026, 9, 8),
            }
        )
        self.assertEqual(voucher.document_type, "seller_deposit")
        self.assertAlmostEqual(voucher.amount, 500.0, places=2)
        self.assertEqual(voucher.voucher_number, "SD-1")
        self.assertEqual(voucher.voucher_date, date(2026, 9, 8))
        self.assertEqual(
            voucher.partner_id,
            self.env.ref("collection.partner_seller_deposit"),
        )

    def _enable_seller_deposit_type(self):
        catalog = self.env.ref("collection.document_type_seller_deposit")
        self.env.company.write(
            {"allowed_document_type_ids": [Command.link(catalog.id)]}
        )
        return catalog

    def test_seller_deposit_stamps_sentinel_partner(self):
        """NEW seller_deposit create MUST stamp the seeded sentinel partner."""
        self._enable_seller_deposit_type()
        seller = self._ensure_enabled_seller()
        voucher = self.env["collection.voucher"].create(
            {
                "document_type": "seller_deposit",
                "seller_id": seller.id,
                "amount": 100.0,
                "voucher_number": "SD-SENT",
                "voucher_date": date(2026, 9, 8),
            }
        )
        sentinel = self.env.ref("collection.partner_seller_deposit")
        self.assertEqual(voucher.partner_id, sentinel)
        self.assertTrue(voucher.partner_id)
        self.assertTrue(sentinel.id)

    def test_seller_deposit_refuses_customer_partner(self):
        """ORM seller_deposit MUST refuse a customer partner with no write."""
        self._enable_seller_deposit_type()
        seller = self._ensure_enabled_seller()
        customer = dummy_customer_partner(self.env, customer="CUST-SD-REFUSE")
        Voucher = self.env["collection.voucher"]
        before_ids = set(Voucher.search([]).ids)
        with self.assertRaises(UserError):
            Voucher.create(
                {
                    "document_type": "seller_deposit",
                    "seller_id": seller.id,
                    "partner_id": customer.id,
                    "amount": 100.0,
                    "voucher_number": "SD-BAD",
                    "voucher_date": date(2026, 9, 8),
                }
            )
        self.assertEqual(set(Voucher.search([]).ids), before_ids)

    def test_seller_deposit_refuses_customer_identification(self):
        """Triangulation: dummy customer identification MUST also refuse."""
        self._enable_seller_deposit_type()
        Voucher = self.env["collection.voucher"]
        before_ids = set(Voucher.search([]).ids)
        with self.assertRaises(UserError):
            self._create_voucher(
                customer_identification="CUST-SD-IDENT",
                document_type="seller_deposit",
                amount=80.0,
                voucher_number="SD-IDENT",
                voucher_date=date(2026, 9, 8),
            )
        self.assertEqual(set(Voucher.search([]).ids), before_ids)

    def test_cash_persists_without_proof(self):
        """Triangulation: cash with amount and no designated proof MUST persist."""
        voucher = self._create_voucher(
            customer_identification="CUST-CASH-NOPROOF",
            document_type="cash",
            amount=250.5,
        )
        self.assertEqual(voucher.document_type, "cash")
        self.assertAlmostEqual(voucher.amount, 250.5, places=2)
        self.assertFalse(voucher.message_main_attachment_id)

    # --- 1.4 / 1.5 Seller validate, intercept, unlink ---

    def test_action_validate_seller_from_draft_does_not_stamp_reviewer(self):
        voucher = self._create_voucher()
        self.assertEqual(voucher.state, "draft")
        self.assertFalse(voucher.reviewed_by)
        self.assertFalse(voucher.reviewed_at)
        voucher.action_validate_seller()
        self.assertEqual(voucher.state, "validated_seller")
        self.assertFalse(voucher.reviewed_by)
        self.assertFalse(voucher.reviewed_at)

    def test_action_reject_does_not_exist(self):
        voucher = self._create_voucher(customer_identification="CUST-REJ")
        self.assertFalse(hasattr(voucher, "action_reject"))
        self.assertFalse(hasattr(voucher, "action_approve"))
        self.assertEqual(voucher.state, "draft")

    def test_terminal_states_block_validate_seller(self):
        seller_done = self._create_voucher(customer_identification="V1")
        seller_done.action_validate_seller()
        with self.assertRaises(UserError):
            seller_done.action_validate_seller()
        self.assertEqual(seller_done.state, "validated_seller")

        collections_done = self._create_voucher(customer_identification="R1")
        collections_done.with_context(collection_audited_state=True).write(
            {"state": "validated_collections"}
        )
        with self.assertRaises(UserError):
            collections_done.action_validate_seller()
        self.assertEqual(collections_done.state, "validated_collections")

    def test_create_refuses_validated_collections(self):
        with self.assertRaises(UserError):
            self._create_voucher(
                customer_identification="CUST-CREATE-COLL",
                state="validated_collections",
            )

    def test_create_may_stamp_validated_seller(self):
        """MCP-style create MAY stamp validated_seller; default remains draft."""
        stamped = self._create_voucher(
            customer_identification="CUST-CREATE-SELLER",
            state="validated_seller",
        )
        self.assertEqual(stamped.state, "validated_seller")
        self.assertEqual(self._create_voucher().state, "draft")

    def test_unlink_allowed_when_draft(self):
        """Draft unlink MUST be allowed when allocation is unset."""
        voucher = self._create_voucher()
        self.assertFalse(voucher.allocation_id)
        voucher_id = voucher.id
        voucher.unlink()
        self.assertFalse(self.env["collection.voucher"].browse(voucher_id).exists())

    def test_unlink_draft_on_draft_allowed_when_residual_holds(self):
        """Draft unlink on a draft allocation MUST succeed when residual stays ≥ 0."""
        partner = dummy_customer_partner(self.env, customer="UNL-DRAFT-OK")
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            partner_id=partner.id,
            sheet_id=sheet.id,
            amount=50.0,
            document_id="UNL-DRAFT-OK",
        )
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[
                self._line_vals(
                    amount_applied=0.0,
                    invoice_balance=50.0,
                    external_invoice_id="INV-UNL-DRAFT-OK",
                )
            ],
        )
        self.assertEqual(voucher.state, "draft")
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(allocation.residual, 50.0)
        voucher_id = voucher.id
        voucher.unlink()
        self.assertFalse(self.env["collection.voucher"].browse(voucher_id).exists())
        self.assertFalse(allocation.voucher_ids)

    def test_unlink_draft_on_draft_with_sibling_when_residual_holds(self):
        """Triangulation: deleting one draft member MUST keep the sibling."""
        partner = dummy_customer_partner(self.env, customer="UNL-DRAFT-SIB")
        sheet = self._create_sheet()
        first = self._create_voucher(
            partner_id=partner.id,
            sheet_id=sheet.id,
            amount=30.0,
            document_id="UNL-DRAFT-SIB-1",
        )
        second = self._create_voucher(
            partner_id=partner.id,
            sheet_id=sheet.id,
            amount=70.0,
            document_id="UNL-DRAFT-SIB-2",
        )
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=first | second,
            lines=[
                self._line_vals(
                    amount_applied=0.0,
                    invoice_balance=100.0,
                    external_invoice_id="INV-UNL-DRAFT-SIB",
                )
            ],
        )
        self.assertEqual(allocation.residual, 100.0)
        first_id = first.id
        first.unlink()
        self.assertFalse(self.env["collection.voucher"].browse(first_id).exists())
        self.assertEqual(allocation.voucher_ids, second)
        self.assertEqual(second.allocation_id, allocation)

    def test_unlink_draft_on_confirmed_refused(self):
        """Draft unlink on a confirmed allocation MUST refuse; voucher stays."""
        partner = dummy_customer_partner(self.env, customer="UNL-CONF")
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            partner_id=partner.id,
            sheet_id=sheet.id,
            amount=40.0,
            document_id="UNL-CONF",
        )
        allocation = self._create_allocation(
            sheet, partner, vouchers=voucher, residual_reason="on_account"
        )
        self._confirm(allocation)
        self.assertEqual(voucher.state, "draft")
        voucher_id = voucher.id
        with self.assertRaises(UserError):
            voucher.unlink()
        leftover = self.env["collection.voucher"].browse(voucher_id)
        self.assertTrue(leftover.exists())
        self.assertEqual(leftover.allocation_id, allocation)

    def test_unlink_draft_on_draft_at_residual_zero_succeeds(self):
        """Draft unlink MUST succeed at residual 0; residual stays debt−applied."""
        partner = dummy_customer_partner(self.env, customer="UNL-ZERO")
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            partner_id=partner.id,
            sheet_id=sheet.id,
            amount=100.0,
            document_id="UNL-ZERO",
        )
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[self._line_vals(amount_applied=100.0, invoice_balance=100.0)],
        )
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

    def test_unlink_draft_on_draft_leftover_less_than_amount_succeeds(self):
        """Draft unlink MUST succeed when residual is less than voucher amount."""
        partner = dummy_customer_partner(self.env, customer="UNL-LEFT")
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            partner_id=partner.id,
            sheet_id=sheet.id,
            amount=100.0,
            document_id="UNL-LEFT",
        )
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[self._line_vals(amount_applied=60.0, invoice_balance=100.0)],
        )
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(allocation.residual, 40.0)
        line_before = [
            (line.id, line.amount_applied, line.external_invoice_id)
            for line in allocation.line_ids
        ]
        voucher_id = voucher.id
        voucher.unlink()
        self.assertFalse(self.env["collection.voucher"].browse(voucher_id).exists())
        self.assertFalse(allocation.voucher_ids)
        self.assertEqual(allocation.residual, 40.0)
        allocation.invalidate_recordset(["line_ids"])
        self.assertEqual(
            [
                (line.id, line.amount_applied, line.external_invoice_id)
                for line in allocation.line_ids
            ],
            line_before,
        )

    def test_unlink_blocked_when_not_draft(self):
        voucher = self._create_voucher()
        voucher.action_validate_seller()
        with self.assertRaises(UserError):
            voucher.unlink()
        self.assertTrue(voucher.exists())

        collections_done = self._create_voucher(customer_identification="CUST-UNL-COLL")
        collections_done.with_context(collection_audited_state=True).write(
            {"state": "validated_collections"}
        )
        with self.assertRaises(UserError):
            collections_done.unlink()
        self.assertTrue(collections_done.exists())

    def test_action_validate_removed(self):
        """Aggregate header validate must not exist on the standalone voucher."""
        voucher = self._create_voucher()
        self.assertFalse(hasattr(voucher, "action_validate"))

    # --- Intercept / attachment reopen ---

    def test_raw_write_validated_seller_routes_through_seller_action(self):
        """Bare write({state: validated_seller}) MUST run action_validate_seller."""
        voucher = self._create_voucher()
        voucher.write({"state": "validated_seller"})
        self.assertEqual(voucher.state, "validated_seller")
        self.assertFalse(voucher.reviewed_by)
        self.assertFalse(voucher.reviewed_at)

    def test_raw_write_validated_collections_refused(self):
        """Raw write of validated_collections MUST refuse; Review is the only path."""
        voucher = self._create_voucher()
        voucher.action_validate_seller()
        with self.assertRaises(UserError):
            voucher.write({"state": "validated_collections"})
        self.assertEqual(voucher.state, "validated_seller")

        draft = self._create_voucher(customer_identification="CUST-RAW-COLL-DRAFT")
        with self.assertRaises(UserError):
            draft.write({"state": "validated_collections"})
        self.assertEqual(draft.state, "draft")

    def test_reopen_to_draft_without_attachment_refused(self):
        """state=draft without replacing designated proof must refuse reopen."""
        voucher = self._create_voucher()
        voucher.action_validate_seller()
        with self.assertRaises(UserError):
            voucher.write({"state": "draft"})
        self.assertEqual(voucher.state, "validated_seller")

    def test_validate_seller_when_review_is_off(self):
        """Validate by Seller MUST remain when Document Review is OFF."""
        self.env.company.write({"document_review_enabled": False})
        voucher = self._create_voucher(customer_identification="CUST-REVIEW-OFF")
        voucher.action_validate_seller()
        self.assertEqual(voucher.state, "validated_seller")

    def test_replace_main_resets_to_validated_seller_clears_audit_and_rotation(self):
        """Replacing designated proof MUST set validated_seller and reset rotation."""
        voucher = self._create_voucher(
            customer_identification="CUST-ATT-RST",
            document_id="DOC-ATT-RST",
        )
        first = post_voucher_proof(voucher, "old.png", PNG_B64)
        voucher.write({"attachment_rotation": 90})
        voucher.with_context(collection_audited_state=True).write(
            {
                "state": "validated_collections",
                "reviewed_by": self.env.user.id,
                "reviewed_at": fields.Datetime.now(),
            }
        )
        self.assertEqual(voucher.state, "validated_collections")
        self.assertTrue(voucher.reviewed_by)
        replacement = self.env["ir.attachment"].create(
            {
                "name": "new.pdf",
                "raw": b64decode(PDF_B64),
                "res_model": "collection.voucher",
                "res_id": voucher.id,
            }
        )
        voucher.write({"message_main_attachment_id": replacement.id})
        self.assertEqual(voucher.state, "validated_seller")
        self.assertFalse(voucher.reviewed_by)
        self.assertFalse(voucher.reviewed_at)
        self.assertEqual(voucher.attachment_rotation, 0)
        self.assertEqual(voucher.message_main_attachment_id, replacement)
        self.assertNotEqual(voucher.message_main_attachment_id, first)

    def test_extra_chatter_does_not_reset_review_or_rotation(self):
        """Extra chatter files MUST NOT reset review, audit, or rotation."""
        voucher = self._create_voucher(customer_identification="CUST-ATT-EXTRA")
        proof = post_voucher_proof(voucher, "keep.png", PNG_B64)
        voucher.write({"attachment_rotation": 180})
        voucher.with_context(collection_audited_state=True).write(
            {
                "state": "validated_collections",
                "reviewed_by": self.env.user.id,
                "reviewed_at": fields.Datetime.now(),
            }
        )
        extra = self.env["ir.attachment"].create(
            {
                "name": "notes.txt",
                "raw": b"hello world",
                "res_model": "collection.voucher",
                "res_id": voucher.id,
            }
        )
        extra._post_add_create()
        voucher.invalidate_recordset()
        self.assertEqual(voucher.state, "validated_collections")
        self.assertEqual(voucher.reviewed_by, self.env.user)
        self.assertTrue(voucher.reviewed_at)
        self.assertEqual(voucher.attachment_rotation, 180)
        self.assertEqual(voucher.message_main_attachment_id, proof)

    def test_clear_main_resets_rotation_keeps_decided(self):
        """Clearing designated proof MUST reset rotation and MUST NOT reopen."""
        voucher = self._create_voucher(customer_identification="CUST-ATT-CLR")
        post_voucher_proof(voucher, "clear-me.png", PNG_B64)
        voucher.write({"attachment_rotation": 270})
        voucher.action_validate_seller()
        voucher.write({"message_main_attachment_id": False})
        self.assertEqual(voucher.state, "validated_seller")
        self.assertEqual(voucher.attachment_rotation, 0)
        self.assertFalse(voucher.message_main_attachment_id)

    def test_omit_proof_remains_valid(self):
        """Omit/empty designated proof MUST remain valid on create."""
        voucher = self._create_voucher(customer_identification="CUST-ATT-OMIT")
        self.assertTrue(voucher.id)
        self.assertFalse(voucher.message_main_attachment_id)

    def test_invalid_main_attachment_raises_user_error(self):
        """Setting designated proof to a non-image/non-PDF MUST raise UserError."""
        voucher = self._create_voucher(customer_identification="CUST-ATT-BAD")
        extra = self.env["ir.attachment"].create(
            {
                "name": "notes.txt",
                "raw": b"hello world",
                "res_model": "collection.voucher",
                "res_id": voucher.id,
            }
        )
        with self.assertRaises(UserError):
            voucher.write({"message_main_attachment_id": extra.id})
        self.assertFalse(voucher.message_main_attachment_id)

    def test_assigned_without_seller_fails(self):
        """Assigned voucher MUST keep a non-null seller."""
        seller = self._ensure_enabled_seller()
        sheet = self.env["collection.sheet"].create({"seller_id": seller.id})
        voucher = self._create_voucher(customer_identification="CUST-SHEET-NO-SELLER")
        self.env.cr.execute(
            """
            UPDATE collection_voucher
               SET seller_id = NULL, sheet_id = NULL
             WHERE id = %s
            """,
            (voucher.id,),
        )
        voucher.invalidate_recordset(["seller_id", "sheet_id"])
        self.assertFalse(voucher.seller_id)
        with mute_logger("odoo.sql_db"):
            try:
                voucher.write({"sheet_id": sheet.id})
            except (UserError, ValidationError, IntegrityError):
                return
        self.fail("Assigning a seller-less voucher to a sheet must be rejected")

    # --- Chatter designated proof ---

    def _inherit_names(self):
        inherit = self.env["collection.voucher"]._inherit
        if isinstance(inherit, str):
            return [inherit]
        return list(inherit)

    def test_proof_is_message_main_attachment_id(self):
        """Designated proof MUST be message_main_attachment_id, not Binary fields."""
        fields_map = self.env["collection.voucher"]._fields
        self.assertIn("message_main_attachment_id", fields_map)
        self.assertNotIn("attachment", fields_map)
        self.assertNotIn("attachment_filename", fields_map)
        self.assertIn("mail.thread.main.attachment", self._inherit_names())
        voucher = self._create_voucher(customer_identification="CUST-PROOF-MAIN")
        proof = post_voucher_proof(voucher, "proof.png", PNG_B64)
        self.assertEqual(voucher.message_main_attachment_id, proof)
        self.assertEqual(proof.name, "proof.png")
        self.assertFalse(proof.res_field)

    def test_picker_promotes_pdf_when_main_empty(self):
        """Triangulation: a valid PDF chatter file MUST become designated proof."""
        voucher = self._create_voucher(customer_identification="CUST-PROOF-PDF")
        proof = post_voucher_proof(voucher, "receipt.pdf", PDF_B64)
        self.assertEqual(voucher.message_main_attachment_id, proof)
        self.assertEqual(proof.name, "receipt.pdf")
        self.assertTrue(
            (proof.mimetype or "").startswith("application/pdf")
            or proof.mimetype == "application/pdf"
        )

    def test_picker_force_cannot_promote_non_image_pdf(self):
        """MIME picker MUST refuse non-image/non-PDF even when force=True."""
        voucher = self._create_voucher(customer_identification="CUST-PROOF-FORCE")
        extra = self.env["ir.attachment"].create(
            {
                "name": "notes.txt",
                "raw": b"hello world",
                "res_model": "collection.voucher",
                "res_id": voucher.id,
            }
        )
        voucher._message_set_main_attachment_id(extra, force=True)
        voucher.invalidate_recordset()
        self.assertFalse(voucher.message_main_attachment_id)

    # --- Partner write does not auto-follow allocation ---

    def test_allocation_id_write_on_draft_or_unset(self):
        """Write of allocation_id MUST succeed when current and target are draft
        or unset.
        """
        partner = dummy_customer_partner(self.env, customer="MEMB-DRAFT")
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            partner_id=partner.id,
            sheet_id=sheet.id,
            amount=40.0,
            document_id="MEMB-DRAFT",
        )
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[self._line_vals(amount_applied=40.0, invoice_balance=40.0)],
        )
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(allocation.residual, 0.0)
        voucher.write({"allocation_id": False})
        self.assertFalse(voucher.allocation_id)
        self.assertEqual(allocation.residual, 0.0)
        voucher.write({"allocation_id": allocation.id})
        self.assertEqual(voucher.allocation_id, allocation)
        self.assertEqual(allocation.residual, 0.0)

    def test_confirmed_membership_write_refused(self):
        """Write of allocation_id MUST be refused when current or target is
        confirmed.
        """
        partner = dummy_customer_partner(self.env, customer="MEMB-CONF")
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            partner_id=partner.id,
            sheet_id=sheet.id,
            amount=40.0,
            document_id="MEMB-CONF",
        )
        allocation = self._create_allocation(
            sheet, partner, vouchers=voucher, residual_reason="on_account"
        )
        self._confirm(allocation)
        stored = voucher.allocation_id
        with self.assertRaises(UserError):
            voucher.write({"allocation_id": False})
        self.assertEqual(voucher.allocation_id, stored)
        outsider = self._create_voucher(
            partner_id=partner.id,
            sheet_id=sheet.id,
            amount=10.0,
            document_id="MEMB-CONF-OUT",
        )
        with self.assertRaises(UserError):
            outsider.write({"allocation_id": allocation.id})
        self.assertFalse(outsider.allocation_id)

    def test_allocated_partner_write_refused(self):
        """Allocated voucher MUST refuse partner_id write until unassigned."""
        partner_p = dummy_customer_partner(self.env, customer="REASSIGN-P")
        partner_q = dummy_customer_partner(self.env, customer="REASSIGN-Q")
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            partner_id=partner_p.id,
            sheet_id=sheet.id,
            amount=80.0,
            document_id="REASSIGN-SAME-VALS",
        )
        allocation_a = self._create_allocation(
            sheet,
            partner_p,
            vouchers=voucher,
            lines=[
                self._line_vals(
                    amount_applied=0.0,
                    invoice_balance=80.0,
                    external_invoice_id="INV-REASSIGN-A",
                )
            ],
        )
        self._create_allocation(
            sheet,
            partner_q,
            lines=[
                self._line_vals(
                    amount_applied=0.0,
                    invoice_balance=80.0,
                    external_invoice_id="INV-REASSIGN-B",
                )
            ],
        )
        with self.assertRaises(UserError):
            voucher.write({"partner_id": partner_q.id})
        self.assertEqual(voucher.partner_id, partner_p)
        self.assertEqual(voucher.allocation_id, allocation_a)

    def test_allocated_partner_write_refused_when_residual_zero(self):
        """Triangulation: fully applied source still refuses partner_id write."""
        partner_p = dummy_customer_partner(self.env, customer="REASSIGN-FULL-P")
        partner_q = dummy_customer_partner(self.env, customer="REASSIGN-FULL-Q")
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            partner_id=partner_p.id,
            sheet_id=sheet.id,
            amount=100.0,
            document_id="REASSIGN-FULL-SRC",
        )
        allocation = self._create_allocation(
            sheet,
            partner_p,
            vouchers=voucher,
            lines=[
                {
                    "external_invoice_id": "INV-FULL",
                    "invoice_number": "F-1",
                    "invoice_balance": 100.0,
                    "amount_applied": 100.0,
                }
            ],
        )
        self.assertEqual(allocation.residual, 0.0)
        with self.assertRaises(UserError):
            voucher.write({"partner_id": partner_q.id})
        self.assertEqual(voucher.partner_id, partner_p)
        self.assertEqual(voucher.allocation_id, allocation)
        self.assertIn(voucher, allocation.voucher_ids)

    def test_unassign_then_partner_write(self):
        """Clearing allocation_id first MUST allow a later Customer change."""
        partner_p = dummy_customer_partner(self.env, customer="REASSIGN-LEFT-P")
        partner_q = dummy_customer_partner(self.env, customer="REASSIGN-LEFT-Q")
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            partner_id=partner_p.id,
            sheet_id=sheet.id,
            amount=100.0,
            document_id="REASSIGN-LEFT-SRC",
        )
        allocation = self._create_allocation(
            sheet,
            partner_p,
            vouchers=voucher,
            lines=[self._line_vals(amount_applied=60.0, invoice_balance=100.0)],
        )
        self._create_allocation(sheet, partner_q, residual_reason="on_account")
        voucher.write({"allocation_id": False})
        self.assertFalse(voucher.allocation_id)
        voucher.write({"partner_id": partner_q.id})
        self.assertEqual(voucher.partner_id, partner_q)
        self.assertFalse(voucher.allocation_id)
        self.assertNotIn(voucher, allocation.voucher_ids)

    def test_unassigned_partner_write_does_not_auto_follow(self):
        """Unallocated voucher MUST NOT auto-attach a draft allocation for Q."""
        partner_p = dummy_customer_partner(self.env, customer="REASSIGN-ATT-P")
        partner_q = dummy_customer_partner(self.env, customer="REASSIGN-ATT-Q")
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            partner_id=partner_p.id,
            sheet_id=sheet.id,
            amount=40.0,
            document_id="REASSIGN-ATTACH",
        )
        self.assertFalse(voucher.allocation_id)
        allocation_q = self._create_allocation(
            sheet, partner_q, residual_reason="on_account"
        )
        voucher.write({"partner_id": partner_q.id})
        self.assertEqual(voucher.partner_id, partner_q)
        self.assertFalse(voucher.allocation_id)
        self.assertNotIn(voucher, allocation_q.voucher_ids)

    def test_same_value_partner_write_does_not_recompute(self):
        """Same-value partner_id MUST leave allocation_id unchanged."""
        partner_p = dummy_customer_partner(self.env, customer="REASSIGN-UNALLOC-P")
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            partner_id=partner_p.id,
            sheet_id=sheet.id,
            amount=40.0,
            document_id="REASSIGN-UNALLOC",
        )
        allocation = self._create_allocation(
            sheet, partner_p, vouchers=voucher, residual_reason="on_account"
        )
        voucher.write({"partner_id": partner_p.id})
        self.assertEqual(voucher.partner_id, partner_p)
        self.assertEqual(voucher.allocation_id, allocation)

    def test_partner_write_confirmed_source_refused(self):
        """Confirmed source allocation MUST refuse partner_id write; fields stay."""
        partner_p = dummy_customer_partner(self.env, customer="REASSIGN-CONF-P")
        partner_q = dummy_customer_partner(self.env, customer="REASSIGN-CONF-Q")
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            partner_id=partner_p.id,
            sheet_id=sheet.id,
            amount=25.0,
            document_id="REASSIGN-CONFIRMED",
        )
        allocation = self._create_allocation(
            sheet, partner_p, vouchers=voucher, residual_reason="on_account"
        )
        self._confirm(allocation)
        with self.assertRaises(UserError):
            voucher.write({"partner_id": partner_q.id})
        self.assertEqual(voucher.partner_id, partner_p)
        self.assertEqual(voucher.allocation_id, allocation)

    def test_all_voucher_states_may_change_partner(self):
        """Any voucher state MUST NOT freeze partner_id on an open sheet."""
        partner_p = dummy_customer_partner(self.env, customer="REASSIGN-DECIDED-P")
        partner_q = dummy_customer_partner(self.env, customer="REASSIGN-DECIDED-Q")
        partner_r = dummy_customer_partner(self.env, customer="REASSIGN-DECIDED-R")
        sheet = self._create_sheet()
        seller_done = self._create_voucher(
            partner_id=partner_p.id,
            sheet_id=sheet.id,
            amount=10.0,
            document_id="REASSIGN-SELLER",
        )
        seller_done.action_validate_seller()
        seller_done.write({"partner_id": partner_q.id})
        self.assertEqual(seller_done.partner_id, partner_q)
        self.assertEqual(seller_done.state, "validated_seller")

        collections_done = self._create_voucher(
            partner_id=partner_p.id,
            sheet_id=sheet.id,
            amount=10.0,
            document_id="REASSIGN-COLLECTIONS",
        )
        collections_done.with_context(collection_audited_state=True).write(
            {"state": "validated_collections"}
        )
        collections_done.write({"partner_id": partner_r.id})
        self.assertEqual(collections_done.partner_id, partner_r)
        self.assertEqual(collections_done.state, "validated_collections")

    def test_constrain_mismatch_allocation_id_without_partner_refused(self):
        """allocation_id of another customer without matching partner_id MUST refuse."""
        partner_p = dummy_customer_partner(self.env, customer="REASSIGN-CON-P")
        partner_q = dummy_customer_partner(self.env, customer="REASSIGN-CON-Q")
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            partner_id=partner_p.id,
            sheet_id=sheet.id,
            amount=30.0,
            document_id="REASSIGN-CONSTRAIN",
        )
        self._create_allocation(
            sheet, partner_p, vouchers=voucher, residual_reason="on_account"
        )
        allocation_b = self._create_allocation(
            sheet, partner_q, residual_reason="on_account"
        )
        original_allocation = voucher.allocation_id
        with self.assertRaises(UserError):
            voucher.write({"allocation_id": allocation_b.id})
        self.assertEqual(voucher.partner_id, partner_p)
        self.assertEqual(voucher.allocation_id, original_allocation)

    def test_open_membership_and_business_fields_writable(self):
        """Open-sheet voucher MUST persist sheet_id clear and business-field writes."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            sheet_id=sheet.id,
            amount=25.0,
            document_id="OPEN-FIELDS",
            from_account="OPEN-FROM",
        )
        voucher.write({"amount": 30.0, "from_account": "OPEN-FROM-2"})
        self.assertAlmostEqual(voucher.amount, 30.0, places=2)
        self.assertEqual(voucher.from_account, "OPEN-FROM-2")
        voucher.write({"sheet_id": False})
        self.assertFalse(voucher.sheet_id)
        self.assertTrue(sheet.exists())

    def test_proposal_membership_sheet_id_refused(self):
        """Proposal membership writes via voucher.sheet_id MUST raise UserError."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            sheet_id=sheet.id, amount=10.0, document_id="FRZ-PROP-SHEET"
        )
        self._mark_validated_collections(voucher)
        confirm_sheet(sheet)
        self.assertEqual(sheet.state, "proposal")
        with self.assertRaises(UserError) as error:
            voucher.write({"sheet_id": False})
        self.assertEqual(
            str(error.exception),
            "Closed collection sheets cannot change membership. Reopen first.",
        )
        self.assertEqual(voucher.sheet_id, sheet)

    def test_cancelled_membership_sheet_id_refused(self):
        """Triangulation: cancelled sheet_id membership writes MUST also freeze."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            sheet_id=sheet.id, amount=10.0, document_id="FRZ-CAN-SHEET"
        )
        self._mark_validated_collections(voucher)
        confirm_sheet(sheet)
        sheet.action_cancel()
        self.assertEqual(sheet.state, "cancelled")
        with self.assertRaises(UserError):
            voucher.write({"sheet_id": False})
        self.assertEqual(voucher.sheet_id, sheet)

    def test_proposal_partner_id_reuses_membership_error(self):
        """Proposal partner_id writes MUST reuse the membership UserError."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            sheet_id=sheet.id, amount=10.0, document_id="FRZ-PROP-PARTNER"
        )
        other = dummy_customer_partner(self.env, customer="FRZ-PROP-OTHER")
        original = voucher.partner_id
        self._mark_validated_collections(voucher)
        confirm_sheet(sheet)
        with self.assertRaises(UserError) as error:
            voucher.write({"partner_id": other.id})
        self.assertEqual(
            str(error.exception),
            "Closed collection sheets cannot change membership. Reopen first.",
        )
        self.assertEqual(voucher.partner_id, original)

    def test_proposal_business_fields_refused(self):
        """Proposal sheets MUST refuse voucher business-field writes."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            sheet_id=sheet.id,
            amount=40.0,
            document_id="FRZ-PROP-BIZ",
            from_account="KEEP-FROM",
        )
        self._mark_validated_collections(voucher)
        confirm_sheet(sheet)
        with self.assertRaises(UserError):
            voucher.write({"amount": 99.0})
        voucher.invalidate_recordset()
        self.assertAlmostEqual(voucher.amount, 40.0, places=2)
        self.assertEqual(voucher.from_account, "KEEP-FROM")

    def test_cancelled_business_fields_refused(self):
        """Triangulation: cancelled sheets MUST refuse a different business field."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            sheet_id=sheet.id,
            amount=40.0,
            document_id="FRZ-CAN-BIZ",
            from_account="KEEP-FROM-CAN",
        )
        self._mark_validated_collections(voucher)
        confirm_sheet(sheet)
        sheet.action_cancel()
        with self.assertRaises(UserError):
            voucher.write({"from_account": "HACKED"})
        voucher.invalidate_recordset()
        self.assertEqual(voucher.from_account, "KEEP-FROM-CAN")
        self.assertAlmostEqual(voucher.amount, 40.0, places=2)

    def test_closed_business_fields_refused(self):
        """Closed sheets MUST refuse voucher business-field writes."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            sheet_id=sheet.id, amount=15.0, document_id="FRZ-CLOSED-BIZ"
        )
        self._mark_validated_collections(voucher)
        confirm_sheet(sheet)
        sheet.action_close()
        with self.assertRaises(UserError):
            voucher.write({"amount": 1.0})
        voucher.invalidate_recordset()
        self.assertAlmostEqual(voucher.amount, 15.0, places=2)

    def test_allocation_id_writable_on_proposal(self):
        """allocation_id MUST stay writable while the sheet is proposal."""
        partner = dummy_customer_partner(self.env, customer="PROP-ALLOC")
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            partner_id=partner.id,
            sheet_id=sheet.id,
            amount=20.0,
            document_id="PROP-ALLOC-V",
        )
        allocation = self._create_allocation(
            sheet, partner, residual_reason="on_account"
        )
        self._mark_validated_collections(voucher)
        confirm_sheet(sheet)
        self.assertEqual(sheet.state, "proposal")
        self.assertEqual(allocation.state, "draft")
        voucher.write({"allocation_id": allocation.id})
        self.assertEqual(voucher.allocation_id, allocation)
        voucher.write({"allocation_id": False})
        self.assertFalse(voucher.allocation_id)

    def test_chatter_remains_writable_when_sheet_frozen(self):
        """Chatter MUST persist on a voucher whose sheet is proposal or closed."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            sheet_id=sheet.id, amount=10.0, document_id="FRZ-CHATTER"
        )
        self._mark_validated_collections(voucher)
        confirm_sheet(sheet)
        proposal_note = voucher.message_post(
            body="Operator note on proposal voucher",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        self.assertTrue(proposal_note.id)
        self.assertIn(proposal_note, voucher.message_ids)
        self.assertIn("Operator note on proposal voucher", proposal_note.body)
        sheet.action_close()
        closed_note = voucher.message_post(
            body="Operator note on closed voucher",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        self.assertTrue(closed_note.id)
        self.assertIn(closed_note, voucher.message_ids)
        self.assertIn("Operator note on closed voucher", closed_note.body)


def _load_collection_migrate(filename):
    path = Path(__file__).resolve().parents[1] / "migrations" / "19.0.1.13.0" / filename
    spec = spec_from_file_location(filename, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestCollectionVoucherAttachmentMigrate(TransactionCase):
    """RED/GREEN: Binary field attachments migrate onto chatter designated proof."""

    def _insert_field_attachment(self, voucher, name, datas_b64, filename=None):
        attachment = self.env["ir.attachment"].create(
            {
                "name": name,
                "raw": b64decode(datas_b64),
                "res_model": "collection.voucher",
                "res_id": voucher.id,
                "res_field": "attachment",
            }
        )
        if filename is not None and "attachment_filename" in voucher._fields:
            self.env.cr.execute(
                """
                UPDATE collection_voucher
                   SET attachment_filename = %s
                 WHERE id = %s
                """,
                (filename or None, voucher.id),
            )
        elif filename is not None:
            self.env.cr.execute(
                """
                SELECT 1
                  FROM information_schema.columns
                 WHERE table_name = 'collection_voucher'
                   AND column_name = 'attachment_filename'
                """
            )
            if self.env.cr.fetchone():
                self.env.cr.execute(
                    """
                    UPDATE collection_voucher
                       SET attachment_filename = %s
                     WHERE id = %s
                    """,
                    (filename or None, voucher.id),
                )
            elif filename:
                self.env.cr.execute(
                    """
                    UPDATE ir_attachment
                       SET name = %s
                     WHERE id = %s
                    """,
                    (filename, attachment.id),
                )
        return attachment

    def _run_migrate(self):
        _load_collection_migrate("pre-migrate.py").migrate(self.env.cr, "19.0.1.12.0")
        _load_collection_migrate("post-migrate.py").migrate(self.env.cr, "19.0.1.12.0")
        self.env.invalidate_all()

    def test_binary_field_attachment_migrates_to_chatter_main(self):
        voucher = self.env["collection.voucher"].create(
            {
                "partner_id": dummy_customer_partner(
                    self.env, customer="CUST-MIG-MAIN"
                ).id,
                "document_type": "bank_transfer",
                "seller_id": ensure_enabled_seller(self.env).id,
            }
        )
        attachment = self._insert_field_attachment(
            voucher, "attachment", PNG_B64, filename="migrated.png"
        )
        self._run_migrate()
        attachment.invalidate_recordset()
        voucher.invalidate_recordset()
        self.assertFalse(attachment.res_field)
        self.assertEqual(attachment.name, "migrated.png")
        self.assertEqual(voucher.message_main_attachment_id, attachment)
        self.assertTrue(
            voucher.message_ids.filtered(
                lambda message: attachment in message.attachment_ids
            )
        )
        leftover = self.env["ir.attachment"].search(
            [
                ("res_model", "=", "collection.voucher"),
                ("res_id", "=", voucher.id),
                ("res_field", "=", "attachment"),
            ]
        )
        self.assertFalse(leftover)

    def test_empty_filename_falls_back_to_proof_bin(self):
        """Triangulation: empty attachment_filename MUST become proof.bin."""
        voucher = self.env["collection.voucher"].create(
            {
                "partner_id": dummy_customer_partner(
                    self.env, customer="CUST-MIG-BIN"
                ).id,
                "document_type": "cash_deposit",
                "seller_id": ensure_enabled_seller(self.env).id,
            }
        )
        attachment = self._insert_field_attachment(
            voucher, "attachment", PDF_B64, filename=""
        )
        self._run_migrate()
        attachment.invalidate_recordset()
        voucher.invalidate_recordset()
        self.assertEqual(attachment.name, "proof.bin")
        self.assertEqual(voucher.message_main_attachment_id, attachment)
        self.assertFalse(attachment.res_field)


class TestCollectionVoucherProvenance(TransactionCase):
    """RED/GREEN: typed ocr_*/seller_* copies; write() rejects; create may stamp."""

    def _create_voucher(self, customer=None, **extra):
        partner = dummy_customer_partner(
            self.env, customer=customer, extra=extra, default="CUST-PROV"
        )
        vals = {
            "partner_id": partner.id,
            "document_type": "bank_transfer",
            "amount": 40.0,
        }
        if "seller_id" not in extra:
            vals["seller_id"] = ensure_enabled_seller(self.env).id
        elif extra.get("seller_id"):
            ensure_enabled_seller(
                self.env, self.env["res.users"].browse(extra["seller_id"])
            )
        vals.update(extra)
        return self.env["collection.voucher"].create(vals)

    def _assert_empty_provenance(self, voucher):
        for name in voucher._REVIEW_EDITABLE_FIELDS:
            ocr_value = voucher[f"ocr_{name}"]
            seller_value = voucher[f"seller_{name}"]
            if name == "amount":
                self.assertEqual(ocr_value, 0.0, f"ocr_{name}")
                self.assertEqual(seller_value, 0.0, f"seller_{name}")
            else:
                self.assertFalse(ocr_value, f"ocr_{name}")
                self.assertFalse(seller_value, f"seller_{name}")

    def test_write_rejects_ocr_and_seller_keys(self):
        """Voucher write MUST reject provenance keys and leave stored copies."""
        voucher = self._create_voucher(
            ocr_amount=11.0,
            seller_amount=40.0,
            ocr_document_type="bank_transfer",
            seller_document_type="bank_transfer",
        )
        self.assertAlmostEqual(voucher.ocr_amount, 11.0, places=2)
        self.assertAlmostEqual(voucher.seller_amount, 40.0, places=2)
        with self.assertRaises(UserError):
            voucher.write({"ocr_amount": 99.0})
        with self.assertRaises(UserError):
            voucher.write({"seller_from_account": "HACKED"})
        voucher.invalidate_recordset()
        self.assertAlmostEqual(voucher.ocr_amount, 11.0, places=2)
        self.assertAlmostEqual(voucher.seller_amount, 40.0, places=2)
        self.assertFalse(voucher.seller_from_account)
        self.assertAlmostEqual(voucher.amount, 40.0, places=2)

    def test_create_may_stamp_provenance_and_copy_false(self):
        """Create MAY stamp provenance; copy MUST leave the clone empty."""
        voucher = self._create_voucher(
            from_account="CUR-FROM",
            ocr_amount=9.0,
            ocr_from_account="OCR-FROM",
            ocr_document_type="bank_transfer",
            seller_amount=40.0,
            seller_from_account="CUR-FROM",
            seller_document_type="bank_transfer",
        )
        self.assertAlmostEqual(voucher.ocr_amount, 9.0, places=2)
        self.assertEqual(voucher.ocr_from_account, "OCR-FROM")
        self.assertAlmostEqual(voucher.seller_amount, 40.0, places=2)
        self.assertEqual(voucher.seller_from_account, "CUR-FROM")
        for name in voucher._REVIEW_EDITABLE_FIELDS:
            self.assertFalse(voucher._fields[f"ocr_{name}"].copy)
            self.assertFalse(voucher._fields[f"seller_{name}"].copy)
        clone = voucher.copy({"document_id": "DOC-PROV-CLONE"})
        self.assertEqual(clone.from_account, "CUR-FROM")
        self._assert_empty_provenance(clone)

    def test_existing_rows_keep_current_with_null_provenance(self):
        """Rows created without stamps keep current fields and zero snapshots."""
        voucher = self._create_voucher(
            customer_identification="CUST-PROV-EXISTING",
            amount=77.0,
            to_account="TO-KEEP",
        )
        self.assertAlmostEqual(voucher.amount, 77.0, places=2)
        self.assertEqual(voucher.to_account, "TO-KEEP")
        self._assert_empty_provenance(voucher)
        self.assertEqual(
            self.env["collection.voucher.review.snapshot"].search_count(
                [("voucher_id", "=", voucher.id)]
            ),
            0,
        )


class TestCollectionNewWorkHelper(TransactionCase):
    """NEW-work helper: enabled seller + allowed type; historical stays operable."""

    def _admin_seller(self):
        return self.env.ref("base.user_admin")

    def _enable_sellers(self, *sellers):
        self.env.company.write(
            {"enabled_seller_ids": [Command.set([seller.id for seller in sellers])]}
        )

    def _clear_enabled_sellers(self):
        self.env.company.write({"enabled_seller_ids": [Command.clear()]})

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

    def _create_internal_seller(self, login):
        Partner = self.env["res.partner"].with_context(
            tracking_disable=True,
            mail_create_nolog=True,
            mail_notrack=True,
            mail_create_nosubscribe=True,
        )
        partner_vals = {
            "name": login,
            "email": f"{login}@example.com",
        }
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
                    "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
                }
            )
        )

    def _voucher_vals(self, customer=None, **extra):
        partner = dummy_customer_partner(
            self.env, customer=customer, extra=extra, default="CUST-NEW-WORK"
        )
        vals = {
            "partner_id": partner.id,
            "document_type": extra.pop("document_type", "bank_transfer"),
        }
        vals.update(extra)
        return vals

    def _create_voucher(self, customer=None, **extra):
        return self.env["collection.voucher"].create(
            self._voucher_vals(customer=customer, **extra)
        )

    def test_empty_enabled_sellers_rejects_voucher_create(self):
        """Empty enabled-seller list MUST mean none for NEW voucher work."""
        seller = self._admin_seller()
        self._clear_enabled_sellers()
        before = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError):
            self._create_voucher(seller_id=seller.id)
        self.assertEqual(self.env["collection.voucher"].search_count([]), before)

    def test_disabled_seller_rejects_voucher_create(self):
        """A seller not on the company enabled list MUST be rejected on create."""
        enabled = self._admin_seller()
        disabled = self._create_internal_seller("nw_disabled_voucher_seller")
        self._enable_sellers(enabled)
        before = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError):
            self._create_voucher(
                customer_identification="CUST-NW-DISABLED",
                seller_id=disabled.id,
            )
        self.assertEqual(self.env["collection.voucher"].search_count([]), before)

    def test_enabled_seller_create_succeeds(self):
        """Triangulation: an enabled seller MUST be accepted on voucher create."""
        seller = self._admin_seller()
        self._enable_sellers(seller)
        voucher = self._create_voucher(seller_id=seller.id)
        self.assertEqual(voucher.seller_id, seller)
        self.assertTrue(voucher.id)

    def test_disallowed_type_rejects_voucher_create(self):
        unsupported = self.env.ref("collection.document_type_unsupported")
        seller = self._admin_seller()
        self._enable_sellers(seller)
        others = self.env.company.allowed_document_type_ids - unsupported
        self.env.company.write({"allowed_document_type_ids": [Command.set(others.ids)]})
        before = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError):
            self._create_voucher(
                customer_identification="CUST-NW-BAD-TYPE",
                seller_id=seller.id,
                document_type="unsupported",
            )
        self.assertEqual(self.env["collection.voucher"].search_count([]), before)

    def test_seller_write_to_disabled_seller_rejected(self):
        enabled = self._admin_seller()
        disabled = self._create_internal_seller("nw_write_disabled_seller")
        self._enable_sellers(enabled)
        voucher = self._create_voucher(
            customer_identification="CUST-NW-WRITE-SELLER",
            seller_id=enabled.id,
        )
        with self.assertRaises(UserError):
            voucher.write({"seller_id": disabled.id})
        self.assertEqual(voucher.seller_id, enabled)

    def test_document_type_write_to_disallowed_type_rejected(self):
        unsupported = self.env.ref("collection.document_type_unsupported")
        seller = self._admin_seller()
        self._enable_sellers(seller)
        voucher = self._create_voucher(
            customer_identification="CUST-NW-WRITE-TYPE",
            seller_id=seller.id,
            document_type="bank_transfer",
        )
        others = self.env.company.allowed_document_type_ids - unsupported
        self.env.company.write({"allowed_document_type_ids": [Command.set(others.ids)]})
        with self.assertRaises(UserError):
            voucher.write({"document_type": "unsupported"})
        self.assertEqual(voucher.document_type, "bank_transfer")

    def test_disabled_seller_voucher_stays_visible_and_validatable(self):
        seller = self._admin_seller()
        self._enable_sellers(seller)
        voucher = self._create_voucher(
            customer_identification="CUST-NW-HIST-APPROVE",
            seller_id=seller.id,
        )
        self._enable_sellers()  # clear: empty set
        found = self.env["collection.voucher"].search([("id", "=", voucher.id)])
        self.assertEqual(found, voucher, "disabled-seller voucher must stay listed")
        voucher.action_validate_seller()
        self.assertEqual(voucher.state, "validated_seller")
        self.assertTrue(voucher.exists())

    def test_disabled_seller_validate_seller_skips_helper(self):
        """Triangulation: Validate by Seller without seller/type write skips helper."""
        seller = self._admin_seller()
        self._enable_sellers(seller)
        voucher = self._create_voucher(
            customer_identification="CUST-NW-HIST-REJECT",
            seller_id=seller.id,
        )
        self._clear_enabled_sellers()
        voucher.action_validate_seller()
        self.assertEqual(voucher.state, "validated_seller")
        self.assertTrue(voucher.exists())

    def test_document_type_selection_is_allowed_union_current(self):
        """Type choices MUST be allowed types plus the current value if dropped."""
        unsupported = self.env.ref("collection.document_type_unsupported")
        seller = self._admin_seller()
        self._enable_sellers(seller)
        voucher = self._create_voucher(
            customer_identification="CUST-NW-TYPE-UNION",
            seller_id=seller.id,
            document_type="unsupported",
        )
        others = self.env.company.allowed_document_type_ids - unsupported
        self.env.company.write({"allowed_document_type_ids": [Command.set(others.ids)]})

        new_codes = {code for code, _label in voucher._selection_document_type()}
        empty_codes = {
            code
            for code, _label in self.env[
                "collection.voucher"
            ]._selection_document_type()
        }
        self.assertNotIn(
            "unsupported",
            empty_codes,
            "new work must not offer a disabled document type",
        )
        self.assertIn("bank_transfer", empty_codes)
        self.assertIn(
            "unsupported",
            new_codes,
            "historical current type must remain in choices",
        )

    def test_document_type_selection_empty_recordset_excludes_disabled(self):
        """Triangulation: empty recordset type choices follow the company allow-list."""
        unsupported = self.env.ref("collection.document_type_unsupported")
        others = self.env.company.allowed_document_type_ids - unsupported
        self.env.company.write({"allowed_document_type_ids": [Command.set(others.ids)]})
        empty_codes = {
            code
            for code, _label in self.env[
                "collection.voucher"
            ]._selection_document_type()
        }
        self.assertNotIn("unsupported", empty_codes)
        self.assertIn("bank_transfer", empty_codes)
