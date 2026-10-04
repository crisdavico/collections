# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.translate import _

CONNECTOR_SETTING_FIELDS = (
    "sqlite_path",
    "bejerman_ws_url",
    "bejerman_usuario",
    "bejerman_clave",
    "bejerman_empresa",
    "bejerman_puesto",
    "bejerman_sucursal",
    "bejerman_timeout",
    "bejerman_allow_insecure",
    "bejerman_ca_bundle",
    "bejerman_seller_scenario",
    "bejerman_seller_view",
    "bejerman_debt_scenario",
    "bejerman_debt_view",
    "bejerman_quotation_kinds",
    "bejerman_debt_filter_field",
)


class CollectionConnectorSettings(models.TransientModel):
    _name = "collection.connector.settings"
    _description = "Company Collection Connector Settings"

    connector_id = fields.Many2one("collection.connector", required=True)
    connector_type = fields.Selection(related="connector_id.type", related_sudo=False)
    sqlite_path = fields.Char(string="SQLite Path")
    bejerman_ws_url = fields.Char(string="Web Service URL")
    bejerman_usuario = fields.Char(string="User")
    bejerman_clave = fields.Char(string="Password")
    bejerman_empresa = fields.Char(string="External Company")
    bejerman_puesto = fields.Char(string="Workstation")
    bejerman_sucursal = fields.Char(string="Branch")
    bejerman_timeout = fields.Integer(string="Timeout", default=60)
    bejerman_allow_insecure = fields.Boolean(string="Allow Insecure HTTP/TLS")
    bejerman_ca_bundle = fields.Char(string="CA Bundle")
    bejerman_seller_scenario = fields.Char(string="Seller Scenario")
    bejerman_seller_view = fields.Char(string="Seller View")
    bejerman_debt_scenario = fields.Char(string="Debt Scenario")
    bejerman_debt_view = fields.Char(string="Debt View")
    bejerman_quotation_kinds = fields.Char(string="Quotation Kinds")
    bejerman_debt_filter_field = fields.Char(string="Customer Filter Column")

    @api.private
    def _checked_connector(self):
        self.ensure_one()
        self.check_access("write")
        connector = self.connector_id
        connector._check_collection_management_access()
        return connector

    @api.model
    def default_get(self, field_names):
        vals = super().default_get(field_names)
        connector = self.env["collection.connector"].browse(vals.get("connector_id"))
        if connector:
            connector._check_collection_management_access()
            # Credentials remain protected on adapter models; only this checked
            # company connector's whitelisted settings are exposed to its manager.
            elevated = connector.sudo()
            for name in CONNECTOR_SETTING_FIELDS:
                if name in field_names and name in elevated._fields:
                    vals[name] = elevated[name]
        return vals

    def action_save(self):
        connector = self._checked_connector()
        prefix = "bejerman_" if connector.type == "bejerman" else "sqlite_"
        vals = {
            name: self[name]
            for name in CONNECTOR_SETTING_FIELDS
            if name.startswith(prefix) and name in connector._fields
        }
        connector.sudo().write(vals)
        return {"type": "ir.actions.act_window_close"}

    def action_test_connection(self):
        connector = self._checked_connector()
        self.action_save()
        return connector.sudo().test_connection()

    def action_refresh_snapshot(self):
        connector = self._checked_connector()
        if connector.type != "bejerman" or not hasattr(
            connector, "_bejerman_refresh_snapshot"
        ):
            raise UserError(_("The requested connector operation is not available."))
        self.action_save()
        connector.sudo()._bejerman_refresh_snapshot()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Debt Snapshot Refreshed"),
                "message": _("The company's debt snapshot was refreshed."),
                "type": "success",
            },
        }


class CollectionConnector(models.Model):
    _inherit = "collection.connector"

    @api.private
    def _check_collection_management_access(self):
        self.ensure_one()
        if not self.env.user.has_group("collection.group_collection_manager"):
            raise AccessError(_("Only Collections Managers can configure collections."))
        self.check_access("write")
        if (
            self.company_id not in self.env.companies
            or self.company_id not in self.env.user.company_ids
        ):
            raise AccessError(_("You cannot configure this company's connector."))

    def action_collection_connector_settings(self):
        self._check_collection_management_access()
        return {
            "type": "ir.actions.act_window",
            "name": _("Connector Settings"),
            "res_model": "collection.connector.settings",
            "view_mode": "form",
            "target": "new",
            "context": {"default_connector_id": self.id},
        }
