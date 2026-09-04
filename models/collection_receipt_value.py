# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _

from .collection_allocation import _FROZEN_SHEET_STATES


class CollectionReceiptValue(models.Model):
    _name = "collection.receipt.value"
    _description = "Collection Receipt Value"
    _order = "id"

    receipt_id = fields.Many2one(
        comodel_name="collection.receipt",
        required=True,
        ondelete="cascade",
        index=True,
    )
    voucher_id = fields.Many2one(
        comodel_name="collection.voucher",
        required=True,
        ondelete="restrict",
        index=True,
    )
    amount = fields.Monetary(
        required=True,
        currency_field="currency_id",
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

    _amount_positive = models.Constraint(
        "CHECK(amount > 0)",
        "Receipt value amount must be greater than zero.",
    )
    _receipt_voucher_uniq = models.Constraint(
        "UNIQUE(receipt_id, voucher_id)",
        "Each voucher can appear only once per receipt.",
    )

    @api.constrains("voucher_id", "receipt_id")
    def _check_same_allocation(self):
        for value in self:
            if not value.voucher_id or not value.receipt_id:
                continue
            if value.voucher_id.allocation_id != value.receipt_id.allocation_id:
                raise ValidationError(
                    _("Receipt values must use vouchers from the same allocation.")
                )

    @api.constrains("amount", "voucher_id", "receipt_id")
    def _check_voucher_split_cap(self):
        vouchers = self.mapped("voucher_id")
        for voucher in vouchers:
            if not voucher:
                continue
            allocation = voucher.allocation_id
            values = self.env["collection.receipt.value"].search(
                [
                    ("voucher_id", "=", voucher.id),
                    ("receipt_id.allocation_id", "=", allocation.id),
                ]
            )
            total = sum(value.amount or 0.0 for value in values)
            if total > (voucher.amount or 0.0):
                raise ValidationError(
                    _("Receipt values for a voucher cannot exceed the voucher amount.")
                )

    def write(self, vals):
        if self.env.context.get("collection_receipt_issuing"):
            return super().write(vals)
        self._raise_if_sheet_frozen()
        self._raise_if_receipt_issued()
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_if_issued_or_frozen(self):
        if self.env.context.get("collection_allocation_parent_unlink"):
            return
        self._raise_if_sheet_frozen()
        self._raise_if_receipt_issued()

    @api.private
    def _raise_if_sheet_frozen(self):
        frozen = self.receipt_id.sheet_id.filtered(
            lambda sheet: sheet.state in _FROZEN_SHEET_STATES
        )
        if frozen:
            raise UserError(
                _(
                    "Closed or cancelled collection sheets cannot change "
                    "collection receipt values."
                )
            )

    @api.private
    def _raise_if_receipt_issued(self):
        if any(value.receipt_id.state == "issued" for value in self):
            raise UserError(_("Issued collection receipts cannot be modified."))
