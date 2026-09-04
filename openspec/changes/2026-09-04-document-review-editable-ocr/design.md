# Design: Document Review editable OCR prefill

## Technical Approach

Keep stored `ocr_*` / `seller_*` / current. OWL holds a per-item `draft` initialized
from OCR with current fallback. Approve sends current keys only. Server filters through
`_REVIEW_EDITABLE_FIELDS`, writes current after the review lock, then snapshots.

## Architecture Decisions

| Decision        | Options                         | Tradeoff                          | Choice                                                                |
| --------------- | ------------------------------- | --------------------------------- | --------------------------------------------------------------------- |
| Prefill         | OCR-only; current-only; OCR→cur | Empty OCR blanks the form         | **OCR when non-empty, else current** (amount `0.0` is empty)          |
| Type groups     | OCR ∪ seller; draft type        | Dual groups fight single-field UX | **`draft.document_type`**                                             |
| Seller warnings | Keep; drop                      | Second value on screen            | **Drop** from OWL; keep queue `seller_changed_fields`                 |
| Approve vals    | Ignore; apply whitelist         | Ignore drops reviewer edits       | **`_editable_review_vals`** then write, then `_write_review_decision` |
| Version         | Migrate folder                  | No stored fields                  | **`19.0.1.38.0`**, no `migrations/`                                   |

## Data Flow

```
OWL loadQueue ──orm──► get_review_queue
                         └─ payload (current + ocr_* + seller_*)
OWL initDraftFromOcr (ocr else current)
OWL approve ──orm──► action_review_approve([[id], sheetId, vals])
                         ├─ lock / eligible
                         ├─ write current whitelist
                         └─ _write_review_decision → snapshot current
```

## File Changes

| File                                                        | Action | Description                                       |
| ----------------------------------------------------------- | ------ | ------------------------------------------------- |
| `models/collection_voucher.py`                              | Modify | Restore `_editable_review_vals`; apply on approve |
| `static/src/document_review/document_review_helpers.esm.js` | Modify | `initDraftFromOcr`, `buildApproveVals`            |
| `static/src/document_review/document_review_action.esm.js`  | Modify | Draft state, `onFieldInput`, approve with vals    |
| `static/src/document_review/document_review_action.xml`     | Modify | One editable control; drop warnings               |
| `static/src/document_review/document_review_action.scss`    | Modify | Drop `.seller-warning`                            |
| `tests/test_collection_document_review.py`                  | Modify | Persist + OWL contract                            |
| `tests/test_collection_acl.py`                              | Modify | Internal approve persists amount                  |
| `__manifest__.py`, `AGENTS.md`, migration tests             | Modify | `19.0.1.38.0`                                     |

## Interfaces / Contracts

```python
action_review_approve(self, sheet_id=None, vals=None)
# vals keys kept: _REVIEW_EDITABLE_FIELDS only
# omitted / {} → no current rewrite
```

```javascript
initDraftFromOcr(item); // {document_type, amount, ...}
buildApproveVals(draft); // current keys only
```
