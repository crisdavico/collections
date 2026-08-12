/** @odoo-module **/

import {Component, onWillStart, onWillUnmount, useState} from "@odoo/owl";
import {
  LINE_MODEL,
  applyViewerPan,
  applyWheelZoom,
  attachmentViewerKind,
  buildApproveVals,
  identityViewerZoom,
  initialViewerStatus,
  isViewerZoomIdentity,
  nextIndexAfterReload,
  nextViewerRotation,
  rpcErrorMessage,
  sanitizeQueueItem,
  storedViewerRotation,
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
      viewerStatus: "empty",
      viewerFit: false,
      viewerZoom: identityViewerZoom(),
      viewerRotation: 0,
      viewerPanning: false,
    });
    this.viewerPanPointer = null;
    onWillStart(() => this.loadQueue());
    onWillUnmount(() => this.stopViewerPan());
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

  get viewerKind() {
    return attachmentViewerKind(this.current);
  }

  get viewerIsEmpty() {
    return this.viewerKind === "empty";
  }

  get viewerIsImage() {
    return this.viewerKind === "image";
  }

  get viewerIsPdf() {
    return this.viewerKind === "pdf";
  }

  get viewerIsReady() {
    return this.state.viewerStatus === "ready";
  }

  get pdfFitFragment() {
    return this.state.viewerFit ? "#view=Fit" : "";
  }

  get viewerZoomStyle() {
    const {scale, x, y} = this.state.viewerZoom;
    return `transform: translate(${x}px, ${y}px) scale(${scale}); transform-origin: 0 0;`;
  }

  get viewerRotateStyle() {
    return `transform: rotate(${this.state.viewerRotation}deg);`;
  }

  get viewerRotateIsOdd() {
    return this.state.viewerRotation % 180 !== 0;
  }

  get viewerCanPan() {
    return this.viewerIsReady && !isViewerZoomIdentity(this.state.viewerZoom);
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
      this.syncViewer();
    }
  }

  goPrev() {
    if (this.canPrev) {
      this.state.index -= 1;
      this.syncViewer();
    }
  }

  goNext() {
    if (this.canNext) {
      this.state.index += 1;
      this.syncViewer();
    }
  }

  syncViewer() {
    this.resetViewerTransform();
    this.state.viewerStatus = initialViewerStatus(this.viewerKind);
  }

  resetViewerTransform() {
    this.stopViewerPan();
    this.state.viewerFit = false;
    this.state.viewerZoom = identityViewerZoom();
    this.state.viewerRotation = storedViewerRotation(this.current);
  }

  fitViewer() {
    if (!this.viewerIsReady) {
      return;
    }
    this.state.viewerFit = true;
    this.state.viewerZoom = identityViewerZoom();
  }

  rotateViewerLeft() {
    this.rotateViewer(-90);
  }

  rotateViewerRight() {
    this.rotateViewer(90);
  }

  async rotateViewer(step) {
    if (!this.viewerIsReady || !this.current) {
      return;
    }
    const next = nextViewerRotation(this.state.viewerRotation, step);
    this.state.viewerRotation = next;
    this.current.attachment_rotation = next;
    try {
      await this.orm.call(LINE_MODEL, "action_review_set_rotation", [
        [this.current.id],
        next,
      ]);
    } catch (error) {
      this.notifyError(error);
    }
  }

  onViewerWheel(ev) {
    if (!this.viewerIsReady) {
      return;
    }
    const rect = ev.currentTarget.getBoundingClientRect();
    const next = applyWheelZoom(
      this.state.viewerZoom,
      {x: ev.clientX - rect.left, y: ev.clientY - rect.top},
      ev.deltaY
    );
    this.state.viewerZoom.scale = next.scale;
    this.state.viewerZoom.x = next.x;
    this.state.viewerZoom.y = next.y;
  }

  onViewerPointerDown(ev) {
    if (!this.viewerCanPan || ev.button !== 0) {
      return;
    }
    this.viewerPanPointer = {id: ev.pointerId, x: ev.clientX, y: ev.clientY};
    this.state.viewerPanning = true;
    if (typeof ev.currentTarget.setPointerCapture === "function") {
      ev.currentTarget.setPointerCapture(ev.pointerId);
    }
    ev.preventDefault();
  }

  onViewerPointerMove(ev) {
    if (!this.state.viewerPanning || !this.viewerPanPointer) {
      return;
    }
    if (this.viewerPanPointer.id !== ev.pointerId) {
      return;
    }
    const next = applyViewerPan(
      this.state.viewerZoom,
      ev.clientX - this.viewerPanPointer.x,
      ev.clientY - this.viewerPanPointer.y
    );
    this.viewerPanPointer.x = ev.clientX;
    this.viewerPanPointer.y = ev.clientY;
    this.state.viewerZoom.x = next.x;
    this.state.viewerZoom.y = next.y;
  }

  onViewerPointerUp(ev) {
    if (this.viewerPanPointer && this.viewerPanPointer.id !== ev.pointerId) {
      return;
    }
    this.stopViewerPan(ev.currentTarget, ev.pointerId);
  }

  stopViewerPan(target, pointerId) {
    const captureId =
      pointerId === undefined
        ? this.viewerPanPointer && this.viewerPanPointer.id
        : pointerId;
    this.viewerPanPointer = null;
    this.state.viewerPanning = false;
    if (
      target &&
      captureId !== undefined &&
      typeof target.hasPointerCapture === "function" &&
      target.hasPointerCapture(captureId) &&
      typeof target.releasePointerCapture === "function"
    ) {
      target.releasePointerCapture(captureId);
    }
  }

  onViewerLoad() {
    if (this.state.viewerStatus === "loading") {
      this.state.viewerStatus = "ready";
    }
  }

  onViewerError() {
    this.state.viewerStatus = "error";
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
      _t("Payment voucher approved.")
    );
  }

  async reject() {
    await this.runDecision(
      () => this.orm.call(LINE_MODEL, "action_review_reject", [[this.current.id]]),
      _t("Payment voucher rejected.")
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
