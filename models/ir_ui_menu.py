# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        if not self.env.company._document_review_enabled():
            menu = self.env.ref(
                "collection.menu_collection_document_review",
                raise_if_not_found=False,
            )
            if menu:
                res.append(menu.id)
        return res
