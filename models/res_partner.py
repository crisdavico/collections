# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from .collection_common import is_company_restricted


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if (
            "company_id" in fields_list
            and "company_id" not in values
            and is_company_restricted(self.env)
        ):
            values["company_id"] = self.env.user.company_id.id
        return values
