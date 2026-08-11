# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Collections",
    "version": "19.0.1.3.0",
    "category": "Sales/CRM",
    "summary": "Manual payment vouchers for cobranzas",
    "author": "Seedian",
    "website": "https://seedian.ai",
    "depends": ["base", "mail", "muk_mcp"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/collection_views.xml",
    ],
    "installable": True,
    "application": True,
    "license": "AGPL-3",
}
