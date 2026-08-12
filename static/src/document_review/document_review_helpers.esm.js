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
