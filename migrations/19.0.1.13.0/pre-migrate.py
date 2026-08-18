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
    """Convert Binary field attachments into chatter files before the field drop."""
    has_filename = _has_column(cr, "collection_voucher", "attachment_filename")
    filename_select = (
        "v.attachment_filename" if has_filename else "NULL::varchar"
    )
    cr.execute(
        """
        SELECT res_id FROM ir_model_data
         WHERE module = 'mail' AND name = 'mt_note'
        """
    )
    subtype_row = cr.fetchone()
    subtype_id = subtype_row[0] if subtype_row else None
    cr.execute(
        f"""
        SELECT a.id, a.res_id, a.name, {filename_select}
          FROM ir_attachment a
     LEFT JOIN collection_voucher v ON v.id = a.res_id
         WHERE a.res_model = 'collection.voucher'
           AND a.res_field = 'attachment'
        """
    )
    rows = cr.fetchall()
    for attachment_id, res_id, current_name, stored_filename in rows:
        new_name = (stored_filename or "").strip()
        if not new_name:
            current = (current_name or "").strip()
            new_name = (
                "proof.bin" if current in ("", "attachment") else current
            )
        cr.execute(
            """
            UPDATE ir_attachment
               SET res_field = NULL,
                   name = %s
             WHERE id = %s
            """,
            (new_name, attachment_id),
        )
        cr.execute(
            """
            SELECT 1
              FROM message_attachment_rel
             WHERE attachment_id = %s
            """,
            (attachment_id,),
        )
        if cr.fetchone() or not res_id:
            continue
        cr.execute(
            """
            INSERT INTO mail_message (
                model, res_id, body, message_type, subtype_id,
                date, create_uid, write_uid, create_date, write_date, author_id
            )
            VALUES (
                'collection.voucher', %s, 'Payment proof attached.',
                'notification', %s,
                (now() AT TIME ZONE 'UTC'), 1, 1,
                (now() AT TIME ZONE 'UTC'), (now() AT TIME ZONE 'UTC'),
                (SELECT partner_id FROM res_users WHERE id = 1)
            )
            RETURNING id
            """,
            (res_id, subtype_id),
        )
        message_id = cr.fetchone()[0]
        cr.execute(
            """
            INSERT INTO message_attachment_rel (message_id, attachment_id)
            VALUES (%s, %s)
            """,
            (message_id, attachment_id),
        )
