# Apply Progress: document-review-ocr-validation

**Change**: `document-review-ocr-validation` **Mode**: Strict TDD **Batch**: PR 4 / work
unit 4 (ACL + final verification) — merged with PR 1 + PR 2 + PR 3 **Delivery**:
stacked-to-main **applyState at start**: ready

Merged: Phase 1 (PR 1 / model review workflow) + Phase 2 (PR 2 / OWL ORM client) + Phase
3 (PR 3 / authenticated binary viewer) + Phase 4 (PR 4 / ACL + upgrade + full tests +
scoped pre-commit).

## Completed Tasks

- [x] 1.1 RED `tests/test_collection_document_review.py`: queue eligibility + empty
      queue
- [x] 1.2 RED: default `pending`/audit; approve persists edits; reject; aggregate
      validate; line reject→voucher reject
- [x] 1.3 RED: stale/concurrent refuse; attachment write resets pending+clears audit;
      `action_validate` blocked while attached pending
- [x] 1.4 GREEN `models/collection_voucher_line.py`: fields + queue/approve/reject;
      attach write→pending
- [x] 1.5 GREEN `models/collection_voucher.py`: refuse `action_validate` if any attached
      line `pending`
- [x] 1.6 RED→GREEN extend `tests/test_collection_voucher.py` +
      `tests/test_collection_payment.py` for guard + reset
- [x] 1.7 REFACTOR private helpers; keep public queue/approve/reject contracts (no
      base64 in queue)
- [x] 2.1 RED extend `tests/test_collection_ui.py`: menu/action/tag
      `collection.document_review` survive
- [x] 2.2 GREEN `static/src/document_review/document_review_action.esm.js` + `.xml`: ORM
      queue; typed editors by `document_type`; readonly `document_id`/voucher/position;
      nav + next after decision; empty state; drop mocks/stamps/notes
- [x] 2.3 GREEN wire approve/reject RPCs + notifications; reload queue on `UserError`
- [x] 2.4 REFACTOR thin OWL; never put attachment datas/base64 in component state
- [x] 3.1 RED assert queue payload content URL only (no `datas`/base64) in
      `tests/test_collection_document_review.py`
- [x] 3.2 GREEN `/web/content` image vs PDF viewer + loading/error/empty in
      `document_review_action.*` (+scss)
- [x] 3.3 REFACTOR MIME/filename branching only
- [x] 4.1 RED→GREEN `tests/test_collection_acl.py`: non-internal denied
      queue/approve/reject; internal OK
- [x] 4.2 Bump `__manifest__.py` `19.0.1.3.0` → `19.0.1.4.0`; upgrade `collection` on
      devel
- [x] 4.3 Full `/collection` tests; 0 failures
- [x] 4.4 Scoped pre-commit on Phase 4 collection paths

## Files Changed

### Phase 1 (PR 1)

