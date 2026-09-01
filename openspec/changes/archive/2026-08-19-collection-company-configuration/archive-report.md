# Archive Report: collection-company-configuration

**Date**: 2026-08-19 **Change**: collection-company-configuration **Archived to**:
`openspec/changes/archive/2026-08-19-collection-company-configuration/` **Artifact
store**: openspec **Status**: success **Intentional warnings**: yes (verify
`pass_with_warnings` — zero CRITICAL; design/TDD deviations listed below are closed
history, not open work)

## Gates

| Gate                      | Result                 | Evidence                                                                                                                                                                                                                                                            |
| ------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Task Completion           | PASS                   | Archived `tasks.md` — no `- [ ]`; Phases 1–8 tasks 1.1–8.2 all `[x]` (15/15)                                                                                                                                                                                        |
| Native Review Receipt     | PASS (absent)          | `reviewGate` structurally absent; archive proceeded under ordinary repository policy; no receipt demanded                                                                                                                                                           |
| CRITICAL in verify-report | PASS                   | `CRITICAL`: None; `blockers`: 0; verdict `pass_with_warnings`                                                                                                                                                                                                       |
| Destructive delta         | PASS (not destructive) | `rules.archive`: warn before merging destructive deltas. Four deltas have ADDED + MODIFIED only; **no REMOVED / RENAMED**. Unrelated main-spec requirements were preserved (vouchers 16, sheets 5, seller-lookup 5, document-review 14). No large-section deletion. |

## Final-state authority

Per orchestrator launch facts (outrank stale `verify-report` / `apply-progress` /
`state.yaml` pending or FAIL claims):

- All tasks 1.1–8.2 complete in `tasks.md` (15/15; no `- [ ]`)
- Verify at close: `pass_with_warnings`; **27/27** requirements; **98/98** scenarios;
  **0 CRITICAL**; **0 blockers**. Tests: `invoke test -m collection --mode=update` →
  **392 passed / 0 failed**. Scoped pre-commit exit 0
- Prior verify FAIL (94/98 UNTESTED When-paths) was **closed** by Phase 8 covering tests
  (commits `924c132` / `4d4005b` on `feat/collection-company-config-08-verify-gaps`).
  Those UNTESTED rows are **not** open work
- `reviewGate` absent; archive proceeded under ordinary repository policy
- `state.yaml` notes about FAIL (if any older snapshot) are stale; the file as moved
  already records re-verify PASS WITH WARNINGS and Phase 8 close-out

Attributed snapshot history (not current state):

- Per `verify-report` at re-verification time: WARNING list of design/TDD deviations
  (migrate folder `19.0.1.17.0` not `1.16.0`; snapshot `precompute=True`; helper on
  `sheet.create`; catalog ACL in WU1; some RED already-green). Orchestrator final-state
  facts: not CRITICAL; do not treat as still-open work
- Per `verify-report` assertion quality: 2 WARNING source-scan `sudo()` checks
  (companion `_call` tests still assert live behavior). Not CRITICAL

## Spec sync

Performed **before** the folder move. Existing main specs were merged in place (ADDED
append; MODIFIED replace full matching `### Requirement:` block). No new main-spec
domain was created from a delta copy.

| Domain                | Action  | Details                                                                   |
| --------------------- | ------- | ------------------------------------------------------------------------- |
| `collection-vouchers` | Updated | 6 added, 9 modified, 0 removed; 16 other preserved (25 → 31 requirements) |
| `collection-sheets`   | Updated | 3 added, 6 modified, 0 removed; 5 other preserved (11 → 14 requirements)  |
| `seller-lookup`       | Updated | 1 added, 0 modified, 0 removed; 5 other preserved (5 → 6 requirements)    |
| `document-review`     | Updated | 1 added, 1 modified, 0 removed; 14 other preserved (15 → 16 requirements) |

### collection-vouchers — `openspec/specs/collection-vouchers/spec.md`

| Action   | Requirement                                         |
| -------- | --------------------------------------------------- |
| ADDED    | Collection Settings persistence                     |
| ADDED    | Company ownership of vouchers                       |
| ADDED    | Enabled seller and allowed type on new voucher work |
| ADDED    | Historical vouchers remain operable                 |
| ADDED    | Cross-company document_id reject not replay         |
| ADDED    | Upgrade stamps voucher company and seeds settings   |
| MODIFIED | Voucher sequence naming                             |
| MODIFIED | Authorization for internal users                    |
| MODIFIED | Payment document_id uniqueness                      |
| MODIFIED | MCP optional payment attachment on create           |
| MODIFIED | MCP tool create_collection_vouchers                 |
| MODIFIED | Voucher seller field                                |
| MODIFIED | Create auto-assign to open sheet                    |
| MODIFIED | Immutable review snapshots and ACL                  |
| MODIFIED | MCP nested provenance on all-new create             |
| REMOVED  | none                                                |
| RENAMED  | none                                                |

