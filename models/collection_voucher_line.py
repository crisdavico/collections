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

    _document_id_uniq = models.Constraint(
        "UNIQUE(document_id)",
        "Document ID must be unique!",
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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._validate_attachment_payload(vals.get("attachment"))
        return super().create(vals_list)

    def write(self, vals):
        if "attachment" in vals:
            self._validate_attachment_payload(vals.get("attachment"))
        return super().write(vals)