| File                                       | Action   | What Was Done                                                                                                                          |
| ------------------------------------------ | -------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/test_collection_document_review.py` | Created  | Queue, approve/reject, aggregate, races, empty, reset, validate guard                                                                  |
| `tests/__init__.py`                        | Modified | Import `test_collection_document_review`                                                                                               |
| `models/collection_voucher_line.py`        | Modified | Review fields; `get_review_queue` / `action_review_approve` / `action_review_reject`; attachment write resets pending; private helpers |
| `models/collection_voucher.py`             | Modified | `action_validate` pending-attached guard; `_ensure_no_pending_attached_review`                                                         |
| `tests/test_collection_voucher.py`         | Modified | Guard + unattached-does-not-block (existing no-line validate kept)                                                                     |
| `tests/test_collection_payment.py`         | Modified | Attachment replace resets approved/rejected review + clears audit                                                                      |

### Phase 2 (PR 2)

| File                                                                | Action   | What Was Done                                                                                                            |
| ------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------ |
| `tests/test_collection_ui.py`                                       | Modified | Menu/action xmlid + tag + path assertions for Document Review                                                            |
| `__manifest__.py`                                                   | Modified | Added `views/collection_document_review_views.xml` to `data` and `web.assets_backend` glob; version left at `19.0.1.3.0` |
| `views/collection_document_review_views.xml`                        | Kept     | Menu/action/tag/path unchanged                                                                                           |
| `static/src/document_review/document_review_action.esm.js`          | Modified | ORM queue, typed editors, nav, approve/reject RPCs, notifications; dropped mocks                                         |
| `static/src/document_review/document_review_helpers.esm.js`         | Created  | Pure helpers: sanitize (no datas/base64), typed vals, next-index, RPC error text                                         |
| `static/src/document_review/document_review_action.xml`             | Modified | Typed editors, readonly context, empty/loading, placeholder viewer; dropped stamps/notes/fake SVG                        |
| `static/src/document_review/document_review_action.scss`            | Modified | Kept clay layout; trimmed stamp/note/fake-sheet styles; empty + placeholder                                              |
| `openspec/changes/document-review-ocr-validation/tasks.md`          | Modified | Phase 1–2 `[x]`; Phase 3–4 left unchecked                                                                                |
| `openspec/changes/document-review-ocr-validation/apply-progress.md` | Modified | Merged Phase 1 + Phase 2 evidence                                                                                        |

### Phase 3 (PR 3 / this batch)

| File                                                                | Action   | What Was Done                                                                                                                                |
| ------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/test_collection_document_review.py`                          | Modified | Strengthened `_assert_no_binary_in_payload`; exact PNG/JPG/PDF `/web/content` URLs; OWL img/iframe + loading/error/empty-attachment contract |
| `static/src/document_review/document_review_action.xml`             | Modified | Replaced placeholder with img + iframe bound to `current.attachment_url`; distinct loading/error/empty-attachment copy                       |
| `static/src/document_review/document_review_action.esm.js`          | Modified | Viewer status + load/error handlers; thin getters over helpers; never fetches binary into state                                              |
| `static/src/document_review/document_review_action.scss`            | Modified | Viewer image/PDF/loading/error/empty styles; dropped `.viewer-placeholder`                                                                   |
| `static/src/document_review/document_review_helpers.esm.js`         | Modified | Pure `attachmentViewerKind` / `filenameExtension` / `initialViewerStatus`; `sanitizeQueueItem` still strips `datas`/`attachment`             |
| `openspec/changes/document-review-ocr-validation/tasks.md`          | Modified | Phase 3 `[x]`; Phase 4 left unchecked                                                                                                        |
| `openspec/changes/document-review-ocr-validation/apply-progress.md` | Modified | Merged Phase 1 + 2 + 3 evidence                                                                                                              |

### Phase 4 (PR 4 / this batch)

| File                                                                | Action    | What Was Done                                                                                                 |
| ------------------------------------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------- |
| `tests/test_collection_acl.py`                                      | Modified  | Portal AccessError on queue/approve/reject/read; internal create+queue+approve; internal reject triangulation |
| `__manifest__.py`                                                   | Modified  | Version `19.0.1.3.0` → `19.0.1.4.0`                                                                           |
| `README.rst`                                                        | Modified  | Regenerated digest by `oca-gen-addon-readme` after version bump                                               |
| `static/description/index.html`                                     | Modified  | Regenerated digest by `oca-gen-addon-readme` after version bump                                               |
| `security/ir.model.access.csv`                                      | Unchanged | Existing `base.group_user` full CRUD already denies portal; no new groups or record rules                     |
| `openspec/changes/document-review-ocr-validation/tasks.md`          | Modified  | Phase 4 `[x]`                                                                                                 |
| `openspec/changes/document-review-ocr-validation/apply-progress.md` | Modified  | Merged Phase 1 + 2 + 3 + 4 evidence                                                                           |

## TDD Cycle Evidence

### Phase 1