Preserved (not in delta): Mail thread and activities; Deferred integrations not
required; Concurrent and stale review attempts; Attachment replacement resets review to
pending; Voucher fields and defaults; Voucher lifecycle; Payment field contract; Payment
Vouchers UI; Unsupported vouchers remain persistable; Optional image or PDF attachment
per voucher; Attachment widgets on Payment Vouchers views; Destructive reset of legacy
header and line data; Designated proof is message_main_attachment_id; Pre-upgrade
migration of Binary proofs; Typed provenance copies of payment fields; Additive upgrade
without provenance backfill.

### collection-sheets — `openspec/specs/collection-sheets/spec.md`

| Action   | Requirement                                        |
| -------- | -------------------------------------------------- |
| ADDED    | Company ownership of sheets                        |
| ADDED    | Historical sheets remain operable                  |
| ADDED    | Upgrade stamps sheet company and sequences         |
| MODIFIED | Sheet sequence identity                            |
| MODIFIED | Sheet seller and same-seller invariant             |
| MODIFIED | Create sheet Action                                |
| MODIFIED | Authorization for internal users                   |
| MODIFIED | Open/closed lifecycle                              |
| MODIFIED | At most one open sheet per seller (new operations) |
| REMOVED  | none                                               |
| RENAMED  | none                                               |

Preserved (not in delta): Membership, dates, and deletion; Collection Sheets UI; Mail
thread and activities; Saved-sheet header action opens Document Review; Closed sheet
membership freeze.

### seller-lookup — `openspec/specs/seller-lookup/spec.md`

| Action   | Requirement                                            |
| -------- | ------------------------------------------------------ |
| ADDED    | Lookup ignores enabled sellers and company allow-lists |
| MODIFIED | none                                                   |
| REMOVED  | none                                                   |
| RENAMED  | none                                                   |

Preserved (not in delta): Read-only MCP tool get_seller_id; Caller authorization; Fail
closed on empty or invalid mobile; Phone-only AR WhatsApp identity; Unique internal
match or fail closed.

### document-review — `openspec/specs/document-review/spec.md`

| Action   | Requirement                          |
| -------- | ------------------------------------ |
| ADDED    | Review snapshots isolated by company |
| MODIFIED | Per-company Document Review flag     |
| REMOVED  | none                                 |
| RENAMED  | none                                 |

Preserved (not in delta): Eligible review queue; OWL client loads real ORM data;
Authenticated binary attachment viewer; Viewer fit and cursor-anchored zoom; Viewer
rotation; Approve and reject without mocks; Document Review authorization; Document
Review menu and RPCs when flag is off; Sheet identifier required on review operations;
Three-way raw, seller, and current comparison; Queue payload includes readonly
provenance; Document Review decisions append immutable snapshots; Repeated Document
Review appends another revision; Voucher review history is visible.

## Mechanical archive

- Method: `git mv` succeeded (change folder was tracked; 11 files)
- Archive path: `openspec/changes/archive/2026-08-19-collection-company-configuration/`
- Active path removed: `openspec/changes/collection-company-configuration/` no longer
  exists
- Pre-move snapshot vs archive `diff -r`: empty (byte-identical); `DIFF_STATUS=0`
- Archive-report is additive after the move and excluded from the snapshot comparison
- `state.yaml` moved as-is (`phase: archive`; notes already record re-verify PASS WITH
  WARNINGS); not rewritten after the move

### Verbatim `diff -r` readback (Step 3 — snapshot vs archive)

```
=== DIFF snapshot vs archive ===
DIFF_STATUS=0
```

(empty — no differences)

## Archive contents

- proposal.md ✅
- design.md ✅
- exploration.md ✅
- specs/collection-vouchers/spec.md ✅
- specs/collection-sheets/spec.md ✅
- specs/seller-lookup/spec.md ✅
- specs/document-review/spec.md ✅
- tasks.md ✅ (15/15 implementation tasks complete)
- verify-report.md ✅
- apply-progress.md ✅
- state.yaml ✅ (moved as-is; phase `archive`)
- archive-report.md ✅ (this file; additive after move)

## Verification at close

| Check                        | Result                                                                                       |
| ---------------------------- | -------------------------------------------------------------------------------------------- |
| Main specs updated           | yes (4 domains merged; 11 added / 16 modified / 0 removed; unrelated requirements preserved) |
| Change folder in archive     | yes                                                                                          |
| Active change path gone      | yes                                                                                          |
| tasks.md unchecked items     | none                                                                                         |
| `diff -r` empty              | yes (Step 3 snapshot vs archive empty; `DIFF_STATUS=0`)                                      |
| Application Python/XML/tests | not edited by archive                                                                        |
| Attempt token                | not settled (orchestrator owns settle)                                                       |

## Engram

OpenSpec-only persistence. `mem_save` not used (Engram unavailable).

## Out of scope at close

- Application Python/XML/tests were not edited by archive
- Nebula-agent was out of this change
- Warnings at close (not open work): migrate folder `19.0.1.17.0` not `1.16.0`; snapshot
  `precompute=True`; helper on `sheet.create`; catalog ACL in WU1; some RED
  already-green

## SDD cycle

Fully planned, implemented, verified (`pass_with_warnings`), and archived. Ready for the
next change.
