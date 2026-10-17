# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import inspect
import json
from datetime import date
from pathlib import Path

from odoo.exceptions import AccessError, UserError
from odoo.fields import Command
from odoo.tests import TransactionCase

from odoo.addons.muk_mcp.core.tool import get_tool_index

from .common_connector import (
    advance_sheet_to,
    force_sheet_state,
    install_bound_test_connector,
    install_test_connector_type,
)
from .test_collection_acl import TestCollectionAcl
from .test_collection_payment import (
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
)

TOOL_NAME = "get_collection_allocation"
IDENT = "20-11111111-1"
UNBOUND_LISTABLE = "20-88888888-8"
UNKNOWN_IDENT = "99-00000000-0"
MULTI_OPEN_MSG = "This seller has more than one open collection sheet."
_TOP_KEYS = {"allocation", "vouchers", "invoices", "receipts"}
_ALLOC_KEYS = {
    "id",
    "name",
    "state",
    "revision",
    "total_vouchers",
    "total_applied",
    "residual",
}
_VOUCHER_KEYS = {
    "id",
    "name",
    "state",
    "document_id",
    "amount",
    "document_type",
    "check_number",
}
_INVOICE_KEYS = {
    "external_invoice_id",
    "number",
    "issue_date",
    "due_date",
    "amount",
    "balance",
    "state",
    "amount_applied",
    "document_kind",
}
_RECEIPT_KEYS = {
    "document_kind",
    "state",
    "external_receipt_id",
    "total_values",
    "total_applied",
    "amount_on_account",
    "values",
}
_RECEIPT_VALUE_KEYS = {"document_id", "amount"}
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
_MEDIA_TOKENS = ("attachment", "datas", "base64")


