# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import annotations

import uuid
from typing import Any

from odoo import _, api, models
from odoo.exceptions import AccessError, UserError

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
        "attachment": _ATTACHMENT_NEST_SCHEMA,
    },
    "required": ["seller_id", "amount", "voucher_number", "voucher_date"],
}


class CollectionSellerDepositMcpMixin(models.AbstractModel):
    """MuK MCP write tool to create a seller_deposit on a submitted sheet."""

    _inherit = "muk_mcp.mixin"

    @api.model
    @mcp_tool(
        name="create_seller_deposit",
        description=(
            "Create a seller_deposit on the seller's submitted sheet. Mints "
            "sd-<uuid4 hex>, stamps the sentinel, writes validated_collections. "
            "Returns {sheet, voucher}. Internal users only."
        ),
        input_schema=_CREATE_SELLER_DEPOSIT_SCHEMA,
        category="write",
        registry="mcp",
    )
    def create_seller_deposit(
        self,
        seller_id: int,
        amount: Any,
        voucher_number: str,
        voucher_date: Any,
        attachment: Any = None,
        **kwargs: Any,
    ) -> dict:
        """Create a remittance voucher on the seller's submitted sheet.

        :raise AccessError: when the caller is not an internal user.
        :raise UserError: when the seller, type, extra keys, amounts, dates,
            or submitted-sheet set are invalid.
        """
        if kwargs:
            _collection_reject_unknown_keys(
                kwargs,
                frozenset(),
                _("create_seller_deposit"),
            )
        if not self.env.user.has_group("base.group_user"):
            raise AccessError(_("Only internal users can create seller deposits."))
        if not isinstance(voucher_number, str) or not voucher_number.strip():
            raise UserError(_("voucher_number is required."))
        try:
            parsed_amount = _collection_normalize_amount(amount)
            parsed_date = _collection_normalize_iso_date(voucher_date)
        except ValueError as err:
            raise UserError(
                _("amount must be an amount and voucher_date must be an ISO date.")
            ) from err
        sidecar = None
        if attachment not in _OMIT_VALUES:
            sidecar = self._collection_parse_attachment_nest(attachment, 0)
        seller = self._collection_require_internal_seller(seller_id)
        self.env.company._assert_new_work(seller, "seller_deposit")
        Sheet = self.env["collection.sheet"]
        Sheet._lock_open_sheet_for_seller(seller, self.env.company)
        submitted = Sheet._submitted_sheets_for_seller(seller, self.env.company)
        if len(submitted) > 1:
            raise UserError(_("This seller has more than one open collection sheet."))
        if not submitted:
            raise UserError(_("This seller has no submitted collection sheet."))
        submitted.check_access("write")
        voucher = self.env["collection.voucher"].create(
            {
                "seller_id": seller.id,
                "document_type": "seller_deposit",
                "document_id": f"sd-{uuid.uuid4().hex}",
                "amount": parsed_amount,
                "voucher_number": voucher_number.strip(),
                "voucher_date": parsed_date,
                "sheet_id": submitted.id,
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
        voucher.with_context(collection_audited_state=True).write(
            {"state": "validated_collections"}
        )
        return {
            "sheet": self._collection_sheet_identity(submitted),
            "voucher": {
                "id": voucher.id,
                "name": voucher.name,
                "state": voucher.state,
                "document_id": voucher.document_id,
            },
        }
