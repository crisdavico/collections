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
    dummy_customer_partner,
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
            "collection_mcp_seller_deposit_internal", "collection.group_collection_user"
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
            "attachment": self._proof(),
        }
        payload.update(extra)
        return payload

    def _proof(self, name="deposit.png"):
        return {"name": name, "mimetype": "image/png", "datas": PNG_B64}

    def _enable_document_review(self):
        self.env.company.write({"document_review_enabled": True})
        return self.env.company

    def _sheet_with_replaceable_cash(self, cash_amount=100.0):
        """Return an open sheet plus the receipt value a deposit can replace."""
        sheet = self._create_sheet()
        partner = dummy_customer_partner(self.env, customer="SD-REVIEW-CUST")
        cash = self.env["collection.voucher"].create(
            {
                "partner_id": partner.id,
                "document_type": "cash",
                "seller_id": sheet.seller_id.id,
                "sheet_id": sheet.id,
                "amount": cash_amount,
            }
        )
        allocation = self.env["collection.allocation"].create(
            {
                "sheet_id": sheet.id,
                "partner_id": partner.id,
                "voucher_ids": [Command.set(cash.ids)],
                "line_ids": [
                    Command.create(
                        {
                            "external_invoice_id": "INV-SD-REVIEW",
                            "invoice_number": "SD-R-1",
                            "issue_date": date(2026, 1, 1),
                            "due_date": date(2026, 1, 31),
                            "invoice_amount": cash_amount,
                            "invoice_balance": cash_amount,
                            "invoice_state": "open",
                            "amount_applied": cash_amount,
                            "document_kind": "invoice",
                        }
                    )
                ],
            }
        )
        receipt = self.env["collection.receipt"].create(
            {"allocation_id": allocation.id, "document_kind": "invoice"}
        )
        cash_value = self.env["collection.receipt.value"].create(
            {
                "receipt_id": receipt.id,
                "voucher_id": cash.id,
                "amount": cash_amount,
            }
        )
        cash.action_validate_seller()
        return sheet, cash, cash_value

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

    def test_input_schema_requires_seller_amount_number_date_and_file(self):
        """Schema MUST require seller_id, amount, number, date, file; omit sheet_id."""
        by_name = {
            entry["name"]: entry for entry in self.tool_model.get_tools(registry="mcp")
        }
        schema = by_name[TOOL_NAME]["inputSchema"]
        self.assertEqual(schema["type"], "object")
        self.assertEqual(
            set(schema["required"]),
            {"seller_id", "amount", "voucher_number", "voucher_date", "attachment"},
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
        self.assertEqual(voucher.partner_id, self.seller.partner_id)
        self.assertTrue(voucher.partner_id)
        self.assertAlmostEqual(voucher.amount, 80.5, places=2)
        self.assertEqual(voucher.voucher_number, "SD-MCP-1")
        self.assertEqual(voucher.voucher_date, date(2026, 9, 8))
        self.assertRegex(voucher.document_id, _DOCUMENT_ID_RE)
        self.assertEqual(voucher.document_id, voucher_payload["document_id"])
        self.assertEqual(voucher.state, "validated_seller")
        self.assertEqual(voucher_payload["state"], "validated_seller")
        self.assertFalse(voucher.reviewed_by)
        self.assertFalse(voucher.reviewed_at)
        self.assertFalse(voucher.allocation_id)
        self.assertNotIn("content_base64", result)

    def test_deposit_without_proof_is_refused_no_writes(self):
        """A deposit MUST carry the file of its deposit slip."""
        sheet = self._create_sheet()
        sheet.action_seller_close()
        before = self.env["collection.voucher"].search_count([])
        args = self._args()
        args.pop("attachment", None)
        with self.assertRaises(UserError) as ctx:
            self._call(args)
        self.assertIn("deposit slip", str(ctx.exception))
        self.assertEqual(self.env["collection.voucher"].search_count([]), before)

    def test_optional_proof_becomes_designated_proof_awaiting_review(self):
        """Optional nested attachment MUST become reviewable designated proof."""
        sheet = self._create_sheet()
        sheet.action_seller_close()
        result = self._call(self._args(attachment=self._proof()))
        voucher = self.env["collection.voucher"].browse(result["voucher"]["id"])
        self.assertEqual(voucher.state, "validated_seller")
        self.assertTrue(voucher.message_main_attachment_id)
        self.assertEqual(voucher.message_main_attachment_id.name, "deposit.png")

    def test_deposit_with_proof_enters_the_review_queue(self):
        """The deposit slip MUST be listed by get_review_queue for its sheet."""
        self._enable_document_review()
        sheet = self._create_sheet()
        sheet.action_seller_close()
        result = self._call(self._args(attachment=self._proof()))
        voucher = self.env["collection.voucher"].browse(result["voucher"]["id"])
        queue = self.env["collection.voucher"].get_review_queue(sheet_id=sheet.id)
        self.assertEqual([row["voucher_id"] for row in queue], [voucher.id])
        self.assertEqual(voucher.state, "validated_seller")

    def test_review_approve_promotes_the_deposit_and_replaces_cash(self):
        """Document Review Approve MUST be the promote path and MUST replace cash."""
        self._enable_document_review()
        sheet, cash, cash_value = self._sheet_with_replaceable_cash()
        sheet.action_seller_close(commission_withheld=0.0)
        result = self._call(self._args(amount=40.0, attachment=self._proof()))
        deposit = self.env["collection.voucher"].browse(result["voucher"]["id"])
        deposit.action_review_approve(sheet_id=sheet.id)
        self.assertEqual(deposit.state, "validated_collections")
        self.assertEqual(deposit.reviewed_by, self.env.user)
        self.assertTrue(deposit.reviewed_at)
        self.assertAlmostEqual(deposit.replacing_amount, 40.0, places=2)
        self.assertAlmostEqual(cash.replaced_amount, 40.0, places=2)
        self.assertAlmostEqual(cash_value.amount, 60.0, places=2)
        deposit_value = sheet.allocation_ids.receipt_ids.value_ids.filtered(
            lambda value: value.voucher_id == deposit
        )
        self.assertAlmostEqual(deposit_value.amount, 40.0, places=2)

    def test_unreviewed_deposit_still_blocks_confirm(self):
        """A validated_seller deposit MUST keep Confirm blocked."""
        sheet = self._create_sheet()
        sheet.action_seller_close()
        self._call()
        with self.assertRaises(UserError):
            sheet.action_confirm()
        self.assertEqual(sheet.state, "submitted")

    def test_open_sheet_receives_the_deposit_before_close(self):
        """The seller loads a deposit slip on the open sheet before closing it."""
        sheet = self._create_sheet()
        self.assertEqual(sheet.state, "open")
        result = self._call()
        self.assertEqual(result["sheet"]["id"], sheet.id)
        self.assertEqual(result["sheet"]["state"], "open")
        voucher = self.env["collection.voucher"].browse(result["voucher"]["id"])
        self.assertEqual(voucher.sheet_id, sheet)
        self.assertEqual(voucher.document_type, "seller_deposit")
        self.assertEqual(voucher.state, "validated_seller")
        self.assertEqual(sheet.state, "open")
        self.assertAlmostEqual(sheet.cash_banked, 80.5, places=2)

    def test_open_sheet_wins_over_a_submitted_one(self):
        """With an open and a submitted sheet, the deposit goes to the open one."""
        submitted = self._create_sheet()
        submitted.action_seller_close()
        current = self._create_sheet()
        result = self._call()
        self.assertEqual(result["sheet"]["id"], current.id)
        self.assertAlmostEqual(current.cash_banked, 80.5, places=2)
        self.assertFalse(submitted.cash_banked)

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
        self.assertIn("_open_sheets_for_seller", method_code)
        self.assertIn("_submitted_sheets_for_seller", method_code)
        self.assertNotIn("validated_collections", method_code)
        self.assertIn("sd-", method_code)
