# Archive Report: collection-sheets

**Date**: 2026-08-17
**Change**: collection-sheets
**Archived to**: `openspec/changes/archive/2026-08-17-collection-sheets/`
**Artifact store**: openspec
**Status**: success
**Intentional warnings**: yes (verify `pass_with_warnings` — zero CRITICAL; settings-menu WIP remains out of this change)

## Gates

| Gate | Result | Evidence |
| ---- | ------ | -------- |
| Task Completion | PASS | Archived `tasks.md` — no `- [ ]`; tasks 1.1–4.4 all `[x]` (18/18) |
| Native Review Receipt | PASS (absent) | `reviewGate` structurally absent; archive proceeded under ordinary repository policy; no receipt demanded |
| CRITICAL in verify-report | PASS | `critical_findings: 0`, blockers: 0; verdict `pass_with_warnings` |
| Destructive delta | PASS (not destructive) | `rules.archive`: warn before merging destructive deltas. This change ADDED one voucher requirement and MODIFIED MCP `create_collection_vouchers`; no REMOVED/RENAMED. Full `collection-sheets` spec created. No destructive merge. |

## Final-state authority

Per orchestrator launch facts (outrank stale `verify-report` / `apply-progress` pending claims):

- All tasks 1.1–4.4 complete in `tasks.md` (no `- [ ]`)
- Verify at close: `pass_with_warnings`; 8/8 requirements; 23/23 scenarios; `invoke test -m collection --mode=update` exit 0 (166/166). No CRITICAL findings
- Flag-off isolation is committed: `6cc16f0` on `feat/collection-sheets-05-test-isolation` (`[FIX] collection: isolate Document Review flag-off tests from company state`). Do not treat the verify-report warning that isolation was uncommitted as current state
- Settings-menu WIP remains unstaged (`tests/test_collection_ui.py` extra settings tests, `views/res_config_settings_views.xml`) and is **out of this change**. Suite 166 vs apply-progress 164 is because that WIP is still in the working tree; it is not part of archive close
- Stacked branches not pushed
- Nebula-agent not updated (intentional follow-up)
- Manifest `19.0.1.10.0`
- `reviewGate` absent (review kill switch may be on but no receipt was started)

Attributed snapshot history (not current state):

- Per `apply-progress` at PR4 time: official runner 12 failed / 164 tests (pre-existing flag-off failures); remaining-tasks sections from earlier PR slices are superseded by tasks 1.1–4.4 `[x]`
- Per `verify-report` at verification time: isolation edits were uncommitted relative to `71cbf1a`; that warning is superseded by commit `6cc16f0`

## Spec sync

Performed **before** the folder move.

**Domain**: `collection-sheets`
**Main spec**: `openspec/specs/collection-sheets/spec.md` (did not exist; mechanical full-spec copy)

| Action | Requirement |
| ------ | ----------- |
| Created | Full spec copied via mktemp + `cp` + `diff -r` + `mv` (6 requirements / 12 scenarios) |
| ADDED | n/a (delta was the full spec) |
| MODIFIED | none |
| REMOVED | none |
| RENAMED | none |

**Domain**: `collection-vouchers`
**Main spec**: `openspec/specs/collection-vouchers/spec.md` (existing; requirements not named in the delta preserved)

| Action | Requirement |
| ------ | ----------- |
| ADDED | Voucher seller field (4 scenarios) |
| MODIFIED | MCP tool create_collection_vouchers — replaced entire matching block (required top-level `seller_id`; stamp all-new only; exact replay must not mutate, including legacy null seller) |
| REMOVED | none |
| RENAMED | none |

Preserved unchanged: Voucher sequence naming; Mail thread and activities; Authorization for internal users; Deferred integrations not required; Payment document_id uniqueness; MCP optional payment attachment on create; Concurrent and stale review attempts; Attachment replacement resets review to pending; Voucher fields and defaults; Voucher lifecycle; Payment field contract; Payment Vouchers UI; Unsupported vouchers remain persistable; Optional image or PDF attachment per voucher; Attachment widgets on Payment Vouchers views; Destructive reset of legacy header and line data. Purpose line unchanged. RFC 2119 / Given-When-Then retained.

## Mechanical archive

- Method: `git mv openspec/changes/collection-sheets` → `openspec/changes/archive/2026-08-17-collection-sheets` succeeded (tracked `tasks.md` / `apply-progress.md` recorded as rename; previously untracked artifacts landed in the archive folder)
- Archive path: `openspec/changes/archive/2026-08-17-collection-sheets/`
- Active path removed: `openspec/changes/collection-sheets/` no longer exists
- Pre-move snapshot vs archive `diff -r`: empty (byte-identical); `DIFF_STATUS=0`
- Archive-report is additive after the move and excluded from the snapshot comparison
- `state.yaml` updated after the empty `diff -r` to `phase: archived`

### Verbatim `diff -r` readback (Step 2 — collection-sheets spec copy)

Source vs temp (mktemp), then source vs final `openspec/specs/collection-sheets/spec.md`. Empty output; `diff_exit=0` both times.

```
=== DIFF collection-sheets spec copy (source vs temp) ===
diff_exit=0
=== DIFF collection-sheets spec copy (source vs final) ===
diff_exit=0
```

### Verbatim `diff -r` readback (Step 2 — collection-vouchers merge)

In-place heading-matched merge into the existing main spec (not a mechanical full-spec overwrite).

```
(n/a — existing main spec edited; ADDED appended; MCP requirement replaced; other requirements preserved)
```

### Verbatim `diff -r` readback (Step 3 — snapshot vs archive)

```
(empty — no differences)
```

`DIFF_STATUS=0`

## Archive contents

- proposal.md ✅
- design.md ✅
- exploration.md ✅
- specs/collection-sheets/spec.md ✅
- specs/collection-vouchers/spec.md ✅
- tasks.md ✅ (18/18 implementation tasks complete)
- verify-report.md ✅
- apply-progress.md ✅
- state.yaml ✅ (updated after move; phase `archived`)
- archive-report.md ✅ (this file; additive after move)

## Verification at close

| Check | Result |
| ----- | ------ |
| Main specs updated | yes (`collection-sheets` created 6 req / 12 sc; `collection-vouchers` 1 ADDED + 1 MODIFIED; 16 preserved) |
| Change folder in archive | yes |
| Active change path gone | yes |
| tasks.md unchecked items | none |
| `diff -r` empty | yes (Step 2 spec copy empty; Step 3 snapshot vs archive empty; `DIFF_STATUS=0`) |
| Settings-menu WIP | not touched (`tests/test_collection_ui.py`, `views/res_config_settings_views.xml` still dirty) |
| Isolation tests | not reverted/edited (`6cc16f0` remains HEAD) |
| Attempt token | not settled (orchestrator owns PR6 commit) |

## Engram

Engram unavailable for this session — MCP server `user-engram` not found. `mem_save` for `sdd/collection-sheets/archive-report` skipped per orchestrator instruction. OpenSpec filesystem artifacts are the audit trail.

## Out of scope at close

- Settings-menu WIP remains unstaged and is not part of this change
- Stacked feature branches are not pushed
- Nebula-agent is not updated (intentional follow-up consumer)

## SDD cycle

Fully planned, implemented, verified (`pass_with_warnings`), and archived. Ready for the next change.
