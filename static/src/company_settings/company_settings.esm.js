/** @odoo-module **/

import {formView} from "@web/views/form/form_view";
import {registry} from "@web/core/registry";

class CollectionSettingsModel extends formView.Model {
  static withCache = false;

  _getNextConfig() {
    const config = super._getNextConfig(...arguments);
    // Settings must reflect the company, including after returning from banks.
    config.resId = false;
    return config;
  }
}

class CollectionSettingsController extends formView.Controller {
  setup() {
    super.setup();
    this.canCreate = false;
  }

  displayName() {
    return this.archInfo.xmlDoc.getAttribute("string");
  }
}

registry.category("views").add("collection_company_settings", {
  ...formView,
  Controller: CollectionSettingsController,
  Model: CollectionSettingsModel,
});
