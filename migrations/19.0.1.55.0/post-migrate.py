# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Carry what the audit tables held into the allocation and voucher, then drop them.

Odoo removes the ir.model rows of the dropped models but keeps their tables,
whose restrict keys would still block deletes. Before dropping them:

- each allocation's revisions become its ``request_log``, and the latest one
  its ``request_id`` and ``content_hash``, so earlier agent requests replay;
- the cash replacement ledger nets into the ``replaced_amount`` and
  ``replacing_amount`` counters, so a later undo gives the right cash back.
"""

from odoo.tools import SQL

_DROPPED_TABLES = (
    "collection_allocation_revision",
    "collection_voucher_review_snapshot",
    "collection_cash_replacement",
)


def _table_exists(cr, table):
    cr.execute("SELECT 1 FROM pg_class WHERE relname = %s AND relkind = 'r'", (table,))
    return bool(cr.fetchone())


def _backfill_requests(cr):
    cr.execute(
        """
        UPDATE collection_allocation allocation
           SET request_log = log.entries,
               request_id = last.request_id,
               content_hash = last.content_hash
          FROM (
                SELECT allocation_id,
                       jsonb_object_agg(
                           request_id,
                           jsonb_build_object(
                               'revision', revision,
                               'content_hash', content_hash,
                               -- Two decimals, so whole amounts read as floats.
                               'total_vouchers',
                               round(COALESCE(total_vouchers, 0.0), 2),
                               'total_applied',
                               round(COALESCE(total_applied, 0.0), 2),
                               'residual', round(COALESCE(residual, 0.0), 2)
                           )
                           ORDER BY revision, id
                       ) AS entries
                  FROM collection_allocation_revision
                 GROUP BY allocation_id
               ) log,
               (
                SELECT DISTINCT ON (allocation_id)
                       allocation_id, request_id, content_hash
                  FROM collection_allocation_revision
                 ORDER BY allocation_id, revision DESC, id DESC
               ) last
         WHERE log.allocation_id = allocation.id
           AND last.allocation_id = allocation.id
        """
    )


def _backfill_cash_counters(cr):
    for counter, key in (
        ("replaced_amount", "cash_voucher_id"),
        ("replacing_amount", "deposit_voucher_id"),
    ):
        cr.execute(
            SQL(
                """
                UPDATE collection_voucher voucher
                   SET %(counter)s = ledger.net
                  FROM (
                        SELECT %(key)s AS voucher_id,
                               SUM(CASE WHEN direction = 'replace'
                                        THEN amount ELSE -amount END) AS net
                          FROM collection_cash_replacement
                         GROUP BY %(key)s
                       ) ledger
                 WHERE ledger.voucher_id = voucher.id
                """,
                counter=SQL.identifier(counter),
                key=SQL.identifier(key),
            )
        )


def migrate(cr, version):
    if _table_exists(cr, "collection_allocation_revision"):
        _backfill_requests(cr)
    if _table_exists(cr, "collection_cash_replacement"):
        _backfill_cash_counters(cr)
    for table in _DROPPED_TABLES:
        cr.execute(SQL("DROP TABLE IF EXISTS %s CASCADE", SQL.identifier(table)))
