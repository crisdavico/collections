# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL
from odoo.tools.translate import _

from .collection_common import (
    ADMIN_EDITABLE_SHEET_STATES,
    SELLER_DECLARATION_STATES,
    SELLER_SHEET_STATES,
    record_id,
    sanitize_voucher_commands,
)

_STATE_WRITE_ACTIONS = {
    "proposal": "action_confirm",
    "closed": "action_close",
    "cancelled": "action_cancel",
    "submitted": "_dispatch_submitted_state_write",
}
_VALIDATED_COLLECTIONS = "validated_collections"


class CollectionSheet(models.Model):
    _name = "collection.sheet"
    _description = "Collection Sheet"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default="/",
    )
    seller_id = fields.Many2one(
        comodel_name="res.users",
        string="Seller",
        required=True,
        readonly=True,
        domain=[("share", "=", False)],
        ondelete="restrict",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    voucher_ids = fields.One2many(
        comodel_name="collection.voucher",
        inverse_name="sheet_id",
        string="Vouchers",
    )
    allocation_ids = fields.One2many(
        comodel_name="collection.allocation",
        inverse_name="sheet_id",
        string="Allocations",
    )
    debt_line_ids = fields.One2many(
        comodel_name="collection.allocation.line",
        inverse_name="sheet_id",
        string="Debt",
    )
    date_from = fields.Date(compute="_compute_dates", store=True)
    date_to = fields.Date(compute="_compute_dates", store=True)
    state = fields.Selection(
        selection=[
            ("open", "Open"),
            ("submitted", "Submitted by Seller"),
            ("proposal", "Proposal"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        default="open",
        required=True,
        tracking=True,
        copy=False,
    )
    document_review_enabled = fields.Boolean(
        compute="_compute_document_review_enabled",
    )
    voucher_count = fields.Integer(compute="_compute_voucher_count")

    @api.depends("voucher_ids", "voucher_ids.create_date")
    def _compute_dates(self):
        for sheet in self:
            create_dates = [
                fields.Date.to_date(voucher.create_date)
                for voucher in sheet.voucher_ids
                if voucher.create_date
            ]
            sheet.date_from = min(create_dates) if create_dates else False
            sheet.date_to = max(create_dates) if create_dates else False

    @api.depends_context("company")
    def _compute_document_review_enabled(self):
        enabled = bool(self.env.company._document_review_enabled())
        for sheet in self:
            sheet.document_review_enabled = enabled

    @api.depends("voucher_ids")
    def _compute_voucher_count(self):
        for sheet in self:
            sheet.voucher_count = len(sheet.voucher_ids)

    @api.private
    def _open_sheets_for_seller(self, seller, company):
        return self.search(
            [
                ("seller_id", "=", record_id(seller)),
                ("company_id", "=", record_id(company)),
                ("state", "in", list(SELLER_SHEET_STATES)),
            ]
        )

    @api.private
    def _submitted_sheets_for_seller(self, seller, company):
        return self.search(
            [
                ("seller_id", "=", record_id(seller)),
                ("company_id", "=", record_id(company)),
                ("state", "in", list(SELLER_DECLARATION_STATES)),
            ]
        )

    @api.private
    def _lock_open_sheet_for_seller(self, seller, company):
        self.env.cr.execute(
            SQL(
                "SELECT pg_advisory_xact_lock(hashtext(%s || %s), %s)",
                "collection.sheet.open.",
                str(int(record_id(company))),
                int(record_id(seller)),
            )
        )

    @api.private
    def _raise_if_seller_has_open_sheet(self, seller, company):
        if self._open_sheets_for_seller(seller, company):
            raise UserError(_("This seller already has an open collection sheet."))

    @api.private
    def _resolve_open_sheet_id_for_create(self, seller_id, company_id):
        self._lock_open_sheet_for_seller(seller_id, company_id)
        opens = self._open_sheets_for_seller(seller_id, company_id)
        if len(opens) > 1:
            raise UserError(_("This seller has more than one open collection sheet."))
        if len(opens) == 1:
            return opens.id
        return self.create({"seller_id": seller_id, "company_id": company_id}).id

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        opening_keys = set()
        for vals in vals_list:
            company_id = vals.get("company_id") or self.env.company.id
            company = self.env["res.company"].browse(company_id)
            company._assert_new_work(vals.get("seller_id"))
            if vals.get("name", "/") in (False, "/", "New"):
                vals["name"] = (
                    sequence.with_company(company_id).next_by_code("collection.sheet")
                    or "/"
                )
            if "voucher_ids" in vals:
                vals["voucher_ids"] = sanitize_voucher_commands(vals["voucher_ids"])
            if vals.get("state") and vals["state"] not in SELLER_SHEET_STATES:
                raise UserError(_("Collection sheets can only be created in Open."))
            seller_id = vals.get("seller_id")
            if seller_id:
                key = (company_id, seller_id)
                if key in opening_keys:
                    raise UserError(
                        _("This seller already has an open collection sheet.")
                    )
                self._lock_open_sheet_for_seller(seller_id, company_id)
                self._raise_if_seller_has_open_sheet(seller_id, company_id)
                opening_keys.add(key)
        return super().create(vals_list)

    def write(self, vals):
        if "seller_id" in vals:
            raise UserError(_("The sheet seller cannot be changed."))
        if "state" in vals and not self.env.context.get(
            "collection_sheet_audited_state"
        ):
            target = vals["state"]
            rest = {key: value for key, value in vals.items() if key != "state"}
            if rest:
                if target == "submitted":
                    raise UserError(
                        _(
                            "Sheet state can only be changed via Seller Close, "
                            "Confirm, Close, Cancel, or Reinstate."
                        )
                    )
                super().write(rest)
            action_name = _STATE_WRITE_ACTIONS.get(target)
            if action_name:
                return getattr(self, action_name)()
            raise UserError(
                _(
                    "Sheet state can only be changed via Seller Close, Confirm, "
                    "Close, Cancel, or Reinstate."
                )
            )
        if "voucher_ids" in vals:
            if not self.env.context.get("collection_sheet_unlinking") and any(
                sheet.state not in ADMIN_EDITABLE_SHEET_STATES for sheet in self
            ):
                raise UserError(
                    _(
                        "Closed collection sheets cannot change membership. "
                        "Reopen first."
                    )
                )
            vals = dict(vals)
            vals["voucher_ids"] = sanitize_voucher_commands(vals["voucher_ids"])
        return super().write(vals)

    def unlink(self):
        if not self.env.context.get("collection_sheet_unlinking"):
            return self.with_context(collection_sheet_unlinking=True).unlink()
        return super().unlink()

    @api.ondelete(at_uninstall=False)
    def _unlink_open_sheets_and_cascade_allocations(self):
        if any(sheet.state not in SELLER_SHEET_STATES for sheet in self):
            raise UserError(_("Only open collection sheets can be deleted."))
        self.allocation_ids.unlink()

    def action_seller_close(self, cash_on_hand=None, commission_withheld=None):
        for sheet in self:
            self._lock_open_sheet_for_seller(sheet.seller_id, sheet.company_id)
            # Lock is worthless without a re-read: cached state/membership can
            # predate the lock and hide a concurrent close or voucher insert.
            sheet.invalidate_recordset(["state", "voucher_ids"])
            if sheet.state not in SELLER_SHEET_STATES:
                raise UserError(
                    _("Only open collection sheets can be closed by the seller.")
                )
        self._raise_if_draft_vouchers_block_seller_close()
        return self.with_context(collection_sheet_audited_state=True).write(
            {"state": "submitted"}
        )

    @api.private
    def _cash_collected_total(self):
        """Return SUM of cash voucher amounts on this sheet (company currency)."""
        self.ensure_one()
        return self.cash_collected or 0.0

    @api.private
    def _raise_if_draft_vouchers_block_seller_close(self):
        drafts = self.mapped("voucher_ids").filtered(
            lambda voucher: voucher.state == "draft"
        )
        if not drafts:
            return
        names = ", ".join(drafts.mapped("name"))
        raise UserError(_("Seller Close cannot include draft vouchers: %s", names))

    def action_declare_cash(self, cash_on_hand, commission_withheld):
        if any(sheet.state not in SELLER_DECLARATION_STATES for sheet in self):
            raise UserError(_("Only submitted collection sheets can declare cash."))
        return self.write(
            {
                "cash_on_hand": cash_on_hand,
                "commission_withheld": commission_withheld,
                "cash_declared_at": fields.Datetime.now(),
                "cash_declared_by": self.env.user.id,
            }
        )

    @api.private
    def _dispatch_submitted_state_write(self):
        states = set(self.mapped("state"))
        if len(states) != 1:
            raise UserError(
                _("Seller Close and Reinstate cannot run on mixed sheet states.")
            )
        current = next(iter(states))
        if current in SELLER_SHEET_STATES:
            return self.action_seller_close()
        if current == "cancelled":
            return self.action_reinstate()
        raise UserError(_("Only open collection sheets can be closed by the seller."))

    def action_confirm(self):
        if any(sheet.state != "submitted" for sheet in self):
            raise UserError(_("Only submitted sheets can be confirmed."))
        for sheet in self:
            if any(
                voucher.state != _VALIDATED_COLLECTIONS for voucher in sheet.voucher_ids
            ):
                raise UserError(
                    _(
                        "Confirm requires every member voucher to be validated "
                        "by collections."
                    )
                )
            collected = sheet._cash_collected_total()
            currency = sheet.company_id.currency_id
            if (
                currency.compare_amounts(collected, 0.0) > 0
                and not sheet.cash_declared_at
            ):
                raise UserError(
                    _(
                        "Confirm requires Declare Cash when the sheet has "
                        "collected cash."
                    )
                )
        return self.with_context(collection_sheet_audited_state=True).write(
            {"state": "proposal"}
        )

    def action_close(self):
        if any(sheet.state != "proposal" for sheet in self):
            raise UserError(_("Only proposal sheets can be closed."))
        self._mark_draft_receipts_closed()
        allocations = self.mapped("allocation_ids")
        if allocations:
            allocations.with_context(collection_allocation_audited_state=True).write(
                {"state": "confirmed"}
            )
        result = self.with_context(collection_sheet_audited_state=True).write(
            {"state": "closed"}
        )
        if allocations:
            allocations._check_sheet_state_iff()
        return result

    def action_cancel(self):
        if any(
            sheet.state not in ("submitted", "proposal", "closed") for sheet in self
        ):
            raise UserError(
                _("Only submitted, proposal, or closed sheets can be cancelled.")
            )
        self._reopen_closed_receipts()
        allocations = self.mapped("allocation_ids")
        result = self.with_context(collection_sheet_audited_state=True).write(
            {"state": "cancelled"}
        )
        if allocations:
            allocations.with_context(collection_allocation_audited_state=True).write(
                {"state": "draft"}
            )
            allocations._check_sheet_state_iff()
        return result

    @api.private
    def _mark_draft_receipts_closed(self):
        """Close every local draft receipt. Skip issued. No connector."""
        self.mapped("allocation_ids.receipt_ids")._action_mark_closed()

    @api.private
    def _reopen_closed_receipts(self):
        """Reopen local closed receipts to draft. Skip issued."""
        self.mapped("allocation_ids.receipt_ids")._action_reopen_closed()

    def action_reinstate(self):
        if any(sheet.state != "cancelled" for sheet in self):
            raise UserError(_("Only cancelled sheets can be reinstated."))
        allocations = self.mapped("allocation_ids")
        result = self.with_context(collection_sheet_audited_state=True).write(
            {"state": "submitted"}
        )
        if allocations:
            allocations._check_sheet_state_iff()
        return result

    def action_open_document_review(self):
        self.ensure_one()
        self.env["collection.voucher"]._ensure_document_review_enabled()
        self._ensure_saved_sheet()
        if self.state not in ADMIN_EDITABLE_SHEET_STATES:
            raise UserError(
                _("Document Review is only available on open collection sheets.")
            )
        action = self.env["ir.actions.actions"]._for_xml_id(
            "collection.action_collection_document_review"
        )
        action["params"] = dict(action.get("params") or {}, sheet_id=self.id)
        return action

    def action_open_vouchers(self):
        self.ensure_one()
        self._ensure_saved_sheet()
        return {
            "type": "ir.actions.act_window",
            "name": _("Vouchers"),
            "res_model": "collection.voucher",
            "view_mode": "list,kanban,form",
            "domain": [("sheet_id", "=", self.id)],
            "context": {
                "default_sheet_id": self.id,
                "default_seller_id": self.seller_id.id,
            },
        }

    @api.private
    def _ensure_saved_sheet(self):
        self.ensure_one()
        if isinstance(self.id, bool) or not isinstance(self.id, int) or self.id <= 0:
            raise UserError(_("This action requires a saved collection sheet."))
