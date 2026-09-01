# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


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
    invoice_number = fields.Char()
    issue_date = fields.Date()
    due_date = fields.Date()
    invoice_amount = fields.Monetary(currency_field="currency_id")
    invoice_balance = fields.Monetary(currency_field="currency_id")
    invoice_state = fields.Char()
    amount_applied = fields.Monetary(
        required=True,
        currency_field="currency_id",
    )

    _amount_applied_positive = models.Constraint(
        "CHECK(amount_applied > 0)",
        "Applied amount must be greater than zero.",
    )
    _amount_applied_lte_balance = models.Constraint(
        "CHECK(amount_applied <= invoice_balance)",
        "Applied amount cannot exceed the invoice balance.",
    )
    _allocation_invoice_uniq = models.Constraint(
        "UNIQUE(allocation_id, external_invoice_id)",
        "Each external invoice can appear only once per allocation.",
    )
