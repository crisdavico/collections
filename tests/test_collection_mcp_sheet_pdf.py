# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import json
from datetime import date
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.fields import Command
from odoo.tests import TransactionCase

from odoo.addons.muk_mcp.core.tool import get_tool_index

from .test_collection_acl import TestCollectionAcl
from .test_collection_payment import (
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
)

TOOL_NAME = "get_collection_sheet_pdf"
REPORT_XMLID = "collection.action_report_collection_sheet"
REPORT_NAME = "collection.report_collection_sheet"
MULTI_OPEN_MSG = "This seller has more than one open collection sheet."
FAKE_PDF = b"%PDF-1.7 fake planilla bytes"
_TOP_KEYS = {"sheet", "filename", "mimetype", "content_base64"}
_SHEET_KEYS = {
    "id",
    "name",
    "state",
    "seller_id",
    "date_from",
    "date_to",
    "voucher_count",
}
_FORBIDDEN_INPUT_KEYS = ("model", "domain", "fields", "context", "order")
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


class TestCollectionMcpSheetPdf(TransactionCase):
    """RED: MCP get_collection_sheet_pdf discovery, null branch, base64 payload."""

    def setUp(self):
        super().setUp()
        self._doc_seq = 0
        self.tool_model = self.env["muk_mcp.tool"]
        self.internal_user = self._create_user(
            "collection_mcp_sheet_pdf_internal", "base.group_user"
        )
        self.portal_user = self._create_user(
            "collection_mcp_sheet_pdf_portal", "base.group_portal"
        )
        self.public_user = self._create_user(
            "collection_mcp_sheet_pdf_public", "base.group_public"
        )
        self.seller = create_internal_seller(self.env, "collection_mcp_sheet_pdf_ana")
        self.seller.write({"name": "Planilla Seller Ana"})
        ensure_enabled_seller(self.env, self.seller)

    # ------------------------------------------------------------------
    # Borrowed helpers
    # ------------------------------------------------------------------

    def _partner_has_autopost_bills_column(self):
        return TestCollectionAcl._partner_has_autopost_bills_column.__func__(self)

    def _create_user(self, login, group_xmlid):
        return TestCollectionAcl._create_user.__func__(self, login, group_xmlid)

    def _create_company(self, name):
        return TestCollectionAcl._create_company(self, name)

    def _restrict_user_to_company(self, user, company):
        return TestCollectionAcl._restrict_user_to_company(self, user, company)

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

    def _next_document_id(self, prefix="PDFTOOL"):
        self._doc_seq += 1
        return f"{prefix}-{self._testMethodName}-{self._doc_seq}"

    def _create_sheet(self, *, seller=None, company=None):
        seller = seller or self.seller
        company = company or self.env.company
        ensure_enabled_seller(self.env, seller, company=company)
        return (
            self.env["collection.sheet"]
            .with_company(company)
            .create({"seller_id": seller.id, "company_id": company.id})
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
        return (
            self.env["collection.voucher"].with_company(sheet.company_id).create(vals)
        )

    def _line_vals(self, amount=100.0, invoice_number="FAC-1001"):
        return {
            "external_invoice_id": self._next_document_id("INV"),
            "invoice_number": invoice_number,
            "issue_date": date(2026, 1, 1),
            "due_date": date(2026, 1, 31),
            "invoice_amount": amount,
            "invoice_balance": amount,
            "invoice_state": "open",
            "amount_applied": amount,
            "document_kind": "invoice",
        }

    def _populate(self, sheet, partner_name="Cliente Norte SA", amount=100.0):
        partner = dummy_customer_partner(self.env, customer=partner_name)
        voucher = self._create_voucher(partner, sheet, amount=amount)
        self.env["collection.allocation"].create(
            {
                "sheet_id": sheet.id,
                "partner_id": partner.id,
                "voucher_ids": [Command.set(voucher.ids)],
                "line_ids": [Command.create(self._line_vals(amount=amount))],
            }
        )
        return partner

    def _drive_sheet(self, sheet, target):
        if sheet.voucher_ids:
            sheet.voucher_ids.with_context(collection_audited_state=True).write(
                {"state": "validated_collections"}
            )
        sheet.action_confirm()
        if target == "proposal":
            return sheet
        if target == "closed":
            sheet.action_close()
            return sheet
        if target == "cancelled":
            sheet.action_cancel()
            return sheet
        raise AssertionError(target)

    # ------------------------------------------------------------------
    # Invocation
    # ------------------------------------------------------------------

    def _call(self, arguments=None, user=None):
        """Run get_collection_sheet_pdf in-process and return decoded JSON."""
        if arguments is None:
            arguments = {"seller_id": self.seller.id}
        env = self.env(user=user) if user else self.env(user=self.internal_user)
        text, _info = self.tool_model._call(TOOL_NAME, arguments, env)
        return json.loads(text)

    def _call_with_stub_render(self, arguments=None, user=None):
        """Call the tool with ir.actions.report._render stubbed; return (result, calls).

        wkhtmltopdf is absent in the test container, so no test may hit the real
        PDF pipeline; the HTML path is exercised separately.
        """
        calls = []
        report_model = type(self.env["ir.actions.report"])

        def _fake_render(report_self, report_ref, res_ids, data=None):
            calls.append(
                {
                    "report_ref": report_ref,
                    "res_ids": list(res_ids or []),
                    "uid": report_self.env.uid,
                }
            )
            return FAKE_PDF, "pdf"

        with patch.object(report_model, "_render", _fake_render):
            result = self._call(arguments, user=user)
        return result, calls

    def _counts(self):
        return {
            "sheets": self.env["collection.sheet"].search_count([]),
            "vouchers": self.env["collection.voucher"].search_count([]),
            "allocations": self.env["collection.allocation"].search_count([]),
            "attachments": self.env["ir.attachment"].search_count([]),
        }

    def _assert_null(self, result):
        self.assertEqual(set(result), {"sheet"})
        self.assertIsNone(result["sheet"])

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def test_discovered_as_method_read_mcp(self):
        """get_collection_sheet_pdf is method-discovered read/mcp; no DB row."""
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
            "get_collection_sheet_pdf must not have a DB muk_mcp.tool row",
        )

    def test_input_schema_is_seller_id_only(self):
        """Schema MUST require only integer seller_id and expose no generic keys."""
        by_name = {
            entry["name"]: entry for entry in self.tool_model.get_tools(registry="mcp")
        }
        schema = by_name[TOOL_NAME]["inputSchema"]
        self.assertEqual(schema["type"], "object")
        self.assertEqual(list(schema["required"]), ["seller_id"])
        self.assertEqual(set(schema["properties"]), {"seller_id"})
        self.assertEqual(schema["properties"]["seller_id"]["type"], "integer")
        self.assertTrue(schema["properties"]["seller_id"]["description"])
        for key in _FORBIDDEN_INPUT_KEYS:
            self.assertNotIn(key, schema["properties"])

    # ------------------------------------------------------------------
    # Authorization
    # ------------------------------------------------------------------

    def test_portal_and_public_callers_denied_access_error(self):
        """Portal and public callers MUST receive AccessError."""
        self.assertTrue(self.portal_user.share)
        self.assertTrue(self.public_user.share)
        for user in (self.portal_user, self.public_user):
            with self.subTest(login=user.login):
                with self.assertRaises(AccessError):
                    self._call(user=user)

    def test_invalid_seller_id_fails_closed(self):
        """Missing, non-numeric, portal, or unknown seller_id MUST raise UserError."""
        cases = (
            {"seller_id": 0},
            {"seller_id": -1},
            {"seller_id": self.portal_user.id},
            {"seller_id": 987654321},
        )
        before = self._counts()
        for arguments in cases:
            with self.subTest(arguments=arguments):
                with self.assertRaises(UserError) as ctx:
                    self._call(arguments)
                message = str(ctx.exception)
                for token in _LEAK_TOKENS:
                    self.assertNotIn(token, message)
        self.assertEqual(self._counts(), before)

    def test_tool_source_never_sudoes(self):
        """The tool module MUST NOT call sudo()."""
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[1] / "tools" / "sheet_report.py"
        ).read_text(encoding="utf-8")
        code = "\n".join(
            line for line in source.splitlines() if not line.lstrip().startswith("#")
        )
        self.assertNotIn("sudo(", code)

    # ------------------------------------------------------------------
    # Null branches
    # ------------------------------------------------------------------

    def test_no_sheet_at_all_returns_null(self):
        """A seller with no sheet MUST return {sheet: null} and never render."""
        before = self._counts()
        result, calls = self._call_with_stub_render()
        self._assert_null(result)
        self.assertEqual(calls, [])
        self.assertEqual(self._counts(), before)

    def test_closed_and_cancelled_sheets_return_null(self):
        """Non-open sheets MUST NOT be printed; the tool returns {sheet: null}."""
        for target in ("closed", "cancelled"):
            with self.subTest(target=target):
                sheet = self._create_sheet()
                self._populate(sheet, partner_name=f"Cliente {target}")
                self._drive_sheet(sheet, target)
                self.assertEqual(sheet.state, target)
                result, calls = self._call_with_stub_render()
                self._assert_null(result)
                self.assertEqual(calls, [])

    def test_proposal_sheet_returns_null(self):
        """A proposal sheet is not open; the tool returns {sheet: null}."""
        sheet = self._create_sheet()
        self._populate(sheet, partner_name="Cliente Proposal")
        self._drive_sheet(sheet, "proposal")
        self.assertEqual(sheet.state, "proposal")
        result, calls = self._call_with_stub_render()
        self._assert_null(result)
        self.assertEqual(calls, [])

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_open_sheet_returns_base64_pdf_envelope(self):
        """The open sheet MUST come back as a base64 PDF with sheet metadata."""
        sheet = self._create_sheet()
        self._populate(sheet)
        before = self._counts()

        result, calls = self._call_with_stub_render()

        self.assertEqual(set(result), _TOP_KEYS)
        self.assertEqual(result["mimetype"], "application/pdf")
        self.assertEqual(
            base64.b64decode(result["content_base64"], validate=True), FAKE_PDF
        )
        self.assertTrue(result["filename"].endswith(".pdf"))
        self.assertIn("Planilla_de_Cobranza", result["filename"])
        self.assertNotIn("/", result["filename"])
        self.assertNotIn(" ", result["filename"])
        self.assertIn(sheet.name.replace("/", "-"), result["filename"])

        payload = result["sheet"]
        self.assertEqual(set(payload), _SHEET_KEYS)
        self.assertEqual(payload["id"], sheet.id)
        self.assertEqual(payload["name"], sheet.name)
        self.assertEqual(payload["state"], "open")
        self.assertEqual(payload["seller_id"], self.seller.id)
        self.assertEqual(payload["voucher_count"], 1)

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["report_ref"], REPORT_NAME)
        self.assertEqual(calls[0]["res_ids"], sheet.ids)
        self.assertEqual(calls[0]["uid"], self.internal_user.id)
        self.assertEqual(self._counts(), before)

    def test_open_sheet_picked_over_closed_history(self):
        """With closed history present, the open sheet MUST be the one rendered."""
        closed = self._create_sheet()
        self._populate(closed, partner_name="Cliente Viejo")
        self._drive_sheet(closed, "closed")
        current = self._create_sheet()
        self._populate(current, partner_name="Cliente Nuevo")

        result, calls = self._call_with_stub_render()

        self.assertEqual(result["sheet"]["id"], current.id)
        self.assertEqual(calls[0]["res_ids"], current.ids)

    def test_empty_open_sheet_still_renders(self):
        """An open sheet with no vouchers MUST still return a PDF."""
        sheet = self._create_sheet()
        result, calls = self._call_with_stub_render()
        self.assertEqual(result["sheet"]["id"], sheet.id)
        self.assertEqual(result["sheet"]["voucher_count"], 0)
        self.assertIsNone(result["sheet"]["date_from"])
        self.assertIsNone(result["sheet"]["date_to"])
        self.assertEqual(len(calls), 1)

    def test_seller_scoping_two_sellers(self):
        """Each seller MUST get their own open sheet, never the other's."""
        other = create_internal_seller(self.env, "collection_mcp_sheet_pdf_beto")
        ensure_enabled_seller(self.env, other)
        mine = self._create_sheet()
        theirs = self._create_sheet(seller=other)

        result, calls = self._call_with_stub_render()
        self.assertEqual(result["sheet"]["id"], mine.id)
        self.assertEqual(calls[0]["res_ids"], mine.ids)

        result, calls = self._call_with_stub_render({"seller_id": other.id})
        self.assertEqual(result["sheet"]["id"], theirs.id)
        self.assertEqual(calls[0]["res_ids"], theirs.ids)

    def test_multiple_open_sheets_raise_user_error(self):
        """Corrupted data with two open sheets MUST raise, not guess."""
        sheet = self._create_sheet()
        # The model refuses a second open sheet per seller, so forge the
        # corruption in SQL: hand another seller's open sheet to ours.
        other = create_internal_seller(self.env, "collection_mcp_sheet_pdf_donor")
        ensure_enabled_seller(self.env, other)
        second = self._create_sheet(seller=other)
        self.env.cr.execute(
            "UPDATE collection_sheet SET seller_id = %s WHERE id = %s",
            (self.seller.id, second.id),
        )
        second.invalidate_recordset(["seller_id"])
        self.assertEqual(
            len(
                self.env["collection.sheet"]._open_sheets_for_seller(
                    self.seller, self.env.company
                )
            ),
            2,
        )
        with self.assertRaises(UserError) as ctx:
            self._call_with_stub_render()
        self.assertIn(MULTI_OPEN_MSG, str(ctx.exception))
        self.assertTrue(sheet.exists())

    # ------------------------------------------------------------------
    # Company scoping
    # ------------------------------------------------------------------

    def test_other_company_open_sheet_is_not_leaked(self):
        """A company-A caller MUST NOT receive a company-B sheet PDF."""
        company_b = self._create_company("Sheet PDF Hidden Co B")
        seller_b = create_internal_seller(self.env, "collection_mcp_sheet_pdf_hidden")
        sheet_b = self._create_sheet(seller=seller_b, company=company_b)
        self.assertEqual(sheet_b.company_id, company_b)

        user_a = self._create_user("collection_mcp_sheet_pdf_only_a", "base.group_user")
        self._restrict_user_to_company(user_a, self.env.company)

        result, calls = self._call_with_stub_render(
            {"seller_id": seller_b.id}, user=user_a
        )
        self._assert_null(result)
        self.assertEqual(calls, [])

    # ------------------------------------------------------------------
    # Real render smoke test (HTML, wkhtmltopdf-free)
    # ------------------------------------------------------------------

    def test_resolved_sheet_renders_real_template_html(self):
        """The report ref the tool uses MUST render the resolved sheet in-process."""
        sheet = self._create_sheet()
        partner = self._populate(sheet)
        report = self.env.ref(REPORT_XMLID)
        self.assertEqual(report.report_name, REPORT_NAME)

        # devel's report_assets_common still lists website snippet SCSS while
        # website is not installed; skip asset nodes so HTML render stays in-process.
        with patch.object(
            type(self.env["ir.qweb"]), "_get_asset_nodes", return_value=[]
        ):
            html, report_type = (
                self.env["ir.actions.report"]
                .with_user(self.internal_user)
                .with_context(discard_logo_check=True)
                ._render_qweb_html(REPORT_XMLID, sheet.ids)
            )
        self.assertEqual(report_type, "html")
        markup = html.decode() if isinstance(html, bytes) else html
        self.assertIn(sheet.name, markup)
        self.assertIn(partner.name, markup)