| Task | Test File                                    | Layer                  | Safety Net                              | RED                                               | GREEN                   | TRIANGULATE                                                              | REFACTOR                                                 |
| ---- | -------------------------------------------- | ---------------------- | --------------------------------------- | ------------------------------------------------- | ----------------------- | ------------------------------------------------------------------------ | -------------------------------------------------------- |
| 1.1  | `tests/test_collection_document_review.py`   | Unit (TransactionCase) | ✅ 29/29 voucher+payment                | ✅ Written (`get_review_queue` missing)           | ✅ 15/15 class pass     | ✅ eligible + empty + PNG/PDF order                                      | ✅ 1.7 helpers                                           |
| 1.2  | `tests/test_collection_document_review.py`   | Unit (TransactionCase) | ✅ same baseline                        | ✅ Written (fields/actions missing)               | ✅ Passed               | ✅ transfer edits + check fields; aggregate + line reject                | ✅ `_write_review_decision`                              |
| 1.3  | `tests/test_collection_document_review.py`   | Unit (TransactionCase) | ✅ same baseline                        | ✅ Written (1 FAIL validate guard + missing APIs) | ✅ Passed               | ✅ stale decided + voucher-not-new/unattached; approved + rejected reset | ✅ `_lines_with_attachment`                              |
| 1.4  | `models/collection_voucher_line.py`          | Unit                   | N/A (GREEN of 1.1–1.3)                  | ✅ Tests first                                    | ✅ Passed               | ✅ covered by 1.1–1.3                                                    | ✅ private helpers                                       |
| 1.5  | `models/collection_voucher.py`               | Unit                   | ✅ `test_action_validate_from_new` kept | ✅ Tests first                                    | ✅ Passed               | ✅ attached pending blocks; unattached/no-lines allow                    | ✅ `_ensure_no_pending_attached_review`                  |
| 1.6  | `tests/test_collection_{voucher,payment}.py` | Unit (TransactionCase) | ✅ 29/29 then 15/15                     | ✅ Written (behaviors already RED in 1.3)         | ✅ 48/48 focused pass   | ✅ voucher guard + unattached; approved + rejected reset                 | ➖ None needed in test files                             |
| 1.7  | `models/collection_voucher*.py`              | Unit                   | ✅ 48/48 before refactor                | N/A (refactor)                                    | ✅ 48/48 after refactor | ➖ Structural                                                            | ✅ Extracted private helpers; public contracts unchanged |

### Phase 2

| Task | Test File                                                     | Layer                               | Safety Net                 | RED                                               | GREEN                                                                   | TRIANGULATE                                                | REFACTOR                                       |
| ---- | ------------------------------------------------------------- | ----------------------------------- | -------------------------- | ------------------------------------------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------- | ---------------------------------------------- |
| 2.1  | `tests/test_collection_ui.py`                                 | Unit (TransactionCase / UI arch)    | ✅ 32/32 Ui+DocumentReview | ✅ Written (xmlids missing from manifest)         | ✅ 34/34 focused pass                                                   | ✅ menu/parent/tag + client path/name (not act_window)     | ➖ Tests only                                  |
| 2.2  | `tests/test_collection_ui.py` + existing review payload tests | Unit (no OWL E2E)                   | ✅ 32/32                   | ✅ 2.1 xmlids first; views not in manifest        | ✅ Manifest + OWL queue/editors/nav/empty                               | ✅ bank/check/cash field sets in template; empty vs queued | ✅ 2.4 helpers module                          |
| 2.3  | same                                                          | Unit (RPC contract via model tests) | ✅ 15/15 DocumentReview    | ✅ Tests first (2.1); RPCs not wired in prototype | ✅ `orm.call` approve `[[id], vals]` / reject `[[id]]`; notify + reload | ✅ success notify vs UserError notify+reload               | ✅ `runDecision`                               |
| 2.4  | `document_review_helpers.esm.js`                              | Unit                                | ✅ 34/34 after GREEN       | N/A (refactor)                                    | ✅ 34/34 after extract; full `/collection` 96/96                        | ➖ Structural                                              | ✅ Pure helpers; no datas/base64 in `useState` |

### Phase 3

| Task | Test File                                  | Layer                                      | Safety Net                 | RED                                                          | GREEN                                              | TRIANGULATE                                                                                   | REFACTOR                                                                |
| ---- | ------------------------------------------ | ------------------------------------------ | -------------------------- | ------------------------------------------------------------ | -------------------------------------------------- | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| 3.1  | `tests/test_collection_document_review.py` | Unit (TransactionCase)                     | ✅ 34/34 Ui+DocumentReview | ✅ Written (placeholder still in XML; viewer states missing) | ✅ 4/4 new tests after 3.2                         | ✅ PNG + JPG image URLs; dedicated PDF URL; img vs iframe; loading/error/empty vs queue-empty | ✅ 3.3 helpers                                                          |
| 3.2  | `document_review_action.{esm.js,xml,scss}` | Unit (URL + template contract; no OWL E2E) | ✅ 34/34                   | ✅ Tests first (2 FAIL XML)                                  | ✅ 4/4 then 38/38 focused                          | ✅ image `<img>` + PDF `<iframe>` both bind `current.attachment_url`                          | ✅ 3.3                                                                  |
| 3.3  | `document_review_helpers.esm.js`           | Unit                                       | ✅ 38/38 before extract    | N/A (refactor)                                               | ✅ 38/38 after extract; full `/collection` 100/100 | ➖ Structural (MIME/filename already branched in GREEN)                                       | ✅ `attachmentViewerKind` + `filenameExtension` + `initialViewerStatus` |

