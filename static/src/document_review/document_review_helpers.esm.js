/** @odoo-module **/

import {_t} from "@web/core/l10n/translation";

export const LINE_MODEL = "collection.voucher";
export const BINARY_KEYS = new Set(["datas", "attachment"]);
export const REVIEW_EDITABLE_FIELDS = [
  "document_type",
  "amount",
  "from_account",
  "to_account",
  "voucher_number",
  "voucher_date",
  "check_number",
  "check_bank",
  "check_type",
  "check_issue_date",
  "check_payment_date",
  "retention_kind",
];

export const DOCUMENT_TYPE_LABELS = {
  bank_transfer: "Transferencia bancaria",
  check: "Cheque",
  cash_deposit: "Depósito en efectivo",
  seller_deposit: "Depósito del vendedor",
};
export const CHECK_TYPE_LABELS = {
  common: "Común",
  deferred: "Diferido",
};
export const SELLER_CHANGED_SELECTION_LABELS = {
  document_type: DOCUMENT_TYPE_LABELS,
  check_type: CHECK_TYPE_LABELS,
};
export const SELLER_CHANGED_DATE_FIELDS = new Set([
  "voucher_date",
  "check_issue_date",
  "check_payment_date",
]);

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

export function isEmptyReviewValue(name, value) {
  if (value === false || value === null || value === undefined || value === "") {
    return true;
  }
  if (name === "amount") {
    const number = Number(value);
    return Number.isNaN(number) || number === 0;
  }
  return false;
}

/**
 * Parse an amount typed with "." as thousands and "," as decimal separator.
 * Without a comma, a single dot followed by 1-2 digits is read as decimal.
 * Returns null when the text is not a number.
 */
export function parseReviewAmount(value) {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }
  const text = String(value ?? "").replace(/\s/g, "");
  if (!text) {
    return null;
  }
  let normalized = text;
  if (text.includes(",")) {
    normalized = text.replace(/\./g, "").replace(",", ".");
  } else if (!/^-?\d+\.\d{1,2}$/.test(text)) {
    normalized = text.replace(/\./g, "");
  }
  if (!/^-?\d+(\.\d+)?$/.test(normalized)) {
    return null;
  }
  return Number(normalized);
}

/** Format an amount as 1.234.567,89. Unparseable text is returned unchanged. */
export function formatReviewAmount(value) {
  if (value === false || value === null || value === undefined || value === "") {
    return "";
  }
  const number = parseReviewAmount(value);
  if (number === null) {
    return String(value);
  }
  const fixed = Math.abs(number).toFixed(2);
  const [integer, decimals] = fixed.split(".");
  const grouped = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const sign = number < 0 && Number(fixed) !== 0 ? "-" : "";
  return `${sign}${grouped},${decimals}`;
}

export function initDraftFromOcr(item) {
  const source = item || {};
  const draft = {};
  for (const name of REVIEW_EDITABLE_FIELDS) {
    const ocrValue = source[`ocr_${name}`];
    draft[name] = isEmptyReviewValue(name, ocrValue) ? source[name] ?? "" : ocrValue;
  }
  draft.amount = formatReviewAmount(draft.amount);
  return draft;
}

export function buildApproveVals(draft) {
  const vals = {};
  const source = draft || {};
  for (const name of REVIEW_EDITABLE_FIELDS) {
    if (!Object.prototype.hasOwnProperty.call(source, name)) {
      continue;
    }
    vals[name] = source[name];
  }
  if (Object.prototype.hasOwnProperty.call(vals, "amount")) {
    vals.amount = parseReviewAmount(vals.amount) ?? "";
  }
  return vals;
}

export function hasSellerChangedField(changedFields, fieldName) {
  return Boolean(
    changedFields && Object.prototype.hasOwnProperty.call(changedFields, fieldName)
  );
}

export function sellerChangedFieldValue(changedFields, fieldName) {
  if (!hasSellerChangedField(changedFields, fieldName)) {
    return undefined;
  }
  return changedFields[fieldName];
}

function isBlankSellerChangedValue(value) {
  return value === false || value === null || value === undefined || value === "";
}

function formatIsoDate(value) {
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    return value.toISOString().slice(0, 10);
  }
  const text = String(value).trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(text)) {
    return text.slice(0, 10);
  }
  return text;
}

export function formatSellerChangedValue(changedFields, fieldName) {
  if (!hasSellerChangedField(changedFields, fieldName)) {
    return "";
  }
  const value = changedFields[fieldName];
  if (isBlankSellerChangedValue(value)) {
    return "";
  }
  if (fieldName === "amount") {
    return formatReviewAmount(value);
  }
  if (SELLER_CHANGED_DATE_FIELDS.has(fieldName)) {
    return formatIsoDate(value);
  }
  const labels = SELLER_CHANGED_SELECTION_LABELS[fieldName];
  if (labels && Object.prototype.hasOwnProperty.call(labels, value)) {
    return labels[value];
  }
  return String(value);
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
  // The server only designates image/* or application/pdf proof, so anything
  // that is not a PDF is rendered by the image viewer.
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
