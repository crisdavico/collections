# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import TransactionCase

from .common_connector import TEST_CONNECTOR_TYPE, install_test_connector_type
from .test_collection_payment import create_collection_user, create_internal_seller

ANA = {
    "id": "ana-1",
    "name": "Ana Import",
    "mobile": "5491188820001",
    "active": 1,
    "commission_percent": 5.0,
}
BRUNO = {
    "id": "bruno-1",
    "name": "Bruno Import",
    "mobile": "5491188820002",
    "active": 1,
    "commission_percent": 0.0,
}
_EMPTY = "The connector returned no sellers. Nothing was changed."


class TestCollectionSellerImport(TransactionCase):
    """Importing sellers only adds; a short or empty answer never disables anyone."""

    def setUp(self):
        super().setUp()
        install_test_connector_type(self)
        self.company = self.env.company
        self.connector = self.env["collection.connector"].create(
            {"name": "Import Safety Connector", "type": TEST_CONNECTOR_TYPE}
        )
        self.company.write({"collection_connector_id": self.connector.id})
        self.manager = create_collection_user(self.env, "import_mgr", manager=True)

    def _sync(self, sellers):
        result = self.company.with_context(
            collection_test_sellers=sellers
        )._sync_enabled_sellers_from_connector()
        self.company.invalidate_recordset(["enabled_seller_ids"])
        return result

    def _user(self, external_id):
        return (
            self.env["collection.connector.seller.binding"]
            .search(
                [
                    ("connector_id", "=", self.connector.id),
                    ("external_seller_id", "=", external_id),
                ]
            )
            .user_id
        )

    def test_empty_answer_is_refused_and_changes_nothing(self):
        kept = create_internal_seller(self.env, "import_kept")
        self.company.write({"enabled_seller_ids": [Command.set(kept.ids)]})
        users_before = self.env["res.users"].search_count([])
        with self.assertRaises(UserError) as ctx:
            self._sync([])
        self.assertEqual(str(ctx.exception), _EMPTY)
        self.assertEqual(self.company.enabled_seller_ids, kept)
        self.assertEqual(self.env["res.users"].search_count([]), users_before)

    def test_sellers_missing_from_the_answer_stay_enabled_and_are_reported(self):
        self._sync([ANA, BRUNO])
        ana, bruno = self._user("ana-1"), self._user("bruno-1")
        result = self._sync([BRUNO])
        self.assertEqual(self.company.enabled_seller_ids, ana | bruno)
        self.assertEqual(result["imported"], bruno)
        self.assertEqual(result["missing"], ana)

    def test_settings_import_warns_about_missing_sellers(self):
        manual = create_internal_seller(self.env, "import_manual")
        self.company.write({"enabled_seller_ids": [Command.set(manual.ids)]})
        settings = self.env["res.config.settings"].create({})
        action = settings.with_context(
            collection_test_sellers=[ANA]
        ).action_import_enabled_sellers()
        params = action["params"]
        self.assertEqual(params["type"], "warning")
        self.assertIn(manual.name, params["message"])
        self.company.invalidate_recordset(["enabled_seller_ids"])
        self.assertIn(manual, self.company.enabled_seller_ids)
        self.assertIn(self._user("ana-1"), self.company.enabled_seller_ids)

    def test_settings_import_without_missing_sellers_succeeds(self):
        settings = self.env["res.config.settings"].create({})
        action = settings.with_context(
            collection_test_sellers=[ANA]
        ).action_import_enabled_sellers()
        self.assertEqual(action["params"]["type"], "success")

    def _wizard(self):
        return (
            self.env["collection.company.settings"]
            .with_user(self.manager)
            .create({"company_id": self.company.id})
        )

    def test_manager_wizard_runs_the_one_model_import(self):
        model = type(self.company)
        original = model._sync_enabled_sellers_from_connector
        calls = []

        def _spy(company):
            calls.append(company)
            return original(company)

        rows = [
            dict(
                external_seller_id="ana-1",
                name=ANA["name"],
                mobile=ANA["mobile"],
                commission_percent=5.0,
            )
        ]
        with (
            patch.object(model, "_sync_enabled_sellers_from_connector", new=_spy),
            patch.object(
                type(self.connector), "list_sellers", return_value={"sellers": rows}
            ),
        ):
            self._wizard().action_import_enabled_sellers()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], self.company)

    def test_manager_wizard_refuses_an_empty_answer(self):
        kept = create_internal_seller(self.env, "import_wizard_kept")
        self.company.write({"enabled_seller_ids": [Command.set(kept.ids)]})
        with (
            patch.object(
                type(self.connector), "list_sellers", return_value={"sellers": []}
            ),
            self.assertRaises(UserError),
        ):
            self._wizard().action_import_enabled_sellers()
        self.company.invalidate_recordset(["enabled_seller_ids"])
        self.assertEqual(self.company.enabled_seller_ids, kept)

    def test_admin_import_matches_only_company_users(self):
        """A user of another company with the same phone is neither reused nor moved."""
        other_company = self.env["res.company"].create({"name": "Import Other Co"})
        outsider = create_internal_seller(self.env, "import_outsider")
        outsider.write(
            {
                "company_ids": [Command.set(other_company.ids)],
                "company_id": other_company.id,
            }
        )
        outsider.partner_id.phone = ANA["mobile"]
        self._sync([ANA])
        ana = self._user("ana-1")
        self.assertNotEqual(ana, outsider)
        self.assertEqual(outsider.company_ids, other_company)
        self.assertIn(self.company, ana.company_ids)
