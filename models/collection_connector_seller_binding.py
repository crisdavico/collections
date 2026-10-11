# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class CollectionConnectorSellerBinding(models.Model):
    _name = "collection.connector.seller.binding"
    _description = "Collection Connector Seller Binding"
    _order = "connector_id, external_seller_id"
    _check_company_auto = True

    connector_id = fields.Many2one(
        comodel_name="collection.connector",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    external_seller_id = fields.Char(required=True, index=True)
    user_id = fields.Many2one(
        comodel_name="res.users",
        required=True,
        ondelete="restrict",
        index=True,
    )
    company_id = fields.Many2one(
        related="connector_id.company_id",
        store=True,
        required=True,
        precompute=True,
        index=True,
    )
    commission_percent = fields.Float(
        string="Commission %",
        digits=(16, 2),
        required=True,
        default=0.0,
    )

    _connector_external_uniq = models.Constraint(
        "UNIQUE(connector_id, external_seller_id)",
        "External seller id must be unique per connector.",
    )
    _connector_user_uniq = models.Constraint(
        "UNIQUE(connector_id, user_id)",
        "Odoo seller must be unique per connector.",
    )
    _commission_percent_range = models.Constraint(
        "CHECK(commission_percent >= 0 AND commission_percent <= 100)",
        "Commission percent must be between 0 and 100.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        Connector = self.env["collection.connector"]
        for vals in vals_list:
            connector_id = vals.get("connector_id")
            company_id = vals.get("company_id")
            if connector_id and company_id:
                connector = Connector.browse(connector_id)
                if company_id != connector.company_id.id:
                    raise UserError(
                        _("Binding company must match the connector company.")
                    )
        return super().create(vals_list)
