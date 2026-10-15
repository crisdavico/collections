# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from .collection_common import COLLECTION_USER_GROUP


class ResUsers(models.Model):
    _inherit = "res.users"

    def _collection_assign_identity_company(self):
        for user in self:
            if (
                user.has_group(COLLECTION_USER_GROUP)
                and not user.has_group("base.group_system")
                and not user.partner_id.company_id
            ):
                user.partner_id.company_id = user.company_id

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._collection_assign_identity_company()
        return users

    def write(self, vals):
        result = super().write(vals)
        if {"company_id", "group_ids"}.intersection(vals):
            self._collection_assign_identity_company()
        return result
