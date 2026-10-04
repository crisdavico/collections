# Archive Report: draft-until-close

**Archived**: 2026-09-02 **Change**: `draft-until-close` **Store**: openspec (filesystem
only; Engram not used) **Status**: success **reviewGate**: absent (kill switch off / no
review started; archive proceeded under ordinary policy)

## Final state at close

These facts outrank intermediate `apply-progress` / `verify-report` snapshots.

| Fact                  | Value                                                                               | Authority                                    |
| --------------------- | ----------------------------------------------------------------------------------- | -------------------------------------------- |
| Implementation tasks  | 13/13 `[x]` (1.1–6.2); pending 0                                                    | persisted `tasks.md` + launch final-state    |
| Verify verdict        | `pass_with_warnings`                                                                | launch final-state (outranks snapshot prose) |
| CRITICAL findings     | 0                                                                                   | launch final-state                           |
| Blockers              | 0                                                                                   | launch final-state                           |
| Module tests at close | `invoke test -m collection --mode=update` exit 0; 0 failed, 0 error(s) of 560 tests | launch final-state                           |
| Design-named version  | `19.0.1.28.0`                                                                       | launch final-state                           |
| Shipped manifest      | `19.0.1.29.0`                                                                       | launch final-state                           |
| Migrate folder        | `migrations/19.0.1.28.0/` (not bumped)                                              | launch final-state                           |
| Nebula-agent          | explicitly deferred; not incomplete work                                            | launch final-state                           |

CRITICAL findings: none. Archive was not blocked. Versions were not bumped at archive.

## Task Completion Gate

Inspected `openspec/changes/draft-until-close/tasks.md` before merge/move. Zero `- [ ]`
implementation tasks. Phases 1–6 (1.1–6.2) are all `[x]`. Gate passed; no archive-time
checkbox reconciliation.

## Native Review Receipt Gate

Structured status `reviewGate` is structurally absent. No review
transaction/ledger/receipt was read. Archive proceeded under ordinary repository policy.

Parent token `sha256:ae02cf024226dc8a5a981ab1f241e67dd7e28009a22227779fd038372cd48372`
was supplied by the orchestrator. This executor did not acquire it again and does not
settle.

## Destructive / backward-incompatible deltas (warned; archive proceeded)

`openspec/config.yaml` `rules.archive` requires a warning before merging destructive or
backward-incompatible deltas. The orchestrator launched archive with these facts already
known. They were merged; they were not re-asked.

1. **Allocation lifecycle invert.** Default `draft`; `confirmed` only after sheet Close.
   Freeze, amend, and membership invert to draft-writable / confirmed-frozen.
2. **Validate/Reject dropped.** `action_validate` / `action_reject` and states
   `validated` / `rejected` are gone. Residual and revalidation apply while `draft` and
   while `confirmed`.
3. **Delete invert.** Draft allocations unlink even with revisions (vouchers persist
   unassigned). Open sheets cascade draft allocations then delete. Closed sheets refuse
   unlink even when empty.
4. **SQL remap is not a safe inverse.** Module `19.0.1.28.0` maps `open`→`draft` and
   `closed`→`confirmed` and collapses leftover `validated`/`rejected`. Upgrade cannot
   restore Selection keys; restore from dump. Manifest rollback target named in the
   delta is `19.0.1.27.0`.

## REMOVED requirement (no matching main-spec heading)

**Requirement:** Back-office Validate and Reject (domain `collection-allocations`)

- **Reason (from delta):** Allocations stay draft until sheet Close; confirmed is the
  freeze. Validate/Reject and `validated`/`rejected` are gone.
- **Migration (from delta):** Module `19.0.1.28.0` SQL-maps allocation `state` from the
  parent sheet (`open`→`draft`, `closed`→`confirmed`) at the start of post-migrate so
  dropped Selection keys never linger. Collapse leftover `validated`/`rejected`. Chatter
  history remains. `reviewed_by`/`reviewed_at` stay on the model and leave the form.
  Upgrade cannot restore Selection keys; restore from dump. Manifest rollback target
  `19.0.1.27.0`.
