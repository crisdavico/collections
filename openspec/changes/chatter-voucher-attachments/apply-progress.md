# Apply Progress: chatter-voucher-attachments

**Change**: chatter-voucher-attachments
**Mode**: Strict TDD
**Batch**: Work Unit 3 / PR 3 (Phase 3, tasks 3.1–3.3) — Phase 1 (1.1–1.11) and
Phase 2 (2.1–2.4) complete
**Branch**: `feat/chatter-voucher-attachments-03-document-review` (stacked on
`feat/chatter-voucher-attachments-02-mcp-tests` @ `78c3f96`; local only; not pushed)

## Completed Tasks

### Phase 1 (PR 1) — preserved

- [x] 1.1 RED voucher/mail chatter proof + MIME picker
- [x] 1.2 GREEN mixin inherit, picker override, drop Binary
- [x] 1.3 RED replace/clear/omit/invalid/reset
- [x] 1.4 GREEN write-reset on `message_main_attachment_id`; keep `attachment_rotation`
- [x] 1.5 RED SQL migrate scenarios
- [x] 1.6 GREEN `migrations/19.0.1.13.0` + manifest `19.0.1.13.0`
- [x] 1.7 RED UI: no Binary widgets; chatter remains
- [x] 1.8 GREEN views: drop Binary widgets; `<chatter open_attachments="True"/>`
- [x] 1.9 RED MCP nest → chatter designated proof
- [x] 1.10 GREEN savepoint `message_post` after create; nest schema unchanged
- [x] 1.11 GREEN helpers create proof via `message_post`

### Phase 2 (PR 2) — preserved

- [x] 2.1 RED `TestCollectionMcpAttachment`: omit valid; MIME/b64 `UserError` no writes; chatter proof not `res_field=attachment`
- [x] 2.2 GREEN validate nest then post; fail-closed before writes
- [x] 2.3 RED exact-retry with/without nest: return all; no add/replace/compare
- [x] 2.4 GREEN exact-retry / UniqueViolation replay: no post, no nest compare

### Phase 3 (PR 3)

