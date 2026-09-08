# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools.translate import _

from .collection_common import (
    DOCUMENT_KIND_SELECTION,
    raise_if_create_vals_frozen,
    raise_if_sheet_frozen,
)


class CollectionAllocationLine(models.Model):
    _name = "collection.allocation.line"
    _description = "Collection Allocation Line"
    _order = "due_date, invoice_number"

    allocation_id = fields.Many2one(
        comodel_name="collection.allocation",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sheet_id = fields.Many2one(
        related="allocation_id.sheet_id",
        store=True,
        index=True,
    )
    partner_id = fields.Many2one(
        related="allocation_id.partner_id",
        string="Customer",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="allocation_id.currency_id",
        store=True,
    )
    company_id = fields.Many2one(
        related="allocation_id.company_id",
        store=True,
        required=True,
        precompute=True,
        index=True,
    )
    external_invoice_id = fields.Char(required=True)
    document_kind = fields.Selection(
        selection=list(DOCUMENT_KIND_SELECTION),
        default="invoice",
        required=True,
    )
    invoice_number = fields.Char()
    issue_date = fields.Date()
    due_date = fields.Date()
    invoice_amount = fields.Monetary(currency_field="currency_id")
    invoice_balance = fields.Monetary(currency_field="currency_id")
    invoice_state = fields.Char()
    amount_applied = fields.Monetary(
        required=True,
        default=0.0,
        currency_field="currency_id",
    )

    _amount_applied_positive = models.Constraint(
        "CHECK(amount_applied >= 0)",
        "Applied amount cannot be negative.",
    )
    _allocation_invoice_uniq = models.Constraint(
        "UNIQUE(allocation_id, external_invoice_id)",
        "Each external invoice can appear only once per allocation.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        raise_if_create_vals_frozen(
            self.env,
            vals_list,
            self._frozen_line_error_message(),
            field="allocation_id",
            comodel="collection.allocation",
        )
        return super().create(vals_list)

    def write(self, vals):
        self._raise_if_sheet_frozen()
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_if_sheet_frozen(self):
        if self.env.context.get("collection_allocation_parent_unlink"):
            return
        self._raise_if_sheet_frozen()

    @api.model
    @api.private
    def _frozen_line_error_message(self):
        return _(
            "Closed or cancelled collection sheets cannot change allocation lines."
        )

    @api.private
    def _raise_if_sheet_frozen(self):
        raise_if_sheet_frozen(self.sheet_id, self._frozen_line_error_message())
