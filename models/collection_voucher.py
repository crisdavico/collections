# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class CollectionVoucher(models.Model):
    _name = "collection.voucher"
    _description = "Payment Voucher"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default="/",
    )
    customer_identification = fields.Char(
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("new", "New"),
            ("validated", "Validated"),
            ("rejected", "Rejected"),
        ],
        default="new",
        required=True,
        tracking=True,
        copy=False,
        group_expand=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    payment_ids = fields.One2many(
        comodel_name="collection.voucher.line",
        inverse_name="voucher_id",
        string="Payment Lines",
    )

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            # Registration time is ORM-owned; callers must not forge create_date.
            vals.pop("create_date", None)
            vals.pop("write_date", None)
            if vals.get("name", "/") in (False, "/", "New"):
                vals["name"] = sequence.next_by_code("collection.voucher") or "/"
        return super().create(vals_list)

    def action_validate(self):
        if any(voucher.state != "new" for voucher in self):
            raise UserError(_("Only new vouchers can be validated."))
        self._ensure_no_pending_attached_review()
        # write() so mail.thread field tracking records the state change
        return self.write({"state": "validated"})

    def action_reject(self):
        if any(voucher.state != "new" for voucher in self):
            raise UserError(_("Only new vouchers can be rejected."))
        return self.write({"state": "rejected"})

    @api.private
    def _ensure_no_pending_attached_review(self):
        pending = self.mapped("payment_ids").filtered(
            lambda line: line.review_status == "pending"
        )
        if pending._lines_with_attachment():
            raise UserError(
                _("Cannot validate while attached payment lines are pending review.")
            )

    @api.ondelete(at_uninstall=False)
    def _unlink_if_new(self):
        if any(voucher.state != "new" for voucher in self):
            raise UserError(_("You can only delete vouchers in the New state."))
