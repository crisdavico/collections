# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.translate import _


class CollectionCompanySettings(models.TransientModel):
    _name = "collection.company.settings"
    _description = "Company Collection Settings"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    enabled_seller_ids = fields.Many2many(
        "res.users",
        string="Enabled Sellers",
        domain="[('share', '=', False), ('company_ids', 'in', company_id)]",
    )
    auto_create_sheet = fields.Boolean(default=True)
    document_review_enabled = fields.Boolean()
    allowed_document_type_ids = fields.Many2many(
        "collection.document.type", string="Allowed Document Types"
    )
    collection_connector_id = fields.Many2one(
        "collection.connector", domain="[('company_id', '=', company_id)]"
    )

    @api.private
    def _checked_company(self):
        self.ensure_one()
        self.check_access("write")
        if not self.env.user.has_group("collection.group_collection_manager"):
            raise AccessError(_("Only Collections Managers can configure collections."))
        company = self.company_id
        if (
            company not in self.env.companies
            or company not in self.env.user.company_ids
        ):
            raise AccessError(_("You cannot configure collections for this company."))
        company.check_access("read")
        return company

    @api.onchange("company_id")
    def _onchange_company_id(self):
        if self.company_id and self.company_id in self.env.companies:
            for name in self._setting_fields():
                self[name] = self.company_id[name]

    @api.model
    def default_get(self, field_names):
        vals = super().default_get(field_names)
        company = self.env["res.company"].browse(
            vals.get("company_id") or self.env.company.id
        )
        if company not in self.env.companies:
            raise AccessError(_("You cannot configure collections for this company."))
        for name in self._setting_fields():
            if name in field_names:
                value = company[name]
                vals[name] = (
                    [Command.set(value.ids)]
                    if self._fields[name].type == "many2many"
                    else value.id
                    if self._fields[name].type == "many2one"
                    else value
                )
        return vals

    @api.model
    @api.private
    def _setting_fields(self):
        return (
            "enabled_seller_ids",
            "auto_create_sheet",
            "document_review_enabled",
            "allowed_document_type_ids",
            "collection_connector_id",
        )

    def action_save(self):
        company = self._checked_company()
        sellers = self.enabled_seller_ids.sudo()
        if any(seller.share or company not in seller.company_ids for seller in sellers):
            raise UserError(
                _("Enabled sellers must be internal users of this company.")
            )
        connector = self.collection_connector_id
        if connector:
            connector.check_access("read")
            if connector.company_id != company:
                raise UserError(_("The connector must belong to this company."))
        # The checked company and fixed field list are the entire elevated write.
        company.sudo().write(
            {
                "enabled_seller_ids": [Command.set(sellers.ids)],
                "auto_create_sheet": self.auto_create_sheet,
                "document_review_enabled": self.document_review_enabled,
                "allowed_document_type_ids": [
                    Command.set(self.allowed_document_type_ids.ids)
                ],
                "collection_connector_id": connector.id,
            }
        )
        return {"type": "ir.actions.act_window_close"}

    @api.model
    def action_bank_accounts(self):
        if not self.env.user.has_group("collection.group_collection_manager"):
            raise AccessError(_("Only Collections Managers can configure collections."))
        company = self.env.company
        return {
            "type": "ir.actions.act_window",
            "name": _("Company Bank Accounts"),
            "res_model": "res.partner.bank",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", company.partner_id.id)],
            "context": {
                "default_partner_id": company.partner_id.id,
                "default_company_id": company.id,
            },
        }

    def action_import_enabled_sellers(self):
        company = self._checked_company()
        self.action_save()
        # The company's one import, elevated only for this checked company: it
        # matches and creates company-local users and never widens access.
        scoped = company.sudo().with_company(company)
        result = scoped._sync_enabled_sellers_from_connector()
        self.enabled_seller_ids = [Command.set(scoped.enabled_seller_ids.ids)]
        return company._collection_seller_import_notification(result)
