# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCollectionUserScope(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other = cls.env["res.company"].create({"name": "Scope other company"})
        cls.user = (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Scoped Collections operator",
                    "login": "collection_scope_operator",
                    "company_id": cls.company.id,
                    "company_ids": [Command.set((cls.company | cls.other).ids)],
                    "group_ids": [
                        Command.set(
                            [cls.env.ref("collection.group_collection_user").id]
                        )
                    ],
                }
            )
        )
        cls.contacts = cls.env["res.partner"].create(
            [
                {"name": "Scope own", "company_id": cls.company.id},
                {"name": "Scope other", "company_id": cls.other.id},
                {"name": "Scope shared", "company_id": False},
            ]
        )

    def _assert_company_scope(self, records, fields):
        Model = records.with_user(self.user).with_context(
            allowed_company_ids=(self.other | self.company).ids,
            collection_unrestricted=True,
        )
        self.assertEqual(Model.search([("id", "in", records.ids)]).ids, records[:1].ids)
        for hidden in Model.browse(records[1:].ids):
            with self.assertRaises(AccessError), self.cr.savepoint():
                hidden.read(fields)

    def test_contacts_exclude_other_and_empty_company(self):
        self._assert_company_scope(self.contacts, ["name"])
        found = self.contacts.with_user(self.user).name_search("Scope ")
        self.assertEqual(
            [record_id for record_id, _name in found], self.contacts[:1].ids
        )

    def test_extra_group_rules_cannot_widen_company_scope(self):
        self.env["ir.rule"].create(
            {
                "name": "Scope permissive contact rule",
                "model_id": self.env.ref("base.model_res_partner").id,
                "groups": [Command.link(self.env.ref("base.group_user").id)],
                "domain_force": "[(1, '=', 1)]",
            }
        )
        self._assert_company_scope(self.contacts, ["name"])

    def test_bank_accounts_exclude_other_and_empty_company(self):
        accounts = self.env["res.partner.bank"].create(
            [
                {
                    "acc_number": f"scope-{index}",
                    "partner_id": partner.id,
                    "company_id": partner.company_id.id,
                }
                for index, partner in enumerate(self.contacts)
            ]
        )
        self._assert_company_scope(accounts, ["acc_number"])

    def test_collection_records_use_profile_company(self):
        connectors = self.env["collection.connector"].create(
            [
                {"name": "Scope own connector", "company_id": self.company.id},
                {"name": "Scope other connector", "company_id": self.other.id},
            ]
        )
        self._assert_company_scope(connectors, ["name"])

    def test_calendar_excludes_other_and_empty_company(self):
        events = (
            self.env["calendar.event"]
            .with_context(dont_notify=True)
            .create(
                [
                    {
                        "name": f"Scope event {index}",
                        "start": "2026-10-15 10:00:00",
                        "stop": "2026-10-15 11:00:00",
                        "company_id": company_id,
                    }
                    for index, company_id in enumerate(
                        (self.company.id, self.other.id, False)
                    )
                ]
            )
        )
        self._assert_company_scope(events, ["name", "start"])
        attendees = self.env["calendar.attendee"].create(
            [
                {"event_id": event.id, "partner_id": self.contacts[0].id}
                for event in events
            ]
        )
        self._assert_company_scope(attendees, ["event_id", "partner_id"])

    def test_discuss_excludes_other_and_empty_company(self):
        channels = self.env["discuss.channel"].create(
            [
                {
                    "name": f"Scope channel {index}",
                    "company_id": company_id,
                    "channel_partner_ids": [Command.link(self.user.partner_id.id)],
                }
                for index, company_id in enumerate(
                    (self.company.id, self.other.id, False)
                )
            ]
        )
        self._assert_company_scope(channels, ["name"])
        members = self.env["discuss.channel.member"].browse(
            [
                channel.channel_member_ids.filtered(
                    lambda member: member.partner_id == self.user.partner_id
                ).id
                for channel in channels
            ]
        )
        self._assert_company_scope(members, ["channel_id"])

    def test_new_calendar_events_default_to_profile_company(self):
        event = (
            self.env["calendar.event"]
            .with_user(self.user)
            .with_context(
                allowed_company_ids=(self.other | self.company).ids, dont_notify=True
            )
            .create(
                {
                    "name": "Scope new event",
                    "start": "2026-10-15 12:00:00",
                    "stop": "2026-10-15 13:00:00",
                }
            )
        )
        self.assertEqual(event.company_id, self.company)

    def test_new_contacts_default_to_profile_company(self):
        contact = (
            self.env["res.partner"]
            .with_user(self.user)
            .create({"name": "Scope new customer"})
        )
        self.assertEqual(contact.company_id, self.company)

    def test_activity_scheduler_opens_on_own_company_contact(self):
        Scheduler = (
            self.env["mail.activity.schedule"]
            .with_user(self.user)
            .with_context(active_model="res.partner", active_ids=self.contacts[:1].ids)
        )
        wizard = Scheduler.create({})
        self.assertEqual(wizard.company_id, self.company)
        self.assertEqual(Scheduler.search([("id", "=", wizard.id)]), wizard)

    def test_users_use_their_own_company_field(self):
        # User contacts are normally shared. A user's company is on res.users.
        self.user.partner_id.company_id = False
        other_user = self.user.copy(
            {
                "name": "Scope other user",
                "login": "scope_other",
                "company_id": self.other.id,
            }
        )
        self._assert_company_scope(self.user | other_user, ["name", "company_id"])

    def test_hidden_records_cannot_be_written_or_created(self):
        self.user.group_ids = [
            Command.link(self.env.ref("base.group_partner_manager").id)
        ]
        Contact = self.env["res.partner"].with_user(self.user)
        for contact in self.contacts[1:]:
            with self.assertRaises(AccessError), self.cr.savepoint():
                contact.with_user(self.user).write({"name": "Forbidden"})
        for company_id in (False, self.other.id):
            with self.assertRaises(AccessError), self.cr.savepoint():
                Contact.create({"name": "Forbidden", "company_id": company_id})

    def test_only_allowed_apps_even_with_extra_groups_and_debug(self):
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "Scope unrelated app",
                "res_model": "res.partner",
                "view_mode": "list,form",
            }
        )
        unrelated = self.env["ir.ui.menu"].create(
            {
                "name": "Scope unrelated app",
                "action": f"ir.actions.act_window,{action.id}",
            }
        )
        self.user.group_ids = [
            Command.link(self.env.ref("base.group_partner_manager").id)
        ]
        expected = {
            menu.id
            for xmlid in (
                "mail.menu_root_discuss",
                "calendar.mail_menu_calendar",
                "collection.menu_collection_root",
            )
            if (menu := self.env.ref(xmlid, raise_if_not_found=False))
        }
        Menu = self.env["ir.ui.menu"].with_user(self.user)
        for debug in (False, True):
            visible = Menu._visible_menu_ids(debug=debug)
            roots = Menu.sudo().search(
                [("id", "in", list(visible)), ("parent_id", "=", False)]
            )
            self.assertEqual(set(roots.ids), expected)
            self.assertNotIn(unrelated.id, visible)
        self.assertIn(unrelated.id, self.env["ir.ui.menu"]._visible_menu_ids())

    def test_unrelated_users_and_administrators_keep_standard_access(self):
        self.assertEqual(
            self.contacts.search([("id", "in", self.contacts.ids)]), self.contacts
        )
        self.user.group_ids = [Command.set([self.env.ref("base.group_user").id])]
        self.assertEqual(
            set(
                self.contacts.with_user(self.user)
                .search([("id", "in", self.contacts.ids)])
                .ids
            ),
            set(self.contacts.ids),
        )
