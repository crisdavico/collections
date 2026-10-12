# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG

from .collection_common import (
    DOCUMENT_KIND_SELECTION,
    is_privileged,
    privileged,
    raise_if_create_vals_frozen,
    raise_if_sheet_frozen,
)

_APPLIED_DEPENDS = (
    "document_kind",
    "allocation_id.line_ids.document_kind",
    "allocation_id.line_ids.amount_applied",
)
_VALUES_DEPENDS = ("value_ids.amount",)
_RECEIPT_STATE_SELECTION = (
    ("draft", "Draft"),
    ("closed", "Closed"),
    ("issued", "Issued"),
)
# Privileged scopes (``collection_common.privileged``), never context keys.
_STATE_SCOPE_AUDITED = "collection_receipt_audited_state"
_STATE_SCOPE_ISSUING = "collection_receipt_issuing"


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
        depends=_VALUES_DEPENDS,
    )
    total_applied = fields.Monetary(
        compute="_compute_totals",
        currency_field="currency_id",
        depends=_APPLIED_DEPENDS,
    )
    amount_on_account = fields.Monetary(
        compute="_compute_totals",
        currency_field="currency_id",
        depends=_VALUES_DEPENDS + _APPLIED_DEPENDS,
    )
    external_receipt_id = fields.Char(index=True, copy=False)
    state = fields.Selection(
        selection=list(_RECEIPT_STATE_SELECTION),
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

    @api.model_create_multi
    def create(self, vals_list):
        raise_if_create_vals_frozen(
            self.env,
            vals_list,
            self._frozen_receipt_error_message(),
            field="allocation_id",
            comodel="collection.allocation",
        )
        return super().create(vals_list)

    def write(self, vals):
        self._intercept_state_write(vals)
        if is_privileged(_STATE_SCOPE_ISSUING):
            return super().write(vals)
        self._raise_if_issued()
        if not is_privileged(_STATE_SCOPE_AUDITED):
            self._raise_if_sheet_frozen()
        return super().write(vals)

    def unlink(self):
        if not self:
            return True
        # ``value_ids`` no longer cascade in the database: refuse first, then
        # remove the values through the ORM under the parent-unlink scope.
        if not self.env.context.get(MODULE_UNINSTALL_FLAG):
            self._unlink_if_issued_or_frozen()
        with privileged("collection_allocation_parent_unlink"):
            self.value_ids.unlink()
        return super().unlink()

    @api.ondelete(at_uninstall=False)
    def _unlink_if_issued_or_frozen(self):
        self._raise_if_issued()
        if self._has_cash_replacements():
            raise UserError(
                _("Collection receipts with cash replacements cannot be deleted.")
            )
        if is_privileged("collection_allocation_parent_unlink"):
            return
        self._raise_if_sheet_frozen()

    @api.private
    def _has_cash_replacements(self):
        """Return whether any cash replacement row points at these receipts."""
        if not self:
            return False
        return bool(
            self.env["collection.cash.replacement"].search_count(
                [("receipt_id", "in", self.ids)], limit=1
            )
        )

    @api.private
    def _action_mark_closed(self):
        drafts = self.filtered(lambda receipt: receipt.state == "draft")
        if not drafts:
            return True
        with privileged(_STATE_SCOPE_AUDITED):
            return drafts.write({"state": "closed"})

    @api.private
    def _action_reopen_closed(self):
        closed = self.filtered(lambda receipt: receipt.state == "closed")
        if not closed:
            return True
        with privileged(_STATE_SCOPE_AUDITED):
            return closed.write({"state": "draft"})

    @api.private
    def _intercept_state_write(self, vals):
        if "state" not in vals or self._state_write_is_audited():
            return None
        raise UserError(_("Receipt state can only be changed via Close or Cancel."))

    @api.private
    def _state_write_is_audited(self):
        return is_privileged(_STATE_SCOPE_AUDITED) or is_privileged(
            _STATE_SCOPE_ISSUING
        )

    @api.private
    def _raise_if_sheet_frozen(self):
        raise_if_sheet_frozen(self.sheet_id, self._frozen_receipt_error_message())

    @api.model
    @api.private
    def _frozen_receipt_error_message(self):
        return _(
            "Closed or cancelled collection sheets cannot change collection receipts."
        )

    @api.private
    def _raise_if_issued(self):
        if any(receipt.state == "issued" for receipt in self):
            raise UserError(_("Issued collection receipts cannot be modified."))
