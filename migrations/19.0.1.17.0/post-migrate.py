# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api

COLLECTION_SEQUENCE_CODES = ("collection.voucher", "collection.sheet")


def _main_company_id(cr):
    cr.execute(
        """
        SELECT res_id
          FROM ir_model_data
         WHERE module = 'base'
           AND name = 'main_company'
        """
    )
    row = cr.fetchone()
    if row:
        return row[0]
    cr.execute("SELECT id FROM res_company ORDER BY id LIMIT 1")
    row = cr.fetchone()
    return row[0] if row else None


def migrate(cr, version):
    """Stamp companies, seed sellers/types, and convert per-company sequences."""
    main_id = _main_company_id(cr)
    if not main_id:
        return

    # 1. Sheet company from seller company else database main company.
    cr.execute(
        """
        UPDATE collection_sheet s
           SET company_id = COALESCE(u.company_id, %s)
          FROM res_users u
         WHERE s.seller_id = u.id
        """,
        (main_id,),
    )

    # 2. Voucher company from sheet when set, else seller company else main.
    cr.execute(
        """
        UPDATE collection_voucher v
           SET company_id = COALESCE(
                (SELECT s.company_id
                   FROM collection_sheet s
                  WHERE s.id = v.sheet_id),
                (SELECT u.company_id
                   FROM res_users u
                  WHERE u.id = v.seller_id),
                %s
           )
        """,
        (main_id,),
    )

    # 3. Repair member vouchers so voucher.company_id = sheet.company_id.
    cr.execute(
        """
        UPDATE collection_voucher v
           SET company_id = s.company_id
          FROM collection_sheet s
         WHERE v.sheet_id = s.id
           AND v.company_id IS DISTINCT FROM s.company_id
        """
    )

    # 4. Seed enabled sellers from distinct sellers on that company's
    # vouchers and sheets (include inactive / historically used).
    cr.execute(
        """
        INSERT INTO res_company_collection_enabled_seller_rel
            (company_id, user_id)
        SELECT DISTINCT company_id, seller_id
          FROM (
                SELECT company_id, seller_id
                  FROM collection_voucher
                 WHERE seller_id IS NOT NULL
                   AND company_id IS NOT NULL
                UNION
                SELECT company_id, seller_id
                  FROM collection_sheet
                 WHERE seller_id IS NOT NULL
                   AND company_id IS NOT NULL
               ) t
            ON CONFLICT (company_id, user_id) DO NOTHING
        """
    )

    env = api.Environment(cr, SUPERUSER_ID, {})
    companies = env["res.company"].search([])
    # 5. Enable all four catalog types on every company (union, no wipe).
    companies._collection_enable_all_document_types()
    # 6. Bind company-less sequences to main, copy others, drop leftovers.
    _migrate_collection_sequences(env, main_id)


def _migrate_collection_sequences(env, main_id):
    Sequence = env["ir.sequence"]
    main = env["res.company"].browse(main_id)
    for code in COLLECTION_SEQUENCE_CODES:
        main_seq = Sequence.search(
            [("code", "=", code), ("company_id", "=", main.id)],
            limit=1,
        )
        orphans = Sequence.search([("code", "=", code), ("company_id", "=", False)])
        if not main_seq and orphans:
            keep = max(orphans, key=lambda seq: seq.number_next_actual)
            keep.company_id = main.id
            orphans -= keep
        orphans.unlink()
    env["res.company"].search([])._collection_copy_sequences()
