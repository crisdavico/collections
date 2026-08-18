/** @odoo-module **/

import {_t} from "@web/core/l10n/translation";

export const LINE_MODEL = "collection.voucher";
export const BINARY_KEYS = new Set(["datas", "attachment"]);

export const BANK_TRANSFER_FIELDS = [
  "from_account",
  "to_account",
  "voucher_number",
  "voucher_date",
];
export const CHECK_FIELDS = [
  "check_number",
  "check_bank",
  "check_type",
  "check_issue_date",
  "check_payment_date",
];
export const SHARED_EDITABLE_FIELDS = ["document_type", "amount"];

export function sanitizeQueueItem(raw) {
  const item = {};
  for (const [key, value] of Object.entries(raw || {})) {
    if (BINARY_KEYS.has(key)) {
      continue;
    }
    item[key] = value === false ? "" : value;
  }
  return item;
}

export function editableKeysForType(documentType) {
  if (documentType === "bank_transfer") {
    return SHARED_EDITABLE_FIELDS.concat(BANK_TRANSFER_FIELDS);
  }
  if (documentType === "check") {
    return SHARED_EDITABLE_FIELDS.concat(CHECK_FIELDS);
  }
  return SHARED_EDITABLE_FIELDS.slice();
}

export function ormValue(value) {
  if (value === "" || value === false) {
    return false;
  }
  return value;
}

export function isProvenanceKey(key) {
  return Boolean(key) && (key.startsWith("ocr_") || key.startsWith("seller_"));
}

export function buildApproveVals(item) {
  const vals = {};
  for (const key of editableKeysForType(item.document_type)) {
    if (isProvenanceKey(key)) {
      continue;
    }
    vals[key] = key === "amount" ? Number(item.amount) || 0 : ormValue(item[key]);
  }
  return vals;
}

export function nextIndexAfterReload(previousIndex, length) {
  if (length <= 0) {
    return 0;
  }
  return Math.min(previousIndex, length - 1);
}

export function rpcErrorMessage(error) {
  if (error && error.data && error.data.message) {
    return error.data.message;
  }
  if (error && error.message) {
    return error.message;
  }
  return _t("Could not complete the review action.");
}

export const IMAGE_EXTENSIONS = new Set([
  "png",
  "jpg",
  "jpeg",
  "gif",
  "webp",
  "bmp",
  "svg",
]);
export const PDF_MIME = "application/pdf";
export const PDF_EXTENSION = "pdf";

export function filenameExtension(filename) {
  const name = String(filename || "")
    .trim()
    .toLowerCase();
  const dot = name.lastIndexOf(".");
  if (dot < 0 || dot === name.length - 1) {
    return "";
  }
  return name.slice(dot + 1);
}

export function attachmentViewerKind(item) {
  if (!item) {
    return "empty";
  }
  const url = String(item.attachment_url || "").trim();
  const filename = String(item.attachment_filename || "").trim();
  if (!url || !filename) {
    return "empty";
  }
  const mime = String(item.mimetype || "").toLowerCase();
  const extension = filenameExtension(filename);
  if (mime === PDF_MIME || extension === PDF_EXTENSION) {
    return "pdf";
  }
  if (mime.startsWith("image/") || IMAGE_EXTENSIONS.has(extension)) {
    return "image";
  }
  return "image";
}

export function initialViewerStatus(kind) {
  return kind === "empty" ? "empty" : "loading";
}

export const VIEWER_ZOOM_MIN = 0.5;
export const VIEWER_ZOOM_MAX = 8;
export const VIEWER_ZOOM_FACTOR = 1.1;

export function identityViewerZoom() {
  return {scale: 1, x: 0, y: 0};
}

export function isViewerZoomIdentity(zoom) {
  return Boolean(zoom) && zoom.scale === 1 && zoom.x === 0 && zoom.y === 0;
}

export const VIEWER_ROTATION_STEP = 90;
export const VIEWER_ROTATIONS = new Set([0, 90, 180, 270]);

export function nextViewerRotation(degrees, step = VIEWER_ROTATION_STEP) {
  return ((((Number(degrees) || 0) + Number(step)) % 360) + 360) % 360;
}

export function storedViewerRotation(item) {
  const degrees = nextViewerRotation(item && item.attachment_rotation, 0);
  return VIEWER_ROTATIONS.has(degrees) ? degrees : 0;
}

export function clampViewerZoom(scale) {
  return Math.min(VIEWER_ZOOM_MAX, Math.max(VIEWER_ZOOM_MIN, scale));
}

export function applyWheelZoom(zoom, cursor, deltaY) {
  const factor = deltaY > 0 ? 1 / VIEWER_ZOOM_FACTOR : VIEWER_ZOOM_FACTOR;
  const nextScale = clampViewerZoom(zoom.scale * factor);
  if (nextScale === zoom.scale) {
    return {scale: zoom.scale, x: zoom.x, y: zoom.y};
  }
  const ratio = nextScale / zoom.scale;
  return {
    scale: nextScale,
    x: cursor.x - (cursor.x - zoom.x) * ratio,
    y: cursor.y - (cursor.y - zoom.y) * ratio,
  };
}

export function applyViewerPan(zoom, dx, dy) {
  return {
    scale: zoom.scale,
    x: zoom.x + (Number(dx) || 0),
    y: zoom.y + (Number(dy) || 0),
  };
}
