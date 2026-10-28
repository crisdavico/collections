# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import inspect
import json
from pathlib import Path
from unittest.mock import patch

from psycopg2.errors import UniqueViolation

from odoo.exceptions import AccessError, UserError
from odoo.fields import Command
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.collection.models.collection_common import privileged
from odoo.addons.collection.tools.collection_voucher import _DOCUMENT_TYPES
from odoo.addons.muk_mcp.core.tool import get_tool_index

from .common_connector import (
    TEST_INVOICES,
    confirm_sheet,
    install_bound_test_connector,
    install_test_connector_type,
    mcp_env_with_listable_customers,
)
from .test_collection_acl import TestCollectionAcl
from .test_collection_payment import (
    PNG_B64,
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
    with_voucher_files,
)

TOOL_NAME = "create_collection_allocation"
VOUCHER_TOOL_NAME = "create_collection_vouchers"
_COLLECTION_HELPERS = (
    "_collection_parse_payment_vals",
    "_collection_parse_payment_attachments",
    "_collection_parse_payment_provenance",
    "_collection_parse_provenance_nests",
    "_collection_parse_attachment_nest",
    "_collection_create_vouchers",
    "_collection_vouchers_payload",
    "_collection_classify_visible",
    "_collection_replay_or_reject",
    "_collection_replay_existing",
    "_collection_document_conflict_error",
    "_collection_require_internal_seller",
    "_collection_vouchers_by_document_ids",
    "_collection_parse_allocation_identity",
)
IDENT = "20-11111111-1"
UNBOUND_LISTABLE = "20-88888888-8"
SHEET_REQUIRED_MSG = "This company requires a collection sheet chosen in Odoo."
_TOP_KEYS = {"sheet_id", "vouchers", "allocation"}
_ALLOC_KEYS = {
    "id",
    "name",
    "state",
    "revision",
    "total_vouchers",
    "total_applied",
    "residual",
}
_VOUCHER_KEYS = {"id", "name", "state", "document_id"}
_LEAK_TOKENS = (
    "SELECT",
    "INSERT",
    "UPDATE",
    "DELETE FROM",
    "sqlite3",
    ".db",
    "/tmp",
    "/home",
)
_DISPATCH_OPS = frozenset(
    {
        "test_connection",
        "list_sellers",
        "list_customers",
        "get_customer_debt",
        "create_receipt",
    }
)

INVOICE_OVERDUE = {
    "external_invoice_id": "inv-bound-overdue",
    "number": "A-0001",
    "issue_date": "2026-01-10",
    "due_date": "2026-03-10",
    "amount": 100.0,
    "balance": 100.0,
    "state": "overdue",
}
INVOICE_OPEN = {
    "external_invoice_id": "inv-bound-open",
    "number": "A-0002",
    "issue_date": "2026-04-01",
    "due_date": "2026-09-01",
    "amount": 50.0,
    "balance": 50.0,
    "state": "open",
}