### Phase 4

| Task | Test File                      | Layer                        | Safety Net                        | RED                                               | GREEN                                                                                    | TRIANGULATE                                                                     | REFACTOR                                                 |
| ---- | ------------------------------ | ---------------------------- | --------------------------------- | ------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | -------------------------------------------------------- |
| 4.1  | `tests/test_collection_acl.py` | Unit (TransactionCase / ACL) | ✅ 4/4 existing TestCollectionAcl | ✅ Written first (queue/approve/reject ACL cases) | ✅ 0 failed, 0 error(s) of 7 tests; existing `ir.model.access.csv` already denied portal | ✅ portal deny (queue+approve+reject+read) + internal approve + internal reject | ➖ None needed — no production ACL change                |
| 4.2  | `__manifest__.py`              | Structural                   | N/A (version string)              | ➖ Tests N/A                                      | ✅ upgrade exit 0; `Module collection loaded`                                            | ➖ Triangulation skipped: single version string `19.0.1.4.0`                    | ➖ None needed                                           |
| 4.3  | full `/collection`             | Unit (TransactionCase)       | ✅ 100/100 prior full suite       | N/A (verification)                                | ✅ 0 failed, 0 error(s) of 103 tests                                                     | ➖ Full suite, not new cases                                                    | ➖ None needed                                           |
| 4.4  | pre-commit                     | Quality                      | N/A                               | N/A                                               | ✅ scoped `--files` exit 0                                                               | ➖ Triangulation skipped: lint gate                                             | ➖ Reverted unrelated glob auto-fixes (archive/prettier) |

### Test Summary

- **Total tests written this batch (PR 4)**: 3
  (`test_portal_user_review_queue_approve_reject_denied`,
  `test_internal_user_review_queue_and_approve_allowed`,
  `test_internal_user_review_reject_allowed`)
- **Total tests passing**: 103 collection tests, 0 failed, 0 errors (full
  `/collection`); was 100 after PR 3
- **Layers used**: Unit/integration via Odoo `TransactionCase` (3 new ACL + prior), E2E
  (0 — unavailable)
- **Approval tests** (refactoring): existing CRUD ACL tests still pass (4/4 safety net →
  7/7 with review cases)
- **Pure functions created**: 0 (ACL coverage only; helper
  `_create_attached_pending_line` is test-only)

### Safety Net (before adding review ACL tests)

```
docker exec -i seedian-odoo-1 odoo -d devel -u collection --test-enable --stop-after-init --workers=0 --http-port=18069 --test-tags /collection:TestCollectionAcl
```

Result: exit 0; `0 failed, 0 error(s) of 4 tests`.

### RED gate (4.1, tests written first — no production ACL edit)

Same TestCollectionAcl command after adding three review tests: exit 0;
`0 failed, 0 error(s) of 7 tests`. Existing `base.group_user` ACL already raised
`AccessError` for portal on `get_review_queue` / `action_review_approve` /
`action_review_reject` / line read. No `security/*.xml` or CSV change.

### GREEN / 4.2 upgrade

```
docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --http-port=18069
```

Result: exit 0; `Module collection loaded`; `Modules loaded.`; `Registry loaded`.

### 4.3 full module

```
docker exec -i seedian-odoo-1 odoo -d devel -u collection --test-enable --stop-after-init --workers=0 --http-port=18069 --test-tags /collection
```

Result: exit 0; `0 failed, 0 error(s) of 103 tests`.

### 4.4 scoped pre-commit

First glob `odoo/custom/src/private/collection/**` failed on pre-existing trailing
whitespace in `openspec/changes/archive/**` and would have rewritten unrelated files.
Those auto-fixes were reverted. Re-ran on explicit Phase 4 files:

```
pre-commit run --files odoo/custom/src/private/collection/tests/test_collection_acl.py odoo/custom/src/private/collection/__manifest__.py odoo/custom/src/private/collection/README.rst odoo/custom/src/private/collection/static/description/index.html odoo/custom/src/private/collection/openspec/changes/document-review-ocr-validation/tasks.md
```

Result: exit 0; all applicable hooks Passed. Optional pylint
`C8101 manifest-required-author` warning (pre-existing Seedian vs Eynes) did not fail
the hook.

### Safety Net (before production viewer edits — Phase 3, retained)

