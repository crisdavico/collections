# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re
from pathlib import Path

from psycopg2 import IntegrityError

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from .common_connector import TEST_CONNECTOR_TYPE, install_test_connector_type
from .test_collection_payment import create_internal_seller, ensure_enabled_seller

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


class TestCollectionConnector(TransactionCase):
    """Dispatcher allowlist and seller-binding uniqueness."""

    def _assert_user_error_no_leak(self, func):
        with self.assertRaises(UserError) as ctx:
            func()
        message = str(ctx.exception)
        for token in _LEAK_TOKENS:
            self.assertNotIn(token, message)
        return ctx.exception

    def _partner_has_autopost_bills_column(self):
        self.env.cr.execute(
            """
            SELECT 1
              FROM information_schema.columns
             WHERE table_name = 'res_partner'
               AND column_name = 'autopost_bills'
            """
        )
        return bool(self.env.cr.fetchone())

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

    def test_dispatch_unknown_op_raises_user_error(self):
        """Unknown dispatcher op MUST raise UserError with no path/SQL leak."""
        connector = self.env["collection.connector"].create(
            {"name": "Dispatch Unknown Op"}
        )
        self.assertTrue(connector.id)
        self._assert_user_error_no_leak(lambda: connector._dispatch("not_an_operation"))

    def test_dispatch_another_unknown_op_raises_user_error(self):
        """Triangulation: a different unknown op MUST also fail closed."""
        connector = self.env["collection.connector"].create(
            {"name": "Dispatch Gadget Op"}
        )
        self._assert_user_error_no_leak(lambda: connector._dispatch("__class__"))

    def test_dispatch_allowed_op_without_type_raises_user_error(self):
        """Allowlisted op with empty type MUST fail closed (misconfigured)."""
        connector = self.env["collection.connector"].create(
            {"name": "Dispatch Empty Type"}
        )
        self.assertFalse(connector.type)
        self._assert_user_error_no_leak(lambda: connector._dispatch("list_sellers"))
        self._assert_user_error_no_leak(lambda: connector._dispatch("test_connection"))
        self._assert_user_error_no_leak(
            lambda: connector._dispatch("list_customers", "ext-bound")
        )
        self._assert_user_error_no_leak(
            lambda: connector._dispatch(
                "get_customer_debt", "ext-bound", "20-11111111-1"
            )
        )

    def test_test_connection_returns_success_notification(self):
        """Successful connection-test MUST return a success client notification."""
        install_test_connector_type(self)
        connector = self.env["collection.connector"].create(
            {
                "name": "Notify Connection",
                "type": TEST_CONNECTOR_TYPE,
            }
        )
        action = connector.test_connection()
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "display_notification")
        params = action["params"]
        self.assertEqual(params["type"], "success")
        title = str(params["title"])
        message = str(params["message"])
        self.assertTrue(title)
        self.assertTrue(message)
        for token in _LEAK_TOKENS:
            self.assertNotIn(token, title)
            self.assertNotIn(token, message)

    def test_binding_reuse_external_seller_id_rejected(self):
        """Second binding on C that reuses external id E MUST be rejected."""
        user_u = create_internal_seller(self.env, "bind_user_u")
        user_v = create_internal_seller(self.env, "bind_user_v")
        connector = self.env["collection.connector"].create({"name": "Bind C"})
        Binding = self.env["collection.connector.seller.binding"]
        first = Binding.create(
            {
                "connector_id": connector.id,
                "external_seller_id": "E",
                "user_id": user_u.id,
            }
        )
        self.assertEqual(first.external_seller_id, "E")
        self.assertEqual(first.user_id, user_u)
        self.assertEqual(first.company_id, connector.company_id)
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                Binding.create(
                    {
                        "connector_id": connector.id,
                        "external_seller_id": "E",
                        "user_id": user_v.id,
                    }
                )

    def test_binding_reuse_user_rejected(self):
        """Triangulation: second binding on C that reuses user U MUST be rejected."""
        user_u = create_internal_seller(self.env, "bind_reuse_u")
        user_v = create_internal_seller(self.env, "bind_reuse_v")
        connector = self.env["collection.connector"].create({"name": "Bind Reuse U"})
        Binding = self.env["collection.connector.seller.binding"]
        Binding.create(
            {
                "connector_id": connector.id,
                "external_seller_id": "E",
                "user_id": user_u.id,
            }
        )
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                Binding.create(
                    {
                        "connector_id": connector.id,
                        "external_seller_id": "E-other",
                        "user_id": user_u.id,
                    }
                )
        second = Binding.create(
            {
                "connector_id": connector.id,
                "external_seller_id": "E-other",
                "user_id": user_v.id,
            }
        )
        self.assertEqual(second.external_seller_id, "E-other")
        self.assertEqual(second.user_id, user_v)

    def test_binding_other_company_rejected(self):
        """Second binding on C that uses another company MUST be rejected."""
        user_u = create_internal_seller(self.env, "bind_co_u")
        user_v = create_internal_seller(self.env, "bind_co_v")
        connector = self.env["collection.connector"].create({"name": "Bind Co A"})
        Binding = self.env["collection.connector.seller.binding"]
        Binding.create(
            {
                "connector_id": connector.id,
                "external_seller_id": "E",
                "user_id": user_u.id,
            }
        )
        company_b = self._create_company("Binding Other Co")
        self.assertNotEqual(company_b, connector.company_id)
        with self.assertRaises(UserError):
            Binding.create(
                {
                    "connector_id": connector.id,
                    "external_seller_id": "E-b",
                    "user_id": user_v.id,
                    "company_id": company_b.id,
                }
            )

    def test_list_sellers_shape_bound_unbound_inactive_omitted(self):
        """Active bound/unbound rows + source; inactive externals omitted."""
        install_test_connector_type(self)
        connector = self.env["collection.connector"].create(
            {"name": "Shape Connector", "type": TEST_CONNECTOR_TYPE}
        )
        bound_user = create_internal_seller(self.env, "list_bound_seller")
        self.env["collection.connector.seller.binding"].create(
            {
                "connector_id": connector.id,
                "external_seller_id": "ext-bound",
                "user_id": bound_user.id,
            }
        )
        result = connector.list_sellers()
        sellers = result["sellers"]
        self.assertGreater(len(sellers), 0)
        by_ext = {row["external_seller_id"]: row for row in sellers}
        self.assertIn("ext-bound", by_ext)
        self.assertIn("ext-unbound", by_ext)
        self.assertNotIn("ext-inactive", by_ext)
        bound = by_ext["ext-bound"]
        self.assertEqual(bound["name"], "Bound Seller")
        self.assertEqual(bound["mobile"], "5491111111111")
        self.assertTrue(bound["active"])
        self.assertEqual(bound["odoo_seller_id"], bound_user.id)
        unbound = by_ext["ext-unbound"]
        self.assertEqual(unbound["name"], "Unbound Seller")
        self.assertIsNone(unbound["odoo_seller_id"])
        self.assertIsInstance(bound["commission_percent"], float)
        self.assertEqual(bound["commission_percent"], 5.0)
        self.assertIsInstance(unbound["commission_percent"], float)
        self.assertEqual(unbound["commission_percent"], 7.5)
        source = result["source"]
        self.assertEqual(source["connector_id"], connector.id)
        self.assertEqual(source["connector_type"], TEST_CONNECTOR_TYPE)
        self.assertEqual(source["connector_name"], connector.name)
        self.assertEqual(source["company_id"], self.env.company.id)

    def test_list_sellers_missing_commission_percent_coerces_to_zero(self):
        """Active adapter rows without commission_percent MUST list 0.0."""
        install_test_connector_type(self)
        connector = self.env["collection.connector"].create(
            {"name": "Missing Rate Connector", "type": TEST_CONNECTOR_TYPE}
        )
        rows = (
            {
                "id": "ext-missing-rate",
                "name": "Missing Rate Seller",
                "mobile": "5491144444444",
                "active": 1,
            },
            {
                "id": "ext-inactive-missing",
                "name": "Inactive Missing Rate",
                "mobile": "5491155555555",
                "active": 0,
            },
        )
        result = connector.with_context(collection_test_sellers=rows).list_sellers()
        sellers = result["sellers"]
        self.assertGreater(len(sellers), 0)
        by_ext = {row["external_seller_id"]: row for row in sellers}
        self.assertIn("ext-missing-rate", by_ext)
        self.assertNotIn("ext-inactive-missing", by_ext)
        self.assertIsInstance(by_ext["ext-missing-rate"]["commission_percent"], float)
        self.assertEqual(by_ext["ext-missing-rate"]["commission_percent"], 0.0)

    def test_binding_commission_percent_below_zero_rejected(self):
        """CHECK MUST reject commission_percent below 0."""
        user_u = create_internal_seller(self.env, "bind_rate_low")
        connector = self.env["collection.connector"].create({"name": "Bind Rate Low"})
        Binding = self.env["collection.connector.seller.binding"]
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                Binding.create(
                    {
                        "connector_id": connector.id,
                        "external_seller_id": "E",
                        "user_id": user_u.id,
                        "commission_percent": -1.0,
                    }
                )

    def test_binding_commission_percent_above_100_rejected(self):
        """Triangulation: CHECK MUST reject commission_percent above 100."""
        user_u = create_internal_seller(self.env, "bind_rate_high")
        connector = self.env["collection.connector"].create({"name": "Bind Rate High"})
        Binding = self.env["collection.connector.seller.binding"]
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                Binding.create(
                    {
                        "connector_id": connector.id,
                        "external_seller_id": "E",
                        "user_id": user_u.id,
                        "commission_percent": 101.0,
                    }
                )

    def test_binding_commission_percent_write_out_of_range_rejected(self):
        """A later write of commission_percent outside 0–100 MUST be rejected."""
        user_u = create_internal_seller(self.env, "bind_rate_write")
        connector = self.env["collection.connector"].create({"name": "Bind Rate Write"})
        Binding = self.env["collection.connector.seller.binding"]
        binding = Binding.create(
            {
                "connector_id": connector.id,
                "external_seller_id": "E",
                "user_id": user_u.id,
                "commission_percent": 5.0,
            }
        )
        self.assertEqual(binding.commission_percent, 5.0)
        for rate in (-1.0, 101.0):
            with self.subTest(rate=rate):
                with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
                    with self.env.cr.savepoint():
                        binding.write({"commission_percent": rate})

    def test_listed_seller_still_fails_assert_new_work(self):
        """Connector list is not collect permission until Import enables them."""
        install_test_connector_type(self)
        connector = self.env["collection.connector"].create(
            {"name": "No Collect Connector", "type": TEST_CONNECTOR_TYPE}
        )
        bound_user = create_internal_seller(self.env, "list_not_enabled_seller")
        self.env["collection.connector.seller.binding"].create(
            {
                "connector_id": connector.id,
                "external_seller_id": "ext-bound",
                "user_id": bound_user.id,
            }
        )
        self.env.company.write({"enabled_seller_ids": [Command.clear()]})
        self.assertNotIn(bound_user, self.env.company.enabled_seller_ids)
        result = connector.list_sellers()
        listed_ids = [row["odoo_seller_id"] for row in result["sellers"]]
        self.assertIn(bound_user.id, listed_ids)
        with self.assertRaises(UserError):
            self.env.company._assert_new_work(bound_user)

    def _bind_enabled_seller(self, connector, user, external_seller_id):
        ensure_enabled_seller(self.env, user)
        return self.env["collection.connector.seller.binding"].create(
            {
                "connector_id": connector.id,
                "external_seller_id": external_seller_id,
                "user_id": user.id,
            }
        )

    def test_list_customers_shape_active_only_with_source(self):
        """Active bound-seller customers + source; inactive/other sellers omitted."""
        install_test_connector_type(self)
        connector = self.env["collection.connector"].create(
            {"name": "Customer Shape Connector", "type": TEST_CONNECTOR_TYPE}
        )
        bound_user = create_internal_seller(self.env, "cust_list_bound_seller")
        self._bind_enabled_seller(connector, bound_user, "ext-bound")
        before_partners = self.env["res.partner"].search_count([])

        result = connector.list_customers(bound_user.id)

        customers = result["customers"]
        by_ext = {row["external_customer_id"]: row for row in customers}
        self.assertEqual(list(by_ext), ["cust-bound-active"])
        row = by_ext["cust-bound-active"]
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
        source = result["source"]
        self.assertEqual(source["connector_id"], connector.id)
        self.assertEqual(source["connector_type"], TEST_CONNECTOR_TYPE)
        self.assertEqual(source["connector_name"], connector.name)
        self.assertEqual(source["company_id"], self.env.company.id)
        self.assertEqual(self.env["res.partner"].search_count([]), before_partners)

    def test_list_customers_forwards_external_seller_id_not_odoo_id(self):
        """Adapter MUST receive the bound external id, not the internal user id."""
        install_test_connector_type(self)
        connector = self.env["collection.connector"].create(
            {"name": "Customer Dispatch Connector", "type": TEST_CONNECTOR_TYPE}
        )
        bound_user = create_internal_seller(self.env, "cust_list_dispatch_seller")
        self._bind_enabled_seller(connector, bound_user, "ext-bound")
        self.assertNotEqual(str(bound_user.id), "ext-bound")

        result = connector.list_customers(bound_user.id)

        ids = [row["external_customer_id"] for row in result["customers"]]
        self.assertEqual(ids, ["cust-bound-active"])
        self.assertNotIn("cust-unbound-active", ids)

    def test_list_customers_rejects_non_enabled_and_unbound_sellers(self):
        """Non-enabled or unbound sellers MUST fail closed with no leak."""
        install_test_connector_type(self)
        connector = self.env["collection.connector"].create(
            {"name": "Customer Auth Connector", "type": TEST_CONNECTOR_TYPE}
        )
        unbound = create_internal_seller(self.env, "cust_list_unbound_seller")
        ensure_enabled_seller(self.env, unbound)
        enabled_unbound_err = self._assert_user_error_no_leak(
            lambda: connector.list_customers(unbound.id)
        )
        self.assertTrue(str(enabled_unbound_err))

        bound_disabled = create_internal_seller(self.env, "cust_list_disabled_seller")
        self.env["collection.connector.seller.binding"].create(
            {
                "connector_id": connector.id,
                "external_seller_id": "ext-bound",
                "user_id": bound_disabled.id,
            }
        )
        self.env.company.write({"enabled_seller_ids": [Command.clear()]})
        self.assertNotIn(bound_disabled, self.env.company.enabled_seller_ids)
        self._assert_user_error_no_leak(
            lambda: connector.list_customers(bound_disabled.id)
        )

    def test_list_customers_uses_current_company_connector(self):
        """env.company A's connector MUST be used; company B MUST NOT leak in."""
        install_test_connector_type(self)
        connector_a = self.env["collection.connector"].create(
            {"name": "Customer Co A", "type": TEST_CONNECTOR_TYPE}
        )
        company_b = self._create_company("Customer Other Co")
        connector_b = (
            self.env["collection.connector"]
            .with_company(company_b)
            .create(
                {
                    "name": "Customer Co B",
                    "type": TEST_CONNECTOR_TYPE,
                    "company_id": company_b.id,
                }
            )
        )
        seller = create_internal_seller(self.env, "cust_list_company_seller")
        self._bind_enabled_seller(connector_a, seller, "ext-bound")
        self.env["collection.connector.seller.binding"].create(
            {
                "connector_id": connector_b.id,
                "external_seller_id": "ext-unbound",
                "user_id": create_internal_seller(
                    self.env, "cust_list_company_b_seller"
                ).id,
            }
        )
        self.env.company.write({"collection_connector_id": connector_a.id})
        company_b.write({"collection_connector_id": connector_b.id})

        result = connector_a.list_customers(seller.id)

        self.assertEqual(result["source"]["connector_id"], connector_a.id)
        self.assertEqual(result["source"]["company_id"], self.env.company.id)
        self.assertNotEqual(result["source"]["connector_id"], connector_b.id)
        self.assertEqual(
            [row["external_customer_id"] for row in result["customers"]],
            ["cust-bound-active"],
        )

    def test_collection_addon_has_no_sqlite_customer_implementation(self):
        """collection MUST NOT contain SQLite import, connection, path, or SQL."""
        root = Path(__file__).resolve().parents[1]
        sqlite_import = re.compile(
            r"^\s*(?:import sqlite3|from sqlite3\b)", re.MULTILINE
        )
        customer_sql = re.compile(
            r"\b(?:FROM|INTO|TABLE|JOIN)\s+(?:customers|invoices)\b"
            r"|\bPRAGMA table_info\(\s*(?:customers|invoices)\s*\)",
            re.IGNORECASE,
        )
        impl_files = [
            *(root / "models").glob("**/*.py"),
            *(root / "tools").glob("**/*.py"),
        ]
        for path in impl_files:
            source = path.read_text(encoding="utf-8")
            self.assertIsNone(
                sqlite_import.search(source),
                f"{path} MUST NOT import sqlite3",
            )
            self.assertNotIn("sqlite3.connect", source)
            self.assertIsNone(
                customer_sql.search(source),
                f"{path} MUST NOT contain customers or invoices SQL",
            )
            self.assertNotIn("file:%s?mode=ro", source)
            self.assertNotIn("mode=ro", source)

    def test_get_customer_debt_shape_outstanding_only_with_source(self):
        """Active customer debt + source; paid/zero-balance invoices omitted."""
        install_test_connector_type(self)
        connector = self.env["collection.connector"].create(
            {"name": "Debt Shape Connector", "type": TEST_CONNECTOR_TYPE}
        )
        bound_user = create_internal_seller(self.env, "cust_debt_bound_seller")
        self._bind_enabled_seller(connector, bound_user, "ext-bound")
        before_partners = self.env["res.partner"].search_count([])

        result = connector.get_customer_debt(bound_user.id, "20-11111111-1")

        customer = result["customer"]
        self.assertEqual(customer["external_customer_id"], "cust-bound-active")
        self.assertEqual(customer["name"], "Bound Active Customer")
        self.assertEqual(customer["identification"], "20-11111111-1")
        self.assertEqual(customer["customer_code"], "C-BOUND-1")
        self.assertEqual(
            set(customer),
            {
                "external_customer_id",
                "name",
                "identification",
                "customer_code",
            },
        )
        invoices = result["invoices"]
        self.assertEqual(
            [row["external_invoice_id"] for row in invoices],
            ["inv-bound-overdue", "inv-bound-open"],
        )
        self.assertEqual(invoices[0]["number"], "A-0001")
        self.assertEqual(invoices[0]["issue_date"], "2026-01-10")
        self.assertEqual(invoices[0]["due_date"], "2026-03-10")
        self.assertEqual(invoices[0]["amount"], 100.0)
        self.assertEqual(invoices[0]["balance"], 100.0)
        self.assertEqual(invoices[0]["state"], "overdue")
        self.assertEqual(invoices[1]["state"], "open")
        self.assertEqual(invoices[1]["balance"], 50.0)
        self.assertEqual(
            set(invoices[0]),
            {
                "external_invoice_id",
                "number",
                "issue_date",
                "due_date",
                "amount",
                "balance",
                "state",
            },
        )
        summary = result["summary"]
        self.assertEqual(summary["total_balance"], 150.0)
        self.assertEqual(summary["overdue_balance"], 100.0)
        self.assertEqual(summary["open_balance"], 50.0)
        self.assertEqual(summary["invoice_count"], 2)
        self.assertEqual(
            set(summary),
            {
                "total_balance",
                "overdue_balance",
                "open_balance",
                "invoice_count",
            },
        )
        source = result["source"]
        self.assertEqual(source["connector_id"], connector.id)
        self.assertEqual(source["connector_type"], TEST_CONNECTOR_TYPE)
        self.assertEqual(source["connector_name"], connector.name)
        self.assertEqual(source["company_id"], self.env.company.id)
        self.assertEqual(self.env["res.partner"].search_count([]), before_partners)

    def test_get_customer_debt_zero_debt_succeeds(self):
        """Active customer with no outstanding invoices MUST return zeros."""
        install_test_connector_type(self)
        connector = self.env["collection.connector"].create(
            {"name": "Debt Zero Connector", "type": TEST_CONNECTOR_TYPE}
        )
        bound_user = create_internal_seller(self.env, "cust_debt_zero_seller")
        self._bind_enabled_seller(connector, bound_user, "ext-bound")
        result = connector.with_context(collection_test_invoices=()).get_customer_debt(
            bound_user.id, "20-11111111-1"
        )
        self.assertEqual(
            result["customer"]["external_customer_id"], "cust-bound-active"
        )
        self.assertEqual(result["invoices"], [])
        self.assertEqual(result["summary"]["total_balance"], 0.0)
        self.assertEqual(result["summary"]["overdue_balance"], 0.0)
        self.assertEqual(result["summary"]["open_balance"], 0.0)
        self.assertEqual(result["summary"]["invoice_count"], 0)

    def test_get_customer_debt_forwards_external_seller_id_not_odoo_id(self):
        """Adapter MUST receive the bound external id, not the internal user id."""
        install_test_connector_type(self)
        connector = self.env["collection.connector"].create(
            {"name": "Debt Dispatch Connector", "type": TEST_CONNECTOR_TYPE}
        )
        bound_user = create_internal_seller(self.env, "cust_debt_dispatch_seller")
        self._bind_enabled_seller(connector, bound_user, "ext-bound")
        self.assertNotEqual(str(bound_user.id), "ext-bound")

        result = connector.get_customer_debt(bound_user.id, "20-11111111-1")

        self.assertEqual(
            result["customer"]["external_customer_id"], "cust-bound-active"
        )
        ids = [row["external_invoice_id"] for row in result["invoices"]]
        self.assertNotIn("inv-unbound-open", ids)

    def test_get_customer_debt_rejects_unknown_inactive_and_other_seller(self):
        """Unknown, inactive, and other-seller customers MUST fail closed."""
        install_test_connector_type(self)
        connector = self.env["collection.connector"].create(
            {"name": "Debt Reject Connector", "type": TEST_CONNECTOR_TYPE}
        )
        bound_user = create_internal_seller(self.env, "cust_debt_reject_seller")
        self._bind_enabled_seller(connector, bound_user, "ext-bound")
        for identification in (
            "99-99999999-9",
            "20-22222222-2",
            "20-33333333-3",
            "",
            "   ",
        ):
            with self.subTest(identification=identification):
                self._assert_user_error_no_leak(
                    lambda ident=identification: connector.get_customer_debt(
                        bound_user.id, ident
                    )
                )

    def test_get_customer_debt_rejects_non_enabled_and_unbound_sellers(self):
        """Non-enabled or unbound sellers MUST fail closed with no leak."""
        install_test_connector_type(self)
        connector = self.env["collection.connector"].create(
            {"name": "Debt Auth Connector", "type": TEST_CONNECTOR_TYPE}
        )
        unbound = create_internal_seller(self.env, "cust_debt_unbound_seller")
        ensure_enabled_seller(self.env, unbound)
        self._assert_user_error_no_leak(
            lambda: connector.get_customer_debt(unbound.id, "20-11111111-1")
        )

        bound_disabled = create_internal_seller(self.env, "cust_debt_disabled_seller")
        self.env["collection.connector.seller.binding"].create(
            {
                "connector_id": connector.id,
                "external_seller_id": "ext-bound",
                "user_id": bound_disabled.id,
            }
        )
        self.env.company.write({"enabled_seller_ids": [Command.clear()]})
        self.assertNotIn(bound_disabled, self.env.company.enabled_seller_ids)
        self._assert_user_error_no_leak(
            lambda: connector.get_customer_debt(bound_disabled.id, "20-11111111-1")
        )

    def test_get_customer_debt_uses_current_company_connector(self):
        """env.company A's connector MUST be used; company B MUST NOT leak in."""
        install_test_connector_type(self)
        connector_a = self.env["collection.connector"].create(
            {"name": "Debt Co A", "type": TEST_CONNECTOR_TYPE}
        )
        company_b = self._create_company("Debt Other Co")
        connector_b = (
            self.env["collection.connector"]
            .with_company(company_b)
            .create(
                {
                    "name": "Debt Co B",
                    "type": TEST_CONNECTOR_TYPE,
                    "company_id": company_b.id,
                }
            )
        )
        seller = create_internal_seller(self.env, "cust_debt_company_seller")
        self._bind_enabled_seller(connector_a, seller, "ext-bound")
        self.env["collection.connector.seller.binding"].create(
            {
                "connector_id": connector_b.id,
                "external_seller_id": "ext-unbound",
                "user_id": create_internal_seller(
                    self.env, "cust_debt_company_b_seller"
                ).id,
            }
        )
        self.env.company.write({"collection_connector_id": connector_a.id})
        company_b.write({"collection_connector_id": connector_b.id})

        result = connector_a.get_customer_debt(seller.id, "20-11111111-1")

        self.assertEqual(result["source"]["connector_id"], connector_a.id)
        self.assertEqual(result["source"]["company_id"], self.env.company.id)
        self.assertNotEqual(result["source"]["connector_id"], connector_b.id)
        self.assertEqual(
            result["customer"]["external_customer_id"], "cust-bound-active"
        )
