# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import binascii
from base64 import b64decode

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.mimetypes import guess_mimetype
from odoo.tools.translate import _


class CollectionVoucher(models.Model):
    _name = "collection.voucher"
    _description = "Payment Voucher"
    _inherit = ["mail.thread.main.attachment", "mail.activity.mixin"]
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
    seller_id = fields.Many2one(
        comodel_name="res.users",
        string="Seller",
        required=False,
        domain=[("share", "=", False)],
    )
    sheet_id = fields.Many2one(
        comodel_name="collection.sheet",
        string="Collection Sheet",
        ondelete="set null",
    )
    state = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="pending",
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
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    document_id = fields.Char(string="Document ID", index=True)
    document_type = fields.Selection(
        selection="_selection_document_type",
        required=True,
    )
    amount = fields.Monetary()
    from_account = fields.Char()
    to_account = fields.Char()
    voucher_number = fields.Char()
    voucher_date = fields.Date()
    check_number = fields.Char()
    check_bank = fields.Char()
    check_issue_date = fields.Date()
    check_payment_date = fields.Date()
    check_type = fields.Selection(
        selection=[
            ("common", "Common"),
            ("deferred", "Deferred"),
        ],
    )
    attachment_rotation = fields.Integer(default=0, copy=False)
    reviewed_by = fields.Many2one(
        comodel_name="res.users",
        copy=False,
    )
    reviewed_at = fields.Datetime(copy=False)
    review_snapshot_ids = fields.One2many(
        comodel_name="collection.voucher.review.snapshot",
        inverse_name="voucher_id",
        string="Review History",
        copy=False,
        readonly=True,
    )
    ocr_document_type = fields.Selection(
        selection=[
            ("bank_transfer", "Bank Transfer"),
            ("check", "Check"),
            ("cash_deposit", "Cash Deposit"),
            ("unsupported", "Unsupported"),
        ],
        string="Document Type",
        copy=False,
    )
    ocr_amount = fields.Monetary(
        string="Amount", copy=False, currency_field="currency_id"
    )
    ocr_from_account = fields.Char(string="From Account", copy=False)
    ocr_to_account = fields.Char(string="To Account", copy=False)
    ocr_voucher_number = fields.Char(string="Voucher Number", copy=False)
    ocr_voucher_date = fields.Date(string="Voucher Date", copy=False)
    ocr_check_number = fields.Char(string="Check Number", copy=False)
    ocr_check_bank = fields.Char(string="Check Bank", copy=False)
    ocr_check_issue_date = fields.Date(string="Check Issue Date", copy=False)
    ocr_check_payment_date = fields.Date(string="Check Payment Date", copy=False)
    ocr_check_type = fields.Selection(
        selection=[
            ("common", "Common"),
            ("deferred", "Deferred"),
        ],
        string="Check Type",
        copy=False,
    )
    seller_document_type = fields.Selection(
        selection=[
            ("bank_transfer", "Bank Transfer"),
            ("check", "Check"),
            ("cash_deposit", "Cash Deposit"),
            ("unsupported", "Unsupported"),
        ],
        string="Document Type",
        copy=False,
    )
    seller_amount = fields.Monetary(
        string="Amount", copy=False, currency_field="currency_id"
    )
    seller_from_account = fields.Char(string="From Account", copy=False)
    seller_to_account = fields.Char(string="To Account", copy=False)
    seller_voucher_number = fields.Char(string="Voucher Number", copy=False)
    seller_voucher_date = fields.Date(string="Voucher Date", copy=False)
    seller_check_number = fields.Char(string="Check Number", copy=False)
    seller_check_bank = fields.Char(string="Check Bank", copy=False)
    seller_check_issue_date = fields.Date(string="Check Issue Date", copy=False)
    seller_check_payment_date = fields.Date(string="Check Payment Date", copy=False)
    seller_check_type = fields.Selection(
        selection=[
            ("common", "Common"),
            ("deferred", "Deferred"),
        ],
        string="Check Type",
        copy=False,
    )

    _REVIEW_EDITABLE_FIELDS = frozenset(
        {
            "document_type",
            "amount",
            "from_account",
            "to_account",
            "voucher_number",
            "voucher_date",
            "check_number",
            "check_bank",
            "check_type",
            "check_issue_date",
            "check_payment_date",
        }
    )
    _ALLOWED_ROTATIONS = frozenset({0, 90, 180, 270})
    _DOCUMENT_TYPE_SELECTION = (
        ("bank_transfer", "Bank Transfer"),
        ("check", "Check"),
        ("cash_deposit", "Cash Deposit"),
        ("unsupported", "Unsupported"),
    )

    _document_id_uniq = models.Constraint(
        "UNIQUE(document_id)",
        "Document ID must be unique!",
    )
    _attachment_rotation_valid = models.Constraint(
        "CHECK(attachment_rotation IN (0, 90, 180, 270))",
        "Attachment rotation must be 0, 90, 180, or 270 degrees.",
    )
    _sheet_requires_seller = models.Constraint(
        "CHECK(sheet_id IS NULL OR seller_id IS NOT NULL)",
        "A voucher assigned to a sheet must have a seller.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            company = self.env["res.company"].browse(
                vals.get("company_id") or self.env.company.id
            )
            company._assert_new_work(vals.get("seller_id"), vals.get("document_type"))
        self._apply_open_sheet_auto_assign(vals_list)
        for vals in vals_list:
            # Registration time is ORM-owned; callers must not forge create_date.
            vals.pop("create_date", None)
            vals.pop("write_date", None)
            if vals.get("name", "/") in (False, "/", "New"):
                company_id = vals.get("company_id") or self.env.company.id
                vals["name"] = (
                    sequence.with_company(company_id).next_by_code("collection.voucher")
                    or "/"
                )
            if vals.get("sheet_id"):
                self._ensure_sheet_membership_unlocked(vals["sheet_id"])
        return super().create(vals_list)

    def _selection_document_type(self):
        """Allowed company types, plus each record's current value if later dropped."""
        allowed_codes = set(self.env.company.allowed_document_type_ids.mapped("code"))
        current_codes = {rec.document_type for rec in self if rec.document_type}
        keep = allowed_codes | current_codes
        return [item for item in self._DOCUMENT_TYPE_SELECTION if item[0] in keep]

    @api.private
    def _apply_open_sheet_auto_assign(self, vals_list):
        Sheet = self.env["collection.sheet"]
        resolved_sheet_ids = {}
        for vals in vals_list:
            seller_id = vals.get("seller_id")
            if seller_id and not vals.get("sheet_id"):
                company_id = vals.get("company_id") or self.env.company.id
                company = self.env["res.company"].browse(company_id)
                if not company.auto_create_sheet:
                    continue
                key = (company_id, seller_id)
                if key not in resolved_sheet_ids:
                    resolved_sheet_ids[key] = Sheet._resolve_open_sheet_id_for_create(
                        seller_id, company_id
                    )
                vals["sheet_id"] = resolved_sheet_ids[key]

    def write(self, vals):
        if not self:
            return True
        blocked = {
            f"{prefix}_{name}"
            for prefix in ("ocr", "seller")
            for name in self._REVIEW_EDITABLE_FIELDS
        }
        if blocked & set(vals):
            raise UserError(
                _("OCR and seller-confirmed fields cannot be modified after create.")
            )
        if "sheet_id" in vals:
            self._ensure_sheet_membership_unlocked(vals.get("sheet_id"))
        if "seller_id" in vals or "document_type" in vals:
            for voucher in self:
                seller = vals["seller_id"] if "seller_id" in vals else voucher.seller_id
                document_type = (
                    vals["document_type"] if "document_type" in vals else None
                )
                voucher.company_id._assert_new_work(seller, document_type)
        if "message_main_attachment_id" in vals:
            if len(self) > 1:
                return all(rec.write(vals) for rec in self)
            new_id = self._normalize_main_attachment_id(
                vals.get("message_main_attachment_id")
            )
            self._validate_main_attachment_id(new_id)
            vals = self._vals_with_review_reset_on_new_attachment(vals)
        if "state" in vals and not self.env.context.get("collection_audited_state"):
            target = vals["state"]
            if target in ("approved", "rejected"):
                rest = {key: value for key, value in vals.items() if key != "state"}
                if rest:
                    super().write(rest)
                if target == "approved":
                    return self.action_approve()
                return self.action_reject()
            if target == "pending" and "message_main_attachment_id" not in vals:
                raise UserError(
                    _(
                        "Cannot reopen a decided voucher without replacing "
                        "the attachment."
                    )
                )
        return super().write(vals)

    def action_approve(self):
        if any(voucher.state != "pending" for voucher in self):
            raise UserError(_("Only pending vouchers can be approved."))
        return self.with_context(collection_audited_state=True).write(
            {
                "state": "approved",
                "reviewed_by": self.env.user.id,
                "reviewed_at": fields.Datetime.now(),
            }
        )

    def action_reject(self):
        if any(voucher.state != "pending" for voucher in self):
            raise UserError(_("Only pending vouchers can be rejected."))
        return self.with_context(collection_audited_state=True).write(
            {
                "state": "rejected",
                "reviewed_by": self.env.user.id,
                "reviewed_at": fields.Datetime.now(),
            }
        )

    def action_create_collection_sheet(self):
        seller = self._seller_for_sheet_action()
        companies = self.mapped("company_id")
        if len(companies) != 1:
            raise UserError(_("All selected vouchers must belong to the same company."))
        company = companies
        Sheet = self.env["collection.sheet"]
        Sheet._raise_if_seller_has_open_sheet(seller, company)
        sheet = Sheet.create({"seller_id": seller.id, "company_id": company.id})
        self.sheet_id = sheet
        return {
            "type": "ir.actions.act_window",
            "name": _("Collection Sheet"),
            "res_model": "collection.sheet",
            "res_id": sheet.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.private
    def _seller_for_sheet_action(self):
        if not self:
            raise UserError(_("Select at least one payment voucher."))
        if any(not voucher.seller_id for voucher in self):
            raise UserError(_("All selected vouchers must have a seller."))
        sellers = self.mapped("seller_id")
        if len(sellers) != 1:
            raise UserError(_("All selected vouchers must belong to the same seller."))
        if any(voucher.sheet_id for voucher in self):
            raise UserError(_("Selected vouchers must not already belong to a sheet."))
        return sellers

    @api.private
    def _ensure_sheet_membership_unlocked(self, new_sheet_id):
        if self.env.context.get("collection_sheet_unlinking"):
            return
        closed_msg = _(
            "Closed collection sheets cannot change membership. Reopen first."
        )
        target = (
            self.env["collection.sheet"].browse(new_sheet_id)
            if new_sheet_id
            else self.env["collection.sheet"]
        )
        if target and target.state == "closed":
            raise UserError(closed_msg)
        for voucher in self:
            current = voucher.sheet_id
            if current and current.state == "closed" and current != target:
                raise UserError(closed_msg)

    @api.constrains("sheet_id", "seller_id")
    def _check_sheet_seller(self):
        for voucher in self:
            if not voucher.sheet_id:
                continue
            if not voucher.seller_id:
                raise ValidationError(
                    _("A voucher assigned to a sheet must have a seller.")
                )
            if voucher.seller_id != voucher.sheet_id.seller_id:
                raise ValidationError(_("Voucher seller must match the sheet seller."))

    @api.ondelete(at_uninstall=False)
    def _unlink_if_pending(self):
        if any(voucher.state != "pending" for voucher in self):
            raise UserError(_("You can only delete vouchers in the Pending state."))

    def _message_set_main_attachment_id(
        self, attachments, force=False, filter_xml=True
    ):
        """Restrict designated proof to image/* and PDF; extras never steal."""
        attachments = attachments.filtered(self._is_designated_proof_mimetype)
        return super()._message_set_main_attachment_id(
            attachments, force=force, filter_xml=filter_xml
        )

    @api.private
    def _is_designated_proof_mimetype(self, attachment):
        mime = attachment.mimetype or ""
        return mime.startswith("image/") or mime == "application/pdf"

    @api.model
    def _validate_attachment_payload(self, attachment):
        """Validate base64 + detected MIME before posting designated proof."""
        if not attachment:
            return
        raw = attachment
        if isinstance(raw, str):
            raw = raw.encode()
        try:
            decoded = b64decode(raw, validate=True)
        except binascii.Error as err:
            raise UserError(
                self.env._("Attachment content must be valid base64-encoded data.")
            ) from err
        mime = guess_mimetype(decoded) or ""
        if not (mime.startswith("image/") or mime == "application/pdf"):
            raise UserError(
                self.env._(
                    "Attachment must be an image or a PDF "
                    "(detected type: %(mimetype)s).",
                    mimetype=mime or "unknown",
                )
            )

    @api.constrains("attachment_rotation")
    def _check_attachment_rotation(self):
        for voucher in self:
            if voucher.attachment_rotation not in self._ALLOWED_ROTATIONS:
                raise UserError(
                    self.env._(
                        "Attachment rotation must be 0, 90, 180, or 270 degrees."
                    )
                )

    @api.model
    def get_review_queue(self, sheet_id=None):
        sheet = self._require_review_sheet(sheet_id)
        vouchers = self.search(
            [
                ("state", "=", "pending"),
                ("message_main_attachment_id", "!=", False),
                ("sheet_id", "=", sheet.id),
            ],
            order="id",
        )
        total = len(vouchers)
        return [
            voucher._review_queue_payload(position=index, total=total)
            for index, voucher in enumerate(vouchers, start=1)
        ]

    def action_review_approve(self, sheet_id=None, vals=None):
        sheet = self._require_review_sheet(sheet_id)
        self.ensure_one()
        self._ensure_review_sheet_member(sheet)
        self._lock_and_ensure_review_eligible()
        self._write_review_decision("approved", self._editable_review_vals(vals))
        return True

    def action_review_reject(self, sheet_id=None):
        sheet = self._require_review_sheet(sheet_id)
        self.ensure_one()
        self._ensure_review_sheet_member(sheet)
        self._lock_and_ensure_review_eligible()
        self._write_review_decision("rejected")
        return True

    def action_review_set_rotation(self, sheet_id=None, degrees=None):
        sheet = self._require_review_sheet(sheet_id)
        self.ensure_one()
        self._ensure_review_sheet_member(sheet)
        self._ensure_review_eligible()
        self.write(
            {"attachment_rotation": self._normalize_attachment_rotation(degrees)}
        )
        return True

    @api.private
    def _ensure_document_review_enabled(self):
        if not self.env.company._document_review_enabled():
            raise UserError(self.env._("Document Review is not enabled."))

    @api.private
    def _require_review_sheet(self, sheet_id):
        self._ensure_document_review_enabled()
        if isinstance(sheet_id, bool) or not isinstance(sheet_id, int) or sheet_id <= 0:
            raise UserError(
                self.env._("A valid collection sheet is required for Document Review.")
            )
        sheet = self.env["collection.sheet"].browse(sheet_id)
        if not sheet.exists():
            raise UserError(
                self.env._("A valid collection sheet is required for Document Review.")
            )
        return sheet

    @api.private
    def _ensure_review_sheet_member(self, sheet):
        self.ensure_one()
        if self.sheet_id != sheet:
            raise UserError(
                self.env._(
                    "This voucher does not belong to the selected collection sheet."
                )
            )

    @api.private
    def _normalize_main_attachment_id(self, value):
        if not value:
            return False
        if isinstance(value, models.BaseModel):
            return value.id or False
        return int(value)

    @api.private
    def _validate_main_attachment_id(self, attachment_id):
        if not attachment_id:
            return
        attachment = self.env["ir.attachment"].browse(attachment_id)
        if not attachment.exists():
            raise UserError(self.env._("Designated proof attachment was not found."))
        if not self._is_designated_proof_mimetype(attachment):
            raise UserError(
                self.env._(
                    "Attachment must be an image or a PDF "
                    "(detected type: %(mimetype)s).",
                    mimetype=attachment.mimetype or "unknown",
                )
            )

    @api.private
    def _vals_with_review_reset_on_new_attachment(self, vals):
        if "message_main_attachment_id" not in vals:
            return vals
        self.ensure_one()
        new_id = self._normalize_main_attachment_id(
            vals.get("message_main_attachment_id")
        )
        old_id = self.message_main_attachment_id.id or False
        if old_id == (new_id or False):
            return vals
        vals = dict(vals)
        vals["attachment_rotation"] = 0
        if new_id:
            vals["state"] = "pending"
            vals["reviewed_by"] = False
            vals["reviewed_at"] = False
        return vals

    @api.private
    def _normalize_attachment_rotation(self, degrees):
        try:
            rotation = int(degrees)
        except (TypeError, ValueError) as err:
            raise UserError(
                self.env._("Attachment rotation must be 0, 90, 180, or 270 degrees.")
            ) from err
        if rotation not in self._ALLOWED_ROTATIONS:
            raise UserError(
                self.env._("Attachment rotation must be 0, 90, 180, or 270 degrees.")
            )
        return rotation

    @api.private
    def _editable_review_vals(self, vals):
        if not vals:
            return {}
        return {
            key: value
            for key, value in vals.items()
            if key in self._REVIEW_EDITABLE_FIELDS
        }

    @api.private
    def _write_review_decision(self, status, extra_vals=None):
        vals = {
            "state": status,
            "reviewed_by": self.env.user.id,
            "reviewed_at": fields.Datetime.now(),
        }
        if extra_vals:
            vals.update(extra_vals)
        self.with_context(collection_audited_state=True).write(vals)
        self._append_review_snapshot(status)

    @api.private
    def _append_review_snapshot(self, decision):
        Snapshot = self.env["collection.voucher.review.snapshot"]
        for voucher in self:
            last = Snapshot.search(
                [("voucher_id", "=", voucher.id)],
                order="revision desc",
                limit=1,
            )
            payload = {
                "voucher_id": voucher.id,
                "revision": (last.revision or 0) + 1,
                "reviewer_id": voucher.reviewed_by.id,
                "reviewed_at": voucher.reviewed_at,
                "decision": decision,
            }
            for name in self._REVIEW_EDITABLE_FIELDS:
                payload[name] = voucher[name]
            Snapshot.with_context(collection_review_snapshot=True).create(payload)

    @api.private
    def _lock_and_ensure_review_eligible(self):
        self.ensure_one()
        self.env.cr.execute(
            """
            SELECT id FROM collection_voucher
            WHERE id = %s
            FOR UPDATE
            """,
            [self.id],
        )
        self.invalidate_recordset()
        self._ensure_review_eligible()

    @api.private
    def _ensure_review_eligible(self):
        self.ensure_one()
        if not self._is_review_eligible():
            raise UserError(self.env._("This voucher is not eligible for review."))

    @api.private
    def _is_review_eligible(self):
        self.ensure_one()
        return bool(self.state == "pending" and self._records_with_attachment())

    @api.private
    def _records_with_attachment(self):
        """Return subset of ``self`` that has designated chatter proof."""
        return self.filtered(lambda voucher: bool(voucher.message_main_attachment_id))

    @api.private
    def _attachment_content_url(self):
        self.ensure_one()
        attachment = self.message_main_attachment_id
        if not attachment:
            return ""
        return f"/web/content/{attachment.id}"

    @api.private
    def _review_queue_payload(self, position, total):
        self.ensure_one()
        attachment = self.message_main_attachment_id
        payload = {
            "id": self.id,
            "voucher_id": self.id,
            "voucher_name": self.name,
            "document_id": self.document_id,
            "document_type": self.document_type,
            "amount": self.amount,
            "from_account": self.from_account,
            "to_account": self.to_account,
            "voucher_number": self.voucher_number,
            "voucher_date": self.voucher_date,
            "check_number": self.check_number,
            "check_bank": self.check_bank,
            "check_type": self.check_type,
            "check_issue_date": self.check_issue_date,
            "check_payment_date": self.check_payment_date,
            "position": position,
            "total": total,
            "attachment_filename": attachment.name,
            "mimetype": attachment.mimetype,
            "attachment_url": self._attachment_content_url(),
            "attachment_rotation": self.attachment_rotation,
        }
        for prefix in ("ocr", "seller"):
            for name in self._REVIEW_EDITABLE_FIELDS:
                payload[f"{prefix}_{name}"] = self[f"{prefix}_{name}"]
        return payload
