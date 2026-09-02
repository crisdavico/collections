# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from pathlib import Path

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import TransactionCase

from .common_connector import TEST_CONNECTOR_TYPE, install_test_connector_type
from .test_collection_payment import create_internal_seller

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

ANA = {
    "id": "ana-1",
    "name": "Ana Pérez",
    "mobile": "5491188810001",
    "active": 1,
    "commission_percent": 5.0,
}
BRUNO = {
    "id": "bruno-1",
    "name": "Bruno Gómez",
    "mobile": "5491188810002",
    "active": 1,
}
INACTIVE = {
    "id": "facundo-1",
    "name": "Facundo López",
    "mobile": "5491188810099",
    "active": 0,
}


class TestCollectionSellerSync(TransactionCase):
    """Import replaces enabled_seller_ids from connector.list_sellers()."""

    def setUp(self):
        super().setUp()
        install_test_connector_type(self)
        self.company = self.env.company
        self.connector = self.env["collection.connector"].create(
            {
                "name": "Sync Test Connector",
                "type": TEST_CONNECTOR_TYPE,
            }
        )
        self.company.write({"collection_connector_id": self.connector.id})

    def _sync(self, sellers=None):
        company = self.company
        if sellers is not None:
            company = company.with_context(collection_test_sellers=sellers)
        company._sync_enabled_sellers_from_connector()
        self.company.invalidate_recordset(["enabled_seller_ids"])
        self.connector.invalidate_recordset(["seller_binding_ids"])
        return self.company

    def _assert_user_error_no_leak(self, func):
        with self.assertRaises(UserError) as ctx:
            func()
        message = str(ctx.exception)
        for token in _LEAK_TOKENS:
            self.assertNotIn(token, message)
        return ctx.exception

    def _binding_for(self, external_seller_id):
        return self.env["collection.connector.seller.binding"].search(
            [
                ("connector_id", "=", self.connector.id),
                ("external_seller_id", "=", external_seller_id),
            ],
            limit=1,
        )

    def test_import_creates_user_and_binding_for_unbound_seller(self):
        """Unbound active source row MUST create an internal user and binding."""
        self._sync([ANA])
        binding = self._binding_for("ana-1")
        self.assertTrue(binding)
        user = binding.user_id
        self.assertFalse(user.share)
        self.assertTrue(user.has_group("base.group_user"))
        self.assertEqual(user.login, f"collection.{self.company.id}.ana-1")
        self.assertEqual(user.phone, ANA["mobile"])
        self.assertIn(self.company, user.company_ids)
        self.assertEqual(self.company.enabled_seller_ids, user)

    def test_import_matches_existing_user_by_normalized_phone(self):
        """Unique internal phone match MUST reuse that user instead of creating."""
        existing = create_internal_seller(self.env, "sync_phone_match")
        existing.partner_id.phone = "+54 9 11 8881-0001"
        before = self.env["res.users"].search_count([])
        self._sync([ANA])
        binding = self._binding_for("ana-1")
        self.assertEqual(binding.user_id, existing)
        self.assertEqual(self.company.enabled_seller_ids, existing)
        self.assertEqual(self.env["res.users"].search_count([]), before)

    def test_import_reuses_existing_binding(self):
        """Existing binding MUST win even when the stored phone differs."""
        bound = create_internal_seller(self.env, "sync_bound_user")
        bound.partner_id.phone = "+54 9 11 0000-1111"
        self.env["collection.connector.seller.binding"].create(
            {
                "connector_id": self.connector.id,
                "external_seller_id": "ana-1",
                "user_id": bound.id,
            }
        )
        before = self.env["res.users"].search_count([])
        self._sync([ANA])
        binding = self._binding_for("ana-1")
        self.assertEqual(binding.user_id, bound)
        self.assertEqual(self.company.enabled_seller_ids, bound)
        self.assertEqual(self.env["res.users"].search_count([]), before)

    def test_import_replaces_enabled_list_and_omits_inactive(self):
        """Replace-all MUST drop extras and omit inactive source rows."""
        extra = create_internal_seller(self.env, "sync_manual_extra")
        self.company.write({"enabled_seller_ids": [Command.set([extra.id])]})
        self.assertEqual(self.company.enabled_seller_ids, extra)
        self._sync([ANA, BRUNO, INACTIVE])
        enabled = self.company.enabled_seller_ids
        self.assertNotIn(extra, enabled)
        self.assertEqual(len(enabled), 2)
        self.assertFalse(self._binding_for("facundo-1"))
        logins = set(enabled.mapped("login"))
        self.assertIn(f"collection.{self.company.id}.ana-1", logins)
        self.assertIn(f"collection.{self.company.id}.bruno-1", logins)

    def test_import_does_not_delete_users_dropped_from_the_list(self):
        """Users that fall off Enabled Sellers MUST remain (bindings kept)."""
        self._sync([ANA, BRUNO])
        ana = self._binding_for("ana-1").user_id
        bruno = self._binding_for("bruno-1").user_id
        self.assertTrue(ana.exists())
        self._sync([BRUNO])
        self.assertTrue(ana.exists())
        self.assertTrue(self._binding_for("ana-1"))
        self.assertEqual(self.company.enabled_seller_ids, bruno)

    def test_missing_connector_leaves_enabled_list_unchanged(self):
        """Missing connector MUST UserError and MUST NOT change enabled sellers."""
        extra = create_internal_seller(self.env, "sync_keep_extra")
        self.company.write(
            {
                "enabled_seller_ids": [Command.set([extra.id])],
                "collection_connector_id": False,
            }
        )
        before_users = self.env["res.users"].search_count([])
        self._assert_user_error_no_leak(
            self.company._sync_enabled_sellers_from_connector
        )
        self.assertEqual(self.company.enabled_seller_ids, extra)
        self.assertEqual(self.env["res.users"].search_count([]), before_users)

    def test_inactive_connector_leaves_enabled_list_unchanged(self):
        """Inactive connector MUST fail closed with the list unchanged."""
        extra = create_internal_seller(self.env, "sync_inactive_keep")
        self.company.write({"enabled_seller_ids": [Command.set([extra.id])]})
        self.connector.active = False
        self._assert_user_error_no_leak(
            self.company._sync_enabled_sellers_from_connector
        )
        self.assertEqual(self.company.enabled_seller_ids, extra)

    def test_misconfigured_connector_leaves_enabled_list_unchanged(self):
        """Misconfigured connector (no type) MUST fail closed."""
        extra = create_internal_seller(self.env, "sync_misconfig_keep")
        self.company.write({"enabled_seller_ids": [Command.set([extra.id])]})
        self.connector.type = False
        self._assert_user_error_no_leak(
            self.company._sync_enabled_sellers_from_connector
        )
        self.assertEqual(self.company.enabled_seller_ids, extra)

    def test_duplicate_source_phone_aborts_without_partial_write(self):
        """Duplicate normalized phones in the source MUST abort the whole sync."""
        extra = create_internal_seller(self.env, "sync_dup_phone_keep")
        self.company.write({"enabled_seller_ids": [Command.set([extra.id])]})
        before_users = self.env["res.users"].search_count([])
        duplicate = dict(BRUNO, mobile=ANA["mobile"])
        self._assert_user_error_no_leak(lambda: self._sync([ANA, duplicate]))
        self.assertEqual(self.company.enabled_seller_ids, extra)
        self.assertEqual(self.env["res.users"].search_count([]), before_users)
        self.assertFalse(self.connector.seller_binding_ids)

    def test_two_source_ids_mapping_to_same_user_aborts(self):
        """Binding + phone match onto one user MUST abort with no partial write."""
        user = create_internal_seller(self.env, "sync_collision_user")
        user.partner_id.phone = "+54 9 11 8881-0002"
        self.env["collection.connector.seller.binding"].create(
            {
                "connector_id": self.connector.id,
                "external_seller_id": "ana-1",
                "user_id": user.id,
            }
        )
        extra = create_internal_seller(self.env, "sync_collision_keep")
        self.company.write({"enabled_seller_ids": [Command.set([extra.id])]})
        before_users = self.env["res.users"].search_count([])
        ana_other_phone = dict(ANA, mobile="5491199900001")
        self._assert_user_error_no_leak(lambda: self._sync([ana_other_phone, BRUNO]))
        self.assertEqual(self.company.enabled_seller_ids, extra)
        self.assertEqual(self.env["res.users"].search_count([]), before_users)

    def test_second_import_is_idempotent(self):
        """A second Import MUST reuse the same user ids."""
        self._sync([ANA, BRUNO])
        first_ids = set(self.company.enabled_seller_ids.ids)
        self.assertEqual(len(first_ids), 2)
        self._sync([ANA, BRUNO])
        self.assertEqual(set(self.company.enabled_seller_ids.ids), first_ids)
        self.assertEqual(len(self.connector.seller_binding_ids), 2)

    def test_settings_import_returns_success_notification(self):
        """Import action MUST notify success and refresh enabled sellers."""
        settings = self.env["res.config.settings"].create({})
        action = settings.with_context(
            collection_test_sellers=[ANA]
        ).action_import_enabled_sellers()
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "display_notification")
        params = action["params"]
        self.assertEqual(params["type"], "success")
        self.assertTrue(str(params.get("title") or ""))
        self.assertTrue(str(params.get("message") or ""))
        self.company.invalidate_recordset(["enabled_seller_ids"])
        self.assertTrue(self.company.enabled_seller_ids)
        self.assertEqual(len(self.company.enabled_seller_ids), 1)

    def test_sync_source_omits_sudo(self):
        """Company sync MUST NOT call sudo()."""
        source_path = Path(__file__).resolve().parents[1] / "models" / "res_company.py"
        self.assertTrue(source_path.is_file(), source_path)
        source = source_path.read_text(encoding="utf-8")
        method = []
        capture = False
        for line in source.splitlines():
            if "def _sync_enabled_sellers_from_connector" in line:
                capture = True
            if capture:
                method.append(line)
                if (
                    len(method) > 1
                    and line.startswith("    def ")
                    and "_sync_enabled_sellers_from_connector" not in line
                ):
                    break
        code = "\n".join(
            line
            for line in method
            if not line.lstrip().startswith("#") and '"""' not in line
        )
        self.assertTrue(method, "sync method must exist")
        self.assertNotIn(".sudo(", code)
        self.assertNotIn("sudo()", code)

    def test_import_persists_ana_commission_percent(self):
        """Import MUST store Ana's 5.0 on the binding, not on res.users."""
        self._sync([ANA])
        binding = self._binding_for("ana-1")
        self.assertTrue(binding)
        self.assertEqual(binding.commission_percent, 5.0)
        self.assertNotIn("commission_percent", self.env["res.users"]._fields)

    def test_import_overwrites_commission_percent_same_user(self):
        """Re-Import MUST overwrite the stored rate and reuse the same user."""
        self._sync([ANA])
        binding = self._binding_for("ana-1")
        user = binding.user_id
        self.assertEqual(binding.commission_percent, 5.0)
        self._sync([dict(ANA, commission_percent=7.5)])
        binding = self._binding_for("ana-1")
        self.assertEqual(binding.user_id, user)
        self.assertEqual(binding.commission_percent, 7.5)
        self.assertEqual(len(self.connector.seller_binding_ids), 1)

    def test_invalid_commission_percent_fails_closed_before_write(self):
        """Invalid rates MUST UserError with zero user/binding/enabled writes."""
        extra = create_internal_seller(self.env, "sync_invalid_rate_keep")
        self.company.write({"enabled_seller_ids": [Command.set([extra.id])]})
        before_users = self.env["res.users"].search_count([])
        for rate in (-0.01, 100.01, "abc"):
            with self.subTest(rate=rate):
                self._assert_user_error_no_leak(
                    lambda invalid=rate: self._sync(
                        [dict(ANA, commission_percent=invalid)]
                    )
                )
                self.assertEqual(self.company.enabled_seller_ids, extra)
                self.assertEqual(self.env["res.users"].search_count([]), before_users)
                self.assertFalse(self.connector.seller_binding_ids)

    def test_import_zero_commission_percent_is_valid(self):
        """Rate 0.0 MUST persist and Import MUST succeed."""
        self._sync([dict(ANA, commission_percent=0.0)])
        binding = self._binding_for("ana-1")
        self.assertTrue(binding)
        self.assertEqual(binding.commission_percent, 0.0)
        self.assertEqual(self.company.enabled_seller_ids, binding.user_id)