- [x] 3.1 RED `tests/test_collection_document_review.py`: queue pending+main; empty/cross-sheet; `/web/content/{id}` (no `field=`); image+PDF; OWL no base64; viewer states; extras skip rotation reset; replace/clear → 0; stale if proof missing
- [x] 3.2 GREEN `models/collection_voucher.py`: eligibility on main; `_attachment_content_url` → `/web/content/{id}`; payload from `ir.attachment`. OWL keeps `current.attachment_url`
- [x] 3.3 GREEN `AGENTS.md` + `readme/DESCRIPTION.md`: chatter proof; no Binary

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_collection_voucher.py`, `tests/test_collection_mail.py` | Unit (TransactionCase) | ✅ 26/26 `TestCollectionVoucher`+`TestCollectionMail` | ✅ Written then executed: 1 failed, 5 error(s) of 6 (no `message_main_attachment_id`) | ✅ Passed after mixin + picker | ✅ PNG proof, PDF proof, extra does not steal, non-image extra, force=True text | ➖ None needed |
| 1.2 | same | Unit | (same baseline) | (1.1 RED) | ✅ Inherit `mail.thread.main.attachment`; override picker; drop Binary | ➖ Structural with 1.1 cases | ➖ None needed |
| 1.3 | `tests/test_collection_voucher.py` | Unit | covered by 1.1 net | ✅ Written: replace/clear/omit/invalid/extra-no-reset | ✅ Passed with 1.4 | ✅ approved replace, rejected extra, clear keeps decided, omit, invalid UserError | ➖ None needed |
| 1.4 | `models/collection_voucher.py` | Unit | — | (1.3 RED) | ✅ write-reset on main id change; clear rotation 0; kanban reopen requires main replace | ✅ replace vs extra vs clear | ➖ None needed |
| 1.5 | `tests/test_collection_voucher.py` (`TestCollectionVoucherAttachmentMigrate`) | Unit | N/A (new class) | ✅ Written (import migrate scripts + SQL leftover rows) | ✅ Passed after 1.6 | ✅ named filename vs empty → `proof.bin` | ➖ None needed |
| 1.6 | `migrations/19.0.1.13.0/{pre,post}-migrate.py`, `__manifest__.py` | Unit | — | (1.5 RED) | ✅ pre nulls `res_field`, renames, links `mail.message`; post sets main | ➖ Structural with 1.5 cases | ➖ None needed |
| 1.7 | `tests/test_collection_ui.py` | Unit (arch) | UI Binary-widget test existed | ✅ Written invert: no Binary; chatter `open_attachments` | Execute blocked until 1.8 (`-u` ParseError on leftover widgets) then ✅ | ✅ form + list + kanban omit widgets | ➖ None needed |
| 1.8 | `views/collection_views.xml` | Unit | — | (1.7 RED) | ✅ widgets stripped; `<chatter open_attachments="True"/>` | ➖ Structural | ➖ None needed |
| 1.9 | `tests/test_collection_mcp_tool.py` | Unit | — | ✅ `test_create_with_valid_png_nest_becomes_chatter_proof` | ✅ Passed with 1.10 | ✅ PDF nest adapted helper still persists | ➖ None needed |
| 1.10 | `tools/collection_voucher.py` | Unit | — | (1.9 RED) | ✅ validate nest → sidecar → `message_post` in savepoint; no Binary vals | ➖ Nest schema unchanged (Phase 2 exact-retry triangulation) | ➖ None needed |
| 1.11 | `tests/test_collection_{acl,document_review,document_review_flag,mcp_tool,payment}.py` | Unit | — | N/A helpers | ✅ `post_voucher_proof` / `message_post` only | ➖ Helper rewrite | ➖ None needed |
| 2.1 | `tests/test_collection_mcp_tool.py` (`TestCollectionMcpAttachment`) | Unit (TransactionCase) | ✅ 0 failed, 0 error(s) of 9 tests | ✅ Written first: omit, MIME/b64/text, incomplete nest, batch fail-closed, `res_field=attachment` leftover + no Binary fields. Execute of 2.1 methods: **0 failed, 0 error(s) of 7 tests** (already GREEN from 1.10 persist glue; contract locked) | ✅ No new persist code; Phase 1 `message_post` + nest validate-before-create already satisfy omit/MIME fail-closed/chatter proof | ✅ PNG not field-attachment, omit empty main, MIME mismatch, bad b64, text/plain, incomplete `datas`, two-payment batch writes nothing | ➖ None needed |
| 2.2 | `tools/collection_voucher.py` | Unit | (2.1 net) | (2.1 RED locked the contract) | ✅ Validate nest then `message_post` in savepoint; fail-closed before writes (already in 1.10). Nest schema `{name,mimetype,datas}` unchanged | ✅ batch sibling does not persist | ➖ `message_post` body wrapped with `_()` for pylint C8107 on the touched file |
| 2.3 | `tests/test_collection_mcp_tool.py` | Unit | covered | ✅ Written: exact-retry invalid nest; mixed two-payment return-all; UniqueViolation no-post / no-replace; UniqueViolation invalid nest | Exact-retry + UniqueViolation **valid** nest: **0 failed, 0 error(s) of 7 tests** immediately. UniqueViolation **invalid** nest: **0 failed, 1 error(s) of 1 tests** (`UserError: Attachment content must be valid base64-encoded data.`) | ✅ with/without nest, add vs replace, mixed set return-all, invalid nest ignored on exact-retry | — |
| 2.4 | `tools/collection_voucher.py` | Unit | — | (2.3 UniqueViolation invalid-nest RED) | ✅ On nest `UserError` after a search miss, invalidate + replay if the exact `document_id` set exists; UniqueViolation path uses the same helper. True all-new invalid nest still re-raises (fail-closed). Focused class after GREEN: **0 failed, 0 error(s) of 16 tests** | ✅ UniqueViolation + valid nest no post; UniqueViolation + PDF nest does not replace PNG; UniqueViolation + invalid nest replays | ✅ Extracted `_collection_replay_existing`; tests still **0 failed, 0 error(s) of 18** including `TestCollectionMcpTool` UniqueViolation cases |
| 3.1 | `tests/test_collection_document_review.py` | Unit (TransactionCase) | ✅ 0 failed, 0 error(s) of 36 tests | ✅ Written: invert URL to `/web/content/{att.id}` (no `field=`), payload `mimetype` from `ir.attachment`, extras skip rotation, clear → 0, stale if proof missing. Execute: **2 failed, 4 error(s) of 39 tests** (`field=attachment` URLs + `KeyError: mimetype`) | ✅ Passed with 3.2 | ✅ PNG+JPEG image URLs, PDF URL, extras keep 90°, clear drops queue, stale mutations refused | ➖ None needed |
| 3.2 | `models/collection_voucher.py` | Unit | (3.1 net) | (3.1 RED) | ✅ `_attachment_content_url` → `/web/content/{id}`; payload filename/mimetype/url from designated `ir.attachment`; eligibility already `pending` + main. OWL unchanged (`current.attachment_url`). Focused class: **0 failed, 0 error(s) of 39 tests** (exit 0) | ✅ image vs PDF mimetype; extras vs replace vs clear | ➖ None needed |
| 3.3 | `AGENTS.md`, `readme/DESCRIPTION.md` | Docs | N/A | N/A (docs) | ✅ Chatter designated proof; no Binary `attachment` field; review `/web/content/{id}` | ➖ Single | ➖ None needed |

### Test Summary

- **Safety net (Phase 3 start)**: `TestCollectionDocumentReview` → **0 failed, 0 error(s) of 36 tests**
- **3.1 RED execute**: **2 failed, 4 error(s) of 39 tests** (old Binary `field=attachment` URLs + missing payload `mimetype`)
- **Phase 3 focused GREEN**: `TestCollectionDocumentReview` → **0 failed, 0 error(s) of 39 tests** (exit 0)
- **Layers used**: Unit/TransactionCase
- **Approval tests**: none
- **Pure functions created**: 0

## Work Unit Evidence

### Phase 2 (preserved)

| Evidence | Required value |
|---|---|
| Focused test command and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection:TestCollectionMcpAttachment` → **exit 0**, `0 failed, 0 error(s) of 16 tests` |
| Runtime harness command/scenario and exact result | N/A — Odoo `TransactionCase` rolls back; no extra runtime boundary beyond the focused module tests |
| Rollback boundary | Revert PR 2 branch/commit: `tests/test_collection_mcp_tool.py`, `tools/collection_voucher.py`, and Phase 2 marks. Does **not** revert Phase 1 mixin/migration/views |

