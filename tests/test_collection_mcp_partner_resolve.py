# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from unittest.mock import patch

from psycopg2.errors import UniqueViolation

from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from .common_connector import (
    TEST_CUSTOMERS,
    install_bound_test_connector,
    mcp_env_with_listable_customers,
)
from .test_collection_mcp_tool import _nest_seller_confirmed, _on_account_receipts
from .test_collection_payment import (
    create_collection_user,
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
)

TOOL_NAME = "create_collection_allocation"
BINDING = "collection.connector.customer.binding"
CUSTOMER_UNAVAILABLE = "The requested customer is not available."
DOCUMENT_CONFLICT = "Payment document_id conflict could not be resolved."
IDENT_ACTIVE = TEST_CUSTOMERS[0]["identification"]
IDENT_INACTIVE = TEST_CUSTOMERS[1]["identification"]
IDENT_OTHER_SELLER = TEST_CUSTOMERS[2]["identification"]


class TestCollectionMcpPartnerResolve(TransactionCase):
    """MCP create: resolve after classify, batch stamp, replay skip, binding race."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tool_model = cls.env["muk_mcp.tool"]
        # The agent calls as the MCP API user (a Collections User) on behalf of
        # a seller, who stays a plain internal identity.
        cls.internal_user = create_collection_user(
            cls.env, "collection_mcp_partner_resolve"
        )
        cls.seller = create_internal_seller(
            cls.env, "collection_mcp_partner_resolve_seller"
        )
        ensure_enabled_seller(cls.env, cls.seller)

    def setUp(self):
        super().setUp()
        install_bound_test_connector(self, self.seller)

    def _call(self, arguments, user=None):
        arguments = dict(arguments)
        ident = arguments.get("customer_identification")
        echo_args = dict(arguments)
        if ident:
            echoed = []
            for payment in arguments.get("payments") or [{}]:
                item = dict(payment) if isinstance(payment, dict) else {}
                item.setdefault("customer_identification", ident)
                echoed.append(item)
            echo_args = {**arguments, "payments": echoed}
        env = mcp_env_with_listable_customers(
            self.env, echo_args, user, self.internal_user
        )
        text, _info = self.tool_model._call(TOOL_NAME, arguments, env)
        return json.loads(text)

    def _payload(self, customer, payments, **extra):
        cleaned = [_nest_seller_confirmed(payment) for payment in payments]
        payload = {
            "payments": cleaned,
            "seller_id": self.seller.id,
            "customer_identification": customer,
            "request_id": extra.pop("request_id", f"req-{self._testMethodName}"),
            "receipts": extra.pop("receipts", _on_account_receipts(cleaned)),
        }
        extra.pop("invoices", None)
        extra.pop("residual_reason", None)
        payload.update(extra)
        return payload

    def _partners(self, identification):
        return self.env["res.partner"].search([("vat", "=", identification)])

    def _bindings(self, identification):
        return self.env[BINDING].search([("identification", "=", identification)])

    def test_all_new_resolves_after_classify_inside_savepoint(self):
        """All-new create MUST classify first, then resolve inside the savepoint."""
        Mixin = type(self.env["muk_mcp.mixin"])
        Connector = type(self.env["collection.connector"])
        orig_classify = Mixin._collection_classify_visible
        orig_resolve = Connector.resolve_customer_partner
        order = []

        def classify(this, existing, document_ids, *args):
            order.append("classify")
            result = orig_classify(this, existing, document_ids, *args)
            order.append("classified-new" if result is None else "classified-replay")
            return result

        def resolve(this, seller_id, identification):
            order.append("resolve")
            return orig_resolve(this, seller_id, identification)

        with (
            patch.object(Mixin, "_collection_classify_visible", classify),
            patch.object(Connector, "resolve_customer_partner", resolve),
        ):
            result = self._call(
                self._payload(
                    IDENT_ACTIVE,
                    [
                        {
                            "document_id": "MCP-P4-NEW-A",
                            "document_type": "bank_transfer",
                            "amount": 15.0,
                        }
                    ],
                )
            )

        self.assertEqual(order[0], "classify")
        self.assertIn("classified-new", order)
        self.assertIn("resolve", order)
        self.assertLess(order.index("classify"), order.index("resolve"))
        self.assertLess(order.index("classified-new"), order.index("resolve"))
        voucher = self.env["collection.voucher"].browse(result["vouchers"][0]["id"])
        self.assertEqual(voucher.partner_id.vat, IDENT_ACTIVE)
        self.assertNotIn("partner_id", result["vouchers"][0])
        self.assertIn("allocation", result)
        self.assertIn("sheet_id", result)

    def test_invalid_customer_rolls_back_partners_and_bindings(self):
        """Invalid top-level identification MUST fail with no leftover writes."""
        cases = {
            "inactive": IDENT_INACTIVE,
            "other_seller": IDENT_OTHER_SELLER,
        }
        before_vouchers = self.env["collection.voucher"].search_count([])
        for label, invalid in cases.items():
            with self.subTest(label=label):
                before_partners = self._partners(invalid)
                before_bindings = self._bindings(invalid)
                with self.assertRaises(UserError) as err:
                    self._call(
                        self._payload(
                            invalid,
                            [
                                {
                                    "document_id": f"MCP-P4-ATOMIC-BAD-{label}",
                                    "document_type": "bank_transfer",
                                    "amount": 10.0,
                                },
                            ],
                            request_id=f"req-{self._testMethodName}-{label}",
                        )
                    )
                self.assertEqual(str(err.exception), CUSTOMER_UNAVAILABLE)
                self.assertNotIn(DOCUMENT_CONFLICT, str(err.exception))
                self.assertFalse(
                    self.env["collection.voucher"].search(
                        [("document_id", "=", f"MCP-P4-ATOMIC-BAD-{label}")]
                    )
                )
                self.assertEqual(self._partners(invalid), before_partners)
                self.assertEqual(self._bindings(invalid), before_bindings)
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )

    def test_exact_replay_skips_adapter_keeps_first_partner(self):
        """Exact replay MUST skip list_customers and keep first-call partner_id.

        A replay under another customer string is not the same request: it is
        the generic conflict, still without calling the adapter or writing.
        """
        Connector = type(self.env["collection.connector"])
        orig = Connector.list_customers
        calls = {"n": 0}

        def list_customers(this, seller_id):
            calls["n"] += 1
            return orig(this, seller_id)

        payments_first = [
            {
                "document_id": "MCP-P4-REPLAY-A",
                "document_type": "bank_transfer",
                "amount": 10.0,
            }
        ]
        with patch.object(Connector, "list_customers", list_customers):
            first = self._call(self._payload(IDENT_ACTIVE, payments_first))
            self.assertGreater(calls["n"], 0)
            after_create = calls["n"]
            voucher = self.env["collection.voucher"].browse(first["vouchers"][0]["id"])
            first_partner = voucher.partner_id
            self.assertTrue(first_partner)
            second = self._call(self._payload(IDENT_ACTIVE, payments_first))
            self.assertEqual(calls["n"], after_create)
            self.assertEqual(second, first)
            with self.assertRaises(UserError) as err:
                self._call(self._payload("MCP-P4-REPLAY-CHANGED", payments_first))
            self.assertEqual(
                str(err.exception),
                "Allocation request conflict could not be resolved.",
            )
            self.assertEqual(calls["n"], after_create)
            voucher.invalidate_recordset(["partner_id", "amount", "document_type"])
            self.assertEqual(voucher.partner_id, first_partner)
            self.assertEqual(voucher.partner_id.vat, IDENT_ACTIVE)
            self.assertEqual(voucher.amount, 10.0)

    def test_binding_unique_violation_is_not_document_conflict(self):
        """Binding UniqueViolation on MCP create MUST NOT be a document_id conflict."""
        BindingModel = type(self.env[BINDING])

        def create_wrapper(this, vals_list):
            raise UniqueViolation()

        with (
            patch.object(BindingModel, "create", create_wrapper),
            self.assertRaises(UserError) as err,
        ):
            self._call(
                self._payload(
                    IDENT_ACTIVE,
                    [
                        {
                            "document_id": "MCP-P4-UV-BIND",
                            "document_type": "bank_transfer",
                            "amount": 12.0,
                        }
                    ],
                )
            )
        self.assertEqual(str(err.exception), CUSTOMER_UNAVAILABLE)
        self.assertNotIn(DOCUMENT_CONFLICT, str(err.exception))
        self.assertFalse(
            self.env["collection.voucher"].search(
                [("document_id", "=", "MCP-P4-UV-BIND")]
            )
        )
        self.assertFalse(self._bindings(IDENT_ACTIVE))

    def test_binding_unique_violation_with_winner_creates(self):
        """Binding UniqueViolation with a winner MUST stamp that partner."""
        winner = dummy_customer_partner(self.env, customer=IDENT_ACTIVE)
        connector = self.env.company.collection_connector_id
        self.env[BINDING].create(
            {
                "connector_id": connector.id,
                "external_customer_id": "cust-bound-active",
                "identification": IDENT_ACTIVE,
                "partner_id": winner.id,
                "customer_code": "C-BOUND-1",
            }
        )
        BindingModel = type(self.env[BINDING])
        orig_search = BindingModel.search
        searches = {"n": 0}

        def search_wrapper(this, *args, **kwargs):
            searches["n"] += 1
            if searches["n"] == 1:
                return this.browse()
            return orig_search(this, *args, **kwargs)

        def create_wrapper(this, vals_list):
            raise UniqueViolation()

        with (
            patch.object(BindingModel, "search", search_wrapper),
            patch.object(BindingModel, "create", create_wrapper),
        ):
            result = self._call(
                self._payload(
                    IDENT_ACTIVE,
                    [
                        {
                            "document_id": "MCP-P4-UV-WIN",
                            "document_type": "bank_transfer",
                            "amount": 13.0,
                        }
                    ],
                )
            )
        voucher = self.env["collection.voucher"].browse(result["vouchers"][0]["id"])
        self.assertEqual(voucher.partner_id, winner)
        self.assertEqual(voucher.document_id, "MCP-P4-UV-WIN")
