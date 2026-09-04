# Archive Report: collection-sheet-workflow

**Archived**: 2026-09-03
**Change**: `collection-sheet-workflow`
**Store**: openspec (filesystem only; Engram not used)
**Status**: success
**reviewGate**: absent (no review started; archive proceeded under ordinary policy)

## Final state at close

These facts outrank intermediate `apply-progress` / `verify-report` snapshots.
`apply-progress` and the first verify attempt are history. A later independent
re-verify admitted `pass_with_warnings` and overwrote the fail report; that
admitted report is the verification artifact at close.

| Fact | Value | Authority |
| ---- | ----- | --------- |
| Implementation tasks | 18/18 `[x]` (1.1–5.2); pending 0 | persisted `tasks.md` |
| applyState | `all_done` | launch structured status + `tasks.md` |
| Verify verdict | `pass_with_warnings` | launch final-state (matches admitted verify-report envelope) |
| CRITICAL findings | 0 | launch final-state |
| Blockers | 0 | launch final-state |
| Module tests at close | `/collection` suite 682/682, `test_exit_code` 0, 0 failed | launch final-state (same as admitted verify-report) |
| Requirements / scenarios | 24/24, 99/99 | launch final-state (same as admitted verify-report) |
| Shipped manifest | `19.0.1.33.0` | admitted verify-report + launch |
| Nebula-agent | explicitly out of scope | proposal + launch |
| Docs-scanner remediation | `test_agents_md_four_state_workflow` collapses whitespace (`" ".join(agents.split())`) so prettier `proseWrap` of `one-open still \`open\` only` no longer fails the scanner | launch final-state (post-fail maintainer fix; admitted re-verify) |

CRITICAL findings: none. Archive was not blocked. Versions were not bumped at
archive.

Do not treat the superseded fail report (1/682) as current. That run was
before the AGENTS.md docs-scanner whitespace collapse. The admitted
`pass_with_warnings` report is the close-time verification record.

## Task Completion Gate

Inspected `openspec/changes/collection-sheet-workflow/tasks.md` before merge/move.
Zero `- [ ]` implementation tasks. Phases 1–5 (1.1–5.2) are all `[x]` (18/18).
Gate passed; no archive-time checkbox reconciliation.

## Native Review Receipt Gate

Structured status `reviewGate` is structurally absent. No review
transaction/ledger/receipt was read. Archive proceeded under ordinary
repository policy. A post-verify offer, if any, was not a gate.

## Destructive / backward-incompatible deltas (warned; archive proceeded)

`openspec/config.yaml` `rules.archive` requires a warning before merging
destructive or backward-incompatible deltas. The orchestrator launched archive
with these facts already known. They were merged; they were not re-asked.

1. **Four-state sheet replaces open/closed + Reopen.** Legal transitions are
   Confirm / Close / Cancel / Open. Reopen MUST NOT exist. Membership freeze
   and unlink-refuse extend to `proposal` and `cancelled`, not only `closed`.
2. **REMOVED `Reassign header action and kanban`** (`collection-sheets`).
   Reason: customer reassignment moves to ordinary voucher and allocation
   edits. Migration: delete the reassign header action and kanban XMLID on
   upgrade; unassign `allocation_id` before changing voucher Customer.
3. **REMOVED `Context-gated partner group_expand`** (`collection-vouchers`).
   Reason: Reassign kanban is gone; `group_expand` existed only for that UI.
   Migration: remove `_read_group_partner_ids` and
   `collection_reassign_sheet_id`.
4. **Partner write no longer auto-follows allocation.** An allocated voucher
   MUST be unassigned before Customer MAY change.

No large unrelated requirement blocks were deleted. Five `collection-sheets`
requirements that were not named in the delta were preserved byte-identical.

## Specs synced to source of truth

Delta specs merged into existing main specs. Requirements not named in a delta
were preserved (byte-identical vs pre-merge snapshot after splice). MODIFIED
blocks were replaced with the delta’s full requirement text (byte-identical to
the delta). ADDED blocks were appended. REMOVED blocks were deleted from the
matching main spec after Reason/Migration was recorded here.

`collection-sheets` already existed under `openspec/specs/collection-sheets/spec.md`
(Glob/listing tools hid some spec dirs; the merge confirmed the file on disk).
It was updated, not created.

