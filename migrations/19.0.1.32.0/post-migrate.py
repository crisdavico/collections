# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    """Drop leftover residual_reason columns after the field is removed."""
    cr.execute(
        """
        ALTER TABLE collection_allocation
            DROP COLUMN IF EXISTS residual_reason
        """
    )
    cr.execute(
        """
        ALTER TABLE IF EXISTS collection_allocation_revision
            DROP COLUMN IF EXISTS residual_reason
        """
    )
    cr.execute(
        """
        ALTER TABLE collection_allocation_line
            DROP CONSTRAINT IF EXISTS
                collection_allocation_line_amount_applied_lte_balance
        """
    )
    cr.execute(
        """
        ALTER TABLE collection_allocation_line
            DROP CONSTRAINT IF EXISTS
                collection_allocation_line_amount_applied_non_negative
        """
    )
    cr.execute(
        """
        DELETE FROM ir_ui_view
        WHERE id IN (
            SELECT res_id FROM ir_model_data
            WHERE module = 'collection'
              AND name = 'view_collection_allocation_form_document_kind'
              AND model = 'ir.ui.view'
        )
        """
    )
    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE module = 'collection'
          AND name = 'view_collection_allocation_form_document_kind'
        """
    )
