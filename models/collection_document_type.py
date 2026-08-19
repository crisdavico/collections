# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CollectionDocumentType(models.Model):
    _name = "collection.document.type"
    _description = "Collection Document Type"
    _order = "name"

    code = fields.Char(required=True)
    name = fields.Char(required=True, translate=True)

    _code_uniq = models.Constraint(
        "UNIQUE(code)",
        "Document type code must be unique.",
    )
