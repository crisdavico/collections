# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Collections",
    "version": "19.0.1.9.0",
    "category": "Sales/CRM",
    "summary": "Manual payment vouchers for cobranzas",
    "author": "Seedian",
    "website": "https://seedian.ai",
    "depends": ["base", "mail", "muk_mcp"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/collection_views.xml",
        "views/collection_document_review_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "collection/static/src/document_review/**/*",
        ],
    },
    "installable": True,
    "application": True,
    "license": "AGPL-3",
}
