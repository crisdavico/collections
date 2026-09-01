# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import inspect
import json
from pathlib import Path

from odoo.exceptions import AccessError, UserError
from odoo.fields import Command
from odoo.tests import TransactionCase

from odoo.addons.muk_mcp.core.tool import get_tool_index

TOOL_NAME = "get_seller_id"
SELLER_PHONE = "+54 9 11 5555-0199"
SELLER_MOBILE_QUERY = "5491155550199"
SELLER_LOCAL_QUERY = "1155550199"
ZERO_MATCH_MOBILE = "5491199990000"
DUP_PHONE = "+54 9 11 5555-0200"
PORTAL_ONLY_PHONE = "+54 9 11 5555-0777"
SELLER_BAR_PHONE = "+54 9 11 5555-0888"


class TestCollectionMcpSellerLookup(TransactionCase):
    """get_seller_id MCP discovery, unique match, and fail-closed specs."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tool_model = cls.env["muk_mcp.tool"]
        cls.internal_user = cls._create_user(
            "collection_seller_lookup_internal", "base.group_user"
        )
        cls.portal_user = cls._create_user(
            "collection_seller_lookup_portal", "base.group_portal"
        )
        cls.public_user = cls._create_user(
            "collection_seller_lookup_public", "base.group_public"
        )
        cls.internal_user.partner_id.phone = SELLER_PHONE

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
        """Run get_seller_id in-process and return decoded JSON."""
        env = self.env(user=user) if user else self.env(user=self.internal_user)
        text, _info = self.tool_model._call(TOOL_NAME, arguments, env)
        return json.loads(text)

    def test_get_seller_id_discovered_as_method_read_mcp(self):
        """get_seller_id is method-discovered read/mcp; no DB muk_mcp.tool row."""
        by_name = {
            entry["name"]: entry for entry in self.tool_model.get_tools(registry="mcp")
        }
        self.assertIn(
            TOOL_NAME,
            by_name,
            f"{TOOL_NAME} must appear in MCP registry tools",
        )
        self.assertNotIn(
            "list_collection_sellers",
            by_name,
            "list_collection_sellers must not be registered as an MCP tool",
        )
        entry = get_tool_index(self.env, registry="mcp")[TOOL_NAME]
        self.assertEqual(entry["category"], "read")
        self.assertEqual(entry["registry"], "mcp")
        self.assertEqual(entry["kind"], "method")
        self.assertNotEqual(entry.get("kind"), "db")
        self.assertFalse(
            self.env["muk_mcp.tool"].search([("name", "=", TOOL_NAME)]),
            "get_seller_id must not have a DB muk_mcp.tool row",
        )

    def _enable_lookup_seller(self, user=None):
        """Put the lookup user on the current company's enabled-seller list."""
        user = user or self.internal_user
        self.env.company.write({"enabled_seller_ids": [Command.set([user.id])]})

    def test_unique_internal_match_returns_seller_id_only(self):
        """Unique normalized internal phone returns {seller_id} only."""
        self.assertTrue(self.internal_user.partner_id.phone)
        self.assertGreater(self.internal_user.id, 0)
        self._enable_lookup_seller()
        before_vouchers = self.env["collection.voucher"].search_count([])

        result = self._call({"mobile": SELLER_MOBILE_QUERY})

        self.assertEqual(result, {"seller_id": self.internal_user.id})
        self.assertIsInstance(result["seller_id"], int)
        self.assertGreater(result["seller_id"], 0)
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
            "get_seller_id must not create or update vouchers",
        )

    def test_portal_and_public_callers_denied_access_error(self):
        """Portal and public callers MUST receive AccessError, not a seller_id."""
        self.assertTrue(self.portal_user.share)
        self.assertTrue(self.public_user.share)
        for user in (self.portal_user, self.public_user):
            with self.subTest(login=user.login):
                with self.assertRaises(AccessError):
                    self._call({"mobile": SELLER_MOBILE_QUERY}, user=user)

    def test_empty_whitespace_or_invalid_mobile_rejected(self):
        """Empty, whitespace-only, or no-usable-digits mobile MUST raise UserError."""
        for mobile in ("", "   \t  ", "---", "++abc"):
            with self.subTest(mobile=repr(mobile)):
                with self.assertRaises(UserError):
                    self._call({"mobile": mobile})

    def test_ar_whatsapp_variants_match_same_seller(self):
        """Stored +54 9 … matches 549… and local 10-digit as one seller_id."""
        self._enable_lookup_seller()
        self.assertEqual(self.internal_user.partner_id.phone, SELLER_PHONE)
        e164 = self._call({"mobile": SELLER_MOBILE_QUERY})
        local = self._call({"mobile": SELLER_LOCAL_QUERY})
        self.assertEqual(e164, {"seller_id": self.internal_user.id})
        self.assertEqual(local, e164)

    def test_zero_internal_matches_fail_closed(self):
        """No internal phone match MUST raise UserError, not seller_id."""
        with self.assertRaises(UserError):
            self._call({"mobile": ZERO_MATCH_MOBILE})

    def test_many_internal_matches_fail_closed_no_pick_first(self):
        """Two internals with the same normalize MUST raise UserError."""
        first = self._create_user("collection_seller_lookup_dup_a", "base.group_user")
        second = self._create_user("collection_seller_lookup_dup_b", "base.group_user")
        first.partner_id.phone = DUP_PHONE
        second.partner_id.phone = DUP_PHONE
        self.assertNotEqual(first.id, second.id)
        with self.assertRaises(UserError):
            self._call({"mobile": "5491155550200"})

    def test_portal_share_digits_excluded_returns_internal(self):
        """Portal/share digits MUST NOT count; unique internal seller_id is returned."""
        self._enable_lookup_seller()
        self.portal_user.partner_id.phone = SELLER_PHONE
        self.assertTrue(self.portal_user.share)
        result = self._call({"mobile": SELLER_MOBILE_QUERY})
        self.assertEqual(result, {"seller_id": self.internal_user.id})
        self.assertNotEqual(result["seller_id"], self.portal_user.id)

    def test_portal_only_digits_fail_closed(self):
        """Only a portal/share phone MUST raise UserError, not that id."""
        self.portal_user.partner_id.phone = PORTAL_ONLY_PHONE
        self.assertTrue(self.portal_user.share)
        with self.assertRaises(UserError):
            self._call({"mobile": "5491155550777"})

    def test_unique_hit_fails_seller_bar_without_group_user(self):
        """share=False unique phone without base.group_user MUST raise UserError."""
        user = self._create_user(
            "collection_seller_lookup_no_group_user", "base.group_user"
        )
        user.partner_id.phone = SELLER_BAR_PHONE
        self.assertFalse(user.share)
        group_user_id = self.env.ref("base.group_user").id
        self.env.flush_all()
        self.env.cr.execute(
            "DELETE FROM res_groups_users_rel WHERE uid = %s AND gid = %s",
            (user.id, group_user_id),
        )
        self.env.cr.execute(
            "UPDATE res_users SET share = false WHERE id = %s",
            (user.id,),
        )
        user.invalidate_recordset(["group_ids", "all_group_ids"])
        self.env.registry.clear_cache()
        self.env.cr.execute(
            "UPDATE res_users SET share = false WHERE id = %s",
            (user.id,),
        )
        self.env.cr.execute("SELECT share FROM res_users WHERE id = %s", (user.id,))
        self.assertFalse(self.env.cr.fetchone()[0])
        self.assertFalse(user.has_group("base.group_user"))
        with self.assertRaises(UserError):
            self._call({"mobile": "5491155550888"})

    def test_unique_match_not_on_enabled_list_fails_closed(self):
        """Lookup MUST raise UserError when the unique match is not enabled."""
        company = self.env.company
        if self.internal_user in company.enabled_seller_ids:
            company.write(
                {"enabled_seller_ids": [Command.unlink(self.internal_user.id)]}
            )
        self.assertNotIn(self.internal_user, company.enabled_seller_ids)
        with self.assertRaises(UserError) as ctx:
            self._call({"mobile": SELLER_MOBILE_QUERY})
        self.assertIn("No unique seller found for that mobile.", str(ctx.exception))

    def test_empty_enabled_list_blocks_lookup(self):
        """Empty enabled-seller list MUST block a unique internal match."""
        self.env.company.write({"enabled_seller_ids": [Command.clear()]})
        self.assertFalse(self.env.company.enabled_seller_ids)
        with self.assertRaises(UserError) as ctx:
            self._call({"mobile": SELLER_MOBILE_QUERY})
        self.assertIn("No unique seller found for that mobile.", str(ctx.exception))

    def test_other_company_enabled_lists_do_not_satisfy_lookup(self):
        """Enabled-only-on-another-company MUST NOT resolve the unique match."""
        self.env.company.write({"enabled_seller_ids": [Command.clear()]})
        other = self._create_lookup_company("Lookup-OtherCo-Enabled")
        other.write({"enabled_seller_ids": [Command.set([self.internal_user.id])]})
        self.assertNotIn(self.internal_user, self.env.company.enabled_seller_ids)
        self.assertIn(self.internal_user, other.enabled_seller_ids)
        with self.assertRaises(UserError) as ctx:
            self._call({"mobile": SELLER_MOBILE_QUERY})
        self.assertIn("No unique seller found for that mobile.", str(ctx.exception))

    def test_unique_match_on_enabled_list_returns_seller_id(self):
        """Unique match on the current company's enabled list MUST return seller_id."""
        self._enable_lookup_seller()
        result = self._call({"mobile": SELLER_MOBILE_QUERY})
        self.assertEqual(result, {"seller_id": self.internal_user.id})

    def _create_lookup_company(self, name):
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

    def test_seller_lookup_source_omits_mobile_phone_and_sudo(self):
        """tools/seller_lookup.py MUST NOT use mobile_phone or sudo (no hr install)."""
        source_path = Path(__file__).resolve().parents[1] / "tools" / "seller_lookup.py"
        self.assertTrue(source_path.is_file(), source_path)
        source = source_path.read_text(encoding="utf-8")
        code = "\n".join(
            line for line in source.splitlines() if not line.lstrip().startswith("#")
        )
        self.assertNotIn("mobile_phone", code)
        self.assertNotIn(".sudo(", code)
        self.assertNotIn("sudo()", code)

        mixin = self.env["muk_mcp.mixin"]
        method = getattr(type(mixin), "get_seller_id", None)
        self.assertTrue(callable(method), "muk_mcp.mixin must expose get_seller_id")
        method_code = "\n".join(
            line
            for line in inspect.getsource(method).splitlines()
            if not line.lstrip().startswith("#")
        )
        self.assertNotIn("mobile_phone", method_code)
        self.assertNotIn(".sudo(", method_code)
        self.assertNotIn("sudo()", method_code)
