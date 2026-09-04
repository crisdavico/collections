# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tools.translate import _

_FROZEN_FIELDS = frozenset(
    {"line_ids", "voucher_ids", "receipt_ids", "partner_id", "sheet_id"}
)
_DRAFT_SHEET_STATES = frozenset({"open", "proposal", "cancelled"})
_CONFIRMED_SHEET_STATE = "closed"
_FROZEN_SHEET_STATES = frozenset({"closed", "cancelled"})


class CollectionAllocation(models.Model):
    _name = "collection.allocation"
    _description = "Collection Allocation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default="/",
    )
    sheet_id = fields.Many2one(
        comodel_name="collection.sheet",
        string="Collection Sheet",
        required=True,
        ondelete="restrict",
        index=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        required=True,
        tracking=True,
        ondelete="restrict",
        index=True,
    )
    seller_id = fields.Many2one(
        related="sheet_id.seller_id",
        store=True,
    )
    company_id = fields.Many2one(
        related="sheet_id.company_id",
        store=True,
        required=True,
        precompute=True,
        index=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
        ],
        default="draft",
        required=True,
        tracking=True,
        copy=False,
        group_expand=True,
    )
    revision = fields.Integer(default=1, required=True)
    voucher_ids = fields.One2many(
        comodel_name="collection.voucher",
        inverse_name="allocation_id",
        string="Vouchers",
    )
    voucher_count = fields.Integer(compute="_compute_voucher_count")
    line_ids = fields.One2many(
        comodel_name="collection.allocation.line",
        inverse_name="allocation_id",
        string="Lines",
    )
    receipt_ids = fields.One2many(
        comodel_name="collection.receipt",
        inverse_name="allocation_id",
        string="Receipts",
    )
    revision_ids = fields.One2many(
        comodel_name="collection.allocation.revision",
        inverse_name="allocation_id",
        string="Revisions",
        copy=False,
        readonly=True,
    )
    total_vouchers = fields.Monetary(
        compute="_compute_totals",
        store=True,
        tracking=True,
        currency_field="currency_id",
    )
    total_applied = fields.Monetary(
        compute="_compute_totals",
        store=True,
        tracking=True,
        currency_field="currency_id",
    )
    total_debt = fields.Monetary(
        compute="_compute_totals",
        store=True,
        tracking=True,
        currency_field="currency_id",
    )
    total_invoices = fields.Monetary(
        compute="_compute_totals",
        store=True,
        tracking=True,
        currency_field="currency_id",
    )
    total_quotations = fields.Monetary(
        compute="_compute_totals",
        store=True,
        tracking=True,
        currency_field="currency_id",
    )
    residual = fields.Monetary(
        compute="_compute_totals",
        store=True,
        tracking=True,
        currency_field="currency_id",
    )
    reviewed_by = fields.Many2one(
        comodel_name="res.users",
        copy=False,
    )
    reviewed_at = fields.Datetime(copy=False)

    _sheet_partner_uniq = models.Constraint(
        "UNIQUE(sheet_id, partner_id)",
        "Only one allocation is allowed per customer per sheet.",
    )

    @api.depends(
        "voucher_ids.amount",
        "line_ids.amount_applied",
        "line_ids.invoice_balance",
        "line_ids.document_kind",
    )
    def _compute_totals(self):
        for allocation in self:
            total_vouchers = sum(
                voucher.amount or 0.0 for voucher in allocation.voucher_ids
            )
            total_applied = sum(
                line.amount_applied or 0.0 for line in allocation.line_ids
            )
            total_invoices = 0.0
            total_quotations = 0.0
            total_debt = 0.0
            for line in allocation.line_ids:
                balance = line.invoice_balance or 0.0
                total_debt += balance
                if line.document_kind == "quotation":
                    total_quotations += balance
                else:
                    total_invoices += balance
            allocation.total_vouchers = total_vouchers
            allocation.total_applied = total_applied
            allocation.total_debt = total_debt
            allocation.total_invoices = total_invoices
            allocation.total_quotations = total_quotations
            allocation.residual = total_debt - total_applied

    @api.depends("voucher_ids")
    def _compute_voucher_count(self):
        for allocation in self:
            allocation.voucher_count = len(allocation.voucher_ids)

    @api.model
    @api.private
    def _prepare_customer_debt_lines(self, sheet, partner):
        """Map outstanding ERP invoices to allocation line vals (applied 0)."""
        if not sheet or not partner:
            return []
        company = sheet.company_id or self.env.company
        connector = company.collection_connector_id
        if not connector or not connector.active:
            return []
        binding = self.env["collection.connector.customer.binding"].search(
            [
                ("connector_id", "=", connector.id),
                ("partner_id", "=", partner.id),
            ],
            limit=1,
        )
        if not binding:
            return []
        try:
            debt = connector.with_company(company).get_customer_debt(
                sheet.seller_id.id,
                binding.identification,
            )
        except UserError:
            return []
        return [
            self._customer_debt_line_vals(invoice)
            for invoice in debt.get("invoices") or []
        ]

    @api.model
    @api.private
    def _customer_debt_line_vals(self, invoice):
        """Map one ERP invoice dict to allocation line vals (applied 0)."""
        return {
            "external_invoice_id": invoice.get("external_invoice_id") or False,
            "invoice_number": invoice.get("number") or False,
            "issue_date": invoice.get("issue_date") or False,
            "due_date": invoice.get("due_date") or False,
            "invoice_amount": invoice.get("amount") or 0.0,
            "invoice_balance": invoice.get("balance") or 0.0,
            "invoice_state": invoice.get("state") or False,
            "amount_applied": 0.0,
            "document_kind": (
                invoice.get("document_kind")
                if invoice.get("document_kind") in ("invoice", "quotation")
                else "invoice"
            ),
        }

    @api.onchange("partner_id", "sheet_id")
    def _onchange_customer_debt_lines(self):
        if self.state == "confirmed":
            return
        line_vals = self._prepare_customer_debt_lines(self.sheet_id, self.partner_id)
        self.line_ids = [Command.clear()] + [Command.create(vals) for vals in line_vals]

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if "voucher_ids" in vals:
                vals["voucher_ids"] = self._sanitize_voucher_commands(
                    vals["voucher_ids"]
                )
            sheet = self.env["collection.sheet"].browse(vals.get("sheet_id") or [])
            if "line_ids" not in vals:
                partner = self.env["res.partner"].browse(vals.get("partner_id") or [])
                line_vals = self._prepare_customer_debt_lines(sheet, partner)
                vals["line_ids"] = [Command.create(item) for item in line_vals]
            if vals.get("name", "/") in (False, "/", "New"):
                company_id = self.env.company.id
                if sheet.company_id:
                    company_id = sheet.company_id.id
                vals["name"] = (
                    sequence.with_company(company_id).next_by_code(
                        "collection.allocation"
                    )
                    or "/"
                )
        return super().create(vals_list)

    def write(self, vals):
        if not self:
            return True
        if _FROZEN_FIELDS & set(vals) and self._membership_is_frozen():
            if any(allocation.state == "confirmed" for allocation in self):
                raise UserError(_("Confirmed allocations cannot change membership."))
            raise UserError(
                _(
                    "Closed or cancelled collection sheets cannot change "
                    "allocation membership."
                )
            )
        if "voucher_ids" in vals:
            vals = dict(vals)
            vals["voucher_ids"] = self._sanitize_voucher_commands(vals["voucher_ids"])
        if "state" in vals and not self.env.context.get(
            "collection_allocation_audited_state"
        ):
            raise UserError(
                _("Allocation state can only be changed via Close, Cancel, or Open.")
            )
        return super().write(vals)

    @api.private
    def _membership_is_frozen(self):
        return any(
            allocation.state == "confirmed"
            or allocation.sheet_id.state in _FROZEN_SHEET_STATES
            for allocation in self
        )

    def unlink(self):
        if not self:
            return True
        if not self.env.context.get("collection_allocation_parent_unlink"):
            return self.with_context(collection_allocation_parent_unlink=True).unlink()
        drafts = self.filtered(lambda allocation: allocation.state != "confirmed")
        vouchers = drafts.mapped("voucher_ids")
        if vouchers:
            models.Model.write(vouchers, {"allocation_id": False})
        return super().unlink()

    @api.private
    def _sanitize_voucher_commands(self, commands):
        sanitized = []
        for command in commands or []:
            if command and command[0] == Command.DELETE:
                sanitized.append(Command.unlink(command[1]))
            else:
                sanitized.append(command)
        return sanitized

    @api.constrains("partner_id", "voucher_ids")
    def _check_voucher_partners(self):
        for allocation in self:
            if not allocation.voucher_ids:
                continue
            partners = allocation.voucher_ids.partner_id
            if partners != allocation.partner_id:
                raise ValidationError(
                    _("Allocation vouchers must share the allocation customer.")
                )

    @api.constrains("sheet_id", "voucher_ids")
    def _check_voucher_sheets(self):
        for allocation in self:
            if not allocation.voucher_ids:
                continue
            sheets = allocation.voucher_ids.sheet_id
            if sheets != allocation.sheet_id:
                raise ValidationError(
                    _("Allocation vouchers must belong to the allocation sheet.")
                )

    @api.constrains("company_id", "voucher_ids")
    def _check_voucher_companies(self):
        for allocation in self:
            if not allocation.voucher_ids:
                continue
            companies = allocation.voucher_ids.company_id
            if companies != allocation.company_id:
                raise ValidationError(
                    _("Allocation vouchers must belong to the allocation company.")
                )

    @api.constrains("state", "sheet_id")
    def _check_sheet_state_iff(self):
        if self.env.context.get("collection_allocation_audited_state"):
            return
        for allocation in self:
            sheet = allocation.sheet_id
            if not sheet:
                continue
            if allocation.state == "draft" and sheet.state not in _DRAFT_SHEET_STATES:
                raise ValidationError(
                    _(
                        "Draft allocations must belong to an open, proposal, or "
                        "cancelled collection sheet."
                    )
                )
            if (
                allocation.state == "confirmed"
                and sheet.state != _CONFIRMED_SHEET_STATE
            ):
                raise ValidationError(
                    _("Confirmed allocations must belong to a closed collection sheet.")
                )

    @api.ondelete(at_uninstall=False)
    def _unlink_if_confirmed(self):
        if any(allocation.state == "confirmed" for allocation in self):
            raise UserError(_("Confirmed allocations cannot be deleted."))

    @api.private
    def _ensure_saved_allocation(self):
        self.ensure_one()
        if isinstance(self.id, bool) or not isinstance(self.id, int) or self.id <= 0:
            raise UserError(_("This action requires a saved collection allocation."))

    def action_open_debt_picker(self):
        self.ensure_one()
        self._ensure_writable_debt_picker()
        picker = self.env["collection.allocation.debt.picker"].create(
            {"allocation_id": self.id}
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Add Debt"),
            "res_model": "collection.allocation.debt.picker",
            "res_id": picker.id,
            "view_mode": "form",
            "target": "new",
        }

    @api.private
    def _missing_customer_debt_lines(self):
        """Outstanding ERP invoices not already snapshotted on this allocation."""
        self.ensure_one()
        existing = {
            line.external_invoice_id
            for line in self.line_ids
            if line.external_invoice_id
        }
        return [
            vals
            for vals in self._prepare_customer_debt_lines(
                self.sheet_id, self.partner_id
            )
            if vals.get("external_invoice_id") not in existing
        ]

    @api.private
    def _insert_selected_debt_lines(self, invoices):
        """Append selected connector debts as zero-applied snapshots."""
        self.ensure_one()
        self._ensure_writable_debt_picker()
        existing = {
            line.external_invoice_id
            for line in self.line_ids
            if line.external_invoice_id
        }
        commands = []
        for invoice in invoices or []:
            vals = self._customer_debt_line_vals(invoice)
            external_id = vals.get("external_invoice_id")
            if not external_id or external_id in existing:
                continue
            commands.append(Command.create(vals))
            existing.add(external_id)
        if commands:
            self.write({"line_ids": commands})

    @api.private
    def _ensure_writable_debt_picker(self):
        self.ensure_one()
        self._ensure_saved_allocation()
        if not self._membership_is_frozen():
            return
        if self.state == "confirmed":
            raise UserError(_("Confirmed allocations cannot change membership."))
        raise UserError(
            _(
                "Closed or cancelled collection sheets cannot change "
                "allocation membership."
            )
        )

    def action_open_vouchers(self):
        self.ensure_one()
        self._ensure_saved_allocation()
        return {
            "type": "ir.actions.act_window",
            "name": _("Vouchers"),
            "res_model": "collection.voucher",
            "view_mode": "list,kanban,form",
            "domain": [("allocation_id", "=", self.id)],
            "context": {
                "default_allocation_id": self.id,
                "default_partner_id": self.partner_id.id,
                "default_sheet_id": self.sheet_id.id,
            },
        }
