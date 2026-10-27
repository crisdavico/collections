# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import annotations

from odoo import _, api, models
from odoo.exceptions import UserError

from odoo.addons.muk_mcp.core.tool import mcp_tool

_GET_COLLECTION_SUMMARY_SCHEMA = {
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

_NULL_SHEET = {"sheet": None}


class CollectionSheetSummaryMcpMixin(models.AbstractModel):
    """MuK MCP read tool for the open sheet's Planilla totals."""

    _inherit = "muk_mcp.mixin"

    @api.model
    @api.private
    def _collection_sheet_summary_payload(self, sheet) -> dict:
        """Project the Planilla payload of one sheet to its totals."""
        data = sheet._collection_report_data()
        tendered = data["tendered"]
        recon = data["recon"]
        return {
            "sheet": self._collection_sheet_identity(sheet),
            "collected": {
                "cash": recon["cash_collected"],
                "cash_deposits": tendered["deposits"],
                "checks": tendered["checks"],
                "transfers": tendered["transfers"],
                "echecks": tendered["echecks"],
                "retentions": tendered["retentions"],
                "total": data["collected_total"],
            },
            "cash": {
                "collected": recon["cash_collected"],
                "banked": recon["cash_banked"],
            },
            "commission": {
                "percent": data["commission_percent"],
                "amount": recon["commission"],
            },
        }

    @api.model
    @mcp_tool(
        name="get_collection_summary",
        description=(
            "Return the totals of the authenticated seller's open collection "
            "sheet, the same the Planilla de Cobranza shows: {sheet:{id,name,"
            "state,seller_id,date_from,date_to,voucher_count}, collected:{cash,"
            "cash_deposits,checks,transfers,echecks,retentions,total}, cash:"
            "{collected,banked}, commission:{percent,amount}}, or {sheet: null} "
            "when no sheet is open. collected is what customers paid by voucher "
            "type; cash.banked is the seller deposits; commission.amount is the "
            "seller's commission computed by the sheet. When cash.collected is "
            "above zero, close_collection_sheet needs commission_withheld. "
            "Collections Users only."
        ),
        input_schema=_GET_COLLECTION_SUMMARY_SCHEMA,
        category="read",
        registry="mcp",
    )
    def get_collection_summary(self, seller_id: int | None = None) -> dict:
        """Return the open sheet's Planilla totals, or sheet null.

        :raise AccessError: when the caller is not a Collections User, or the
            trusted seller header does not verify the seller.
        :raise UserError: when the seller is invalid, the open-sheet set is, or
            the sheet mixes currencies.
        """
        self._collection_require_collection_user()
        seller = self._collection_mcp_seller(seller_id)
        opens = self.env["collection.sheet"]._open_sheets_for_seller(
            seller, self.env.company
        )
        if len(opens) > 1:
            raise UserError(_("This seller has more than one open collection sheet."))
        if not opens:
            return dict(_NULL_SHEET)
        opens.check_access("read")
        return self._collection_sheet_summary_payload(opens)
