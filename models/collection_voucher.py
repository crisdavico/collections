# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import binascii
from base64 import b64decode
from datetime import date

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare
from odoo.tools.mimetypes import guess_mimetype
from odoo.tools.translate import _

from .collection_common import (
    ADMIN_EDITABLE_SHEET_STATES,
    CASH_REPLACEMENT_TYPES,
    CHECK_TYPE_SELECTION,
    DOCUMENT_TYPE_SELECTION,
    FROZEN_SHEET_STATES,
    RETENTION_KIND_SELECTION,
    record_id,
)


class CollectionVoucher(models.Model):
    _name = "collection.voucher"
    _description = "Payment Voucher"
    _inherit = ["mail.thread.main.attachment", "mail.activity.mixin"]
    _order = "id desc"

    _DOCUMENT_TYPE_SELECTION = DOCUMENT_TYPE_SELECTION
    _RETENTION_KIND_SELECTION = RETENTION_KIND_SELECTION
    _SENTINEL_PARTNER_GETTERS = {
        "seller_deposit": "_seller_deposit_partner",
        "seller_commission": "_seller_commission_partner",
    }

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default="/",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        required=True,
        tracking=True,
        index=True,
        ondelete="restrict",
    )
    seller_id = fields.Many2one(
        comodel_name="res.users",
        string="Seller",
        required=False,
        domain=[("share", "=", False)],
        tracking=True,
    )
    sheet_id = fields.Many2one(
        comodel_name="collection.sheet",
        string="Collection Sheet",
        ondelete="set null",
        tracking=True,
    )
    allocation_id = fields.Many2one(
        comodel_name="collection.allocation",
        string="Allocation",
        ondelete="set null",
        check_company=True,
        index=True,
    )
    receipt_value_ids = fields.One2many(
        comodel_name="collection.receipt.value",
        inverse_name="voucher_id",
        string="Receipt Values",
        readonly=True,
    )
    cash_replacement_ids = fields.One2many(
        comodel_name="collection.cash.replacement",
        inverse_name="cash_voucher_id",
        string="Cash Replacements",
        readonly=True,
    )
    replaced_amount = fields.Monetary(
        compute="_compute_replaced_amount",
        currency_field="currency_id",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("validated_seller", "Validated by Seller"),
            ("validated_collections", "Validated by Collections"),
        ],
        default="draft",
        required=True,
        tracking=True,
        copy=False,
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
        tracking=True,
    )
    amount = fields.Monetary(tracking=True)
    from_account = fields.Char()
    to_account = fields.Char()
    voucher_number = fields.Char()
    voucher_date = fields.Date()
    check_number = fields.Char()
    check_bank = fields.Char()
    check_issue_date = fields.Date()
    check_payment_date = fields.Date()
    check_type = fields.Selection(selection=list(CHECK_TYPE_SELECTION))
    retention_kind = fields.Selection(selection=_RETENTION_KIND_SELECTION)
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
        selection=_DOCUMENT_TYPE_SELECTION,
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
        selection=list(CHECK_TYPE_SELECTION),
        string="Check Type",
        copy=False,
    )
    ocr_retention_kind = fields.Selection(
        selection=_RETENTION_KIND_SELECTION,
        string="Retention Kind",
        copy=False,
    )
    seller_document_type = fields.Selection(
        selection=_DOCUMENT_TYPE_SELECTION,
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
        selection=list(CHECK_TYPE_SELECTION),
        string="Check Type",
        copy=False,
    )
    seller_retention_kind = fields.Selection(
        selection=_RETENTION_KIND_SELECTION,
        string="Retention Kind",
        copy=False,
    )

    _REVIEW_EDITABLE_FIELD_ORDER = (
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
        "retention_kind",
    )
    _REVIEW_EDITABLE_FIELDS = frozenset(_REVIEW_EDITABLE_FIELD_ORDER)
    _ALLOWED_ROTATIONS = frozenset({0, 90, 180, 270})

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

    @api.depends("cash_replacement_ids.amount", "cash_replacement_ids.direction")
    def _compute_replaced_amount(self):
        for voucher in self:
            replace = 0.0
            reverse = 0.0
            for row in voucher.cash_replacement_ids:
                if row.direction == "replace":
                    replace += row.amount or 0.0
                elif row.direction == "reverse":
                    reverse += row.amount or 0.0
            net = replace - reverse
            voucher.replaced_amount = (
                voucher.currency_id.round(net) if voucher.currency_id else net
            )

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            self._apply_seller_deposit_partner(vals)
            company = self.env["res.company"].browse(
                vals.get("company_id") or self.env.company.id
            )
            company._assert_new_work(vals.get("seller_id"), vals.get("document_type"))
        self._apply_open_sheet_auto_assign(vals_list)
        for vals in vals_list:
            if vals.get("state") == "validated_collections":
                raise UserError(
                    _("Validated by Collections is only available via Document Review.")
                )
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

    @api.private
    def _apply_seller_deposit_partner(self, vals):
        """Stamp the type's sentinel partner; refuse a customer partner."""
        document_type = vals.get("document_type")
        getter_name = self._SENTINEL_PARTNER_GETTERS.get(document_type)
        if not getter_name:
            return
        if vals.get("customer_identification"):
            if document_type == "seller_deposit":
                raise UserError(
                    _("Seller deposits cannot use a customer identification.")
                )
            raise UserError(
                _("Seller commissions cannot use a customer identification.")
            )
        company = self.env["res.company"].browse(
            vals.get("company_id") or self.env.company.id
        )
        sentinel = getattr(company, getter_name)()
        partner_id = record_id(vals.get("partner_id"))
        if partner_id and partner_id != sentinel.id:
            if document_type == "seller_deposit":
                raise UserError(_("Seller deposits cannot use a customer partner."))
            raise UserError(_("Seller commissions cannot use a customer partner."))
        vals["partner_id"] = sentinel.id

    def _selection_document_type(self):
        """Allowed company types, plus each record's current value if later dropped.

        Labels come from the ``collection.document.type`` catalog, whose ``name``
        is ``translate=True``. A selection resolved by method never passes through
        ``ir.model.fields.selection``, so ``_description_selection`` hands back the
        constant verbatim -- English in every language. The catalog mirrors
        ``_DOCUMENT_TYPE_SELECTION`` code for code, so reading the label off the
        record keeps en_US byte-identical while giving es_AR a translation.
        """
        allowed = self.env.company.allowed_document_type_ids
        allowed_codes = set(allowed.mapped("code"))
        current_codes = {rec.document_type for rec in self if rec.document_type}
        keep = allowed_codes | current_codes
        catalog = allowed
        missing = current_codes - allowed_codes
        if missing:
            catalog |= self.env["collection.document.type"].search(
                [("code", "in", list(missing))]
            )
        labels = {rec.code: rec.name for rec in catalog}
        return [
            (code, labels.get(code) or label)
            for code, label in self._DOCUMENT_TYPE_SELECTION
            if code in keep
        ]

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
        self._ensure_sheet_business_fields_unlocked(vals)
        vals, split_result = self._prepare_partner_reassign_write(vals)
        if split_result is not None:
            return split_result
        if "sheet_id" in vals:
            self._ensure_sheet_membership_unlocked(vals.get("sheet_id"))
        if "allocation_id" in vals:
            self._ensure_allocation_membership_writable(vals.get("allocation_id"))
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
            new_id = record_id(vals.get("message_main_attachment_id"))
            self._validate_main_attachment_id(new_id)
            vals = self._vals_with_review_reset_on_new_attachment(vals)
        intercepted = self._intercept_state_write(vals)
        if intercepted is not None:
            return intercepted
        entering = self._cash_replacers_entering_validated_collections(vals)
        result = super().write(vals)
        entering._run_cash_replacement()
        return result

    def action_validate_seller(self):
        if any(voucher.state != "draft" for voucher in self):
            raise UserError(_("Only draft vouchers can be validated by seller."))
        return self.with_context(collection_audited_state=True).write(
            {"state": "validated_seller"}
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
    def _prepare_partner_reassign_write(self, vals):
        if "partner_id" not in vals:
            return vals, None
        self._ensure_partner_reassign_unlocked(vals.get("partner_id"))
        if len(self) > 1:
            return vals, all(rec.write(vals) for rec in self)
        return vals, None

    @api.private
    def _cash_replacers_entering_validated_collections(self, vals):
        """Return cash-replacing rows whose write is entering validated_collections."""
        if vals.get("state") != "validated_collections":
            return self.browse()
        return self.filtered(
            lambda voucher: voucher.document_type in CASH_REPLACEMENT_TYPES
            and voucher.state != "validated_collections"
        )

    @api.private
    def _run_cash_replacement(self):
        """Replace cash receipt values with this deposit or commission."""
        Value = self.env["collection.receipt.value"]
        for replacer in self.sorted("id"):
            if replacer.document_type not in CASH_REPLACEMENT_TYPES:
                continue
            sheet = replacer.sheet_id
            if not sheet or sheet.state in FROZEN_SHEET_STATES:
                continue
            currency = replacer.currency_id
            remaining = currency.round(replacer.amount or 0.0)
            for receipt, cash_value in replacer._iter_replaceable_cash_values():
                if currency.compare_amounts(remaining, 0.0) <= 0:
                    break
                if not cash_value.exists():
                    continue
                slice_amount = min(remaining, cash_value.amount or 0.0)
                row = Value._cash_replace(
                    receipt, cash_value.voucher_id, replacer, slice_amount
                )
                if row:
                    remaining = currency.round(remaining - row.amount)
            if (
                replacer.document_type == "seller_commission"
                and currency.compare_amounts(remaining, 0.0) != 0
            ):
                raise UserError(_("Seller commission exceeds replaceable cash."))

    @api.model
    @api.private
    def _replacement_fifo_key(self, line):
        """Same shape as satellite `_proposal_fifo_key` (due_date, number)."""
        return (line.due_date or date.max, line.invoice_number or "")

    @api.model
    @api.private
    def _replacement_receipt_fifo_key(self, receipt):
        """Earliest applied-line FIFO key on the receipt; undated applications last."""
        keys = [self._replacement_fifo_key(line) for line in receipt.line_ids]
        return min(keys) if keys else (date.max, "")

    @api.model
    @api.private
    def _replacement_cash_upload_key(self, value):
        """Oldest-uploaded cash first; id breaks equal create_date."""
        uploaded = value.voucher_id.create_date or fields.Datetime.from_string(
            "1970-01-01 00:00:00"
        )
        return (uploaded, value.id)

    @api.private
    def _iter_replaceable_cash_values(self):
        """Yield replaceable cash: skip issued, then quotation then invoice, FIFO."""
        self.ensure_one()
        receipts = self.sheet_id.allocation_ids.receipt_ids.filtered(
            lambda receipt: receipt.state != "issued"
        )
        for kind in ("quotation", "invoice"):
            kind_receipts = receipts.filtered(
                lambda receipt, current=kind: receipt.document_kind == current
            ).sorted(key=self._replacement_receipt_fifo_key)
            for receipt in kind_receipts:
                cash_values = receipt.value_ids.filtered(
                    lambda value: value.voucher_id.document_type == "cash"
                ).sorted(key=self._replacement_cash_upload_key)
                for cash_value in cash_values:
                    yield receipt, cash_value

    @api.private
    def _intercept_state_write(self, vals):
        if "state" not in vals or self.env.context.get("collection_audited_state"):
            return None
        target = vals["state"]
        if target == "validated_collections":
            raise UserError(
                _("Validated by Collections is only available via Document Review.")
            )
        if target == "validated_seller":
            if "message_main_attachment_id" in vals:
                return None
            rest = {key: value for key, value in vals.items() if key != "state"}
            if rest:
                super().write(rest)
            return self.action_validate_seller()
        if (
            target == "draft"
            and "message_main_attachment_id" not in vals
            and any(voucher.state != "draft" for voucher in self)
        ):
            raise UserError(
                _("Cannot reopen a decided voucher without replacing the attachment.")
            )
        return None

    @api.private
    def _closed_membership_user_error(self):
        return UserError(
            _("Closed collection sheets cannot change membership. Reopen first.")
        )

    @api.private
    def _sheet_is_frozen(self, sheet):
        return bool(sheet) and sheet.state not in ADMIN_EDITABLE_SHEET_STATES

    @api.private
    def _ensure_sheet_membership_unlocked(self, new_sheet_id):
        if self.env.context.get("collection_sheet_unlinking"):
            return
        target = (
            self.env["collection.sheet"].browse(new_sheet_id)
            if new_sheet_id
            else self.env["collection.sheet"]
        )
        if self._sheet_is_frozen(target):
            raise self._closed_membership_user_error()
        for voucher in self:
            current = voucher.sheet_id
            if self._sheet_is_frozen(current) and current != target:
                raise self._closed_membership_user_error()

    @api.private
    def _ensure_partner_reassign_unlocked(self, new_partner):
        new_id = record_id(new_partner)
        for voucher in self:
            if not self._sheet_is_frozen(voucher.sheet_id):
                continue
            if (voucher.partner_id.id or False) != new_id:
                raise self._closed_membership_user_error()

    @api.private
    def _ensure_sheet_business_fields_unlocked(self, vals):
        if not (self._REVIEW_EDITABLE_FIELDS & set(vals)):
            return
        if any(self._sheet_is_frozen(voucher.sheet_id) for voucher in self):
            raise UserError(
                _(
                    "Voucher fields cannot be changed while the collection "
                    "sheet is not open."
                )
            )

    @api.constrains("amount", "document_type")
    def _check_amount_positive(self):
        for voucher in self:
            if voucher.document_type == "unsupported":
                continue
            if voucher.currency_id.compare_amounts(voucher.amount or 0.0, 0.0) <= 0:
                raise ValidationError(_("Amount must be greater than zero."))

    @api.constrains(
        "document_type", "check_type", "check_issue_date", "check_payment_date"
    )
    def _check_check_dates_coherent(self):
        for voucher in self:
            if voucher.document_type not in ("check", "echeck"):
                continue
            issue = voucher.check_issue_date
            payment = voucher.check_payment_date
            if issue and payment and issue > payment:
                raise ValidationError(
                    _("Check issue date cannot be after the check payment date.")
                )
            if voucher.check_type == "deferred" and (
                not issue or not payment or payment <= issue
            ):
                raise ValidationError(
                    _(
                        "A deferred check must have a payment date strictly "
                        "after the issue date."
                    )
                )

    @api.constrains("voucher_date", "check_issue_date")
    def _check_dates_not_in_future(self):
        for voucher in self:
            today = fields.Date.context_today(voucher)
            if voucher.voucher_date and voucher.voucher_date > today:
                raise ValidationError(_("Voucher date cannot be in the future."))
            if voucher.check_issue_date and voucher.check_issue_date > today:
                raise ValidationError(_("Check issue date cannot be in the future."))

    @api.constrains("partner_id", "allocation_id")
    def _check_voucher_allocation_partner(self):
        for voucher in self:
            allocation = voucher.allocation_id
            if allocation and voucher.partner_id != allocation.partner_id:
                raise UserError(
                    _("Voucher customer must match the allocation customer.")
                )

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
    def _unlink_if_draft(self):
        if any(voucher.state != "draft" for voucher in self):
            raise UserError(_("You can only delete vouchers in the Draft state."))
        if any(
            not self._allocation_is_draft_or_unset(voucher.allocation_id)
            for voucher in self
        ):
            raise self._allocation_membership_user_error()

    @api.private
    def _allocation_membership_user_error(self):
        return UserError(
            _(
                "Allocation membership can only change when the current "
                "and target allocations are draft or unset."
            )
        )

    @api.private
    def _ensure_allocation_membership_writable(self, new_allocation_id):
        target = self._allocation_from_value(new_allocation_id)
        if not self._allocation_is_draft_or_unset(target) or any(
            not self._allocation_is_draft_or_unset(voucher.allocation_id)
            for voucher in self
        ):
            raise self._allocation_membership_user_error()

    @api.private
    def _allocation_from_value(self, value):
        return self.env["collection.allocation"].browse(record_id(value) or [])

    @api.private
    def _allocation_is_draft_or_unset(self, allocation):
        return not allocation or allocation.state == "draft"

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
        """Validate base64 + detected MIME before posting designated proof.

        Returns ``(decoded bytes, detected mimetype)`` so callers do not have to
        decode the payload again, or ``(b"", "")`` when there is nothing to check.
        """
        if not attachment:
            return b"", ""
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
        return decoded, mime

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
                ("state", "=", "validated_seller"),
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
        extra = self._editable_review_vals(vals)
        if extra:
            self.write(extra)
        self._write_review_decision()
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
        if sheet.state not in ADMIN_EDITABLE_SHEET_STATES:
            raise UserError(
                self.env._(
                    "Document Review is only available on open collection sheets."
                )
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
        new_id = record_id(vals.get("message_main_attachment_id"))
        old_id = self.message_main_attachment_id.id or False
        if old_id == (new_id or False):
            return vals
        vals = dict(vals)
        vals["attachment_rotation"] = 0
        if old_id and new_id:
            vals["state"] = "validated_seller"
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
    def _write_review_decision(self):
        self.with_context(collection_audited_state=True).write(
            {
                "state": "validated_collections",
                "reviewed_by": self.env.user.id,
                "reviewed_at": fields.Datetime.now(),
            }
        )
        self._append_review_snapshot("approved")

    @api.private
    def _editable_review_vals(self, vals):
        """Return current-field corrections allowed on Document Review approve."""
        if not vals:
            return {}
        return {
            name: vals[name]
            for name in self._REVIEW_EDITABLE_FIELD_ORDER
            if name in vals
        }

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
        return self.state == "validated_seller" and bool(
            self.message_main_attachment_id
        )

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
            "position": position,
            "total": total,
            "attachment_filename": attachment.name,
            "mimetype": attachment.mimetype,
            "attachment_url": self._attachment_content_url(),
            "attachment_rotation": self.attachment_rotation,
        }
        for name in self._REVIEW_EDITABLE_FIELD_ORDER:
            payload[name] = self[name]
        for prefix in ("ocr", "seller"):
            for name in self._REVIEW_EDITABLE_FIELDS:
                payload[f"{prefix}_{name}"] = self[f"{prefix}_{name}"]
        payload["seller_changed_fields"] = self._review_seller_changed_fields()
        return payload

    @api.private
    def _review_field_is_empty(self, name, value):
        """Return whether a typed review field value is empty."""
        if value is False or value is None:
            return True
        if name == "amount":
            return float_compare(value, 0.0, precision_digits=2) == 0
        return value == ""

    @api.private
    def _review_fields_equal(self, name, left, right):
        """Return whether two typed review field values compare equal."""
        if name == "amount":
            return float_compare(left, right, precision_digits=2) == 0
        if self._fields[name].type == "date":
            return fields.Date.to_date(left) == fields.Date.to_date(right)
        return left == right

    @api.private
    def _review_seller_raw_value(self, name, value):
        """Return the seller value to expose in seller_changed_fields."""
        if self._review_field_is_empty(name, value):
            return 0.0 if name == "amount" else False
        return value

    @api.private
    def _review_seller_changed_fields(self):
        """Return OCR-vs-seller diffs keyed in ``_REVIEW_EDITABLE_FIELD_ORDER``."""
        self.ensure_one()
        changed = {}
        for name in self._REVIEW_EDITABLE_FIELD_ORDER:
            ocr_value = self[f"ocr_{name}"]
            seller_value = self[f"seller_{name}"]
            ocr_empty = self._review_field_is_empty(name, ocr_value)
            seller_empty = self._review_field_is_empty(name, seller_value)
            if ocr_empty and seller_empty:
                continue
            if (
                not ocr_empty
                and not seller_empty
                and self._review_fields_equal(name, ocr_value, seller_value)
            ):
                continue
            changed[name] = self._review_seller_raw_value(name, seller_value)
        return changed
