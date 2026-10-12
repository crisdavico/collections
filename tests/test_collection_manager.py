# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import patch

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
        Wizard = (
            self.env["collection.connector.settings"]
            .with_user(self.manager)
            .with_context(**self.ctx)
        )
        with self.assertRaises(AccessError):
            Wizard.with_context(default_connector_id=connector.id).default_get(
                ["connector_id", "bejerman_clave"]
            )
        with self.assertRaises(AccessError):
            Wizard.create({"connector_id": connector.id}).action_save()

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

    def _connector_wizard(self, connector, user):
        return (
            self.env["collection.connector.settings"]
            .with_user(user)
            .with_context(**self.ctx, default_connector_id=connector.id)
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

    def test_wizard_system_settings_are_admin_only_fields(self):
        """Credentials, endpoint, TLS and file path never reach a manager."""
        Wizard = self.env["collection.connector.settings"]
        for name in SYSTEM_SETTING_FIELDS:
            with self.subTest(field=name):
                self.assertEqual(Wizard._fields[name].groups, "base.group_system")
        arch = (
            Wizard.with_user(self.manager)
            .with_context(**self.ctx)
            .get_view(view_type="form")["arch"]
        )
        for name in SYSTEM_SETTING_FIELDS:
            with self.subTest(view_field=name):
                self.assertNotIn(f'name="{name}"', arch)
        connector = self.env["collection.connector"].create(
            {"name": "Forged settings", "company_id": self.company.id}
        )
        ManagerWizard = Wizard.with_user(self.manager).with_context(**self.ctx)
        for name, value in FORGED_SYSTEM_SETTINGS.items():
            with self.subTest(forged=name), self.assertRaises(AccessError):
                ManagerWizard.create({"connector_id": connector.id, name: value})

    def test_manager_wizard_never_returns_connector_credentials(self):
        connector = self._bejerman_connector()
        Wizard = self._connector_wizard(connector, self.manager)
        defaults = Wizard.default_get(list(Wizard._fields))
        for name in SYSTEM_SETTING_FIELDS:
            with self.subTest(field=name):
                self.assertNotIn(name, defaults)
        self.assertEqual(defaults["bejerman_empresa"], "old-company")

    def test_manager_saves_settings_without_touching_system_ones(self):
        connector = self._bejerman_connector()
        Wizard = self._connector_wizard(connector, self.manager)
        defaults = Wizard.default_get(list(Wizard._fields))
        defaults["bejerman_empresa"] = "new-company"
        settings = Wizard.create(defaults)
        settings.action_save()
        self.assertEqual(connector.bejerman_empresa, "new-company")
        for name, value in STORED_BEJERMAN_SETTINGS.items():
            if name == "bejerman_empresa":
                continue
            with self.subTest(field=name):
                self.assertEqual(connector[name], value)
        with self.assertRaises(AccessError):
            connector.with_user(self.manager).read(["bejerman_clave"])
        with patch.object(type(connector), "_bejerman_refresh_snapshot") as refresh:
            settings.action_refresh_snapshot()
        refresh.assert_called_once()

    def test_admin_manages_connector_credentials_through_wizard(self):
        connector = self._bejerman_connector()
        Wizard = self._connector_wizard(connector, self._connector_admin())
        defaults = Wizard.default_get(list(Wizard._fields))
        self.assertEqual(defaults["bejerman_clave"], "stored-secret")
        self.assertEqual(defaults["bejerman_ws_url"], "https://erp.example.com/ws")
        defaults.update(
            {
                "bejerman_clave": "rotated-secret",
                "bejerman_ws_url": "https://erp2.example.com/ws",
                "bejerman_allow_insecure": True,
                "bejerman_ca_bundle": "/srv/new-ca.pem",
            }
        )
        Wizard.create(defaults).action_save()
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
            "menu_collection_connector",
            "menu_collection_company_settings",
            "menu_collection_company_banks",
        ):
            self.assertIn(self.env.ref(f"collection.{xmlid}").id, visible)
        self.assertNotIn(
            self.env.ref("collection.menu_collection_settings").id, visible
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
