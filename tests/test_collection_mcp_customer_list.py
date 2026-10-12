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

TOOL_NAME = "list_collection_customers"
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


class TestCollectionMcpCustomerList(TransactionCase):
    """list_collection_customers MCP discovery, auth, routing, and payload."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        install_test_connector_type(cls)
        cls.tool_model = cls.env["muk_mcp.tool"]
        cls.internal_user = cls._create_user(
            "collection_customer_list_internal", "collection.group_collection_user"
        )
        cls.portal_user = cls._create_user(
            "collection_customer_list_portal", "base.group_portal"
        )
        cls.public_user = cls._create_user(
            "collection_customer_list_public", "base.group_public"
        )
        cls.seller = create_internal_seller(cls.env, "collection_customer_list_seller")

    def setUp(self):
        super().setUp()
        install_test_connector_type(self)
        self.connector = self.env["collection.connector"].create(
            {
                "name": "MCP Customer Connector",
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
        """Run list_collection_customers in-process and return decoded JSON."""
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

    def test_list_collection_customers_discovered_as_method_read_mcp(self):
        """list_collection_customers is method-discovered read/mcp; no DB row."""
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
            "list_collection_customers must not have a DB muk_mcp.tool row",
        )
        schema = by_name[TOOL_NAME]["inputSchema"]
        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["required"], ["seller_id"])
        self.assertEqual(schema["properties"]["seller_id"]["type"], "integer")

    def test_success_returns_normalized_customers_without_source(self):
        """Enabled bound seller MUST return active customers and omit source."""
        before_partners = self.env["res.partner"].search_count([])
        result = self._call({"seller_id": self.seller.id})
        self.assertEqual(set(result), {"customers"})
        self.assertNotIn("source", result)
        customers = result["customers"]
        self.assertEqual(
            [row["external_customer_id"] for row in customers],
            ["cust-bound-active"],
        )
        row = customers[0]
        self.assertEqual(row["name"], "Bound Active Customer")
        self.assertEqual(row["identification"], "20-11111111-1")
        self.assertEqual(row["customer_code"], "C-BOUND-1")
        self.assertEqual(
            set(row),
            {
                "external_customer_id",
                "name",
                "identification",
                "customer_code",
            },
        )
        self.assertEqual(self.env["res.partner"].search_count([]), before_partners)

    def test_portal_and_public_callers_denied_access_error(self):
        """Portal and public callers MUST receive AccessError."""
        self.assertTrue(self.portal_user.share)
        self.assertTrue(self.public_user.share)
        for user in (self.portal_user, self.public_user):
            with self.subTest(login=user.login):
                with self.assertRaises(AccessError):
                    self._call({"seller_id": self.seller.id}, user=user)

    def test_non_enabled_seller_fails_closed(self):
        """Seller absent from enabled_seller_ids MUST raise UserError."""
        other = create_internal_seller(self.env, "collection_customer_list_not_enabled")
        self.env["collection.connector.seller.binding"].create(
            {
                "connector_id": self.connector.id,
                "external_seller_id": "ext-unbound",
                "user_id": other.id,
            }
        )
        self.assertNotIn(other, self.env.company.enabled_seller_ids)
        self._assert_user_error_no_leak(lambda: self._call({"seller_id": other.id}))

    def test_unbound_enabled_seller_fails_closed(self):
        """Enabled seller without a connector binding MUST raise UserError."""
        extra = create_internal_seller(self.env, "collection_customer_list_unbound")
        ensure_enabled_seller(self.env, extra)
        self._assert_user_error_no_leak(lambda: self._call({"seller_id": extra.id}))

    def test_missing_connector_fails_closed(self):
        """Missing active connector MUST raise UserError with no leak."""
        self.env.company.write({"collection_connector_id": False})
        self._assert_user_error_no_leak(
            lambda: self._call({"seller_id": self.seller.id})
        )

    def test_inactive_connector_fails_closed(self):
        """Inactive company connector MUST raise UserError with no leak."""
        self.connector.active = False
        self._assert_user_error_no_leak(
            lambda: self._call({"seller_id": self.seller.id})
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
        other_company = self._create_company("MCP Customer Other Co")
        other_connector = (
            self.env["collection.connector"]
            .with_company(other_company)
            .create(
                {
                    "name": "MCP Customer Other Connector",
                    "type": TEST_CONNECTOR_TYPE,
                    "company_id": other_company.id,
                }
            )
        )
        other_company.write({"collection_connector_id": other_connector.id})
        result = self._call({"seller_id": self.seller.id})
        self.assertNotIn("source", result)
        self.assertEqual(
            [row["external_customer_id"] for row in result["customers"]],
            ["cust-bound-active"],
        )
        self.assertNotEqual(other_connector.id, self.connector.id)

    def test_customer_list_source_omits_sudo(self):
        """tools/customer_list.py MUST NOT use sudo."""
        source_path = Path(__file__).resolve().parents[1] / "tools" / "customer_list.py"
        self.assertTrue(source_path.is_file(), source_path)
        source = source_path.read_text(encoding="utf-8")
        code = "\n".join(
            line for line in source.splitlines() if not line.lstrip().startswith("#")
        )
        self.assertNotIn(".sudo(", code)
        self.assertNotIn("sudo()", code)

        mixin = self.env["muk_mcp.mixin"]
        method = getattr(type(mixin), "list_collection_customers", None)
        self.assertTrue(
            callable(method), "muk_mcp.mixin must expose list_collection_customers"
        )
        method_code = "\n".join(
            line
            for line in inspect.getsource(method).splitlines()
            if not line.lstrip().startswith("#")
        )
        self.assertNotIn(".sudo(", method_code)
        self.assertNotIn("sudo()", method_code)
