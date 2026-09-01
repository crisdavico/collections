# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Copy per-company collection sequences, including CA/."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["res.company"].search([])._collection_copy_sequences()
