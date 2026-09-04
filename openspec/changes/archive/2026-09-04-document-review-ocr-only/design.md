# Design: Document Review OCR-only

## Technical Approach

Keep stored `ocr_*` / `seller_*` / current. Diff those copies on `_review_queue_payload`
into `seller_changed_fields`. OWL: one readonly `ocr_*` plus inline warning. Approve
ignores client `vals` and snapshots current. Form three-way unchanged. Delta:
`specs/document-review/spec.md`.

## Architecture Decisions

| Decision                      | Options                                                | Tradeoff                                                                                               | Choice                                                                                                                                                                                                                          |
| ----------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `seller_changed_fields` shape | Name list; `{name, seller_value}[]`; dict              | Names omit seller value; object list is clumsy in QWeb; frozenset order is unstable                    | **JSON object** name → seller value. Iterate `_REVIEW_EDITABLE_FIELD_ORDER` tuple (keep frozenset for membership). Unchanged omitted. Empty `{}`                                                                                |
| JSON types                    | `""` vs `false`; date str vs `date`                    | Match `seller_*` (`amount` `0.0`, else `False`). `sanitizeQueueItem` is shallow — nested `false` stays | Emptied Char/Date/Selection: **`false`**. Monetary empty/zero: **`0.0`**. Set Date: `datetime.date` (RPC ISO). Set Selection: key. Set Char: str. Set Monetary: float                                                           |
| Empty / equality              | Strip; `not value`; type-aware                         | `not 0.0` is true; dates ≠ strings                                                                     | Empty: amount `False`/`None`/`0.0`; else `False`/`None`/`""`. Then amount `float_compare` 2 digits; Date `fields.Date.to_date`; Char/Selection exact. Both empty omit; else **seller** raw (`False`/`0.0` if emptied). No strip |
| Dual typed groups             | OR current type; OCR ∪ seller                          | Current type shows groups with no provenance                                                           | `_layerHasDocumentType`: **ocr ∪ seller only**. Shared type/amount always shown                                                                                                                                                 |
| Warning UI                    | Seller column; tooltip; inline                         | Spec: inline seller value, emptied visible                                                             | After OCR, `t-if` on key. `<p class="seller-warning" role="status" aria-live="polite">`. Selection → existing Spanish labels; date ISO; amount 2dp; empty blank (node stays). `--rose`; not `.btn.no`                           |
| Approve vals                  | Refuse nonempty; apply `_editable_review_vals`; ignore | Refuse breaks old OWL; apply rewrites current                                                          | **Ignore `vals`** (omit/`{}`/leftover). `_write_review_decision()` with no extra. Delete `_editable_review_vals`. Client `orm.call(..., [[id], sheetId])`; drop `buildApproveVals` / `onFieldInput`                             |
| TDD                           | Hoot; source-string OWL                                | No Hoot suite                                                                                          | Failing tests first in `tests/test_collection_document_review.py`. OWL = file-string/xpath                                                                                                                                      |
| Version                       | Hardcode `19.0.1.36.0`; migrate                        | Receipts may take the number; no stored fields                                                         | Bump **at apply** to next unused. **No** `migrations/`                                                                                                                                                                          |

## Data Flow

```
OWL loadQueue ──orm──► get_review_queue
                         └─ _review_queue_payload
                            + seller_changed_fields (ocr vs seller)
OWL render: ocr_* + warning(map)
OWL approve ──orm──► action_review_approve (vals ignored)
                         └─ _write_review_decision()
                            write state+audit ──► snapshot current
```

## File Changes

| File                                                        | Action | Description                                                                      |
| ----------------------------------------------------------- | ------ | -------------------------------------------------------------------------------- |
| `models/collection_voucher.py`                              | Modify | Order tuple; empty/eq helpers; payload map; ignore approve `vals`                |
| `static/src/document_review/document_review_action.xml`     | Modify | One readonly `ocr_*`; drop seller/current widgets and `t-on-input`; warning node |
| `static/src/document_review/document_review_action.esm.js`  | Modify | Type getters OCR∪seller; drop `onFieldInput`; approve without vals               |
| `static/src/document_review/document_review_helpers.esm.js` | Modify | Drop rewrite helpers; add map lookup + seller-value format                       |
| `static/src/document_review/document_review_action.scss`    | Modify | `.seller-warning` using `--rose`                                                 |
| `tests/test_collection_document_review.py`                  | Modify | RED then GREEN: map, OWL OCR-only, approve no rewrite                            |
| `__manifest__.py`                                           | Modify | Bump at apply only (dirty `19.0.1.35.0` → next unused)                           |

Do **not** edit the Payment Voucher form, `tests/test_collection_ui.py`, or receipts.

## Interfaces / Contracts

```python
# payload extra; keys in _REVIEW_EDITABLE_FIELD_ORDER
"seller_changed_fields": {"from_account": False, "amount": 80.0}  # or {}
```

Current / `ocr_*` / `seller_*` keys unchanged. `document_id` stays on payload, hidden in
OWL. Signature `action_review_approve(sheet_id, vals=None)` kept; `vals` unused. No new
routes; no `sudo()`.

## Testing Strategy

| Layer            | What                                                                                                                                                        | Approach             |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- |
| Unit (RED first) | Empty-empty omit; emptied seller → key + `False`/`0.0`; typed diffs; approve empty/omit/nonempty leaves current; snapshot `approved`                        | `TransactionCase`    |
| OWL (source)     | One `ocr_*`; no seller/current/`t-on-`; type getter omits `document_type`; `role="status"`; dual bank/check groups; no `document_id`; no `buildApproveVals` | `_action_js` / xpath |
| Integration      | `invoke test -m collection --mode=update`                                                                                                                   | Container Odoo       |
| E2E              | N/A                                                                                                                                                         | No Hoot              |

Rewrite: `test_approve_persists_*`, `test_reviewer_correction_*`, stale-approve amount
(stays pre-approve), `test_owl_keeps_type_visibility_*`, `test_build_approve_vals_*`.
Keep empty-vals snapshot test.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR, or process-integration boundary.

## Migration / Rollout

No stored fields; no migrate folder. `-u collection` for assets. Manifest bump at apply
from current. Model: payload + ignore vals. View: OWL only, not form XML. Sequence:
none. Security: ignore client vals.

## Open Questions

- None blocking. Exact manifest version is apply-time (likely `19.0.1.36.0`).