class TestCollectionMcpAllocation(TransactionCase):
    """RED: MCP create_collection_allocation inline payments, replay, amend, gates."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        install_test_connector_type(cls)
        cls.tool_model = cls.env["muk_mcp.tool"]
        cls.internal_user = cls._create_user(
            "collection_mcp_alloc_internal", "collection.group_collection_user"
        )
        cls.portal_user = cls._create_user(
            "collection_mcp_alloc_portal", "base.group_portal"
        )
        cls.public_user = cls._create_user(
            "collection_mcp_alloc_public", "base.group_public"
        )
        cls.seller = create_internal_seller(cls.env, "collection_mcp_alloc_seller")

    def setUp(self):
        super().setUp()
        install_test_connector_type(self)
        self.connector = install_bound_test_connector(self, self.seller)
        self.partner = dummy_customer_partner(self.env, customer=IDENT)
        self.env["collection.connector.customer.binding"].create(
            {
                "connector_id": self.connector.id,
                "external_customer_id": "cust-bound-active",
                "identification": IDENT,
                "partner_id": self.partner.id,
                "customer_code": "C-BOUND-1",
            }
        )
        self.sheet = self._create_sheet()
        self._doc_seq = 0

    @classmethod
    def _partner_has_autopost_bills_column(cls):
        return TestCollectionAcl._partner_has_autopost_bills_column.__func__(cls)

    @classmethod
    def _create_user(cls, login, group_xmlid):
        return TestCollectionAcl._create_user.__func__(cls, login, group_xmlid)

    def _create_sheet(self, *, seller=None, company=None, force_new=False):
        seller = seller or self.seller
        company = company or self.env.company
        ensure_enabled_seller(self.env, seller, company=company)
        if not force_new:
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
        return (
            self.env["collection.sheet"]
            .with_company(company)
            .create({"seller_id": seller.id, "company_id": company.id})
        )

    def _close_open_sheet(self, sheet=None):
        sheet = sheet or self.sheet
        if sheet.voucher_ids:
            with privileged("collection_audited_state"):
                sheet.voucher_ids.write({"state": "validated_collections"})
        confirm_sheet(sheet)
        sheet.action_close()
        return sheet

    def _next_document_id(self, prefix="ALLOC-DOC"):
        self._doc_seq += 1
        return f"{prefix}-{self._testMethodName}-{self._doc_seq}"

    def _create_vouchers(
        self,
        amounts,
        *,
        partner=None,
        sheet=None,
        seller=None,
        prefix="ALLOC-DOC",
        **extra,
    ):
        partner = partner or self.partner
        sheet = sheet or self.sheet
        seller = seller or self.seller
        ensure_enabled_seller(self.env, seller, company=sheet.company_id)
        document_type = extra.pop("document_type", "bank_transfer")
        vouchers = self.env["collection.voucher"]
        for amount in amounts:
            vals = {
                "partner_id": partner.id,
                "document_type": document_type,
                "document_id": self._next_document_id(prefix),
                "seller_id": seller.id,
                "sheet_id": sheet.id,
                "company_id": sheet.company_id.id,
                "amount": amount,
            }
            vals.update(extra)
            vouchers |= (
                self.env["collection.voucher"]
                .with_company(sheet.company_id)
                .create(vals)
            )
        return vouchers

    def _application(self, invoice, amount_applied, balance_seen=None):
        return {
            "external_document_id": invoice["external_invoice_id"],
            "number": invoice.get("number"),
            "balance_seen": (
                invoice["balance"] if balance_seen is None else balance_seen
            ),
            "amount_applied": amount_applied,
        }

    def _applied(self, invoice, amount_applied, balance_seen=None):
        """Build one receipt application from an invoice fixture."""
        return self._application(invoice, amount_applied, balance_seen=balance_seen)

    def _payment(self, amount, document_id=None, **extra):
        document_type = extra.pop("document_type", "bank_transfer")
        seller = extra.pop("seller_confirmed", None)
        if seller is None:
            seller = {"document_type": document_type, "amount": amount}
            for field_name in (
                "from_account",
                "to_account",
                "voucher_number",
                "voucher_date",
                "check_number",
                "check_bank",
                "check_issue_date",
                "check_payment_date",
                "check_type",
            ):
                if field_name in extra:
                    seller[field_name] = extra.pop(field_name)
        payment = {
            "document_id": document_id or self._next_document_id(),
            "seller_confirmed": seller,
        }
        payment.update(extra)
        return payment

    def _payments_from_vouchers(self, vouchers):
        return [
            {
                "document_id": voucher.document_id,
                "seller_confirmed": {
                    "document_type": voucher.document_type,
                    "amount": voucher.amount,
                },
            }
            for voucher in vouchers
        ]

    def _receipt(
        self, payments, applications=None, document_kind="invoice", values=None
    ):
        if values is None:
            values = [
                {
                    "document_id": payment["document_id"],
                    "amount": payment["seller_confirmed"]["amount"],
                }
                for payment in payments
            ]
        return {
            "document_kind": document_kind,
            "values": values,
            "applications": list(applications or []),
        }

    def _payload(self, payments, receipts=None, **extra):
        extra.pop("residual_reason", None)
        extra.pop("total_debt", None)
        if receipts is None or receipts == []:
            wrapped = [self._receipt(payments)]
        elif receipts and isinstance(receipts[0], dict) and "values" in receipts[0]:
            wrapped = receipts
        else:
            applications = []
            for row in receipts:
                if "external_document_id" in row:
                    applications.append(
                        {
                            "external_document_id": row["external_document_id"],
                            "number": row.get("number"),
                            "balance_seen": row.get("balance_seen", row.get("balance")),
                            "amount_applied": row["amount_applied"],
                        }
                    )
                else:
                    applications.append(self._application(row, row["amount_applied"]))
            wrapped = [self._receipt(payments, applications)]
        arguments = {
            "seller_id": extra.pop("seller_id", self.seller.id),
            "customer_identification": extra.pop("customer_identification", IDENT),
            "request_id": extra.pop("request_id", f"req-{self._testMethodName}"),
            "payments": payments,
            "receipts": wrapped,
        }
        arguments.update(extra)
        return arguments

    def _call(self, arguments, user=None, context=None):
        uid = user if user else self.internal_user
        echo_args = dict(arguments)
        ident = arguments.get("customer_identification")
        if ident:
            echoed = []
            raw_payments = arguments.get("payments") or [{}]
            for payment in raw_payments:
                item = dict(payment) if isinstance(payment, dict) else {}
                item.setdefault("customer_identification", ident)
                echoed.append(item)
            echo_args = {**arguments, "payments": echoed}
        env = mcp_env_with_listable_customers(self.env, echo_args, uid, uid)
        if context:
            env = env(context={**env.context, **context})
        text, _info = self.tool_model._call(
            TOOL_NAME, with_voucher_files(arguments), env
        )
        return json.loads(text)

    def _counts(self):
        return {
            "allocations": self.env["collection.allocation"].search_count([]),
            "lines": self.env["collection.allocation.line"].search_count([]),
            "requests": sum(
                len(allocation.request_log or {})
                for allocation in self.env["collection.allocation"].search([])
            ),
            "vouchers": self.env["collection.voucher"].search_count([]),
            "sheets": self.env["collection.sheet"].search_count([]),
        }

    def _partner_binding_counts(self):
        return {
            "partners": self.env["res.partner"].search_count([]),
            "bindings": self.env["collection.connector.customer.binding"].search_count(
                []
            ),
        }

    def _assert_payload(self, result, allocation, *, revision=1, document_ids):
        self.assertEqual(set(result), _TOP_KEYS)
        self.assertEqual(result["sheet_id"], allocation.sheet_id.id)
        rows = result["vouchers"]
        self.assertEqual(len(rows), len(document_ids))
        self.assertGreater(len(rows), 0)
        for row, doc_id in zip(rows, document_ids, strict=True):
            self.assertEqual(set(row), _VOUCHER_KEYS)
            self.assertEqual(row["document_id"], doc_id)
            self.assertIsInstance(row["id"], int)
            self.assertTrue(row["name"])
            self.assertTrue(row["state"])
        body = result["allocation"]
        self.assertEqual(set(body), _ALLOC_KEYS)
        self.assertIsInstance(body["revision"], int)
        self.assertNotIsInstance(body["revision"], bool)
        self.assertEqual(body["id"], allocation.id)
        self.assertEqual(body["name"], allocation.name)
        self.assertEqual(body["state"], allocation.state)
        self.assertEqual(body["revision"], revision)
        self.assertEqual(body["total_vouchers"], allocation.total_vouchers)
        self.assertEqual(body["total_applied"], allocation.total_applied)
        self.assertEqual(body["residual"], allocation.residual)

    def _assert_debt_lines(self, allocation, applied_by_id):
        lines = {line.external_invoice_id: line for line in allocation.line_ids}
        self.assertEqual(set(lines), set(applied_by_id))
        self.assertGreater(len(lines), 0)
        for external_id, amount_applied in applied_by_id.items():
            self.assertEqual(lines[external_id].amount_applied, amount_applied)

    def _assert_user_error_no_writes(self, func, before=None):
        before = before or self._counts()
        with self.assertRaises(UserError) as ctx:
            func()
        message = str(ctx.exception)
        self.assertNotIn("tool not found", message.lower())
        self.assertNotIn('{"error"', message)
        for token in _LEAK_TOKENS:
            self.assertNotIn(token, message)
        self.assertEqual(self._counts(), before)
        return ctx.exception

    def _assert_generic_conflict(self, err, *records):
        message = str(err)
        lowered = message.lower()
        self.assertIn("conflict", lowered)
        self.assertNotIn("tool not found", lowered)
        for record in records:
            self.assertNotIn(str(record.id), message)
            if getattr(record, "name", None):
                self.assertNotIn(record.name, message)

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
        return self.env["res.company"].create({"name": name, "partner_id": partner.id})

    def _patch_request_lookup_miss_once(self, request_id):
        mixin_cls = type(self.env["muk_mcp.mixin"])
        real_lookup = mixin_cls._collection_allocation_by_request_id
        calls = {"n": 0}

        def lookup_proxy(model_self, key):
            if key == request_id:
                calls["n"] += 1
                if calls["n"] == 1:
                    return model_self.env["collection.allocation"]
            return real_lookup(model_self, key)

        return (
            patch.object(
                mixin_cls, "_collection_allocation_by_request_id", lookup_proxy
            ),
            calls,
        )

    def _confirm(self, allocation):
        with privileged("collection_allocation_audited_state"):
            allocation.write({"state": "confirmed"})
        return allocation

    def test_discovered_as_method_write_mcp(self):
        """create_collection_allocation is method-discovered write/mcp; no DB row."""
        by_name = {
            entry["name"]: entry for entry in self.tool_model.get_tools(registry="mcp")
        }
        self.assertIn(TOOL_NAME, by_name)
        self.assertNotIn(
            VOUCHER_TOOL_NAME,
            by_name,
            "create_collection_vouchers must not remain registered",
        )
        entry = get_tool_index(self.env, registry="mcp")[TOOL_NAME]
        self.assertEqual(entry["category"], "write")
        self.assertEqual(entry["registry"], "mcp")
        self.assertEqual(entry["kind"], "method")
        self.assertFalse(
            self.env["muk_mcp.tool"].search([("name", "=", TOOL_NAME)]),
            "create_collection_allocation must not have a DB muk_mcp.tool row",
        )
        schema = by_name[TOOL_NAME]["inputSchema"]
        self.assertEqual(schema["type"], "object")
        self.assertEqual(
            set(schema["required"]),
            {
                "seller_id",
                "customer_identification",
                "request_id",
                "payments",
                "receipts",
            },
        )
        self.assertNotIn("vouchers", schema["properties"])
        self.assertNotIn("invoices", schema["properties"])
        self.assertNotIn("splits", schema["properties"])
        self.assertNotIn("total_debt", schema["properties"])
        self.assertNotIn("residual_reason", schema["properties"])
        self.assertEqual(schema["properties"]["seller_id"]["type"], "integer")
        self.assertEqual(
            schema["properties"]["customer_identification"]["type"], "string"
        )
        self.assertEqual(schema["properties"]["request_id"]["type"], "string")
        payments = schema["properties"]["payments"]
        self.assertEqual(payments["type"], "array")
        self.assertGreaterEqual(payments.get("minItems", 0), 1)
        self.assertNotIn("customer_identification", payments["items"]["properties"])
        self.assertNotIn(
            "customer_identification", payments["items"].get("required", [])
        )
        self.assertEqual(
            set(payments["items"].get("required", [])),
            {"document_id", "seller_confirmed"},
        )
        receipts = schema["properties"]["receipts"]
        self.assertEqual(receipts["type"], "array")
        self.assertGreaterEqual(receipts.get("minItems", 0), 1)
        self.assertEqual(
            set(receipts["items"].get("required", [])),
            {"document_kind", "values"},
        )
        from odoo.addons.collection.tools.collection_allocation import (
            _RECEIPT_ITEM_SCHEMA,
        )
        from odoo.addons.collection.tools.collection_voucher import _PAYMENT_SCHEMA

        self.assertEqual(payments["items"], _PAYMENT_SCHEMA)
        self.assertEqual(receipts["items"], _RECEIPT_ITEM_SCHEMA)
        description = (by_name[TOOL_NAME].get("description") or "").lower()
        self.assertIn("draft", description)
        self.assertNotIn("confirmed collection allocation", description)

    def test_create_collection_vouchers_absent_from_mcp_registry(self):
        """Retired voucher write MUST not be an MCP tool; `_collection_*` remain."""
        by_name = {
            entry["name"]: entry for entry in self.tool_model.get_tools(registry="mcp")
        }
        self.assertNotIn(
            VOUCHER_TOOL_NAME,
            by_name,
            "create_collection_vouchers must not appear in MCP registry tools",
        )
        self.assertFalse(
            self.env["muk_mcp.tool"].search([("name", "=", VOUCHER_TOOL_NAME)]),
            "create_collection_vouchers must not have a DB muk_mcp.tool row",
        )
        mixin_cls = type(self.env["muk_mcp.mixin"])
        self.assertFalse(
            hasattr(mixin_cls, VOUCHER_TOOL_NAME),
            "muk_mcp.mixin must not expose create_collection_vouchers",
        )
        for helper_name in _COLLECTION_HELPERS:
            self.assertTrue(
                callable(getattr(mixin_cls, helper_name, None)),
                f"{helper_name} must remain on muk_mcp.mixin",
            )
            self.assertNotIn(helper_name, by_name)
            self.assertFalse(
                self.env["muk_mcp.tool"].search([("name", "=", helper_name)]),
                f"{helper_name} must not have a DB muk_mcp.tool row",
            )
            helper = getattr(mixin_cls, helper_name)
            self.assertFalse(
                getattr(helper, "_mcp_tool", False)
                or getattr(helper, "_mcp_name", None),
                f"{helper_name} must not be decorated as an MCP tool",
            )

    def test_payment_schema_and_parse_replicate_top_level_identification(self):
        """_PAYMENT_SCHEMA omits ident; parse replicates the top-level argument."""
        from odoo.addons.collection.tools.collection_voucher import _PAYMENT_SCHEMA

        self.assertNotIn("customer_identification", _PAYMENT_SCHEMA["properties"])
        self.assertEqual(
            set(_PAYMENT_SCHEMA["required"]), {"document_id", "seller_confirmed"}
        )
        mixin = self.env["muk_mcp.mixin"]
        payments = [
            {
                "document_id": "DOC-PARSE-A",
                "seller_confirmed": {
                    "document_type": "bank_transfer",
                    "amount": 10.0,
                },
            },
            {
                "document_id": "DOC-PARSE-B",
                "seller_confirmed": {
                    "document_type": "cash_deposit",
                    "amount": 20.0,
                },
            },
        ]
        vals = mixin._collection_parse_payment_vals(payments, f"  {IDENT}  ")
        self.assertEqual(
            [row["document_id"] for row in vals],
            ["DOC-PARSE-A", "DOC-PARSE-B"],
        )
        self.assertNotIn("customer_identification", vals[0])
        self.assertNotIn("customer_identification", vals[1])
        with self.assertRaises(UserError):
            mixin._collection_parse_payment_vals(payments, "   ")

    def test_first_create_draft_revision_one_totals(self):
        """First create MUST persist draft revision 1 with matching totals."""
        payment = self._payment(100.0)
        before = self._counts()
        result = self._call(
            self._payload([payment], [self._applied(INVOICE_OVERDUE, 100.0)])
        )
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        self.assertTrue(allocation.exists())
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(result["allocation"]["state"], "draft")
        self.assertEqual(allocation.revision, 1)
        self.assertEqual(allocation.partner_id, self.partner)
        self.assertEqual(allocation.sheet_id, self.sheet)
        self.assertEqual(allocation.total_vouchers, 100.0)
        self.assertEqual(allocation.total_applied, 100.0)
        self.assertEqual(allocation.residual, 50.0)
        self.assertEqual(allocation.total_debt, 150.0)
        self._assert_debt_lines(
            allocation,
            {
                INVOICE_OVERDUE["external_invoice_id"]: 100.0,
                INVOICE_OPEN["external_invoice_id"]: 0.0,
            },
        )
        self.assertEqual(list(allocation.request_log), [allocation.request_id])
        self.assertEqual(allocation.request_log[allocation.request_id]["revision"], 1)
        self._assert_payload(
            result, allocation, revision=1, document_ids=[payment["document_id"]]
        )
        self.assertEqual(self._counts()["allocations"], before["allocations"] + 1)
        self.assertEqual(self._counts()["requests"], before["requests"] + 1)
        self.assertEqual(self._counts()["vouchers"], before["vouchers"] + 1)

    def test_debt_lines_keep_the_connector_untaxed_amount(self):
        """Lines snapshot `amount_untaxed`, or the amount when it is not given."""
        invoices = [dict(row) for row in TEST_INVOICES]
        invoices[0]["amount_untaxed"] = 82.64
        result = self._call(
            self._payload(
                [self._payment(100.0)], [self._applied(INVOICE_OVERDUE, 100.0)]
            ),
            context={"collection_test_invoices": invoices},
        )
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        lines = {line.external_invoice_id: line for line in allocation.line_ids}
        self.assertEqual(lines["inv-bound-overdue"].invoice_amount_untaxed, 82.64)
        self.assertEqual(lines["inv-bound-open"].invoice_amount_untaxed, 50.0)

    def test_response_shape_freeze_ordered_vouchers(self):
        """Success body MUST freeze {sheet_id,vouchers,allocation} with send order."""
        first = self._payment(40.0)
        second = self._payment(60.0)
        result = self._call(
            self._payload(
                [second, first],
                [self._applied(INVOICE_OVERDUE, 100.0)],
            )
        )
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        document_ids = [second["document_id"], first["document_id"]]
        self._assert_payload(result, allocation, revision=1, document_ids=document_ids)
        self.assertEqual(
            [row["document_id"] for row in result["vouchers"]], document_ids
        )

    def test_request_id_replay_zero_writes(self):
        """Identical request_id MUST replay full payload with no writes."""
        payment = self._payment(100.0)
        arguments = self._payload(
            [payment],
            [self._applied(INVOICE_OVERDUE, 100.0)],
            request_id="req-replay",
        )
        first = self._call(arguments)
        allocation = self.env["collection.allocation"].browse(first["allocation"]["id"])
        write_date = allocation.write_date
        request_log = dict(allocation.request_log)
        before = self._counts()
        second = self._call(arguments)
        self.assertEqual(second, first)
        self._assert_payload(
            second, allocation, revision=1, document_ids=[payment["document_id"]]
        )
        allocation.invalidate_recordset()
        self.assertEqual(allocation.write_date, write_date)
        self.assertEqual(allocation.request_log, request_log)
        self.assertEqual(self._counts(), before)
        self.assertEqual(allocation.total_applied, 100.0)

    def test_content_hash_replay_new_request_id_no_extra_revision(self):
        """Matching content_hash with a new request_id MUST not add a revision."""
        payment = self._payment(100.0)
        invoices = [self._applied(INVOICE_OVERDUE, 100.0)]
        first = self._call(self._payload([payment], invoices, request_id="req-hash-1"))
        allocation = self.env["collection.allocation"].browse(first["allocation"]["id"])
        write_date = allocation.write_date
        before = self._counts()
        second = self._call(self._payload([payment], invoices, request_id="req-hash-2"))
        self.assertEqual(second["allocation"]["id"], first["allocation"]["id"])
        self.assertEqual(second["allocation"]["revision"], 1)
        self.assertEqual(second["sheet_id"], first["sheet_id"])
        allocation.invalidate_recordset()
        self.assertEqual(list(allocation.request_log), ["req-hash-1"])
        self.assertEqual(allocation.request_id, "req-hash-1")
        self.assertEqual(allocation.write_date, write_date)
        self.assertEqual(self._counts(), before)

    def test_omitted_extras_hash_matches_receipts_payload(self):
        """Content hash MUST cover receipt values, applications, and kind."""
        import hashlib

        payment = self._payment(100.0)
        receipts = [
            self._receipt([payment], [self._application(INVOICE_OVERDUE, 100.0)])
        ]
        first = self._call(
            self._payload([payment], receipts, request_id="req-receipt-hash")
        )
        allocation = self.env["collection.allocation"].browse(first["allocation"]["id"])
        vouchers = allocation.voucher_ids
        mixin = self.env["muk_mcp.mixin"]
        digest = mixin._collection_allocation_content_hash(vouchers, receipts)
        self.assertEqual(allocation.content_hash, digest)
        self.assertEqual(
            allocation.request_log["req-receipt-hash"]["content_hash"], digest
        )
        expected_payload = {
            "receipts": [
                {
                    "applications": sorted(
                        [
                            [
                                INVOICE_OVERDUE["external_invoice_id"],
                                "100.000000",
                                "100.000000",
                            ]
                        ]
                    ),
                    "document_kind": "invoice",
                    "values": sorted([[payment["document_id"], "100.000000"]]),
                }
            ],
            "vouchers": sorted(vouchers.ids),
        }
        expected = hashlib.sha256(
            json.dumps(expected_payload, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()
        self.assertEqual(digest, expected)

    def test_payload_kind_prevents_hash_replay(self):
        """Different receipt document_kind MUST not replay as unchanged content."""
        # On account: no application, so either receipt kind is valid.
        payment = self._payment(100.0)
        invoice_receipts = [self._receipt([payment], [])]
        quotation_receipts = [self._receipt([payment], [], document_kind="quotation")]
        first = self._call(
            self._payload([payment], invoice_receipts, request_id="req-kind-1")
        )
        second = self._call(
            self._payload([payment], quotation_receipts, request_id="req-kind-2")
        )
        self.assertEqual(second["allocation"]["id"], first["allocation"]["id"])
        self.assertEqual(second["allocation"]["revision"], 2)
        allocation = self.env["collection.allocation"].browse(
            second["allocation"]["id"]
        )
        self.assertEqual(len(allocation.request_log), 2)

    def test_exact_document_id_reuse_continues_to_allocation(self):
        """Exact same-company document_id set MUST reuse rows and persist allocation."""
        vouchers = self._create_vouchers([100.0])
        before = self._counts()
        result = self._call(
            self._payload(
                self._payments_from_vouchers(vouchers),
                [self._applied(INVOICE_OVERDUE, 100.0)],
                request_id="req-reuse",
            )
        )
        self.assertEqual(self._counts()["vouchers"], before["vouchers"])
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        self.assertTrue(allocation.exists())
        self.assertEqual(allocation.voucher_ids, vouchers)
        self._assert_payload(
            result,
            allocation,
            revision=1,
            document_ids=vouchers.mapped("document_id"),
        )
        self.assertEqual(self._counts()["allocations"], before["allocations"] + 1)

    def test_amend_reuses_own_vouchers_and_creates_new_payments(self):
        """Own existing vouchers plus new payments MUST amend, creating only the new."""
        first_payment = self._payment(100.0)
        first = self._call(
            self._payload(
                [first_payment],
                [self._applied(INVOICE_OVERDUE, 100.0)],
                request_id="req-reuse-1",
            )
        )
        new_payment = self._payment(50.0)
        before = self._counts()
        second = self._call(
            self._payload(
                [first_payment, new_payment],
                [
                    self._applied(INVOICE_OVERDUE, 100.0),
                    self._applied(INVOICE_OPEN, 50.0),
                ],
                request_id="req-reuse-2",
            )
        )
        allocation = self.env["collection.allocation"].browse(
            second["allocation"]["id"]
        )
        self.assertEqual(allocation.id, first["allocation"]["id"])
        self.assertEqual(allocation.revision, 2)
        self.assertEqual(self._counts()["vouchers"], before["vouchers"] + 1)
        self.assertEqual(
            set(allocation.voucher_ids.mapped("document_id")),
            {first_payment["document_id"], new_payment["document_id"]},
        )
        self.assertEqual(allocation.total_vouchers, 150.0)

    def test_agent_draft_allocation_can_be_deleted_on_an_open_sheet(self):
        """A draft allocation the agent wrote MUST go while its sheet is open."""
        result = self._call(
            self._payload(
                [self._payment(100.0)],
                [self._applied(INVOICE_OVERDUE, 100.0)],
                request_id="req-unlink-agent",
            )
        )
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        vouchers = allocation.voucher_ids
        receipts = allocation.receipt_ids
        self.assertEqual(allocation.sheet_id.state, "open")
        self.assertTrue(receipts)
        allocation.unlink()
        self.assertFalse(allocation.exists())
        self.assertFalse(receipts.exists())
        self.assertTrue(vouchers.exists())
        self.assertFalse(vouchers.allocation_id)

    def test_earlier_request_id_still_replays_after_an_amend(self):
        """An amend MUST keep the earlier vouchers and earlier request_ids."""
        first_payment = self._payment(100.0)
        first_args = self._payload(
            [first_payment],
            [self._applied(INVOICE_OVERDUE, 100.0)],
            request_id="req-earlier-1",
        )
        first = self._call(first_args)
        new_payment = self._payment(50.0)
        second = self._call(
            self._payload(
                [first_payment, new_payment],
                [
                    self._applied(INVOICE_OVERDUE, 100.0),
                    self._applied(INVOICE_OPEN, 50.0),
                ],
                request_id="req-earlier-2",
            )
        )
        allocation = self.env["collection.allocation"].browse(
            second["allocation"]["id"]
        )
        self.assertEqual(second["allocation"]["revision"], 2)
        self.assertEqual(
            set(allocation.voucher_ids.mapped("document_id")),
            {first_payment["document_id"], new_payment["document_id"]},
        )
        before = self._counts()
        replayed = self._call(first_args)
        self.assertEqual(replayed["allocation"], first["allocation"])
        self.assertEqual(replayed["sheet_id"], first["sheet_id"])
        self.assertEqual(self._counts(), before)
        self.assertEqual(allocation.revision, 2)
        changed = self._payload(
            [first_payment],
            [self._applied(INVOICE_OVERDUE, 90.0)],
            request_id="req-earlier-1",
        )
        changed["payments"][0]["seller_confirmed"]["amount"] = 100.0
        err = self._assert_user_error_no_writes(lambda: self._call(changed), before)
        self._assert_generic_conflict(err, allocation)

    def test_new_non_cash_payment_without_file_refused_no_writes(self):
        """A new non-cash payment without its voucher file MUST be refused."""
        before = self._counts()
        err = self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    [self._payment(100.0, attachment=None)],
                    [self._applied(INVOICE_OVERDUE, 100.0)],
                    request_id="req-no-file",
                )
            ),
            before,
        )
        self.assertIn("file", str(err))
        self.assertIn("index 0", str(err))

    def test_new_cash_payment_without_file_is_accepted(self):
        """A cash payment MUST NOT need a voucher file."""
        payment = self._payment(100.0, document_type="cash")
        payment["seller_confirmed"] = {"document_type": "cash", "amount": 100.0}
        result = self._call(
            self._payload(
                [payment],
                [self._applied(INVOICE_OVERDUE, 100.0)],
                request_id="req-cash-no-file",
            )
        )
        self.assertEqual(result["allocation"]["revision"], 1)

    def test_reused_voucher_without_file_still_amends(self):
        """An amend MUST NOT re-check files of the seller's existing vouchers."""
        existing = self._create_vouchers([100.0])
        new_payment = self._payment(
            50.0,
            attachment={"name": "v.png", "mimetype": "image/png", "datas": PNG_B64},
        )
        result = self._call(
            self._payload(
                self._payments_from_vouchers(existing) + [new_payment],
                [
                    self._applied(INVOICE_OVERDUE, 100.0),
                    self._applied(INVOICE_OPEN, 50.0),
                ],
                request_id="req-reuse-no-file",
            )
        )
        self.assertEqual(result["allocation"]["total_vouchers"], 150.0)

    def test_partial_overlap_with_changed_fields_conflicts_no_writes(self):
        """Partial overlap whose existing payment changed fields MUST conflict."""
        existing = self._create_vouchers([100.0])
        changed = self._payments_from_vouchers(existing)
        changed[0]["seller_confirmed"]["amount"] = 90.0
        payments = changed + [self._payment(50.0)]
        before = self._counts()
        err = self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    payments,
                    [
                        self._applied(INVOICE_OVERDUE, 90.0),
                        self._applied(INVOICE_OPEN, 50.0),
                    ],
                    request_id="req-partial-changed",
                )
            ),
            before,
        )
        self._assert_generic_conflict(err, existing)

    def test_partial_overlap_with_other_sellers_voucher_conflicts_no_writes(self):
        """Partial overlap with another seller's voucher MUST generic-conflict."""
        other_seller = create_internal_seller(self.env, "collection_mcp_alloc_partial")
        ensure_enabled_seller(self.env, other_seller)
        other_sheet = self._create_sheet(seller=other_seller, force_new=True)
        foreign = self._create_vouchers(
            [100.0], sheet=other_sheet, seller=other_seller, prefix="ALLOC-PF"
        )
        payments = self._payments_from_vouchers(foreign) + [self._payment(50.0)]
        before = self._counts()
        err = self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    payments,
                    [
                        self._applied(INVOICE_OVERDUE, 100.0),
                        self._applied(INVOICE_OPEN, 50.0),
                    ],
                    request_id="req-partial-foreign",
                )
            ),
            before,
        )
        self._assert_generic_conflict(err, foreign)

    def test_other_company_document_id_conflict(self):
        """Other-company document_id hit MUST generic-conflict with no writes."""
        company_b = self._create_company("MCP-Alloc-DocCo")
        self.seller.write({"company_ids": [Command.link(company_b.id)]})
        sheet_b = self._create_sheet(company=company_b, force_new=True)
        foreign = self._create_vouchers([100.0], sheet=sheet_b, prefix="ALLOC-OC-DOC")
        before = self._counts()
        err = self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    self._payments_from_vouchers(foreign),
                    [self._applied(INVOICE_OVERDUE, 100.0)],
                    request_id="req-other-doc",
                )
            ),
            before,
        )
        self._assert_generic_conflict(err, foreign, company_b)

    def test_auto_create_sheet_off_named_error_zero_writes(self):
        """auto_create_sheet False MUST raise the named error with zero writes."""
        self.env.company.auto_create_sheet = False
        before = self._counts()
        err = self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    [self._payment(100.0)],
                    [self._applied(INVOICE_OVERDUE, 100.0)],
                    request_id="req-sheet-off",
                )
            ),
            before,
        )
        self.assertEqual(str(err), SHEET_REQUIRED_MSG)

    def test_create_new_open_while_proposal_exists(self):
        """Proposal MUST NOT occupy MCP open; create MAY open a new sheet."""
        proposal = self.sheet
        self.assertEqual(proposal.state, "open")
        confirm_sheet(proposal)
        self.assertEqual(proposal.state, "proposal")
        self.env.company.auto_create_sheet = True
        payment = self._payment(100.0)
        result = self._call(
            self._payload([payment], [self._applied(INVOICE_OVERDUE, 100.0)])
        )
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        self.assertTrue(allocation.exists())
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(allocation.sheet_id.state, "open")
        self.assertNotEqual(allocation.sheet_id, proposal)
        self.assertEqual(result["sheet_id"], allocation.sheet_id.id)
        proposal.invalidate_recordset(["state"])
        self.assertEqual(proposal.state, "proposal")

    def test_create_new_open_while_submitted_exists(self):
        """Submitted MUST NOT occupy MCP open; create MAY open a new sheet."""
        submitted = self.sheet
        self.assertEqual(submitted.state, "open")
        submitted.action_seller_close()
        self.assertEqual(submitted.state, "submitted")
        self.env.company.auto_create_sheet = True
        payment = self._payment(100.0)
        result = self._call(
            self._payload([payment], [self._applied(INVOICE_OVERDUE, 100.0)])
        )
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        self.assertTrue(allocation.exists())
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(allocation.sheet_id.state, "open")
        self.assertNotEqual(allocation.sheet_id, submitted)
        self.assertEqual(result["sheet_id"], allocation.sheet_id.id)
        submitted.invalidate_recordset(["state"])
        self.assertEqual(submitted.state, "submitted")

    def test_empty_applications_on_account(self):
        """Empty applications MUST expand to every outstanding ERP invoice at 0."""
        payment = self._payment(80.0)
        result = self._call(
            self._payload(
                [payment],
                [self._receipt([payment])],
                request_id="req-empty-applications",
            )
        )
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        self._assert_debt_lines(
            allocation,
            {
                INVOICE_OVERDUE["external_invoice_id"]: 0.0,
                INVOICE_OPEN["external_invoice_id"]: 0.0,
            },
        )
        self.assertEqual(allocation.total_applied, 0.0)
        self.assertEqual(allocation.total_vouchers, 80.0)
        self.assertEqual(allocation.residual, 150.0)
        self.assertEqual(allocation.total_debt, 150.0)
        self._assert_payload(
            result, allocation, revision=1, document_ids=[payment["document_id"]]
        )

    def test_applied_only_payload_expands_outstanding_zeros(self):
        """I1 applied + omitted I2 MUST persist I2 at amount_applied 0."""
        payment = self._payment(100.0)
        result = self._call(
            self._payload(
                [payment],
                [self._applied(INVOICE_OVERDUE, 100.0)],
                request_id="req-expand-i2-zero",
            )
        )
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        self._assert_debt_lines(
            allocation,
            {
                INVOICE_OVERDUE["external_invoice_id"]: 100.0,
                INVOICE_OPEN["external_invoice_id"]: 0.0,
            },
        )
        self.assertEqual(allocation.total_applied, 100.0)
        self.assertEqual(allocation.total_debt, 150.0)
        self.assertEqual(allocation.residual, 50.0)

    def test_residual_reason_not_stored(self):
        """Persist MUST succeed without residual_reason on allocation or revision."""
        payment = self._payment(150.0)
        result = self._call(
            self._payload(
                [payment],
                [self._applied(INVOICE_OVERDUE, 100.0)],
                request_id="req-missing-reason",
            )
        )
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        self.assertTrue(allocation.exists())
        self.assertEqual(allocation.residual, 50.0)
        self.assertFalse(hasattr(type(allocation), "residual_reason"))
        self.assertNotIn("residual_reason", allocation._fields)

    def test_applications_exceeding_funded_values_refused(self):
        """Applied above funded receipt values MUST raise with no writes."""
        before = self._counts()
        payment = self._payment(10.0)
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    [payment],
                    [self._applied(INVOICE_OVERDUE, 100.0)],
                    request_id="req-over-funded",
                )
            ),
            before,
        )

    def test_identical_receipts_new_request_id_is_hash_noop(self):
        """Matching receipt content with a new request_id MUST not add a revision."""
        payment = self._payment(150.0)
        receipts = [self._applied(INVOICE_OVERDUE, 100.0)]
        first = self._call(
            self._payload(
                [payment],
                receipts,
                request_id="req-reason-1",
            )
        )
        allocation = self.env["collection.allocation"].browse(first["allocation"]["id"])
        self.assertEqual(allocation.revision, 1)
        write_date = allocation.write_date
        before = self._counts()
        second = self._call(
            self._payload(
                [payment],
                receipts,
                request_id="req-reason-2",
            )
        )
        allocation.invalidate_recordset()
        self.assertEqual(second["allocation"]["id"], first["allocation"]["id"])
        self.assertEqual(allocation.revision, 1)
        self.assertEqual(second["allocation"]["revision"], 1)
        self.assertEqual(list(allocation.request_log), ["req-reason-1"])
        self.assertEqual(allocation.request_id, "req-reason-1")
        self.assertEqual(allocation.write_date, write_date)
        self.assertEqual(self._counts(), before)

    def test_parse_receipt_applications_reject_non_positive(self):
        """Parse MUST reject non-positive application amounts and empty receipts."""
        mixin = self.env["muk_mcp.mixin"]
        payment_vals = [
            {"document_id": "DOC-A", "amount": 50.0, "document_type": "bank_transfer"}
        ]
        rows = mixin._collection_parse_allocation_receipts(
            [
                {
                    "document_kind": "invoice",
                    "values": [{"document_id": "DOC-A", "amount": 50.0}],
                    "applications": [self._application(INVOICE_OPEN, 50.0)],
                }
            ],
            payment_vals,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["applications"][0]["amount_applied"], 50.0)
        with self.assertRaises(UserError):
            mixin._collection_parse_allocation_receipts([], payment_vals)
        with self.assertRaises(UserError):
            mixin._collection_parse_allocation_receipts(
                [
                    {
                        "document_kind": "invoice",
                        "values": [{"document_id": "DOC-A", "amount": 50.0}],
                        "applications": [self._application(INVOICE_OVERDUE, 0.0)],
                    }
                ],
                payment_vals,
            )

    def test_unsent_erp_invoices_expand_at_zero(self):
        """Applications omit I2; persist MUST still snapshot I2 at amount_applied 0."""
        result = self._call(
            self._payload(
                [self._payment(100.0)],
                [self._applied(INVOICE_OVERDUE, 100.0)],
                request_id="req-zero-stale-ignored",
            )
        )
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        self._assert_debt_lines(
            allocation,
            {
                INVOICE_OVERDUE["external_invoice_id"]: 100.0,
                INVOICE_OPEN["external_invoice_id"]: 0.0,
            },
        )
        self.assertNotIn(
            "inv-bound-paid",
            allocation.line_ids.mapped("external_invoice_id"),
        )

    def test_revalidation_rolls_back_vouchers(self):
        """ERP revalidation failure MUST roll back newly created vouchers."""
        paid = {
            "external_invoice_id": "inv-bound-paid",
            "number": "A-0003",
            "issue_date": "2026-02-01",
            "due_date": "2026-03-01",
            "amount": 20.0,
            "balance": 20.0,
            "state": "paid",
        }
        before = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    [self._payment(20.0)],
                    [self._applied(paid, 20.0)],
                    request_id="req-reval-rollback",
                )
            ),
            before,
        )

    def test_unbound_write_lazy_creates_partner_and_binding(self):
        """Unbound listable identification MUST lazy-create partner and binding."""
        before_partners = self._partner_binding_counts()
        payment = self._payment(80.0)
        result = self._call(
            self._payload(
                [payment],
                [],
                customer_identification=UNBOUND_LISTABLE,
                request_id="req-lazy-partner",
                residual_reason="on_account",
            )
        )
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        after = self._partner_binding_counts()
        self.assertEqual(after["partners"], before_partners["partners"] + 1)
        self.assertEqual(after["bindings"], before_partners["bindings"] + 1)
        self.assertEqual(allocation.partner_id.vat, UNBOUND_LISTABLE)
        binding = self.env["collection.connector.customer.binding"].search(
            [("identification", "=", UNBOUND_LISTABLE)]
        )
        self.assertEqual(binding.partner_id, allocation.partner_id)
        self.assertEqual(allocation.voucher_ids.partner_id, allocation.partner_id)

    def test_amend_superset_bumps_revision(self):
        """SUPERSET voucher set MUST amend revision+1 and link the new voucher."""
        first_payment = self._payment(100.0)
        first = self._call(
            self._payload(
                [first_payment],
                [self._applied(INVOICE_OVERDUE, 100.0)],
                request_id="req-amend-1",
            )
        )
        extra = self._create_vouchers([50.0])
        first_voucher = self.env["collection.voucher"].search(
            [("document_id", "=", first_payment["document_id"])]
        )
        combined = first_voucher | extra
        second = self._call(
            self._payload(
                self._payments_from_vouchers(combined),
                [
                    self._applied(INVOICE_OVERDUE, 100.0),
                    self._applied(INVOICE_OPEN, 50.0),
                ],
                request_id="req-amend-2",
            )
        )
        allocation = self.env["collection.allocation"].browse(
            second["allocation"]["id"]
        )
        self.assertEqual(allocation.id, first["allocation"]["id"])
        self.assertEqual(allocation.revision, 2)
        self.assertEqual(second["allocation"]["revision"], 2)
        self.assertEqual(allocation.voucher_ids, combined)
        self.assertEqual(allocation.total_vouchers, 150.0)
        self.assertEqual(allocation.total_applied, 150.0)
        self.assertEqual(allocation.residual, 0.0)
        self.assertEqual(allocation.state, "draft")
        self.assertEqual(second["allocation"]["state"], "draft")
        self.assertEqual(len(allocation.request_log), 2)
        self._assert_payload(
            second,
            allocation,
            revision=2,
            document_ids=combined.mapped("document_id"),
        )

    def test_subset_and_partial_overlap_rejected(self):
        """Subset or partial overlap MUST UserError with no writes."""
        v1 = self._create_vouchers([100.0])
        v2 = self._create_vouchers([50.0])
        current = v1 | v2
        self._call(
            self._payload(
                self._payments_from_vouchers(current),
                [
                    self._applied(INVOICE_OVERDUE, 100.0),
                    self._applied(INVOICE_OPEN, 50.0),
                ],
                request_id="req-overlap-base",
            )
        )
        before = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    self._payments_from_vouchers(v1),
                    [self._applied(INVOICE_OVERDUE, 100.0)],
                    request_id="req-overlap-subset",
                )
            ),
            before,
        )
        v3 = self._create_vouchers([40.0])
        before_partial = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    self._payments_from_vouchers(v2 | v3),
                    [self._applied(INVOICE_OPEN, 50.0)],
                    request_id="req-overlap-partial",
                    residual_reason="on_account",
                )
            ),
            before_partial,
        )
        allocation = self.env["collection.allocation"].search(
            [("sheet_id", "=", self.sheet.id), ("partner_id", "=", self.partner.id)]
        )
        self.assertEqual(allocation.revision, 1)
        self.assertEqual(allocation.voucher_ids, current)

    def test_unique_violation_same_company_replays(self):
        """UniqueViolation then same-company request_id re-lookup MUST replay."""
        payment = self._payment(100.0)
        arguments = self._payload(
            [payment],
            [self._applied(INVOICE_OVERDUE, 100.0)],
            request_id="req-uv-replay",
        )
        first = self._call(arguments)
        allocation = self.env["collection.allocation"].browse(first["allocation"]["id"])
        write_date = allocation.write_date
        before = self._counts()
        search_patch, calls = self._patch_request_lookup_miss_once("req-uv-replay")
        mixin_cls = type(self.env["muk_mcp.mixin"])

        def raise_unique(*_args, **_kwargs):
            raise UniqueViolation()

        with (
            mute_logger("odoo.sql_db"),
            search_patch,
            patch.object(mixin_cls, "_collection_allocation_write", raise_unique),
        ):
            second = self._call(arguments)
        self.assertGreaterEqual(
            calls["n"],
            2,
            "Expected initial miss + post-UniqueViolation re-lookup",
        )
        self.assertEqual(second["allocation"]["id"], first["allocation"]["id"])
        self.assertEqual(second["allocation"]["revision"], 1)
        self._assert_payload(
            second, allocation, revision=1, document_ids=[payment["document_id"]]
        )
        allocation.invalidate_recordset()
        self.assertEqual(allocation.write_date, write_date)
        self.assertEqual(self._counts(), before)

    def test_unique_violation_hidden_other_company_generic_no_ids(self):
        """Hidden other-company request_id UniqueViolation MUST generic-conflict."""
        company_b = self._create_company("MCP-Alloc-OtherCo")
        seller_b = create_internal_seller(self.env, "collection_mcp_alloc_seller_b")
        seller_b.write({"company_ids": [Command.link(company_b.id)]})
        sheet_b = self._create_sheet(seller=seller_b, company=company_b, force_new=True)
        partner_b = dummy_customer_partner(self.env, customer="ALLOC-OTHER-CO")
        voucher_b = self._create_vouchers(
            [40.0], partner=partner_b, sheet=sheet_b, seller=seller_b, prefix="ALLOC-B"
        )
        foreign = (
            self.env["collection.allocation"]
            .with_company(company_b)
            .create(
                {
                    "sheet_id": sheet_b.id,
                    "partner_id": partner_b.id,
                    "voucher_ids": [Command.set(voucher_b.ids)],
                }
            )
        )
        with privileged("collection_allocation_request"):
            foreign.write(
                {
                    "request_id": "req-uv-hidden",
                    "content_hash": "foreign-hash",
                    "request_log": {
                        "req-uv-hidden": {
                            "revision": 1,
                            "content_hash": "foreign-hash",
                            "total_vouchers": 40.0,
                            "total_applied": 0.0,
                            "residual": 40.0,
                        }
                    },
                }
            )
        self.internal_user.write(
            {
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
            }
        )
        hidden = (
            self.env["collection.allocation"]
            .with_user(self.internal_user)
            .search([("request_id", "=", "req-uv-hidden")])
        )
        self.assertFalse(hidden, "Caller must not see company B's allocation")
        before = self._counts()
        with mute_logger("odoo.sql_db"):
            err = self._assert_user_error_no_writes(
                lambda: self._call(
                    self._payload(
                        [self._payment(100.0)],
                        [self._applied(INVOICE_OVERDUE, 100.0)],
                        request_id="req-uv-hidden",
                    )
                ),
                before,
            )
        self._assert_generic_conflict(err, foreign, company_b)
        self.assertNotIn(str(foreign.id), str(err))

    def test_amount_null_or_non_positive_rejected(self):
        """Null or ≤0 voucher amount MUST error with no writes."""
        before = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    [self._payment(0.0)],
                    [self._applied(INVOICE_OVERDUE, 100.0)],
                    request_id="req-zero-amount",
                )
            ),
            before,
        )
        empty = self._create_vouchers([100.0], prefix="ALLOC-NULL")
        self.env.cr.execute(
            "UPDATE collection_voucher SET amount = NULL WHERE id = %s",
            [empty.id],
        )
        empty.invalidate_recordset(["amount"])
        before_null = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    self._payments_from_vouchers(empty),
                    [self._applied(INVOICE_OVERDUE, 100.0)],
                    request_id="req-null-amount",
                )
            ),
            before_null,
        )

    def test_all_voucher_states_may_allocate(self):
        """draft, validated_seller, and validated_collections must allocate."""
        for index, state in enumerate(
            ("draft", "validated_seller", "validated_collections")
        ):
            if index:
                self._close_open_sheet()
                self.sheet = self._create_sheet(force_new=True)
            vouchers = self._create_vouchers([10.0], prefix=f"ALLOC-ST-{state}")
            if state == "validated_seller":
                vouchers.action_validate_seller()
            elif state == "validated_collections":
                with privileged("collection_audited_state"):
                    vouchers.write({"state": "validated_collections"})
            result = self._call(
                self._payload(
                    self._payments_from_vouchers(vouchers),
                    [self._applied(INVOICE_OVERDUE, 10.0)],
                    request_id=f"req-all-states-{state}",
                )
            )
            self.assertTrue(result["allocation"]["id"])
            self.assertEqual(vouchers.state, state)
            self.assertEqual(result["vouchers"][0]["state"], state)

    def test_rejected_voucher_other_company_other_sheet_mixed_rejected(self):
        """Other-company, other-sheet, and mixed sets MUST error."""
        company_b = self._create_company("MCP-Alloc-VoucherCo")
        self.seller.write({"company_ids": [Command.link(company_b.id)]})
        sheet_b = self._create_sheet(company=company_b, force_new=True)
        other_company = self._create_vouchers([100.0], sheet=sheet_b, prefix="ALLOC-OC")
        before_other_company = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    self._payments_from_vouchers(other_company),
                    [self._applied(INVOICE_OVERDUE, 100.0)],
                    request_id="req-other-company",
                )
            ),
            before_other_company,
        )

        closed_vouchers = self._create_vouchers(
            [100.0], sheet=self.sheet, prefix="ALLOC-CLOSED"
        )
        self._close_open_sheet()
        other_sheet = self._create_sheet(force_new=True)
        before_closed = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    self._payments_from_vouchers(closed_vouchers),
                    [self._applied(INVOICE_OVERDUE, 100.0)],
                    request_id="req-closed-sheet",
                )
            ),
            before_closed,
        )
        mixed_sheet = self._create_vouchers(
            [50.0], sheet=other_sheet, prefix="ALLOC-MS"
        )
        open_vouchers = self._create_vouchers(
            [50.0], sheet=other_sheet, prefix="ALLOC-OPEN"
        )
        before_mixed_sheet = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    self._payments_from_vouchers(closed_vouchers | mixed_sheet),
                    [self._applied(INVOICE_OVERDUE, 100.0)],
                    request_id="req-mixed-sheet",
                )
            ),
            before_mixed_sheet,
        )

        other_partner = dummy_customer_partner(self.env, customer="ALLOC-MIX-PARTNER")
        mixed_partner = self._create_vouchers(
            [50.0], partner=other_partner, sheet=other_sheet, prefix="ALLOC-MP"
        )
        before_mixed = self._partner_binding_counts()
        before_mixed_partner = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    self._payments_from_vouchers(open_vouchers | mixed_partner),
                    [self._applied(INVOICE_OVERDUE, 100.0)],
                    request_id="req-mixed-partner",
                )
            ),
            before_mixed_partner,
        )
        self.assertEqual(self._partner_binding_counts(), before_mixed)

        other_seller = create_internal_seller(self.env, "collection_mcp_alloc_mixed")
        ensure_enabled_seller(self.env, other_seller)
        self.env["collection.connector.seller.binding"].create(
            {
                "connector_id": self.connector.id,
                "external_seller_id": "ext-alloc-mixed",
                "user_id": other_seller.id,
            }
        )
        before_mixed_seller = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    self._payments_from_vouchers(open_vouchers),
                    [self._applied(INVOICE_OVERDUE, 100.0)],
                    seller_id=other_seller.id,
                    request_id="req-mixed-seller",
                )
            ),
            before_mixed_seller,
        )

    def test_own_voucher_of_another_customer_is_named_no_writes(self):
        """A seller's own voucher of another customer MUST be named."""
        other = dummy_customer_partner(self.env, customer="ALLOC-OTHER-CUSTOMER")
        loaded = self._create_vouchers([100.0], partner=other, prefix="ALLOC-OCU")
        mixed = self._payments_from_vouchers(loaded) + [self._payment(50.0)]
        alone = self._payments_from_vouchers(loaded)
        for payments, request_id in (
            (mixed, "req-other-customer-mixed"),
            (alone, "req-other-customer-alone"),
        ):
            err = self._assert_user_error_no_writes(
                lambda payments=payments, request_id=request_id: self._call(
                    self._payload(
                        payments,
                        [self._applied(INVOICE_OVERDUE, 100.0)],
                        request_id=request_id,
                    )
                )
            )
            message = str(err)
            self.assertIn("already loaded for another customer", message)
            self.assertIn(loaded.document_id, message)
            self.assertIn(other.display_name, message)

    def test_unbound_reuse_and_partner_mismatch_rejected_no_create(self):
        """Reuse with unbound ident or partner mismatch MUST not create rows."""
        vouchers = self._create_vouchers([100.0])
        before = self._counts()
        before_partners = self._partner_binding_counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    self._payments_from_vouchers(vouchers),
                    [self._applied(INVOICE_OVERDUE, 100.0)],
                    customer_identification="99-99999999-9",
                    request_id="req-unbound",
                )
            ),
            before,
        )
        self.assertEqual(self._partner_binding_counts(), before_partners)
        other = dummy_customer_partner(self.env, customer="ALLOC-MISMATCH")
        mismatched = self._create_vouchers([100.0], partner=other, prefix="ALLOC-MM")
        before_mismatch = self._counts()
        before_mismatch_partners = self._partner_binding_counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    self._payments_from_vouchers(mismatched),
                    [self._applied(INVOICE_OVERDUE, 100.0)],
                    request_id="req-mismatch",
                )
            ),
            before_mismatch,
        )
        self.assertEqual(self._partner_binding_counts(), before_mismatch_partners)

    def test_empty_payments_and_authorization_denied(self):
        """Empty payments, portal/public, and non-enabled seller MUST fail closed."""
        before = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    [],
                    [self._applied(INVOICE_OVERDUE, 100.0)],
                    request_id="req-empty-payments",
                )
            ),
            before,
        )
        payment = self._payment(100.0)
        arguments = self._payload(
            [payment], [self._applied(INVOICE_OVERDUE, 100.0)], request_id="req-auth"
        )
        for user in (self.portal_user, self.public_user):
            with self.subTest(login=user.login):
                with self.assertRaises(AccessError):
                    self._call(arguments, user=user)
        self.assertEqual(self._counts(), before)

        other = create_internal_seller(self.env, "collection_mcp_alloc_disabled")
        self.env["collection.connector.seller.binding"].create(
            {
                "connector_id": self.connector.id,
                "external_seller_id": "ext-unbound",
                "user_id": other.id,
            }
        )
        self.assertNotIn(other, self.env.company.enabled_seller_ids)
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    [self._payment(100.0)],
                    [self._applied(INVOICE_OVERDUE, 100.0)],
                    seller_id=other.id,
                    request_id="req-disabled-seller",
                )
            ),
            before,
        )

    def test_confirmed_destination_refuses_amend(self):
        """Confirmed destination MUST refuse amend with no writes."""
        payment = self._payment(100.0)
        first = self._call(
            self._payload([payment], [self._applied(INVOICE_OVERDUE, 100.0)])
        )
        allocation = self.env["collection.allocation"].browse(first["allocation"]["id"])
        self._confirm(allocation)
        extra = self._create_vouchers([50.0])
        first_voucher = self.env["collection.voucher"].search(
            [("document_id", "=", payment["document_id"])]
        )
        before = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    self._payments_from_vouchers(first_voucher | extra),
                    [
                        self._applied(INVOICE_OVERDUE, 100.0),
                        self._applied(INVOICE_OPEN, 50.0),
                    ],
                    request_id="req-frozen-amend",
                )
            ),
            before,
        )
        allocation.invalidate_recordset()
        self.assertEqual(allocation.state, "confirmed")
        self.assertEqual(allocation.revision, 1)
        self.assertEqual(allocation.voucher_ids, first_voucher)

    def test_closed_sheet_refuses_amend(self):
        """Closed-sheet destination MUST refuse amend with no writes."""
        payment = self._payment(100.0)
        first = self._call(
            self._payload([payment], [self._applied(INVOICE_OVERDUE, 100.0)])
        )
        allocation = self.env["collection.allocation"].browse(first["allocation"]["id"])
        extra = self._create_vouchers([50.0])
        first_voucher = self.env["collection.voucher"].search(
            [("document_id", "=", payment["document_id"])]
        )
        self._close_open_sheet()
        self.assertEqual(allocation.state, "confirmed")
        before = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    self._payments_from_vouchers(first_voucher | extra),
                    [
                        self._applied(INVOICE_OVERDUE, 100.0),
                        self._applied(INVOICE_OPEN, 50.0),
                    ],
                    request_id="req-closed-amend",
                )
            ),
            before,
        )
        allocation.invalidate_recordset()
        self.assertEqual(allocation.state, "confirmed")
        self.assertEqual(allocation.revision, 1)
        self.assertEqual(allocation.voucher_ids, first_voucher)

    def test_revalidation_subtracts_other_draft_and_confirmed(self):
        """Available MUST be fresh balance minus other draft and confirmed applies."""
        other_partner = dummy_customer_partner(self.env, customer="ALLOC-OTHER-DRAFT")
        other_vouchers = self._create_vouchers(
            [40.0], partner=other_partner, prefix="ALLOC-DRAFT-OTHER"
        )
        other_alloc = self.env["collection.allocation"].create(
            {
                "sheet_id": self.sheet.id,
                "partner_id": other_partner.id,
                "voucher_ids": [Command.set(other_vouchers.ids)],
                "line_ids": [
                    Command.create(
                        {
                            "external_invoice_id": INVOICE_OPEN["external_invoice_id"],
                            "invoice_number": INVOICE_OPEN["number"],
                            "issue_date": INVOICE_OPEN["issue_date"],
                            "due_date": INVOICE_OPEN["due_date"],
                            "invoice_amount": INVOICE_OPEN["amount"],
                            "invoice_balance": INVOICE_OPEN["balance"],
                            "invoice_state": INVOICE_OPEN["state"],
                            "amount_applied": 40.0,
                        }
                    )
                ],
            }
        )
        self.assertEqual(other_alloc.state, "draft")
        over = self._create_vouchers([20.0], prefix="ALLOC-OVER")
        before = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    self._payments_from_vouchers(over),
                    [self._applied(INVOICE_OPEN, 20.0)],
                    request_id="req-over-available",
                )
            ),
            before,
        )
        ok = self._create_vouchers([10.0], prefix="ALLOC-OK")
        first = self._call(
            self._payload(
                self._payments_from_vouchers(ok),
                [self._applied(INVOICE_OPEN, 10.0)],
                request_id="req-ok-available",
            )
        )
        first_alloc = self.env["collection.allocation"].browse(
            first["allocation"]["id"]
        )
        self.assertEqual(first_alloc.total_applied, 10.0)
        self.assertEqual(first_alloc.state, "draft")
        self.assertNotEqual(first_alloc.id, other_alloc.id)

        self._close_open_sheet()
        other_alloc.invalidate_recordset()
        first_alloc.invalidate_recordset()
        self.assertEqual(other_alloc.state, "confirmed")
        self.assertEqual(first_alloc.state, "confirmed")
        sheet_two = self._create_sheet(force_new=True)
        too_much = self._create_vouchers([10.0], sheet=sheet_two, prefix="ALLOC-CONF")
        before_conf = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    self._payments_from_vouchers(too_much),
                    [self._applied(INVOICE_OPEN, 10.0)],
                    request_id="req-confirmed-subtract",
                )
            ),
            before_conf,
        )

    def test_hidden_proposal_reservation_refuses_new_open_apply(self):
        """Hidden proposal draft of full open balance MUST refuse a 1-peso apply."""
        other_partner = dummy_customer_partner(
            self.env, customer="ALLOC-HIDDEN-PROPOSAL"
        )
        other_alloc = self.env["collection.allocation"].create(
            {
                "sheet_id": self.sheet.id,
                "partner_id": other_partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "external_invoice_id": INVOICE_OPEN["external_invoice_id"],
                            "invoice_number": INVOICE_OPEN["number"],
                            "issue_date": INVOICE_OPEN["issue_date"],
                            "due_date": INVOICE_OPEN["due_date"],
                            "invoice_amount": INVOICE_OPEN["amount"],
                            "invoice_balance": INVOICE_OPEN["balance"],
                            "invoice_state": INVOICE_OPEN["state"],
                            "amount_applied": 50.0,
                        }
                    )
                ],
            }
        )
        # Confirm now refuses an allocation whose total_applied exceeds the
        # money its vouchers actually collected, so other_alloc needs a
        # validated voucher covering its 50.0 applied before self.sheet can
        # be confirmed. This voucher is unrelated to the reservation gate
        # under test (the hidden proposal draft blocking a new open apply).
        cover = self._create_vouchers(
            [50.0],
            partner=other_partner,
            prefix="ALLOC-HIDDEN-COVER",
            allocation_id=other_alloc.id,
        )
        with privileged("collection_audited_state"):
            cover.write({"state": "validated_collections"})
        confirm_sheet(self.sheet)
        self.assertEqual(self.sheet.state, "proposal")
        self.assertEqual(other_alloc.state, "draft")
        sheet_two = self._create_sheet(force_new=True)
        too_much = self._create_vouchers([1.0], sheet=sheet_two, prefix="ALLOC-HIDDEN")
        before = self._counts()
        err = self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    self._payments_from_vouchers(too_much),
                    [self._applied(INVOICE_OPEN, 1.0)],
                    request_id="req-hidden-proposal-apply",
                )
            ),
            before,
        )
        self.assertEqual(str(err), "Applied amount exceeds available invoice balance.")

        dest_vouchers = self._create_vouchers(
            [100.0], sheet=sheet_two, prefix="ALLOC-DEST"
        )
        first = self._call(
            self._payload(
                self._payments_from_vouchers(dest_vouchers),
                [self._applied(INVOICE_OVERDUE, 100.0)],
                request_id="req-hidden-dest-create",
            )
        )
        dest = self.env["collection.allocation"].browse(first["allocation"]["id"])
        extra = self._create_vouchers(
            [10.0], sheet=sheet_two, prefix="ALLOC-DEST-AMEND"
        )
        amended = self._call(
            self._payload(
                self._payments_from_vouchers(dest.voucher_ids | extra),
                [self._applied(INVOICE_OVERDUE, 100.0)],
                request_id="req-hidden-dest-amend",
            )
        )
        dest.invalidate_recordset()
        self.assertEqual(amended["allocation"]["id"], dest.id)
        self.assertEqual(dest.revision, 2)
        self.assertEqual(dest.total_applied, 100.0)

    def test_invoice_missing_from_fresh_debt_rejected(self):
        """external_invoice_id absent from fresh get_customer_debt MUST error."""
        paid = {
            "external_invoice_id": "inv-bound-paid",
            "number": "A-0003",
            "issue_date": "2026-02-01",
            "due_date": "2026-03-01",
            "amount": 20.0,
            "balance": 20.0,
            "state": "paid",
        }
        before = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    [self._payment(100.0)],
                    [self._applied(paid, 20.0)],
                    request_id="req-stale-invoice",
                )
            ),
            before,
        )

    def test_computed_total_debt_from_fresh_snapshot(self):
        """Persist MUST store computed line-sum total_debt, not a caller total."""
        payment = self._payment(100.0)
        result = self._call(
            self._payload(
                [payment],
                [self._applied(INVOICE_OVERDUE, 100.0)],
            )
        )
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        self.assertEqual(allocation.total_debt, 150.0)

    def test_seller_confirmed_optional_raw_ocr_stamps(self):
        """seller_confirmed is required; raw_ocr stamps ocr_* only when present."""
        with_ocr = self._payment(
            40.0,
            raw_ocr={"document_type": "bank_transfer", "amount": 39.0},
        )
        self._call(self._payload([with_ocr], [self._applied(INVOICE_OVERDUE, 40.0)]))
        voucher = self.env["collection.voucher"].search(
            [("document_id", "=", with_ocr["document_id"])]
        )
        self.assertEqual(voucher.amount, 40.0)
        self.assertEqual(voucher.seller_amount, 40.0)
        self.assertEqual(voucher.ocr_amount, 39.0)
        self._close_open_sheet()
        self.sheet = self._create_sheet(force_new=True)
        seller_only = self._payment(50.0)
        self._call(
            self._payload(
                [seller_only],
                [self._applied(INVOICE_OPEN, 50.0)],
                request_id="req-seller-only-ocr",
            )
        )
        voucher_only = self.env["collection.voucher"].search(
            [("document_id", "=", seller_only["document_id"])]
        )
        self.assertEqual(voucher_only.seller_amount, 50.0)
        self.assertEqual(voucher_only.ocr_amount, 0.0)

    def test_unsupported_and_non_positive_seller_confirmed_rejected(self):
        """unsupported or non-positive seller_confirmed MUST write nothing."""
        before = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    [
                        self._payment(
                            10.0,
                            seller_confirmed={
                                "document_type": "unsupported",
                                "amount": 10.0,
                            },
                        )
                    ],
                    request_id="req-unsupported",
                )
            ),
            before,
        )
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    [self._payment(0.0)],
                    [self._applied(INVOICE_OVERDUE, 100.0)],
                    request_id="req-non-positive",
                )
            ),
            before,
        )

    def test_unsupported_document_type_rejected_in_every_nest(self):
        """``unsupported`` is no document type: no nest may carry it, nothing writes."""
        self.assertNotIn("unsupported", _DOCUMENT_TYPES)
        before = self._counts()
        for nest in ("raw_ocr", "seller_confirmed"):
            with self.subTest(nest=nest):
                payment = self._payment(10.0)
                payment[nest] = {"document_type": "unsupported", "amount": 10.0}
                self._assert_user_error_no_writes(
                    lambda payment=payment, nest=nest: self._call(
                        self._payload([payment], request_id=f"req-unsup-{nest}")
                    ),
                    before,
                )

    def test_seller_commission_seller_confirmed_rejected(self):
        """MCP write MUST reject seller_commission; it MUST NOT join the nest enum."""
        self.assertNotIn("seller_commission", _DOCUMENT_TYPES)
        before = self._counts()
        existing_commissions = self.env["collection.voucher"].search_count(
            [("document_type", "=", "seller_commission")]
        )
        err = self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    [
                        self._payment(
                            10.0,
                            seller_confirmed={
                                "document_type": "seller_commission",
                                "amount": 10.0,
                            },
                        )
                    ],
                    request_id="req-seller-commission",
                )
            ),
            before,
        )
        self.assertIn("commission", str(err).lower())
        self.assertEqual(
            self.env["collection.voucher"].search_count(
                [("document_type", "=", "seller_commission")]
            ),
            existing_commissions,
        )

    def test_receipt_validation_uniqueness_and_unknown_document(self):
        """Duplicate kind, unknown document_id, and over-split MUST raise."""
        payment = self._payment(100.0)
        before = self._counts()
        duplicate_kind = [
            self._receipt([payment], [self._application(INVOICE_OVERDUE, 40.0)]),
            self._receipt([payment], [self._application(INVOICE_OPEN, 60.0)]),
        ]
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload([payment], duplicate_kind, request_id="req-dup-kind")
            ),
            before,
        )
        unknown = [
            {
                "document_kind": "invoice",
                "values": [{"document_id": "missing-doc", "amount": 100.0}],
                "applications": [self._application(INVOICE_OVERDUE, 100.0)],
            }
        ]
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload([payment], unknown, request_id="req-unknown-doc")
            ),
            before,
        )

    def test_stale_balance_seen_refused(self):
        """Stale application balance_seen MUST raise and write nothing."""
        payment = self._payment(100.0)
        before = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    [payment],
                    [
                        self._receipt(
                            [payment],
                            [
                                self._application(
                                    INVOICE_OVERDUE, 100.0, balance_seen=80.0
                                )
                            ],
                        )
                    ],
                    request_id="req-stale-balance",
                )
            ),
            before,
        )

    def test_split_values_land_on_matching_receipts(self):
        """Explicit receipt values MUST persist on the matching receipt kinds."""
        payment = self._payment(100.0)
        result = self._call(
            self._payload(
                [payment],
                [
                    {
                        "document_kind": "invoice",
                        "values": [
                            {"document_id": payment["document_id"], "amount": 40.0}
                        ],
                        "applications": [self._application(INVOICE_OVERDUE, 40.0)],
                    },
                    {
                        "document_kind": "quotation",
                        "values": [
                            {"document_id": payment["document_id"], "amount": 60.0}
                        ],
                        "applications": [],
                    },
                ],
                request_id="req-split-persist",
            )
        )
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        invoice = allocation.receipt_ids.filtered(
            lambda rec: rec.document_kind == "invoice"
        )
        quotation = allocation.receipt_ids.filtered(
            lambda rec: rec.document_kind == "quotation"
        )
        self.assertEqual(len(invoice), 1)
        self.assertEqual(len(quotation), 1)
        self.assertEqual(invoice.value_ids.amount, 40.0)
        self.assertEqual(quotation.value_ids.amount, 60.0)
        overdue = allocation.line_ids.filtered(
            lambda line: line.external_invoice_id
            == INVOICE_OVERDUE["external_invoice_id"]
        )
        self.assertEqual(overdue.amount_applied, 40.0)
        self.assertEqual(overdue.document_kind, "invoice")

    def test_disallowed_document_type_rejected(self):
        """Disallowed document_type MUST fail via _assert_new_work with no writes."""
        allowed = self.env["collection.document.type"].search(
            [("code", "=", "cash_deposit")]
        )
        self.env.company.write(
            {"allowed_document_type_ids": [Command.set(allowed.ids)]}
        )
        before = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    [self._payment(100.0, document_type="bank_transfer")],
                    [self._applied(INVOICE_OVERDUE, 100.0)],
                    request_id="req-disallowed-type",
                )
            ),
            before,
        )

    def _seller_confirmed_dump(self, document_type, amount="150000"):
        """Inline Nebula ``model_dump(mode='json')`` nest for one allocatable type."""
        if document_type == "bank_transfer":
            return {
                "document_type": "bank_transfer",
                "amount": amount,
                "from_account": "ACC-FROM-1",
                "to_account": "ACC-TO-1",
                "voucher_number": "TRF-100",
                "voucher_date": "2026-09-01",
            }
        if document_type in ("check", "echeck"):
            return {
                "document_type": document_type,
                "amount": amount,
                # check/echeck share one duplicate-identity namespace
                # (company_id, check_number); this helper is exercised for
                # both types in the same test loop, so the number must
                # differ per type or the second create collides with the
                # first as a duplicate check.
                "check_number": f"CHK-9-{document_type}",
                "check_bank": "Banco Nacion",
                "check_issue_date": "2026-01-10",
                "check_payment_date": "2026-02-10",
                "check_type": "deferred",
            }
        if document_type == "cash_deposit":
            return {
                "document_type": "cash_deposit",
                "amount": amount,
                "to_account": "ACC-TO-1",
                "voucher_number": "CASH-1",
                "voucher_date": "2026-09-01",
            }
        if document_type == "retention_certificate":
            return {
                "document_type": "retention_certificate",
                "amount": amount,
                "voucher_number": "RET-1",
                "voucher_date": "2026-09-01",
                "retention_kind": "iva",
            }
        if document_type == "cash":
            return {
                "document_type": "cash",
                "amount": amount,
                "voucher_date": "2026-09-01",
            }
        raise AssertionError(f"unsupported dump type {document_type}")

    def _dump_payment(self, document_type, amount="150000"):
        nest = self._seller_confirmed_dump(document_type, amount)
        payment = {
            "document_id": self._next_document_id(f"DUMP-{document_type}"),
            "seller_confirmed": nest,
        }
        if document_type == "cash":
            payment["attachment"] = None
            payment["raw_ocr"] = None
        else:
            payment["raw_ocr"] = dict(nest)
        return payment

    def test_six_dump_types_persist_draft_with_decimal_strings(self):
        """Six dump types MUST persist draft ``{sheet_id,vouchers,allocation}``."""
        for document_type in (
            "bank_transfer",
            "check",
            "echeck",
            "cash_deposit",
            "retention_certificate",
            "cash",
        ):
            with self.subTest(document_type=document_type):
                payment = self._dump_payment(document_type)
                ident = f"20-dump-{document_type}-1"
                receipts = [
                    {
                        "document_kind": "invoice",
                        "values": [
                            {
                                "document_id": payment["document_id"],
                                "amount": "150000",
                            }
                        ],
                        "applications": [],
                    }
                ]
                result = self._call(
                    self._payload(
                        [payment],
                        receipts,
                        customer_identification=ident,
                        request_id=f"req-dump-{document_type}",
                    )
                )
                allocation = self.env["collection.allocation"].browse(
                    result["allocation"]["id"]
                )
                self.assertTrue(allocation.exists())
                self.assertEqual(allocation.state, "draft")
                self.assertEqual(result["allocation"]["state"], "draft")
                self._assert_payload(
                    result,
                    allocation,
                    revision=1,
                    document_ids=[payment["document_id"]],
                )
                voucher = self.env["collection.voucher"].search(
                    [("document_id", "=", payment["document_id"])]
                )
                self.assertEqual(len(voucher), 1)
                self.assertEqual(voucher.document_type, document_type)
                self.assertAlmostEqual(voucher.amount, 150000, places=2)
                if document_type == "cash":
                    self.assertFalse(voucher.message_main_attachment_id)
                if document_type == "retention_certificate":
                    self.assertEqual(voucher.retention_kind, "iva")

    def test_unsupported_dump_raises_with_zero_writes(self):
        """Dump ``unsupported`` MUST raise UserError with zero writes."""
        before = self._counts()
        payment = {
            "document_id": self._next_document_id("DUMP-unsupported"),
            "attachment": None,
            "raw_ocr": {"document_type": "unsupported"},
            "seller_confirmed": {"document_type": "unsupported"},
        }
        receipts = [
            {
                "document_kind": "invoice",
                "values": [{"document_id": payment["document_id"], "amount": "1"}],
                "applications": [],
            }
        ]
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    [payment],
                    receipts,
                    request_id="req-dump-unsupported",
                )
            ),
            before,
        )

    def test_extra_keys_on_request_payment_receipt_value_rejected(self):
        """Unknown keys at request/payment/receipt/value MUST raise with no writes."""
        payment = self._payment(100.0)
        applied = [self._application(INVOICE_OVERDUE, 100.0)]
        receipts = [self._receipt([payment], applied)]
        before = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    [payment],
                    receipts,
                    request_id="req-extra-request",
                    unexpected_request_key=True,
                )
            ),
            before,
        )
        extra_payment = dict(payment, unexpected_payment_key=1)
        extra_payment_receipts = [self._receipt([extra_payment], applied)]
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    [extra_payment],
                    extra_payment_receipts,
                    request_id="req-extra-payment",
                )
            ),
            before,
        )
        extra_receipt = dict(receipts[0], unexpected_receipt_key=1)
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    [payment], [extra_receipt], request_id="req-extra-receipt"
                )
            ),
            before,
        )
        extra_value = {
            "document_kind": "invoice",
            "values": [
                {
                    "document_id": payment["document_id"],
                    "amount": 100.0,
                    "unexpected_value_key": 1,
                }
            ],
            "applications": [self._application(INVOICE_OVERDUE, 100.0)],
        }
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload([payment], [extra_value], request_id="req-extra-value")
            ),
            before,
        )
        extra_app = dict(self._application(INVOICE_OVERDUE, 100.0))
        extra_app["unexpected_app_key"] = 1
        extra_app_receipt = {
            "document_kind": "invoice",
            "values": [{"document_id": payment["document_id"], "amount": 100.0}],
            "applications": [extra_app],
        }
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    [payment], [extra_app_receipt], request_id="req-extra-app"
                )
            ),
            before,
        )

    def test_decimal_string_receipt_amounts_persist(self):
        """Receipt value/application amounts MUST accept decimal strings."""
        payment = self._dump_payment("bank_transfer", amount="100")
        result = self._call(
            self._payload(
                [payment],
                [
                    {
                        "document_kind": "invoice",
                        "values": [
                            {"document_id": payment["document_id"], "amount": "100"}
                        ],
                        "applications": [
                            {
                                "external_document_id": INVOICE_OVERDUE[
                                    "external_invoice_id"
                                ],
                                "number": INVOICE_OVERDUE["number"],
                                "balance_seen": "100",
                                "amount_applied": "100",
                            }
                        ],
                    }
                ],
                request_id="req-decimal-receipt",
            )
        )
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        self.assertEqual(allocation.state, "draft")
        self.assertAlmostEqual(allocation.total_vouchers, 100.0, places=2)
        self.assertAlmostEqual(allocation.total_applied, 100.0, places=2)
        overdue = allocation.line_ids.filtered(
            lambda line: line.external_invoice_id
            == INVOICE_OVERDUE["external_invoice_id"]
        )
        self.assertEqual(overdue.amount_applied, 100.0)

    def test_tool_source_has_no_sudo(self):
        """tools/collection_allocation.py MUST NOT use sudo."""
        source_path = (
            Path(__file__).resolve().parents[1] / "tools" / "collection_allocation.py"
        )
        self.assertTrue(source_path.is_file(), source_path)
        source = source_path.read_text(encoding="utf-8")
        code = "\n".join(
            line for line in source.splitlines() if not line.lstrip().startswith("#")
        )
        self.assertNotIn(".sudo(", code)
        self.assertNotIn("sudo()", code)
        self.assertNotIn('{"error"', code)
        self.assertNotIn("{'error'", code)
        self.assertIn("draft", code.lower())
        self.assertNotIn("confirmed collection allocation", code.lower())

        mixin = self.env["muk_mcp.mixin"]
        method = getattr(type(mixin), TOOL_NAME, None)
        self.assertTrue(callable(method), f"muk_mcp.mixin must expose {TOOL_NAME}")
        method_code = "\n".join(
            line
            for line in inspect.getsource(method).splitlines()
            if not line.lstrip().startswith("#")
        )
        self.assertNotIn(".sudo(", method_code)
        self.assertNotIn("sudo()", method_code)
        file_source = inspect.getsource(inspect.getmodule(method))
        self.assertNotIn(".sudo(", file_source)

    def test_dispatch_ops_untouched(self):
        """Connector _DISPATCH_OPS MUST include create_receipt among the five ops."""
        from odoo.addons.collection.models.collection_connector import (
            _DISPATCH_OPS as ops,
        )

        self.assertEqual(ops, _DISPATCH_OPS)
