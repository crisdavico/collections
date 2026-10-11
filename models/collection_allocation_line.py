# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

from .collection_common import (
    DOCUMENT_KIND_SELECTION,
    is_privileged,
    privileged,
    raise_if_create_vals_frozen,
    raise_if_sheet_frozen,
    record_id,
)

# Fields that move money between an allocation's receipts.
_RECEIPT_CAP_FIELDS = frozenset({"amount_applied", "document_kind", "allocation_id"})
# Opened by the allocation and sheet writes that save several lines at once:
# their line writes skip the receipt cap and the parent checks the end state.
LINE_BATCH_SCOPE = "collection_allocation_line_batch"


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
        if is_privileged(LINE_BATCH_SCOPE):
            return super().create(vals_list)
        allocations = self.env["collection.allocation"].browse(
            {record_id(vals.get("allocation_id")) for vals in vals_list} - {False}
        )
        before = self._receipt_applied_totals(allocations)
        lines = super().create(vals_list)
        self._check_receipts_within_values(allocations, before)
        return lines

    def write(self, vals):
        self._raise_if_sheet_frozen()
        if not _RECEIPT_CAP_FIELDS & set(vals) or is_privileged(LINE_BATCH_SCOPE):
            return super().write(vals)
        allocations = self.allocation_id
        if vals.get("allocation_id"):
            allocations |= allocations.browse(record_id(vals["allocation_id"]))
        before = self._receipt_applied_totals(allocations)
        result = super().write(vals)
        self._check_receipts_within_values(allocations, before)
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_if_sheet_frozen(self):
        if is_privileged("collection_allocation_parent_unlink"):
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

    @api.private
    def _invoice_label(self):
        self.ensure_one()
        return self.invoice_number or self.external_invoice_id or ""

    @api.constrains("amount_applied", "invoice_balance")
    def _check_applied_within_invoice_balance(self):
        """A line MUST NOT apply more than the balance it snapshotted."""
        for line in self:
            currency = line.company_id.currency_id
            applied = line.amount_applied or 0.0
            if currency.compare_amounts(applied, 0.0) <= 0:
                continue
            if currency.compare_amounts(applied, line.invoice_balance or 0.0) > 0:
                raise ValidationError(
                    _(
                        "Applied amount cannot exceed the invoice balance "
                        "(%(invoice)s).",
                        invoice=line._invoice_label(),
                    )
                )

    @api.constrains("amount_applied", "external_invoice_id", "invoice_balance")
    def _check_invoice_not_over_applied(self):
        """One ERP document MUST NOT be applied above its balance overall.

        Counts every allocation of the company whose sheet is not cancelled
        (draft and confirmed alike, as the MCP tool does), and caps the total
        at the largest balance any of those lines snapshotted. Balances only
        fall as payments land, so the largest is the oldest snapshot, and the
        cap holds whether or not the ERP already registered the earlier
        applications. Cancelled sheets free the document; Reinstate checks
        again. Lines applying nothing are never refused.
        """
        lines = self.filtered(
            lambda line: line.external_invoice_id
            and line.sheet_id.state != "cancelled"
            and line.company_id.currency_id.compare_amounts(
                line.amount_applied or 0.0, 0.0
            )
            > 0
        )
        if not lines:
            return
        groups = self._read_group(
            [
                ("company_id", "in", lines.company_id.ids),
                (
                    "external_invoice_id",
                    "in",
                    list(set(lines.mapped("external_invoice_id"))),
                ),
                ("sheet_id.state", "!=", "cancelled"),
            ],
            groupby=["company_id", "external_invoice_id"],
            aggregates=["amount_applied:sum", "invoice_balance:max"],
        )
        totals = {
            (company.id, external_id): (applied or 0.0, balance or 0.0)
            for company, external_id, applied, balance in groups
        }
        for line in lines:
            applied, balance = totals.get(
                (line.company_id.id, line.external_invoice_id), (0.0, 0.0)
            )
            if line.company_id.currency_id.compare_amounts(applied, balance) > 0:
                raise ValidationError(
                    _(
                        "Applied amount exceeds available invoice balance "
                        "(%(invoice)s).",
                        invoice=line._invoice_label(),
                    )
                )

    @api.model
    @api.private
    def _write_line_batch(self, allocations, write):
        """Run ``write`` (a parent save of several lines) under one receipt cap.

        A form save sends one command per edited line, so moving an amount
        between two documents would otherwise be judged halfway through.
        """
        before = self._receipt_applied_totals(allocations)
        with privileged(LINE_BATCH_SCOPE):
            result = write()
        self._check_receipts_within_values(allocations, before)
        return result

    @api.model
    @api.private
    def _receipt_applied_totals(self, allocations):
        """Return ``{(allocation_id, document_kind): applied}`` for ``allocations``."""
        allocations = allocations.exists()
        if not allocations:
            return {}
        groups = self._read_group(
            [("allocation_id", "in", allocations.ids)],
            groupby=["allocation_id", "document_kind"],
            aggregates=["amount_applied:sum"],
        )
        return {
            (allocation.id, kind): applied or 0.0
            for allocation, kind, applied in groups
        }

    @api.model
    @api.private
    def _check_receipts_within_values(self, allocations, before):
        """A receipt MUST NOT apply more than its values fund.

        Only a change that raises a receipt's applications is refused: the
        board shrinks values before it redistributes, so an overdrawn receipt
        may still lower its applications. A circuit without a receipt yet is
        left to the Confirm and Close gate.
        """
        allocations = allocations.exists()
        if not allocations:
            return
        after = self._receipt_applied_totals(allocations)
        labels = dict(self._fields["document_kind"]._description_selection(self.env))
        for receipt in allocations.receipt_ids:
            key = (receipt.allocation_id.id, receipt.document_kind)
            applied = after.get(key, 0.0)
            currency = receipt.company_id.currency_id
            if (
                currency.compare_amounts(applied, receipt.total_values or 0.0) > 0
                and currency.compare_amounts(applied, before.get(key, 0.0)) > 0
            ):
                raise ValidationError(
                    _(
                        "Receipt applications cannot exceed funded values "
                        "(%(allocation)s, %(kind)s).",
                        allocation=receipt.allocation_id.name,
                        kind=labels.get(receipt.document_kind, receipt.document_kind),
                    )
                )
