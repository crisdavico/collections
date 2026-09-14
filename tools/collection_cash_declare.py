# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import annotations

from typing import Any

from odoo import _, api, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.collection.tools.collection_voucher import (
    _COLLECTION_AMOUNT_SCHEMA,
    _collection_normalize_amount,
    _collection_reject_unknown_keys,
)
from odoo.addons.muk_mcp.core.tool import mcp_tool

_DECLARE_COLLECTION_CASH_SCHEMA = {
    "type": "object",
    "properties": {
        "seller_id": {
            "type": "integer",
            "minimum": 1,
            "description": "Internal seller user id.",
        },
        "commission_withheld": dict(_COLLECTION_AMOUNT_SCHEMA),
    },
    "required": ["seller_id", "commission_withheld"],
}


class CollectionCashDeclareMcpMixin(models.AbstractModel):
    """MuK MCP write tool to Declare Cash on a seller's submitted sheet."""

    _inherit = "muk_mcp.mixin"

    @api.model
    @mcp_tool(
        name="declare_collection_cash",
        description=(
            "Declare Cash on the authenticated seller's submitted collection "
            "sheet with commission_withheld. Cash to Administration is computed "
            "from the sheet vouchers and MUST NOT be sent. Returns "
            "{sheet:{id,name,state,seller_id,date_from,date_to,voucher_count}} "
            "with state submitted. Internal users only."
        ),
        input_schema=_DECLARE_COLLECTION_CASH_SCHEMA,
        category="write",
        registry="mcp",
    )
    def declare_collection_cash(
        self,
        seller_id: int,
        commission_withheld: Any,
        **kwargs: Any,
    ) -> dict:
        """Declare Cash on the seller's submitted sheet.

        :raise AccessError: when the caller is not an internal user.
        :raise UserError: when the seller is invalid, extra keys are passed,
            amounts are invalid, or the submitted-sheet set is empty or mixed.
        """
        if kwargs:
            _collection_reject_unknown_keys(
                kwargs,
                frozenset(),
                _("declare_collection_cash"),
            )
        if not self.env.user.has_group("base.group_user"):
            raise AccessError(_("Only internal users can declare collection cash."))
        try:
            withheld = _collection_normalize_amount(commission_withheld)
        except ValueError as err:
            raise UserError(_("commission_withheld must be an amount.")) from err
        seller = self._collection_require_internal_seller(seller_id)
        Sheet = self.env["collection.sheet"]
        Sheet._lock_open_sheet_for_seller(seller, self.env.company)
        submitted = Sheet._submitted_sheets_for_seller(seller, self.env.company)
        if len(submitted) > 1:
            raise UserError(_("This seller has more than one open collection sheet."))
        if not submitted:
            raise UserError(_("This seller has no submitted collection sheet."))
        submitted.check_access("write")
        submitted.action_declare_cash(commission_withheld=withheld)
        return {"sheet": self._collection_sheet_identity(submitted)}
