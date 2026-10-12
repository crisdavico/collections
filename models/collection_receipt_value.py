# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _

from .collection_common import (
    is_privileged,
    privileged,
    raise_if_create_vals_frozen,
    raise_if_sheet_frozen,
)


class CollectionReceiptValue(models.Model):
    _name = "collection.receipt.value"
    _description = "Collection Receipt Value"
    _order = "id"
    _check_company_auto = True

    receipt_id = fields.Many2one(
        comodel_name="collection.receipt",
        required=True,
        ondelete="restrict",
        index=True,
    )
    voucher_id = fields.Many2one(
        comodel_name="collection.voucher",
        required=True,
        ondelete="restrict",
        index=True,
        check_company=True,
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
        """A value MUST use a voucher of the receipt's sheet.

        Same sheet, not same allocation, on purpose: cross-customer splits
        (the board) and cash replacement (deposits and commissions carry no
        allocation) put a voucher's money on other allocations' receipts.
        """
        for value in self:
            if not value.voucher_id or not value.receipt_id:
                continue
            voucher_sheet = value.voucher_id.sheet_id
            receipt_sheet = value.receipt_id.sheet_id
            if not voucher_sheet or voucher_sheet != receipt_sheet:
                raise ValidationError(
                    _(
                        "Receipt values must use vouchers from the same "
                        "collection sheet."
                    )
                )

    @api.constrains("amount", "voucher_id", "receipt_id")
    def _check_voucher_split_cap(self):
        vouchers = self.voucher_id
        if not vouchers:
            return
        # One search for the whole batch; splitting per voucher would be N+1.
        applied = {}
        for value in self.search([("voucher_id", "in", vouchers.ids)]):
            voucher = value.voucher_id
            applied[voucher.id] = applied.get(voucher.id, 0.0) + (value.amount or 0.0)
        for voucher in vouchers:
            total = applied.get(voucher.id, 0.0)
            if voucher.currency_id.compare_amounts(total, voucher.amount or 0.0) > 0:
                raise ValidationError(
                    _("Receipt values for a voucher cannot exceed the voucher amount.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        raise_if_create_vals_frozen(
            self.env,
            vals_list,
            self._frozen_value_error_message(),
            field="receipt_id",
            comodel="collection.receipt",
        )
        return super().create(vals_list)

    def write(self, vals):
        if is_privileged("collection_receipt_issuing"):
            return super().write(vals)
        self._raise_if_sheet_frozen()
        self._raise_if_receipt_issued()
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_if_issued_or_frozen(self):
        if is_privileged("collection_allocation_parent_unlink"):
            return
        self._raise_if_sheet_frozen()
        self._raise_if_receipt_issued()

    @api.model
    @api.private
    def _frozen_value_error_message(self):
        return _(
            "Closed or cancelled collection sheets cannot change "
            "collection receipt values."
        )

    @api.private
    def _raise_if_sheet_frozen(self):
        raise_if_sheet_frozen(
            self.receipt_id.sheet_id, self._frozen_value_error_message()
        )

    @api.private
    def _raise_if_receipt_issued(self):
        if any(value.receipt_id.state == "issued" for value in self):
            raise UserError(_("Issued collection receipts cannot be modified."))

    @api.model
    @api.private
    def _assert_replacement_currencies(self, receipt, cash_voucher, deposit_voucher):
        currencies = {
            receipt.currency_id.id,
            cash_voucher.currency_id.id,
            deposit_voucher.currency_id.id,
        }
        if not all(currencies) or len(currencies) != 1:
            raise UserError(_("Cash replacement currencies must agree."))

    @api.private
    def _shrink_or_unlink(self, amount):
        """Reduce this value by a rounded slice; unlink when the slice is all of it.

        Returns the applied slice, or 0.0 when the slice is skipped.
        """
        self.ensure_one()
        currency = self.currency_id
        slice_amount = currency.round(amount or 0.0)
        if currency.compare_amounts(slice_amount, 0.0) == 0:
            return 0.0
        current = currency.round(self.amount or 0.0)
        if currency.compare_amounts(slice_amount, current) == 0:
            self.unlink()
            return slice_amount
        remaining = currency.round(current - slice_amount)
        if currency.compare_amounts(remaining, currency.rounding) < 0:
            return 0.0
        self.amount = remaining
        return slice_amount

    @api.model
    @api.private
    def _grow_voucher_amount(self, receipt, voucher, amount):
        """Add a rounded slice of ``voucher`` onto ``receipt``.

        Returns True when the money merged into an existing value.
        """
        currency = receipt.currency_id
        slice_amount = currency.round(amount or 0.0)
        if currency.compare_amounts(slice_amount, 0.0) == 0:
            return False
        twin = receipt.value_ids.filtered(
            lambda value, target=voucher: value.voucher_id == target
        )[:1]
        if twin:
            twin.amount = currency.round((twin.amount or 0.0) + slice_amount)
            return True
        self.create(
            {
                "receipt_id": receipt.id,
                "voucher_id": voucher.id,
                "amount": slice_amount,
            }
        )
        return False

    @api.model
    @api.private
    def _cash_replace(self, receipt, cash_voucher, deposit_voucher, amount):
        """Shrink cash and grow deposit on the same receipt; persist a replace row."""
        return self._cash_move(
            receipt,
            source_voucher=cash_voucher,
            target_voucher=deposit_voucher,
            amount=amount,
            direction="replace",
        )

    @api.model
    @api.private
    def _cash_reverse(self, receipt, cash_voucher, deposit_voucher, amount):
        """Shrink deposit and grow cash on the same receipt; persist a reverse row."""
        return self._cash_move(
            receipt,
            source_voucher=deposit_voucher,
            target_voucher=cash_voucher,
            amount=amount,
            direction="reverse",
        )

    @api.model
    @api.private
    def _cash_move(self, receipt, source_voucher, target_voucher, amount, direction):
        cash_voucher = source_voucher if direction == "replace" else target_voucher
        deposit_voucher = target_voucher if direction == "replace" else source_voucher
        self._assert_replacement_currencies(receipt, cash_voucher, deposit_voucher)
        currency = receipt.currency_id
        slice_amount = currency.round(amount or 0.0)
        empty = self.env["collection.cash.replacement"]
        if currency.compare_amounts(slice_amount, 0.0) == 0:
            return empty
        source_value = receipt.value_ids.filtered(
            lambda value, target=source_voucher: value.voucher_id == target
        )[:1]
        if not source_value:
            return empty
        applied = source_value._shrink_or_unlink(slice_amount)
        if currency.compare_amounts(applied, 0.0) == 0:
            return empty
        self._grow_voucher_amount(receipt, target_voucher, applied)
        with privileged("collection_cash_replacement"):
            return empty.create(
                {
                    "receipt_id": receipt.id,
                    "cash_voucher_id": cash_voucher.id,
                    "deposit_voucher_id": deposit_voucher.id,
                    "amount": applied,
                    "direction": direction,
                    "created_by": self.env.user.id,
                    "created_at": fields.Datetime.now(),
                }
            )
