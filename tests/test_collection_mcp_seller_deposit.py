# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import inspect
import json
import re
from datetime import date
from pathlib import Path

from odoo.exceptions import AccessError, UserError
from odoo.fields import Command
from odoo.tests import TransactionCase

from odoo.addons.collection.tools.collection_voucher import _DOCUMENT_TYPES
from odoo.addons.muk_mcp.core.tool import get_tool_index

from .test_collection_acl import TestCollectionAcl
from .test_collection_payment import (
    PNG_B64,
    create_internal_seller,
    ensure_enabled_seller,
)

TOOL_NAME = "create_seller_deposit"
ALLOCATION_TOOL = "create_collection_allocation"
_SHEET_KEYS = {
    "id",
    "name",
    "state",
    "seller_id",
    "date_from",
    "date_to",
    "voucher_count",
}
_VOUCHER_KEYS = {"id", "name", "state", "document_id"}
_FORBIDDEN_INPUT_KEYS = (
    "sheet_id",
    "customer_identification",
    "model",
    "domain",
    "fields",
    "context",
    "order",
)
_DOCUMENT_ID_RE = re.compile(r"\Asd-[0-9a-f]{32}\Z")
_SOURCE_PATH = (
    Path(__file__).resolve().parents[1] / "tools" / "collection_seller_deposit.py"
)


