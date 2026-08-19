# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.fields import Command


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _default_allowed_document_type_ids(self):
        return self.env["collection.document.type"].search([])

    document_review_enabled = fields.Boolean(default=False)
    enabled_seller_ids = fields.Many2many(
        comodel_name="res.users",
        relation="res_company_collection_enabled_seller_rel",
        column1="company_id",
        column2="user_id",
        string="Enabled Sellers",
        domain=[("share", "=", False)],
    )
    auto_create_sheet = fields.Boolean(default=True)
    allowed_document_type_ids = fields.Many2many(
        comodel_name="collection.document.type",
        relation="res_company_collection_allowed_document_type_rel",
        column1="company_id",
        column2="document_type_id",
        string="Allowed Document Types",
        default=_default_allowed_document_type_ids,
    )

    @api.model
    @api.private
    def _document_review_enabled(self):
        return bool(self.env.company.document_review_enabled)

    @api.model
    def _collection_seed_allowed_document_types(self):
        """Enable all catalog types on companies that have none yet."""
        types = self.env["collection.document.type"].search([])
        if not types:
            return True
        companies = self.search([("allowed_document_type_ids", "=", False)])
        if companies:
            companies.write({"allowed_document_type_ids": [Command.set(types.ids)]})
        return True

    def write(self, vals):
        result = super().write(vals)
        if "document_review_enabled" in vals:
            self.env.registry.clear_cache()
        return result
