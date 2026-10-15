# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from .collection_common import is_company_restricted


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    def _visible_menu_ids(self, debug=False):
        visible = super()._visible_menu_ids(debug=debug)
        if not is_company_restricted(self.env):
            return visible
        roots = self.browse(
            [
                self.env.ref(xmlid).id
                for xmlid in (
                    "mail.menu_root_discuss",
                    "calendar.mail_menu_calendar",
                    "collection.menu_collection_root",
                )
            ]
        )
        allowed = self.sudo().search([("id", "child_of", roots.ids)])
        return visible.intersection(allowed.ids)
