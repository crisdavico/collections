# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import annotations

from odoo import _, api, models
from odoo.exceptions import AccessError

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
            "collection connector. Returns {customers}. Internal users only."
        ),
        input_schema=_LIST_COLLECTION_CUSTOMERS_SCHEMA,
        category="read",
        registry="mcp",
    )
    def list_collection_customers(self, seller_id: int) -> dict:
        """Return active connector customers for an Enabled Seller.

        :raise AccessError: when the caller is not an internal user.
        :raise UserError: when the seller, connector, or adapter is unavailable.
        """
        if not self.env.user.has_group("base.group_user"):
            raise AccessError(_("Only internal users can list collection customers."))
        seller = self._collection_require_internal_seller(seller_id)
        connector = self.env.company._collection_active_connector()
        result = connector.list_customers(seller.id)
        result.pop("source", None)
        return result
