# Apply Progress: document-review-ocr-validation

**Change**: `document-review-ocr-validation`
**Mode**: Strict TDD
**Batch**: PR 1 / work unit 1 (model review workflow)
**Delivery**: stacked-to-main
**applyState at start**: ready

First apply batch — no prior `apply-progress` to merge.

## Completed Tasks

- [x] 1.1 RED `tests/test_collection_document_review.py`: queue eligibility + empty queue
- [x] 1.2 RED: default `pending`/audit; approve persists edits; reject; aggregate validate; line reject→voucher reject
- [x] 1.3 RED: stale/concurrent refuse; attachment write resets pending+clears audit; `action_validate` blocked while attached pending
- [x] 1.4 GREEN `models/collection_voucher_line.py`: fields + queue/approve/reject; attach write→pending
- [x] 1.5 GREEN `models/collection_voucher.py`: refuse `action_validate` if any attached line `pending`
- [x] 1.6 RED→GREEN extend `tests/test_collection_voucher.py` + `tests/test_collection_payment.py` for guard + reset
- [x] 1.7 REFACTOR private helpers; keep public queue/approve/reject contracts (no base64 in queue)

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `tests/test_collection_document_review.py` | Created | Queue, approve/reject, aggregate, races, empty, reset, validate guard |
| `tests/__init__.py` | Modified | Import `test_collection_document_review` |
| `models/collection_voucher_line.py` | Modified | Review fields; `get_review_queue` / `action_review_approve` / `action_review_reject`; attachment write resets pending; private helpers |
| `models/collection_voucher.py` | Modified | `action_validate` pending-attached guard; `_ensure_no_pending_attached_review` |
| `tests/test_collection_voucher.py` | Modified | Guard + unattached-does-not-block (existing no-line validate kept) |
| `tests/test_collection_payment.py` | Modified | Attachment replace resets approved/rejected review + clears audit |
| `openspec/changes/document-review-ocr-validation/tasks.md` | Modified | Phase 1 `[x]`; Phase 2–4 left unchecked |
| `openspec/changes/document-review-ocr-validation/apply-progress.md` | Created | This artifact |

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_collection_document_review.py` | Unit (TransactionCase) | ✅ 29/29 voucher+payment | ✅ Written (`get_review_queue` missing) | ✅ 15/15 class pass | ✅ eligible + empty + PNG/PDF order | ✅ 1.7 helpers |
| 1.2 | `tests/test_collection_document_review.py` | Unit (TransactionCase) | ✅ same baseline | ✅ Written (fields/actions missing) | ✅ Passed | ✅ transfer edits + check fields; aggregate + line reject | ✅ `_write_review_decision` |
| 1.3 | `tests/test_collection_document_review.py` | Unit (TransactionCase) | ✅ same baseline | ✅ Written (1 FAIL validate guard + missing APIs) | ✅ Passed | ✅ stale decided + voucher-not-new/unattached; approved + rejected reset | ✅ `_lines_with_attachment` |
| 1.4 | `models/collection_voucher_line.py` | Unit | N/A (GREEN of 1.1–1.3) | ✅ Tests first | ✅ Passed | ✅ covered by 1.1–1.3 | ✅ private helpers |
| 1.5 | `models/collection_voucher.py` | Unit | ✅ `test_action_validate_from_new` kept | ✅ Tests first | ✅ Passed | ✅ attached pending blocks; unattached/no-lines allow | ✅ `_ensure_no_pending_attached_review` |
| 1.6 | `tests/test_collection_{voucher,payment}.py` | Unit (TransactionCase) | ✅ 29/29 then 15/15 | ✅ Written (behaviors already RED in 1.3) | ✅ 48/48 focused pass | ✅ voucher guard + unattached; approved + rejected reset | ➖ None needed in test files |
| 1.7 | `models/collection_voucher*.py` | Unit | ✅ 48/48 before refactor | N/A (refactor) | ✅ 48/48 after refactor | ➖ Structural | ✅ Extracted private helpers; public contracts unchanged |

### Test Summary

- **Total tests written this batch**: 19 (15 in `TestCollectionDocumentReview` + 2 voucher + 2 payment)
- **Total tests passing**: 94 collection tests, 0 failed, 0 errors (full `/collection`)
- **Layers used**: Unit/integration via Odoo `TransactionCase` (19), E2E (0)
- **Approval tests** (refactoring): existing `test_action_validate_from_new` (no-line voucher) still passes
- **Pure functions created**: 0 (recordset helpers; ORM I/O)

### Safety Net (before production model edits)

```
docker exec -i seedian-odoo-1 odoo -d devel -u collection --test-enable --stop-after-init --workers=0 --http-port=18069 --test-tags /collection:TestCollectionVoucher,/collection:TestCollectionPaymentDocumentId,/collection:TestCollectionPaymentAttachment
```

Result: exit 0; `0 failed, 0 error(s) of 29 tests`.

### RED gate (1.1–1.3, tests only)

```
docker exec -i seedian-odoo-1 odoo -d devel -u collection --test-enable --stop-after-init --workers=0 --http-port=18069 --test-tags /collection:TestCollectionDocumentReview
```

Result: exit 1; `1 failed, 13 error(s) of 15 tests` — missing `get_review_queue` / `action_review_*` / `review_status`; `test_action_validate_blocked_while_attached_pending` failed because validate still succeeded.

### GREEN gate (after 1.4–1.5)

Same focused command: exit 0; `0 failed, 0 error(s) of 15 tests`.

### After 1.6 + 1.7

Focused (review + voucher + payment): exit 0; `0 failed, 0 error(s) of 48 tests`.

## Work Unit Evidence

| Evidence | Value |
|----------|-------|
| Focused test command and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --test-enable --stop-after-init --workers=0 --http-port=18069 --test-tags /collection:TestCollectionDocumentReview,/collection:TestCollectionVoucher,/collection:TestCollectionPaymentDocumentId,/collection:TestCollectionPaymentAttachment` → exit 0; **0 failed, 0 error(s) of 48 tests**. Full module: `--test-tags /collection` → exit 0; **0 failed, 0 error(s) of 94 tests**. (`--http-port=18069` because 8069 is held by the running odoo process.) |
| Runtime harness command/scenario and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --http-port=18069` → exit 0; `Module collection loaded`; `Modules loaded.`; `Registry loaded`. Additive `review_status` default `pending` applied without `migrations/`. |
| Rollback boundary | `models/collection_voucher.py`, `models/collection_voucher_line.py`, `tests/test_collection_document_review.py`, `tests/__init__.py`, voucher/payment test extensions, `openspec/changes/document-review-ocr-validation/tasks.md`, `openspec/changes/document-review-ocr-validation/apply-progress.md`. Revert those files and upgrade `collection`. Does not include OWL/static, document-review views, ACL tests, or `__manifest__.py` version. |

## Public contracts (this slice)

- `collection.voucher.line.get_review_queue()` — ordered payloads; content URL; no `datas`/base64
- `collection.voucher.line.action_review_approve(vals=None)` — eligible only; editable fields; not `document_id`; audit; aggregate `action_validate` when all attached siblings approved
- `collection.voucher.line.action_review_reject()` — eligible only; audit; `action_reject` on voucher
- Attachment Binary write → `pending` + clear audit
- `collection.voucher.action_validate()` — `UserError` if any attached line is `pending`

## Deviations from Design

None — implementation matches design.

## Issues Found

- `docker exec` of a second `odoo` on the live `seedian-odoo-1` container requires `--http-port` other than 8069 (`Address already in use`). Focused and full tests used `--http-port=18069`.
- `invoke test -m collection` uses `docker compose run` and was not used, per apply instructions when the stack is already up.

## Remaining Tasks

- [ ] Phase 2 (PR 2): OWL ORM client
- [ ] Phase 3 (PR 3): binary viewer
- [ ] Phase 4: ACL + manifest bump + full pre-commit

## Workload / PR Boundary

- Mode: stacked PR slice (`stacked-to-main`)
- Current work unit: PR 1 / model review workflow
- Boundary: starts at review fields/queue/approve/reject/validate guard; ends before OWL/JS/XML/SCSS, ACL tests, and manifest version bump
- Estimated review budget impact: model + tests only; OWL prototype files left untouched
