Closed plan used instead of a question round.

# Proposal: Document Review OCR-only

## Intent

OWL Document Review edits current fields; **Aprobar y seguir** rewrites them before
snapshot. Review should show OCR, warn on seller diffs, and leave current unchanged.
Form three-way stays.

## Scope

### In Scope

- `seller_changed_fields` on `_review_queue_payload` (`ocr_*` vs `seller_*`)
- OWL: one readonly `ocr_*` per field; inline seller-value warning; dual typed groups
  (OCR ∪ seller type)
- Approve ignores client vals; current authoritative; snapshot copies current
- Rewrite `tests/test_collection_document_review.py`; delta `document-review`
- Manifest bump at apply (dirty `19.0.1.35.0`; next unused)

### Out of Scope

- Form (`views/collection_views.xml`, `tests/test_collection_ui.py`)
- Stored fields / migration; Nebula (overrides config rule); receipts
- `collection-vouchers` (no Review approve-rewrite requirement)

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `document-review`: split OWL vs form. OWL: OCR-only + seller-change warnings; Approve
  MUST NOT rewrite current. Keep form three-way. Queue MUST include
  `seller_changed_fields`. Empty-empty → no warning.

## Approach

Exploration 1. Diff `_REVIEW_EDITABLE_FIELDS` (`ocr_{name}` vs `seller_{name}`). Empty =
False / None / `""` / monetary `0.0`. Both empty → omit; else seller value (False if
emptied). OWL: OCR + warning map. `_layerHasDocumentType` = OCR ∪ seller. Approve:
client `{}`/omit; server ignore `_editable_review_vals`. Snapshot after state write. No
migration.

## Affected Areas

| Area                                       | Impact   | Description                   |
| ------------------------------------------ | -------- | ----------------------------- |
| `models/collection_voucher.py`             | Modified | Diff map; ignore approve vals |
| `static/src/document_review/*`             | Modified | OCR-only OWL; warning SCSS    |
| `tests/test_collection_document_review.py` | Modified | TDD: payload, OWL, no rewrite |
| `openspec/specs/document-review/spec.md`   | Modified | Delta in this change          |
| `__manifest__.py`                          | Modified | Bump at apply only            |

## Risks

| Risk                            | Likelihood | Mitigation                  |
| ------------------------------- | ---------- | --------------------------- |
| Review tests require rewrite    | High       | Same-change TDD rewrite     |
| Parallel-agent dirty form tests | Med        | Do not edit form / UI tests |
| `0.0` vs genuine zero           | Med        | Empty-provenance convention |
| Manifest collision              | Med        | Bump from current at apply  |
| 400-line review budget          | Med        | `sdd-tasks` forecast        |

## Rollback Plan

Revert OWL, helpers, payload, approve ignore, review tests, spec delta, manifest.
Restore three-way edits and `buildApproveVals`. No DB reverse. Form unchanged.

## Dependencies

- Existing `ocr_*`/`seller_*` copies and empty-vals snapshot path
- `-u collection` after ship (assets)

## Success Criteria

- [ ] Readonly OCR only; seller diffs warned inline (empty shown empty)
- [ ] Empty legacy provenance: no warning
- [ ] Type change shows OCR-type and seller-type groups
- [ ] Approve does not rewrite current; snapshot matches current
- [ ] Form three-way unchanged
- [ ] `invoke test -m collection --mode=update` passes Document Review tests