class TestCollectionMcpAllocationLookup(TransactionCase):
    """RED: MCP get_collection_allocation discovery, null branches, payload."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        install_test_connector_type(cls)
        cls.tool_model = cls.env["muk_mcp.tool"]
        cls.internal_user = cls._create_user(
            "collection_mcp_alloc_lookup_internal", "collection.group_collection_user"
        )
        cls.portal_user = cls._create_user(
            "collection_mcp_alloc_lookup_portal", "base.group_portal"
        )
        cls.public_user = cls._create_user(
            "collection_mcp_alloc_lookup_public", "base.group_public"
        )
        cls.seller = create_internal_seller(
            cls.env, "collection_mcp_alloc_lookup_seller"
        )

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
        self._doc_seq = 0

    @classmethod
    def _partner_has_autopost_bills_column(cls):
        return TestCollectionAcl._partner_has_autopost_bills_column.__func__(cls)

    @classmethod
    def _create_user(cls, login, group_xmlid):
        return TestCollectionAcl._create_user.__func__(cls, login, group_xmlid)

    def _call(self, arguments, user=None):
        """Run get_collection_allocation in-process and return decoded JSON."""
        env = self.env(user=user) if user else self.env(user=self.internal_user)
        text, _info = self.tool_model._call(TOOL_NAME, arguments, env)
        return json.loads(text)

    def _args(self, identification=IDENT, seller=None):
        return {
            "seller_id": (seller or self.seller).id,
            "customer_identification": identification,
        }

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
            "partners": self.env["res.partner"].search_count([]),
            "bindings": self.env["collection.connector.customer.binding"].search_count(
                []
            ),
        }

    def _assert_null(self, result):
        self.assertEqual(set(result), {"allocation"})
        self.assertIsNone(result["allocation"])

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

    def _create_sheet(self, *, seller=None, company=None):
        seller = seller or self.seller
        company = company or self.env.company
        ensure_enabled_seller(self.env, seller, company=company)
        return (
            self.env["collection.sheet"]
            .with_company(company)
            .create(
                {
                    "seller_id": seller.id,
                    "company_id": company.id,
                }
            )
        )

    def _drive_sheet(self, sheet, target):
        return advance_sheet_to(sheet, target)

    def _next_document_id(self, prefix="LOOKUP-DOC"):
        self._doc_seq += 1
        return f"{prefix}-{self._testMethodName}-{self._doc_seq}"

    def _create_voucher(self, sheet, partner, amount, **extra):
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
        return (
            self.env["collection.voucher"].with_company(sheet.company_id).create(vals)
        )

    def _line_vals(self, amount_applied=100.0, invoice_balance=100.0, **extra):
        vals = {
            "external_invoice_id": extra.pop(
                "external_invoice_id", "inv-bound-overdue"
            ),
            "invoice_number": extra.pop("invoice_number", "A-0001"),
            "issue_date": extra.pop("issue_date", date(2026, 1, 10)),
            "due_date": extra.pop("due_date", date(2026, 3, 10)),
            "invoice_amount": extra.pop("invoice_amount", invoice_balance),
            "invoice_balance": invoice_balance,
            "invoice_state": extra.pop("invoice_state", "overdue"),
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

    def test_discovered_as_method_read_mcp(self):
        """get_collection_allocation is method-discovered read/mcp; no DB row."""
        by_name = {
            entry["name"]: entry for entry in self.tool_model.get_tools(registry="mcp")
        }
        self.assertIn(TOOL_NAME, by_name)
        entry = get_tool_index(self.env, registry="mcp")[TOOL_NAME]
        self.assertEqual(entry["category"], "read")
        self.assertEqual(entry["registry"], "mcp")
        self.assertEqual(entry["kind"], "method")
        self.assertFalse(
            self.env["muk_mcp.tool"].search([("name", "=", TOOL_NAME)]),
            "get_collection_allocation must not have a DB muk_mcp.tool row",
        )
        schema = by_name[TOOL_NAME]["inputSchema"]
        self.assertEqual(schema["type"], "object")
        self.assertEqual(
            set(schema["required"]), {"seller_id", "customer_identification"}
        )
        self.assertEqual(schema["properties"]["seller_id"]["type"], "integer")
        self.assertEqual(
            schema["properties"]["customer_identification"]["type"], "string"
        )

    def test_portal_and_public_callers_denied_access_error(self):
        """Portal and public callers MUST receive AccessError."""
        self.assertTrue(self.portal_user.share)
        self.assertTrue(self.public_user.share)
        arguments = self._args()
        for user in (self.portal_user, self.public_user):
            with self.subTest(login=user.login):
                with self.assertRaises(AccessError):
                    self._call(arguments, user=user)

    def test_non_enabled_seller_fails_closed(self):
        """Seller absent from enabled_seller_ids MUST raise UserError."""
        other = create_internal_seller(
            self.env, "collection_mcp_alloc_lookup_not_enabled"
        )
        self.env["collection.connector.seller.binding"].create(
            {
                "connector_id": self.connector.id,
                "external_seller_id": "ext-unbound",
                "user_id": other.id,
            }
        )
        self.assertNotIn(other, self.env.company.enabled_seller_ids)
        self._assert_user_error_no_writes(lambda: self._call(self._args(seller=other)))

    def test_unbound_enabled_seller_fails_closed(self):
        """Enabled seller without a connector binding MUST raise UserError."""
        extra = create_internal_seller(
            self.env, "collection_mcp_alloc_lookup_unbound_seller"
        )
        ensure_enabled_seller(self.env, extra)
        self._assert_user_error_no_writes(lambda: self._call(self._args(seller=extra)))

    def test_no_open_sheet_returns_null(self):
        """No open sheet MUST return {allocation: null} with zero writes."""
        before = self._counts()
        result = self._call(self._args())
        self._assert_null(result)
        self.assertEqual(self._counts(), before)

    def test_closed_sheet_only_returns_null(self):
        """A closed sheet MUST NOT count as open; GET returns null."""
        sheet = self._create_sheet()
        self._drive_sheet(sheet, "closed")
        self.assertEqual(sheet.state, "closed")
        before = self._counts()
        result = self._call(self._args())
        self._assert_null(result)
        self.assertEqual(self._counts(), before)

    def test_proposal_sheet_does_not_occupy_mcp_open(self):
        """A proposal sheet MUST NOT satisfy MCP open lookup."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(sheet, self.partner, 150.0)
        self._create_allocation(
            sheet,
            self.partner,
            vouchers=voucher,
            lines=[self._line_vals(amount_applied=100.0, invoice_balance=100.0)],
        )
        self._drive_sheet(sheet, "proposal")
        self.assertEqual(sheet.state, "proposal")
        before = self._counts()
        result = self._call(self._args())
        self._assert_null(result)
        self.assertEqual(self._counts(), before)

    def test_submitted_sheet_does_not_occupy_mcp_open(self):
        """A submitted sheet MUST NOT satisfy MCP open lookup."""
        sheet = self._create_sheet()
        self._drive_sheet(sheet, "submitted")
        self.assertEqual(sheet.state, "submitted")
        before = self._counts()
        result = self._call(self._args())
        self._assert_null(result)
        self.assertEqual(self._counts(), before)

    def test_cancelled_sheet_only_returns_null(self):
        """A cancelled sheet MUST NOT count as open; GET returns null."""
        sheet = self._create_sheet()
        self._drive_sheet(sheet, "cancelled")
        self.assertEqual(sheet.state, "cancelled")
        before = self._counts()
        result = self._call(self._args())
        self._assert_null(result)
        self.assertEqual(self._counts(), before)

    def test_unbound_identification_returns_null_without_creating_partner(self):
        """Unbound identification MUST return null and MUST NOT create partner."""
        before = self._counts()
        result = self._call(self._args(UNBOUND_LISTABLE))
        self._assert_null(result)
        self.assertEqual(self._counts(), before)

    def test_unknown_identification_returns_null_without_creating_partner(self):
        """Unknown identification MUST return null; no partner or binding."""
        before = self._counts()
        result = self._call(self._args(UNKNOWN_IDENT))
        self._assert_null(result)
        self.assertEqual(self._counts(), before)

    def test_open_sheet_without_allocation_returns_null(self):
        """Open sheet with no allocation for the partner MUST return null."""
        self._create_sheet()
        before = self._counts()
        result = self._call(self._args())
        self._assert_null(result)
        self.assertEqual(self._counts(), before)

    def test_found_payload_omits_reason_includes_document_kind(self):
        """Found payload MUST omit residual_reason and include invoice document_kind."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(sheet, self.partner, 150.0)
        allocation = self._create_allocation(
            sheet,
            self.partner,
            vouchers=voucher,
            lines=[self._line_vals(amount_applied=100.0, invoice_balance=100.0)],
        )
        before = self._counts()
        result = self._call(self._args())
        self.assertEqual(set(result), _TOP_KEYS)
        self.assertEqual(self._counts(), before)
        body = result["allocation"]
        self.assertEqual(set(body), _ALLOC_KEYS)
        self.assertNotIn("residual_reason", body)
        self.assertEqual(body["id"], allocation.id)
        self.assertEqual(body["name"], allocation.name)
        self.assertEqual(body["state"], "draft")
        self.assertNotIn(body["state"], ("validated", "rejected"))
        self.assertIsInstance(body["revision"], int)
        self.assertNotIsInstance(body["revision"], bool)
        self.assertEqual(body["revision"], 1)
        self.assertEqual(body["total_vouchers"], 150.0)
        self.assertEqual(body["total_applied"], 100.0)
        self.assertEqual(body["residual"], 0.0)
        self.assertEqual(len(result["vouchers"]), 1)
        row = result["vouchers"][0]
        self.assertEqual(set(row), _VOUCHER_KEYS)
        self.assertEqual(row["id"], voucher.id)
        self.assertEqual(row["name"], voucher.name)
        self.assertEqual(row["state"], voucher.state)
        self.assertEqual(row["document_id"], voucher.document_id)
        self.assertEqual(row["amount"], 150.0)
        self.assertEqual(row["document_type"], "bank_transfer")
        self.assertIsNone(row["check_number"])
        self.assertEqual(len(result["invoices"]), 1)
        invoice = result["invoices"][0]
        self.assertEqual(set(invoice), _INVOICE_KEYS)
        self.assertEqual(invoice["external_invoice_id"], "inv-bound-overdue")
        self.assertEqual(invoice["number"], "A-0001")
        self.assertEqual(invoice["issue_date"], "2026-01-10")
        self.assertEqual(invoice["due_date"], "2026-03-10")
        self.assertEqual(invoice["amount"], 100.0)
        self.assertEqual(invoice["balance"], 100.0)
        self.assertEqual(invoice["state"], "overdue")
        self.assertEqual(invoice["amount_applied"], 100.0)
        self.assertEqual(invoice["document_kind"], "invoice")
        self.assertEqual(result["receipts"], [])

    def test_found_payload_includes_the_current_check_number(self):
        """A check's current number is returned, so an amend can restate it.

        create_collection_allocation validates seller_confirmed.check_number on
        every check and echeck payment, reused vouchers included, and compares
        it with the voucher's current value.
        """
        sheet = self._create_sheet()
        check = self._create_voucher(
            sheet,
            self.partner,
            200.0,
            document_type="check",
            check_number="00071264",
            seller_check_number="00071200",
        )
        echeck = self._create_voucher(
            sheet,
            self.partner,
            300.0,
            document_type="echeck",
            check_number="E-5521",
        )
        self._create_allocation(sheet, self.partner, vouchers=check | echeck)

        result = self._call(self._args())

        numbers = {
            row["document_id"]: row["check_number"] for row in result["vouchers"]
        }
        self.assertEqual(
            numbers,
            {check.document_id: "00071264", echeck.document_id: "E-5521"},
        )

    def test_get_invoices_include_stored_document_kind(self):
        """GET invoice rows MUST echo stored document_kind, including quotation."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(sheet, self.partner, 150.0)
        self._create_allocation(
            sheet,
            self.partner,
            vouchers=voucher,
            lines=[
                self._line_vals(amount_applied=100.0, invoice_balance=100.0),
                self._line_vals(
                    amount_applied=0.0,
                    invoice_balance=50.0,
                    external_invoice_id="inv-bound-open",
                    invoice_number="A-0002",
                    invoice_amount=50.0,
                    invoice_state="open",
                    document_kind="quotation",
                ),
            ],
        )
        result = self._call(self._args())
        kinds = {
            row["external_invoice_id"]: row["document_kind"]
            for row in result["invoices"]
        }
        self.assertEqual(
            kinds,
            {
                "inv-bound-overdue": "invoice",
                "inv-bound-open": "quotation",
            },
        )
        for row in result["invoices"]:
            self.assertIn("document_kind", row)
        self.assertNotIn("residual_reason", result["allocation"])

    def test_on_account_empty_invoices_still_present_as_list(self):
        """On-account allocation MUST include invoices as an empty list."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(sheet, self.partner, 80.0)
        allocation = self._create_allocation(
            sheet,
            self.partner,
            vouchers=voucher,
            lines=[],
            residual_reason="on_account",
        )
        result = self._call(self._args())
        self.assertEqual(set(result), _TOP_KEYS)
        self.assertEqual(result["allocation"]["id"], allocation.id)
        self.assertEqual(result["allocation"]["state"], "draft")
        self.assertEqual(result["allocation"]["residual"], 0.0)
        self.assertNotIn("residual_reason", result["allocation"])
        self.assertEqual(len(result["vouchers"]), 1)
        self.assertEqual(result["invoices"], [])
        self.assertEqual(result["receipts"], [])

    def test_found_open_sheet_state_is_draft(self):
        """Found open-sheet allocation MUST return state draft, never validated."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(sheet, self.partner, 100.0)
        allocation = self._create_allocation(
            sheet,
            self.partner,
            vouchers=voucher,
            lines=[self._line_vals(amount_applied=100.0, invoice_balance=100.0)],
        )
        self.assertEqual(allocation.state, "draft")
        before = self._counts()
        result = self._call(self._args())
        self.assertEqual(result["allocation"]["state"], "draft")
        self.assertEqual(result["allocation"]["id"], allocation.id)
        self.assertNotIn(result["allocation"]["state"], ("validated", "rejected"))
        self.assertIsInstance(result["vouchers"], list)
        self.assertIsInstance(result["invoices"], list)
        self.assertEqual(self._counts(), before)

    def test_multi_open_raises_existing_user_error(self):
        """More than one open sheet MUST raise the existing multi-open UserError."""
        first = self._create_sheet()
        force_sheet_state(first, "closed")
        leftover = self._create_sheet()
        force_sheet_state(first, "open")
        self.assertEqual(first.state, "open")
        self.assertEqual(leftover.state, "open")
        err = self._assert_user_error_no_writes(lambda: self._call(self._args()))
        self.assertEqual(str(err), MULTI_OPEN_MSG)

    def test_read_does_not_create_sheet_when_auto_create_on(self):
        """GET MUST NOT create a sheet even when auto_create_sheet is True."""
        self.assertTrue(self.env.company.auto_create_sheet)
        before = self._counts()
        result = self._call(self._args())
        self._assert_null(result)
        self.assertEqual(self._counts()["sheets"], before["sheets"])
        self.assertEqual(self._counts(), before)

    def _assert_no_media_keys(self, payload):
        keys = set()
        stack = [payload]
        while stack:
            current = stack.pop()
            if isinstance(current, dict):
                keys.update(current)
                stack.extend(current.values())
            elif isinstance(current, list):
                stack.extend(current)
        for token in _MEDIA_TOKENS:
            self.assertNotIn(token, keys)

    def test_found_payload_omits_attachments_and_base64(self):
        """Found payload MUST NEVER include attachment, datas, or base64 keys."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            sheet,
            self.partner,
            100.0,
            document_id=self._next_document_id("LOOKUP-PROOF"),
        )
        self._create_allocation(
            sheet,
            self.partner,
            vouchers=voucher,
            lines=[self._line_vals(amount_applied=100.0, invoice_balance=100.0)],
        )
        result = self._call(self._args())
        self.assertTrue(result["vouchers"])
        self.assertTrue(result["invoices"])
        self._assert_no_media_keys(result)

    def test_found_payload_includes_receipts_list(self):
        """Found payload MUST list receipts with values even while still draft."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(sheet, self.partner, 150.0)
        allocation = self._create_allocation(
            sheet,
            self.partner,
            vouchers=voucher,
            lines=[self._line_vals(amount_applied=100.0, invoice_balance=100.0)],
        )
        receipt = self.env["collection.receipt"].create(
            {
                "allocation_id": allocation.id,
                "document_kind": "invoice",
            }
        )
        self.env["collection.receipt.value"].create(
            {
                "receipt_id": receipt.id,
                "voucher_id": voucher.id,
                "amount": 150.0,
            }
        )
        result = self._call(self._args())
        self.assertEqual(set(result), _TOP_KEYS)
        self.assertEqual(len(result["receipts"]), 1)
        row = result["receipts"][0]
        self.assertEqual(set(row), _RECEIPT_KEYS)
        self.assertEqual(row["document_kind"], "invoice")
        self.assertEqual(row["state"], "draft")
        self.assertIsNone(row["external_receipt_id"])
        self.assertEqual(row["total_values"], 150.0)
        self.assertEqual(row["total_applied"], 100.0)
        self.assertEqual(row["amount_on_account"], 50.0)
        self.assertEqual(len(row["values"]), 1)
        self.assertEqual(set(row["values"][0]), _RECEIPT_VALUE_KEYS)
        self.assertEqual(row["values"][0]["document_id"], voucher.document_id)
        self.assertEqual(row["values"][0]["amount"], 150.0)

    def test_tool_source_has_no_sudo_or_write_helpers(self):
        """tools/allocation_lookup.py MUST NOT sudo or create partners/sheets."""
        source_path = (
            Path(__file__).resolve().parents[1] / "tools" / "allocation_lookup.py"
        )
        self.assertTrue(source_path.is_file(), source_path)
        source = source_path.read_text(encoding="utf-8")
        code = "\n".join(
            line for line in source.splitlines() if not line.lstrip().startswith("#")
        )
        self.assertNotIn(".sudo(", code)
        self.assertNotIn("sudo()", code)
        self.assertNotIn('{"error"', code)
        self.assertNotIn("resolve_customer_partner", code)
        self.assertNotIn("_resolve_open_sheet_id_for_create", code)

        mixin = self.env["muk_mcp.mixin"]
        method = getattr(type(mixin), "get_collection_allocation", None)
        self.assertTrue(
            callable(method), "muk_mcp.mixin must expose get_collection_allocation"
        )
        method_code = "\n".join(
            line
            for line in inspect.getsource(method).splitlines()
            if not line.lstrip().startswith("#")
        )
        self.assertNotIn(".sudo(", method_code)
        self.assertNotIn("sudo()", method_code)
        self.assertNotIn("resolve_customer_partner", method_code)
        self.assertNotIn("_resolve_open_sheet_id_for_create", method_code)
