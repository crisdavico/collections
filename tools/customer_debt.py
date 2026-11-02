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
            "description": (
                "Customer CUIT, customer code, or the numeric part of the code "
                "when only one of this seller's customers has that number."
            ),
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
            "{customer, summary, invoices, as_of}. Each invoice has its ERP "
            "balance, document_kind (default invoice), allocatable_balance (its "
            "real open amount: the ERP balance net of what collection sheets "
            "already applied that the ERP does not show yet, never below zero) "
            "and in_collection (balance minus allocatable_balance). "
            "summary.pending_total is what the customer still owes: "
            "summary.net_total (open invoices, gross_total, net of open credit "
            "notes, credit_total; also total_balance) minus "
            "summary.in_collection_total, the money already collected on sheets "
            "and pending entry in the ERP. Allocations only apply to the listed "
            "invoices. as_of is when the figures were read from the ERP "
            "(ISO 8601, company timezone). Refuses with an error when the "
            "connector's copy of the ERP is out of date. Collections Users only."
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
            # Commission base: not part of what the agent tells the seller.
            invoice.pop("amount_untaxed", None)
            kind = invoice.get("document_kind")
            if kind in (None, False, ""):
                invoice["document_kind"] = "invoice"
        open_amounts = self.env["collection.allocation.line"]._open_amounts(
            {
                invoice["external_invoice_id"]: invoice.get("balance") or 0.0
                for invoice in invoices
                if invoice.get("external_invoice_id")
            }
        )
        currency = self.env.company.currency_id
        total_allocatable = 0.0
        open_allocatable = 0.0
        overdue_allocatable = 0.0
        in_collection_total = 0.0
        for invoice in invoices:
            gross = invoice.get("balance") or 0.0
            allocatable = open_amounts.get(
                invoice.get("external_invoice_id"), max(gross, 0.0)
            )
            invoice["allocatable_balance"] = allocatable
            invoice["in_collection"] = currency.round(max(gross - allocatable, 0.0))
            in_collection_total += invoice["in_collection"]
            total_allocatable += allocatable
            state = invoice.get("state")
            if state == "open":
                open_allocatable += allocatable
            elif state == "overdue":
                overdue_allocatable += allocatable
        summary = result.setdefault("summary", {})
        summary["total_allocatable_balance"] = currency.round(total_allocatable)
        summary["open_allocatable_balance"] = currency.round(open_allocatable)
        summary["overdue_allocatable_balance"] = currency.round(overdue_allocatable)
        summary["in_collection_total"] = currency.round(in_collection_total)
        net_total = summary.get("net_total", summary.get("total_balance")) or 0.0
        summary["pending_total"] = currency.round(net_total - in_collection_total)
        return result
