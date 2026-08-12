# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    document_review_enabled = fields.Boolean(
        related="company_id.document_review_enabled",
        readonly=False,
    )
