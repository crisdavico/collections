# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    """Remap allocation state from parent sheet; collapse dropped keys."""
    # SQL first so ORM never browses leftover validated/rejected Selection keys.
    cr.execute(
        """
        UPDATE collection_allocation a
           SET state = CASE
                WHEN s.state = 'open' THEN 'draft'
                WHEN s.state = 'closed' THEN 'confirmed'
                ELSE a.state
           END
          FROM collection_sheet s
         WHERE a.sheet_id = s.id
        """
    )
    cr.execute(
        """
        UPDATE collection_allocation
           SET state = 'confirmed'
         WHERE state IN ('validated', 'rejected')
        """
    )
