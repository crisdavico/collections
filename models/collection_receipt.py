# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

from .collection_common import DOCUMENT_KIND_SELECTION, raise_if_sheet_frozen


class CollectionReceipt(models.Model):
    _name = "collection.receipt"
    _description = "Collection Receipt"
    _order = "id desc"

    allocation_id = fields.Many2one(
        comodel_name="collection.allocation",
        required=True,
        ondelete="cascade",
        index=True,
    )
    document_kind = fields.Selection(
        selection=list(DOCUMENT_KIND_SELECTION),
        default="invoice",
        required=True,
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
    value_ids = fields.One2many(
        comodel_name="collection.receipt.value",
        inverse_name="receipt_id",
        string="Values",
    )
    line_ids = fields.Many2many(
        comodel_name="collection.allocation.line",
        string="Applications",
        compute="_compute_line_ids",
    )
    total_values = fields.Monetary(
        compute="_compute_totals",
        currency_field="currency_id",
    )
    total_applied = fields.Monetary(
        compute="_compute_totals",
        currency_field="currency_id",
    )
    amount_on_account = fields.Monetary(
        compute="_compute_totals",
        currency_field="currency_id",
    )
    external_receipt_id = fields.Char(index=True, copy=False)
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("issued", "Issued"),
        ],
        default="draft",
        required=True,
        copy=False,
    )

    _allocation_kind_uniq = models.Constraint(
        "UNIQUE(allocation_id, document_kind)",
        "Only one receipt is allowed per document kind on an allocation.",
    )
    _external_receipt_id_uniq = models.Constraint(
        "UNIQUE(external_receipt_id)",
        "External receipt id must be unique.",
    )

    @api.depends(
        "allocation_id.line_ids.document_kind",
        "allocation_id.line_ids.amount_applied",
        "document_kind",
    )
    def _compute_line_ids(self):
        for receipt in self:
            receipt.line_ids = receipt.allocation_id.line_ids.filtered(
                lambda line, kind=receipt.document_kind: line.document_kind == kind
                and (line.amount_applied or 0.0) > 0.0
            )

    @api.depends("value_ids.amount", "line_ids.amount_applied")
    def _compute_totals(self):
        for receipt in self:
            total_values = sum(value.amount or 0.0 for value in receipt.value_ids)
            total_applied = sum(line.amount_applied or 0.0 for line in receipt.line_ids)
            receipt.total_values = total_values
            receipt.total_applied = total_applied
            receipt.amount_on_account = total_values - total_applied

    def write(self, vals):
        if self.env.context.get("collection_receipt_issuing"):
            return super().write(vals)
        self._raise_if_sheet_frozen()
        self._raise_if_issued()
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_if_issued_or_frozen(self):
        if self.env.context.get("collection_allocation_parent_unlink"):
            return
        self._raise_if_sheet_frozen()
        self._raise_if_issued()

    @api.private
    def _raise_if_sheet_frozen(self):
        raise_if_sheet_frozen(
            self.sheet_id,
            _(
                "Closed or cancelled collection sheets cannot change "
                "collection receipts."
            ),
        )

    @api.private
    def _raise_if_issued(self):
        if any(receipt.state == "issued" for receipt in self):
            raise UserError(_("Issued collection receipts cannot be modified."))
