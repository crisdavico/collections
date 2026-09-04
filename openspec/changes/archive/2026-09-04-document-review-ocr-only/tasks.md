# Tasks: Document Review OCR-only

## Review Workload Forecast

| Field                   | Value                                              |
| ----------------------- | -------------------------------------------------- |
| Estimated changed lines | 480–720                                            |
| 400-line budget risk    | High                                               |
| Chained PRs recommended | Yes                                                |
| Suggested split         | PR 1 = phases 1–3 after OWL GREEN → PR 2 = phase 4 |
| Delivery strategy       | ask-on-risk                                        |
| Chain strategy          | stacked-to-main                                    |

Decision needed before apply: Yes Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

### Suggested Work Units

| Unit | Goal                                                          | Likely PR   | Focused test command                                  | Runtime harness                                         | Rollback boundary                                                            |
| ---- | ------------------------------------------------------------- | ----------- | ----------------------------------------------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------- |
| 1    | RED `tests/test_collection_document_review.py`                | PR 1 (hold) | `invoke test -m collection --mode=update` (must fail) | N/A — RED-only                                          | that test file only                                                          |
| 2    | GREEN `models/collection_voucher.py` payload + ignore approve | PR 1        | same; payload/approve pass                            | `-u collection`; approve on open-sheet eligible voucher | voucher.py map/helpers; delete `_editable_review_vals`                       |
| 3    | GREEN `static/src/document_review/*`                          | PR 1        | same; OWL source tests pass                           | `-u collection`; open Document Review                   | xml/js/helpers/scss                                                          |
| 4    | Manifest + AGENTS + verify                                    | PR 2        | same + scoped pre-commit                              | `-u collection` (assets)                                | `__manifest__.py`, `tests/test_collection_company_migration.py`, `AGENTS.md` |

Do not edit receipts, form views, `tests/test_collection_ui.py`, or leftover
`openspec/changes/collection-receipts/`. Threat matrix N/A.

## Phase 1: RED tests (`tests/test_collection_document_review.py` only)

- [x] 1.1 Fail `get_review_queue`: `seller_changed_fields` omits empty-empty; emptied
      seller key is `False`/`0.0`; typed Char/Date/Selection/Monetary diffs; keys follow
      `_REVIEW_EDITABLE_FIELD_ORDER`.
- [x] 1.2 Rewrite `test_approve_persists_*`, `test_reviewer_correction_*`,
      stale-approve: empty/omit/nonempty `vals` leave current unchanged; snapshot
      `approved` matches current. Keep empty-vals snapshot test.
- [x] 1.3 Rewrite OWL source tests: one readonly `ocr_*`; no seller/current widgets,
      `t-on-*`/`onFieldInput`, or `buildApproveVals`; `_layerHasDocumentType` OCR∪seller
      only; `.seller-warning` `role="status"`; dual bank/check groups; no `document_id`.
      Approve RPC `[[id], sheetId]`.
- [x] 1.4 `invoke test -m collection --mode=update` — RED. No `models/` or `static/`
      yet.

## Phase 2: GREEN server (`models/collection_voucher.py`)

- [x] 2.1 Add `_REVIEW_EDITABLE_FIELD_ORDER` plus empty/eq helpers (`float_compare` 2dp;
      `fields.Date.to_date`; Char/Selection exact).
- [x] 2.2 `_review_queue_payload` adds `seller_changed_fields` (ocr vs seller; both
      empty omit; else seller raw). Keep current/`ocr_*`/`seller_*`.
- [x] 2.3 Ignore approve `vals`; `_write_review_decision()` with no extra; delete
      `_editable_review_vals`. Keep `action_review_approve(..., vals=None)`.
- [x] 2.4 Payload + approve tests GREEN; OWL tests still RED.

## Phase 3: GREEN OWL (`static/src/document_review/`)

- [x] 3.1 `document_review_action.xml`: one readonly `ocr_*`; drop
      seller/current/`t-on-*`;
      `<p class="seller-warning" role="status" aria-live="polite">`; dual groups
      OCR∪seller type.
- [x] 3.2 `document_review_action.esm.js`: type getters OCR∪seller; drop `onFieldInput`;
      `orm.call(..., [[id], sheetId])`.
- [x] 3.3 `document_review_helpers.esm.js`: drop `buildApproveVals`; map lookup + format
      (Spanish/ISO/2dp/blank).
- [x] 3.4 `document_review_action.scss`: `.seller-warning` `--rose` (not `.btn.no`). OWL
      source tests GREEN.

## Phase 4: Version / docs / verify

- [x] 4.1 Bump `__manifest__.py` from CURRENT at apply (likely `19.0.1.36.0`; do not
      clobber receipts). No `migrations/`.
- [x] 4.2 Match `tests/test_collection_company_migration.py` version asserts.
      `AGENTS.md`: version + Document Review OCR-only/warnings/no-rewrite only.
- [x] 4.3 Scoped `pre-commit run --files` on touched collection paths.
      `invoke test -m collection --mode=update`.
