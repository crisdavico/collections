# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import inspect
import json
from pathlib import Path

from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase

from odoo.addons.muk_mcp.core.tool import get_tool_index

from .common_connector import TEST_CONNECTOR_TYPE, install_test_connector_type
from .test_collection_payment import create_internal_seller, ensure_enabled_seller

TOOL_NAME = "customer_debt"
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


class TestCollectionMcpCustomerDebt(TransactionCase):
    """customer_debt MCP discovery, auth, routing, and payload."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        install_test_connector_type(cls)
        cls.tool_model = cls.env["muk_mcp.tool"]
        cls.internal_user = cls._create_user(
            "collection_customer_debt_internal", "base.group_user"
        )
        cls.portal_user = cls._create_user(
            "collection_customer_debt_portal", "base.group_portal"
        )
        cls.public_user = cls._create_user(
            "collection_customer_debt_public", "base.group_public"
        )
        cls.seller = create_internal_seller(cls.env, "collection_customer_debt_seller")

    def setUp(self):
        super().setUp()
        install_test_connector_type(self)
        self.connector = self.env["collection.connector"].create(
            {
                "name": "MCP Debt Connector",
                "type": TEST_CONNECTOR_TYPE,
            }
        )
        self.env.company.write({"collection_connector_id": self.connector.id})
        ensure_enabled_seller(self.env, self.seller)
        self.env["collection.connector.seller.binding"].create(
            {
                "connector_id": self.connector.id,
                "external_seller_id": "ext-bound",
                "user_id": self.seller.id,
            }
        )

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

    def _call(self, arguments, user=None):
        """Run customer_debt in-process and return decoded JSON."""
        env = self.env(user=user) if user else self.env(user=self.internal_user)
        text, _info = self.tool_model._call(TOOL_NAME, arguments, env)
        return json.loads(text)

    def _assert_user_error_no_leak(self, func):
        with self.assertRaises(UserError) as ctx:
            func()
        message = str(ctx.exception)
        for token in _LEAK_TOKENS:
            self.assertNotIn(token, message)
        return ctx.exception

    def test_customer_debt_discovered_as_method_read_mcp(self):
        """customer_debt is method-discovered read/mcp; no DB row."""
        by_name = {
            entry["name"]: entry for entry in self.tool_model.get_tools(registry="mcp")
        }
        self.assertIn(TOOL_NAME, by_name)
        self.assertNotIn("list_collection_sellers", by_name)
        entry = get_tool_index(self.env, registry="mcp")[TOOL_NAME]
        self.assertEqual(entry["category"], "read")
        self.assertEqual(entry["registry"], "mcp")
        self.assertEqual(entry["kind"], "method")
        self.assertFalse(
            self.env["muk_mcp.tool"].search([("name", "=", TOOL_NAME)]),
            "customer_debt must not have a DB muk_mcp.tool row",
        )
        schema = by_name[TOOL_NAME]["inputSchema"]
        self.assertEqual(schema["type"], "object")
        self.assertEqual(
            set(schema["required"]), {"seller_id", "customer_identification"}
        )
        self.assertEqual(schema["properties"]["seller_id"]["type"], "integer")
        self.assertEqual(
            schema["properties"]["customer_identification"]["type"], "string"
        )

    def test_success_returns_normalized_debt_without_source(self):
        """Enabled bound seller MUST return outstanding invoices and omit source."""
        before_partners = self.env["res.partner"].search_count([])
        result = self._call(
            {
                "seller_id": self.seller.id,
                "customer_identification": "20-11111111-1",
            }
        )
        self.assertEqual(set(result), {"customer", "summary", "invoices"})
        self.assertNotIn("source", result)
        customer = result["customer"]
        self.assertEqual(customer["external_customer_id"], "cust-bound-active")
        self.assertEqual(customer["name"], "Bound Active Customer")
        self.assertEqual(customer["identification"], "20-11111111-1")
        self.assertEqual(customer["customer_code"], "C-BOUND-1")
        self.assertEqual(
            [row["external_invoice_id"] for row in result["invoices"]],
            ["inv-bound-overdue", "inv-bound-open"],
        )
        for row in result["invoices"]:
            self.assertEqual(row["document_kind"], "invoice")
            self.assertEqual(
                set(row),
                {
                    "external_invoice_id",
                    "number",
                    "issue_date",
                    "due_date",
                    "amount",
                    "balance",
                    "state",
                    "document_kind",
                },
            )
        self.assertEqual(result["summary"]["total_balance"], 150.0)
        self.assertEqual(result["summary"]["overdue_balance"], 100.0)
        self.assertEqual(result["summary"]["open_balance"], 50.0)
        self.assertEqual(result["summary"]["invoice_count"], 2)
        self.assertEqual(self.env["res.partner"].search_count([]), before_partners)

    def test_quotation_debt_rows_include_kind_and_omit_source(self):
        """MCP customer_debt MUST pass quotation kind and still omit source."""
        mixed = (
            {
                "id": "inv-bound-open",
                "customer_id": "cust-bound-active",
                "number": "A-0002",
                "issue_date": "2026-04-01",
                "due_date": "2026-09-01",
                "amount": 50.0,
                "balance": 50.0,
                "state": "open",
            },
            {
                "id": "quo-bound-overdue",
                "customer_id": "cust-bound-active",
                "number": "Q-0001",
                "issue_date": "2026-01-15",
                "due_date": "2026-03-15",
                "amount": 75.0,
                "balance": 75.0,
                "state": "overdue",
                "document_kind": "quotation",
            },
        )
        mixin = self.env["muk_mcp.mixin"].with_context(collection_test_invoices=mixed)
        payload = mixin.customer_debt(self.seller.id, "20-11111111-1")
        self.assertEqual(set(payload), {"customer", "summary", "invoices"})
        self.assertNotIn("source", payload)
        kinds = {
            row["external_invoice_id"]: row["document_kind"]
            for row in payload["invoices"]
        }
        self.assertEqual(kinds["inv-bound-open"], "invoice")
        self.assertEqual(kinds["quo-bound-overdue"], "quotation")
        self.assertEqual(payload["summary"]["invoice_count"], 2)

    def test_zero_debt_returns_empty_invoices(self):
        """Active customer with no outstanding invoices MUST succeed with zeros."""
        result = self._call(
            {
                "seller_id": self.seller.id,
                "customer_identification": "20-11111111-1",
            }
        )
        self.assertTrue(result["invoices"])
        mixin = self.env["muk_mcp.mixin"].with_context(collection_test_invoices=())
        payload = mixin.customer_debt(self.seller.id, "20-11111111-1")
        self.assertNotIn("source", payload)
        self.assertEqual(payload["invoices"], [])
        self.assertEqual(payload["summary"]["invoice_count"], 0)
        self.assertEqual(payload["summary"]["total_balance"], 0.0)

    def test_portal_and_public_callers_denied_access_error(self):
        """Portal and public callers MUST receive AccessError."""
        self.assertTrue(self.portal_user.share)
        self.assertTrue(self.public_user.share)
        arguments = {
            "seller_id": self.seller.id,
            "customer_identification": "20-11111111-1",
        }
        for user in (self.portal_user, self.public_user):
            with self.subTest(login=user.login):
                with self.assertRaises(AccessError):
                    self._call(arguments, user=user)

    def test_non_enabled_seller_fails_closed(self):
        """Seller absent from enabled_seller_ids MUST raise UserError."""
        other = create_internal_seller(self.env, "collection_customer_debt_not_enabled")
        self.env["collection.connector.seller.binding"].create(
            {
                "connector_id": self.connector.id,
                "external_seller_id": "ext-unbound",
                "user_id": other.id,
            }
        )
        self.assertNotIn(other, self.env.company.enabled_seller_ids)
        self._assert_user_error_no_leak(
            lambda: self._call(
                {
                    "seller_id": other.id,
                    "customer_identification": "20-33333333-3",
                }
            )
        )

    def test_unbound_enabled_seller_fails_closed(self):
        """Enabled seller without a connector binding MUST raise UserError."""
        extra = create_internal_seller(self.env, "collection_customer_debt_unbound")
        ensure_enabled_seller(self.env, extra)
        self._assert_user_error_no_leak(
            lambda: self._call(
                {
                    "seller_id": extra.id,
                    "customer_identification": "20-11111111-1",
                }
            )
        )

    def test_unknown_inactive_and_other_seller_fail_closed(self):
        """Unknown, inactive, and other-seller identifications MUST UserError."""
        for identification in ("99-99999999-9", "20-22222222-2", "20-33333333-3"):
            with self.subTest(identification=identification):
                self._assert_user_error_no_leak(
                    lambda ident=identification: self._call(
                        {
                            "seller_id": self.seller.id,
                            "customer_identification": ident,
                        }
                    )
                )

    def test_empty_identification_fails_closed(self):
        """Empty customer_identification MUST raise UserError with no leak."""
        self._assert_user_error_no_leak(
            lambda: self._call(
                {
                    "seller_id": self.seller.id,
                    "customer_identification": "",
                }
            )
        )
        self._assert_user_error_no_leak(
            lambda: self._call(
                {
                    "seller_id": self.seller.id,
                    "customer_identification": "   ",
                }
            )
        )

    def test_missing_connector_fails_closed(self):
        """Missing active connector MUST raise UserError with no leak."""
        self.env.company.write({"collection_connector_id": False})
        self._assert_user_error_no_leak(
            lambda: self._call(
                {
                    "seller_id": self.seller.id,
                    "customer_identification": "20-11111111-1",
                }
            )
        )

    def test_inactive_connector_fails_closed(self):
        """Inactive company connector MUST raise UserError with no leak."""
        self.connector.active = False
        self._assert_user_error_no_leak(
            lambda: self._call(
                {
                    "seller_id": self.seller.id,
                    "customer_identification": "20-11111111-1",
                }
            )
        )

    def _create_company(self, name):
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

    def test_other_company_connector_is_not_used(self):
        """Current-company connector MUST be used; other companies MUST NOT leak."""
        other_company = self._create_company("MCP Debt Other Co")
        other_connector = (
            self.env["collection.connector"]
            .with_company(other_company)
            .create(
                {
                    "name": "MCP Debt Other Connector",
                    "type": TEST_CONNECTOR_TYPE,
                    "company_id": other_company.id,
                }
            )
        )
        other_company.write({"collection_connector_id": other_connector.id})
        result = self._call(
            {
                "seller_id": self.seller.id,
                "customer_identification": "20-11111111-1",
            }
        )
        self.assertNotIn("source", result)
        self.assertEqual(
            result["customer"]["external_customer_id"], "cust-bound-active"
        )
        self.assertNotEqual(other_connector.id, self.connector.id)

    def test_customer_debt_source_omits_sudo(self):
        """tools/customer_debt.py MUST NOT use sudo."""
        source_path = Path(__file__).resolve().parents[1] / "tools" / "customer_debt.py"
        self.assertTrue(source_path.is_file(), source_path)
        source = source_path.read_text(encoding="utf-8")
        code = "\n".join(
            line for line in source.splitlines() if not line.lstrip().startswith("#")
        )
        self.assertNotIn(".sudo(", code)
        self.assertNotIn("sudo()", code)

        mixin = self.env["muk_mcp.mixin"]
        method = getattr(type(mixin), "customer_debt", None)
        self.assertTrue(callable(method), "muk_mcp.mixin must expose customer_debt")
        method_code = "\n".join(
            line
            for line in inspect.getsource(method).splitlines()
            if not line.lstrip().startswith("#")
        )
        self.assertNotIn(".sudo(", method_code)
        self.assertNotIn("sudo()", method_code)
