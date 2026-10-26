# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CollectionSheetCloseWizard(models.TransientModel):
    """Seller Close from the form: ask the cash kept before closing."""

    _name = "collection.sheet.close.wizard"
    _description = "Seller Close Cash Declaration"

    sheet_id = fields.Many2one(
        comodel_name="collection.sheet",
        required=True,
        ondelete="cascade",
    )
    currency_id = fields.Many2one(related="sheet_id.currency_id")
    cash_collected = fields.Monetary(
        related="sheet_id.cash_collected",
        currency_field="currency_id",
    )
    commission_amount = fields.Monetary(
        related="sheet_id.commission_amount",
        currency_field="currency_id",
    )
    commission_withheld = fields.Monetary(
        string="Commission Kept From Cash",
        currency_field="currency_id",
        help="Cash the seller kept as commission, zero if none.",
    )

    def action_seller_close(self):
        self.ensure_one()
        self.sheet_id.action_seller_close(commission_withheld=self.commission_withheld)
        return {"type": "ir.actions.act_window_close"}
