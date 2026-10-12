# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import annotations

from odoo import api, models

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
            "{customer, summary, invoices, as_of} with invoice document_kind "
            "(default invoice) and allocatable_balance (gross balance minus "
            "draft and confirmed reservations, clamped at zero). as_of is "
            "when the figures were read from the ERP (ISO 8601, company "
            "timezone). Refuses with an error when the connector's copy of "
            "the ERP is out of date. Collections Users only."
        ),
        input_schema=_CUSTOMER_DEBT_SCHEMA,
        category="read",
        registry="mcp",
    )
    def customer_debt(
        self, seller_id: int | None = None, customer_identification: str | None = None
    ) -> dict:
        """Return outstanding connector debt for one Enabled Seller customer.

        :raise AccessError: when the caller is not a Collections User, or the
            trusted seller header does not verify the seller.
        :raise UserError: when the seller, customer, connector, or adapter is
            unavailable.
        """
        self._collection_require_collection_user()
        seller = self._collection_mcp_seller(seller_id)
        connector = self.env.company._collection_active_connector()
        result = connector.get_customer_debt(seller.id, customer_identification)
        result.pop("source", None)
        invoices = result.get("invoices") or []
        for invoice in invoices:
            kind = invoice.get("document_kind")
            if kind in (None, False, ""):
                invoice["document_kind"] = "invoice"
        reserved = self._collection_reserved_amounts(
            [
                invoice["external_invoice_id"]
                for invoice in invoices
                if invoice.get("external_invoice_id")
            ]
        )
        total_allocatable = 0.0
        open_allocatable = 0.0
        overdue_allocatable = 0.0
        for invoice in invoices:
            gross = invoice.get("balance") or 0.0
            elsewhere = reserved.get(invoice.get("external_invoice_id"), 0.0)
            allocatable = gross - elsewhere
            if allocatable < 0.0:
                allocatable = 0.0
            invoice["allocatable_balance"] = allocatable
            total_allocatable += allocatable
            state = invoice.get("state")
            if state == "open":
                open_allocatable += allocatable
            elif state == "overdue":
                overdue_allocatable += allocatable
        summary = result.setdefault("summary", {})
        summary["total_allocatable_balance"] = total_allocatable
        summary["open_allocatable_balance"] = open_allocatable
        summary["overdue_allocatable_balance"] = overdue_allocatable
        return result
