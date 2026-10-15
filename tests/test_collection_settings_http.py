# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import HttpCase, tagged

from .test_collection_payment import create_collection_user


@tagged("post_install", "-at_install")
class TestCollectionSettingsHttp(HttpCase):
    def test_manager_configuration_navigation_and_save(self):
        manager = create_collection_user(
            self.env, "settings_browser_manager", manager=True
        )
        manager.lang = "en_US"
        company = manager.company_id
        company.auto_create_sheet = True
        action = self.env.ref("collection.action_collection_company_settings")
        self.browser_js(
            f"/odoo/action-{action.id}",
            """
            (async () => {
                const waitFor = async (predicate) => {
                    for (let i = 0; i < 200; i++) {
                        const value = predicate();
                        if (value) return value;
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }
                    throw new Error('Settings UI did not become ready');
                };
                await waitFor(() => document.querySelector('.o_notebook .nav-link'));
                const tabs = [...document.querySelectorAll('.o_notebook .nav-link')];
                if (tabs.map(tab => tab.textContent.trim()).join('|') !==
                    'General|Sellers|Bank Accounts|Integration') {
                    throw new Error('Expected four configuration tabs');
                }
                if (document.querySelector('.modal .o_form_view')) {
                    throw new Error('Configuration must be a full page');
                }
                const checkbox = document.querySelector(
                    '.o_field_widget[name="auto_create_sheet"] input');
                checkbox.click();
                const save = await waitFor(() => document.querySelector(
                    '.o_form_button_save'));
                save.click();
                await waitFor(() => document.querySelector(
                    '.o_form_status_indicator_buttons.invisible'));
                checkbox.click();
                await waitFor(() => !document.querySelector(
                    '.o_form_status_indicator_buttons.invisible'));
                document.querySelector('.o_form_button_cancel').click();
                await waitFor(() => !document.querySelector(
                    '.o_field_widget[name="auto_create_sheet"] input').checked);
                tabs[1].click();
                await waitFor(() => document.querySelector(
                    '[name="enabled_seller_ids"]'));
                tabs[2].click();
                await waitFor(() => document.querySelector(
                    'button[name="action_open_bank_accounts"]'));
                tabs[3].click();
                await waitFor(() => document.querySelector(
                    '[name="collection_connector_id"]'));
                if (document.querySelector(
                    '[name="collection_mcp_trusted_seller_header"]')) {
                    throw new Error('Manager must not see the system header');
                }
                tabs[2].click();
                const banks = await waitFor(() => document.querySelector(
                    'button[name="action_open_bank_accounts"]'));
                banks.click();
                await waitFor(() => document.querySelector(
                    '.o_list_view .o_control_panel'));
                const config = await waitFor(() => document.querySelector(
                    '[data-menu-xmlid="collection.menu_collection_config"]'));
                config.click();
                await waitFor(() => document.querySelector('.o_notebook .nav-link'));
                document.querySelector('.o_notebook .nav-link').click();
                const savedCheckbox = await waitFor(() => document.querySelector(
                    '.o_field_widget[name="auto_create_sheet"] input'));
                if (savedCheckbox.checked) {
                    throw new Error('Saved setting did not survive reopening');
                }
                console.log('test successful');
            })();
            """,
            login=manager.login,
            timeout=60,
        )
        company.invalidate_recordset(["auto_create_sheet"])
        self.assertFalse(company.auto_create_sheet)
