# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    """ORM adds collection.receipt / collection.receipt.value. Do not backfill."""
    return None
