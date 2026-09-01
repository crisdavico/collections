# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class CollectionConnectorCustomerBinding(models.Model):
    _name = "collection.connector.customer.binding"
    _description = "Collection Connector Customer Binding"
    _order = "connector_id, external_customer_id"

    connector_id = fields.Many2one(
        comodel_name="collection.connector",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    external_customer_id = fields.Char(required=True, index=True)
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        required=True,
        ondelete="restrict",
        index=True,
    )
    identification = fields.Char(required=True, index=True)
    customer_code = fields.Char()
    company_id = fields.Many2one(
        related="connector_id.company_id",
        store=True,
        required=True,
        precompute=True,
        index=True,
    )

    _connector_external_uniq = models.Constraint(
        "UNIQUE(connector_id, external_customer_id)",
        "External customer id must be unique per connector.",
    )
    _connector_identification_uniq = models.Constraint(
        "UNIQUE(connector_id, identification)",
        "Customer identification must be unique per connector.",
    )
    _connector_partner_uniq = models.Constraint(
        "UNIQUE(connector_id, partner_id)",
        "Odoo partner must be unique per connector.",
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
