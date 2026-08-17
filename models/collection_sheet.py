# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class CollectionSheet(models.Model):
    _name = "collection.sheet"
    _description = "Collection Sheet"
    _order = "id desc"

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default="/",
    )
    seller_id = fields.Many2one(
        comodel_name="res.users",
        string="Seller",
        required=True,
        readonly=True,
        domain=[("share", "=", False)],
        ondelete="restrict",
    )

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", "/") in (False, "/", "New"):
                vals["name"] = sequence.next_by_code("collection.sheet") or "/"
        return super().create(vals_list)

    def write(self, vals):
        if "seller_id" in vals:
            raise UserError(_("The sheet seller cannot be changed."))
        return super().write(vals)
