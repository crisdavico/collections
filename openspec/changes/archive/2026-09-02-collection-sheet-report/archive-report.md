# Archive Report: collection-sheet-report

**Archived**: 2026-09-02
**Change**: `collection-sheet-report`
**Store**: openspec (filesystem only; Engram not used — `mem_save` skipped)
**Status**: success
**Next**: none
**reviewGate**: structurally absent (no review discovered; archive proceeded under ordinary policy)

## Final state at close

The collection sheet report shipped. Specs are in main, the change folder is archived, and verification closed as `pass_with_warnings` with zero blockers and zero CRITICAL findings.

These facts outrank intermediate `apply-progress` / `verify-report` snapshots. Launch-prompt final-state facts and persisted `tasks.md` agree; warnings at verify time remain warnings at close (no later fix commits, and they did not become CRITICAL).

| Fact | Value | Authority |
| ---- | ----- | --------- |
| Implementation tasks | 10/10 `[x]`; pending 0 | persisted `tasks.md` (1.1–4.2) |
| Verify verdict | `pass_with_warnings`; blockers 0; critical_findings 0 | launch final-state + `verify-report.md` envelope |
| Requirements / scenarios (this change) | 11/11, 26/26 (report 10/21 + allocations ADDED 1/5) | launch final-state + `verify-report.md` header |
| Gate | `invoke test -m collection --mode=update` exit 0; **0 failed, 0 error(s) of 597 tests** | launch final-state + `verify-report.md` |
| Pre-commit | scoped collection files exit 0 | launch final-state + `verify-report.md` |
| Collection version shipped | `19.0.1.30.0` | launch final-state |
| Implementation on disk | report package, payload inherit, XLSX | launch final-state |

CRITICAL findings: none. Archive was not blocked.

Open non-critical warnings at close (still true; not CRITICAL):

1. Optional wkhtmltopdf PDF render and browser Print-menu smoke were skipped at verification time (TransactionCase already covers `_render_qweb_html` and XLSX `PK`/zip).
2. Inherit xpath for `document_kind` was asserted from disk XML rather than a live upgraded arch.
3. Safety Net was N/A on some additive edits.

## Task Completion Gate

Inspected `openspec/changes/collection-sheet-report/tasks.md` before merge/move. Zero `- [ ]` implementation tasks. Phases 1–4 (1.1–4.2) are all `[x]`. Gate passed; no archive-time checkbox reconciliation. Archived `tasks.md` still has zero unchecked implementation tasks.

## Native Review Receipt Gate

Structured status `reviewGate` is structurally absent. No review transaction/ledger/receipt was read. Archive proceeded under ordinary repository policy. No review was started. No receipt was invented.

## Destructive / backward-incompatible deltas

`openspec/config.yaml` `rules.archive` requires a warning before merging destructive or backward-incompatible deltas. This change had no REMOVED, RENAMED, or MODIFIED sections. Deltas were:

- Full new capability `collection-sheet-report` (create main spec).
- ADDED-only `collection-allocations` (append; existing draft-until-close language preserved).

No destructive merge.

## Specs synced to source of truth

| Domain | Action | Details |
| ------ | ------ | ------- |
| collection-sheet-report | Created | Mechanical `mktemp` + `cp` + empty `diff -r` + `mv`. Full spec. 10 requirements, 21 scenarios. Main spec did not exist. |
| collection-allocations | Updated | ADDED 1 (`Allocation line document_kind`) with 5 scenarios. REMOVED 0. MODIFIED 0. RENAMED 0. Existing requirements including draft-until-close were preserved. |

Main spec paths:

- `openspec/specs/collection-sheet-report/spec.md`
- `openspec/specs/collection-allocations/spec.md`

Preserved on `collection-allocations` (not in this delta): MCP create_collection_allocation; Idempotency and amend; Input and sheet gates; Revalidation and residual; Freeze, revisions, ACL, back-office; Source detach residual refuse; Partner match after voucher write; MCP get_collection_allocation; Draft default and confirm-on-close invariant; Draft unlink with revisions.

## Mechanical move

- Change folder was **untracked**. `git mv` failed with `fatal: source directory is empty`. Fallback `mv` succeeded.
- Archive path: `openspec/changes/archive/2026-09-02-collection-sheet-report/`
- Active path `openspec/changes/collection-sheet-report/` is gone after the move.
- Pre-move recursive snapshot compared with `diff -r`. Empty diff (exit 0). This report is additive and was written after that comparison.

Sibling archives were not edited: `2026-09-02-draft-until-close`, `2026-09-02-seller-commission-percent`, `2026-09-02-inline-collection-allocation`, `2026-09-02-sheet-form-allocations-only`, `2026-09-02-voucher-customer-reassign`. `.codegraph/` and other untracked noise were not deleted.

## Archive contents

- proposal.md
- exploration.md
- design.md
- tasks.md (10/10 complete; no unchecked implementation tasks)
- specs/collection-sheet-report/spec.md
- specs/collection-allocations/spec.md
- apply-progress.md
- verify-report.md
- state.yaml
- archive-report.md (this file; additive after move)

## Attempt

Parent holds the archive acquire token `sha256:e3e3dd6e0f88a7c5a9fd7783b47db6a08c508e35d205a456566ea64f042917e8` for work-unit `archive`. This executor did not call `sdd-attempt acquire` or `settle`.

## Risks at close

- Verify warnings (wkhtmltopdf/browser Print smoke skipped; inherit xpath from disk XML; Safety Net N/A on additive edits) remain open and non-CRITICAL.
- None of those warnings later became CRITICAL; there were no post-verify fix commits.
