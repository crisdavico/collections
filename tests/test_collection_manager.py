# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged

# Connector settings that carry credentials or reach the network: admins only.
SYSTEM_SETTING_FIELDS = (
    "sqlite_path",
    "bejerman_ws_url",
    "bejerman_usuario",
    "bejerman_clave",
    "bejerman_allow_insecure",
    "bejerman_ca_bundle",
)
STORED_BEJERMAN_SETTINGS = {
    "bejerman_ws_url": "https://erp.example.com/ws",
    "bejerman_usuario": "erp-user",
    "bejerman_clave": "stored-secret",
    "bejerman_allow_insecure": False,
    "bejerman_ca_bundle": "/srv/ca.pem",
    "bejerman_empresa": "old-company",
}
FORGED_SYSTEM_SETTINGS = {
    "sqlite_path": "/etc/passwd",
    "bejerman_ws_url": "http://attacker.example.com/ws",
    "bejerman_usuario": "attacker",
    "bejerman_clave": "attacker-secret",
    "bejerman_allow_insecure": True,
    "bejerman_ca_bundle": "/tmp/attacker.pem",
}


@tagged("post_install", "-at_install")
class TestCollectionManager(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Manager company"})
        cls.other = cls.env.company
        cls.manager = (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Collections manager",
                    "login": "test_collections_manager",
                    "company_id": cls.company.id,
                    "company_ids": [Command.set(cls.company.ids)],
                    "group_ids": [
                        Command.set(
                            [cls.env.ref("collection.group_collection_manager").id]
                        )
                    ],
                }
            )
        )
        cls.company.enabled_seller_ids = cls.manager
        cls.ctx = {"allowed_company_ids": cls.company.ids}

    def _settings(self, **vals):
        return (
            self.env["collection.company.settings"]
            .with_user(self.manager)
            .with_context(**self.ctx)
            .create({"company_id": self.company.id, **vals})
        )

    def test_manager_settings_without_system_access(self):
        self.assertFalse(self.manager.has_group("base.group_system"))
        settings = self._settings()
        settings.auto_create_sheet = False
        settings.document_review_enabled = True
        settings.action_save()
        self.assertFalse(self.company.auto_create_sheet)
        self.assertTrue(self.company.document_review_enabled)
        with self.assertRaises(AccessError):
            self.company.with_user(self.manager).write({"name": "Forbidden"})
        with self.assertRaises(AccessError):
            self.manager.with_user(self.manager).write(
                {"company_ids": [Command.link(self.other.id)]}
            )

    def test_settings_reject_other_company_and_seller(self):
        with self.assertRaises(AccessError):
            self._settings(company_id=self.other.id).action_save()
        other_user = self.manager.copy(
            {
                "login": "other_only_collection_user",
                "company_id": self.other.id,
                "company_ids": [Command.set(self.other.ids)],
            }
        )
        with self.assertRaises(UserError):
            self._settings(
                enabled_seller_ids=[Command.set(other_user.ids)]
            ).action_save()

    def test_connector_settings_reject_other_company(self):
        connector = self.env["collection.connector"].create(
            {"name": "Private source", "company_id": self.other.id}
        )
        with self.assertRaises(AccessError):
            connector.with_user(self.manager).with_context(
                **self.ctx
            ).action_collection_connector_settings()

    def _bejerman_connector(self):
        Connector = self.env["collection.connector"]
        if "bejerman_clave" not in Connector._fields:
            self.skipTest("Bejerman adapter is not installed")
        return Connector.create(
            {
                "name": "Company service",
                "company_id": self.company.id,
                "type": "bejerman",
                **STORED_BEJERMAN_SETTINGS,
            }
        )

    def _connector_admin(self):
        return self.manager.copy(
            {
                "login": "collections_connector_admin",
                "group_ids": [
                    Command.set(
                        [
                            self.env.ref("collection.group_collection_manager").id,
                            self.env.ref("base.group_system").id,
                        ]
                    )
                ],
            }
        )

    def test_connector_form_is_the_only_settings_interface(self):
        Connector = self.env["collection.connector"].with_user(self.manager)
        arch = etree.fromstring(Connector.get_view(view_type="form")["arch"])
        self.assertFalse(
            arch.xpath("//button[@name='action_collection_connector_settings']")
        )
        self.assertEqual(len(arch.xpath("//button[@name='test_connection']")), 1)
        self.assertNotIn("collection.connector.settings", self.env.registry)
        self.assertFalse(
            self.env.ref(
                "collection.view_collection_connector_settings_form",
                raise_if_not_found=False,
            )
        )

    def test_manager_connector_form_never_returns_system_settings(self):
        connector = self._bejerman_connector()
        managed = connector.with_user(self.manager).with_context(**self.ctx)
        names = managed.fields_get()
        arch = managed.get_view(view_type="form")["arch"]
        for name in SYSTEM_SETTING_FIELDS:
            if name not in connector._fields:
                continue
            with self.subTest(field=name):
                self.assertNotIn(name, names)
                self.assertNotIn(f'name="{name}"', arch)
                with self.assertRaises(AccessError):
                    managed.read([name])
                with self.assertRaises(AccessError):
                    managed.write({name: FORGED_SYSTEM_SETTINGS[name]})
                with self.assertRaises(AccessError), self.cr.savepoint():
                    managed.create(
                        {"name": "Forged connector", name: FORGED_SYSTEM_SETTINGS[name]}
                    )

    def test_manager_saves_connector_without_touching_system_settings(self):
        connector = self._bejerman_connector()
        managed = connector.with_user(self.manager).with_context(**self.ctx)
        self.assertEqual(
            managed.read(["bejerman_empresa"])[0]["bejerman_empresa"], "old-company"
        )
        managed.write({"bejerman_empresa": "new-company", "bejerman_timeout": 90})
        self.assertEqual(connector.bejerman_empresa, "new-company")
        for name, value in STORED_BEJERMAN_SETTINGS.items():
            if name != "bejerman_empresa":
                self.assertEqual(connector[name], value)
        with patch.object(type(connector), "_bejerman_refresh_snapshot") as refresh:
            managed.action_bejerman_refresh_snapshot()
        refresh.assert_called_once()
        foreign = connector.copy({"company_id": self.other.id})
        with patch.object(type(connector), "_bejerman_refresh_snapshot") as refresh:
            with self.assertRaises(AccessError):
                foreign.with_user(self.manager).with_context(
                    **self.ctx
                ).action_bejerman_refresh_snapshot()
        refresh.assert_not_called()

    def test_admin_manages_credentials_on_connector_form(self):
        connector = self._bejerman_connector()
        managed = connector.with_user(self._connector_admin()).with_context(**self.ctx)
        self.assertEqual(
            managed.read(["bejerman_clave"])[0]["bejerman_clave"], "stored-secret"
        )
        managed.write(
            {
                "bejerman_clave": "rotated-secret",
                "bejerman_ws_url": "https://erp2.example.com/ws",
                "bejerman_allow_insecure": True,
                "bejerman_ca_bundle": "/srv/new-ca.pem",
            }
        )
        self.assertEqual(connector.bejerman_clave, "rotated-secret")
        self.assertEqual(connector.bejerman_ws_url, "https://erp2.example.com/ws")
        self.assertTrue(connector.bejerman_allow_insecure)
        self.assertEqual(connector.bejerman_ca_bundle, "/srv/new-ca.pem")

    def test_bank_accounts_are_company_scoped(self):
        Bank = (
            self.env["res.partner.bank"]
            .with_user(self.manager)
            .with_context(**self.ctx)
        )
        account = Bank.create(
            {
                "acc_number": "1234567890123456",
                "partner_id": self.company.partner_id.id,
                "company_id": self.company.id,
            }
        )
        account.acc_number = "1234567890123457"
        other = self.env["res.partner.bank"].create(
            {
                "acc_number": "9876543210987654",
                "partner_id": self.other.partner_id.id,
                "company_id": self.other.id,
            }
        )
        self.assertNotIn(other.id, Bank.search([]).ids)
        with self.assertRaises(AccessError):
            Bank.browse(other.id).write({"acc_number": "forbidden"})
        with self.assertRaises(AccessError):
            Bank.create(
                {
                    "acc_number": "1122334455667788",
                    "partner_id": self.other.partner_id.id,
                }
            )
        account.unlink()

    def test_configuration_menus_are_visible(self):
        Menu = self.env["ir.ui.menu"].with_user(self.manager).with_context(**self.ctx)
        visible = Menu._visible_menu_ids()
        for xmlid in (
            "menu_collection_root",
            "menu_collection_config",
        ):
            self.assertIn(self.env.ref(f"collection.{xmlid}").id, visible)
        config = self.env.ref("collection.menu_collection_config")
        self.assertEqual(
            config.action, self.env.ref("collection.action_collection_company_settings")
        )
        self.assertFalse(Menu.search([("parent_id", "=", config.id)]))

    def test_full_settings_page_has_four_tabs_and_no_manager_secrets(self):
        Wizard = self.env["collection.company.settings"].with_user(self.manager)
        arch = etree.fromstring(Wizard.get_view(view_type="form")["arch"])
        self.assertEqual(
            arch.xpath("//notebook/page/@name"),
            ["general", "sellers", "bank_accounts", "integration"],
        )
        self.assertFalse(
            arch.xpath("//field[@name='collection_mcp_trusted_seller_header']")
        )
        self.assertEqual(
            self.env.ref("collection.action_collection_company_settings").target,
            "current",
        )

    def test_native_settings_save_persists_company_and_keeps_other_company(self):
        parameter = self.env["ir.config_parameter"].sudo()
        parameter.set_param("collection.mcp_trusted_seller_header", "X-Existing-Sender")
        Wizard = (
            self.env["collection.company.settings"]
            .with_user(self.manager)
            .with_context(**self.ctx)
        )
        other_auto = self.other.auto_create_sheet
        result = Wizard.web_save(
            {"auto_create_sheet": False, "document_review_enabled": True},
            {"company_id": {"fields": {"display_name": {}}}},
        )
        self.assertFalse(self.company.auto_create_sheet)
        self.assertTrue(self.company.document_review_enabled)
        self.assertEqual(self.other.auto_create_sheet, other_auto)
        self.assertEqual(
            parameter.get_param("collection.mcp_trusted_seller_header"),
            "X-Existing-Sender",
        )
        settings = Wizard.browse(result[0]["id"])
        settings.web_save({"auto_create_sheet": True}, {})
        self.assertTrue(self.company.auto_create_sheet)

    def test_spanish_settings_tab_labels(self):
        if not self.env["res.lang"].search_count([("code", "=", "es_AR")]):
            self.skipTest("Argentine Spanish is not installed")
        arch = (
            self.env["collection.company.settings"]
            .with_user(self.manager)
            .with_context(**self.ctx, lang="es_AR")
            .get_view(view_type="form")["arch"]
        )
        self.assertEqual(
            etree.fromstring(arch).xpath("//notebook/page/@string"),
            ["General", "Vendedores", "Cuentas bancarias", "Integración"],
        )

    def test_integration_shortcuts_use_only_settings_company(self):
        connector = self.env["collection.connector"].create(
            {"name": "Settings source", "company_id": self.company.id}
        )
        settings = self._settings(collection_connector_id=connector.id)
        action = settings.action_open_connector_settings()
        self.assertEqual(action["res_model"], "collection.connector")
        self.assertEqual(action["res_id"], connector.id)
        self.assertEqual(action["target"], "current")
        self.assertEqual(
            action["views"],
            [(self.env.ref("collection.view_collection_connector_form").id, "form")],
        )
        action = settings.action_manage_connectors()
        self.assertEqual(action["domain"], [("company_id", "=", self.company.id)])
        action = settings.action_open_bank_accounts()
        self.assertEqual(
            action["domain"], [("partner_id", "=", self.company.partner_id.id)]
        )
        with patch.object(type(connector), "test_connection", return_value={}) as test:
            settings.action_test_connection()
        test.assert_called_once()
        foreign = self.env["collection.connector"].create(
            {"name": "Foreign settings source", "company_id": self.other.id}
        )
        settings.collection_connector_id = foreign
        with self.assertRaises(AccessError):
            settings.action_open_connector_settings()

    def test_manager_cannot_read_or_forge_trusted_header(self):
        settings = self._settings()
        with self.assertRaises(AccessError):
            settings.read(["collection_mcp_trusted_seller_header"])
        with self.assertRaises(AccessError):
            settings.web_save({"collection_mcp_trusted_seller_header": "Forged"}, {})

    def test_system_admin_without_collection_role_can_configure(self):
        admin = self.manager.copy(
            {
                "login": "settings_system_admin",
                "group_ids": [Command.set([self.env.ref("base.group_system").id])],
            }
        )
        self.assertFalse(admin.has_group("collection.group_collection_manager"))
        Wizard = (
            self.env["collection.company.settings"]
            .with_user(admin)
            .with_context(**self.ctx)
        )
        Wizard.web_save({"collection_mcp_trusted_seller_header": "X-Test-Sender"}, {})
        self.assertEqual(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("collection.mcp_trusted_seller_header"),
            "X-Test-Sender",
        )
        self.assertIn(
            self.env.ref("collection.menu_collection_config").id,
            self.env["ir.ui.menu"].with_user(admin)._visible_menu_ids(),
        )

    def test_manager_connector_crud_is_company_scoped(self):
        Connector = (
            self.env["collection.connector"]
            .with_user(self.manager)
            .with_context(**self.ctx)
        )
        connector = Connector.create({"name": "Own connector"})
        connector.name = "Updated"
        other = self.env["collection.connector"].create(
            {"name": "Other connector", "company_id": self.other.id}
        )
        self.assertNotIn(other.id, Connector.search([]).ids)
        with self.assertRaises(AccessError):
            other.with_user(self.manager).with_context(**self.ctx).read(["name"])
        with self.assertRaises(AccessError), self.cr.savepoint():
            Connector.create({"name": "Forbidden", "company_id": self.other.id})
        connector.unlink()

    def test_sheet_lifecycle_and_company_isolation(self):
        Sheet = (
            self.env["collection.sheet"]
            .with_user(self.manager)
            .with_context(**self.ctx)
        )
        sheet = Sheet.create({"seller_id": self.manager.id})
        sheet.action_seller_close()
        sheet.action_confirm()
        sheet.action_close()
        self.assertEqual(sheet.state, "closed")
        with self.assertRaises(AccessError):
            Sheet.with_context(allowed_company_ids=[self.other.id]).search([])

    def test_import_creates_only_company_sellers(self):
        connector = self.env["collection.connector"].create(
            {"name": "Source", "company_id": self.company.id}
        )
        self.company.collection_connector_id = connector
        rows = [
            {
                "external_seller_id": "manager-source",
                "name": "Seller",
                "mobile": "5491188810001",
                "commission_percent": 5,
            }
        ]
        unrelated = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Other seller",
                    "login": "other_company_seller",
                    "phone": rows[0]["mobile"],
                    "company_id": self.other.id,
                    "company_ids": [Command.set(self.other.ids)],
                    "group_ids": [Command.set([self.env.ref("base.group_user").id])],
                }
            )
        )
        with patch.object(
            type(connector), "list_sellers", return_value={"sellers": rows}
        ):
            self._settings().action_import_enabled_sellers()
        # T28: Import adds sellers; it no longer replaces the enabled list.
        seller = connector.seller_binding_ids.filtered(
            lambda binding: binding.external_seller_id == "manager-source"
        ).user_id
        self.assertIn(seller, self.company.enabled_seller_ids)
        self.assertNotEqual(seller, unrelated)
        self.assertEqual(seller.company_ids, self.company)
        self.assertEqual(unrelated.company_ids, self.other)
        self.assertFalse(seller.has_group("base.group_system"))

    def test_regular_internal_user_cannot_configure(self):
        regular = self.manager.copy(
            {
                "login": "regular_collections_user",
                "group_ids": [Command.set([self.env.ref("base.group_user").id])],
            }
        )
        with self.assertRaises(AccessError):
            self._settings().with_user(regular).action_save()
