# Archive Report: sheet-form-allocations-only

**Change**: `sheet-form-allocations-only` **Archived**: 2026-09-02 **Artifact store**:
openspec **Skill resolution**: paths-injected **Engram**: skipped by orchestrator
instruction (`openspec` mode; do not call `mem_save`) **Work unit**: `archive-close`

## Final-state authority

Ranked sources at close (most authoritative first):

1. **Native review authority**: `reviewGate` is structurally **absent**. Archive
   proceeds under ordinary policy. There is no receipt to read or block on.
2. **Persisted tasks artifact**: archived `tasks.md` 12/12 `[x]`; zero `- [ ]`
   implementation tasks. Task Completion Gate passed before spec merge.
3. **Orchestrator launch prompt (2026-09-02)**: `applyState: all_done`;
   `taskProgress: 12/12 complete, allComplete true`; `dependencies.archive: ready`;
   `nextRecommended: archive`. Verify at close: `pass` (not `pass_with_warnings`);
   envelope requirements 2/2, scenarios 11/11, `test_exit_code` 0, 509/509 tests.
   Implementation on disk (uncommitted): `AGENTS.md`, `models/collection_sheet.py`,
   `views/collection_views.xml`, `tests/test_collection_ui.py`,
   `tests/test_collection_sheet.py`, plus this change folder. Orchestrator will commit
   after archive. No CRITICAL findings.
4. **`verify-report.md` (verification-time snapshot)**: verdict `pass`; blockers 0;
   `critical_findings: 0`; requirements 2/2; scenarios 11/11; collection suite 509
   passed. Used as historical evidence of the passing envelope; final numbers match the
   orchestrator close facts, so they are restated as current.

## Gates

| Gate                                      | Result                                 |
| ----------------------------------------- | -------------------------------------- |
| Native Review Receipt                     | Absent — proceed under ordinary policy |
| Task Completion                           | Pass — 12/12 `[x]`                     |
| CRITICAL in verify-report                 | Pass — 0 CRITICAL                      |
| `rules.archive` destructive-delta warning | Recorded below — do not stop           |

## Spec merge (before folder move)

Deltas merged into existing main specs. Requirements not named in the delta were
preserved. MODIFIED blocks replaced the matching named requirement entirely, including
all scenarios. No ADDED, REMOVED, or RENAMED sections.

`(Previously: …)` lines from the deltas were **kept** in main specs. Project convention
from archived merges (`customer-partner-binding`, `collection-allocations`) retains
those lines as requirement history.

### collection-sheets

| Action   | Requirement                                                                                                                                                               |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| MODIFIED | Sheet form notebook — allocations-only page with Customer; no `voucher_ids`; counted Vouchers action for saved sheets; unsaved hide/refuse; unlink via voucher `sheet_id` |

### collection-vouchers

| Action   | Requirement                                                                                                                                                                          |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| MODIFIED | Payment Vouchers UI — list/form/search expose `sheet_id`; kanban does not; clear `sheet_id` unlinks open membership; closed-sheet writes rejected; no sheet-form voucher member list |

### `rules.archive` destructive / backward-incompatible warning

This merge is **requirement replacement**, not a large deletion. UI contract change:

- Sheet form no longer notebooks `voucher_ids`; membership is voucher `sheet_id`.
- Payment Vouchers list/form/search gain `sheet_id`; sheet member list is not a voucher
  UI surface.

Archive proceeded without asking the orchestrator to stop (launch prompt: proceed).

## Mechanical move

- Source: `openspec/changes/sheet-form-allocations-only/`
- Destination: `openspec/changes/archive/2026-09-02-sheet-form-allocations-only/`
- Method: `git mv` failed (`fatal: source directory is empty` — untracked change
  folder); fallback `mv` succeeded.
- Pre-move recursive snapshot vs archived folder `diff -r`: **empty** (status 0).
- Active change path is gone.
- `archive-report.md` is additive after the move and was excluded from that diff.

Verbatim `diff -r` evidence:

```text
DIFF_R_BEGIN
DIFF_R_END status=0
```

## Archive contents

- proposal.md
- specs/collection-sheets/spec.md
- specs/collection-vouchers/spec.md
- design.md
- tasks.md (12/12 complete)
- verify-report.md
- apply-progress.md
- exploration.md
- state.yaml
- archive-report.md (this file; written after move)

## Shipped behavior at close

Allocations-only sheet form plus counted Vouchers stat button; voucher `sheet_id` on
list/form/search. Verify **PASS**. 12/12 tasks complete. Main specs synced.

## Source of truth after close

- `openspec/specs/collection-sheets/spec.md`
- `openspec/specs/collection-vouchers/spec.md`

The SDD cycle for `sheet-form-allocations-only` is complete: planned, implemented,
verified, and archived.
