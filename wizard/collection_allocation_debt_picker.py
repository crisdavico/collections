# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class CollectionAllocationDebtCandidate(models.TransientModel):
    _name = "collection.allocation.debt.candidate"
    _description = "Outstanding Customer Debt Candidate"
    _order = "due_date, invoice_number, external_invoice_id"
    _rec_names_search = ["invoice_number", "external_invoice_id"]

    picker_id = fields.Many2one(
        comodel_name="collection.allocation.debt.picker",
        required=True,
        ondelete="cascade",
        index=True,
    )
    name = fields.Char(compute="_compute_name", store=True)
    external_invoice_id = fields.Char(required=True)
    document_kind = fields.Selection(
        selection=[
            ("invoice", "Invoice"),
            ("quotation", "Quotation"),
        ],
        required=True,
        default="invoice",
    )
    invoice_number = fields.Char()
    issue_date = fields.Date()
    due_date = fields.Date()
    currency_id = fields.Many2one(
        related="picker_id.currency_id",
    )
    invoice_amount = fields.Monetary(currency_field="currency_id")
    invoice_balance = fields.Monetary(currency_field="currency_id")
    invoice_state = fields.Char()

    @api.depends("invoice_number", "external_invoice_id")
    def _compute_name(self):
        for candidate in self:
            candidate.name = (
                candidate.invoice_number or candidate.external_invoice_id or ""
            )

    @api.private
    def _invoice_payload(self):
        self.ensure_one()
        return {
            "external_invoice_id": self.external_invoice_id,
            "number": self.invoice_number,
            "issue_date": self.issue_date,
            "due_date": self.due_date,
            "amount": self.invoice_amount,
            "balance": self.invoice_balance,
            "state": self.invoice_state,
            "document_kind": self.document_kind,
        }


class CollectionAllocationDebtPicker(models.TransientModel):
    _name = "collection.allocation.debt.picker"
    _description = "Add Customer Debt"

    allocation_id = fields.Many2one(
        comodel_name="collection.allocation",
        required=True,
        ondelete="cascade",
    )
    currency_id = fields.Many2one(
        related="allocation_id.currency_id",
    )
    company_id = fields.Many2one(
        related="allocation_id.company_id",
    )
    candidate_ids = fields.One2many(
        comodel_name="collection.allocation.debt.candidate",
        inverse_name="picker_id",
        string="Available Debts",
    )
    selected_ids = fields.Many2many(
        comodel_name="collection.allocation.debt.candidate",
        relation="collection_allocation_debt_picker_selected_rel",
        column1="picker_id",
        column2="candidate_id",
        string="Debts",
        domain="[('picker_id', '=', id)]",
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.filtered(
            lambda picker: not picker.candidate_ids
        )._load_missing_candidates()
        return records

    @api.private
    def _load_missing_candidates(self):
        Candidate = self.env["collection.allocation.debt.candidate"]
        for picker in self:
            vals_list = [
                picker._candidate_vals(line_vals)
                for line_vals in picker.allocation_id._missing_customer_debt_lines()
            ]
            if vals_list:
                Candidate.create(vals_list)

    @api.private
    def _candidate_vals(self, line_vals):
        self.ensure_one()
        return {
            "picker_id": self.id,
            "external_invoice_id": line_vals.get("external_invoice_id") or False,
            "document_kind": line_vals.get("document_kind") or "invoice",
            "invoice_number": line_vals.get("invoice_number") or False,
            "issue_date": line_vals.get("issue_date") or False,
            "due_date": line_vals.get("due_date") or False,
            "invoice_amount": line_vals.get("invoice_amount") or 0.0,
            "invoice_balance": line_vals.get("invoice_balance") or 0.0,
            "invoice_state": line_vals.get("invoice_state") or False,
        }

    def action_add_debts(self):
        self.ensure_one()
        selected = self.selected_ids.filtered(lambda rec: rec.picker_id == self)
        invoices = [candidate._invoice_payload() for candidate in selected]
        self.allocation_id._insert_selected_debt_lines(invoices)
        return {"type": "ir.actions.act_window_close"}
