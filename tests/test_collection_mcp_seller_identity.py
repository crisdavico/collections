# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import importlib
import json
from types import SimpleNamespace
from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests import TransactionCase

from .common_connector import (
    install_bound_test_connector,
    install_test_connector_type,
    mcp_env_with_listable_customers,
)
from .test_collection_acl import TestCollectionAcl
from .test_collection_payment import (
    create_internal_seller,
    ensure_enabled_seller,
    voucher_file,
    with_voucher_files,
)

HEADER_PARAM = "collection.mcp_trusted_seller_header"
HEADER_NAME = "X-Nebula-Sender"
IDENTITY_MODULE = "odoo.addons.collection.tools.seller_identity"
IDENTITY_ERROR = "The seller identity could not be verified."
COLLECTION_USER_ERROR = "Only Collections Users can use the collection agent tools."
SELLER_PHONE = "+54 9 11 4444-0101"
SELLER_HEADER = "5491144440101"
OTHER_PHONE = "+54 9 11 4444-0202"
OTHER_HEADER = "5491144440202"
UNKNOWN_HEADER = "5491144449999"
IDENT = "20-11111111-1"


def _tool_arguments(seller_id):
    """Smallest valid arguments per seller-acting tool, so identity is reached."""
    seller = {} if seller_id is None else {"seller_id": seller_id}
    payment = {
        "document_id": "IDENTITY-DOC-1",
        "seller_confirmed": {"document_type": "bank_transfer", "amount": 10.0},
    }
    return {
        "list_collection_customers": dict(seller),
        "customer_debt": {**seller, "customer_identification": IDENT},
        "get_collection_allocation": {**seller, "customer_identification": IDENT},
        "get_collection_sheet_pdf": dict(seller),
        "close_collection_sheet": dict(seller),
        "declare_collection_cash": {**seller, "commission_withheld": 1.0},
        "create_seller_deposit": {
            **seller,
            "amount": 10.0,
            "voucher_number": "SD-IDENTITY-1",
            "voucher_date": "2026-09-01",
            "attachment": voucher_file("slip.png"),
        },
        "create_collection_allocation": {
            **seller,
            "customer_identification": IDENT,
            "request_id": "req-identity",
            "payments": [payment],
            "receipts": [
                {
                    "document_kind": "invoice",
                    "values": [{"document_id": "IDENTITY-DOC-1", "amount": 10.0}],
                    "applications": [],
                }
            ],
        },
    }


