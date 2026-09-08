# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import annotations

from typing import Any

from odoo import _, api, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.collection.tools.collection_voucher import (
    _collection_reject_unknown_keys,
)
from odoo.addons.muk_mcp.core.tool import mcp_tool

_CLOSE_COLLECTION_SHEET_SCHEMA = {
    "type": "object",
    "properties": {
        "seller_id": {
            "type": "integer",
            "minimum": 1,
            "description": "Internal seller user id.",
        },
    },
    "required": ["seller_id"],
}


class CollectionSheetCloseMcpMixin(models.AbstractModel):
    """MuK MCP write tool to Seller Close a seller's open collection sheet."""

    _inherit = "muk_mcp.mixin"

    @api.model
    @mcp_tool(
        name="close_collection_sheet",
        description=(
            "Seller Close the authenticated seller's open collection sheet. "
            "Returns {sheet:{id,name,state,seller_id,date_from,date_to,"
            "voucher_count}, cash:{collected}} with state submitted. "
            "Internal users only."
        ),
        input_schema=_CLOSE_COLLECTION_SHEET_SCHEMA,
        category="write",
        registry="mcp",
    )
    def close_collection_sheet(
        self,
        seller_id: int,
        **kwargs: Any,
    ) -> dict:
        """Close the seller's open sheet via Seller Close.

        :raise AccessError: when the caller is not an internal user.
        :raise UserError: when the seller is invalid, extra keys are passed,
            or the open-sheet set is empty or mixed.
        """
        if kwargs:
            _collection_reject_unknown_keys(
                kwargs,
                frozenset(),
                _("close_collection_sheet"),
            )
        if not self.env.user.has_group("base.group_user"):
            raise AccessError(_("Only internal users can close collection sheets."))
        seller = self._collection_require_internal_seller(seller_id)
        Sheet = self.env["collection.sheet"]
        Sheet._lock_open_sheet_for_seller(seller, self.env.company)
        opens = Sheet._open_sheets_for_seller(seller, self.env.company)
        if len(opens) > 1:
            raise UserError(_("This seller has more than one open collection sheet."))
        if not opens:
            raise UserError(_("This seller has no open collection sheet."))
        opens.check_access("write")
        collected = opens._cash_collected_total()
        opens.action_seller_close()
        return {
            "sheet": self._collection_sheet_identity(opens),
            "cash": {"collected": collected},
        }
