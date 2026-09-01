# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import inspect
import json
from datetime import date
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.fields import Command
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.muk_mcp.core.tool import get_tool_index

from .common_connector import (
    install_bound_test_connector,
    mcp_env_with_listable_customers,
)
from .test_collection_payment import (
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
)

TOOL_NAME = "create_collection_vouchers"
OLD_TOOL_NAME = "create_collection_voucher"

# Minimal valid payloads (base64) for MCP attachment triangulation.
PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQ"
    "DJ/pLvAAAAAElFTkSuQmCC"
)
PDF_B64 = "JVBERi0xLjEKMSAwIG9iajw8Pj5lbmRvYmoKdHJhaWxlcjw8Pj4KJSVFT0YK"
TXT_B64 = "aGVsbG8gd29ybGQ="
INVALID_B64 = "!!!not-base64!!!"


class TestCollectionMcpTool(TransactionCase):
    """RED/GREEN: create_collection_vouchers MCP discover, create, replay, ACL."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tool_model = cls.env["muk_mcp.tool"]
        cls.internal_user = cls._create_user(
            "collection_mcp_internal", "base.group_user"
        )
        cls.portal_user = cls._create_user("collection_mcp_portal", "base.group_portal")
        ensure_enabled_seller(cls.env, cls.internal_user)

    def setUp(self):
        super().setUp()
        install_bound_test_connector(self, self.internal_user)

    @classmethod
    def _partner_has_autopost_bills_column(cls):
        cls.env.cr.execute(
            """
            SELECT 1
              FROM information_schema.columns
             WHERE table_name = 'res_partner'
               AND column_name = 'autopost_bills'
            """
        )
        return bool(cls.env.cr.fetchone())

    @classmethod
    def _create_user(cls, login, group_xmlid):
        """Create a user; satisfy account.autopost_bills when the DB column exists."""
        partner_vals = {
            "name": login,
            "email": f"{login}@example.com",
        }
        Partner = cls.env["res.partner"].with_context(
            tracking_disable=True,
            mail_create_nolog=True,
            mail_notrack=True,
            mail_create_nosubscribe=True,
        )
        if "autopost_bills" in Partner._fields:
            partner_vals["autopost_bills"] = "ask"
            partner = Partner.create(partner_vals)
        elif cls._partner_has_autopost_bills_column():
            cls.env.cr.execute(
                """
                INSERT INTO res_partner (
                    name, email, active, complete_name, type, autopost_bills,
                    create_uid, write_uid, create_date, write_date
                )
                VALUES (
                    %s, %s, true, %s, 'contact', 'ask',
                    1, 1,
                    (now() AT TIME ZONE 'UTC'),
                    (now() AT TIME ZONE 'UTC')
                )
                RETURNING id
                """,
                (login, partner_vals["email"], login),
            )
            partner = Partner.browse(cls.env.cr.fetchone()[0])
        else:
            partner = Partner.create(partner_vals)

        return (
            cls.env["res.users"]
            .with_context(no_reset_password=True, tracking_disable=True)
            .create(
                {
                    "name": login,
                    "login": login,
                    "email": partner_vals["email"],
                    "partner_id": partner.id,
                    "group_ids": [(6, 0, [cls.env.ref(group_xmlid).id])],
                }
            )
        )

    def _create_legacy_null_seller_voucher(self, **vals):
        """Create via ORM then SQL-null seller/sheet (historical row)."""
        partner = dummy_customer_partner(self.env, extra=vals, default="MCP-LEGACY")
        vals.setdefault("partner_id", partner.id)
        vals.setdefault(
            "seller_id",
            ensure_enabled_seller(self.env, self.internal_user).id,
        )
        voucher = self.env["collection.voucher"].create(vals)
        self.env.cr.execute(
            """
            UPDATE collection_voucher
               SET seller_id = NULL, sheet_id = NULL
             WHERE id = %s
            """,
            (voucher.id,),
        )
        voucher.invalidate_recordset(["seller_id", "sheet_id"])
        return voucher

    def _call(self, arguments, user=None):
        """Run the N-voucher MCP tool in-process and return decoded JSON."""
        env = mcp_env_with_listable_customers(
            self.env, arguments, user, self.internal_user
        )
        text, _info = self.tool_model._call(TOOL_NAME, arguments, env)
        return json.loads(text)

    def _payload(self, customer="MCP-CUST-NEW", payments=None, *, seller_id="default"):
        if payments is None:
            payments = [
                {
                    "document_id": "MCP-DOC-A",
                    "document_type": "bank_transfer",
                    "amount": 100.0,
                    "from_account": "FROM-1",
                    "to_account": "TO-1",
                },
                {
                    "document_id": "MCP-DOC-B",
                    "document_type": "check",
                    "amount": 50.0,
                    "check_number": "CHK-1",
                    "check_type": "common",
                },
            ]
        stamped_payments = []
        for payment in payments:
            item = dict(payment)
            if "customer_identification" not in item:
                item["customer_identification"] = customer
            stamped_payments.append(item)
        payload = {
            "payments": stamped_payments,
        }
        if seller_id == "default":
            payload["seller_id"] = self.internal_user.id
        elif seller_id is not None:
            payload["seller_id"] = seller_id
        return payload

    def _assert_voucher_list(self, result, document_ids, state="pending"):
        """Assert payment-order list identity for create and exact replay."""
        self.assertIn("vouchers", result)
        self.assertEqual(len(result["vouchers"]), len(document_ids))
        self.assertEqual(
            [item["document_id"] for item in result["vouchers"]],
            list(document_ids),
        )
        for item in result["vouchers"]:
            self.assertIsInstance(item["id"], int)
            self.assertTrue(item["name"])
            self.assertEqual(item["state"], state)
            self.assertIn("document_id", item)

    # --- 4.1 Discover + schema + all-new create ---

    def test_tool_discovered_with_write_registry_and_schema(self):
        """Plural tool is method-discovered write/mcp; no DB row; no received_date."""
        by_name = {
            entry["name"]: entry for entry in self.tool_model.get_tools(registry="mcp")
        }
        self.assertIn(
            TOOL_NAME,
            by_name,
            f"{TOOL_NAME} must appear in MCP registry tools",
        )
        self.assertNotIn(
            OLD_TOOL_NAME,
            by_name,
            "singular create_collection_voucher must not remain registered",
        )
        self.assertNotIn(
            "list_collection_sellers",
            by_name,
            "list_collection_sellers must not be registered as an MCP tool",
        )
        self.assertFalse(
            self.env["muk_mcp.tool"].search([("name", "=", "list_collection_sellers")]),
            "list_collection_sellers must not have a DB muk_mcp.tool row",
        )
        entry = get_tool_index(self.env, registry="mcp")[TOOL_NAME]
        self.assertEqual(entry["category"], "write")
        self.assertEqual(entry["kind"], "method")
        self.assertNotEqual(entry.get("kind"), "db")

        self.assertFalse(
            self.env["muk_mcp.tool"].search([("name", "=", TOOL_NAME)]),
            "create_collection_vouchers must not have a DB muk_mcp.tool row",
        )
        self.assertFalse(
            self.env["muk_mcp.tool"].search([("name", "=", OLD_TOOL_NAME)]),
            "singular tool must not have a DB muk_mcp.tool row either",
        )

        schema = by_name[TOOL_NAME]["inputSchema"]
        self.assertEqual(schema["type"], "object")
        self.assertEqual(
            set(schema["required"]),
            {"payments", "seller_id"},
        )
        self.assertNotIn(
            "customer_identification",
            schema["required"],
            "top-level customer_identification must not be required",
        )
        self.assertNotIn(
            "customer_identification",
            schema.get("properties", {}),
            "top-level schema must not expose customer_identification",
        )
        self.assertIn("payments", schema["required"])
        self.assertIn(
            "seller_id",
            schema["required"],
            "MCP schema must require top-level seller_id",
        )
        self.assertIn("seller_id", schema.get("properties", {}))
        self.assertNotIn(
            "received_date",
            schema.get("properties", {}),
            "MCP schema must not accept received_date",
        )
        payment_schema = schema["properties"]["payments"]["items"]
        self.assertIn("document_id", payment_schema["required"])
        self.assertIn("document_type", payment_schema["required"])
        self.assertIn(
            "customer_identification",
            payment_schema["required"],
            "each payment must require customer_identification",
        )
        self.assertIn(
            "customer_identification",
            payment_schema.get("properties", {}),
        )
        self.assertNotIn(
            "received_date",
            payment_schema.get("properties", {}),
        )

    def test_create_collection_vouchers_does_not_use_sudo(self):
        """Authenticated caller env only — method source must not call sudo()."""
        mixin = self.env["muk_mcp.mixin"]
        method = getattr(type(mixin), TOOL_NAME, None)
        self.assertTrue(
            callable(method),
            f"muk_mcp.mixin must expose {TOOL_NAME}",
        )
        source = inspect.getsource(method)
        code_lines = [
            line for line in source.splitlines() if not line.lstrip().startswith("#")
        ]
        code = "\n".join(code_lines)
        self.assertNotIn(".sudo(", code)
        self.assertNotIn("sudo()", code)

    def test_all_new_create_returns_vouchers_in_payment_order(self):
        """All-new document_ids create one voucher per payment in payment order."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        result = self._call(self._payload())

        self._assert_voucher_list(result, ["MCP-DOC-A", "MCP-DOC-B"])
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers + 2,
        )

        first = self.env["collection.voucher"].browse(result["vouchers"][0]["id"])
        second = self.env["collection.voucher"].browse(result["vouchers"][1]["id"])
        self.assertTrue(first.exists())
        self.assertTrue(second.exists())
        self.assertEqual(first.partner_id.vat, "MCP-CUST-NEW")
        self.assertEqual(second.partner_id.vat, "MCP-CUST-NEW")
        self.assertEqual(first.state, "pending")
        self.assertEqual(second.state, "pending")
        self.assertEqual(first.document_id, "MCP-DOC-A")
        self.assertEqual(second.document_id, "MCP-DOC-B")
        self.assertEqual(first.document_type, "bank_transfer")
        self.assertEqual(second.document_type, "check")
        self.assertEqual(first.currency_id, self.env.company.currency_id)
        self.assertEqual(first.create_uid, self.internal_user)
        self.assertEqual(second.create_uid, self.internal_user)
        self.assertEqual(result["vouchers"][0]["name"], first.name)
        self.assertEqual(result["vouchers"][1]["name"], second.name)

    def test_create_rejects_missing_document_id(self):
        """Triangulation: MCP payments without document_id must be rejected."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError) as err:
            self._call(
                self._payload(
                    customer="MCP-CUST-NODOC",
                    payments=[
                        {
                            "document_type": "cash_deposit",
                            "amount": 10.0,
                        }
                    ],
                ),
            )
        self.assertIn("document_id", str(err.exception).lower())
        self.assertNotIn("tool not found", str(err.exception).lower())
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )

    def test_create_rejects_empty_document_id(self):
        """Triangulation: empty-string document_id must be rejected with no writes."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError) as err:
            self._call(
                self._payload(
                    customer="MCP-CUST-EMPTYDOC",
                    payments=[
                        {
                            "document_id": "  ",
                            "document_type": "unsupported",
                        }
                    ],
                ),
            )
        self.assertIn("document_id", str(err.exception).lower())
        self.assertNotIn("tool not found", str(err.exception).lower())
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )

    def test_create_rejects_empty_payments(self):
        """Triangulation: empty payments list must be rejected."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError) as err:
            self._call(
                {
                    "seller_id": self.internal_user.id,
                    "payments": [],
                },
            )
        message = str(err.exception).lower()
        self.assertTrue(
            "payment" in message or "payments" in message,
            f"Expected payments validation message, got: {err.exception}",
        )
        self.assertNotIn("tool not found", message)
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )

    def test_create_rejects_top_level_customer_without_per_payment_customer(self):
        """Old shape: top-level customer and payments missing it MUST reject."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError):
            self._call(
                {
                    "customer_identification": "MCP-CUST-OLD-SHAPE",
                    "seller_id": self.internal_user.id,
                    "payments": [
                        {
                            "document_id": "MCP-DOC-OLD-SHAPE",
                            "document_type": "bank_transfer",
                            "amount": 1.0,
                        }
                    ],
                },
            )
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertFalse(
            self.env["collection.voucher"].search(
                [("document_id", "=", "MCP-DOC-OLD-SHAPE")]
            ),
        )

    def test_create_rejects_missing_per_payment_customer(self):
        """Payment without customer_identification MUST UserError with no writes."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        payload = self._payload(
            customer="MCP-CUST-MISSING",
            payments=[
                {
                    "document_id": "MCP-DOC-MISSING-CUST",
                    "document_type": "bank_transfer",
                    "amount": 1.0,
                }
            ],
        )
        del payload["payments"][0]["customer_identification"]
        with self.assertRaises(UserError) as err:
            self._call(payload)
        self.assertIn("customer_identification", str(err.exception).lower())
        self.assertNotIn("tool not found", str(err.exception).lower())
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertFalse(
            self.env["collection.voucher"].search(
                [("document_id", "=", "MCP-DOC-MISSING-CUST")]
            ),
        )

    def test_create_rejects_blank_per_payment_customer(self):
        """Empty-string and whitespace-only per-payment customer MUST reject."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        for blank, document_id in (
            ("", "MCP-DOC-BLANK-CUST"),
            ("   ", "MCP-DOC-WS-CUST"),
        ):
            with self.subTest(customer=blank):
                with self.assertRaises(UserError) as err:
                    self._call(
                        self._payload(
                            customer=blank,
                            payments=[
                                {
                                    "document_id": document_id,
                                    "document_type": "cash_deposit",
                                    "amount": 1.0,
                                }
                            ],
                        ),
                    )
                self.assertIn("customer_identification", str(err.exception).lower())
                self.assertNotIn("tool not found", str(err.exception).lower())
                self.assertFalse(
                    self.env["collection.voucher"].search(
                        [("document_id", "=", document_id)]
                    ),
                )
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )

    def test_mixed_customers_create_one_voucher_each(self):
        """One call with two customers MUST stamp each voucher from its payment."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        result = self._call(
            self._payload(
                payments=[
                    {
                        "customer_identification": "MCP-CUST-MIX-A",
                        "document_id": "MCP-DOC-MIX-A",
                        "document_type": "bank_transfer",
                        "amount": 10.0,
                    },
                    {
                        "customer_identification": "MCP-CUST-MIX-B",
                        "document_id": "MCP-DOC-MIX-B",
                        "document_type": "cash_deposit",
                        "amount": 20.0,
                    },
                ],
            ),
        )
        self._assert_voucher_list(result, ["MCP-DOC-MIX-A", "MCP-DOC-MIX-B"])
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers + 2,
        )
        first = self.env["collection.voucher"].browse(result["vouchers"][0]["id"])
        second = self.env["collection.voucher"].browse(result["vouchers"][1]["id"])
        self.assertEqual(first.partner_id.vat, "MCP-CUST-MIX-A")
        self.assertEqual(second.partner_id.vat, "MCP-CUST-MIX-B")
        self.assertEqual(first.document_id, "MCP-DOC-MIX-A")
        self.assertEqual(second.document_id, "MCP-DOC-MIX-B")

    def test_mixed_customer_batch_invalid_payment_writes_nothing(self):
        """Mixed-customer batch MUST be atomic: one invalid payment writes zero."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        cases = (
            (
                "blank-customer",
                [
                    {
                        "customer_identification": "MCP-CUST-ATOMIC-A",
                        "document_id": "MCP-DOC-ATOMIC-OK-BLANK",
                        "document_type": "bank_transfer",
                        "amount": 10.0,
                    },
                    {
                        "customer_identification": "   ",
                        "document_id": "MCP-DOC-ATOMIC-BAD-BLANK",
                        "document_type": "cash_deposit",
                        "amount": 20.0,
                    },
                ],
                ["MCP-DOC-ATOMIC-OK-BLANK", "MCP-DOC-ATOMIC-BAD-BLANK"],
            ),
            (
                "missing-document_id",
                [
                    {
                        "customer_identification": "MCP-CUST-ATOMIC-A",
                        "document_id": "MCP-DOC-ATOMIC-OK-DOC",
                        "document_type": "bank_transfer",
                        "amount": 10.0,
                    },
                    {
                        "customer_identification": "MCP-CUST-ATOMIC-B",
                        "document_type": "cash_deposit",
                        "amount": 20.0,
                    },
                ],
                ["MCP-DOC-ATOMIC-OK-DOC"],
            ),
        )
        for label, payments, document_ids in cases:
            with self.subTest(case=label):
                with self.assertRaises(UserError):
                    self._call(self._payload(payments=payments))
                self.assertFalse(
                    self.env["collection.voucher"].search(
                        [("document_id", "in", document_ids)]
                    ),
                )
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )

    # --- 4.3 Exact-retry / in-call dup / partial / former cross-voucher ---

    def test_exact_retry_returns_all_vouchers_ignores_customer(self):
        """Exact document_id set must replay all vouchers.

        Per-payment customer on retry is ignored.
        """
        first = self._call(
            self._payload(
                payments=[
                    {
                        "customer_identification": "MCP-CUST-RETRY-A",
                        "document_id": "MCP-DOC-RETRY-A",
                        "document_type": "bank_transfer",
                        "amount": 10.0,
                    },
                    {
                        "customer_identification": "MCP-CUST-RETRY-B",
                        "document_id": "MCP-DOC-RETRY-B",
                        "document_type": "cash_deposit",
                        "amount": 20.0,
                    },
                ],
            ),
        )
        self._assert_voucher_list(first, ["MCP-DOC-RETRY-A", "MCP-DOC-RETRY-B"])
        before_vouchers = self.env["collection.voucher"].search_count([])

        second = self._call(
            self._payload(
                payments=[
                    {
                        "customer_identification": "MCP-CUST-RETRY-A-OTHER",
                        "document_id": "MCP-DOC-RETRY-A",
                        "document_type": "bank_transfer",
                        "amount": 999.0,
                    },
                    {
                        "customer_identification": "MCP-CUST-RETRY-B-OTHER",
                        "document_id": "MCP-DOC-RETRY-B",
                        "document_type": "cash_deposit",
                        "amount": 888.0,
                    },
                ],
            ),
        )

        self.assertEqual(second["vouchers"], first["vouchers"])
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        voucher_a = self.env["collection.voucher"].browse(first["vouchers"][0]["id"])
        voucher_b = self.env["collection.voucher"].browse(first["vouchers"][1]["id"])
        self.assertEqual(voucher_a.partner_id.vat, "MCP-CUST-RETRY-A")
        self.assertEqual(voucher_b.partner_id.vat, "MCP-CUST-RETRY-B")
        self.assertEqual(voucher_a.amount, 10.0)
        self.assertEqual(voucher_b.amount, 20.0)

    def test_in_call_duplicate_document_id_rejects_no_writes(self):
        """Two payments sharing a document_id in one call must reject with no writes."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError) as err:
            self._call(
                self._payload(
                    customer="MCP-CUST-INCALL-DUP",
                    payments=[
                        {
                            "document_id": "MCP-DOC-DUP-SAME",
                            "document_type": "bank_transfer",
                            "amount": 1.0,
                        },
                        {
                            "document_id": "MCP-DOC-DUP-SAME",
                            "document_type": "check",
                            "amount": 2.0,
                        },
                    ],
                ),
            )
        message = str(err.exception).lower()
        self.assertTrue(
            "document_id" in message or "duplicate" in message,
            f"Expected duplicate document_id message, got: {err.exception}",
        )
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertFalse(
            self.env["collection.voucher"].search(
                [("document_id", "=", "MCP-DOC-DUP-SAME")]
            ),
        )

    def test_partial_conflict_rejects_no_writes(self):
        """Some existing + some new document_ids must reject with no writes."""
        self._call(
            self._payload(
                customer="MCP-CUST-PARTIAL-SEED",
                payments=[
                    {
                        "document_id": "MCP-DOC-PARTIAL-EXIST",
                        "document_type": "bank_transfer",
                        "amount": 5.0,
                    }
                ],
            ),
        )
        before_vouchers = self.env["collection.voucher"].search_count([])

        with self.assertRaises(UserError) as err:
            self._call(
                self._payload(
                    customer="MCP-CUST-PARTIAL",
                    payments=[
                        {
                            "document_id": "MCP-DOC-PARTIAL-EXIST",
                            "document_type": "bank_transfer",
                            "amount": 5.0,
                        },
                        {
                            "document_id": "MCP-DOC-PARTIAL-NEW",
                            "document_type": "cash_deposit",
                            "amount": 7.0,
                        },
                    ],
                ),
            )
        self.assertNotIn("tool not found", str(err.exception).lower())
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertFalse(
            self.env["collection.voucher"].search(
                [("document_id", "=", "MCP-DOC-PARTIAL-NEW")]
            ),
        )

    def test_existing_document_ids_on_different_vouchers_succeed(self):
        """Exact set spanning multiple vouchers must replay all (not reject)."""
        first = self._call(
            self._payload(
                customer="MCP-CUST-CROSS-A",
                payments=[
                    {
                        "document_id": "MCP-DOC-CROSS-A",
                        "document_type": "bank_transfer",
                        "amount": 1.0,
                    }
                ],
            ),
        )
        second = self._call(
            self._payload(
                customer="MCP-CUST-CROSS-B",
                payments=[
                    {
                        "document_id": "MCP-DOC-CROSS-B",
                        "document_type": "check",
                        "amount": 2.0,
                    }
                ],
            ),
        )
        before_vouchers = self.env["collection.voucher"].search_count([])

        replayed = self._call(
            self._payload(
                customer="MCP-CUST-CROSS-MERGE",
                payments=[
                    {
                        "document_id": "MCP-DOC-CROSS-A",
                        "document_type": "bank_transfer",
                        "amount": 1.0,
                    },
                    {
                        "document_id": "MCP-DOC-CROSS-B",
                        "document_type": "check",
                        "amount": 2.0,
                    },
                ],
            ),
        )
        self._assert_voucher_list(replayed, ["MCP-DOC-CROSS-A", "MCP-DOC-CROSS-B"])
        self.assertEqual(replayed["vouchers"][0]["id"], first["vouchers"][0]["id"])
        self.assertEqual(replayed["vouchers"][1]["id"], second["vouchers"][0]["id"])
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        voucher_a = self.env["collection.voucher"].browse(first["vouchers"][0]["id"])
        self.assertEqual(voucher_a.partner_id.vat, "MCP-CUST-CROSS-A")

    # --- 4.4 UniqueViolation → re-lookup replay / reject ---

    def _patch_voucher_search_miss_once(self, document_ids):
        """Simulate a race: first document_id lookup misses rows that already exist."""
        Voucher = self.env["collection.voucher"]
        empty = Voucher.browse()
        real_search = type(Voucher).search
        calls = {"n": 0}

        def search_proxy(model_self, domain=None, *args, **kwargs):
            domain = domain or []
            is_doc_lookup = any(
                isinstance(term, (list, tuple))
                and len(term) >= 3
                and term[0] == "document_id"
                and term[1] == "in"
                and set(term[2]) == set(document_ids)
                for term in domain
            )
            if model_self._name == "collection.voucher" and is_doc_lookup:
                calls["n"] += 1
                if calls["n"] == 1:
                    return empty
            return real_search(model_self, domain, *args, **kwargs)

        return patch("odoo.models.Model.search", search_proxy), calls

    def test_unique_violation_full_match_replays(self):
        """Race: UniqueViolation then exact-set re-lookup must replay all vouchers."""
        first = self._call(
            self._payload(
                customer="MCP-CUST-UV-REPLAY",
                payments=[
                    {
                        "document_id": "MCP-DOC-UV-A",
                        "document_type": "bank_transfer",
                        "amount": 11.0,
                    },
                    {
                        "document_id": "MCP-DOC-UV-B",
                        "document_type": "cash_deposit",
                        "amount": 22.0,
                    },
                ],
            ),
        )
        before_vouchers = self.env["collection.voucher"].search_count([])
        doc_ids = ["MCP-DOC-UV-A", "MCP-DOC-UV-B"]
        search_patch, calls = self._patch_voucher_search_miss_once(doc_ids)

        with mute_logger("odoo.sql_db"), search_patch:
            second = self._call(
                self._payload(
                    customer="MCP-CUST-UV-REPLAY-OTHER",
                    payments=[
                        {
                            "document_id": "MCP-DOC-UV-A",
                            "document_type": "bank_transfer",
                            "amount": 11.0,
                        },
                        {
                            "document_id": "MCP-DOC-UV-B",
                            "document_type": "cash_deposit",
                            "amount": 22.0,
                        },
                    ],
                ),
            )

        self.assertGreaterEqual(
            calls["n"],
            2,
            "Expected initial miss + post-UniqueViolation re-lookup",
        )
        self.assertEqual(second["vouchers"], first["vouchers"])
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )

    def test_unique_violation_partial_match_rejects(self):
        """Triangulation: UniqueViolation then incomplete re-lookup must UserError."""
        self._call(
            self._payload(
                customer="MCP-CUST-UV-PARTIAL",
                payments=[
                    {
                        "document_id": "MCP-DOC-UV-PARTIAL-EXIST",
                        "document_type": "bank_transfer",
                        "amount": 3.0,
                    }
                ],
            ),
        )
        before_vouchers = self.env["collection.voucher"].search_count([])
        doc_ids = ["MCP-DOC-UV-PARTIAL-EXIST", "MCP-DOC-UV-PARTIAL-NEW"]
        search_patch, _calls = self._patch_voucher_search_miss_once(doc_ids)

        with (
            mute_logger("odoo.sql_db"),
            search_patch,
            self.assertRaises(UserError) as err,
        ):
            self._call(
                self._payload(
                    customer="MCP-CUST-UV-PARTIAL-CALL",
                    payments=[
                        {
                            "document_id": "MCP-DOC-UV-PARTIAL-EXIST",
                            "document_type": "bank_transfer",
                            "amount": 3.0,
                        },
                        {
                            "document_id": "MCP-DOC-UV-PARTIAL-NEW",
                            "document_type": "check",
                            "amount": 4.0,
                        },
                    ],
                ),
            )
        self.assertNotIn("tool not found", str(err.exception).lower())
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertFalse(
            self.env["collection.voucher"].search(
                [("document_id", "=", "MCP-DOC-UV-PARTIAL-NEW")]
            ),
        )

    def test_portal_user_denied_no_writes(self):
        """Non-permitted caller gets AccessError and writes no voucher rows."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        with self.assertRaises(AccessError):
            self._call(
                self._payload(
                    customer="MCP-PORTAL-DENY",
                    payments=[
                        {
                            "document_id": "MCP-DOC-PORTAL",
                            "document_type": "bank_transfer",
                            "amount": 1.0,
                        }
                    ],
                ),
                user=self.portal_user,
            )
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
            "ACL denial must not create vouchers",
        )
        self.assertFalse(
            self.env["collection.voucher"].search(
                [("document_id", "=", "MCP-DOC-PORTAL")]
            ),
        )

    # --- seller_id required, stamp all-new only, replay read-only ---

    def _payload_with_seller(self, seller_id=None, **kwargs):
        payload = self._payload(**kwargs)
        payload["seller_id"] = self.internal_user.id if seller_id is None else seller_id
        return payload

    def test_all_new_create_stamps_seller_id(self):
        """All-new create MUST stamp top-level seller_id on every voucher."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        result = self._call(
            self._payload_with_seller(
                customer="MCP-CUST-SELLER",
                payments=[
                    {
                        "document_id": "MCP-DOC-SELLER-A",
                        "document_type": "bank_transfer",
                        "amount": 15.0,
                    },
                    {
                        "document_id": "MCP-DOC-SELLER-B",
                        "document_type": "cash_deposit",
                        "amount": 25.0,
                    },
                ],
            )
        )
        self._assert_voucher_list(result, ["MCP-DOC-SELLER-A", "MCP-DOC-SELLER-B"])
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers + 2,
        )
        first = self.env["collection.voucher"].browse(result["vouchers"][0]["id"])
        second = self.env["collection.voucher"].browse(result["vouchers"][1]["id"])
        self.assertEqual(first.seller_id, self.internal_user)
        self.assertEqual(second.seller_id, self.internal_user)

    def test_exact_retry_does_not_mutate_null_seller(self):
        """Exact replay MUST ignore seller_id and MUST NOT fill a legacy null seller."""
        legacy = self._create_legacy_null_seller_voucher(
            customer_identification="MCP-CUST-LEGACY-NULL",
            document_type="bank_transfer",
            document_id="MCP-DOC-LEGACY-NULL",
            amount=9.0,
        )
        self.assertFalse(legacy.seller_id)
        before_vouchers = self.env["collection.voucher"].search_count([])
        write_date = legacy.write_date

        result = self._call(
            self._payload_with_seller(
                customer="MCP-CUST-LEGACY-RETRY",
                payments=[
                    {
                        "document_id": "MCP-DOC-LEGACY-NULL",
                        "document_type": "bank_transfer",
                        "amount": 999.0,
                    }
                ],
            )
        )
        self._assert_voucher_list(result, ["MCP-DOC-LEGACY-NULL"])
        self.assertEqual(result["vouchers"][0]["id"], legacy.id)
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        legacy.invalidate_recordset()
        self.assertFalse(legacy.seller_id)
        self.assertEqual(legacy.partner_id.vat, "MCP-CUST-LEGACY-NULL")
        self.assertEqual(legacy.amount, 9.0)
        self.assertEqual(legacy.write_date, write_date)

    def test_exact_retry_does_not_replace_existing_seller(self):
        """Triangulation: replay with another seller MUST NOT rewrite seller_id."""
        first = self._call(
            self._payload_with_seller(
                customer="MCP-CUST-SELLER-KEEP",
                payments=[
                    {
                        "document_id": "MCP-DOC-SELLER-KEEP",
                        "document_type": "unsupported",
                    }
                ],
            )
        )
        voucher = self.env["collection.voucher"].browse(first["vouchers"][0]["id"])
        self.assertEqual(voucher.seller_id, self.internal_user)
        other_seller = self.env.ref("base.user_admin")
        self.assertNotEqual(other_seller, self.internal_user)

        result = self._call(
            self._payload_with_seller(
                seller_id=other_seller.id,
                customer="MCP-CUST-SELLER-KEEP-OTHER",
                payments=[
                    {
                        "document_id": "MCP-DOC-SELLER-KEEP",
                        "document_type": "unsupported",
                    }
                ],
            )
        )
        self.assertEqual(result["vouchers"][0]["id"], voucher.id)
        voucher.invalidate_recordset()
        self.assertEqual(voucher.seller_id, self.internal_user)
        self.assertEqual(voucher.partner_id.vat, "MCP-CUST-SELLER-KEEP")

    def test_missing_seller_id_rejects_no_writes(self):
        """Payloads missing seller_id MUST be rejected with no voucher writes."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError) as err:
            self._call(
                self._payload(
                    customer="MCP-CUST-NO-SELLER",
                    seller_id=None,
                    payments=[
                        {
                            "document_id": "MCP-DOC-NO-SELLER",
                            "document_type": "bank_transfer",
                            "amount": 1.0,
                        }
                    ],
                )
            )
        self.assertIn("seller_id", str(err.exception).lower())
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertFalse(
            self.env["collection.voucher"].search(
                [("document_id", "=", "MCP-DOC-NO-SELLER")]
            )
        )

    def test_portal_seller_id_rejects_no_writes(self):
        """Portal/share seller_id MUST be rejected with no writes."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        self.assertTrue(self.portal_user.share)
        with self.assertRaises(UserError) as err:
            self._call(
                self._payload_with_seller(
                    seller_id=self.portal_user.id,
                    customer="MCP-CUST-PORTAL-SELLER",
                    payments=[
                        {
                            "document_id": "MCP-DOC-PORTAL-SELLER",
                            "document_type": "check",
                            "amount": 2.0,
                            "check_type": "common",
                        }
                    ],
                )
            )
        message = str(err.exception).lower()
        self.assertNotIn("unexpected keyword", message)
        self.assertIn(
            "internal",
            message,
            f"Expected internal-seller validation message, got: {err.exception}",
        )
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertFalse(
            self.env["collection.voucher"].search(
                [("document_id", "=", "MCP-DOC-PORTAL-SELLER")]
            )
        )

    def test_unknown_seller_id_rejects_no_writes(self):
        """Unknown seller_id MUST be rejected with no writes."""
        unknown_id = (
            max(self.env["res.users"].search([], order="id desc", limit=1).id, 1)
            + 999999
        )
        self.assertFalse(self.env["res.users"].browse(unknown_id).exists())
        before_vouchers = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError) as err:
            self._call(
                self._payload_with_seller(
                    seller_id=unknown_id,
                    customer="MCP-CUST-UNKNOWN-SELLER",
                    payments=[
                        {
                            "document_id": "MCP-DOC-UNKNOWN-SELLER",
                            "document_type": "cash_deposit",
                            "amount": 3.0,
                        }
                    ],
                )
            )
        message = str(err.exception).lower()
        self.assertNotIn("unexpected keyword", message)
        self.assertIn(
            "seller_id",
            message,
            f"Expected seller_id validation message, got: {err.exception}",
        )
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertFalse(
            self.env["collection.voucher"].search(
                [("document_id", "=", "MCP-DOC-UNKNOWN-SELLER")]
            )
        )

    def _assert_mcp_voucher_payload_keys(self, result):
        for item in result["vouchers"]:
            self.assertEqual(set(item), {"id", "name", "state", "document_id"})
            self.assertNotIn("sheet_id", item)

    def test_all_new_unique_open_assigns_all_payments(self):
        """All-new MCP create MUST assign every voucher to the unique open sheet."""
        sheet = self.env["collection.sheet"].create(
            {"seller_id": self.internal_user.id}
        )
        result = self._call(
            self._payload(
                customer="MCP-CUST-AA-UNIQ",
                payments=[
                    {
                        "document_id": "MCP-DOC-AA-UNIQ-A",
                        "document_type": "bank_transfer",
                        "amount": 11.0,
                    },
                    {
                        "document_id": "MCP-DOC-AA-UNIQ-B",
                        "document_type": "check",
                        "amount": 22.0,
                        "check_type": "common",
                    },
                ],
            )
        )
        self._assert_voucher_list(result, ["MCP-DOC-AA-UNIQ-A", "MCP-DOC-AA-UNIQ-B"])
        self._assert_mcp_voucher_payload_keys(result)
        first = self.env["collection.voucher"].browse(result["vouchers"][0]["id"])
        second = self.env["collection.voucher"].browse(result["vouchers"][1]["id"])
        self.assertEqual(first.sheet_id, sheet)
        self.assertEqual(second.sheet_id, sheet)
        self.assertEqual(first.seller_id, self.internal_user)
        self.assertEqual(second.seller_id, self.internal_user)

    def test_all_new_no_open_creates_one_sheet_and_assigns_all(self):
        """Zero opens MUST create one open sheet and assign the whole MCP batch."""
        opens_before = self.env["collection.sheet"].search_count(
            [("seller_id", "=", self.internal_user.id), ("state", "=", "open")]
        )
        self.assertEqual(opens_before, 0)
        result = self._call(
            self._payload(
                customer="MCP-CUST-AA-NONE",
                payments=[
                    {
                        "document_id": "MCP-DOC-AA-NONE-A",
                        "document_type": "bank_transfer",
                        "amount": 3.0,
                    },
                    {
                        "document_id": "MCP-DOC-AA-NONE-B",
                        "document_type": "cash_deposit",
                        "amount": 4.0,
                    },
                ],
            )
        )
        self._assert_voucher_list(result, ["MCP-DOC-AA-NONE-A", "MCP-DOC-AA-NONE-B"])
        self._assert_mcp_voucher_payload_keys(result)
        first = self.env["collection.voucher"].browse(result["vouchers"][0]["id"])
        second = self.env["collection.voucher"].browse(result["vouchers"][1]["id"])
        self.assertTrue(first.sheet_id)
        self.assertEqual(first.sheet_id, second.sheet_id)
        self.assertEqual(first.sheet_id.seller_id, self.internal_user)
        self.assertEqual(first.sheet_id.state, "open")
        self.assertEqual(
            self.env["collection.sheet"].search_count(
                [("seller_id", "=", self.internal_user.id), ("state", "=", "open")]
            ),
            1,
        )

    def test_all_new_multiple_opens_rejects_no_writes(self):
        """More than one open MUST raise UserError with no MCP voucher writes."""
        first_sheet = self.env["collection.sheet"].create(
            {"seller_id": self.internal_user.id}
        )
        leftover = self.env["collection.sheet"].create(
            {"seller_id": self.internal_user.id, "state": "closed"}
        )
        leftover.with_context(collection_sheet_audited_state=True).write(
            {"state": "open"}
        )
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_sheets = self.env["collection.sheet"].search_count([])
        with self.assertRaises(UserError):
            self._call(
                self._payload(
                    customer="MCP-CUST-AA-MULTI",
                    payments=[
                        {
                            "document_id": "MCP-DOC-AA-MULTI-A",
                            "document_type": "unsupported",
                        },
                        {
                            "document_id": "MCP-DOC-AA-MULTI-B",
                            "document_type": "unsupported",
                        },
                    ],
                )
            )
        self.assertEqual(
            self.env["collection.voucher"].search_count([]), before_vouchers
        )
        self.assertEqual(self.env["collection.sheet"].search_count([]), before_sheets)
        self.assertFalse(
            self.env["collection.voucher"].search(
                [("document_id", "in", ["MCP-DOC-AA-MULTI-A", "MCP-DOC-AA-MULTI-B"])]
            )
        )
        self.assertEqual(first_sheet.state, "open")
        self.assertEqual(leftover.state, "open")

    def test_all_new_empty_enabled_sellers_rejects_no_writes(self):
        """All-new MCP MUST reject unused docs when the enabled-seller list is empty."""
        self.env.company.write({"enabled_seller_ids": [Command.clear()]})
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_sheets = self.env["collection.sheet"].search_count([])
        document_ids = ["MCP-DOC-EMPTY-SELLERS-A", "MCP-DOC-EMPTY-SELLERS-B"]
        with self.assertRaises(UserError) as err:
            self._call(
                self._payload(
                    customer="MCP-CUST-EMPTY-SELLERS",
                    payments=[
                        {
                            "document_id": document_ids[0],
                            "document_type": "bank_transfer",
                            "amount": 10.0,
                        },
                        {
                            "document_id": document_ids[1],
                            "document_type": "check",
                            "amount": 20.0,
                            "check_type": "common",
                        },
                    ],
                )
            )
        self.assertIn("seller", str(err.exception).lower())
        self.assertNotIn("tool not found", str(err.exception).lower())
        self.assertEqual(
            self.env["collection.voucher"].search_count([]), before_vouchers
        )
        self.assertEqual(self.env["collection.sheet"].search_count([]), before_sheets)
        self.assertFalse(
            self.env["collection.voucher"].search([("document_id", "in", document_ids)])
        )

    def test_all_new_disabled_seller_rejects_no_writes(self):
        """Triangulation: all-new MCP MUST reject a seller missing from the list."""
        disabled = create_internal_seller(self.env, "mcp_all_new_disabled_seller")
        self.env.company.write(
            {"enabled_seller_ids": [Command.set([self.internal_user.id])]}
        )
        self.assertNotIn(disabled, self.env.company.enabled_seller_ids)
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_sheets = self.env["collection.sheet"].search_count([])
        document_ids = ["MCP-DOC-DISABLED-SELLER-A", "MCP-DOC-DISABLED-SELLER-B"]
        with self.assertRaises(UserError) as err:
            self._call(
                self._payload(
                    customer="MCP-CUST-DISABLED-SELLER",
                    payments=[
                        {
                            "document_id": document_ids[0],
                            "document_type": "bank_transfer",
                            "amount": 11.0,
                        },
                        {
                            "document_id": document_ids[1],
                            "document_type": "cash_deposit",
                            "amount": 12.0,
                        },
                    ],
                    seller_id=disabled.id,
                )
            )
        self.assertIn("seller", str(err.exception).lower())
        self.assertNotIn("tool not found", str(err.exception).lower())
        self.assertEqual(
            self.env["collection.voucher"].search_count([]), before_vouchers
        )
        self.assertEqual(self.env["collection.sheet"].search_count([]), before_sheets)
        self.assertFalse(
            self.env["collection.voucher"].search([("document_id", "in", document_ids)])
        )

    def test_all_new_disallowed_type_rejects_no_writes(self):
        """All-new MCP MUST reject unused docs whose document_type is not allowed."""
        bank = self.env["collection.document.type"].search(
            [("code", "=", "bank_transfer")], limit=1
        )
        self.assertTrue(bank)
        self.env.company.write({"allowed_document_type_ids": [Command.unlink(bank.id)]})
        self.assertIn(self.internal_user, self.env.company.enabled_seller_ids)
        self.assertNotIn(
            "bank_transfer",
            self.env.company.allowed_document_type_ids.mapped("code"),
        )
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_sheets = self.env["collection.sheet"].search_count([])
        document_id = "MCP-DOC-DISALLOWED-TYPE"
        with self.assertRaises(UserError) as err:
            self._call(
                self._payload(
                    customer="MCP-CUST-DISALLOWED-TYPE",
                    payments=[
                        {
                            "document_id": document_id,
                            "document_type": "bank_transfer",
                            "amount": 13.0,
                        }
                    ],
                )
            )
        message = str(err.exception).lower()
        self.assertIn("document type", message)
        self.assertNotIn("tool not found", message)
        self.assertEqual(
            self.env["collection.voucher"].search_count([]), before_vouchers
        )
        self.assertEqual(self.env["collection.sheet"].search_count([]), before_sheets)
        self.assertFalse(
            self.env["collection.voucher"].search([("document_id", "=", document_id)])
        )

    def test_all_new_auto_create_off_stays_unassigned(self):
        """All-new MCP with auto_create_sheet OFF MUST create unassigned vouchers."""
        self.env.company.write({"auto_create_sheet": False})
        self.assertIn(self.internal_user, self.env.company.enabled_seller_ids)
        before_sheets = self.env["collection.sheet"].search_count([])
        before_vouchers = self.env["collection.voucher"].search_count([])
        document_ids = ["MCP-DOC-AUTO-OFF-A", "MCP-DOC-AUTO-OFF-B"]
        result = self._call(
            self._payload(
                customer="MCP-CUST-AUTO-OFF",
                payments=[
                    {
                        "document_id": document_ids[0],
                        "document_type": "bank_transfer",
                        "amount": 14.0,
                    },
                    {
                        "document_id": document_ids[1],
                        "document_type": "check",
                        "amount": 15.0,
                        "check_type": "common",
                    },
                ],
            )
        )
        self._assert_voucher_list(result, document_ids)
        self._assert_mcp_voucher_payload_keys(result)
        self.assertEqual(
            self.env["collection.voucher"].search_count([]), before_vouchers + 2
        )
        self.assertEqual(self.env["collection.sheet"].search_count([]), before_sheets)
        first = self.env["collection.voucher"].browse(result["vouchers"][0]["id"])
        second = self.env["collection.voucher"].browse(result["vouchers"][1]["id"])
        self.assertFalse(first.sheet_id)
        self.assertFalse(second.sheet_id)
        self.assertEqual(first.seller_id, self.internal_user)
        self.assertEqual(second.seller_id, self.internal_user)

    def test_exact_replay_leaves_sheet_id_and_write_date(self):
        """Exact replay MUST NOT attach, move, or clear sheets (incl. leftover)."""
        assigned = self._call(
            self._payload(
                customer="MCP-CUST-AA-REPLAY",
                payments=[
                    {
                        "document_id": "MCP-DOC-AA-REPLAY-A",
                        "document_type": "bank_transfer",
                        "amount": 8.0,
                    }
                ],
            )
        )
        voucher = self.env["collection.voucher"].browse(assigned["vouchers"][0]["id"])
        self.assertTrue(voucher.sheet_id)
        sheet_id = voucher.sheet_id.id
        write_date = voucher.write_date

        leftover = self._create_legacy_null_seller_voucher(
            customer_identification="MCP-CUST-AA-REPLAY-LEFT",
            document_type="cash_deposit",
            document_id="MCP-DOC-AA-REPLAY-LEFT",
            amount=1.0,
        )
        self.assertFalse(leftover.seller_id)
        self.assertFalse(leftover.sheet_id)
        leftover_write = leftover.write_date
        before_sheets = self.env["collection.sheet"].search_count([])

        retried_assigned = self._call(
            self._payload(
                customer="MCP-CUST-AA-REPLAY-OTHER",
                payments=[
                    {
                        "document_id": "MCP-DOC-AA-REPLAY-A",
                        "document_type": "bank_transfer",
                        "amount": 999.0,
                    }
                ],
            )
        )
        self._assert_mcp_voucher_payload_keys(retried_assigned)
        self.assertEqual(retried_assigned["vouchers"][0]["id"], voucher.id)
        voucher.invalidate_recordset()
        self.assertEqual(voucher.sheet_id.id, sheet_id)
        self.assertEqual(voucher.write_date, write_date)
        self.assertEqual(voucher.partner_id.vat, "MCP-CUST-AA-REPLAY")

        retried_left = self._call(
            self._payload(
                customer="MCP-CUST-AA-REPLAY-LEFT-OTHER",
                payments=[
                    {
                        "document_id": "MCP-DOC-AA-REPLAY-LEFT",
                        "document_type": "cash_deposit",
                        "amount": 999.0,
                    }
                ],
            )
        )
        self._assert_mcp_voucher_payload_keys(retried_left)
        leftover.invalidate_recordset()
        self.assertEqual(retried_left["vouchers"][0]["id"], leftover.id)
        self.assertFalse(leftover.sheet_id)
        self.assertFalse(leftover.seller_id)
        self.assertEqual(leftover.write_date, leftover_write)
        self.assertEqual(self.env["collection.sheet"].search_count([]), before_sheets)

    # --- company-scoped MCP replay classifier ---

    def _create_company(self, name):
        """Persist a second company; satisfy partner.autopost_bills when present."""
        Partner = self.env["res.partner"].with_context(
            tracking_disable=True,
            mail_create_nolog=True,
            mail_notrack=True,
            mail_create_nosubscribe=True,
        )
        partner_vals = {"name": name, "is_company": True}
        if "autopost_bills" in Partner._fields:
            partner_vals["autopost_bills"] = "ask"
            partner = Partner.create(partner_vals)
        elif self._partner_has_autopost_bills_column():
            self.env.cr.execute(
                """
                INSERT INTO res_partner (
                    name, email, active, complete_name, type, is_company,
                    autopost_bills, create_uid, write_uid, create_date, write_date
                )
                VALUES (
                    %s, %s, true, %s, 'contact', true, 'ask',
                    1, 1,
                    (now() AT TIME ZONE 'UTC'),
                    (now() AT TIME ZONE 'UTC')
                )
                RETURNING id
                """,
                (name, f"{name}@example.com", name),
            )
            partner = Partner.browse(self.env.cr.fetchone()[0])
        else:
            partner = Partner.create(partner_vals)
        return self.env["res.company"].create(
            {
                "name": name,
                "partner_id": partner.id,
            }
        )

    def _create_voucher_in_company(self, company, document_id, customer=None, **extra):
        """Create a voucher stamped on ``company`` (seller enabled there)."""
        seller = extra.pop("seller_id", self.internal_user)
        ensure_enabled_seller(self.env, seller, company=company)
        partner = dummy_customer_partner(
            self.env, customer=customer, extra=extra, default="MCP-OTHER-CO"
        )
        vals = {
            "partner_id": partner.id,
            "document_type": extra.pop("document_type", "bank_transfer"),
            "document_id": document_id,
            "seller_id": seller.id,
            "company_id": company.id,
        }
        vals.update(extra)
        company.write({"auto_create_sheet": False})
        return self.env["collection.voucher"].with_company(company).create(vals)

    def _grant_companies(self, user, companies, current):
        user.write(
            {
                "company_id": current.id,
                "company_ids": [(6, 0, companies.ids)],
            }
        )

    def _assert_generic_document_conflict(self, err, voucher, company):
        """Conflict UserError must not disclose voucher id/name or company."""
        message = str(err.exception)
        lowered = message.lower()
        self.assertIn("conflict", lowered)
        self.assertNotIn("tool not found", lowered)
        self.assertNotIn(str(voucher.id), message)
        self.assertNotIn(voucher.name, message)
        self.assertNotIn(company.name, message)

    def test_same_company_replay_skips_disabled_seller_and_disallowed_type(self):
        """Same-company exact replay MUST skip seller/type gates and sheet mutate."""
        first = self._call(
            self._payload(
                customer="MCP-CUST-REPLAY-GATES",
                payments=[
                    {
                        "document_id": "MCP-DOC-REPLAY-GATES",
                        "document_type": "bank_transfer",
                        "amount": 3.0,
                    }
                ],
            )
        )
        voucher = self.env["collection.voucher"].browse(first["vouchers"][0]["id"])
        self.assertEqual(voucher.company_id, self.env.company)
        sheet_id = voucher.sheet_id.id
        write_date = voucher.write_date
        bank = self.env["collection.document.type"].search(
            [("code", "=", "bank_transfer")], limit=1
        )
        self.assertTrue(bank)
        self.env.company.write(
            {
                "enabled_seller_ids": [Command.clear()],
                "allowed_document_type_ids": [Command.unlink(bank.id)],
            }
        )
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_sheets = self.env["collection.sheet"].search_count([])

        replayed = self._call(
            self._payload(
                customer="MCP-CUST-REPLAY-GATES-OTHER",
                payments=[
                    {
                        "document_id": "MCP-DOC-REPLAY-GATES",
                        "document_type": "bank_transfer",
                        "amount": 999.0,
                    }
                ],
            )
        )

        self._assert_voucher_list(replayed, ["MCP-DOC-REPLAY-GATES"])
        self._assert_mcp_voucher_payload_keys(replayed)
        self.assertEqual(replayed["vouchers"][0]["id"], voucher.id)
        self.assertEqual(
            self.env["collection.voucher"].search_count([]), before_vouchers
        )
        self.assertEqual(self.env["collection.sheet"].search_count([]), before_sheets)
        voucher.invalidate_recordset()
        self.assertEqual(voucher.sheet_id.id, sheet_id)
        self.assertEqual(voucher.write_date, write_date)
        self.assertEqual(voucher.seller_id, self.internal_user)
        self.assertEqual(voucher.document_type, "bank_transfer")
        self.assertEqual(voucher.partner_id.vat, "MCP-CUST-REPLAY-GATES")
        self.assertEqual(voucher.amount, 3.0)

    def test_other_company_visible_hit_rejects_generic_no_ids(self):
        """Visible other-company document_id MUST reject, not replay, with no ids."""
        company_a = self.env.company
        company_b = self._create_company("MCP-OtherCo-Visible")
        self._grant_companies(
            self.internal_user, company_a | company_b, current=company_a
        )
        voucher_b = self._create_voucher_in_company(company_b, "MCP-DOC-OTHER-VISIBLE")
        self.assertEqual(voucher_b.company_id, company_b)
        visible = (
            self.env["collection.voucher"]
            .with_user(self.internal_user)
            .search([("document_id", "=", "MCP-DOC-OTHER-VISIBLE")])
        )
        self.assertEqual(visible, voucher_b)
        before_vouchers = self.env["collection.voucher"].search_count([])

        with self.assertRaises(UserError) as err:
            self._call(
                self._payload(
                    customer="MCP-CUST-OTHER-VISIBLE",
                    payments=[
                        {
                            "document_id": "MCP-DOC-OTHER-VISIBLE",
                            "document_type": "bank_transfer",
                            "amount": 1.0,
                        }
                    ],
                )
            )

        self._assert_generic_document_conflict(err, voucher_b, company_b)
        self.assertEqual(
            self.env["collection.voucher"].search_count([]), before_vouchers
        )
        self.assertFalse(
            self.env["collection.voucher"].search(
                [
                    ("document_id", "=", "MCP-DOC-OTHER-VISIBLE"),
                    ("company_id", "=", company_a.id),
                ]
            )
        )

    def test_multi_company_reader_does_not_replay_other_company(self):
        """Triangulation: a reader of A and B MUST NOT replay B when creating in A."""
        company_a = self.env.company
        company_b = self._create_company("MCP-OtherCo-NoReplay")
        self._grant_companies(
            self.internal_user, company_a | company_b, current=company_a
        )
        voucher_b = self._create_voucher_in_company(company_b, "MCP-DOC-NO-B-REPLAY")
        before_vouchers = self.env["collection.voucher"].search_count([])

        with self.assertRaises(UserError) as err:
            self._call(
                self._payload(
                    customer="MCP-CUST-NO-B-REPLAY",
                    payments=[
                        {
                            "document_id": "MCP-DOC-NO-B-REPLAY",
                            "document_type": "check",
                            "amount": 2.0,
                            "check_type": "common",
                        }
                    ],
                )
            )

        self._assert_generic_document_conflict(err, voucher_b, company_b)
        self.assertEqual(
            self.env["collection.voucher"].search_count([]), before_vouchers
        )

    def test_unique_violation_hidden_other_company_generic_error(self):
        """UniqueViolation with a rule-hidden other-company row MUST generic-reject."""
        company_a = self.env.company
        company_b = self._create_company("MCP-OtherCo-Hidden")
        self.internal_user.write(
            {
                "company_id": company_a.id,
                "company_ids": [(6, 0, [company_a.id])],
            }
        )
        voucher_b = self._create_voucher_in_company(company_b, "MCP-DOC-UV-HIDDEN")
        hidden = (
            self.env["collection.voucher"]
            .with_user(self.internal_user)
            .search([("document_id", "=", "MCP-DOC-UV-HIDDEN")])
        )
        self.assertFalse(hidden, "Caller must not see company B's voucher")
        self.env.company.write({"auto_create_sheet": False})
        before_a = self.env["collection.voucher"].search_count(
            [("company_id", "=", company_a.id)]
        )

        with mute_logger("odoo.sql_db"), self.assertRaises(UserError) as err:
            self._call(
                self._payload(
                    customer="MCP-CUST-UV-HIDDEN",
                    payments=[
                        {
                            "document_id": "MCP-DOC-UV-HIDDEN",
                            "document_type": "bank_transfer",
                            "amount": 4.0,
                        }
                    ],
                )
            )

        self._assert_generic_document_conflict(err, voucher_b, company_b)
        self.assertEqual(
            self.env["collection.voucher"].search_count(
                [("company_id", "=", company_a.id)]
            ),
            before_a,
        )
        voucher_b.invalidate_recordset()
        self.assertTrue(voucher_b.exists())
        self.assertEqual(voucher_b.company_id, company_b)


class TestCollectionMcpAttachment(TransactionCase):
    """RED/GREEN: optional nested MCP attachment on create; exact-retry ignore."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tool_model = cls.env["muk_mcp.tool"]
        cls.internal_user = cls.env.ref("base.user_admin")
        ensure_enabled_seller(cls.env, cls.internal_user)

    def setUp(self):
        super().setUp()
        install_bound_test_connector(self, self.internal_user)

    def _call(self, arguments, user=None):
        arguments = dict(arguments)
        arguments.setdefault("seller_id", self.internal_user.id)
        env = mcp_env_with_listable_customers(
            self.env, arguments, user, self.internal_user
        )
        text, _info = self.tool_model._call(TOOL_NAME, arguments, env)
        return json.loads(text)

    def _voucher_attachments(self, voucher):
        return self.env["ir.attachment"].search(
            [
                ("res_model", "=", "collection.voucher"),
                ("res_id", "=", voucher.id),
                ("res_field", "=", False),
            ]
        )

    def _field_attachments(self, voucher):
        """Binary-field leftovers (`res_field=attachment`) must not exist."""
        return self.env["ir.attachment"].search(
            [
                ("res_model", "=", "collection.voucher"),
                ("res_id", "=", voucher.id),
                ("res_field", "=", "attachment"),
            ]
        )

    def _chatter_attachment_count(self):
        return self.env["ir.attachment"].search_count(
            [
                ("res_model", "=", "collection.voucher"),
                ("res_field", "=", False),
            ]
        )

    def _nest(self, name, mimetype, datas):
        return {"name": name, "mimetype": mimetype, "datas": datas}

    def test_create_with_valid_png_nest_becomes_chatter_proof(self):
        """All-new create with valid nested PNG becomes chatter designated proof."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_atts = self._chatter_attachment_count()
        result = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-PNG",
                        "document_id": "MCP-DOC-ATT-PNG",
                        "document_type": "bank_transfer",
                        "amount": 12.0,
                        "attachment": self._nest("proof.png", "image/png", PNG_B64),
                    }
                ],
            },
        )
        self.assertEqual(len(result["vouchers"]), 1)
        voucher = self.env["collection.voucher"].browse(result["vouchers"][0]["id"])
        self.assertTrue(voucher.exists())
        self.assertEqual(result["vouchers"][0]["document_id"], "MCP-DOC-ATT-PNG")
        self.assertEqual(voucher.message_main_attachment_id.name, "proof.png")
        self.assertTrue(voucher.message_main_attachment_id)
        attachments = self._voucher_attachments(voucher)
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments.datas, PNG_B64.encode())
        self.assertFalse(attachments.res_field)
        self.assertFalse(
            self._field_attachments(voucher),
            "MCP nest must not persist as Binary res_field=attachment",
        )
        self.assertNotIn("attachment", voucher._fields)
        self.assertNotIn("attachment_filename", voucher._fields)
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers + 1,
        )
        self.assertEqual(self._chatter_attachment_count(), before_atts + 1)

    def test_create_with_valid_pdf_nest_persists(self):
        """Triangulation: valid nested PDF also persists via ir.attachment."""
        result = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-PDF",
                        "document_id": "MCP-DOC-ATT-PDF",
                        "document_type": "cash_deposit",
                        "amount": 8.0,
                        "attachment": self._nest(
                            "receipt.pdf", "application/pdf", PDF_B64
                        ),
                    }
                ],
            },
        )
        voucher = self.env["collection.voucher"].browse(result["vouchers"][0]["id"])
        self.assertEqual(voucher.message_main_attachment_id.name, "receipt.pdf")
        self.assertEqual(len(self._voucher_attachments(voucher)), 1)
        self.assertEqual(self._voucher_attachments(voucher).datas, PDF_B64.encode())

    def test_create_omitting_nest_still_creates(self):
        """Omit nest remains valid and creates a voucher without a file."""
        result = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-OMIT",
                        "document_id": "MCP-DOC-ATT-OMIT",
                        "document_type": "check",
                        "amount": 3.0,
                        "check_type": "common",
                    }
                ],
            },
        )
        voucher = self.env["collection.voucher"].browse(result["vouchers"][0]["id"])
        self.assertTrue(voucher.exists())
        self.assertFalse(voucher.message_main_attachment_id)
        self.assertFalse(self._voucher_attachments(voucher))
        self.assertFalse(self._field_attachments(voucher))

    def test_create_mime_mismatch_rejects_no_writes(self):
        """Declared MIME mismatch / non-allow-list must UserError with no writes."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_atts = self._chatter_attachment_count()
        with self.assertRaises(UserError) as err:
            self._call(
                {
                    "payments": [
                        {
                            "customer_identification": "MCP-ATT-MIME",
                            "document_id": "MCP-DOC-ATT-MIME",
                            "document_type": "bank_transfer",
                            "amount": 1.0,
                            # PNG bytes but declared as PDF → mismatch.
                            "attachment": self._nest(
                                "fake.pdf", "application/pdf", PNG_B64
                            ),
                        }
                    ],
                },
            )
        self.assertNotIn("tool not found", str(err.exception).lower())
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertEqual(
            self._chatter_attachment_count(),
            before_atts,
        )
        self.assertFalse(
            self.env["collection.voucher"].search(
                [("document_id", "=", "MCP-DOC-ATT-MIME")]
            ),
        )
        leftover = self.env["collection.voucher"].search(
            [("document_id", "=", "MCP-DOC-ATT-MIME")]
        )
        self.assertFalse(leftover)
        self.assertFalse(
            self.env["ir.attachment"].search(
                [
                    ("res_model", "=", "collection.voucher"),
                    ("res_field", "=", "attachment"),
                    ("name", "=", "fake.pdf"),
                ]
            ),
        )

    def test_create_bad_base64_rejects_no_writes(self):
        """Triangulation: bad base64 nest must UserError with no writes."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError) as err:
            self._call(
                {
                    "payments": [
                        {
                            "customer_identification": "MCP-ATT-B64",
                            "document_id": "MCP-DOC-ATT-B64",
                            "document_type": "bank_transfer",
                            "amount": 1.0,
                            "attachment": self._nest(
                                "bad.bin", "image/png", INVALID_B64
                            ),
                        }
                    ],
                },
            )
        self.assertNotIn("tool not found", str(err.exception).lower())
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertFalse(
            self.env["collection.voucher"].search(
                [("document_id", "=", "MCP-DOC-ATT-B64")]
            ),
        )

    def test_create_text_mime_rejects_no_writes(self):
        """Triangulation: text content with text/plain declared must reject."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError):
            self._call(
                {
                    "payments": [
                        {
                            "customer_identification": "MCP-ATT-TXT",
                            "document_id": "MCP-DOC-ATT-TXT",
                            "document_type": "bank_transfer",
                            "amount": 1.0,
                            "attachment": self._nest(
                                "notes.txt", "text/plain", TXT_B64
                            ),
                        }
                    ],
                },
            )
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertFalse(
            self.env["collection.voucher"].search(
                [("document_id", "=", "MCP-DOC-ATT-TXT")]
            ),
        )

    def test_create_batch_invalid_nest_writes_nothing(self):
        """Fail-closed: invalid nest MUST reject the whole batch before writes."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_atts = self._chatter_attachment_count()
        with self.assertRaises(UserError) as err:
            self._call(
                {
                    "payments": [
                        {
                            "customer_identification": "MCP-ATT-BATCH-FAIL",
                            "document_id": "MCP-DOC-ATT-BATCH-OK",
                            "document_type": "bank_transfer",
                            "amount": 10.0,
                            "attachment": self._nest("ok.png", "image/png", PNG_B64),
                        },
                        {
                            "customer_identification": "MCP-ATT-BATCH-FAIL",
                            "document_id": "MCP-DOC-ATT-BATCH-BAD",
                            "document_type": "cash_deposit",
                            "amount": 11.0,
                            "attachment": self._nest(
                                "fake.pdf", "application/pdf", PNG_B64
                            ),
                        },
                    ],
                },
            )
        self.assertNotIn("tool not found", str(err.exception).lower())
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertEqual(self._chatter_attachment_count(), before_atts)
        self.assertFalse(
            self.env["collection.voucher"].search(
                [
                    (
                        "document_id",
                        "in",
                        ["MCP-DOC-ATT-BATCH-OK", "MCP-DOC-ATT-BATCH-BAD"],
                    )
                ]
            ),
        )

    def test_create_incomplete_nest_rejects_no_writes(self):
        """Triangulation: nest missing datas MUST UserError with no writes."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_atts = self._chatter_attachment_count()
        with self.assertRaises(UserError) as err:
            self._call(
                {
                    "payments": [
                        {
                            "customer_identification": "MCP-ATT-INCOMPLETE",
                            "document_id": "MCP-DOC-ATT-INCOMPLETE",
                            "document_type": "bank_transfer",
                            "amount": 1.0,
                            "attachment": {
                                "name": "proof.png",
                                "mimetype": "image/png",
                            },
                        }
                    ],
                },
            )
        message = str(err.exception).lower()
        self.assertNotIn("tool not found", message)
        self.assertTrue(
            "datas" in message or "attachment" in message,
            f"Expected nest datas validation, got: {err.exception}",
        )
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertEqual(self._chatter_attachment_count(), before_atts)
        self.assertFalse(
            self.env["collection.voucher"].search(
                [("document_id", "=", "MCP-DOC-ATT-INCOMPLETE")]
            ),
        )

    def test_exact_retry_with_nest_does_not_replace_attachment(self):
        """Exact-retry with a different nest must leave stored attachment unchanged."""
        first = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-RETRY",
                        "document_id": "MCP-DOC-ATT-RETRY",
                        "document_type": "bank_transfer",
                        "amount": 5.0,
                        "attachment": self._nest("original.png", "image/png", PNG_B64),
                    }
                ],
            },
        )
        voucher = self.env["collection.voucher"].browse(first["vouchers"][0]["id"])
        original_att_ids = self._voucher_attachments(voucher).ids
        self.assertEqual(len(original_att_ids), 1)
        self.assertEqual(voucher.message_main_attachment_id.name, "original.png")
        self.assertEqual(voucher.message_main_attachment_id.datas, PNG_B64.encode())
        before_atts = self._chatter_attachment_count()

        second = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-RETRY-OTHER",
                        "document_id": "MCP-DOC-ATT-RETRY",
                        "document_type": "bank_transfer",
                        "amount": 999.0,
                        "attachment": self._nest(
                            "replacement.pdf", "application/pdf", PDF_B64
                        ),
                    }
                ],
            },
        )
        self.assertEqual(second["vouchers"][0]["id"], first["vouchers"][0]["id"])
        voucher.invalidate_recordset()
        self.assertEqual(voucher.message_main_attachment_id.name, "original.png")
        self.assertEqual(voucher.message_main_attachment_id.datas, PNG_B64.encode())
        self.assertEqual(self._voucher_attachments(voucher).ids, original_att_ids)
        self.assertEqual(
            self._chatter_attachment_count(),
            before_atts,
        )

    def test_exact_retry_with_nest_does_not_add_when_voucher_has_none(self):
        """Exact-retry nest MUST NOT add an attachment when the voucher has none."""
        first = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-RETRY-EMPTY",
                        "document_id": "MCP-DOC-ATT-RETRY-EMPTY",
                        "document_type": "cash_deposit",
                        "amount": 4.0,
                    }
                ],
            },
        )
        voucher = self.env["collection.voucher"].browse(first["vouchers"][0]["id"])
        self.assertFalse(voucher.message_main_attachment_id)
        before_atts = self._chatter_attachment_count()

        second = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-RETRY-EMPTY-OTHER",
                        "document_id": "MCP-DOC-ATT-RETRY-EMPTY",
                        "document_type": "cash_deposit",
                        "amount": 4.0,
                        "attachment": self._nest("late.png", "image/png", PNG_B64),
                    }
                ],
            },
        )
        self.assertEqual(second["vouchers"][0]["id"], first["vouchers"][0]["id"])
        voucher.invalidate_recordset()
        self.assertFalse(voucher.message_main_attachment_id)
        self.assertFalse(self._voucher_attachments(voucher))
        self.assertEqual(
            self._chatter_attachment_count(),
            before_atts,
        )

    def test_exact_retry_without_nest_leaves_existing_attachment(self):
        """Triangulation: exact-retry omitting nest must not clear existing file."""
        first = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-RETRY-OMIT",
                        "document_id": "MCP-DOC-ATT-RETRY-OMIT",
                        "document_type": "check",
                        "amount": 6.0,
                        "check_type": "common",
                        "attachment": self._nest(
                            "keep.pdf", "application/pdf", PDF_B64
                        ),
                    }
                ],
            },
        )
        voucher = self.env["collection.voucher"].browse(first["vouchers"][0]["id"])
        second = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-RETRY-OMIT-OTHER",
                        "document_id": "MCP-DOC-ATT-RETRY-OMIT",
                        "document_type": "check",
                        "amount": 6.0,
                        "check_type": "common",
                    }
                ],
            },
        )
        self.assertEqual(second["vouchers"][0]["id"], first["vouchers"][0]["id"])
        voucher.invalidate_recordset()
        self.assertEqual(voucher.message_main_attachment_id.name, "keep.pdf")
        self.assertEqual(voucher.message_main_attachment_id.datas, PDF_B64.encode())
        self.assertEqual(len(self._voucher_attachments(voucher)), 1)

    def _patch_voucher_search_miss_once(self, document_ids):
        """Simulate a race: first document_id lookup misses rows that already exist."""
        Voucher = self.env["collection.voucher"]
        empty = Voucher.browse()
        real_search = type(Voucher).search
        calls = {"n": 0}

        def search_proxy(model_self, domain=None, *args, **kwargs):
            domain = domain or []
            is_doc_lookup = any(
                isinstance(term, (list, tuple))
                and len(term) >= 3
                and term[0] == "document_id"
                and term[1] == "in"
                and set(term[2]) == set(document_ids)
                for term in domain
            )
            if model_self._name == "collection.voucher" and is_doc_lookup:
                calls["n"] += 1
                if calls["n"] == 1:
                    return empty
            return real_search(model_self, domain, *args, **kwargs)

        return patch("odoo.models.Model.search", search_proxy), calls

    def test_exact_retry_ignores_invalid_nest(self):
        """Exact-retry MUST NOT compare nests: invalid MIME still replays."""
        first = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-RETRY-IGN",
                        "document_id": "MCP-DOC-ATT-RETRY-IGN",
                        "document_type": "bank_transfer",
                        "amount": 7.0,
                        "attachment": self._nest("keep.png", "image/png", PNG_B64),
                    }
                ],
            },
        )
        voucher = self.env["collection.voucher"].browse(first["vouchers"][0]["id"])
        original_att_ids = self._voucher_attachments(voucher).ids
        before_atts = self._chatter_attachment_count()

        second = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-RETRY-IGN-OTHER",
                        "document_id": "MCP-DOC-ATT-RETRY-IGN",
                        "document_type": "bank_transfer",
                        "amount": 7.0,
                        "attachment": self._nest("bad.bin", "image/png", INVALID_B64),
                    }
                ],
            },
        )
        self.assertEqual(second["vouchers"], first["vouchers"])
        voucher.invalidate_recordset()
        self.assertEqual(voucher.message_main_attachment_id.name, "keep.png")
        self.assertEqual(self._voucher_attachments(voucher).ids, original_att_ids)
        self.assertEqual(self._chatter_attachment_count(), before_atts)
        self.assertFalse(self._field_attachments(voucher))

    def test_exact_retry_returns_all_with_mixed_nests(self):
        """Exact-retry of a two-payment set MUST return all and ignore mixed nests."""
        first = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-RETRY-ALL",
                        "document_id": "MCP-DOC-ATT-RETRY-ALL-A",
                        "document_type": "bank_transfer",
                        "amount": 1.0,
                        "attachment": self._nest("a.png", "image/png", PNG_B64),
                    },
                    {
                        "customer_identification": "MCP-ATT-RETRY-ALL",
                        "document_id": "MCP-DOC-ATT-RETRY-ALL-B",
                        "document_type": "cash_deposit",
                        "amount": 2.0,
                    },
                ],
            },
        )
        self.assertEqual(len(first["vouchers"]), 2)
        voucher_a = self.env["collection.voucher"].browse(first["vouchers"][0]["id"])
        voucher_b = self.env["collection.voucher"].browse(first["vouchers"][1]["id"])
        a_att_ids = self._voucher_attachments(voucher_a).ids
        before_atts = self._chatter_attachment_count()

        second = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-RETRY-ALL-OTHER",
                        "document_id": "MCP-DOC-ATT-RETRY-ALL-A",
                        "document_type": "bank_transfer",
                        "amount": 99.0,
                    },
                    {
                        "customer_identification": "MCP-ATT-RETRY-ALL-OTHER",
                        "document_id": "MCP-DOC-ATT-RETRY-ALL-B",
                        "document_type": "cash_deposit",
                        "amount": 99.0,
                        "attachment": self._nest(
                            "late.pdf", "application/pdf", PDF_B64
                        ),
                    },
                ],
            },
        )
        self.assertEqual(second["vouchers"], first["vouchers"])
        voucher_a.invalidate_recordset()
        voucher_b.invalidate_recordset()
        self.assertEqual(voucher_a.message_main_attachment_id.name, "a.png")
        self.assertEqual(self._voucher_attachments(voucher_a).ids, a_att_ids)
        self.assertFalse(voucher_b.message_main_attachment_id)
        self.assertFalse(self._voucher_attachments(voucher_b))
        self.assertEqual(self._chatter_attachment_count(), before_atts)

    def test_unique_violation_replay_with_nest_does_not_post(self):
        """UniqueViolation exact-set replay MUST NOT message_post a nested proof."""
        first = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-UV",
                        "document_id": "MCP-DOC-ATT-UV",
                        "document_type": "bank_transfer",
                        "amount": 13.0,
                    }
                ],
            },
        )
        voucher = self.env["collection.voucher"].browse(first["vouchers"][0]["id"])
        self.assertFalse(voucher.message_main_attachment_id)
        before_atts = self._chatter_attachment_count()
        doc_ids = ["MCP-DOC-ATT-UV"]
        search_patch, calls = self._patch_voucher_search_miss_once(doc_ids)

        with mute_logger("odoo.sql_db"), search_patch:
            second = self._call(
                {
                    "payments": [
                        {
                            "customer_identification": "MCP-ATT-UV-OTHER",
                            "document_id": "MCP-DOC-ATT-UV",
                            "document_type": "bank_transfer",
                            "amount": 13.0,
                            "attachment": self._nest("race.png", "image/png", PNG_B64),
                        }
                    ],
                },
            )

        self.assertGreaterEqual(
            calls["n"],
            2,
            "Expected initial miss + post-UniqueViolation re-lookup",
        )
        self.assertEqual(second["vouchers"], first["vouchers"])
        voucher.invalidate_recordset()
        self.assertFalse(voucher.message_main_attachment_id)
        self.assertFalse(self._voucher_attachments(voucher))
        self.assertEqual(self._chatter_attachment_count(), before_atts)

    def test_unique_violation_replay_does_not_replace_existing_proof(self):
        """Triangulation: UniqueViolation replay MUST NOT replace stored proof."""
        first = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-UV-KEEP",
                        "document_id": "MCP-DOC-ATT-UV-KEEP",
                        "document_type": "cash_deposit",
                        "amount": 4.0,
                        "attachment": self._nest("orig.png", "image/png", PNG_B64),
                    }
                ],
            },
        )
        voucher = self.env["collection.voucher"].browse(first["vouchers"][0]["id"])
        original_att_ids = self._voucher_attachments(voucher).ids
        before_atts = self._chatter_attachment_count()
        doc_ids = ["MCP-DOC-ATT-UV-KEEP"]
        search_patch, calls = self._patch_voucher_search_miss_once(doc_ids)

        with mute_logger("odoo.sql_db"), search_patch:
            second = self._call(
                {
                    "payments": [
                        {
                            "customer_identification": "MCP-ATT-UV-KEEP-OTHER",
                            "document_id": "MCP-DOC-ATT-UV-KEEP",
                            "document_type": "cash_deposit",
                            "amount": 4.0,
                            "attachment": self._nest(
                                "race.pdf", "application/pdf", PDF_B64
                            ),
                        }
                    ],
                },
            )

        self.assertGreaterEqual(calls["n"], 2)
        self.assertEqual(second["vouchers"], first["vouchers"])
        voucher.invalidate_recordset()
        self.assertEqual(voucher.message_main_attachment_id.name, "orig.png")
        self.assertEqual(voucher.message_main_attachment_id.datas, PNG_B64.encode())
        self.assertEqual(self._voucher_attachments(voucher).ids, original_att_ids)
        self.assertEqual(self._chatter_attachment_count(), before_atts)
        self.assertFalse(self._field_attachments(voucher))

    def test_unique_violation_replay_ignores_invalid_nest(self):
        """Race replay ignores nests, including invalid MIME."""
        first = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-UV-IGN",
                        "document_id": "MCP-DOC-ATT-UV-IGN",
                        "document_type": "bank_transfer",
                        "amount": 5.0,
                    }
                ],
            },
        )
        voucher = self.env["collection.voucher"].browse(first["vouchers"][0]["id"])
        self.assertFalse(voucher.message_main_attachment_id)
        before_atts = self._chatter_attachment_count()
        doc_ids = ["MCP-DOC-ATT-UV-IGN"]
        search_patch, calls = self._patch_voucher_search_miss_once(doc_ids)

        with mute_logger("odoo.sql_db"), search_patch:
            second = self._call(
                {
                    "payments": [
                        {
                            "customer_identification": "MCP-ATT-UV-IGN-OTHER",
                            "document_id": "MCP-DOC-ATT-UV-IGN",
                            "document_type": "bank_transfer",
                            "amount": 5.0,
                            "attachment": self._nest(
                                "bad.bin", "image/png", INVALID_B64
                            ),
                        }
                    ],
                },
            )

        self.assertGreaterEqual(calls["n"], 2)
        self.assertEqual(second["vouchers"], first["vouchers"])
        voucher.invalidate_recordset()
        self.assertFalse(voucher.message_main_attachment_id)
        self.assertFalse(self._voucher_attachments(voucher))
        self.assertEqual(self._chatter_attachment_count(), before_atts)