class TestCollectionMcpSellerIdentity(TransactionCase):
    """MCP seller identity from a trusted gateway header (D3), off by default."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        install_test_connector_type(cls)
        cls.tool_model = cls.env["muk_mcp.tool"]
        cls.caller = cls._create_user(
            "collection_identity_caller", "collection.group_collection_user"
        )
        cls.plain_user = cls._create_user(
            "collection_identity_plain", "base.group_user"
        )

    @classmethod
    def _partner_has_autopost_bills_column(cls):
        return TestCollectionAcl._partner_has_autopost_bills_column.__func__(cls)

    @classmethod
    def _create_user(cls, login, group_xmlid):
        return TestCollectionAcl._create_user.__func__(cls, login, group_xmlid)

    def setUp(self):
        super().setUp()
        self.seller = create_internal_seller(self.env, "collection_identity_seller")
        self.seller.partner_id.phone = SELLER_PHONE
        self.other = create_internal_seller(self.env, "collection_identity_other")
        self.other.partner_id.phone = OTHER_PHONE
        install_bound_test_connector(self, self.seller)
        ensure_enabled_seller(self.env, self.other)

    def _enable_header(self, name=HEADER_NAME):
        self.env["ir.config_parameter"].set_param(HEADER_PARAM, name)

    def _call(self, tool, arguments, headers=None, user=None):
        """Run one tool in-process with ``headers`` as the request headers."""
        headers = dict(headers or {})
        env = mcp_env_with_listable_customers(
            self.env, arguments, user or self.caller, self.caller
        )
        with patch(
            f"{IDENTITY_MODULE}.request_header",
            side_effect=lambda name: headers.get(name, ""),
        ):
            text, _info = self.tool_model._call(
                tool, with_voucher_files(arguments), env
            )
        return json.loads(text)

    def _counts(self):
        return {
            model: self.env[model].search_count([])
            for model in (
                "collection.voucher",
                "collection.sheet",
                "collection.allocation",
            )
        }

    def _assert_identity_refused(self, tool, arguments, headers):
        before = self._counts()
        with self.assertRaises(AccessError) as ctx:
            self._call(tool, arguments, headers)
        self.assertEqual(str(ctx.exception), IDENTITY_ERROR)
        self.assertEqual(self._counts(), before)

    def test_setting_is_an_admin_only_config_parameter(self):
        """The header name lives in ir.config_parameter, admins only, off by default."""
        field = self.env["res.config.settings"]._fields.get(
            "collection_mcp_trusted_seller_header"
        )
        self.assertIsNotNone(field, "the trusted header setting must exist")
        self.assertEqual(field.config_parameter, HEADER_PARAM)
        self.assertEqual(field.groups, "base.group_system")
        self.assertFalse(self.env["ir.config_parameter"].get_param(HEADER_PARAM))

    def test_without_the_setting_the_header_is_ignored(self):
        """Feature off: the tool acts for seller_id whatever the request carries."""
        result = self._call(
            "list_collection_customers",
            {"seller_id": self.seller.id},
            {HEADER_NAME: OTHER_HEADER},
        )
        self.assertEqual(
            [row["external_customer_id"] for row in result["customers"]],
            ["cust-bound-active"],
        )

    def test_header_seller_is_used_when_seller_id_is_omitted(self):
        """With the setting on, the tool needs no seller_id: the header names it."""
        self._enable_header()
        result = self._call(
            "list_collection_customers", {}, {HEADER_NAME: SELLER_HEADER}
        )
        self.assertEqual(
            [row["external_customer_id"] for row in result["customers"]],
            ["cust-bound-active"],
        )

    def test_matching_seller_id_is_accepted(self):
        """A seller_id naming the header's seller passes; phone format is free."""
        self._enable_header()
        result = self._call(
            "list_collection_customers",
            {"seller_id": self.seller.id},
            {HEADER_NAME: SELLER_PHONE},
        )
        self.assertEqual(len(result["customers"]), 1)

    def test_every_seller_tool_refuses_another_sellers_id(self):
        """A seller_id that differs from the header's seller is refused, no writes."""
        self._enable_header()
        for tool, arguments in _tool_arguments(self.other.id).items():
            with self.subTest(tool=tool):
                self._assert_identity_refused(
                    tool, arguments, {HEADER_NAME: SELLER_HEADER}
                )

    def test_every_seller_tool_fails_closed_without_a_verified_header(self):
        """Missing, empty, unknown or misnamed header: one generic refusal."""
        self._enable_header()
        for label, headers in (
            ("missing", {}),
            ("empty", {HEADER_NAME: "   "}),
            ("unknown", {HEADER_NAME: UNKNOWN_HEADER}),
            ("other header", {"X-Other-Sender": SELLER_HEADER}),
        ):
            for tool, arguments in _tool_arguments(self.seller.id).items():
                with self.subTest(case=label, tool=tool):
                    self._assert_identity_refused(tool, arguments, headers)

    def test_header_of_a_seller_that_is_not_enabled_fails_closed(self):
        """A known phone of a seller off the enabled list reads like an unknown one."""
        self._enable_header()
        self.env.company.write({"enabled_seller_ids": [Command.unlink(self.other.id)]})
        for tool, arguments in _tool_arguments(None).items():
            with self.subTest(tool=tool):
                self._assert_identity_refused(
                    tool, arguments, {HEADER_NAME: OTHER_HEADER}
                )

    def test_get_seller_id_answers_with_the_header_seller(self):
        """get_seller_id returns the header's seller; another mobile is refused."""
        self._enable_header()
        headers = {HEADER_NAME: SELLER_HEADER}
        self.assertEqual(
            self._call("get_seller_id", {}, headers), {"seller_id": self.seller.id}
        )
        self.assertEqual(
            self._call("get_seller_id", {"mobile": "11 4444-0101"}, headers),
            {"seller_id": self.seller.id},
        )
        for label, arguments, case_headers in (
            ("other mobile", {"mobile": OTHER_HEADER}, headers),
            ("no header", {"mobile": SELLER_HEADER}, {}),
            ("unknown header", {}, {HEADER_NAME: UNKNOWN_HEADER}),
        ):
            with self.subTest(case=label):
                self._assert_identity_refused("get_seller_id", arguments, case_headers)

    def test_allocation_is_written_for_the_header_seller(self):
        """The write tool persists vouchers for the header's seller, not an argument."""
        self._enable_header()
        arguments = _tool_arguments(None)["create_collection_allocation"]
        result = self._call(
            "create_collection_allocation", arguments, {HEADER_NAME: SELLER_HEADER}
        )
        vouchers = self.env["collection.voucher"].browse(
            [row["id"] for row in result["vouchers"]]
        )
        self.assertEqual(vouchers.seller_id, self.seller)
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        self.assertEqual(allocation.sheet_id.seller_id, self.seller)

    def test_tools_require_the_collections_user_group(self):
        """A plain internal user is refused by every tool before any lookup."""
        tools = {
            **_tool_arguments(self.seller.id),
            "get_seller_id": {"mobile": SELLER_HEADER},
        }
        for tool, arguments in tools.items():
            with self.subTest(tool=tool):
                with self.assertRaises(AccessError) as ctx:
                    self._call(tool, arguments, user=self.plain_user)
                self.assertEqual(str(ctx.exception), COLLECTION_USER_ERROR)

    def test_request_header_reads_the_current_http_request(self):
        """The one helper reads the live request, and nothing outside a request."""
        identity = importlib.import_module(IDENTITY_MODULE)
        self.assertEqual(identity.request_header(HEADER_NAME), "")
        fake = SimpleNamespace(
            httprequest=SimpleNamespace(headers={HEADER_NAME: f"  {SELLER_HEADER} "})
        )
        with patch(f"{IDENTITY_MODULE}.request", fake):
            self.assertEqual(identity.request_header(HEADER_NAME), SELLER_HEADER)
            self.assertEqual(identity.request_header("X-Missing"), "")
