# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    """Remove the retired settings views before validating the connector form.

    Connector values live on the persistent connector and are never rewritten.
    Odoo's obsolete-model cleanup removes the transient model, ACLs and rule.
    """
    cr.execute(
        """
        DELETE FROM ir_ui_view
        WHERE id IN (
            SELECT res_id FROM ir_model_data
            WHERE module = 'collection'
              AND name IN ('view_collection_connector_form_management',
                           'view_collection_connector_settings_form')
              AND model = 'ir.ui.view'
        )
        """
    )
    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE module = 'collection'
          AND name IN ('view_collection_connector_form_management',
                       'view_collection_connector_settings_form')
          AND model = 'ir.ui.view'
        """
    )
