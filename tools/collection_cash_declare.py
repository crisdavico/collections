# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import annotations

from typing import Any

from odoo import _, api, models
from odoo.exceptions import UserError

from odoo.addons.collection.tools.collection_voucher import (
    _COLLECTION_AMOUNT_SCHEMA,
    _collection_normalize_amount,
    _collection_reject_unknown_keys,
)
from odoo.addons.muk_mcp.core.tool import mcp_tool

_DECLARE_COLLECTION_CASH_SCHEMA = {
    "type": "object",
    "properties": {
        "seller_id": {
            "type": "integer",
            "minimum": 1,
            "description": "Internal seller user id.",
        },
        "commission_withheld": dict(_COLLECTION_AMOUNT_SCHEMA),
    },
    "required": ["seller_id", "commission_withheld"],
}


class CollectionCashDeclareMcpMixin(models.AbstractModel):
    """MuK MCP write tool to Declare Cash on a seller's submitted sheet."""

    _inherit = "muk_mcp.mixin"

    @api.model
    @mcp_tool(
        name="declare_collection_cash",
        description=(
            "Declare Cash on the authenticated seller's submitted collection "
            "sheet with commission_withheld: the cash the seller kept as "
            "commission, at most the sheet's computed commission and at most "
            "the cash collected minus seller deposits. Cash to Administration "
            "is computed from the sheet vouchers and MUST NOT be sent. Returns "
            "{sheet:{id,name,state,seller_id,date_from,date_to,voucher_count}, "
            "commission:{percent,amount,withheld,owed}} with state submitted; "
            "owed is the commission not kept from cash. Collections Users only."
        ),
        input_schema=_DECLARE_COLLECTION_CASH_SCHEMA,
        category="write",
        registry="mcp",
    )
    def declare_collection_cash(
        self,
        seller_id: int | None = None,
        commission_withheld: Any = None,
        **kwargs: Any,
    ) -> dict:
        """Declare Cash on the seller's submitted sheet.

        :raise AccessError: when the caller is not a Collections User, or the
            trusted seller header does not verify the seller.
        :raise UserError: when the seller is invalid, extra keys are passed,
            amounts are invalid, or the submitted-sheet set is empty or mixed.
        """
        if kwargs:
            _collection_reject_unknown_keys(
                kwargs,
                frozenset(),
                _("declare_collection_cash"),
            )
        self._collection_require_collection_user()
        try:
            withheld = _collection_normalize_amount(commission_withheld)
        except ValueError as err:
            raise UserError(_("commission_withheld must be an amount.")) from err
        currency = self.env.company.currency_id
        if currency.compare_amounts(withheld, 0.0) < 0:
            raise UserError(_("commission_withheld must be zero or more."))
        seller = self._collection_mcp_seller(seller_id)
        Sheet = self.env["collection.sheet"]
        Sheet._lock_open_sheet_for_seller(seller, self.env.company)
        submitted = Sheet._submitted_sheets_for_seller(seller, self.env.company)
        if len(submitted) > 1:
            raise UserError(_("This seller has more than one open collection sheet."))
        if not submitted:
            raise UserError(_("This seller has no submitted collection sheet."))
        submitted.check_access("write")
        commission = submitted.commission_amount or 0.0
        if currency.compare_amounts(withheld, commission) > 0:
            raise UserError(
                _(
                    "commission_withheld cannot exceed the seller commission "
                    "of %(amount)s.",
                    amount=commission,
                )
            )
        cash = max(
            (submitted.cash_collected or 0.0) - (submitted.cash_banked or 0.0), 0.0
        )
        if currency.compare_amounts(withheld, cash) > 0:
            raise UserError(
                _(
                    "commission_withheld cannot exceed the cash collected minus "
                    "seller deposits, %(amount)s.",
                    amount=cash,
                )
            )
        submitted.action_declare_cash(commission_withheld=withheld)
        return {
            "sheet": self._collection_sheet_identity(submitted),
            "commission": {
                "percent": submitted.commission_percent or 0.0,
                "amount": submitted.commission_amount or 0.0,
                "withheld": submitted.commission_withheld or 0.0,
                "owed": submitted.commission_owed or 0.0,
            },
        }