```
docker exec -i seedian-odoo-1 odoo -d devel -u collection --test-enable --stop-after-init --workers=0 --http-port=18069 --test-tags /collection:TestCollectionDocumentReview,/collection:TestCollectionUi
```

Result: exit 0; `0 failed, 0 error(s) of 34 tests`.

### RED gate (3.1, tests only — placeholder viewer still in XML)

```
docker exec -i seedian-odoo-1 odoo -d devel -u collection --test-enable --stop-after-init --workers=0 --http-port=18069 --test-tags /collection:TestCollectionDocumentReview.test_queue_image_payload_is_web_content_url_only,/collection:TestCollectionDocumentReview.test_queue_pdf_payload_is_web_content_url_only,/collection:TestCollectionDocumentReview.test_document_review_viewer_binds_web_content_for_image_and_pdf,/collection:TestCollectionDocumentReview.test_document_review_viewer_has_loading_error_empty_attachment_states
```

Result: exit 1; `2 failed, 0 error(s) of 4 tests` — payload URL tests passed (queue
already returned `/web/content`); XML tests failed (`viewer-placeholder` present;
`viewer-loading` missing).

### GREEN gate (after img/iframe viewer)

Same four-test command: exit 0; `0 failed, 0 error(s) of 4 tests`.

Focused Ui+DocumentReview: exit 0; `0 failed, 0 error(s) of 38 tests`.

### After 3.3 refactor

Focused: exit 0; `0 failed, 0 error(s) of 38 tests`. Full module:
`--test-tags /collection` → exit 0; `0 failed, 0 error(s) of 100 tests`.

## Work Unit Evidence

### Phase 1 (prior batch)

| Evidence                                          | Value                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --test-enable --stop-after-init --workers=0 --http-port=18069 --test-tags /collection:TestCollectionDocumentReview,/collection:TestCollectionVoucher,/collection:TestCollectionPaymentDocumentId,/collection:TestCollectionPaymentAttachment` → exit 0; **0 failed, 0 error(s) of 48 tests**. Full module then: `--test-tags /collection` → exit 0; **0 failed, 0 error(s) of 94 tests**. |
| Runtime harness command/scenario and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --http-port=18069` → exit 0; `Module collection loaded`; `Modules loaded.`; `Registry loaded`. Additive `review_status` default `pending` applied without `migrations/`.                                                                                                                                                                                                |
| Rollback boundary                                 | `models/collection_voucher.py`, `models/collection_voucher_line.py`, `tests/test_collection_document_review.py`, `tests/__init__.py`, voucher/payment test extensions. Revert those files and upgrade `collection`. Does not include OWL/static, document-review views, ACL tests, or `__manifest__.py` version.                                                                                                                                     |

### Phase 2 (prior batch)

| Evidence                                          | Value                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Focused test command and exact result             | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --test-enable --stop-after-init --workers=0 --http-port=18069 --test-tags /collection:TestCollectionUi,/collection:TestCollectionDocumentReview` → exit 0; **0 failed, 0 error(s) of 34 tests**. Full module: `--test-tags /collection` → exit 0; **0 failed, 0 error(s) of 96 tests**. (`--http-port=18069` because 8069 is held by the running odoo process.)                       |
| Runtime harness command/scenario and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --http-port=18069` → exit 0; `Module collection loaded`; `Modules loaded.`; `Registry loaded`. UI xmlid/tag assertions are the harness for empty + multi-line nav. **N/A browser E2E** — e2e layer unavailable in `openspec/config.yaml`.                                                                                                                           |
| Rollback boundary                                 | `static/src/document_review/*`, `views/collection_document_review_views.xml`, `__manifest__.py` (data/assets only; version still `19.0.1.3.0`), `tests/test_collection_ui.py`, `openspec/changes/document-review-ocr-validation/tasks.md`, `openspec/changes/document-review-ocr-validation/apply-progress.md`. Revert those and upgrade `collection`. Does not include model review fields, ACL tests, binary viewer, or manifest version bump. |

### Phase 3 (prior batch)

