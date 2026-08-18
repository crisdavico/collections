# Apply Progress: chatter-voucher-attachments

**Change**: chatter-voucher-attachments

**Mode**: Strict TDD (Phases 1–3); Phase 4 is upgrade/lint/full tests plus a test-helper
TDD cycle for 4.3

**Batch**: Work Unit 4 / Phase 4 (tasks 4.1–4.3 complete)

**Branch**: `feat/chatter-voucher-attachments-04-upgrade` (stacked on
`feat/chatter-voucher-attachments-03-document-review` @ `68d5bfc`; local only; not
pushed). Attempt
`sha256:27d029566e887f7f1c83e14a8068f616ef45198fe48c34b18f46a88aa12484c5` acquired
(`proceed`); **not settled** (orchestrator instruction).

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

- [x] 2.1 RED `TestCollectionMcpAttachment`: omit valid; MIME/b64 `UserError` no writes;
      chatter proof not `res_field=attachment`
- [x] 2.2 GREEN validate nest then post; fail-closed before writes
- [x] 2.3 RED exact-retry with/without nest: return all; no add/replace/compare
- [x] 2.4 GREEN exact-retry / UniqueViolation replay: no post, no nest compare

### Phase 3 (PR 3) — preserved

- [x] 3.1 RED `tests/test_collection_document_review.py`: queue pending+main;
      empty/cross-sheet; `/web/content/{id}` (no `field=`); image+PDF; OWL no base64;
      viewer states; extras skip rotation reset; replace/clear → 0; stale if proof
      missing
- [x] 3.2 GREEN `models/collection_voucher.py`: eligibility on main;
      `_attachment_content_url` → `/web/content/{id}`; payload from `ir.attachment`. OWL
      keeps `current.attachment_url`
- [x] 3.3 GREEN `AGENTS.md` + `readme/DESCRIPTION.md`: chatter proof; no Binary

### Phase 4 (this batch)

- [x] 4.1 Module upgrade on `devel` (exit 0)
- [x] 4.2 Scoped pre-commit on change files (exit 0 after hook-only fixes)
- [x] 4.3 Full `invoke test -m collection --mode=update` — **0 failed, 0 error(s) of 242
      tests** (exit 0)

## TDD Cycle Evidence

Preserved from Phases 1–3 (see prior apply-progress batches). Phase 4.3 added a
test-helper cycle after live `-u collection` dropped `attachment_filename`.

| Task | Test File                                                                                              | Layer                  | Safety Net                                                                               | RED                                                                                                                                                                                                                                                               | GREEN                                                                                                                                                                                                                                                                      | TRIANGULATE                                                                                                                            | REFACTOR                                                                                                                                       |
| ---- | ------------------------------------------------------------------------------------------------------ | ---------------------- | ---------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.1  | `tests/test_collection_voucher.py`, `tests/test_collection_mail.py`                                    | Unit (TransactionCase) | ✅ 26/26 `TestCollectionVoucher`+`TestCollectionMail`                                    | ✅ Written then executed: 1 failed, 5 error(s) of 6 (no `message_main_attachment_id`)                                                                                                                                                                             | ✅ Passed after mixin + picker                                                                                                                                                                                                                                             | ✅ PNG proof, PDF proof, extra does not steal, non-image extra, force=True text                                                        | ➖ None needed                                                                                                                                 |
| 1.2  | same                                                                                                   | Unit                   | (same baseline)                                                                          | (1.1 RED)                                                                                                                                                                                                                                                         | ✅ Inherit `mail.thread.main.attachment`; override picker; drop Binary                                                                                                                                                                                                     | ➖ Structural with 1.1 cases                                                                                                           | ➖ None needed                                                                                                                                 |
| 1.3  | `tests/test_collection_voucher.py`                                                                     | Unit                   | covered by 1.1 net                                                                       | ✅ Written: replace/clear/omit/invalid/extra-no-reset                                                                                                                                                                                                             | ✅ Passed with 1.4                                                                                                                                                                                                                                                         | ✅ approved replace, rejected extra, clear keeps decided, omit, invalid UserError                                                      | ➖ None needed                                                                                                                                 |
| 1.4  | `models/collection_voucher.py`                                                                         | Unit                   | —                                                                                        | (1.3 RED)                                                                                                                                                                                                                                                         | ✅ write-reset on main id change; clear rotation 0; kanban reopen requires main replace                                                                                                                                                                                    | ✅ replace vs extra vs clear                                                                                                           | ➖ None needed                                                                                                                                 |
| 1.5  | `tests/test_collection_voucher.py` (`TestCollectionVoucherAttachmentMigrate`)                          | Unit                   | N/A (new class)                                                                          | ✅ Written (import migrate scripts + SQL leftover rows)                                                                                                                                                                                                           | ✅ Passed after 1.6                                                                                                                                                                                                                                                        | ✅ named filename vs empty → `proof.bin`                                                                                               | ➖ None needed                                                                                                                                 |
| 1.6  | `migrations/19.0.1.13.0/{pre,post}-migrate.py`, `__manifest__.py`                                      | Unit                   | —                                                                                        | (1.5 RED)                                                                                                                                                                                                                                                         | ✅ pre nulls `res_field`, renames, links `mail.message`; post sets main                                                                                                                                                                                                    | ➖ Structural with 1.5 cases                                                                                                           | ➖ None needed                                                                                                                                 |
| 1.7  | `tests/test_collection_ui.py`                                                                          | Unit (arch)            | UI Binary-widget test existed                                                            | ✅ Written invert: no Binary; chatter `open_attachments`                                                                                                                                                                                                          | Execute blocked until 1.8 (`-u` ParseError on leftover widgets) then ✅                                                                                                                                                                                                    | ✅ form + list + kanban omit widgets                                                                                                   | ➖ None needed                                                                                                                                 |
| 1.8  | `views/collection_views.xml`                                                                           | Unit                   | —                                                                                        | (1.7 RED)                                                                                                                                                                                                                                                         | ✅ widgets stripped; `<chatter open_attachments="True"/>`                                                                                                                                                                                                                  | ➖ Structural                                                                                                                          | ➖ None needed                                                                                                                                 |
| 1.9  | `tests/test_collection_mcp_tool.py`                                                                    | Unit                   | —                                                                                        | ✅ `test_create_with_valid_png_nest_becomes_chatter_proof`                                                                                                                                                                                                        | ✅ Passed with 1.10                                                                                                                                                                                                                                                        | ✅ PDF nest adapted helper still persists                                                                                              | ➖ None needed                                                                                                                                 |
| 1.10 | `tools/collection_voucher.py`                                                                          | Unit                   | —                                                                                        | (1.9 RED)                                                                                                                                                                                                                                                         | ✅ validate nest → sidecar → `message_post` in savepoint; no Binary vals                                                                                                                                                                                                   | ➖ Nest schema unchanged (Phase 2 exact-retry triangulation)                                                                           | ➖ None needed                                                                                                                                 |
| 1.11 | `tests/test_collection_{acl,document_review,document_review_flag,mcp_tool,payment}.py`                 | Unit                   | —                                                                                        | N/A helpers                                                                                                                                                                                                                                                       | ✅ `post_voucher_proof` / `message_post` only                                                                                                                                                                                                                              | ➖ Helper rewrite                                                                                                                      | ➖ None needed                                                                                                                                 |
| 2.1  | `tests/test_collection_mcp_tool.py` (`TestCollectionMcpAttachment`)                                    | Unit (TransactionCase) | ✅ 0 failed, 0 error(s) of 9 tests                                                       | ✅ Written first: omit, MIME/b64/text, incomplete nest, batch fail-closed, `res_field=attachment` leftover + no Binary fields. Execute of 2.1 methods: **0 failed, 0 error(s) of 7 tests** (already GREEN from 1.10 persist glue; contract locked)                | ✅ No new persist code; Phase 1 `message_post` + nest validate-before-create already satisfy omit/MIME fail-closed/chatter proof                                                                                                                                           | ✅ PNG not field-attachment, omit empty main, MIME mismatch, bad b64, text/plain, incomplete `datas`, two-payment batch writes nothing | ➖ None needed                                                                                                                                 |
| 2.2  | `tools/collection_voucher.py`                                                                          | Unit                   | (2.1 net)                                                                                | (2.1 RED locked the contract)                                                                                                                                                                                                                                     | ✅ Validate nest then `message_post` in savepoint; fail-closed before writes (already in 1.10). Nest schema `{name,mimetype,datas}` unchanged                                                                                                                              | ✅ batch sibling does not persist                                                                                                      | ➖ `message_post` body wrapped with `_()` for pylint C8107 on the touched file                                                                 |
| 2.3  | `tests/test_collection_mcp_tool.py`                                                                    | Unit                   | covered                                                                                  | ✅ Written: exact-retry invalid nest; mixed two-payment return-all; UniqueViolation no-post / no-replace; UniqueViolation invalid nest                                                                                                                            | Exact-retry + UniqueViolation **valid** nest: **0 failed, 0 error(s) of 7 tests** immediately. UniqueViolation **invalid** nest: **0 failed, 1 error(s) of 1 tests** (`UserError: Attachment content must be valid base64-encoded data.`)                                  | ✅ with/without nest, add vs replace, mixed set return-all, invalid nest ignored on exact-retry                                        | —                                                                                                                                              |
| 2.4  | `tools/collection_voucher.py`                                                                          | Unit                   | —                                                                                        | (2.3 UniqueViolation invalid-nest RED)                                                                                                                                                                                                                            | ✅ On nest `UserError` after a search miss, invalidate + replay if the exact `document_id` set exists; UniqueViolation path uses the same helper. True all-new invalid nest still re-raises (fail-closed). Focused class after GREEN: **0 failed, 0 error(s) of 16 tests** | ✅ UniqueViolation + valid nest no post; UniqueViolation + PDF nest does not replace PNG; UniqueViolation + invalid nest replays       | ✅ Extracted `_collection_replay_existing`; tests still **0 failed, 0 error(s) of 18** including `TestCollectionMcpTool` UniqueViolation cases |
| 3.1  | `tests/test_collection_document_review.py`                                                             | Unit (TransactionCase) | ✅ 0 failed, 0 error(s) of 36 tests                                                      | ✅ Written: invert URL to `/web/content/{att.id}` (no `field=`), payload `mimetype` from `ir.attachment`, extras skip rotation, clear → 0, stale if proof missing. Execute: **2 failed, 4 error(s) of 39 tests** (`field=attachment` URLs + `KeyError: mimetype`) | ✅ Passed with 3.2                                                                                                                                                                                                                                                         | ✅ PNG+JPEG image URLs, PDF URL, extras keep 90°, clear drops queue, stale mutations refused                                           | ➖ None needed                                                                                                                                 |
| 3.2  | `models/collection_voucher.py`                                                                         | Unit                   | (3.1 net)                                                                                | (3.1 RED)                                                                                                                                                                                                                                                         | ✅ `_attachment_content_url` → `/web/content/{id}`; payload filename/mimetype/url from designated `ir.attachment`; eligibility already `pending` + main. OWL unchanged (`current.attachment_url`). Focused class: **0 failed, 0 error(s) of 39 tests** (exit 0)            | ✅ image vs PDF mimetype; extras vs replace vs clear                                                                                   | ➖ None needed                                                                                                                                 |
| 3.3  | `AGENTS.md`, `readme/DESCRIPTION.md`                                                                   | Docs                   | N/A                                                                                      | N/A (docs)                                                                                                                                                                                                                                                        | ✅ Chatter designated proof; no Binary `attachment` field; review `/web/content/{id}`                                                                                                                                                                                      | ➖ Single                                                                                                                              | ➖ None needed                                                                                                                                 |
| 4.3  | `tests/test_collection_voucher.py` (`TestCollectionVoucherAttachmentMigrate._insert_field_attachment`) | Unit (TransactionCase) | ✅ `test_empty_filename_falls_back_to_proof_bin` still passed after live `-u collection` | ✅ Already RED: `test_binary_field_attachment_migrates_to_chatter_main` → `AssertionError: 'proof.bin' != 'migrated.png'` (helper could not seed `migrated.png` once `attachment_filename` was gone)                                                              | ✅ Helper seeds `ir.attachment.name` when the column is missing (keep `res_field=attachment`). Focused class: **0 failed, 0 error(s) of 2 tests** (exit 0). Production migrate SQL unchanged                                                                               | ✅ named `migrated.png` vs empty → `proof.bin`                                                                                         | ➖ None needed                                                                                                                                 |

### Test Summary (Phases 1–3 preserved; 4.3 added)

- **Safety net (Phase 3 start)**: `TestCollectionDocumentReview` → **0 failed, 0
  error(s) of 36 tests**
- **3.1 RED execute**: **2 failed, 4 error(s) of 39 tests** (old Binary
  `field=attachment` URLs + missing payload `mimetype`)
- **Phase 3 focused GREEN**: `TestCollectionDocumentReview` → **0 failed, 0 error(s) of
  39 tests** (exit 0)
- **4.3 RED**: named-filename migrate after live schema drop →
  `'proof.bin' != 'migrated.png'`
- **4.3 GREEN**: focused migrate class **0 failed, 0 error(s) of 2 tests** (exit 0);
  full `--mode=update` **0 failed, 0 error(s) of 242 tests** (exit 0)
- **Layers used**: Unit/TransactionCase
- **Approval tests**: none
- **Pure functions created**: 0

## Work Unit Evidence

### Phase 2 (preserved)

| Evidence                                          | Required value                                                                                                                                                                                                                 |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Focused test command and exact result             | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection:TestCollectionMcpAttachment` → **exit 0**, `0 failed, 0 error(s) of 16 tests` |
| Runtime harness command/scenario and exact result | N/A — Odoo `TransactionCase` rolls back; no extra runtime boundary beyond the focused module tests                                                                                                                             |
| Rollback boundary                                 | Revert PR 2 branch/commit: `tests/test_collection_mcp_tool.py`, `tools/collection_voucher.py`, and Phase 2 marks. Does **not** revert Phase 1 mixin/migration/views                                                            |

### Phase 3 (preserved)

| Evidence                                          | Required value                                                                                                                                                                                                                                                              |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection:TestCollectionDocumentReview` → **exit 0**, `0 failed, 0 error(s) of 39 tests`                                             |
| Runtime harness command/scenario and exact result | N/A — Odoo `TransactionCase` rolls back; no extra runtime boundary beyond the focused module tests. Attempt acquired (`sha256:b705bd143693cae895ba2aceef292d0002d71f185e7bd3d6f0a34e8d9e48c348`); not settled                                                               |
| Rollback boundary                                 | Revert this branch/commit: `tests/test_collection_document_review.py`, `models/collection_voucher.py` (`_attachment_content_url` + payload), `AGENTS.md`, `readme/DESCRIPTION.md`, and Phase 3 marks in this change folder. Does **not** revert Phase 1/2 mixin/MCP persist |

### Phase 4 (this batch)

| Evidence                                          | Required value                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection:TestCollectionVoucherAttachmentMigrate` → **exit 0**, `0 failed, 0 error(s) of 2 tests`. Then from seedian root: `invoke test -m collection --mode=update` → **exit 0**, `0 failed, 0 error(s) of 242 tests`                                                                                     |
| Runtime harness command/scenario and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --workers=0 --http-port=18069` → **exit 0** (module `collection` loaded; views/security/data applied; no Traceback). Scoped `pre-commit run --files` on change model/tools/views/migrations/tests/AGENTS.md/readme → **exit 0**. Attempt acquired (`sha256:27d029566e887f7f1c83e14a8068f616ef45198fe48c34b18f46a88aa12484c5`); **not settled**                       |
| Rollback boundary                                 | Revert Phase 4 commits/branch: `openspec/changes/chatter-voucher-attachments/{tasks.md,apply-progress.md}`, prettier wrap in `AGENTS.md`, ruff-format in `tests/test_collection_{payment,voucher}.py`, E501 docstring wrap, pylint E8103 split of filename SELECT in `migrations/19.0.1.13.0/pre-migrate.py`, and the 4.3 helper seed of `ir.attachment.name` when `attachment_filename` is gone. Does **not** revert Phases 1–3 product behavior |

## Installability coupling (Phase 1, preserved)

Binary field drop cannot `-u collection` while views still declare `attachment`. Widget
strip (1.8) and MCP `message_post` glue (1.10) traveled with 1.2 so the upgrade loads.
Queue eligibility uses `message_main_attachment_id`. Review URL is now
`/web/content/{id}` of designated proof (Phase 3). Phase 4.1 upgrade on `devel`
completed with exit 0 after that drop.

## Deviations from Design

None on proof pointer, picker, MCP persist, nest schema, exact-retry ignore, or review
`/web/content/{id}`. Phase 2 added a search-miss + nest-`UserError` re-lookup so
UniqueViolation-style replay does not compare nests; true all-new invalid nests still
fail-closed. OWL `static/src/document_review/*` was not edited; it already binds
`current.attachment_url` and reads `mimetype`. Phase 4 lint-only: split `pre-migrate.py`
filename SELECT into two static queries (pylint E8103); no product behavior change
intended. Phase 4.3: production migrate SQL unchanged — named-filename coverage after
the live column drop is restored by seeding `ir.attachment.name` in the migrate test
helper when `attachment_filename` is absent.

## Issues Found

- Phase 1: `TestCollectionDocumentReviewFlag` settings-toggle tests error on
  `res_config_settings.default_picking_policy` NOT NULL. Pre-existing stock/settings
  schema issue; **not reproduced** in the Phase 4 full run (those two methods started
  and the suite reported **0 errors**).
- Phase 2: `message_post` body was wrapped with `_()` (pylint C8107) because that slice
  edits `tools/collection_voucher.py`. Nest schema unchanged.
- Phase 4.2: optional pylint C8101 (`manifest-required-author` expects `Eynes`) remains
  a warning; hook still Passed. Not fixed (pre-existing author).
- Phase 4.3 (resolved): after live `-u collection`, `attachment_filename` is gone so the
  migrate helper could not inject `migrated.png` and pre-migrate treated
  `ir.attachment.name == "attachment"` as empty → `proof.bin`. Fixed by seeding
  `ir.attachment.name` when the column is missing; empty filename still becomes
  `proof.bin`. Production migrate SQL unchanged.

## Remaining Tasks

None — Phase 4 apply complete. Next: sdd-verify.

## Workload / PR Boundary

- Mode: stacked PR slice (`auto-chain` / `stacked-to-main`)
- Current work unit: Phase 4 upgrade / lint / full tests
- Boundary: starts from PR 3 `feat/chatter-voucher-attachments-03-document-review`
  (`68d5bfc`); ends with upgrade evidence, scoped pre-commit, hook-only lint fixes, and
  4.3 named-filename migrate test helper after `attachment_filename` drop
- Estimated review budget impact: lint/docs/progress + small test-helper branch (well
  under 400)
