# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import inspect

from lxml import etree
from psycopg2 import IntegrityError

from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from .test_collection_acl import TestCollectionAcl
from .test_collection_payment import create_internal_seller

MODEL = "collection.connector.customer.binding"


class TestCollectionCustomerBinding(TransactionCase):
    """UNIQUE, company-guard, ACL 1,0,1,0, and connector notebook."""

    def _create_company(self, name):
        partner = self._create_partner(name)
        self.env.cr.execute(
            """
            INSERT INTO res_company (
                name, partner_id, currency_id,
                fiscalyear_last_day, fiscalyear_last_month,
                account_price_include, cost_method, horizon_days,
                inventory_period, layout_background, security_lead
            )
            SELECT
                %s, %s, currency_id,
                fiscalyear_last_day, fiscalyear_last_month,
                account_price_include, cost_method, horizon_days,
                inventory_period, layout_background, security_lead
            FROM res_company
            WHERE id = %s
            RETURNING id
            """,
            (name, partner.id, self.env.company.id),
        )
        company = self.env["res.company"].browse(self.env.cr.fetchone()[0])
        company.invalidate_recordset()
        return company

    def _restrict_user_to_company(self, user, company):
        return TestCollectionAcl._restrict_user_to_company(self, user, company)

    def _assert_global_company_rule(self, model_name):
        return TestCollectionAcl._assert_global_company_rule(self, model_name)

    def _assert_hidden_from_user(self, user, record, read_fields):
        return TestCollectionAcl._assert_hidden_from_user(
            self, user, record, read_fields
        )

    def _create_partner(self, name):
        Partner = self.env["res.partner"].with_context(
            tracking_disable=True,
            mail_create_nolog=True,
            mail_notrack=True,
            mail_create_nosubscribe=True,
        )
        vals = {"name": name}
        if "autopost_bills" in Partner._fields:
            vals["autopost_bills"] = "ask"
            return Partner.create(vals)
        self.env.cr.execute(
            """
            SELECT 1
              FROM information_schema.columns
             WHERE table_name = 'res_partner'
               AND column_name = 'autopost_bills'
            """
        )
        if not self.env.cr.fetchone():
            return Partner.create(vals)
        self.env.cr.execute(
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
            (name, f"{name}@example.com", name),
        )
        return Partner.browse(self.env.cr.fetchone()[0])

    def _binding_vals(self, connector, partner, **extra):
        vals = {
            "connector_id": connector.id,
            "external_customer_id": extra.pop("external_customer_id", "E"),
            "identification": extra.pop("identification", "I"),
            "partner_id": partner.id,
        }
        vals.update(extra)
        return vals

    def _create_binding(self, connector, partner, **extra):
        return self.env[MODEL].create(self._binding_vals(connector, partner, **extra))

    def test_binding_reuse_external_customer_id_rejected(self):
        """Second binding on C that reuses external id E MUST be rejected."""
        connector = self.env["collection.connector"].create({"name": "Cust Bind C"})
        partner_p = self._create_partner("Cust Bind P")
        partner_q = self._create_partner("Cust Bind Q")
        first = self._create_binding(connector, partner_p)
        self.assertEqual(first.external_customer_id, "E")
        self.assertEqual(first.identification, "I")
        self.assertEqual(first.partner_id, partner_p)
        self.assertEqual(first.company_id, connector.company_id)
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self._create_binding(
                    connector,
                    partner_q,
                    identification="I-other",
                )

    def test_binding_reuse_identification_rejected(self):
        """Triangulation: second binding on C that reuses identification I MUST fail."""
        connector = self.env["collection.connector"].create({"name": "Cust Bind Ident"})
        partner_p = self._create_partner("Cust Ident P")
        partner_q = self._create_partner("Cust Ident Q")
        self._create_binding(connector, partner_p)
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self._create_binding(
                    connector,
                    partner_q,
                    external_customer_id="E-other",
                )
        second = self._create_binding(
            connector,
            partner_q,
            external_customer_id="E-other",
            identification="I-other",
        )
        self.assertEqual(second.external_customer_id, "E-other")
        self.assertEqual(second.identification, "I-other")
        self.assertEqual(second.partner_id, partner_q)

    def test_binding_reuse_partner_rejected(self):
        """Triangulation: second binding on C that reuses partner P MUST fail."""
        connector = self.env["collection.connector"].create(
            {"name": "Cust Bind Partner"}
        )
        partner_p = self._create_partner("Cust Partner P")
        partner_q = self._create_partner("Cust Partner Q")
        self._create_binding(connector, partner_p)
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self._create_binding(
                    connector,
                    partner_p,
                    external_customer_id="E-other",
                    identification="I-other",
                )
        other = self.env["collection.connector"].create({"name": "Cust Bind C2"})
        shared = self._create_binding(other, partner_p)
        self.assertEqual(shared.connector_id, other)
        self.assertEqual(shared.partner_id, partner_p)
        self.assertEqual(shared.company_id, other.company_id)
        third = self._create_binding(
            connector,
            partner_q,
            external_customer_id="E-q",
            identification="I-q",
        )
        self.assertEqual(third.partner_id, partner_q)

    def test_binding_other_company_rejected(self):
        """Binding whose company does not match the connector MUST be rejected."""
        connector = self.env["collection.connector"].create({"name": "Cust Bind Co A"})
        partner_p = self._create_partner("Cust Co P")
        partner_q = self._create_partner("Cust Co Q")
        self._create_binding(connector, partner_p)
        company_b = self._create_company("Cust Binding Other Co")
        self.assertNotEqual(company_b, connector.company_id)
        with self.assertRaises(UserError):
            self._create_binding(
                connector,
                partner_q,
                external_customer_id="E-b",
                identification="I-b",
                company_id=company_b.id,
            )

    def test_acl_rows_user_create_system_full(self):
        """group_user 1,0,1,0; group_system 1,1,1,1; no extra groups."""
        acls = self.env["ir.model.access"].search([("model_id.model", "=", MODEL)])
        self.assertEqual(len(acls), 2)
        user_group = self.env.ref("base.group_user")
        system_group = self.env.ref("base.group_system")
        user_acl = acls.filtered(lambda acl: acl.group_id == user_group)
        system_acl = acls.filtered(lambda acl: acl.group_id == system_group)
        self.assertEqual(len(user_acl), 1)
        self.assertTrue(user_acl.perm_read)
        self.assertFalse(user_acl.perm_write)
        self.assertTrue(user_acl.perm_create)
        self.assertFalse(user_acl.perm_unlink)
        self.assertEqual(len(system_acl), 1)
        self.assertTrue(system_acl.perm_read)
        self.assertTrue(system_acl.perm_write)
        self.assertTrue(system_acl.perm_create)
        self.assertTrue(system_acl.perm_unlink)
        self.assertFalse(
            self.env["ir.model.data"].search(
                [("module", "=", "collection"), ("model", "=", "res.groups")]
            )
        )
        self._assert_global_company_rule(MODEL)
        create_source = inspect.getsource(type(self.env[MODEL]).create)
        code_lines = [
            line
            for line in create_source.splitlines()
            if not line.lstrip().startswith("#")
        ]
        code = "\n".join(code_lines)
        self.assertNotIn(".sudo(", code)
        self.assertNotIn("sudo()", code)

    def test_user_can_create_not_write_or_unlink(self):
        """Internal user MAY create a same-company binding; write/unlink denied."""
        user = create_internal_seller(self.env, "cust_bind_acl_user")
        connector = self.env["collection.connector"].create({"name": "ACL Cust Bind"})
        partner = self._create_partner("ACL Cust Partner")
        Binding = self.env[MODEL].with_user(user)
        binding = Binding.create(self._binding_vals(connector, partner))
        self.assertTrue(binding.id)
        self.assertEqual(binding.partner_id, partner)
        self.assertEqual(
            Binding.browse(binding.id).read(["identification"])[0]["identification"],
            "I",
        )
        with self.assertRaises(AccessError):
            Binding.browse(binding.id).write({"customer_code": "NOPE"})
        with self.assertRaises(AccessError):
            Binding.browse(binding.id).unlink()
        self.assertTrue(binding.exists())

    def test_other_company_bindings_hidden(self):
        """ir.rule MUST hide a customer binding in a company the user cannot access."""
        self._assert_global_company_rule(MODEL)
        user = create_internal_seller(self.env, "cust_bind_rule_user")
        self._restrict_user_to_company(user, self.env.company)
        connector_a = self.env["collection.connector"].create(
            {"name": "Cust Bind Visible"}
        )
        partner_a = self._create_partner("Cust Visible P")
        binding_a = self._create_binding(connector_a, partner_a)
        company_b = self._create_company("Cust Bind Hidden Co")
        connector_b = self.env["collection.connector"].create(
            {"name": "Cust Bind Hidden", "company_id": company_b.id}
        )
        partner_b = self._create_partner("Cust Hidden P")
        binding_b = self._create_binding(
            connector_b,
            partner_b,
            external_customer_id="E-b",
            identification="I-b",
        )
        self.assertEqual(binding_b.company_id, company_b)
        Binding = self.env[MODEL].with_user(user)
        self.assertEqual(Binding.search([("id", "=", binding_a.id)]), binding_a)
        self._assert_hidden_from_user(user, binding_b, ["identification", "id"])

    def test_connector_customer_binding_ids_and_notebook(self):
        """Connector MUST expose customer_binding_ids on a Customer Bindings page."""
        field = self.env["collection.connector"]._fields["customer_binding_ids"]
        self.assertEqual(field.type, "one2many")
        self.assertEqual(field.comodel_name, MODEL)
        self.assertEqual(field.inverse_name, "connector_id")
        connector = self.env["collection.connector"].create({"name": "Notebook Bind"})
        partner = self._create_partner("Notebook Partner")
        binding = self._create_binding(connector, partner, customer_code="C-1")
        self.assertEqual(connector.customer_binding_ids, binding)
        self.assertEqual(binding.customer_code, "C-1")
        view = self.env.ref("collection.view_collection_connector_form")
        root = etree.fromstring(view.arch)
        pages = root.xpath('//notebook/page[@string="Customer Bindings"]')
        self.assertEqual(len(pages), 1)
        names = [
            node.get("name") for node in pages[0].xpath(".//field") if node.get("name")
        ]
        self.assertIn("customer_binding_ids", names)
        self.assertIn("external_customer_id", names)
        self.assertIn("identification", names)
        self.assertIn("partner_id", names)
        self.assertIn("customer_code", names)

    def test_connector_seller_binding_notebook_readonly(self):
        """Readonly Seller Bindings page; Customer Bindings stays."""
        field = self.env["collection.connector"]._fields["seller_binding_ids"]
        self.assertEqual(field.type, "one2many")
        self.assertEqual(
            field.comodel_name,
            "collection.connector.seller.binding",
        )
        self.assertEqual(field.inverse_name, "connector_id")
        connector = self.env["collection.connector"].create(
            {"name": "Seller Notebook Bind"}
        )
        seller = create_internal_seller(self.env, "seller_notebook_user")
        binding = self.env["collection.connector.seller.binding"].create(
            {
                "connector_id": connector.id,
                "external_seller_id": "EXT-NB",
                "user_id": seller.id,
                "commission_percent": 7.5,
            }
        )
        self.assertEqual(connector.seller_binding_ids, binding)
        self.assertAlmostEqual(binding.commission_percent, 7.5)
        view = self.env.ref("collection.view_collection_connector_form")
        root = etree.fromstring(view.arch)
        customer_pages = root.xpath('//notebook/page[@string="Customer Bindings"]')
        self.assertEqual(len(customer_pages), 1)
        pages = root.xpath('//notebook/page[@string="Seller Bindings"]')
        self.assertEqual(len(pages), 1)
        names = [
            node.get("name") for node in pages[0].xpath(".//field") if node.get("name")
        ]
        self.assertIn("seller_binding_ids", names)
        self.assertIn("external_seller_id", names)
        self.assertIn("user_id", names)
        self.assertIn("commission_percent", names)
        lists = pages[0].xpath(".//list")
        self.assertEqual(len(lists), 1, "Seller Bindings must use Odoo 19 <list>")
        self.assertFalse(
            pages[0].xpath(".//tree"),
            "Seller Bindings must not use <tree>",
        )
        for name in ("external_seller_id", "user_id", "commission_percent"):
            nodes = pages[0].xpath(f'.//field[@name="{name}"]')
            self.assertEqual(len(nodes), 1, f"Seller Bindings must list {name}")
            readonly = (nodes[0].get("readonly") or "").lower()
            self.assertIn(
                readonly,
                ("1", "true"),
                f"{name} must be readonly (got {nodes[0].get('readonly')!r})",
            )