| Evidence                                          | Value                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --test-enable --stop-after-init --workers=0 --http-port=18069 --test-tags /collection:TestCollectionDocumentReview,/collection:TestCollectionUi` → exit 0; **0 failed, 0 error(s) of 38 tests**. Full module: `--test-tags /collection` → exit 0; **0 failed, 0 error(s) of 100 tests**.                                                                                                                                                                     |
| Runtime harness command/scenario and exact result | **N/A browser E2E** — e2e layer unavailable in `openspec/config.yaml`. Image vs PDF branching is covered by Python URL tests (`test_queue_image_payload_is_web_content_url_only`, `test_queue_pdf_payload_is_web_content_url_only`) plus `attachmentViewerKind` helper logic; browser visual check is follow-up. Upgrade: `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --http-port=18069` → exit 0; `Module collection loaded`; `Modules loaded.`; `Registry loaded`.                   |
| Rollback boundary                                 | viewer in `document_review_action.*` + helpers + any 3.1 test additions + openspec tasks/apply-progress. Specifically: `static/src/document_review/document_review_action.esm.js`, `.xml`, `.scss`, `document_review_helpers.esm.js`, `tests/test_collection_document_review.py`, `openspec/changes/document-review-ocr-validation/tasks.md`, `openspec/changes/document-review-ocr-validation/apply-progress.md`. Revert those and upgrade `collection`. Does not include ACL tests or `__manifest__.py` version bump. |

### Phase 4 (this batch)

| Evidence                                          | Value                                                                                                                                                                                                                                                                                                                                         |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --test-enable --stop-after-init --workers=0 --http-port=18069 --test-tags /collection:TestCollectionAcl` → exit 0; **0 failed, 0 error(s) of 7 tests**. Full module: `--test-tags /collection` → exit 0; **0 failed, 0 error(s) of 103 tests**.                                    |
| Runtime harness command/scenario and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --http-port=18069` → exit 0; `Module collection loaded`; `Modules loaded.`; `Registry loaded`. Version `19.0.1.4.0`.                                                                                                                                             |
| Rollback boundary                                 | `tests/test_collection_acl.py`, `__manifest__.py` version, generated `README.rst` + `static/description/index.html` digests, `openspec/changes/document-review-ocr-validation/tasks.md`, `openspec/changes/document-review-ocr-validation/apply-progress.md`. Revert those and upgrade `collection`. Does not include model/OWL/viewer files. |

## Public contracts (cumulative)

- `collection.voucher.line.get_review_queue()` — ordered payloads; content URL; no
  `datas`/base64
- `collection.voucher.line.action_review_approve(vals=None)` — eligible only; editable
  fields; not `document_id`; audit; aggregate `action_validate` when all attached
  siblings approved
- `collection.voucher.line.action_review_reject()` — eligible only; audit;
  `action_reject` on voucher
- Attachment Binary write → `pending` + clear audit
- `collection.voucher.action_validate()` — `UserError` if any attached line is `pending`
- OWL client tag `collection.document_review`: `orm.call` queue/approve/reject; typed
  editors; no attachment datas in `useState`; `attachment_url` string only
- Viewer: `<img>` for image filename/MIME, `<iframe>` for PDF; both bind
  `current.attachment_url`
  (`/web/content?model=collection.voucher.line&id=…&field=attachment`); loading until
  load, error on failed load, empty-attachment distinct from queue-empty; never fetch
  binary into JS state
- ACL: `base.group_user` full CRUD only; portal/`with_user(portal)` gets `AccessError`
  on queue/approve/reject (and line read); internal users can create attached pending
  lines, see them in queue, and approve/reject

## Deviations from Design

None — implementation matches design. Existing `ir.model.access.csv` already denied
non-internal users; no new groups or record rules were added.

## Issues Found

- `docker exec` of a second `odoo` on the live `seedian-odoo-1` container requires
  `--http-port` other than 8069 (`Address already in use`). Focused and full tests used
  `--http-port=18069`.
- `invoke test -m collection` uses `docker compose run` and was not used, per apply
  instructions when the stack is already up.
- Browser E2E for image vs PDF visual rendering is unavailable (`openspec/config.yaml`
  e2e: false); Python URL tests + helper logic plus upgrade are the runtime harness for
  PR 3. Browser visual check is follow-up.
- Broad `pre-commit run --files odoo/custom/src/private/collection/**` hits archived
  OpenSpec markdown (trailing whitespace) and would rewrite unrelated files. Phase 4
  re-ran on explicit changed files after reverting those auto-fixes.

## Remaining Tasks

None — all 18 tasks `[x]`. Ready for `sdd-verify`.

## Workload / PR Boundary

- Mode: stacked PR slice (`stacked-to-main`)
- Current work unit: PR 4 / ACL + final verification
- Boundary: starts at review ACL tests + manifest `19.0.1.4.0`; ends after full
  `/collection` tests and scoped pre-commit
- Estimated review budget impact: ACL tests + version bump + generated README digest; no
  production security XML
