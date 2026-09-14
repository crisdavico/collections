# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

from .collection_common import raise_if_create_vals_frozen


class CollectionCashReplacement(models.Model):
    _name = "collection.cash.replacement"
    _description = "Collection Cash Replacement"
    _order = "id"

    receipt_id = fields.Many2one(
        comodel_name="collection.receipt",
        required=True,
        ondelete="cascade",
        index=True,
    )
    cash_voucher_id = fields.Many2one(
        comodel_name="collection.voucher",
        required=True,
        ondelete="restrict",
        index=True,
    )
    deposit_voucher_id = fields.Many2one(
        comodel_name="collection.voucher",
        required=True,
        ondelete="restrict",
        index=True,
        help="The replacing voucher (`seller_deposit` or `seller_commission`).",
    )
    currency_id = fields.Many2one(
        related="receipt_id.currency_id",
        store=True,
    )
    company_id = fields.Many2one(
        related="receipt_id.company_id",
        store=True,
        required=True,
        precompute=True,
        index=True,
    )
    sheet_id = fields.Many2one(
        related="receipt_id.sheet_id",
        store=True,
    )
    amount = fields.Monetary(
        required=True,
        currency_field="currency_id",
    )
    direction = fields.Selection(
        selection=[
            ("replace", "Replace"),
            ("reverse", "Reverse"),
        ],
        required=True,
    )
    created_by = fields.Many2one(
        comodel_name="res.users",
        required=True,
        ondelete="restrict",
    )
    created_at = fields.Datetime(required=True)

    _amount_positive = models.Constraint(
        "CHECK(amount > 0)",
        "Cash replacement amount must be greater than zero.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("collection_cash_replacement"):
            raise UserError(
                _("Cash replacements can only be created by the replacement flow.")
            )
        raise_if_create_vals_frozen(
            self.env,
            vals_list,
            _("Closed or cancelled collection sheets cannot change cash replacements."),
            field="receipt_id",
            comodel="collection.receipt",
        )
        return super().create(vals_list)

    def write(self, vals):
        if self:
            raise UserError(_("Cash replacements cannot be modified."))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_forbidden(self):
        if self.env.context.get("collection_allocation_parent_unlink"):
            return
        raise UserError(_("Cash replacements cannot be deleted."))
