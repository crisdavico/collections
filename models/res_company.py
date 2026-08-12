# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    document_review_enabled = fields.Boolean(default=False)

    @api.model
    @api.private
    def _document_review_enabled(self):
        return bool(self.env.company.document_review_enabled)

    def write(self, vals):
        result = super().write(vals)
        if "document_review_enabled" in vals:
            self.env.registry.clear_cache()
        return result
