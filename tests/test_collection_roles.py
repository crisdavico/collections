# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged

from .common_connector import (
    TEST_CONNECTOR_TYPE,
    advance_sheet_to,
    install_test_connector_type,
)
from .test_collection_payment import (
    COLLECTION_MANAGER_GROUP,
    COLLECTION_USER_GROUP,
    create_collection_user,
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
)

# Every model that holds collection data or configuration.
COLLECTION_MODELS = (
    "collection.voucher",
    "collection.sheet",
    "collection.allocation",
    "collection.allocation.line",
    "collection.allocation.debt.picker",
    "collection.allocation.debt.candidate",
    "collection.receipt",
    "collection.receipt.value",
    "collection.document.type",
    "collection.connector",
    "collection.connector.seller.binding",
    "collection.connector.customer.binding",
)
# Sheet buttons that only a Collections Manager may use.
MANAGER_SHEET_ACTIONS = ("action_close", "action_cancel", "action_reinstate")


@tagged("post_install", "-at_install")
class TestCollectionRoles(TransactionCase):
    """Users + Managers: plain internal users see no collection data."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.seller = create_internal_seller(cls.env, "roles_seller")
        cls.plain_user = create_internal_seller(cls.env, "roles_plain")
        cls.collection_user = create_collection_user(cls.env, "roles_operator")
        cls.manager = create_collection_user(cls.env, "roles_manager", manager=True)
        ensure_enabled_seller(cls.env, cls.seller)

    def _sheet(self, state="open"):
        sheet = self.env["collection.sheet"].create({"seller_id": self.seller.id})
        return advance_sheet_to(sheet, state)

    def test_collections_user_and_manager_groups(self):
        user_group = self.env.ref(COLLECTION_USER_GROUP)
        manager_group = self.env.ref(COLLECTION_MANAGER_GROUP)
        self.assertIn(self.env.ref("base.group_user"), user_group.implied_ids)
        self.assertIn(user_group, manager_group.implied_ids)
        self.assertEqual(user_group.privilege_id, manager_group.privilege_id)
        self.assertTrue(self.manager.has_group(COLLECTION_USER_GROUP))
        self.assertTrue(self.collection_user.has_group(COLLECTION_USER_GROUP))
        self.assertFalse(self.collection_user.has_group(COLLECTION_MANAGER_GROUP))
        for user in (self.plain_user, self.seller):
            with self.subTest(user=user.login):
                self.assertFalse(user.has_group(COLLECTION_USER_GROUP))
        self.assertTrue(
            self.env.ref("base.user_admin").has_group(COLLECTION_MANAGER_GROUP)
        )

    def test_plain_internal_user_has_no_collection_data_access(self):
        for model in COLLECTION_MODELS:
            Model = self.env[model].with_user(self.plain_user)
            for operation in ("read", "create", "write", "unlink"):
                with (
                    self.subTest(model=model, operation=operation),
                    self.assertRaises(AccessError),
                ):
                    Model.check_access(operation)
            with self.subTest(model=model, operation="search"):
                with self.assertRaises(AccessError):
                    Model.search([])
        sheet = self._sheet()
        voucher = self.env["collection.voucher"].create(
            {
                "partner_id": dummy_customer_partner(self.env, customer="ROLES-V").id,
                "document_type": "bank_transfer",
                "amount": 10.0,
                "seller_id": self.seller.id,
                "sheet_id": sheet.id,
            }
        )
        for record in (sheet, voucher):
            with (
                self.subTest(record=record._name),
                self.assertRaises(AccessError),
            ):
                record.with_user(self.plain_user).read(["name"])
        with self.assertRaises(AccessError):
            self.env["collection.sheet"].with_user(self.plain_user).create(
                {"seller_id": self.seller.id}
            )

    def test_plain_internal_user_reads_partner_and_company_with_collection_data(self):
        install_test_connector_type(self)
        company = self.env.company
        connector = self.env["collection.connector"].create(
            {"name": "Roles Connector", "type": TEST_CONNECTOR_TYPE}
        )
        company.write({"collection_connector_id": connector.id})
        self.assertTrue(company.allowed_document_type_ids)
        partner = dummy_customer_partner(self.env, customer="ROLES-BOUND")
        self.env["collection.connector.customer.binding"].create(
            {
                "connector_id": connector.id,
                "external_customer_id": "roles-bound",
                "identification": "ROLES-BOUND",
                "partner_id": partner.id,
            }
        )
        as_plain = company.with_user(self.plain_user)
        collection_fields = [
            name
            for name, field in company._fields.items()
            if "collection" in (getattr(field, "_modules", None) or ())
        ]
        self.assertIn("allowed_document_type_ids", collection_fields)
        visible = as_plain.fields_get()
        # Every collection field a CRM user can see reads without AccessError.
        readable = [name for name in collection_fields if name in visible]
        self.assertEqual(as_plain.read(readable)[0]["id"], company.id)
        for name in (
            "collection_connector_id",
            "allowed_document_type_ids",
            "enabled_seller_ids",
        ):
            with self.subTest(company_field=name):
                self.assertNotIn(name, visible)
        # Collection adds no res.partner field; the bound customer and the
        # seller identity read as any contact does.
        self.assertTrue(as_plain.read(["name"])[0]["name"])
        self.assertEqual(
            partner.with_user(self.plain_user).read(["name", "vat"])[0]["vat"],
            "ROLES-BOUND",
        )
        self.assertTrue(self.seller.with_user(self.plain_user).read(["name"]))
        with self.assertRaises(AccessError):
            connector.with_user(self.plain_user).read(["name"])

    def test_collection_user_cannot_close_cancel_or_reinstate(self):
        proposal = self._sheet("proposal")
        as_user = proposal.with_user(self.collection_user)
        with self.assertRaises(AccessError):
            as_user.action_close()
        with self.assertRaises(AccessError):
            as_user.write({"state": "closed"})
        with self.assertRaises(AccessError):
            as_user.action_cancel()
        self.assertEqual(proposal.state, "proposal")
        cancelled = self._sheet("cancelled")
        with self.assertRaises(AccessError):
            cancelled.with_user(self.collection_user).action_reinstate()
        with self.assertRaises(AccessError):
            cancelled.with_user(self.collection_user).write({"state": "submitted"})
        self.assertEqual(cancelled.state, "cancelled")

    def test_manager_can_close_cancel_and_reinstate(self):
        sheet = self._sheet("proposal").with_user(self.manager)
        sheet.action_close()
        self.assertEqual(sheet.state, "closed")
        sheet.action_cancel()
        self.assertEqual(sheet.state, "cancelled")
        sheet.action_reinstate()
        self.assertEqual(sheet.state, "submitted")

    def test_collection_user_confirms_and_opens_document_review(self):
        self.env.company.write({"document_review_enabled": True})
        submitted = self._sheet("submitted").with_user(self.collection_user)
        action = submitted.action_open_document_review()
        self.assertEqual(action["params"]["sheet_id"], submitted.id)
        self.assertEqual(
            self.env["collection.voucher"]
            .with_user(self.collection_user)
            .get_review_queue(submitted.id),
            [],
        )
        submitted.action_confirm()
        self.assertEqual(submitted.state, "proposal")

    def test_review_and_confirm_refused_without_collection_role(self):
        self.env.company.write({"document_review_enabled": True})
        submitted = self._sheet("submitted")
        as_plain = submitted.with_user(self.plain_user)
        with self.assertRaises(AccessError):
            as_plain.action_open_document_review()
        with self.assertRaises(AccessError):
            self.env["collection.voucher"].with_user(self.plain_user).get_review_queue(
                submitted.id
            )
        with self.assertRaises(AccessError):
            as_plain.action_confirm()
        self.assertEqual(submitted.state, "submitted")

    def test_collection_user_creates_contacts_but_cannot_edit_them(self):
        self.assertFalse(self.collection_user.has_group("base.group_partner_manager"))
        Partner = self.env["res.partner"].with_user(self.collection_user)
        partner = Partner.create({"name": "Roles New Customer"})
        self.assertTrue(partner.id)
        with self.assertRaises(AccessError):
            partner.write({"name": "Renamed"})
        with self.assertRaises(AccessError):
            partner.unlink()
        with self.assertRaises(AccessError):
            self.env["res.partner"].with_user(self.plain_user).create(
                {"name": "Plain user contact"}
            )

    def test_sheet_buttons_and_menus_follow_the_roles(self):
        Sheet = self.env["collection.sheet"]
        arch_user = Sheet.with_user(self.collection_user).get_view(view_type="form")[
            "arch"
        ]
        arch_manager = Sheet.with_user(self.manager).get_view(view_type="form")["arch"]
        for name in MANAGER_SHEET_ACTIONS:
            with self.subTest(button=name):
                self.assertNotIn(f'name="{name}"', arch_user)
                self.assertIn(f'name="{name}"', arch_manager)
        for name in ("action_confirm", "action_open_document_review"):
            with self.subTest(button=name):
                self.assertIn(f'name="{name}"', arch_user)
        root = self.env.ref("collection.menu_collection_root")
        operational = (
            root
            | self.env.ref("collection.menu_collection_voucher")
            | self.env.ref("collection.menu_collection_sheet")
            | self.env.ref("collection.menu_collection_allocation")
            | self.env.ref("collection.menu_collection_receipt")
        )
        Menu = self.env["ir.ui.menu"]
        plain_visible = Menu.with_user(self.plain_user)._visible_menu_ids()
        user_visible = Menu.with_user(self.collection_user)._visible_menu_ids()
        for menu in operational:
            with self.subTest(menu=menu.name):
                self.assertNotIn(menu.id, plain_visible)
                self.assertIn(menu.id, user_visible)

    def test_imported_seller_identities_get_no_collection_group(self):
        """Sellers act through the agent: Import creates plain internal users."""
        install_test_connector_type(self)
        connector = self.env["collection.connector"].create(
            {"name": "Roles Import", "type": TEST_CONNECTOR_TYPE}
        )
        self.env.company.write({"collection_connector_id": connector.id})
        self.env.company._sync_enabled_sellers_from_connector()
        imported = self.env.company.enabled_seller_ids
        self.assertTrue(imported)
        for user in imported:
            with self.subTest(user=user.login):
                self.assertTrue(user.has_group("base.group_user"))
                self.assertFalse(user.has_group(COLLECTION_USER_GROUP))
