# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import inspect
import json
from pathlib import Path

from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase

from odoo.addons.muk_mcp.core.tool import get_tool_index

from .test_collection_acl import TestCollectionAcl
from .test_collection_payment import create_internal_seller, ensure_enabled_seller

TOOL_NAME = "close_collection_sheet"
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
_SOURCE_PATH = (
    Path(__file__).resolve().parents[1] / "tools" / "collection_sheet_close.py"
)


class TestCollectionMcpSheetClose(TransactionCase):
    """RED: MCP close_collection_sheet discovery, seller-only close, no sudo."""

    def setUp(self):
        super().setUp()
        self.tool_model = self.env["muk_mcp.tool"]
        self.internal_user = self._create_user(
            "collection_mcp_sheet_close_internal", "base.group_user"
        )
        self.portal_user = self._create_user(
            "collection_mcp_sheet_close_portal", "base.group_portal"
        )
        self.public_user = self._create_user(
            "collection_mcp_sheet_close_public", "base.group_public"
        )
        self.seller = create_internal_seller(self.env, "collection_mcp_sheet_close_ana")
        ensure_enabled_seller(self.env, self.seller)

    def _partner_has_autopost_bills_column(self):
        return TestCollectionAcl._partner_has_autopost_bills_column.__func__(self)

    def _create_user(self, login, group_xmlid):
        return TestCollectionAcl._create_user.__func__(self, login, group_xmlid)

    def _create_sheet(self, *, seller=None):
        seller = seller or self.seller
        ensure_enabled_seller(self.env, seller)
        return self.env["collection.sheet"].create({"seller_id": seller.id})

    def _args(self, **extra):
        payload = {
            "seller_id": self.seller.id,
            "cash_on_hand": 10.5,
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
        """close_collection_sheet is method-discovered write/mcp; no DB row."""
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
            "close_collection_sheet must not have a DB muk_mcp.tool row",
        )

    def test_input_schema_is_seller_id_and_amounts(self):
        """Schema MUST require seller_id plus amounts and MUST omit sheet_id."""
        by_name = {
            entry["name"]: entry for entry in self.tool_model.get_tools(registry="mcp")
        }
        schema = by_name[TOOL_NAME]["inputSchema"]
        self.assertEqual(schema["type"], "object")
        self.assertEqual(
            set(schema["required"]),
            {"seller_id", "cash_on_hand", "commission_withheld"},
        )
        self.assertEqual(
            set(schema["properties"]),
            {"seller_id", "cash_on_hand", "commission_withheld"},
        )
        self.assertEqual(schema["properties"]["seller_id"]["type"], "integer")
        self.assertEqual(schema["properties"]["cash_on_hand"]["type"], "number")
        self.assertEqual(schema["properties"]["commission_withheld"]["type"], "number")
        for key in _FORBIDDEN_INPUT_KEYS:
            self.assertNotIn(key, schema["properties"])

    def test_portal_and_public_callers_denied_access_error(self):
        """Portal and public callers MUST receive AccessError."""
        sheet = self._create_sheet()
        for user in (self.portal_user, self.public_user):
            with self.subTest(login=user.login):
                with self.assertRaises(AccessError):
                    self._call(user=user)
        self.assertEqual(sheet.state, "open")

    def test_zero_open_sheets_raise_user_error_not_null(self):
        """Zero open sheets MUST raise UserError and MUST NOT return {sheet: null}."""
        for setup in ("none", "submitted"):
            with self.subTest(setup=setup):
                if setup == "submitted":
                    self._create_sheet().action_seller_close()
                before = self.env["collection.sheet"].search_count([])
                with self.assertRaises(UserError) as ctx:
                    result = self._call()
                    self.assertNotEqual(result, {"sheet": None})
                message = str(ctx.exception)
                self.assertNotIn("{sheet: null}", message)
                for token in _LEAK_TOKENS:
                    self.assertNotIn(token, message)
                self.assertEqual(self.env["collection.sheet"].search_count([]), before)

    def test_sheet_id_is_rejected(self):
        """Passing sheet_id MUST refuse and MUST NOT change sheet state."""
        sheet = self._create_sheet()
        with self.assertRaises(UserError):
            self._call(self._args(sheet_id=sheet.id))
        self.assertEqual(sheet.state, "open")

    def test_amounts_accept_number_and_decimal_string(self):
        """Amounts MUST parse as JSON number or decimal string."""
        number_sheet = self._create_sheet()
        result = self._call(self._args(cash_on_hand=40.0, commission_withheld=5.5))
        self.assertEqual(result["sheet"]["id"], number_sheet.id)
        self.assertEqual(result["sheet"]["state"], "submitted")
        self.assertEqual(number_sheet.cash_on_hand, 40.0)
        self.assertEqual(number_sheet.commission_withheld, 5.5)

        string_sheet = self._create_sheet()
        result = self._call(
            self._args(
                seller_id=self.seller.id,
                cash_on_hand="12.50",
                commission_withheld="1.25",
            )
        )
        self.assertEqual(result["sheet"]["id"], string_sheet.id)
        self.assertEqual(string_sheet.cash_on_hand, 12.5)
        self.assertEqual(string_sheet.commission_withheld, 1.25)

    def test_internal_seller_closes_open_sheet(self):
        """Internal caller MUST close the seller's open sheet and return identity."""
        sheet = self._create_sheet()
        result = self._call()
        self.assertEqual(set(result), {"sheet"})
        payload = result["sheet"]
        self.assertEqual(set(payload), _SHEET_KEYS)
        self.assertEqual(payload["id"], sheet.id)
        self.assertEqual(payload["name"], sheet.name)
        self.assertEqual(payload["state"], "submitted")
        self.assertEqual(payload["seller_id"], self.seller.id)
        self.assertEqual(payload["voucher_count"], 0)
        self.assertIsNone(payload["date_from"])
        self.assertIsNone(payload["date_to"])
        self.assertEqual(sheet.state, "submitted")
        self.assertEqual(sheet.cash_on_hand, 10.5)
        self.assertEqual(sheet.commission_withheld, 2.25)
        self.assertNotIn("content_base64", result)
        self.assertNotIn("filename", result)

    def test_disabled_seller_can_still_close(self):
        """A later-disabled seller MUST still close an existing open sheet."""
        sheet = self._create_sheet()
        self.env.company.write({"enabled_seller_ids": [(3, self.seller.id)]})
        result = self._call()
        self.assertEqual(result["sheet"]["id"], sheet.id)
        self.assertEqual(sheet.state, "submitted")

    def test_next_write_uses_a_new_open_sheet(self):
        """After close, a later open sheet create MUST not reuse the submitted row."""
        submitted = self._create_sheet()
        self._call()
        self.assertEqual(submitted.state, "submitted")
        current = self._create_sheet()
        self.assertEqual(current.state, "open")
        self.assertNotEqual(current.id, submitted.id)
        self.assertEqual(submitted.state, "submitted")

    def test_tool_source_never_sudoes_or_returns_error_dict(self):
        """The close tool MUST NOT sudo() or return {\"error\"."""
        source = _SOURCE_PATH.read_text(encoding="utf-8")
        code = "\n".join(
            line for line in source.splitlines() if not line.lstrip().startswith("#")
        )
        self.assertNotIn("sudo(", code)
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
        self.assertNotIn('{"error"', method_code)
        file_source = inspect.getsource(inspect.getmodule(method))
        self.assertNotIn(".sudo(", file_source)
        self.assertNotIn("_assert_new_work", method_code)
