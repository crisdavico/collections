# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.tools.translate import _


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
    collection_connector_id = fields.Many2one(
        related="company_id.collection_connector_id",
        readonly=False,
        domain="[('company_id', '=', company_id)]",
    )

    def action_import_enabled_sellers(self):
        """Replace Enabled Sellers from the active company connector."""
        self.ensure_one()
        self.company_id._sync_enabled_sellers_from_connector()
        self.invalidate_recordset(["enabled_seller_ids"])
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": _("Sellers imported"),
                "message": _("Enabled sellers were replaced from the connector."),
                "sticky": False,
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }
