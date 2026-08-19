# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import SQL
from odoo.tools.translate import _


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
    date_from = fields.Date(compute="_compute_dates", store=True)
    date_to = fields.Date(compute="_compute_dates", store=True)
    state = fields.Selection(
        selection=[
            ("open", "Open"),
            ("closed", "Closed"),
        ],
        default="open",
        required=True,
        tracking=True,
        copy=False,
    )
    document_review_enabled = fields.Boolean(
        compute="_compute_document_review_enabled",
    )

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

    @api.private
    def _open_sheets_for_seller(self, seller):
        seller_id = seller.id if isinstance(seller, models.Model) else seller
        return self.search(
            [
                ("seller_id", "=", seller_id),
                ("state", "=", "open"),
            ]
        )

    @api.private
    def _lock_open_sheet_for_seller(self, seller):
        seller_id = seller.id if isinstance(seller, models.Model) else seller
        self.env.cr.execute(
            SQL(
                "SELECT pg_advisory_xact_lock(hashtext(%s), %s)",
                "collection.sheet.open",
                int(seller_id),
            )
        )

    @api.private
    def _raise_if_seller_has_open_sheet(self, seller):
        if self._open_sheets_for_seller(seller):
            raise UserError(_("This seller already has an open collection sheet."))

    @api.private
    def _resolve_open_sheet_id_for_create(self, seller_id):
        self._lock_open_sheet_for_seller(seller_id)
        opens = self._open_sheets_for_seller(seller_id)
        if len(opens) > 1:
            raise UserError(_("This seller has more than one open collection sheet."))
        if len(opens) == 1:
            return opens.id
        return self.create({"seller_id": seller_id}).id

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        opening_sellers = set()
        for vals in vals_list:
            if vals.get("name", "/") in (False, "/", "New"):
                company_id = vals.get("company_id") or self.env.company.id
                vals["name"] = (
                    sequence.with_company(company_id).next_by_code("collection.sheet")
                    or "/"
                )
            if "voucher_ids" in vals:
                vals["voucher_ids"] = self._sanitize_voucher_commands(
                    vals["voucher_ids"]
                )
            resulting_state = vals.get("state") or "open"
            seller_id = vals.get("seller_id")
            if resulting_state == "open" and seller_id:
                if seller_id in opening_sellers:
                    raise UserError(
                        _("This seller already has an open collection sheet.")
                    )
                self._lock_open_sheet_for_seller(seller_id)
                self._raise_if_seller_has_open_sheet(seller_id)
                opening_sellers.add(seller_id)
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
            if target == "closed":
                return self.action_close()
            if target == "open":
                return self.action_reopen()
            raise UserError(_("Sheet state can only be changed via Close or Reopen."))
        if "voucher_ids" in vals:
            if not self.env.context.get("collection_sheet_unlinking") and any(
                sheet.state == "closed" for sheet in self
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

    def action_close(self):
        if any(sheet.state != "open" for sheet in self):
            raise UserError(_("Only open sheets can be closed."))
        return self.with_context(collection_sheet_audited_state=True).write(
            {"state": "closed"}
        )

    def action_reopen(self):
        if any(sheet.state != "closed" for sheet in self):
            raise UserError(_("Only closed sheets can be reopened."))
        seen_sellers = set()
        for sheet in self:
            seller_id = sheet.seller_id.id
            if seller_id in seen_sellers:
                raise UserError(_("This seller already has an open collection sheet."))
            self._raise_if_seller_has_open_sheet(sheet.seller_id)
            seen_sellers.add(seller_id)
        return self.with_context(collection_sheet_audited_state=True).write(
            {"state": "open"}
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

    def action_open_document_review(self):
        self.ensure_one()
        self.env["collection.voucher"]._ensure_document_review_enabled()
        self._ensure_saved_sheet()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "collection.action_collection_document_review"
        )
        action["params"] = dict(action.get("params") or {}, sheet_id=self.id)
        return action

    @api.private
    def _ensure_saved_sheet(self):
        self.ensure_one()
        if isinstance(self.id, bool) or not isinstance(self.id, int) or self.id <= 0:
            raise UserError(_("Document Review requires a saved collection sheet."))