- **Main-spec action:** No standalone `### Requirement: Back-office Validate and Reject`
  heading existed in `openspec/specs/collection-allocations/spec.md`. No heading was
  invented or deleted. The drop is carried by MODIFIED **Freeze, revisions, ACL,
  back-office** (`MUST NOT expose Validate or Reject`; `validated`/`rejected` MUST NOT
  remain as states).

## Specs synced to source of truth

Delta specs merged into existing main specs. Requirements not named in a delta were
preserved (byte-identical after trailing-newline normalize).

| Domain                 | Action  | Details                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ---------------------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| collection-allocations | Updated | ADDED 2 (`Draft default and confirm-on-close invariant`, `Draft unlink with revisions`); MODIFIED 8 (`MCP create_collection_allocation`, `Idempotency and amend`, `Input and sheet gates`, `Revalidation and residual`, `Freeze, revisions, ACL, back-office`, `Source detach residual refuse`, `Partner match after voucher write`, `MCP get_collection_allocation`); REMOVED 1 skipped (no matching heading, see above). |
| collection-vouchers    | Updated | MODIFIED 3 (`Voucher lifecycle`, `Voucher allocation membership`, `Partner write follows allocation`). All other requirements preserved.                                                                                                                                                                                                                                                                                   |
| collection-sheets      | Updated | MODIFIED 3 (`Membership, dates, and deletion`, `Open/closed lifecycle`, `Closed sheet membership freeze`). All other requirements preserved.                                                                                                                                                                                                                                                                               |

Main spec paths:

- `openspec/specs/collection-allocations/spec.md`
- `openspec/specs/collection-vouchers/spec.md`
- `openspec/specs/collection-sheets/spec.md`

### Leftovers not in the delta (preserved on purpose)

- `collection-allocations` **Purpose** still says “back-office validates or rejects.”
  That Purpose line was not an ADDED/MODIFIED/REMOVED requirement. Historical spec text,
  not incomplete archive work.

## Known warning (not a blocker)

Design named version `19.0.1.28.0`. Shipped manifest is `19.0.1.29.0`. Migrate folder
remains `migrations/19.0.1.28.0/`. Recorded as a known warning. Versions were not bumped
at archive.

Nebula-agent work was explicitly deferred for this change. Missing Nebula copy/PRD/eval
is not incomplete archive work.

## Mechanical move

- Change folder was **untracked** (`git ls-files` miss). `git mv` failed with
  `fatal: source directory is empty`. Fallback `mv` succeeded.
- Archive path: `openspec/changes/archive/2026-09-02-draft-until-close/`
- Active path `openspec/changes/draft-until-close/` is gone after the move.
- Pre-move recursive snapshot compared with `diff -r`. Empty diff (exit 0). This report
  is additive and was written after that comparison.

## Archive contents

- proposal.md
- exploration.md
- design.md
- tasks.md (13/13 complete; no unchecked implementation tasks)
- specs/collection-allocations/spec.md
- specs/collection-vouchers/spec.md
- specs/collection-sheets/spec.md
- apply-progress.md
- verify-report.md
- state.yaml
- archive-report.md (this file; additive after move)

## Out of scope (untouched)

Per launch instructions, this archive did not touch unrelated WIP:
`openspec/changes/collection-sheet-report/`,
`openspec/changes/archive/2026-09-02-seller-commission-percent/`, connector/settings
files, or `collection_sheet_template.xlsx`.

## Risks at close

- Manifest `19.0.1.29.0` vs design/migrate `19.0.1.28.0` may confuse a later rollback
  reader; SQL remap remains the migrate folder name.
- Allocations Purpose still mentions back-office validate/reject until a later change
  edits that non-delta section.
- Coordinated Nebula-agent remains deferred: agent copy, PRD, eval, and
  `_EXISTING_ALLOCATION_MESSAGE` were out of this change.
