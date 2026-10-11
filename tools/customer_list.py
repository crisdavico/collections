# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import annotations

from odoo import api, models

from odoo.addons.muk_mcp.core.tool import mcp_tool

_LIST_COLLECTION_CUSTOMERS_SCHEMA = {
    "type": "object",
    "properties": {
        "seller_id": {
            "type": "integer",
            "description": "Internal seller user id (Enabled Seller).",
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
            "collection connector. Returns {customers}. Collections Users only."
        ),
        input_schema=_LIST_COLLECTION_CUSTOMERS_SCHEMA,
        category="read",
        registry="mcp",
    )
    def list_collection_customers(self, seller_id: int | None = None) -> dict:
        """Return active connector customers for an Enabled Seller.

        :raise AccessError: when the caller is not a Collections User, or the
            trusted seller header does not verify the seller.
        :raise UserError: when the seller, connector, or adapter is unavailable.
        """
        self._collection_require_collection_user()
        seller = self._collection_mcp_seller(seller_id)
        connector = self.env.company._collection_active_connector()
        result = connector.list_customers(seller.id)
        result.pop("source", None)
        return result
