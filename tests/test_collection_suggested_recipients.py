# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCollectionSuggestedRecipients(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.odoobot = cls.env.ref("base.partner_root")
        cls.other = cls.env["res.company"].create({"name": "Recipients other company"})
        cls.user = (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Recipients Collections operator",
                    "login": "collection_recipients_operator",
                    "company_id": cls.other.id,
                    "company_ids": [Command.set(cls.other.ids)],
                    "group_ids": [
                        Command.set(
                            [cls.env.ref("collection.group_collection_user").id]
                        )
                    ],
                }
            )
        )
        cls.contact = cls.env["res.partner"].create(
            {
                "name": "Recipients own",
                "email": "recipients.own@example.com",
                "company_id": cls.other.id,
            }
        )

    def test_suggested_recipients_with_odoobot_outside_company(self):
        self.assertNotEqual(self.odoobot.company_id, self.other)
        contact = self.contact.with_user(self.user).with_context(
            allowed_company_ids=self.other.ids
        )
        # The company boundary still hides OdooBot itself.
        with self.assertRaises(AccessError), self.cr.savepoint():
            self.odoobot.with_user(self.user).read(["email"])
        # Drop the admin-side cache so OdooBot's email is fetched as the user.
        self.env.invalidate_all()
        suggested = contact._message_get_suggested_recipients()
        self.assertNotIn(
            self.odoobot.sudo().email_normalized,
            [recipient["email"] for recipient in suggested],
        )