### Phase 3 (this batch)

| Evidence | Required value |
|---|---|
| Focused test command and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection:TestCollectionDocumentReview` → **exit 0**, `0 failed, 0 error(s) of 39 tests` |
| Runtime harness command/scenario and exact result | N/A — Odoo `TransactionCase` rolls back; no extra runtime boundary beyond the focused module tests. Attempt acquired (`sha256:b705bd143693cae895ba2aceef292d0002d71f185e7bd3d6f0a34e8d9e48c348`); not settled |
| Rollback boundary | Revert this branch/commit: `tests/test_collection_document_review.py`, `models/collection_voucher.py` (`_attachment_content_url` + payload), `AGENTS.md`, `readme/DESCRIPTION.md`, and Phase 3 marks in this change folder. Does **not** revert Phase 1/2 mixin/MCP persist |

## Installability coupling (Phase 1, preserved)

Binary field drop cannot `-u collection` while views still declare `attachment`. Widget strip (1.8) and MCP `message_post` glue (1.10) traveled with 1.2 so the upgrade loads. Queue eligibility uses `message_main_attachment_id`. Review URL is now `/web/content/{id}` of designated proof (Phase 3).

## Deviations from Design

None on proof pointer, picker, MCP persist, nest schema, exact-retry ignore, or review `/web/content/{id}`. Phase 2 added a search-miss + nest-`UserError` re-lookup so UniqueViolation-style replay does not compare nests; true all-new invalid nests still fail-closed. OWL `static/src/document_review/*` was not edited; it already binds `current.attachment_url` and reads `mimetype`.

## Issues Found

- Phase 1: `TestCollectionDocumentReviewFlag` settings-toggle tests error on `res_config_settings.default_picking_policy` NOT NULL. Pre-existing stock/settings schema issue; not fixed in this batch.
- Phase 2: `message_post` body was wrapped with `_()` (pylint C8107) because that slice edits `tools/collection_voucher.py`. Nest schema unchanged.

## Remaining Tasks

- [ ] Phase 4 upgrade/verify (4.1–4.3)

## Workload / PR Boundary

- Mode: stacked PR slice (`auto-chain` / `stacked-to-main`)
- Current work unit: PR 3 document review + docs
- Boundary: starts from PR 2 `feat/chatter-voucher-attachments-02-mcp-tests` (`78c3f96`); ends with review `/web/content/{id}` payload, extras/clear/stale rotation tests, AGENTS/readme
- Estimated review budget impact: authored 119 insertions / 49 deletions on tests+model+docs (under 400 review budget and 800 attempt cap)
