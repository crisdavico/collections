# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import annotations

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.muk_mcp.core.tool import mcp_tool

_GET_COLLECTION_ALLOCATION_SCHEMA = {
    "type": "object",
    "properties": {
        "seller_id": {
            "type": "integer",
            "description": "Internal seller user id (Enabled Seller).",
        },
        "customer_identification": {
            "type": "string",
            "minLength": 1,
            "description": "Customer identification from the connector binding.",
        },
    },
    "required": ["seller_id", "customer_identification"],
}

_NULL_ALLOCATION = {"allocation": None}


class CollectionAllocationLookupMixin(models.AbstractModel):
    """MuK MCP read tool for the open-sheet collection allocation."""

    _inherit = "muk_mcp.mixin"

    @api.model
    @mcp_tool(
        name="get_collection_allocation",
        description=(
            "Return the open-sheet collection allocation for an Enabled Seller "
            "customer, or {allocation: null}. Each voucher carries its current "
            "check_number (null unless check or echeck), which an amend must "
            "restate. Collections Users only."
        ),
        input_schema=_GET_COLLECTION_ALLOCATION_SCHEMA,
        category="read",
        registry="mcp",
    )
    def get_collection_allocation(
        self, seller_id: int | None = None, customer_identification: str | None = None
    ) -> dict:
        """Return the open-sheet allocation payload or allocation null.

        :raise AccessError: when the caller is not a Collections User, or the
            trusted seller header does not verify the seller.
        :raise UserError: when the seller, connector, or open-sheet set is
            invalid.
        """
        self._collection_require_collection_user()
        seller = self._collection_mcp_seller(seller_id)
        connector = self.env.company._collection_active_connector()
        connector._enabled_bound_external_seller_id(seller.id)
        identification = str(customer_identification or "").strip()
        opens = self.env["collection.sheet"]._open_sheets_for_seller(
            seller, self.env.company
        )
        if len(opens) > 1:
            raise UserError(_("This seller has more than one open collection sheet."))
        if not opens or not identification:
            return dict(_NULL_ALLOCATION)
        binding = self.env["collection.connector.customer.binding"].search(
            [
                ("connector_id", "=", connector.id),
                ("identification", "=", identification),
            ],
            limit=1,
        )
        if not binding:
            return dict(_NULL_ALLOCATION)
        allocation = self.env["collection.allocation"].search(
            [
                ("sheet_id", "=", opens.id),
                ("partner_id", "=", binding.partner_id.id),
            ],
            limit=1,
        )
        if not allocation:
            return dict(_NULL_ALLOCATION)
        return self._collection_allocation_lookup_payload(allocation)

    @api.model
    @api.private
    def _collection_allocation_lookup_payload(self, allocation) -> dict:
        """Build the media-free get payload for one allocation."""
        return {
            "allocation": {
                "id": allocation.id,
                "name": allocation.name,
                "state": allocation.state,
                "revision": int(allocation.revision),
                "total_vouchers": allocation.total_vouchers,
                "total_applied": allocation.total_applied,
                "residual": allocation.residual,
            },
            "vouchers": [
                {
                    "id": voucher.id,
                    "name": voucher.name,
                    "state": voucher.state,
                    "document_id": voucher.document_id,
                    "amount": voucher.amount,
                    "document_type": voucher.document_type,
                    # An amend restates every voucher, and Odoo requires a
                    # check's number and compares it with this current value.
                    "check_number": voucher.check_number or None,
                }
                for voucher in allocation.voucher_ids
            ],
            "invoices": [
                {
                    "external_invoice_id": line.external_invoice_id,
                    "number": line.invoice_number or None,
                    "issue_date": fields.Date.to_string(line.issue_date)
                    if line.issue_date
                    else None,
                    "due_date": fields.Date.to_string(line.due_date)
                    if line.due_date
                    else None,
                    "amount": line.invoice_amount,
                    "balance": line.invoice_balance,
                    "state": line.invoice_state or None,
                    "amount_applied": line.amount_applied,
                    "document_kind": line.document_kind or "invoice",
                }
                for line in allocation.line_ids
            ],
            "receipts": [
                {
                    "document_kind": receipt.document_kind,
                    "state": receipt.state,
                    "external_receipt_id": receipt.external_receipt_id or None,
                    "total_values": receipt.total_values,
                    "total_applied": receipt.total_applied,
                    "amount_on_account": receipt.amount_on_account,
                    "values": [
                        {
                            "document_id": value.voucher_id.document_id,
                            "amount": value.amount,
                        }
                        for value in receipt.value_ids
                    ],
                }
                for receipt in allocation.receipt_ids
            ],
        }
