/** @odoo-module **/

import {Component, onWillStart, useState} from "@odoo/owl";
import {
  LINE_MODEL,
  buildApproveVals,
  nextIndexAfterReload,
  rpcErrorMessage,
  sanitizeQueueItem,
} from "@collection/document_review/document_review_helpers.esm";
import {_t} from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";
import {standardActionServiceProps} from "@web/webclient/actions/action_service";
import {useService} from "@web/core/utils/hooks";

export class DocumentReviewAction extends Component {
  static template = "collection.DocumentReviewAction";
  static props = {...standardActionServiceProps};

  setup() {
    this.orm = useService("orm");
    this.notification = useService("notification");
    this.state = useState({
      items: [],
      index: 0,
      loading: true,
      busy: false,
    });
    onWillStart(() => this.loadQueue());
  }

  get current() {
    return this.state.items[this.state.index] || null;
  }

  get hasQueue() {
    return this.state.items.length > 0;
  }

  get canPrev() {
    return this.state.index > 0;
  }

  get canNext() {
    return this.state.index < this.state.items.length - 1;
  }

  get isBankTransfer() {
    return Boolean(this.current && this.current.document_type === "bank_transfer");
  }

  get isCheck() {
    return Boolean(this.current && this.current.document_type === "check");
  }

  async loadQueue({keepIndex = false} = {}) {
    const previousIndex = this.state.index;
    this.state.loading = true;
    try {
      const queue = await this.orm.call(LINE_MODEL, "get_review_queue", []);
      this.state.items = (queue || []).map(sanitizeQueueItem);
      this.state.index = keepIndex
        ? nextIndexAfterReload(previousIndex, this.state.items.length)
        : 0;
    } catch (error) {
      this.notifyError(error);
      this.state.items = [];
      this.state.index = 0;
    } finally {
      this.state.loading = false;
    }
  }

  goPrev() {
    if (this.canPrev) {
      this.state.index -= 1;
    }
  }

  goNext() {
    if (this.canNext) {
      this.state.index += 1;
    }
  }

  onFieldInput(fieldName, ev) {
    const current = this.current;
    if (!current) {
      return;
    }
    current[fieldName] = ev.target.value;
  }

  async approve() {
    await this.runDecision(
      () =>
        this.orm.call(LINE_MODEL, "action_review_approve", [
          [this.current.id],
          buildApproveVals(this.current),
        ]),
      _t("Payment line approved.")
    );
  }

  async reject() {
    await this.runDecision(
      () => this.orm.call(LINE_MODEL, "action_review_reject", [[this.current.id]]),
      _t("Payment line rejected.")
    );
  }

  async runDecision(rpcCall, successMessage) {
    if (!this.current || this.state.busy) {
      return;
    }
    this.state.busy = true;
    try {
      await rpcCall();
      this.notification.add(successMessage, {type: "success"});
    } catch (error) {
      this.notifyError(error);
    }
    try {
      await this.loadQueue({keepIndex: true});
    } finally {
      this.state.busy = false;
    }
  }

  notifyError(error) {
    this.notification.add(rpcErrorMessage(error), {type: "danger"});
  }
}

registry.category("actions").add("collection.document_review", DocumentReviewAction);
