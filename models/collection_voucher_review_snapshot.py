# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_DOCUMENT_TYPE_SELECTION = [
    ("bank_transfer", "Bank Transfer"),
    ("check", "Check"),
    ("cash_deposit", "Cash Deposit"),
    ("unsupported", "Unsupported"),
]
_CHECK_TYPE_SELECTION = [
    ("common", "Common"),
    ("deferred", "Deferred"),
]


class CollectionVoucherReviewSnapshot(models.Model):
    _name = "collection.voucher.review.snapshot"
    _description = "Payment Voucher Review Snapshot"
    _order = "voucher_id, revision"

    voucher_id = fields.Many2one(
        comodel_name="collection.voucher",
        required=True,
        ondelete="cascade",
        index=True,
    )
    revision = fields.Integer(required=True)
    reviewer_id = fields.Many2one(
        comodel_name="res.users",
        required=True,
        ondelete="restrict",
    )
    reviewed_at = fields.Datetime(required=True)
    decision = fields.Selection(
        selection=[
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        required=True,
    )
    currency_id = fields.Many2one(
        related="voucher_id.currency_id",
        store=True,
    )
    company_id = fields.Many2one(
        related="voucher_id.company_id",
        store=True,
        required=True,
        precompute=True,
        index=True,
    )
    document_type = fields.Selection(selection=_DOCUMENT_TYPE_SELECTION)
    amount = fields.Monetary(currency_field="currency_id")
    from_account = fields.Char()
    to_account = fields.Char()
    voucher_number = fields.Char()
    voucher_date = fields.Date()
    check_number = fields.Char()
    check_bank = fields.Char()
    check_issue_date = fields.Date()
    check_payment_date = fields.Date()
    check_type = fields.Selection(selection=_CHECK_TYPE_SELECTION)

    _voucher_revision_uniq = models.Constraint(
        "UNIQUE(voucher_id, revision)",
        "Review snapshot revision must be unique per voucher.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("collection_review_snapshot"):
            raise UserError(
                _("Review snapshots can only be created by Document Review.")
            )
        return super().create(vals_list)

    def write(self, vals):
        if self:
            raise UserError(_("Review snapshots cannot be modified."))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_forbidden(self):
        raise UserError(_("Review snapshots cannot be deleted."))
