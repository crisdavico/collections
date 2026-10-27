# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import inspect
import json

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase

from odoo.addons.collection.tools.seller_identity import TRUSTED_SELLER_HEADER_PARAM
from odoo.addons.muk_mcp.core.tool import get_tool_index

from .test_collection_acl import TestCollectionAcl
from .test_collection_mcp_sheet_close import TestCollectionMcpSheetClose
from .test_collection_payment import (
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
)

TOOL_NAME = "get_collection_summary"
_FORBIDDEN_INPUT_KEYS = ("sheet_id", "model", "domain", "fields", "context", "order")


def _collected(**amounts):
    collected = dict.fromkeys(
        (
            "cash",
            "cash_deposits",
            "checks",
            "transfers",
            "echecks",
            "retentions",
            "total",
        ),
        0.0,
    )
    collected.update(amounts)
    return collected


class TestCollectionMcpSheetSummary(TransactionCase):
    """MCP get_collection_summary: the open sheet's Planilla totals before close."""

    def setUp(self):
        super().setUp()
        # seller_id names the seller only while the trusted header is off.
        self.env["ir.config_parameter"].set_param(TRUSTED_SELLER_HEADER_PARAM, "")
        self.tool_model = self.env["muk_mcp.tool"]
        self.internal_user = self._create_user(
            "collection_mcp_sheet_summary_internal", "collection.group_collection_user"
        )
        self.portal_user = self._create_user(
            "collection_mcp_sheet_summary_portal", "base.group_portal"
        )
        self.public_user = self._create_user(
            "collection_mcp_sheet_summary_public", "base.group_public"
        )
        self.seller = create_internal_seller(
            self.env, "collection_mcp_sheet_summary_ana"
        )
        ensure_enabled_seller(self.env, self.seller)

    def _partner_has_autopost_bills_column(self):
        return TestCollectionAcl._partner_has_autopost_bills_column.__func__(self)

    def _create_user(self, login, group_xmlid):
        return TestCollectionAcl._create_user.__func__(self, login, group_xmlid)

    def _create_sheet(self, *, seller=None):
        return TestCollectionMcpSheetClose._create_sheet(self, seller=seller)

    def _create_cash_sheet(self, cash=40.0, applied=50.0, percent=10.0):
        return TestCollectionMcpSheetClose._create_cash_sheet(
            self, cash=cash, applied=applied, percent=percent
        )

    def _call(self, user=None):
        env = self.env(user=user or self.internal_user)
        text, _info = self.tool_model._call(
            TOOL_NAME, {"seller_id": self.seller.id}, env
        )
        return json.loads(text)

    def test_discovered_as_method_read_mcp(self):
        """get_collection_summary is method-discovered read/mcp; no DB row."""
        by_name = {
            entry["name"]: entry for entry in self.tool_model.get_tools(registry="mcp")
        }
        self.assertIn(TOOL_NAME, by_name)
        entry = get_tool_index(self.env, registry="mcp")[TOOL_NAME]
        self.assertEqual(entry["category"], "read")
        self.assertEqual(entry["registry"], "mcp")
        self.assertEqual(entry["kind"], "method")
        self.assertFalse(self.env["muk_mcp.tool"].search([("name", "=", TOOL_NAME)]))

    def test_input_schema_takes_only_the_seller(self):
        """Schema MUST require and offer seller_id only."""
        by_name = {
            entry["name"]: entry for entry in self.tool_model.get_tools(registry="mcp")
        }
        schema = by_name[TOOL_NAME]["inputSchema"]
        self.assertEqual(set(schema["required"]), {"seller_id"})
        self.assertEqual(set(schema["properties"]), {"seller_id"})
        for key in _FORBIDDEN_INPUT_KEYS:
            self.assertNotIn(key, schema["properties"])

    def test_portal_and_public_callers_denied_access_error(self):
        """Portal and public callers MUST receive AccessError."""
        self._create_cash_sheet()
        for user in (self.portal_user, self.public_user):
            with self.subTest(login=user.login), self.assertRaises(AccessError):
                self._call(user=user)

    def test_no_open_sheet_returns_sheet_null(self):
        """No open sheet, or only a submitted one, MUST return {sheet: null}."""
        self.assertEqual(self._call(), {"sheet": None})
        self._create_sheet().action_seller_close()
        self.assertEqual(self._call(), {"sheet": None})

    def test_open_sheet_with_cash_returns_cash_and_commission(self):
        """The open sheet's cash collected and commission MUST come back unchanged."""
        sheet = self._create_cash_sheet(cash=40.0, applied=50.0, percent=10.0)
        result = self._call()
        self.assertEqual(set(result), {"sheet", "collected", "cash", "commission"})
        self.assertEqual(result["collected"], _collected(cash=40.0, total=40.0))
        self.assertEqual(result["sheet"]["id"], sheet.id)
        self.assertEqual(result["sheet"]["state"], "open")
        self.assertEqual(result["cash"], {"collected": 40.0, "banked": 0.0})
        self.assertEqual(result["commission"], {"percent": 10.0, "amount": 5.0})
        self.assertEqual(sheet.state, "open")
        self.assertFalse(sheet.cash_declared_at)
        self.assertFalse(sheet.commission_withheld)

    def test_open_sheet_without_cash_returns_zero_collected(self):
        """An open sheet without cash vouchers MUST return zero cash collected."""
        self._create_sheet()
        result = self._call()
        self.assertEqual(result["collected"], _collected())
        self.assertEqual(result["cash"], {"collected": 0.0, "banked": 0.0})
        self.assertEqual(result["commission"], {"percent": 0.0, "amount": 0.0})

    def test_seller_deposit_is_returned_as_banked(self):
        """A seller deposit on the open sheet MUST come back as cash.banked."""
        sheet = self._create_cash_sheet(cash=40.0)
        self.env["collection.voucher"].create(
            {
                "document_type": "seller_deposit",
                "document_id": f"sd-{self._testMethodName}",
                "seller_id": self.seller.id,
                "sheet_id": sheet.id,
                "amount": 30.0,
                "voucher_number": "SD-CASH-1",
                "state": "validated_seller",
            }
        )
        result = self._call()
        self.assertEqual(result["cash"], {"collected": 40.0, "banked": 30.0})
        self.assertEqual(result["collected"], _collected(cash=40.0, total=40.0))

    def test_collected_is_split_by_voucher_type(self):
        """collected MUST carry each voucher type and the Planilla total."""
        sheet = self._create_cash_sheet(cash=40.0)
        partner = dummy_customer_partner(self.env, customer="MCP-SUMMARY-TYPES")
        for document_type, amount, extra in (
            ("cash_deposit", 10.0, {}),
            ("check", 25.0, {"check_number": "CHK-SUMMARY-1"}),
            ("bank_transfer", 100.0, {}),
            ("echeck", 7.0, {"check_number": "ECHK-SUMMARY-1"}),
            ("retention_certificate", 3.0, {}),
        ):
            self.env["collection.voucher"].create(
                {
                    "partner_id": partner.id,
                    "document_type": document_type,
                    "document_id": f"{document_type}-{self._testMethodName}",
                    "seller_id": self.seller.id,
                    "sheet_id": sheet.id,
                    "company_id": sheet.company_id.id,
                    "amount": amount,
                    **extra,
                }
            )
        result = self._call()
        self.assertEqual(
            result["collected"],
            _collected(
                cash=40.0,
                cash_deposits=10.0,
                checks=25.0,
                transfers=100.0,
                echecks=7.0,
                retentions=3.0,
                total=185.0,
            ),
        )
        self.assertEqual(result["sheet"]["voucher_count"], 6)

    def test_tool_source_never_sudoes_or_returns_error_dict(self):
        """The tool MUST NOT sudo() or return {\"error\"."""
        mixin = self.env["muk_mcp.mixin"]
        method = getattr(type(mixin), TOOL_NAME, None)
        self.assertTrue(callable(method), f"muk_mcp.mixin must expose {TOOL_NAME}")
        file_source = inspect.getsource(inspect.getmodule(method))
        self.assertNotIn(".sudo(", file_source)
        self.assertNotIn('{"error"', file_source)