class TestCollectionMcpProvenance(TransactionCase):
    """RED/GREEN: nested raw_ocr + seller_confirmed on all-new MCP create."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tool_model = cls.env["muk_mcp.tool"]
        cls.internal_user = cls.env.ref("base.user_admin")
        ensure_enabled_seller(cls.env, cls.internal_user)

    def setUp(self):
        super().setUp()
        install_bound_test_connector(self, self.internal_user)

    def _call(self, arguments, user=None):
        arguments = dict(arguments)
        arguments.setdefault("seller_id", self.internal_user.id)
        env = mcp_env_with_listable_customers(
            self.env, arguments, user, self.internal_user
        )
        text, _info = self.tool_model._call(TOOL_NAME, arguments, env)
        return json.loads(text)

    def _voucher(self, result):
        return self.env["collection.voucher"].browse(result["vouchers"][0]["id"])

    def _snapshot_count(self, voucher):
        Snapshot = self.env["collection.voucher.review.snapshot"]
        return Snapshot.search_count([("voucher_id", "=", voucher.id)])

    def _assert_empty_provenance(self, voucher):
        for name in voucher._REVIEW_EDITABLE_FIELDS:
            ocr_value = voucher[f"ocr_{name}"]
            seller_value = voucher[f"seller_{name}"]
            if name == "amount":
                self.assertEqual(ocr_value, 0.0, f"ocr_{name}")
                self.assertEqual(seller_value, 0.0, f"seller_{name}")
            else:
                self.assertFalse(ocr_value, f"ocr_{name}")
                self.assertFalse(seller_value, f"seller_{name}")

    def _assert_layer_matches(self, voucher, prefix, expected):
        for name in voucher._REVIEW_EDITABLE_FIELDS:
            field_name = f"{prefix}_{name}" if prefix else name
            actual = voucher[field_name]
            if name not in expected:
                if name == "amount":
                    self.assertEqual(actual, 0.0, field_name)
                else:
                    self.assertFalse(actual, field_name)
                continue
            if name == "amount":
                self.assertAlmostEqual(actual, expected[name], places=2, msg=field_name)
            else:
                self.assertEqual(actual, expected[name], field_name)

    def _assert_no_base64_in_provenance(self, voucher):
        for name in voucher._REVIEW_EDITABLE_FIELDS:
            for prefix in ("ocr", "seller"):
                rendered = str(voucher[f"{prefix}_{name}"])
                self.assertNotIn(PNG_B64, rendered)
                self.assertNotIn(PDF_B64, rendered)
                self.assertNotIn("base64", rendered.lower())

    def _patch_voucher_search_miss_once(self, document_ids):
        Voucher = self.env["collection.voucher"]
        empty = Voucher.browse()
        real_search = type(Voucher).search
        calls = {"n": 0}

        def search_proxy(model_self, domain=None, *args, **kwargs):
            domain = domain or []
            is_doc_lookup = any(
                isinstance(term, (list, tuple))
                and len(term) >= 3
                and term[0] == "document_id"
                and term[1] == "in"
                and set(term[2]) == set(document_ids)
                for term in domain
            )
            if model_self._name == "collection.voucher" and is_doc_lookup:
                calls["n"] += 1
                if calls["n"] == 1:
                    return empty
            return real_search(model_self, domain, *args, **kwargs)

        return patch("odoo.models.Model.search", search_proxy), calls

    def test_schema_exposes_nests_without_identity_or_base64(self):
        """MCP payment schema nests typed provenance; identity stays outside."""
        by_name = {
            entry["name"]: entry for entry in self.tool_model.get_tools(registry="mcp")
        }
        payment_schema = by_name[TOOL_NAME]["inputSchema"]["properties"]["payments"][
            "items"
        ]
        properties = payment_schema["properties"]
        self.assertIn("raw_ocr", properties)
        self.assertIn("seller_confirmed", properties)
        self.assertIn("document_id", properties)
        self.assertIn("customer_identification", properties)
        self.assertIn(
            "customer_identification",
            payment_schema["required"],
        )
        self.assertIn("attachment", properties)
        for nest_key in ("raw_ocr", "seller_confirmed"):
            nest_props = properties[nest_key].get("properties", {})
            self.assertIn("document_type", nest_props)
            self.assertIn("document_type", properties[nest_key].get("required", []))
            for forbidden in (
                "datas",
                "attachment",
                "document_id",
                "customer_identification",
                "seller_id",
            ):
                self.assertNotIn(forbidden, nest_props)

    def test_omitted_nests_leave_null_provenance(self):
        """Both nests omitted MUST leave empty provenance on all-new create."""
        result = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-PROV-OMIT",
                        "document_id": "MCP-DOC-PROV-OMIT",
                        "document_type": "bank_transfer",
                        "amount": 40.0,
                        "from_account": "FROM-OMIT",
                    }
                ],
            }
        )
        voucher = self._voucher(result)
        self.assertAlmostEqual(voucher.amount, 40.0, places=2)
        self.assertEqual(voucher.from_account, "FROM-OMIT")
        self._assert_empty_provenance(voucher)
        self.assertEqual(self._snapshot_count(voucher), 0)

    def test_orm_create_without_nests_leaves_null_provenance(self):
        """Triangulation: UI/ORM create MUST remain allowed with empty provenance."""
        voucher = self.env["collection.voucher"].create(
            {
                "partner_id": dummy_customer_partner(
                    self.env, customer="ORM-PROV-OMIT"
                ).id,
                "document_type": "check",
                "amount": 12.0,
                "check_number": "CHK-ORM",
                "seller_id": ensure_enabled_seller(self.env, self.internal_user).id,
            }
        )
        self.assertTrue(voucher.id)
        self.assertEqual(voucher.document_type, "check")
        self.assertEqual(voucher.check_number, "CHK-ORM")
        self._assert_empty_provenance(voucher)
        self.assertEqual(self._snapshot_count(voucher), 0)

    def test_omitted_nests_with_attachment_keep_base64_out_of_provenance(self):
        """Attachment + omitted nests MUST NOT copy base64 into provenance fields."""
        result = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-PROV-ATT-OMIT",
                        "document_id": "MCP-DOC-PROV-ATT-OMIT",
                        "document_type": "bank_transfer",
                        "amount": 5.0,
                        "attachment": {
                            "name": "proof.png",
                            "mimetype": "image/png",
                            "datas": PNG_B64,
                        },
                    }
                ],
            }
        )
        voucher = self._voucher(result)
        self.assertTrue(voucher.message_main_attachment_id)
        self._assert_empty_provenance(voucher)
        self._assert_no_base64_in_provenance(voucher)

    def test_unchanged_seller_stamps_all_three_layers_equal(self):
        """When both nests equal top-level, raw, seller, and current MUST match."""
        fields_vals = {
            "document_type": "bank_transfer",
            "amount": 100.0,
            "from_account": "FROM-1",
            "to_account": "TO-1",
        }
        result = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-PROV-EQUAL",
                        "document_id": "MCP-DOC-PROV-EQUAL",
                        **fields_vals,
                        "raw_ocr": dict(fields_vals),
                        "seller_confirmed": dict(fields_vals),
                    }
                ],
            }
        )
        voucher = self._voucher(result)
        self._assert_layer_matches(voucher, "", fields_vals)
        self._assert_layer_matches(voucher, "ocr", fields_vals)
        self._assert_layer_matches(voucher, "seller", fields_vals)

    def test_seller_correction_keeps_raw_and_aligns_current(self):
        """Raw MAY differ; seller-confirmed MUST equal top-level and current."""
        raw_vals = {
            "document_type": "bank_transfer",
            "amount": 80.0,
            "from_account": "OCR-FROM",
            "to_account": "OCR-TO",
        }
        seller_vals = {
            "document_type": "bank_transfer",
            "amount": 125.5,
            "from_account": "SELLER-FROM",
            "to_account": "SELLER-TO",
        }
        result = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-PROV-CORR",
                        "document_id": "MCP-DOC-PROV-CORR",
                        **seller_vals,
                        "raw_ocr": dict(raw_vals),
                        "seller_confirmed": dict(seller_vals),
                    }
                ],
            }
        )
        voucher = self._voucher(result)
        self._assert_layer_matches(voucher, "", seller_vals)
        self._assert_layer_matches(voucher, "seller", seller_vals)
        self._assert_layer_matches(voucher, "ocr", raw_vals)

    def test_cash_deposit_stores_voucher_number_and_date_in_all_layers(self):
        """Cash-deposit voucher_number/voucher_date MUST persist in all three layers."""
        fields_vals = {
            "document_type": "cash_deposit",
            "amount": 30.0,
            "voucher_number": "CASH-99",
            "voucher_date": date(2026, 4, 1),
        }
        nest = {
            "document_type": "cash_deposit",
            "amount": 30.0,
            "voucher_number": "CASH-99",
            "voucher_date": "2026-04-01",
        }
        result = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-PROV-CASH",
                        "document_id": "MCP-DOC-PROV-CASH",
                        "document_type": "cash_deposit",
                        "amount": 30.0,
                        "voucher_number": "CASH-99",
                        "voucher_date": "2026-04-01",
                        "raw_ocr": dict(nest),
                        "seller_confirmed": dict(nest),
                    }
                ],
            }
        )
        voucher = self._voucher(result)
        self._assert_layer_matches(voucher, "", fields_vals)
        self._assert_layer_matches(voucher, "ocr", fields_vals)
        self._assert_layer_matches(voucher, "seller", fields_vals)
        self.assertNotIn("ocr_document_id", voucher._fields)
        self.assertNotIn("seller_document_id", voucher._fields)
        self.assertNotIn("ocr_attachment", voucher._fields)
        self.assertNotIn("seller_seller_id", voucher._fields)

    def test_one_sided_nests_reject_with_no_writes(self):
        """Only one of raw_ocr/seller_confirmed MUST fail the batch before write."""
        before = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError) as err:
            self._call(
                {
                    "payments": [
                        {
                            "customer_identification": "MCP-PROV-ONE",
                            "document_id": "MCP-DOC-PROV-ONE",
                            "document_type": "bank_transfer",
                            "amount": 10.0,
                            "raw_ocr": {
                                "document_type": "bank_transfer",
                                "amount": 10.0,
                            },
                        }
                    ],
                }
            )
        self.assertNotIn("tool not found", str(err.exception).lower())
        self.assertEqual(self.env["collection.voucher"].search_count([]), before)
        self.assertFalse(
            self.env["collection.voucher"].search(
                [("document_id", "=", "MCP-DOC-PROV-ONE")]
            )
        )

    def test_malformed_and_mismatch_nests_reject_with_no_writes(self):
        """Triangulation: malformed, missing nest type, or mismatch write nothing."""
        before = self.env["collection.voucher"].search_count([])
        cases = [
            (
                "MCP-DOC-PROV-BAD-OBJ",
                {
                    "document_id": "MCP-DOC-PROV-BAD-OBJ",
                    "document_type": "bank_transfer",
                    "amount": 1.0,
                    "raw_ocr": "not-an-object",
                    "seller_confirmed": {
                        "document_type": "bank_transfer",
                        "amount": 1.0,
                    },
                },
            ),
            (
                "MCP-DOC-PROV-BAD-TYPE",
                {
                    "document_id": "MCP-DOC-PROV-BAD-TYPE",
                    "document_type": "bank_transfer",
                    "amount": 2.0,
                    "raw_ocr": {"amount": 2.0},
                    "seller_confirmed": {
                        "document_type": "bank_transfer",
                        "amount": 2.0,
                    },
                },
            ),
            (
                "MCP-DOC-PROV-MISMATCH",
                {
                    "document_id": "MCP-DOC-PROV-MISMATCH",
                    "document_type": "bank_transfer",
                    "amount": 3.0,
                    "raw_ocr": {
                        "document_type": "bank_transfer",
                        "amount": 3.0,
                    },
                    "seller_confirmed": {
                        "document_type": "bank_transfer",
                        "amount": 99.0,
                    },
                },
            ),
            (
                "MCP-DOC-PROV-NEST-ID",
                {
                    "document_id": "MCP-DOC-PROV-NEST-ID",
                    "document_type": "bank_transfer",
                    "amount": 4.0,
                    "raw_ocr": {
                        "document_type": "bank_transfer",
                        "amount": 4.0,
                        "document_id": "LEAKED",
                    },
                    "seller_confirmed": {
                        "document_type": "bank_transfer",
                        "amount": 4.0,
                    },
                },
            ),
        ]
        for document_id, payment in cases:
            with self.subTest(document_id=document_id):
                with self.assertRaises(UserError):
                    self._call(
                        {
                            "payments": [
                                dict(
                                    payment,
                                    customer_identification="MCP-PROV-BAD",
                                )
                            ],
                        }
                    )
                self.assertFalse(
                    self.env["collection.voucher"].search(
                        [("document_id", "=", document_id)]
                    )
                )
        self.assertEqual(self.env["collection.voucher"].search_count([]), before)

    def test_optional_omit_null_empty_nests_are_equal(self):
        """Reuse optional-field equality: omit/null/'' MUST match and stamp."""
        nest = {
            "document_type": "bank_transfer",
            "amount": 15.0,
            "from_account": None,
            "to_account": "",
        }
        result = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-PROV-OPT",
                        "document_id": "MCP-DOC-PROV-OPT",
                        "document_type": "bank_transfer",
                        "amount": 15.0,
                        "raw_ocr": dict(nest),
                        "seller_confirmed": dict(nest),
                    }
                ],
            }
        )
        voucher = self._voucher(result)
        expected = {"document_type": "bank_transfer", "amount": 15.0}
        self._assert_layer_matches(voucher, "", expected)
        self._assert_layer_matches(voucher, "ocr", expected)
        self._assert_layer_matches(voucher, "seller", expected)

    def test_batch_one_sided_second_payment_writes_nothing(self):
        """Fail-closed: a later bad nest MUST reject the whole batch."""
        before = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError):
            self._call(
                {
                    "payments": [
                        {
                            "customer_identification": "MCP-PROV-BATCH",
                            "document_id": "MCP-DOC-PROV-BATCH-OK",
                            "document_type": "bank_transfer",
                            "amount": 8.0,
                            "raw_ocr": {
                                "document_type": "bank_transfer",
                                "amount": 8.0,
                            },
                            "seller_confirmed": {
                                "document_type": "bank_transfer",
                                "amount": 8.0,
                            },
                        },
                        {
                            "customer_identification": "MCP-PROV-BATCH",
                            "document_id": "MCP-DOC-PROV-BATCH-BAD",
                            "document_type": "cash_deposit",
                            "amount": 9.0,
                            "seller_confirmed": {
                                "document_type": "cash_deposit",
                                "amount": 9.0,
                            },
                        },
                    ],
                }
            )
        self.assertEqual(self.env["collection.voucher"].search_count([]), before)
        self.assertFalse(
            self.env["collection.voucher"].search(
                [
                    (
                        "document_id",
                        "in",
                        ["MCP-DOC-PROV-BATCH-OK", "MCP-DOC-PROV-BATCH-BAD"],
                    )
                ]
            )
        )

    def test_provenance_parsed_on_create_path_not_in_payment_vals(self):
        """Parse nests after existing-document check, never in payment vals helper."""
        mixin_cls = type(self.env["muk_mcp.mixin"])
        parse_vals_src = inspect.getsource(mixin_cls._collection_parse_payment_vals)
        self.assertNotIn("raw_ocr", parse_vals_src)
        self.assertNotIn("seller_confirmed", parse_vals_src)
        self.assertTrue(
            hasattr(mixin_cls, "_collection_parse_payment_provenance"),
            "provenance MUST be parsed by a dedicated create-path helper",
        )
        create_src = inspect.getsource(mixin_cls.create_collection_vouchers)
        idx_existing = create_src.index("_collection_vouchers_by_document_ids")
        idx_parse = create_src.index("_collection_parse_payment_provenance")
        idx_create = create_src.index("_collection_create_vouchers")
        self.assertGreater(idx_parse, idx_existing)
        self.assertGreater(idx_create, idx_parse)

    def test_exact_replay_ignores_different_and_omitted_nests(self):
        """Exact replay MUST NOT write, backfill, or mutate provenance or snapshots."""
        fields_vals = {
            "document_type": "bank_transfer",
            "amount": 22.0,
            "from_account": "KEEP-FROM",
        }
        first = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-PROV-REPLAY",
                        "document_id": "MCP-DOC-PROV-REPLAY",
                        **fields_vals,
                        "raw_ocr": dict(fields_vals),
                        "seller_confirmed": dict(fields_vals),
                    }
                ],
            }
        )
        voucher = self._voucher(first)
        self._assert_layer_matches(voucher, "ocr", fields_vals)
        before_snaps = self._snapshot_count(voucher)
        write_date = voucher.write_date

        second = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-PROV-REPLAY-OTHER",
                        "document_id": "MCP-DOC-PROV-REPLAY",
                        "document_type": "bank_transfer",
                        "amount": 999.0,
                        "raw_ocr": {
                            "document_type": "bank_transfer",
                            "amount": 1.0,
                        },
                        "seller_confirmed": {
                            "document_type": "bank_transfer",
                            "amount": 999.0,
                        },
                    }
                ],
            }
        )
        self.assertEqual(second["vouchers"], first["vouchers"])
        voucher.invalidate_recordset()
        self._assert_layer_matches(voucher, "", fields_vals)
        self._assert_layer_matches(voucher, "ocr", fields_vals)
        self._assert_layer_matches(voucher, "seller", fields_vals)
        self.assertEqual(self._snapshot_count(voucher), before_snaps)
        self.assertEqual(voucher.write_date, write_date)

        empty = self.env["collection.voucher"].create(
            {
                "partner_id": dummy_customer_partner(
                    self.env, customer="MCP-PROV-REPLAY-EMPTY"
                ).id,
                "document_type": "cash_deposit",
                "document_id": "MCP-DOC-PROV-REPLAY-EMPTY",
                "amount": 4.0,
                "seller_id": ensure_enabled_seller(self.env, self.internal_user).id,
            }
        )
        self._assert_empty_provenance(empty)
        retried = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-PROV-REPLAY-EMPTY-OTHER",
                        "document_id": "MCP-DOC-PROV-REPLAY-EMPTY",
                        "document_type": "cash_deposit",
                        "amount": 4.0,
                        "raw_ocr": {
                            "document_type": "cash_deposit",
                            "amount": 4.0,
                        },
                        "seller_confirmed": {
                            "document_type": "cash_deposit",
                            "amount": 4.0,
                        },
                    }
                ],
            }
        )
        self.assertEqual(retried["vouchers"][0]["id"], empty.id)
        empty.invalidate_recordset()
        self._assert_empty_provenance(empty)
        self.assertEqual(self._snapshot_count(empty), 0)

    def test_exact_replay_ignores_malformed_nests(self):
        """Triangulation: exact-retry MUST ignore malformed nests and still replay."""
        first = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-PROV-REPLAY-BAD",
                        "document_id": "MCP-DOC-PROV-REPLAY-BAD",
                        "document_type": "check",
                        "amount": 6.0,
                        "check_type": "common",
                    }
                ],
            }
        )
        voucher = self._voucher(first)
        second = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-PROV-REPLAY-BAD-OTHER",
                        "document_id": "MCP-DOC-PROV-REPLAY-BAD",
                        "document_type": "check",
                        "amount": 6.0,
                        "check_type": "common",
                        "raw_ocr": "not-an-object",
                        "seller_confirmed": {"amount": 6.0},
                    }
                ],
            }
        )
        self.assertEqual(second["vouchers"], first["vouchers"])
        voucher.invalidate_recordset()
        self._assert_empty_provenance(voucher)

    def test_unique_violation_replay_ignores_nests_no_backfill(self):
        """UniqueViolation exact-set replay MUST ignore nests and not backfill."""
        first = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-PROV-UV",
                        "document_id": "MCP-DOC-PROV-UV",
                        "document_type": "bank_transfer",
                        "amount": 13.0,
                    }
                ],
            }
        )
        voucher = self._voucher(first)
        self._assert_empty_provenance(voucher)
        doc_ids = ["MCP-DOC-PROV-UV"]
        search_patch, calls = self._patch_voucher_search_miss_once(doc_ids)
        with mute_logger("odoo.sql_db"), search_patch:
            second = self._call(
                {
                    "payments": [
                        {
                            "customer_identification": "MCP-PROV-UV-OTHER",
                            "document_id": "MCP-DOC-PROV-UV",
                            "document_type": "bank_transfer",
                            "amount": 13.0,
                            "raw_ocr": {
                                "document_type": "bank_transfer",
                                "amount": 13.0,
                            },
                            "seller_confirmed": {
                                "document_type": "bank_transfer",
                                "amount": 13.0,
                            },
                        }
                    ],
                }
            )
        self.assertGreaterEqual(calls["n"], 2)
        self.assertEqual(second["vouchers"], first["vouchers"])
        voucher.invalidate_recordset()
        self._assert_empty_provenance(voucher)
        self.assertEqual(self._snapshot_count(voucher), 0)
