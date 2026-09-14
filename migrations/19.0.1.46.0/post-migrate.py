# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Recompute stored ``cash_on_hand`` over the seller-declared column.

    The column already existed, so ``_init_column`` never fires: without this
    every historical sheet would keep the amount the seller typed instead of
    collected cash minus seller deposits minus commission withheld.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    sheets = env["collection.sheet"].search([])
    if not sheets:
        return
    env.add_to_compute(env["collection.sheet"]._fields["cash_on_hand"], sheets)
    sheets.flush_recordset(["cash_on_hand"])
