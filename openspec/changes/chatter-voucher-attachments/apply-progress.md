# Apply Progress: chatter-voucher-attachments

**Change**: chatter-voucher-attachments
**Mode**: Strict TDD
**Batch**: Work Unit 2 / PR 2 (Phase 2, tasks 2.1–2.4) — Phase 1 (1.1–1.11) complete
**Branch**: `feat/chatter-voucher-attachments-02-mcp-tests` (stacked on
`feat/chatter-voucher-attachments-01-migrate-model` @ `86bb6a8`; local only; not pushed)

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

### Phase 2 (PR 2)

- [x] 2.1 RED `TestCollectionMcpAttachment`: omit valid; MIME/b64 `UserError` no writes; chatter proof not `res_field=attachment`
- [x] 2.2 GREEN validate nest then post; fail-closed before writes
- [x] 2.3 RED exact-retry with/without nest: return all; no add/replace/compare
- [x] 2.4 GREEN exact-retry / UniqueViolation replay: no post, no nest compare

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

### Test Summary

- **Safety net (Phase 2 start)**: `TestCollectionMcpAttachment` → **0 failed, 0 error(s) of 9 tests**
- **2.1 RED execute**: **0 failed, 0 error(s) of 7 tests** (behavior already present from 1.10; tests lock omit / MIME-b64 fail-closed / not `res_field=attachment`)
- **2.3 RED execute (exact-retry + UniqueViolation valid nest)**: **0 failed, 0 error(s) of 7 tests**
- **2.3/2.4 RED execute (`test_unique_violation_replay_ignores_invalid_nest`)**: **0 failed, 1 error(s) of 1 tests**
- **Phase 2 focused GREEN**: `TestCollectionMcpAttachment` → **0 failed, 0 error(s) of 16 tests** (exit 0)
- **After refactor**: `TestCollectionMcpAttachment` + UniqueViolation tool tests → **0 failed, 0 error(s) of 18 tests** (exit 0)
- **Layers used**: Unit/TransactionCase
- **Approval tests**: none (behavior change on UniqueViolation+invalid nest only)
- **Pure functions created**: 0 (`_collection_replay_existing` is an ORM helper)

## Work Unit Evidence

| Evidence | Required value |
|---|---|
| Focused test command and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection:TestCollectionMcpAttachment` → **exit 0**, `0 failed, 0 error(s) of 16 tests` |
| Runtime harness command/scenario and exact result | N/A — Odoo `TransactionCase` rolls back; no extra runtime boundary beyond the focused module tests |
| Rollback boundary | Revert this branch/commit: `tests/test_collection_mcp_tool.py`, `tools/collection_voucher.py`, and Phase 2 marks in this change folder. Does **not** revert Phase 1 mixin/migration/views |

## Installability coupling (Phase 1, preserved)

Binary field drop cannot `-u collection` while views still declare `attachment`. Widget strip (1.8) and MCP `message_post` glue (1.10) traveled with 1.2 so the upgrade loads. Review URL remains `/web/content?model=...&field=attachment` (Phase 3). Queue eligibility now uses `message_main_attachment_id` so helpers stay installable.

## Deviations from Design

None on proof pointer, picker, MCP persist, nest schema, or exact-retry ignore. Phase 2 added a search-miss + nest-`UserError` re-lookup so UniqueViolation-style replay does not compare nests; true all-new invalid nests still fail-closed. Review `/web/content/{id}` remains deferred to Phase 3.

## Issues Found

- Phase 1: `TestCollectionDocumentReviewFlag` settings-toggle tests error on `res_config_settings.default_picking_policy` NOT NULL. Pre-existing stock/settings schema issue; not fixed in this batch.
- `message_post` body was wrapped with `_()` (pylint C8107) because this slice edits `tools/collection_voucher.py`. Nest schema unchanged.

## Remaining Tasks

- [ ] Phase 3 review URL `/web/content/{id}`, OWL, AGENTS/readme (3.1–3.3)
- [ ] Phase 4 upgrade/verify (4.1–4.3)

## Workload / PR Boundary

- Mode: stacked PR slice (`auto-chain` / `stacked-to-main`)
- Current work unit: PR 2 MCP tests
- Boundary: starts from PR 1 `feat/chatter-voucher-attachments-01-migrate-model` (`86bb6a8`); ends with MCP nest persist tests + UniqueViolation/exact-retry ignore nests
- Estimated review budget impact: authored ~408 lines on tests+tool (under 800 attempt cap; above 400 review budget as forecast High)
