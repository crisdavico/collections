# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import annotations

import base64
import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.muk_mcp.core.tool import mcp_tool

_REPORT_XMLID = "collection.action_report_collection_sheet"
_FILENAME_STEM = "Planilla_de_Cobranza"

_GET_COLLECTION_SHEET_PDF_SCHEMA = {
    "type": "object",
    "properties": {
        "seller_id": {
            "type": "integer",
            "minimum": 1,
            "description": "Internal seller user id (Enabled Seller).",
        },
    },
    "required": ["seller_id"],
}

_NULL_SHEET = {"sheet": None}


class CollectionSheetReportMcpMixin(models.AbstractModel):
    """MuK MCP read tool for the open-sheet Planilla de Cobranza PDF."""

    _inherit = "muk_mcp.mixin"

    @api.model
    @api.private
    def _collection_sheet_pdf_filename(self, sheet) -> str:
        """Return a slug filename built from the sheet reference (CS/2026/0001)."""
        reference = re.sub(r"[^A-Za-z0-9._-]+", "-", (sheet.name or "").strip())
        reference = reference.strip("-")
        if not reference or reference == "-":
            reference = str(sheet.id)
        return f"{_FILENAME_STEM}_{reference}.pdf"

    @api.model
    @api.private
    def _collection_render_sheet_pdf(self, sheet) -> tuple[bytes, str]:
        """Render the bound Planilla report for one sheet; return (bytes, mimetype).

        :raise UserError: when the report action is missing from the database.
        """
        report = self._resolve_report(_REPORT_XMLID)
        if not report:
            raise UserError(_("The collection sheet report is not installed."))
        content, report_type = report._render(report.report_name, sheet.ids)
        if isinstance(content, str):
            content = content.encode()
        mimetype, _extension = self._report_mimetype(report_type)
        return content, mimetype

    @api.model
    @api.private
    def _collection_sheet_pdf_payload(self, sheet) -> dict:
        """Build the base64 envelope plus sheet metadata for one open sheet."""
        content, mimetype = self._collection_render_sheet_pdf(sheet)
        return {
            "sheet": {
                "id": sheet.id,
                "name": sheet.name,
                "state": sheet.state,
                "seller_id": sheet.seller_id.id,
                "date_from": fields.Date.to_string(sheet.date_from) or None,
                "date_to": fields.Date.to_string(sheet.date_to) or None,
                "voucher_count": sheet.voucher_count,
            },
            "filename": self._collection_sheet_pdf_filename(sheet),
            "mimetype": mimetype,
            "content_base64": base64.b64encode(content).decode(),
        }

    @api.model
    @mcp_tool(
        name="get_collection_sheet_pdf",
        description=(
            "Render the Planilla de Cobranza of a seller's open collection sheet "
            "and return it as base64 ({sheet, filename, mimetype, content_base64}), "
            "or {sheet: null} when the seller has no open sheet. Internal users only."
        ),
        input_schema=_GET_COLLECTION_SHEET_PDF_SCHEMA,
        category="read",
        registry="mcp",
    )
    def get_collection_sheet_pdf(self, seller_id: int) -> dict:
        """Return the open-sheet Planilla PDF payload or sheet null.

        :raise AccessError: when the caller is not an internal user.
        :raise UserError: when the seller is invalid or the open-sheet set is.
        """
        if not self.env.user.has_group("base.group_user"):
            raise AccessError(_("Only internal users can print collection sheets."))
        seller = self._collection_require_internal_seller(seller_id)
        opens = self.env["collection.sheet"]._open_sheets_for_seller(
            seller, self.env.company
        )
        if len(opens) > 1:
            raise UserError(_("This seller has more than one open collection sheet."))
        if not opens:
            return dict(_NULL_SHEET)
        opens.check_access("read")
        return self._collection_sheet_pdf_payload(opens)
