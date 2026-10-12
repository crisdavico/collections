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
    bank_ids = fields.One2many(
        related="company_id.bank_ids",
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
    seller_binding_ids = fields.One2many(
        related="collection_connector_id.seller_binding_ids",
        readonly=True,
    )
    collection_mcp_trusted_seller_header = fields.Char(
        string="Trusted seller header",
        config_parameter="collection.mcp_trusted_seller_header",
        groups="base.group_system",
        help=(
            "HTTP header in which the MCP gateway sends the verified sender "
            "phone. When set, collection agent tools act only for the enabled "
            "seller with that phone and refuse any other seller. Leave empty to "
            "trust the seller the agent names."
        ),
    )

    def action_import_enabled_sellers(self):
        """Enable the active company connector's sellers (never disables)."""
        self.ensure_one()
        company = self.company_id
        result = company._sync_enabled_sellers_from_connector()
        self.invalidate_recordset(["enabled_seller_ids"])
        action = company._collection_seller_import_notification(result)
        action["params"]["next"] = {"type": "ir.actions.client", "tag": "reload"}
        return action
