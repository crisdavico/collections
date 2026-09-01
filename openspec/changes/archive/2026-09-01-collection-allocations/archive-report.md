# Archive Report: collection-allocations

**Change**: `collection-allocations`
**Archived**: 2026-09-01
**Artifact store**: openspec
**Skill resolution**: paths-injected
**Engram**: unavailable — `mem_save` skipped; this file is the closure record
**Work unit**: `archive-close`

## Final-state authority

Ranked sources at close (most authoritative first):

1. **Native review authority**: `reviewGate` is structurally **absent** (no
   review discovered). Archive proceeds under ordinary policy. There is no
   receipt to read or block on.
2. **Persisted tasks artifact**: archived `tasks.md` 15/15 `[x]`; zero `- [ ]`
   implementation tasks. Task Completion Gate passed before spec merge.
3. **Orchestrator launch prompt (2026-09-01)**: `applyState: all_done`;
   `taskProgress: 15/15 complete, allComplete true`; `dependencies.archive:
   ready`; user explicitly instructed archive after verify **PASS WITH
   WARNINGS** (CRITICAL: none). WARNINGs are documented design deviations, not
   blockers.
4. **`verify-report.md` (verification-time snapshot)**: verdict
   `pass_with_warnings`; **CRITICAL**: None; requirements 8/8; scenarios 14/14;
   collection suite 502 passed / 0 failed. Used as historical evidence of the
   passing run, not as a claim that WARNINGs remain live blockers.

This archive **is** the close. Do not treat earlier orchestrator or
`state.yaml` text that still named a next archive launch as current.

## Gates

| Gate | Result |
|------|--------|
| Native Review Receipt | Absent — proceed under ordinary policy |
| Task Completion | Pass — 15/15 `[x]` |
| CRITICAL in verify-report | Pass — **CRITICAL**: None; verdict PASS WITH WARNINGS |
| `rules.archive` destructive-delta warning | Recorded below — do not stop |

## Spec merge (before folder move)

### collection-allocations

Main spec did **not** exist. Mechanical shell copy of the full spec (not a
delta) to `openspec/specs/collection-allocations/spec.md`. Bytes did not pass
through model Read→Write. Pre-`mv` `diff -r` of source vs temp was empty
(status 0).

Verbatim `diff -r` evidence (new spec copy):

```text
DIFF_R_BEGIN
DIFF_R_END status=0
```

| Action | Requirement |
|--------|-------------|
| Created | MCP create_collection_allocation |
| Created | Idempotency and amend |
| Created | Input and sheet gates |
| Created | Revalidation and residual |
| Created | Freeze, revisions, ACL, back-office |

### collection-vouchers

Delta was `## ADDED Requirements` only. Appended to the existing main spec.
All other requirements were preserved. No MODIFIED / REMOVED / RENAMED.

| Action | Requirement |
|--------|-------------|
| ADDED | Voucher allocation membership |

### collection-sheets

Delta had `## ADDED` plus `## MODIFIED` "Membership, dates, and deletion"
(copy-full-then-edit). Appended ADDED; replaced the matching MODIFIED
requirement with the full delta block including all scenarios. Every other
requirement not named in the delta was preserved.

| Action | Requirement |
|--------|-------------|
| ADDED | Sheet form notebook |
| MODIFIED | Membership, dates, and deletion (unlink restrict when allocated) |

### `rules.archive` destructive / backward-incompatible warning

Config `rules.archive` requires a warning before destructive or
backward-incompatible deltas. The MODIFIED "Membership, dates, and deletion"
block **narrows unlink**: empty sheets still unassign members; unlink **MUST
fail** when allocations exist (`ondelete="restrict"`). Previously, deleting
any sheet unassigned members regardless of allocations.

This narrowing is the intended verified behavior. Archive proceeded without
asking the orchestrator to stop. No large unrelated sections were removed.

## Mechanical move

- Source: `openspec/changes/collection-allocations/`
- Destination: `openspec/changes/archive/2026-09-01-collection-allocations/`
- Method: `git mv` failed (`fatal: source directory is empty` — untracked
  change folder); fallback `mv` succeeded.
- Pre-move recursive snapshot vs archived folder `diff -r`: **empty**
  (status 0).
- Active change path is gone.
- `archive-report.md` is additive after the move and was excluded from that
  diff.
- Leftover `openspec/changes/customer-partner-binding/` was not present at
  the active-changes path; it was not touched.

Verbatim `diff -r` evidence (folder move):

```text
DIFF_R_BEGIN
DIFF_R_END status=0
```

## Archive contents

- proposal.md
- specs/collection-allocations/spec.md
- specs/collection-vouchers/spec.md
- specs/collection-sheets/spec.md
- design.md
- tasks.md (15/15 complete)
- verify-report.md
- apply-progress.md
- exploration.md
- state.yaml
- archive-report.md (this file; written after move)

## Verification-time warnings (not current blockers)

Per `verify-report.md` at verification time (`pass_with_warnings`,
**CRITICAL**: None):

- Allocated-sheet delete uses `@api.ondelete` UserError in addition to
  `sheet_id ondelete="restrict"` (pylint E8140); spec still met.
- Amend persist keeps a placeholder `residual_reason` across `Command.clear()`
  flush so the confirmed residual constraint does not fire mid-write.
- Same-company UniqueViolation replay is exercised by missing the first
  `request_id` search then raising `UniqueViolation` from
  `_collection_allocation_write` (live UNIQUE(sheet, partner) hash-replays
  before insert).
- Sheet notebook Allocations nested `<list>` omits `partner_id` so the
  existing unbound-`partner_id` count on the sheet form stays one (voucher
  membership list).

These are documented design deviations. They are not archive blockers.

Optional verification-time suggestions (lint `C8101` manifest author;
duplicate OCR/seller field-label warnings; MuK MCP `exclusiveMinimum` drop
with Python still rejecting `amount_applied` ≤ 0; missing filestore blobs
during `load_menus`) remain snapshot comments, not open work.

## Source of truth after close

- `openspec/specs/collection-allocations/spec.md`
- `openspec/specs/collection-vouchers/spec.md`
- `openspec/specs/collection-sheets/spec.md`

At close: 15/15 tasks complete; verify PASS WITH WARNINGS; 502 tests passed;
8/8 requirements; 14/14 scenarios.

The SDD cycle for `collection-allocations` is complete: planned, implemented,
verified, and archived.
