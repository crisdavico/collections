# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    """Remap voucher state keys before ORM browse; leave snapshot decision."""
    # SQL first so ORM never browses leftover pending/approved/rejected keys.
    cr.execute(
        """
        UPDATE collection_voucher
           SET state = CASE
                WHEN state = 'pending' THEN 'draft'
                WHEN state = 'approved' THEN 'validated_collections'
                WHEN state = 'rejected' THEN 'draft'
                ELSE state
           END
        """
    )
    cr.execute(
        """
        UPDATE collection_voucher
           SET state = 'draft'
         WHERE state NOT IN (
            'draft', 'validated_seller', 'validated_collections'
         )
        """
    )
