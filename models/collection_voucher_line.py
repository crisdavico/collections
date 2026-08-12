# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import binascii
from base64 import b64decode

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.mimetypes import guess_mimetype


class CollectionVoucherLine(models.Model):
    _name = "collection.voucher.line"
    _description = "Payment Voucher Line"
    _order = "id"

    voucher_id = fields.Many2one(
        comodel_name="collection.voucher",
        string="Voucher",
        required=True,
        ondelete="cascade",
        index=True,
    )
    document_id = fields.Char(string="Document ID", index=True)
    document_type = fields.Selection(
        selection=[
            ("bank_transfer", "Bank Transfer"),
            ("check", "Check"),
            ("cash_deposit", "Cash Deposit"),
            ("unsupported", "Unsupported"),
        ],
        required=True,
    )
    amount = fields.Monetary()
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="voucher_id.currency_id",
        store=True,
        readonly=True,
    )
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
    attachment = fields.Binary(attachment=True, copy=False)
    attachment_filename = fields.Char(copy=False)
    attachment_rotation = fields.Integer(default=0, copy=False)
    review_status = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="pending",
        required=True,
        copy=False,
    )
    reviewed_by = fields.Many2one(
        comodel_name="res.users",
        copy=False,
    )
    reviewed_at = fields.Datetime(copy=False)

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

    _document_id_uniq = models.Constraint(
        "UNIQUE(document_id)",
        "Document ID must be unique!",
    )
    _attachment_rotation_valid = models.Constraint(
        "CHECK(attachment_rotation IN (0, 90, 180, 270))",
        "Attachment rotation must be 0, 90, 180, or 270 degrees.",
    )

    @api.model
    def _validate_attachment_payload(self, attachment):
        """Validate base64 + detected MIME before Binary/ir.attachment write."""
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

    @api.constrains("attachment")
    def _check_attachment_content(self):
        for line in self:
            self._validate_attachment_payload(line.attachment)

    @api.constrains("attachment_rotation")
    def _check_attachment_rotation(self):
        for line in self:
            if line.attachment_rotation not in self._ALLOWED_ROTATIONS:
                raise UserError(
                    self.env._(
                        "Attachment rotation must be 0, 90, 180, or 270 degrees."
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._validate_attachment_payload(vals.get("attachment"))
        return super().create(vals_list)

    def write(self, vals):
        if "attachment" in vals:
            self._validate_attachment_payload(vals.get("attachment"))
        vals = self._vals_with_review_reset_on_new_attachment(vals)
        return super().write(vals)

    @api.model
    def get_review_queue(self):
        lines = self.search(
            [
                ("voucher_id.state", "=", "new"),
                ("review_status", "=", "pending"),
                ("attachment", "!=", False),
            ],
            order="id",
        )
        total = len(lines)
        return [
            line._review_queue_payload(position=index, total=total)
            for index, line in enumerate(lines, start=1)
        ]

    def action_review_approve(self, vals=None):
        self.ensure_one()
        self._lock_and_ensure_review_eligible()
        self._write_review_decision("approved", self._editable_review_vals(vals))
        self._validate_voucher_if_all_attached_approved()
        return True

    def action_review_reject(self):
        self.ensure_one()
        self._lock_and_ensure_review_eligible()
        self._write_review_decision("rejected")
        if self.voucher_id.state == "new":
            self.voucher_id.action_reject()
        return True

    def action_review_set_rotation(self, degrees):
        self.ensure_one()
        self._ensure_review_eligible()
        self.write(
            {"attachment_rotation": self._normalize_attachment_rotation(degrees)}
        )
        return True

    @api.private
    def _vals_with_review_reset_on_new_attachment(self, vals):
        if "attachment" not in vals:
            return vals
        vals = dict(vals)
        if vals.get("attachment"):
            vals["review_status"] = "pending"
            vals["reviewed_by"] = False
            vals["reviewed_at"] = False
        vals["attachment_rotation"] = 0
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
            "review_status": status,
            "reviewed_by": self.env.user.id,
            "reviewed_at": fields.Datetime.now(),
        }
        if extra_vals:
            vals.update(extra_vals)
        self.write(vals)

    @api.private
    def _lock_and_ensure_review_eligible(self):
        self.ensure_one()
        self.env.cr.execute(
            """
            SELECT id FROM collection_voucher_line
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
            raise UserError(self.env._("This payment line is not eligible for review."))

    @api.private
    def _is_review_eligible(self):
        self.ensure_one()
        return bool(
            self.voucher_id.state == "new"
            and self.review_status == "pending"
            and self._lines_with_attachment()
        )

    @api.private
    def _lines_with_attachment(self):
        """Return subset of ``self`` that has stored Binary attachment content."""
        if not self:
            return self.browse()
        attachments = self.env["ir.attachment"].search(
            [
                ("res_model", "=", self._name),
                ("res_id", "in", self.ids),
                ("res_field", "=", "attachment"),
            ]
        )
        return self.browse(attachments.mapped("res_id"))

    @api.private
    def _validate_voucher_if_all_attached_approved(self):
        voucher = self.voucher_id
        if voucher.state != "new":
            return
        attached = voucher.payment_ids._lines_with_attachment()
        if attached and all(line.review_status == "approved" for line in attached):
            voucher.action_validate()

    @api.private
    def _attachment_content_url(self):
        self.ensure_one()
        url = (
            f"/web/content?model=collection.voucher.line&id={self.id}&field=attachment"
        )
        if self.attachment_filename:
            url = f"{url}&filename={self.attachment_filename}"
        return url

    @api.private
    def _review_queue_payload(self, position, total):
        self.ensure_one()
        return {
            "id": self.id,
            "voucher_id": self.voucher_id.id,
            "voucher_name": self.voucher_id.name,
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
            "attachment_filename": self.attachment_filename,
            "attachment_url": self._attachment_content_url(),
            "attachment_rotation": self.attachment_rotation,
        }
