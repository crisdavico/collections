# Archive Report: voucher-customer-reassign

**Change**: `voucher-customer-reassign`
**Archived**: 2026-09-02
**Artifact store**: openspec
**Skill resolution**: paths-injected
**Engram**: skipped by orchestrator instruction (`openspec` mode; do not call
`mem_save`)
**Work unit**: `archive-close`

## Final-state authority

Ranked sources at close (most authoritative first):

1. **Native review authority**: `reviewGate` is structurally **absent**. Archive
   proceeds under ordinary policy. There is no receipt to read or block on.
2. **Persisted tasks artifact**: archived `tasks.md` 15/15 `[x]`; zero `- [ ]`
   implementation tasks. Task Completion Gate passed before spec merge.
3. **Orchestrator launch prompt (2026-09-02)**: `applyState: all_done`;
   `taskProgress: 15/15 complete`; `dependencies.archive: ready`;
   `nextRecommended: archive`. Verify at close: PASS; envelope requirements
   7/7, scenarios 22/22, `test_exit_code` 0, 530/530 tests, 0 CRITICAL. Module
   upgrade exit 0. Suggestions in `verify-report` (pylint C8101, OCR
   field-label warnings, docstring) were **not** fixed later — they remain
   suggestions only, not blockers. Implementation is uncommitted on branch
   `main`; orchestrator will commit after archive.
4. **`verify-report.md` (verification-time snapshot)**: verdict `pass`; blockers
   0; `critical_findings: 0`; requirements 7/7; scenarios 22/22; collection
   suite 530 passed. Used as historical evidence of the passing envelope; final
   numbers match the orchestrator close facts, so they are restated as current.
   Suggestion items remain suggestions at close (not later remediations).

## Gates

| Gate | Result |
|------|--------|
| Native Review Receipt | Absent — proceed under ordinary policy |
| Task Completion | Pass — 15/15 `[x]` |
| CRITICAL in verify-report | Pass — 0 CRITICAL |
| `rules.archive` destructive-delta warning | Recorded below — do not stop |

## Spec merge (before folder move)

Deltas merged into existing main specs. Requirements not named in the delta were
preserved. ADDED blocks were appended. MODIFIED blocks replaced the matching
named requirement entirely, including all scenarios. No REMOVED or RENAMED
sections.

`(Previously: …)` lines from the deltas were **kept** in main specs. Project
convention from archived merges (`customer-partner-binding`,
`collection-allocations`, `sheet-form-allocations-only`) retains those lines as
requirement history.

### collection-vouchers

| Action | Requirement |
|--------|-------------|
| ADDED | Partner write follows allocation |
| ADDED | Voucher partner-allocation constrain |
| ADDED | Context-gated partner group_expand |

### collection-allocations

| Action | Requirement |
|--------|-------------|
| ADDED | Source detach residual refuse |
| ADDED | Partner match after voucher write |

### collection-sheets

| Action | Requirement |
|--------|-------------|
| ADDED | Reassign header action and kanban |
| MODIFIED | Closed sheet membership freeze — includes voucher `partner_id`; closed writes reuse membership `UserError` |

### `rules.archive` destructive / backward-incompatible warning

This merge is **requirement replacement plus additive requirements**, not a
large deletion. Behavior change:

- Closed-sheet freeze now covers Customer (`partner_id`) as well as membership
  / `sheet_id`. Closed `partner_id` writes raise the same membership
  `UserError`.
- Open-sheet `partner_id` write follows allocation in the same vals; fully
  applied / negative projected residual sources refuse the move.

Archive proceeded without asking the orchestrator to stop (launch prompt:
proceed).

## Mechanical move

- Source: `openspec/changes/voucher-customer-reassign/`
- Destination: `openspec/changes/archive/2026-09-02-voucher-customer-reassign/`
- Method: `git mv` failed (`fatal: source directory is empty` — untracked
  change folder); fallback `mv` succeeded.
- Pre-move recursive snapshot vs archived folder `diff -r`: **empty**
  (status 0).
- Active change path is gone.
- Sibling archive `2026-09-02-sheet-form-allocations-only/` left untouched.
- `archive-report.md` is additive after the move and was excluded from that
  diff.

Verbatim `diff -r` evidence:

```text
DIFF_R_BEGIN
DIFF_R_END status=0
```

## Archive contents

- proposal.md
- specs/collection-vouchers/spec.md
- specs/collection-allocations/spec.md
- specs/collection-sheets/spec.md
- design.md
- tasks.md (15/15 complete)
- verify-report.md
- apply-progress.md
- exploration.md
- state.yaml
- archive-report.md (this file; written after move)

## Shipped behavior at close

Open-sheet header **Reassign Customers** opens a dedicated customer-grouped
kanban; drop writes Customer and re-attaches a confirmed same-sheet allocation
when residual holds, else unallocated plus chatter. Closed `partner_id` reuses
membership `UserError`. Verify **PASS**. 15/15 tasks complete. Main specs
synced. Suggestions remain suggestions (pylint C8101, OCR field-label
warnings, docstring).

## Source of truth after close

- `openspec/specs/collection-vouchers/spec.md`
- `openspec/specs/collection-allocations/spec.md`
- `openspec/specs/collection-sheets/spec.md`

The SDD cycle for `voucher-customer-reassign` is complete: planned,
implemented, verified, and archived.
