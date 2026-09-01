# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import annotations

from odoo import _, api, models
from odoo.exceptions import AccessError

from odoo.addons.muk_mcp.core.tool import mcp_tool

_CUSTOMER_DEBT_SCHEMA = {
    "type": "object",
    "properties": {
        "seller_id": {
            "type": "integer",
            "description": "Internal seller user id (Enabled Seller).",
        },
        "customer_identification": {
            "type": "string",
            "minLength": 1,
            "description": "Customer identification from the connector.",
        },
    },
    "required": ["seller_id", "customer_identification"],
}


class CollectionCustomerDebtMixin(models.AbstractModel):
    """MuK MCP read tool for seller-scoped customer outstanding debt."""

    _inherit = "muk_mcp.mixin"

    @api.model
    @mcp_tool(
        name="customer_debt",
        description=(
            "Return outstanding invoices and balances for an Enabled Seller's "
            "active customer from the company's collection connector. Returns "
            "{customer, summary, invoices}. Internal users only."
        ),
        input_schema=_CUSTOMER_DEBT_SCHEMA,
        category="read",
        registry="mcp",
    )
    def customer_debt(self, seller_id: int, customer_identification: str) -> dict:
        """Return outstanding connector debt for one Enabled Seller customer.

        :raise AccessError: when the caller is not an internal user.
        :raise UserError: when the seller, customer, connector, or adapter is
            unavailable.
        """
        if not self.env.user.has_group("base.group_user"):
            raise AccessError(_("Only internal users can read customer debt."))
        seller = self._collection_require_internal_seller(seller_id)
        connector = self.env.company._collection_active_connector()
        result = connector.get_customer_debt(seller.id, customer_identification)
        result.pop("source", None)
        return result
