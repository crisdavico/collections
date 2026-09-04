# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import SQL
from odoo.tools.translate import _

_STATE_WRITE_ACTIONS = {
    "proposal": "action_confirm",
    "closed": "action_close",
    "cancelled": "action_cancel",
    "open": "action_open",
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

    def _compute_document_review_enabled(self):
        enabled = bool(self.env.company._document_review_enabled())
        for sheet in self:
            sheet.document_review_enabled = enabled

    @api.depends("voucher_ids")
    def _compute_voucher_count(self):
        for sheet in self:
            sheet.voucher_count = len(sheet.voucher_ids)

    @api.private
    def _company_id_of(self, company):
        return company.id if isinstance(company, models.Model) else company

    @api.private
    def _open_sheets_for_seller(self, seller, company):
        seller_id = seller.id if isinstance(seller, models.Model) else seller
        company_id = self._company_id_of(company)
        return self.search(
            [
                ("seller_id", "=", seller_id),
                ("company_id", "=", company_id),
                ("state", "=", "open"),
            ]
        )

    @api.private
    def _lock_open_sheet_for_seller(self, seller, company):
        seller_id = seller.id if isinstance(seller, models.Model) else seller
        company_id = int(self._company_id_of(company))
        self.env.cr.execute(
            SQL(
                "SELECT pg_advisory_xact_lock(hashtext(%s || %s), %s)",
                "collection.sheet.open.",
                str(company_id),
                int(seller_id),
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
                vals["voucher_ids"] = self._sanitize_voucher_commands(
                    vals["voucher_ids"]
                )
            resulting_state = vals.get("state") or "open"
            if resulting_state != "open":
                raise UserError(_("Collection sheets can only be created in Open."))
            seller_id = vals.get("seller_id")
            if resulting_state == "open" and seller_id:
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
                super().write(rest)
            action_name = _STATE_WRITE_ACTIONS.get(target)
            if action_name:
                return getattr(self, action_name)()
            raise UserError(
                _("Sheet state can only be changed via Confirm, Close, Cancel, or Open.")
            )
        if "voucher_ids" in vals:
            if not self.env.context.get("collection_sheet_unlinking") and any(
                sheet.state != "open" for sheet in self
            ):
                raise UserError(
                    _(
                        "Closed collection sheets cannot change membership. "
                        "Reopen first."
                    )
                )
            vals = dict(vals)
            vals["voucher_ids"] = self._sanitize_voucher_commands(vals["voucher_ids"])
        return super().write(vals)

    def unlink(self):
        if not self.env.context.get("collection_sheet_unlinking"):
            return self.with_context(collection_sheet_unlinking=True).unlink()
        return super().unlink()

    @api.ondelete(at_uninstall=False)
    def _unlink_if_no_allocations(self):
        if any(sheet.state != "open" for sheet in self):
            raise UserError(_("Only open collection sheets can be deleted."))
        drafts = self.mapped("allocation_ids")
        if drafts:
            drafts.unlink()

    def action_confirm(self):
        if any(sheet.state != "open" for sheet in self):
            raise UserError(_("Only open sheets can be confirmed."))
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
        return self.with_context(collection_sheet_audited_state=True).write(
            {"state": "proposal"}
        )

    def action_close(self):
        if any(sheet.state != "proposal" for sheet in self):
            raise UserError(_("Only proposal sheets can be closed."))
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
        if any(sheet.state not in ("proposal", "closed") for sheet in self):
            raise UserError(_("Only proposal or closed sheets can be cancelled."))
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

    def action_open(self):
        if any(sheet.state != "cancelled" for sheet in self):
            raise UserError(_("Only cancelled sheets can be opened."))
        seen_keys = set()
        for sheet in self:
            key = (sheet.company_id.id, sheet.seller_id.id)
            if key in seen_keys:
                raise UserError(_("This seller already has an open collection sheet."))
            self._lock_open_sheet_for_seller(sheet.seller_id, sheet.company_id)
            self._raise_if_seller_has_open_sheet(sheet.seller_id, sheet.company_id)
            seen_keys.add(key)
        allocations = self.mapped("allocation_ids")
        result = self.with_context(collection_sheet_audited_state=True).write(
            {"state": "open"}
        )
        if allocations:
            allocations._check_sheet_state_iff()
        return result

    @api.private
    def _sanitize_voucher_commands(self, commands):
        sanitized = []
        for command in commands or []:
            if command and command[0] == Command.DELETE:
                sanitized.append(Command.unlink(command[1]))
            else:
                sanitized.append(command)
        return sanitized

    def action_open_document_review(self):
        self.ensure_one()
        self.env["collection.voucher"]._ensure_document_review_enabled()
        self._ensure_saved_sheet()
        if self.state != "open":
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
