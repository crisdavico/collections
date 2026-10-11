# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import annotations

import re

from odoo import api, models

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
    def _collection_internal_users_with_phone(self):
        """Return internal users that carry a phone number (one search, no sudo)."""
        return self.env["res.users"].search(
            [
                ("share", "=", False),
                ("phone", "!=", False),
                ("phone", "!=", ""),
            ]
        )

    @api.model
    @api.private
    def _collection_match_internal_users_by_mobile(self, needle: str):
        """Return internal users whose phone normalizes to needle (no sudo)."""
        return self._collection_internal_users_with_phone().filtered(
            lambda user: self._collection_normalize_ar_mobile(user.phone) == needle
        )

    @api.model
    @api.private
    def _collection_enabled_seller_by_mobile(self, mobile: str | None):
        """Return the one enabled internal seller whose phone is ``mobile``.

        Empty, unknown, ambiguous and not-enabled numbers all return an empty
        recordset, so every caller answers them with one indistinct error.
        """
        Users = self.env["res.users"]
        needle = self._collection_normalize_ar_mobile(mobile)
        enabled = self.env.company.enabled_seller_ids
        if not needle or not enabled:
            return Users
        matches = self._collection_match_internal_users_by_mobile(needle) & enabled
        if len(matches) != 1 or not matches.has_group("base.group_user"):
            return Users
        return matches

    @api.model
    @mcp_tool(
        name="get_seller_id",
        description=(
            "Resolve an internal seller user id from the seller's WhatsApp/mobile. "
            "Returns {seller_id} only. Collections Users only."
        ),
        input_schema=_GET_SELLER_ID_SCHEMA,
        category="read",
        registry="mcp",
    )
    def get_seller_id(self, mobile: str | None = None) -> dict:
        """Return the unique enabled seller id for a normalized mobile.

        With a trusted seller header configured, the header names the seller
        and ``mobile``, when given, must match it.

        :raise AccessError: when the caller is not a Collections User, or the
            trusted header does not verify the seller.
        :raise UserError: when mobile is empty/invalid or the match is not unique.
        """
        self._collection_require_collection_user()
        seller = self._collection_mcp_seller_by_mobile(mobile)
        return {"seller_id": seller.id}
