/** @odoo-module **/

import {_t} from "@web/core/l10n/translation";

export const LINE_MODEL = "collection.voucher.line";
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

export function buildApproveVals(item) {
  const vals = {};
  for (const key of editableKeysForType(item.document_type)) {
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
