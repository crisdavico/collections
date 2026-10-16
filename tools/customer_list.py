# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import annotations

from odoo import api, models

from odoo.addons.muk_mcp.core.tool import mcp_tool

from ..customer_match import CUSTOMER_SEARCH_LIMIT, search_customers

_LIST_COLLECTION_CUSTOMERS_SCHEMA = {
    "type": "object",
    "properties": {
        "seller_id": {
            "type": "integer",
            "description": "Internal seller user id (Enabled Seller).",
        },
        "query": {
            "type": "string",
            "description": (
                "Optional customer name, CUIT, or customer code, whole or in "
                f"part. Returns at most {CUSTOMER_SEARCH_LIMIT} customers best "
                "first, each with match exact, partial, or similar, plus "
                "total_matches and truncated. Omit it to list every customer."
            ),
        },
    },
    "required": ["seller_id"],
}


class CollectionCustomerListMixin(models.AbstractModel):
    """MuK MCP read tool for seller-scoped connector customers."""

    _inherit = "muk_mcp.mixin"

    @api.model
    @mcp_tool(
        name="list_collection_customers",
        description=(
            "List active customers for an Enabled Seller from the company's "
            "collection connector. Returns {customers}; with query, only the "
            "best matches. Collections Users only."
        ),
        input_schema=_LIST_COLLECTION_CUSTOMERS_SCHEMA,
        category="read",
        registry="mcp",
    )
    def list_collection_customers(
        self, seller_id: int | None = None, query: str | None = None
    ) -> dict:
        """Return active connector customers for an Enabled Seller.

        A non-blank ``query`` keeps only the customers it may mean
        (``search_customers``); a blank one lists them all.

        :raise AccessError: when the caller is not a Collections User, or the
            trusted seller header does not verify the seller.
        :raise UserError: when the seller, connector, or adapter is unavailable.
        """
        self._collection_require_collection_user()
        seller = self._collection_mcp_seller(seller_id)
        connector = self.env.company._collection_active_connector()
        result = connector.list_customers(seller.id)
        result.pop("source", None)
        text = str(query or "").strip()
        if text:
            return search_customers(result.get("customers") or [], text)
        return result
