# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    """Rename payment-line review_status column to state before ORM update."""
    cr.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'collection_voucher_line'
          AND column_name = 'review_status'
        """
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'collection_voucher_line'
          AND column_name = 'state'
        """
    )
    if cr.fetchone():
        return
    cr.execute(
        "ALTER TABLE collection_voucher_line RENAME COLUMN review_status TO state"
    )
    cr.execute(
        """
        UPDATE ir_model_fields
           SET name = 'state'
         WHERE model = 'collection.voucher.line'
           AND name = 'review_status'
        """
    )
