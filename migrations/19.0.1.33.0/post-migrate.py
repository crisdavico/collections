# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    """Unlink the retired reassign kanban view/XMLID. Do not remap sheet states."""
    cr.execute(
        """
        DELETE FROM ir_ui_view
        WHERE id IN (
            SELECT res_id FROM ir_model_data
            WHERE module = 'collection'
              AND name = 'view_collection_voucher_reassign_kanban'
              AND model = 'ir.ui.view'
        )
        """
    )
    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE module = 'collection'
          AND name = 'view_collection_voucher_reassign_kanban'
        """
    )
