# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class Base(models.AbstractModel):
    _inherit = "base"

    def _message_get_suggested_recipients_batch(self, *args, **kwargs):
        # Mail reads OdooBot's email as the current user to ban it from the
        # suggestions. The Collections company boundary hides OdooBot when it
        # belongs to another company, so load the email with sudo: the ORM
        # serves the later non-sudo read from the cache without an access check.
        self.env.ref("base.partner_root").sudo().email_normalized  # noqa: B018
        return super()._message_get_suggested_recipients_batch(*args, **kwargs)
