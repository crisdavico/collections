# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class CollectionAllocationRevision(models.Model):
    _name = "collection.allocation.revision"
    _description = "Collection Allocation Revision"
    _order = "allocation_id, revision"

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
    revision = fields.Integer(required=True)
    request_id = fields.Char(required=True, index=True)
    content_hash = fields.Char(required=True)
    confirmed_by = fields.Many2one(
        comodel_name="res.users",
        required=True,
        ondelete="restrict",
    )
    confirmed_at = fields.Datetime(required=True)
    total_vouchers = fields.Monetary(currency_field="currency_id")
    total_applied = fields.Monetary(currency_field="currency_id")
    total_debt = fields.Monetary(currency_field="currency_id")
    residual = fields.Monetary(currency_field="currency_id")
    residual_reason = fields.Selection(
        selection=[
            ("on_account", "On Account"),
            ("advance", "Advance"),
            ("pending_invoice", "Pending Invoice"),
            ("rounding", "Rounding"),
        ],
    )

    _allocation_revision_uniq = models.Constraint(
        "UNIQUE(allocation_id, revision)",
        "Revision number must be unique per allocation.",
    )
    _request_id_uniq = models.Constraint(
        "UNIQUE(request_id)",
        "Allocation request id must be unique.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("collection_allocation_revision"):
            raise UserError(
                _("Allocation revisions can only be created by the allocation flow.")
            )
        return super().create(vals_list)

    def write(self, vals):
        if self:
            raise UserError(_("Allocation revisions cannot be modified."))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_forbidden(self):
        if self.env.context.get("collection_allocation_parent_unlink"):
            return
        raise UserError(_("Allocation revisions cannot be deleted."))
