# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from .collection_common import default_record_company


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    company_id = fields.Many2one("res.company", index=True)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if "company_id" in fields_list and "company_id" not in values:
            values["company_id"] = default_record_company(self.env).id
        return values


class DiscussChannelMember(models.Model):
    _inherit = "discuss.channel.member"

    company_id = fields.Many2one(
        related="channel_id.company_id", store=True, index=True
    )
