# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def _has_column(cr, table, column):
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = %s
           AND column_name = %s
        """,
        (table, column),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    """Assign chatter designated proof after Binary fields are dropped."""
    if not _has_column(cr, "collection_voucher", "message_main_attachment_id"):
        return
    cr.execute(
        """
        UPDATE collection_voucher v
           SET message_main_attachment_id = sub.attachment_id
          FROM (
                SELECT DISTINCT ON (a.res_id)
                       a.res_id,
                       a.id AS attachment_id
                  FROM ir_attachment a
                 WHERE a.res_model = 'collection.voucher'
                   AND (a.res_field IS NULL OR a.res_field = '')
                 ORDER BY a.res_id, a.id
               ) sub
         WHERE v.id = sub.res_id
           AND v.message_main_attachment_id IS NULL
        """
    )
    cr.execute(
        """
        UPDATE ir_attachment
           SET res_field = NULL
         WHERE res_model = 'collection.voucher'
           AND res_field = 'attachment'
        """
    )
