# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    document_review_enabled = fields.Boolean(
        related="company_id.document_review_enabled",
        readonly=False,
    )
    enabled_seller_ids = fields.Many2many(
        related="company_id.enabled_seller_ids",
        readonly=False,
    )
    auto_create_sheet = fields.Boolean(
        related="company_id.auto_create_sheet",
        readonly=False,
    )
    allowed_document_type_ids = fields.Many2many(
        related="company_id.allowed_document_type_ids",
        readonly=False,
    )
