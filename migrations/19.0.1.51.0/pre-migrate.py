# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tools import SQL

# Every column that stored a document type before ``unsupported`` was dropped.
_TYPED_COLUMNS = (
    ("collection_voucher", "document_type"),
    ("collection_voucher", "ocr_document_type"),
    ("collection_voucher", "seller_document_type"),
    ("collection_voucher_review_snapshot", "document_type"),
)


def _column_exists(cr, table, column):
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = %s AND column_name = %s
        """,
        [table, column],
    )
    return bool(cr.fetchone())


def _stored_unsupported(cr):
    """Return ``table.column (count)`` for every column still holding the value."""
    found = []
    for table, column in _TYPED_COLUMNS:
        if not _column_exists(cr, table, column):
            continue
        cr.execute(
            SQL(
                "SELECT count(*) FROM %s WHERE %s = 'unsupported'",
                SQL.identifier(table),
                SQL.identifier(column),
            )
        )
        count = cr.fetchone()[0]
        if count:
            found.append(f"{table}.{column} ({count})")
    return found


def migrate(cr, version):
    """Drop the ``unsupported`` document type; refuse when data still uses it.

    Stored values are never rewritten: an ``unsupported`` voucher has no amount
    or instrument fields, so no other type is a faithful replacement. The
    catalog row goes away here rather than through the data file's obsolete
    record cleanup, together with its XMLID and every company allow-list link,
    so nothing dangles even if a database edited the row by hand.
    """
    found = _stored_unsupported(cr)
    if found:
        raise UserError(
            "Cannot upgrade collection: the removed 'unsupported' document type "
            "is still stored in " + ", ".join(found) + ". Retype or delete those "
            "records before upgrading."
        )
    cr.execute(
        """
        DELETE FROM res_company_collection_allowed_document_type_rel
         WHERE document_type_id IN (
               SELECT id FROM collection_document_type WHERE code = 'unsupported'
         )
        """
    )
    cr.execute("DELETE FROM collection_document_type WHERE code = 'unsupported'")
    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE module = 'collection'
           AND name = 'document_type_unsupported'
           AND model = 'collection.document.type'
        """
    )
