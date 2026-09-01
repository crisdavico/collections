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
from .test_collection_payment import (
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
)

TOOL_NAME = "create_collection_vouchers"
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
        cls.internal_user = create_internal_seller(
            cls.env, "collection_mcp_partner_resolve"
        )
        ensure_enabled_seller(cls.env, cls.internal_user)

    def setUp(self):
        super().setUp()
        install_bound_test_connector(self, self.internal_user)

    def _call(self, arguments, user=None):
        env = mcp_env_with_listable_customers(
            self.env, arguments, user, self.internal_user
        )
        text, _info = self.tool_model._call(TOOL_NAME, arguments, env)
        return json.loads(text)

    def _payload(self, customer, payments):
        stamped = []
        for payment in payments:
            item = dict(payment)
            if "customer_identification" not in item:
                item["customer_identification"] = customer
            stamped.append(item)
        return {"payments": stamped, "seller_id": self.internal_user.id}

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

        def classify(this, existing, document_ids):
            order.append("classify")
            result = orig_classify(this, existing, document_ids)
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

    def test_mixed_customer_batch_stamps_distinct_partners(self):
        """Mixed customers in one call MUST stamp distinct resolved partners."""
        ident_b = "MCP-P4-MIX-B"
        result = self._call(
            self._payload(
                IDENT_ACTIVE,
                [
                    {
                        "customer_identification": IDENT_ACTIVE,
                        "document_id": "MCP-P4-MIX-A",
                        "document_type": "bank_transfer",
                        "amount": 10.0,
                    },
                    {
                        "customer_identification": ident_b,
                        "document_id": "MCP-P4-MIX-B",
                        "document_type": "cash_deposit",
                        "amount": 20.0,
                    },
                ],
            )
        )
        first = self.env["collection.voucher"].browse(result["vouchers"][0]["id"])
        second = self.env["collection.voucher"].browse(result["vouchers"][1]["id"])
        self.assertEqual(first.partner_id.vat, IDENT_ACTIVE)
        self.assertEqual(second.partner_id.vat, ident_b)
        self.assertNotEqual(first.partner_id, second.partner_id)
        self.assertEqual(
            [item["document_id"] for item in result["vouchers"]],
            ["MCP-P4-MIX-A", "MCP-P4-MIX-B"],
        )

    def test_invalid_customer_batch_rolls_back_partners_and_bindings(self):
        """One invalid customer MUST fail the batch with no leftover writes."""
        valid = "MCP-P4-ATOMIC-OK"
        cases = {
            "inactive": IDENT_INACTIVE,
            "other_seller": IDENT_OTHER_SELLER,
        }
        before_vouchers = self.env["collection.voucher"].search_count([])
        for label, invalid in cases.items():
            with self.subTest(label=label):
                ident_ok = f"{valid}-{label}"
                before_partners = self._partners(ident_ok)
                before_bindings = self._bindings(ident_ok)
                with self.assertRaises(UserError) as err:
                    self._call(
                        self._payload(
                            ident_ok,
                            [
                                {
                                    "customer_identification": ident_ok,
                                    "document_id": f"MCP-P4-ATOMIC-OK-{label}",
                                    "document_type": "bank_transfer",
                                    "amount": 10.0,
                                },
                                {
                                    "customer_identification": invalid,
                                    "document_id": f"MCP-P4-ATOMIC-BAD-{label}",
                                    "document_type": "cash_deposit",
                                    "amount": 20.0,
                                },
                            ],
                        )
                    )
                self.assertEqual(str(err.exception), CUSTOMER_UNAVAILABLE)
                self.assertNotIn(DOCUMENT_CONFLICT, str(err.exception))
                self.assertFalse(
                    self.env["collection.voucher"].search(
                        [
                            (
                                "document_id",
                                "in",
                                [
                                    f"MCP-P4-ATOMIC-OK-{label}",
                                    f"MCP-P4-ATOMIC-BAD-{label}",
                                ],
                            )
                        ]
                    )
                )
                self.assertEqual(self._partners(ident_ok), before_partners)
                self.assertEqual(self._bindings(ident_ok), before_bindings)
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )

    def test_exact_replay_skips_adapter_keeps_first_partner(self):
        """Exact replay MUST skip list_customers and keep first-call partner_id."""
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
            second = self._call(
                self._payload(
                    "MCP-P4-REPLAY-CHANGED",
                    [
                        {
                            "document_id": "MCP-P4-REPLAY-A",
                            "document_type": "check",
                            "amount": 99.0,
                        }
                    ],
                )
            )
            self.assertEqual(calls["n"], after_create)
            self.assertEqual(second["vouchers"], first["vouchers"])
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
