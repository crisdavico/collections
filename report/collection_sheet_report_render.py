# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class CollectionSheetReportRender(models.AbstractModel):
    _name = "report.collection.report_collection_sheet"
    _description = "Collection Sheet QWeb Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        """Return one Planilla payload per sheet; set `o` for external_layout."""
        sheets = self.env["collection.sheet"].browse(docids)
        sheets.check_access("read")
        payloads = [sheet._collection_report_data() for sheet in sheets]
        return {
            "doc_ids": docids,
            "doc_model": "collection.sheet",
            "docs": sheets,
            "data": data,
            "payloads": payloads,
            "o": payloads[0]["sheet"] if payloads else sheets,
        }