class TestCollectionMcpSellerDeposit(TransactionCase):
    """RED: MCP create_seller_deposit on submitted sheets, no sudo."""

    def setUp(self):
        super().setUp()
        self.tool_model = self.env["muk_mcp.tool"]
        self.internal_user = self._create_user(
            "collection_mcp_seller_deposit_internal", "base.group_user"
        )
        self.portal_user = self._create_user(
            "collection_mcp_seller_deposit_portal", "base.group_portal"
        )
        self.public_user = self._create_user(
            "collection_mcp_seller_deposit_public", "base.group_public"
        )
        self.seller = create_internal_seller(
            self.env, "collection_mcp_seller_deposit_ana"
        )
        ensure_enabled_seller(self.env, self.seller)
        self._enable_seller_deposit_type()

    def _partner_has_autopost_bills_column(self):
        return TestCollectionAcl._partner_has_autopost_bills_column.__func__(self)

    def _create_user(self, login, group_xmlid):
        return TestCollectionAcl._create_user.__func__(self, login, group_xmlid)

    def _enable_seller_deposit_type(self):
        catalog = self.env.ref("collection.document_type_seller_deposit")
        self.env.company.write(
            {"allowed_document_type_ids": [Command.link(catalog.id)]}
        )
        return catalog

    def _create_sheet(self, *, seller=None):
        seller = seller or self.seller
        ensure_enabled_seller(self.env, seller)
        return self.env["collection.sheet"].create({"seller_id": seller.id})

    def _args(self, **extra):
        payload = {
            "seller_id": self.seller.id,
            "amount": 80.5,
            "voucher_number": "SD-MCP-1",
            "voucher_date": "2026-09-08",
        }
        payload.update(extra)
        return payload

    def _call(self, arguments=None, user=None, tool=TOOL_NAME):
        if arguments is None:
            arguments = self._args()
        env = self.env(user=user) if user else self.env(user=self.internal_user)
        text, _info = self.tool_model._call(tool, arguments, env)
        return json.loads(text)

    def test_discovered_as_method_write_mcp(self):
        """create_seller_deposit is method-discovered write/mcp; no DB row."""
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
            "create_seller_deposit must not have a DB muk_mcp.tool row",
        )

    def test_input_schema_requires_seller_amount_number_date(self):
        """Schema MUST require seller_id, amount, number, date; omit sheet_id."""
        by_name = {
            entry["name"]: entry for entry in self.tool_model.get_tools(registry="mcp")
        }
        schema = by_name[TOOL_NAME]["inputSchema"]
        self.assertEqual(schema["type"], "object")
        self.assertEqual(
            set(schema["required"]),
            {"seller_id", "amount", "voucher_number", "voucher_date"},
        )
        self.assertEqual(
            set(schema["properties"]),
            {
                "seller_id",
                "amount",
                "voucher_number",
                "voucher_date",
                "attachment",
            },
        )
        self.assertEqual(schema["properties"]["seller_id"]["type"], "integer")
        self.assertEqual(schema["properties"]["amount"]["type"], "number")
        self.assertEqual(schema["properties"]["voucher_number"]["type"], "string")
        self.assertEqual(schema["properties"]["voucher_date"]["type"], "string")
        for key in _FORBIDDEN_INPUT_KEYS:
            self.assertNotIn(key, schema["properties"])

    def test_internal_seller_creates_a_deposit_on_submitted(self):
        """Internal caller MUST persist a remittance voucher on the submitted sheet."""
        sheet = self._create_sheet()
        sheet.action_seller_close()
        sentinel = self.env.ref("collection.partner_seller_deposit")
        result = self._call()
        self.assertEqual(set(result), {"sheet", "voucher"})
        self.assertEqual(set(result["sheet"]), _SHEET_KEYS)
        self.assertEqual(result["sheet"]["id"], sheet.id)
        self.assertEqual(result["sheet"]["state"], "submitted")
        voucher_payload = result["voucher"]
        self.assertEqual(set(voucher_payload), _VOUCHER_KEYS)
        voucher = self.env["collection.voucher"].browse(voucher_payload["id"])
        self.assertTrue(voucher.exists())
        self.assertEqual(voucher.sheet_id, sheet)
        self.assertEqual(voucher.document_type, "seller_deposit")
        self.assertEqual(voucher.partner_id, sentinel)
        self.assertTrue(voucher.partner_id)
        self.assertAlmostEqual(voucher.amount, 80.5, places=2)
        self.assertEqual(voucher.voucher_number, "SD-MCP-1")
        self.assertEqual(voucher.voucher_date, date(2026, 9, 8))
        self.assertRegex(voucher.document_id, _DOCUMENT_ID_RE)
        self.assertEqual(voucher.document_id, voucher_payload["document_id"])
        self.assertEqual(voucher.state, "validated_collections")
        self.assertEqual(voucher_payload["state"], "validated_collections")
        self.assertFalse(voucher.allocation_id)
        self.assertNotIn("content_base64", result)

    def test_optional_proof_is_posted_before_collections_validate(self):
        """Optional nested attachment MUST become designated proof."""
        sheet = self._create_sheet()
        sheet.action_seller_close()
        result = self._call(
            self._args(
                attachment={
                    "name": "deposit.png",
                    "mimetype": "image/png",
                    "datas": PNG_B64,
                }
            )
        )
        voucher = self.env["collection.voucher"].browse(result["voucher"]["id"])
        self.assertEqual(voucher.state, "validated_collections")
        self.assertTrue(voucher.message_main_attachment_id)
        self.assertEqual(voucher.message_main_attachment_id.name, "deposit.png")

    def test_open_sheet_is_not_the_deposit_target(self):
        """An open sheet MUST NOT receive a deposit; the tool targets submitted only."""
        sheet = self._create_sheet()
        self.assertEqual(sheet.state, "open")
        before = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError):
            self._call()
        self.assertEqual(sheet.state, "open")
        self.assertEqual(self.env["collection.voucher"].search_count([]), before)

    def test_disabled_type_refused(self):
        """Disallowed seller_deposit MUST raise UserError with no write."""
        catalog = self.env.ref("collection.document_type_seller_deposit")
        self.env.company.write(
            {"allowed_document_type_ids": [Command.unlink(catalog.id)]}
        )
        sheet = self._create_sheet()
        sheet.action_seller_close()
        before = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError) as ctx:
            self._call()
        self.assertIn("not allowed", str(ctx.exception).lower())
        self.assertEqual(self.env["collection.voucher"].search_count([]), before)

    def test_portal_and_public_callers_denied_access_error(self):
        """Portal and public callers MUST receive AccessError."""
        sheet = self._create_sheet()
        sheet.action_seller_close()
        before = self.env["collection.voucher"].search_count([])
        for user in (self.portal_user, self.public_user):
            with self.subTest(login=user.login):
                with self.assertRaises(AccessError):
                    self._call(user=user)
        self.assertEqual(self.env["collection.voucher"].search_count([]), before)

    def test_sheet_id_and_customer_identification_are_rejected(self):
        """Passing sheet_id or customer_identification MUST refuse with no write."""
        sheet = self._create_sheet()
        sheet.action_seller_close()
        before = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError):
            self._call(self._args(sheet_id=sheet.id))
        with self.assertRaises(UserError):
            self._call(self._args(customer_identification="20-11111111-1"))
        self.assertEqual(self.env["collection.voucher"].search_count([]), before)

    def test_allocation_write_still_requires_a_customer(self):
        """create_collection_allocation MUST refuse remittance and omitted ident."""
        self.assertNotIn("seller_deposit", _DOCUMENT_TYPES)
        sheet = self._create_sheet()
        sheet.action_seller_close()
        before = self.env["collection.voucher"].search_count(
            [("document_type", "=", "seller_deposit")]
        )
        env = self.env(user=self.internal_user)
        omitted = {
            "seller_id": self.seller.id,
            "customer_identification": "",
            "request_id": "req-sd-no-customer",
            "payments": [
                {
                    "document_id": "DOC-SD-NO-CUST",
                    "seller_confirmed": {
                        "document_type": "seller_deposit",
                        "amount": 50.0,
                    },
                }
            ],
            "receipts": [
                {
                    "document_kind": "invoice",
                    "values": [{"document_id": "DOC-SD-NO-CUST", "amount": 50.0}],
                    "applications": [],
                }
            ],
        }
        with self.assertRaises(UserError):
            self.tool_model._call(ALLOCATION_TOOL, omitted, env)
        typed = dict(omitted)
        typed["customer_identification"] = "20-11111111-1"
        typed["request_id"] = "req-sd-typed"
        with self.assertRaises(UserError):
            self.tool_model._call(ALLOCATION_TOOL, typed, env)
        self.assertEqual(
            self.env["collection.voucher"].search_count(
                [("document_type", "=", "seller_deposit")]
            ),
            before,
        )

    def test_tool_source_never_sudoes_or_returns_error_dict(self):
        """The deposit tool MUST NOT sudo() or return {\"error\"."""
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
        self.assertIn("collection_audited_state", method_code)
        self.assertIn("sd-", method_code)
