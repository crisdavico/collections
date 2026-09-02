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

from odoo.addons.muk_mcp.core.tool import get_tool_index

from .common_connector import (
    install_bound_test_connector,
    install_test_connector_type,
    mcp_env_with_listable_customers,
)
from .test_collection_acl import TestCollectionAcl
from .test_collection_payment import (
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
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
    {"test_connection", "list_sellers", "list_customers", "get_customer_debt"}
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
            "collection_mcp_alloc_internal", "base.group_user"
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

    def _applied(self, invoice, amount_applied):
        row = dict(invoice)
        row["amount_applied"] = amount_applied
        return row

    def _payment(self, amount, document_id=None, **extra):
        payment = {
            "document_id": document_id or self._next_document_id(),
            "document_type": extra.pop("document_type", "bank_transfer"),
            "amount": amount,
        }
        payment.update(extra)
        return payment

    def _payments_from_vouchers(self, vouchers):
        return [
            {
                "document_id": voucher.document_id,
                "document_type": voucher.document_type,
                "amount": voucher.amount,
            }
            for voucher in vouchers
        ]

    def _payload(self, payments, invoices, **extra):
        arguments = {
            "seller_id": extra.pop("seller_id", self.seller.id),
            "customer_identification": extra.pop("customer_identification", IDENT),
            "request_id": extra.pop("request_id", f"req-{self._testMethodName}"),
            "payments": payments,
            "invoices": invoices,
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
        text, _info = self.tool_model._call(TOOL_NAME, arguments, env)
        return json.loads(text)

    def _counts(self):
        return {
            "allocations": self.env["collection.allocation"].search_count([]),
            "lines": self.env["collection.allocation.line"].search_count([]),
            "revisions": self.env["collection.allocation.revision"].search_count([]),
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

    def _patch_revision_search_miss_once(self, request_id):
        Revision = self.env["collection.allocation.revision"]
        empty_revision = Revision.browse()
        real_search = type(Revision).search
        calls = {"n": 0}

        def search_proxy(model_self, domain=None, *args, **kwargs):
            domain = domain or []
            is_req = any(
                isinstance(term, (list, tuple))
                and len(term) >= 3
                and term[0] == "request_id"
                and term[1] == "="
                and term[2] == request_id
                for term in domain
            )
            if model_self._name == "collection.allocation.revision" and is_req:
                calls["n"] += 1
                if calls["n"] == 1:
                    return empty_revision
            return real_search(model_self, domain, *args, **kwargs)

        return patch("odoo.models.Model.search", search_proxy), calls

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
                "invoices",
            },
        )
        self.assertNotIn("vouchers", schema["properties"])
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
        invoices = schema["properties"]["invoices"]
        self.assertEqual(invoices["type"], "array")
        applied = invoices["items"]["properties"]["amount_applied"]
        self.assertEqual(applied["type"], "number")
        from odoo.addons.collection.tools.collection_allocation import (
            _INVOICE_ITEM_SCHEMA,
        )
        from odoo.addons.collection.tools.collection_voucher import _PAYMENT_SCHEMA

        self.assertEqual(payments["items"], _PAYMENT_SCHEMA)
        self.assertEqual(
            _INVOICE_ITEM_SCHEMA["properties"]["amount_applied"]["exclusiveMinimum"],
            0,
        )

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
            set(_PAYMENT_SCHEMA["required"]), {"document_id", "document_type"}
        )
        mixin = self.env["muk_mcp.mixin"]
        payments = [
            {
                "document_id": "DOC-PARSE-A",
                "document_type": "bank_transfer",
                "amount": 10.0,
            },
            {
                "document_id": "DOC-PARSE-B",
                "document_type": "cash_deposit",
                "amount": 20.0,
            },
        ]
        vals, idents = mixin._collection_parse_payment_vals(payments, f"  {IDENT}  ")
        self.assertEqual(idents, [IDENT, IDENT])
        self.assertEqual(
            [row["document_id"] for row in vals],
            ["DOC-PARSE-A", "DOC-PARSE-B"],
        )
        self.assertNotIn("customer_identification", vals[0])
        self.assertNotIn("customer_identification", vals[1])
        with self.assertRaises(UserError):
            mixin._collection_parse_payment_vals(payments, "   ")

    def test_first_create_confirmed_revision_one_totals(self):
        """First create MUST persist confirmed revision 1 with matching totals."""
        payment = self._payment(100.0)
        before = self._counts()
        result = self._call(
            self._payload([payment], [self._applied(INVOICE_OVERDUE, 100.0)])
        )
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        self.assertTrue(allocation.exists())
        self.assertEqual(allocation.state, "confirmed")
        self.assertEqual(allocation.revision, 1)
        self.assertEqual(allocation.partner_id, self.partner)
        self.assertEqual(allocation.sheet_id, self.sheet)
        self.assertEqual(allocation.total_vouchers, 100.0)
        self.assertEqual(allocation.total_applied, 100.0)
        self.assertEqual(allocation.residual, 0.0)
        self.assertEqual(allocation.total_debt, 150.0)
        self.assertEqual(len(allocation.revision_ids), 1)
        self.assertEqual(allocation.revision_ids.revision, 1)
        self._assert_payload(
            result, allocation, revision=1, document_ids=[payment["document_id"]]
        )
        self.assertEqual(self._counts()["allocations"], before["allocations"] + 1)
        self.assertEqual(self._counts()["revisions"], before["revisions"] + 1)
        self.assertEqual(self._counts()["vouchers"], before["vouchers"] + 1)

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
        revision_count = len(allocation.revision_ids)
        before = self._counts()
        second = self._call(
            self._payload(
                [payment],
                [self._applied(INVOICE_OPEN, 50.0)],
                request_id="req-replay",
                residual_reason="on_account",
            )
        )
        self.assertEqual(second, first)
        self._assert_payload(
            second, allocation, revision=1, document_ids=[payment["document_id"]]
        )
        allocation.invalidate_recordset()
        self.assertEqual(allocation.write_date, write_date)
        self.assertEqual(len(allocation.revision_ids), revision_count)
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
        self.assertEqual(len(allocation.revision_ids), 1)
        self.assertEqual(allocation.revision_ids.request_id, "req-hash-1")
        self.assertEqual(allocation.write_date, write_date)
        self.assertEqual(self._counts(), before)

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

    def test_partial_overlap_conflict_no_writes(self):
        """Partial same-company document_id overlap MUST generic-conflict."""
        existing = self._create_vouchers([100.0])
        payments = self._payments_from_vouchers(existing) + [self._payment(50.0)]
        before = self._counts()
        err = self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    payments,
                    [
                        self._applied(INVOICE_OVERDUE, 100.0),
                        self._applied(INVOICE_OPEN, 50.0),
                    ],
                    request_id="req-partial",
                )
            ),
            before,
        )
        self._assert_generic_conflict(err, existing)

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

    def test_empty_invoices_on_account(self):
        """Required empty invoices MUST allocate the full amount on account."""
        payment = self._payment(80.0)
        result = self._call(
            self._payload(
                [payment],
                [],
                request_id="req-empty-invoices",
                residual_reason="on_account",
            )
        )
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        self.assertFalse(allocation.line_ids)
        self.assertEqual(allocation.total_applied, 0.0)
        self.assertEqual(allocation.total_vouchers, 80.0)
        self.assertEqual(allocation.residual, 80.0)
        self.assertEqual(allocation.residual_reason, "on_account")
        self.assertEqual(allocation.total_debt, 150.0)
        self._assert_payload(
            result, allocation, revision=1, document_ids=[payment["document_id"]]
        )

    def test_residual_without_reason_fails(self):
        """Positive residual without residual_reason MUST fail with no writes."""
        before = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    [self._payment(150.0)],
                    [self._applied(INVOICE_OVERDUE, 100.0)],
                    request_id="req-missing-reason",
                )
            ),
            before,
        )

    def test_residual_negative_fails(self):
        """Applied amount above voucher total MUST fail with no writes."""
        before = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    [self._payment(10.0)],
                    [self._applied(INVOICE_OVERDUE, 100.0)],
                    request_id="req-negative-residual",
                )
            ),
            before,
        )

    def test_reason_only_retry_not_noop_hash_includes_reason(self):
        """content_hash MUST include residual_reason so a reason-only retry amends."""
        payment = self._payment(150.0)
        invoices = [self._applied(INVOICE_OVERDUE, 100.0)]
        first = self._call(
            self._payload(
                [payment],
                invoices,
                request_id="req-reason-1",
                residual_reason="on_account",
            )
        )
        allocation = self.env["collection.allocation"].browse(first["allocation"]["id"])
        self.assertEqual(allocation.revision, 1)
        self.assertEqual(allocation.residual_reason, "on_account")
        second = self._call(
            self._payload(
                [payment],
                invoices,
                request_id="req-reason-2",
                residual_reason="advance",
            )
        )
        allocation.invalidate_recordset()
        self.assertEqual(second["allocation"]["id"], first["allocation"]["id"])
        self.assertEqual(allocation.revision, 2)
        self.assertEqual(second["allocation"]["revision"], 2)
        self.assertEqual(allocation.residual_reason, "advance")
        self.assertEqual(len(allocation.revision_ids), 2)

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
        self.assertEqual(len(allocation.revision_ids), 2)
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
        search_patch, calls = self._patch_revision_search_miss_once("req-uv-replay")
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
                    "residual_reason": "on_account",
                }
            )
        )
        self.env["collection.allocation.revision"].with_company(company_b).with_context(
            collection_allocation_revision=True
        ).create(
            {
                "allocation_id": foreign.id,
                "revision": 1,
                "request_id": "req-uv-hidden",
                "content_hash": "foreign-hash",
                "confirmed_by": self.env.user.id,
                "confirmed_at": "2026-09-01 12:00:00",
                "total_vouchers": 40.0,
                "total_applied": 0.0,
                "total_debt": 0.0,
                "residual": 40.0,
                "residual_reason": "on_account",
            }
        )
        self.internal_user.write(
            {
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
            }
        )
        hidden = (
            self.env["collection.allocation.revision"]
            .with_user(self.internal_user)
            .search([("request_id", "=", "req-uv-hidden")])
        )
        self.assertFalse(hidden, "Caller must not see company B's revision")
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

    def test_rejected_voucher_other_company_other_sheet_mixed_rejected(self):
        """Rejected, other-company, other-sheet, and mixed sets MUST error."""
        rejected = self._create_vouchers([100.0], prefix="ALLOC-REJ")
        rejected.action_reject()
        before = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    self._payments_from_vouchers(rejected),
                    [self._applied(INVOICE_OVERDUE, 100.0)],
                    request_id="req-rejected-voucher",
                )
            ),
            before,
        )

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
        self.sheet.action_close()
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

    def test_destination_not_confirmed_refuses_amend(self):
        """Validated or rejected destination MUST refuse amend with no writes."""
        payment = self._payment(100.0)
        first = self._call(
            self._payload([payment], [self._applied(INVOICE_OVERDUE, 100.0)])
        )
        allocation = self.env["collection.allocation"].browse(first["allocation"]["id"])
        allocation.action_validate()
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
        self.assertEqual(allocation.state, "validated")
        self.assertEqual(allocation.revision, 1)
        self.assertEqual(allocation.voucher_ids, first_voucher)

    def test_revalidation_subtracts_other_confirmed_and_validated(self):
        """Available MUST be fresh balance minus other confirmed/validated applies."""
        first_payment = self._payment(40.0)
        first = self._call(
            self._payload(
                [first_payment],
                [self._applied(INVOICE_OPEN, 40.0)],
                request_id="req-prior",
            )
        )
        first_alloc = self.env["collection.allocation"].browse(
            first["allocation"]["id"]
        )
        self.sheet.action_close()
        sheet_two = self._create_sheet(force_new=True)
        over = self._create_vouchers([20.0], sheet=sheet_two, prefix="ALLOC-OVER")
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
        ok = self._create_vouchers([10.0], sheet=sheet_two, prefix="ALLOC-OK")
        second = self._call(
            self._payload(
                self._payments_from_vouchers(ok),
                [self._applied(INVOICE_OPEN, 10.0)],
                request_id="req-ok-available",
            )
        )
        second_alloc = self.env["collection.allocation"].browse(
            second["allocation"]["id"]
        )
        self.assertEqual(second_alloc.total_applied, 10.0)
        self.assertNotEqual(second_alloc.id, first_alloc.id)

        first_alloc.action_validate()
        sheet_two.action_close()
        sheet_three = self._create_sheet(force_new=True)
        too_much = self._create_vouchers([10.0], sheet=sheet_three, prefix="ALLOC-VAL")
        before_val = self._counts()
        self._assert_user_error_no_writes(
            lambda: self._call(
                self._payload(
                    self._payments_from_vouchers(too_much),
                    [self._applied(INVOICE_OPEN, 10.0)],
                    request_id="req-validated-subtract",
                )
            ),
            before_val,
        )

    def test_rejected_allocation_does_not_reduce_available(self):
        """Triangulation: rejected applications MUST NOT reduce available balance."""
        first_payment = self._payment(40.0)
        first = self._call(
            self._payload(
                [first_payment],
                [self._applied(INVOICE_OPEN, 40.0)],
                request_id="req-rej-prior",
            )
        )
        first_alloc = self.env["collection.allocation"].browse(
            first["allocation"]["id"]
        )
        first_alloc.action_reject()
        self.sheet.action_close()
        sheet_two = self._create_sheet(force_new=True)
        later = self._create_vouchers([50.0], sheet=sheet_two, prefix="ALLOC-REJ-OK")
        result = self._call(
            self._payload(
                self._payments_from_vouchers(later),
                [self._applied(INVOICE_OPEN, 50.0)],
                request_id="req-rej-available",
            )
        )
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        self.assertEqual(allocation.total_applied, 50.0)

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

    def test_ignores_caller_total_debt_stores_fresh_summary(self):
        """Caller total_debt MUST be ignored; store fresh summary.total_balance."""
        payment = self._payment(100.0)
        result = self._call(
            self._payload(
                [payment],
                [self._applied(INVOICE_OVERDUE, 100.0)],
                total_debt=999.0,
            )
        )
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        self.assertEqual(allocation.total_debt, 150.0)
        self.assertNotEqual(allocation.total_debt, 999.0)

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
        """Allocation write MUST NOT expand connector _DISPATCH_OPS."""
        from odoo.addons.collection.models.collection_connector import (
            _DISPATCH_OPS as ops,
        )

        self.assertEqual(ops, _DISPATCH_OPS)
