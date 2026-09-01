# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import annotations

import re

from odoo import _, api, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.muk_mcp.core.tool import mcp_tool

_GET_SELLER_ID_SCHEMA = {
    "type": "object",
    "properties": {
        "mobile": {
            "type": "string",
            "description": "Seller WhatsApp/mobile (AR variants accepted).",
        },
    },
    "required": ["mobile"],
}


class CollectionSellerLookupMixin(models.AbstractModel):
    """MuK MCP read tool for seller id lookup by mobile."""

    _inherit = "muk_mcp.mixin"

    @api.model
    @api.private
    def _collection_normalize_ar_mobile(self, value: str | None) -> str:
        """Return AR WhatsApp digits: strip non-digits, one leading 54, then one 9."""
        digits = re.sub(r"\D", "", value or "")
        if digits.startswith("54"):
            digits = digits[2:]
        if digits.startswith("9"):
            digits = digits[1:]
        return digits

    @api.model
    @api.private
    def _collection_match_internal_users_by_mobile(self, needle: str):
        """Return internal users whose phone normalizes to needle (no sudo)."""
        candidates = self.env["res.users"].search(
            [
                ("share", "=", False),
                ("phone", "!=", False),
                ("phone", "!=", ""),
            ]
        )
        return candidates.filtered(
            lambda user: self._collection_normalize_ar_mobile(user.phone) == needle
        )

    @api.model
    @mcp_tool(
        name="get_seller_id",
        description=(
            "Resolve an internal seller user id from the seller's WhatsApp/mobile. "
            "Returns {seller_id} only. Internal users only."
        ),
        input_schema=_GET_SELLER_ID_SCHEMA,
        category="read",
        registry="mcp",
    )
    def get_seller_id(self, mobile: str) -> dict:
        """Return the unique internal seller id for a normalized mobile.

        :raise AccessError: when the caller is not an internal user.
        :raise UserError: when mobile is empty/invalid or the match is not unique.
        """
        if not self.env.user.has_group("base.group_user"):
            raise AccessError(_("Only internal users can look up a seller id."))
        needle = self._collection_normalize_ar_mobile(mobile)
        if not needle:
            raise UserError(_("mobile is required."))
        enabled = self.env.company.enabled_seller_ids
        if not enabled:
            raise UserError(_("No unique seller found for that mobile."))
        matches = self._collection_match_internal_users_by_mobile(needle) & enabled
        if len(matches) != 1:
            raise UserError(_("No unique seller found for that mobile."))
        seller = self._collection_require_internal_seller(matches.id)
        return {"seller_id": seller.id}
