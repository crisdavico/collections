# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import inspect
import json
from pathlib import Path

from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase

from odoo.addons.muk_mcp.core.tool import get_tool_index

from .test_collection_acl import TestCollectionAcl
from .test_collection_payment import (
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
)

TOOL_NAME = "declare_collection_cash"
_SHEET_KEYS = {
    "id",
    "name",
    "state",
    "seller_id",
    "date_from",
    "date_to",
    "voucher_count",
}
_FORBIDDEN_INPUT_KEYS = ("sheet_id", "model", "domain", "fields", "context", "order")
_SOURCE_PATH = (
    Path(__file__).resolve().parents[1] / "tools" / "collection_cash_declare.py"
)


class TestCollectionMcpCashDeclare(TransactionCase):
    """RED: MCP declare_collection_cash on submitted sheets, no sudo."""

    def setUp(self):
        super().setUp()
        self.tool_model = self.env["muk_mcp.tool"]
        self.internal_user = self._create_user(
            "collection_mcp_cash_declare_internal", "collection.group_collection_user"
        )
        self.portal_user = self._create_user(
            "collection_mcp_cash_declare_portal", "base.group_portal"
        )
        self.public_user = self._create_user(
            "collection_mcp_cash_declare_public", "base.group_public"
        )
        self.seller = create_internal_seller(
            self.env, "collection_mcp_cash_declare_ana"
        )
        ensure_enabled_seller(self.env, self.seller)

    def _partner_has_autopost_bills_column(self):
        return TestCollectionAcl._partner_has_autopost_bills_column.__func__(self)

    def _create_user(self, login, group_xmlid):
        return TestCollectionAcl._create_user.__func__(self, login, group_xmlid)

    def _create_sheet(self, *, seller=None, cash=0.0):
        seller = seller or self.seller
        ensure_enabled_seller(self.env, seller)
        sheet = self.env["collection.sheet"].create({"seller_id": seller.id})
        if cash:
            voucher = self.env["collection.voucher"].create(
                {
                    "partner_id": dummy_customer_partner(
                        self.env, customer="MCP-DECLARE-CASH"
                    ).id,
                    "document_type": "cash",
                    "seller_id": seller.id,
                    "sheet_id": sheet.id,
                    "amount": cash,
                }
            )
            voucher.action_validate_seller()
        return sheet

    def _args(self, **extra):
        payload = {
            "seller_id": self.seller.id,
            "commission_withheld": 2.25,
        }
        payload.update(extra)
        return payload

    def _call(self, arguments=None, user=None):
        if arguments is None:
            arguments = self._args()
        env = self.env(user=user) if user else self.env(user=self.internal_user)
        text, _info = self.tool_model._call(TOOL_NAME, arguments, env)
        return json.loads(text)

    def test_discovered_as_method_write_mcp(self):
        """declare_collection_cash is method-discovered write/mcp; no DB row."""
        by_name = {
            entry["name"]: entry for entry in self.tool_model.get_tools(registry="mcp")
        }
        self.assertIn(TOOL_NAME, by_name)
        entry = get_tool_index(self.env, registry="mcp")[TOOL_NAME]
        self.assertEqual(entry["category"], "write")
        self.assertEqual(entry["registry"], "mcp")
        self.assertEqual(entry["kind"], "method")
        self.assertFalse(
            self.env["muk_mcp.tool"].search([("name", "=", TOOL_NAME)]),
            "declare_collection_cash must not have a DB muk_mcp.tool row",
        )

    def test_input_schema_requires_seller_and_withheld(self):
        """Schema MUST require seller_id plus withheld and MUST omit cash_on_hand."""
        by_name = {
            entry["name"]: entry for entry in self.tool_model.get_tools(registry="mcp")
        }
        schema = by_name[TOOL_NAME]["inputSchema"]
        self.assertEqual(schema["type"], "object")
        self.assertEqual(
            set(schema["required"]),
            {"seller_id", "commission_withheld"},
        )
        self.assertEqual(
            set(schema["properties"]),
            {"seller_id", "commission_withheld"},
        )
        self.assertEqual(schema["properties"]["seller_id"]["type"], "integer")
        self.assertEqual(schema["properties"]["commission_withheld"]["type"], "number")
        self.assertNotIn("cash_on_hand", schema["properties"])
        for key in _FORBIDDEN_INPUT_KEYS:
            self.assertNotIn(key, schema["properties"])

    def test_internal_seller_declares_on_submitted_sheet(self):
        """Internal caller MUST declare on the submitted sheet and return identity."""
        sheet = self._create_sheet(cash=12.75)
        sheet.action_seller_close()
        result = self._call()
        self.assertEqual(set(result), {"sheet"})
        payload = result["sheet"]
        self.assertEqual(set(payload), _SHEET_KEYS)
        self.assertEqual(payload["id"], sheet.id)
        self.assertEqual(payload["state"], "submitted")
        self.assertEqual(payload["seller_id"], self.seller.id)
        self.assertEqual(sheet.state, "submitted")
        self.assertEqual(sheet.commission_withheld, 2.25)
        self.assertEqual(sheet.cash_on_hand, 10.5)
        self.assertTrue(sheet.cash_declared_at)
        self.assertNotIn("content_base64", result)

    def test_cash_on_hand_argument_is_rejected(self):
        """cash_on_hand is computed: sending it MUST refuse the declaration."""
        sheet = self._create_sheet(cash=12.75)
        sheet.action_seller_close()
        with self.assertRaises(UserError):
            self._call(self._args(cash_on_hand=10.5))
        self.assertEqual(sheet.state, "submitted")
        self.assertFalse(sheet.cash_declared_at)
        self.assertFalse(sheet.commission_withheld)

    def test_zero_submitted_sheets_raise_user_error_not_null(self):
        """Zero submitted sheets MUST raise UserError and MUST NOT return null."""
        for setup in ("none", "open"):
            with self.subTest(setup=setup):
                if setup == "open":
                    self._create_sheet()
                before = self.env["collection.sheet"].search_count([])
                with self.assertRaises(UserError) as ctx:
                    result = self._call()
                    self.assertNotEqual(result, {"sheet": None})
                self.assertNotIn("{sheet: null}", str(ctx.exception))
                self.assertEqual(self.env["collection.sheet"].search_count([]), before)

    def test_sheet_id_is_rejected(self):
        """Passing sheet_id MUST refuse and MUST NOT stamp declarations."""
        sheet = self._create_sheet()
        sheet.action_seller_close()
        with self.assertRaises(UserError):
            self._call(self._args(sheet_id=sheet.id))
        self.assertEqual(sheet.state, "submitted")
        self.assertFalse(sheet.cash_declared_at)

    def test_open_sheet_is_not_the_declare_target(self):
        """An open sheet MUST NOT be declared; the tool targets submitted only."""
        sheet = self._create_sheet()
        self.assertEqual(sheet.state, "open")
        with self.assertRaises(UserError):
            self._call()
        self.assertEqual(sheet.state, "open")
        self.assertFalse(sheet.cash_declared_at)

    def test_portal_and_public_callers_denied_access_error(self):
        """Portal and public callers MUST receive AccessError."""
        sheet = self._create_sheet()
        sheet.action_seller_close()
        for user in (self.portal_user, self.public_user):
            with self.subTest(login=user.login):
                with self.assertRaises(AccessError):
                    self._call(user=user)
        self.assertFalse(sheet.cash_declared_at)

    def test_tool_source_never_sudoes_or_returns_error_dict(self):
        """The declare tool MUST NOT sudo() or return {\"error\"."""
        source = _SOURCE_PATH.read_text(encoding="utf-8")
        code = "\n".join(
            line for line in source.splitlines() if not line.lstrip().startswith("#")
        )
        self.assertNotIn("sudo(", code)
        self.assertNotIn('{"error"', code)
        mixin = self.env["muk_mcp.mixin"]
        method = getattr(type(mixin), TOOL_NAME, None)
        self.assertTrue(callable(method), f"muk_mcp.mixin must expose {TOOL_NAME}")
        method_code = inspect.getsource(method)
        self.assertNotIn(".sudo(", method_code)
        self.assertNotIn("_open_sheets_for_seller", method_code)
        self.assertIn("_submitted_sheets_for_seller", method_code)
