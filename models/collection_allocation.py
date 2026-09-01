# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tools.translate import _

_FROZEN_FIELDS = frozenset({"line_ids", "voucher_ids", "partner_id", "sheet_id"})


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
            ("confirmed", "Confirmed"),
            ("validated", "Validated"),
            ("rejected", "Rejected"),
        ],
        default="confirmed",
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
    line_ids = fields.One2many(
        comodel_name="collection.allocation.line",
        inverse_name="allocation_id",
        string="Lines",
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
    total_debt = fields.Monetary(currency_field="currency_id")
    residual = fields.Monetary(
        compute="_compute_totals",
        store=True,
        tracking=True,
        currency_field="currency_id",
    )
    residual_reason = fields.Selection(
        selection=[
            ("on_account", "On Account"),
            ("advance", "Advance"),
            ("pending_invoice", "Pending Invoice"),
            ("rounding", "Rounding"),
        ],
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
    )
    def _compute_totals(self):
        for allocation in self:
            total_vouchers = sum(
                voucher.amount or 0.0 for voucher in allocation.voucher_ids
            )
            total_applied = sum(
                line.amount_applied or 0.0 for line in allocation.line_ids
            )
            allocation.total_vouchers = total_vouchers
            allocation.total_applied = total_applied
            allocation.residual = total_vouchers - total_applied

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if "voucher_ids" in vals:
                vals["voucher_ids"] = self._sanitize_voucher_commands(
                    vals["voucher_ids"]
                )
            if vals.get("name", "/") in (False, "/", "New"):
                company_id = self.env.company.id
                sheet_id = vals.get("sheet_id")
                if sheet_id:
                    sheet = self.env["collection.sheet"].browse(sheet_id)
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
        if _FROZEN_FIELDS & set(vals) and any(
            allocation.state != "confirmed" for allocation in self
        ):
            raise UserError(
                _("Validated or rejected allocations cannot change membership.")
            )
        if "voucher_ids" in vals:
            vals = dict(vals)
            vals["voucher_ids"] = self._sanitize_voucher_commands(vals["voucher_ids"])
        if "state" in vals and not self.env.context.get(
            "collection_allocation_audited_state"
        ):
            target = vals["state"]
            rest = {key: value for key, value in vals.items() if key != "state"}
            if rest:
                super().write(rest)
            if target == "validated":
                return self.action_validate()
            if target == "rejected":
                return self.action_reject()
            raise UserError(
                _("Allocation state can only be changed via Validate or Reject.")
            )
        return super().write(vals)

    def action_validate(self):
        if any(allocation.state != "confirmed" for allocation in self):
            raise UserError(_("Only confirmed allocations can be validated."))
        return self.with_context(collection_allocation_audited_state=True).write(
            {
                "state": "validated",
                "reviewed_by": self.env.user.id,
                "reviewed_at": fields.Datetime.now(),
            }
        )

    def action_reject(self):
        if any(allocation.state != "confirmed" for allocation in self):
            raise UserError(_("Only confirmed allocations can be rejected."))
        return self.with_context(collection_allocation_audited_state=True).write(
            {
                "state": "rejected",
                "reviewed_by": self.env.user.id,
                "reviewed_at": fields.Datetime.now(),
            }
        )

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

    @api.constrains("residual", "residual_reason", "state", "currency_id")
    def _check_residual(self):
        for allocation in self:
            if allocation.state != "confirmed":
                continue
            currency = allocation.currency_id
            residual = allocation.residual or 0.0
            if currency.compare_amounts(residual, 0.0) < 0:
                raise ValidationError(
                    _("Confirmed allocations cannot have a negative residual.")
                )
            if (
                currency.compare_amounts(residual, 0.0) > 0
                and not allocation.residual_reason
            ):
                raise ValidationError(
                    _("A residual reason is required when the residual is positive.")
                )

    @api.ondelete(at_uninstall=False)
    def _unlink_if_no_revisions(self):
        if any(allocation.revision_ids for allocation in self):
            raise UserError(_("Allocations with revisions cannot be deleted."))