| Domain | Action | Details |
| ------ | ------ | ------- |
| collection-sheets | Updated | ADDED 2 (`Confirm review gate`, `Four-state sheet editability`); MODIFIED 10 (`Sheet sequence identity`, `Membership, dates, and deletion`, `Collection Sheets UI`, `Mail thread and activities`, `Saved-sheet header action opens Document Review`, `Open/closed lifecycle`, `At most one open sheet per seller (new operations)`, `Closed sheet membership freeze`, `Historical sheets remain operable`, `Sheet form notebook`); REMOVED 1 (`Reassign header action and kanban`); RENAMED 0. Preserved 5 (`Sheet seller and same-seller invariant`, `Create sheet Action`, `Authorization for internal users`, `Company ownership of sheets`, `Upgrade stamps sheet company and sequences`). |
| collection-vouchers | Updated | ADDED 1 (`Sheet-state voucher field guards`); MODIFIED 2 (`Payment Vouchers UI`, `Partner write follows allocation`); REMOVED 1 (`Context-gated partner group_expand`); RENAMED 0. |
| collection-allocations | Updated | ADDED 2 (`Cancelled and Closed allocation write guards`, `MCP open sheet is state open only`); MODIFIED 1 (`Draft default and confirm-on-close invariant`); REMOVED 0; RENAMED 0. |
| collection-sheet-report | Updated | ADDED 1 (`PDF and XLSX available in all sheet states`); MODIFIED 2 (`Sheet reconciliation inputs`, `XLSX workbook and percent scale`); REMOVED 0; RENAMED 0. |
| document-review | Updated | MODIFIED 1 (`Sheet identifier required on review operations`); ADDED 0; REMOVED 0; RENAMED 0. |

Main spec paths:

- `openspec/specs/collection-sheets/spec.md`
- `openspec/specs/collection-vouchers/spec.md`
- `openspec/specs/collection-allocations/spec.md`
- `openspec/specs/collection-sheet-report/spec.md`
- `openspec/specs/document-review/spec.md`

Untouched main specs (byte-identical to pre-merge snapshot):
`collection-connectors`, `seller-lookup`.

### Sibling changes (untouched)

`openspec/changes/voucher-states-ui/**` was not edited, moved, or deleted (no
active folder present at archive time).
`openspec/changes/archive/2026-09-03-allocation-customer-debt/**` and
`openspec/changes/archive/2026-09-03-voucher-states-ui/**` were not modified.
Only the new archive folder for this change was created.

## Known warnings at verification time (not current blockers)

Per admitted `verify-report` at verification time (not defects that reopened
the change):

1. TDD triangulation warning (5/6 checks); CSS-class asserts on sheet/allocation
   stat buttons (`oe_button_box` / `oe_stat_button`).
2. Frozen voucher chatter covers proposal and closed, not cancelled.
3. Iff invariant dedicated non-audited refuse is confirmed-on-open;
   draft-on-closed raw write is not a named test.
4. `_confirm()` test helper can persist confirmed allocations on an open sheet.
5. Suggestion: rename leftover `*_detach_*_succeeds` tests to `*_refused`.
6. Optional pylint C8101 author on manifest (not mandatory).

Verdict `pass_with_warnings`; 0 CRITICAL; 0 blockers. Archive allowed.

The AGENTS.md one-open scanner collapsing whitespace is the close-time scanner
behavior. It is not an open fail.

## Mechanical move

- Change folder was **untracked** (`??`). `git mv` failed with
  `fatal: source directory is empty, source=openspec/changes/collection-sheet-workflow, destination=openspec/changes/archive/2026-09-03-collection-sheet-workflow`.
  Fallback `mv` succeeded.
- Archive path: `openspec/changes/archive/2026-09-03-collection-sheet-workflow/`
- Active path `openspec/changes/collection-sheet-workflow/` is gone after the move.
- Pre-move recursive snapshot compared with `diff -r`. Empty diff (exit 0) for
  both the snapshot copy and the archive move. This report is additive and was
  written after those comparisons.
- `state.yaml` moved with the change folder. Orchestrator state was not rewritten
  here.

### Verbatim `diff -r` readback

Snapshot copy (`openspec/changes/collection-sheet-workflow` vs pre-move snapshot):

```
(empty — `diff -r` produced no stdout; exit 0)
```

Archive move (pre-move snapshot vs `openspec/changes/archive/2026-09-03-collection-sheet-workflow`):

```
(empty — `diff -r` produced no stdout; exit 0)
```

## Archive contents

- proposal.md
- exploration.md
- design.md
- tasks.md (18/18 complete; no unchecked implementation tasks)
- specs/collection-sheets/spec.md
- specs/collection-vouchers/spec.md
- specs/collection-allocations/spec.md
- specs/collection-sheet-report/spec.md
- specs/document-review/spec.md
- apply-progress.md
- verify-report.md (admitted `pass_with_warnings`; 682/682)
- state.yaml
- archive-report.md (this file; additive after move)

## Out of scope (untouched)

Per launch instructions, this archive did not touch sibling change folders,
prior archives except creating this folder, application code, tests, manifests,
`AGENTS.md`, `.codegraph/`, or Nebula-agent. No git commit.

## Risks at close

- Verify warnings above remain documentation/test-hygiene items; they do not
  reopen the cycle.
- `collection-allocations` Purpose still says “back-office validates or
  rejects.” That Purpose line was not an ADDED/MODIFIED/REMOVED requirement.
- Coordinated Nebula-agent remains out of scope.
