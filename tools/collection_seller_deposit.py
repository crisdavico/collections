# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import annotations

import uuid
from typing import Any

from odoo import _, api, models
from odoo.exceptions import UserError

from odoo.addons.collection.tools.collection_voucher import (
    _ATTACHMENT_NEST_SCHEMA,
    _COLLECTION_AMOUNT_SCHEMA,
    _OMIT_VALUES,
    _collection_normalize_amount,
    _collection_normalize_iso_date,
    _collection_reject_unknown_keys,
)
from odoo.addons.muk_mcp.core.tool import mcp_tool

_CREATE_SELLER_DEPOSIT_SCHEMA = {
    "type": "object",
    "properties": {
        "seller_id": {
            "type": "integer",
            "minimum": 1,
            "description": "Internal seller user id.",
        },
        "amount": dict(_COLLECTION_AMOUNT_SCHEMA),
        "voucher_number": {
            "type": "string",
            "description": "Bank voucher number on the deposit slip.",
        },
        "voucher_date": {
            "type": "string",
            "description": "ISO date",
        },
        "attachment": {
            **_ATTACHMENT_NEST_SCHEMA,
            "description": (
                "File of the deposit slip (required). "
                "Required keys: name, mimetype, datas."
            ),
        },
    },
    "required": ["seller_id", "amount", "voucher_number", "voucher_date", "attachment"],
}


class CollectionSellerDepositMcpMixin(models.AbstractModel):
    """MuK MCP write tool to create a seller_deposit on the seller's sheet."""

    _inherit = "muk_mcp.mixin"

    @api.model
    @mcp_tool(
        name="create_seller_deposit",
        description=(
            "Create a seller_deposit on the seller's open sheet (load it "
            "before closing), or on the submitted sheet when none is open. Mints "
            "sd-<uuid4 hex>, stamps the sentinel, leaves the voucher in "
            "validated_seller for Document Review. Returns {sheet, voucher}. "
            "Collections Users only."
        ),
        input_schema=_CREATE_SELLER_DEPOSIT_SCHEMA,
        category="write",
        registry="mcp",
    )
    def create_seller_deposit(
        self,
        seller_id: int | None = None,
        amount: Any = None,
        voucher_number: str | None = None,
        voucher_date: Any = None,
        attachment: Any = None,
        **kwargs: Any,
    ) -> dict:
        """Create a remittance voucher on the seller's open or submitted sheet.

        The deposit slip is a reviewable designated proof, so the voucher stays
        ``validated_seller``: only Document Review Approve promotes it.

        :raise AccessError: when the caller is not a Collections User, or the
            trusted seller header does not verify the seller.
        :raise UserError: when the seller, type, extra keys, amounts, dates,
            or open/submitted sheet set are invalid.
        """
        if kwargs:
            _collection_reject_unknown_keys(
                kwargs,
                frozenset(),
                _("create_seller_deposit"),
            )
        self._collection_require_collection_user()
        if not isinstance(voucher_number, str) or not voucher_number.strip():
            raise UserError(_("voucher_number is required."))
        try:
            parsed_amount = _collection_normalize_amount(amount)
            parsed_date = _collection_normalize_iso_date(voucher_date)
        except ValueError as err:
            raise UserError(
                _("amount must be an amount and voucher_date must be an ISO date.")
            ) from err
        if self.env.company.currency_id.compare_amounts(parsed_amount, 0.0) <= 0:
            raise UserError(_("amount must be greater than zero."))
        if attachment in _OMIT_VALUES:
            raise UserError(_("A seller deposit needs the file of its deposit slip."))
        sidecar = self._collection_parse_attachment_nest(attachment, 0)
        seller = self._collection_mcp_seller(seller_id)
        self.env.company._assert_new_work(seller, "seller_deposit")
        Sheet = self.env["collection.sheet"]
        Sheet._lock_open_sheet_for_seller(seller, self.env.company)
        sheet = Sheet._open_sheets_for_seller(seller, self.env.company)
        if not sheet:
            sheet = Sheet._submitted_sheets_for_seller(seller, self.env.company)
        if len(sheet) > 1:
            raise UserError(_("This seller has more than one open collection sheet."))
        if not sheet:
            raise UserError(_("This seller has no open or submitted collection sheet."))
        sheet.check_access("write")
        voucher = self.env["collection.voucher"].create(
            {
                "seller_id": seller.id,
                "document_type": "seller_deposit",
                "document_id": f"sd-{uuid.uuid4().hex}",
                "amount": parsed_amount,
                "voucher_number": voucher_number.strip(),
                "voucher_date": parsed_date,
                "sheet_id": sheet.id,
                "state": "validated_seller",
            }
        )
        if sidecar:
            name, raw = sidecar
            voucher.message_post(
                body=_("Payment proof attached."),
                message_type="notification",
                attachments=[(name, raw)],
            )
        return {
            "sheet": self._collection_sheet_identity(sheet),
            "voucher": {
                "id": voucher.id,
                "name": voucher.name,
                "state": voucher.state,
                "document_id": voucher.document_id,
            },
        }
