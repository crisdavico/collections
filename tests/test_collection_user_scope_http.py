# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestCollectionUserScopeHttp(HttpCase):
    def test_allowed_apps_initialize(self):
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Collections scope HTTP",
                    "login": "collection_scope_http",
                    "group_ids": [
                        Command.set(
                            [self.env.ref("collection.group_collection_user").id]
                        )
                    ],
                }
            )
        )
        other = self.env["res.company"].create({"name": "Scope HTTP other company"})
        company_ids = (user.company_id.id, other.id, False)
        channels = self.env["discuss.channel"].create(
            [
                {
                    "name": f"Scope HTTP channel {index}",
                    "company_id": company_id,
                    "channel_partner_ids": [Command.link(user.partner_id.id)],
                }
                for index, company_id in enumerate(company_ids)
            ]
        )
        events = (
            self.env["calendar.event"]
            .with_context(dont_notify=True)
            .create(
                [
                    {
                        "name": f"Scope HTTP event {index}",
                        "company_id": company_id,
                        "start": "2026-10-15 10:00:00",
                        "stop": "2026-10-15 11:00:00",
                    }
                    for index, company_id in enumerate(company_ids)
                ]
            )
        )
        self.authenticate(user.login, user.login)
        response = self.url_open("/odoo")
        self.assertEqual(response.status_code, 200)
        menus = self.url_open("/web/webclient/load_menus").json()
        roots = menus["root"]["children"]
        self.assertEqual(
            {menus[str(menu_id)]["xmlid"] for menu_id in roots},
            {
                "mail.menu_root_discuss",
                "calendar.mail_menu_calendar",
                "collection.menu_collection_root",
            },
        )
        messaging = self.make_jsonrpc_request(
            "/mail/data",
            {"fetch_params": ["init_messaging", "channels_as_member"]},
        )
        channel_ids = {
            channel["id"] for channel in messaging.get("discuss.channel", [])
        }
        self.assertIn(channels[0].id, channel_ids)
        self.assertNotIn(channels[1].id, channel_ids)
        self.assertNotIn(channels[2].id, channel_ids)
        visible_events = self.make_jsonrpc_request(
            "/web/dataset/call_kw/calendar.event/search_read",
            {
                "model": "calendar.event",
                "method": "search_read",
                "args": [[("id", "in", events.ids)]],
                "kwargs": {"fields": ["name", "start", "stop", "company_id"]},
            },
        )
        self.assertEqual([event["id"] for event in visible_events], events[:1].ids)
