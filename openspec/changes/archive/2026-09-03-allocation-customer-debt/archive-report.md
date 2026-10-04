# Archive Report: allocation-customer-debt

**Archived**: 2026-09-03 **Change**: `allocation-customer-debt` **Store**: openspec
(filesystem only; Engram not used) **Status**: success **reviewGate**: absent (no review
started; archive proceeded under ordinary policy)

## Final state at close

These facts outrank intermediate `apply-progress` / `verify-report` snapshots.

| Fact                  | Value                                         | Authority                                                                |
| --------------------- | --------------------------------------------- | ------------------------------------------------------------------------ |
| Implementation tasks  | 18/18 `[x]` (1.1–4.5); pending 0              | persisted `tasks.md` + launch final-state                                |
| applyState            | `all_done`                                    | launch structured status                                                 |
| Verify verdict        | `pass_with_warnings`                          | launch final-state (matches verify-report envelope at verification time) |
| CRITICAL findings     | 0                                             | launch final-state                                                       |
| Blockers              | 0                                             | launch final-state                                                       |
| Module tests at close | `/collection` suite 636/636 exit 0            | launch final-state (same count as verify-report at verification time)    |
| Shipped manifest      | `19.0.1.32.0` on top of sibling `19.0.1.31.0` | launch final-state                                                       |
| Nebula-agent          | explicitly out of scope                       | launch final-state                                                       |

CRITICAL findings: none. Archive was not blocked. Versions were not bumped at archive.

## Task Completion Gate

Inspected `openspec/changes/allocation-customer-debt/tasks.md` before merge/move. Zero
`- [ ]` implementation tasks. Phases 1–4 (1.1–4.5) are all `[x]`. Gate passed; no
archive-time checkbox reconciliation.

## Native Review Receipt Gate

Structured status `reviewGate` is structurally absent. No review
transaction/ledger/receipt was read. Archive proceeded under ordinary repository policy.
The post-verify offer was not a gate.

Parent acquire token
`sha256:c644a03ab7275369ac04d6bc130739ca5ce372ac3f7860e225d10643ee1e035f` was
authenticated with `sdd-attempt acquire --token` (zero-mutation `proceed`). This
executor does not settle.

## Destructive / backward-incompatible deltas (warned; archive proceeded)

`openspec/config.yaml` `rules.archive` requires a warning before merging destructive or
backward-incompatible deltas. No `REMOVED` / `RENAMED` sections. No large unrelated
requirement blocks were deleted. The orchestrator launched archive with these facts
already known. They were merged; they were not re-asked.

1. **`residual_reason` dropped from persist.** Allocation and revision no longer store
   the field. MCP create MAY send it and MUST ignore it. Sheet report MUST NOT read it.
   `content_hash` MUST NOT include it (reason-only retry is a no-op).
2. **Residual formula invert.** Residual is `total_debt − total_applied`; negative MUST
   be allowed. Payload expands to every outstanding ERP invoice (zeros included). MCP
   `total_debt` is computed, not stored from caller summary.
3. **Draft detach no longer refuses on leftover-voucher residual.** Fully applied and
   leftover-underflow draft detach/unlink/`partner_id` write MUST succeed; residual MUST
   NOT ± voucher amount. Confirmed detach remains refused.
4. **Customer Debt form / parent-arch `document_kind`.** Invoices tab renamed;
   inherit-only inject replaced by parent-arch field order on
   `collection_allocation_views.xml`.

## Specs synced to source of truth

Delta specs merged into existing main specs. Requirements not named in a delta were
preserved (byte-identical vs `HEAD` after splice). MODIFIED blocks were replaced with
the delta’s full requirement text (byte-identical to the delta).

| Domain                 | Action  | Details                                                                                                                                                                                                                                                                 |
| ---------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| collection-allocations | Updated | ADDED 2 (`Customer Debt snapshot and form`, `Totals and residual formula`); MODIFIED 5 (`Idempotency and amend`, `Revalidation and residual`, `Source detach residual refuse`, `MCP get_collection_allocation`, `Allocation line document_kind`); REMOVED 0; RENAMED 0. |
| collection-vouchers    | Updated | MODIFIED 3 (`Voucher allocation membership`, `Partner write follows allocation`, `Voucher lifecycle`). All other requirements preserved.                                                                                                                                |

Main spec paths:

- `openspec/specs/collection-allocations/spec.md`
- `openspec/specs/collection-vouchers/spec.md`

### Sibling overlap (`voucher-states-ui`)

Concurrent sibling `openspec/changes/voucher-states-ui/` was left untouched (no edit,
move, or delete). Overlapping MODIFIED voucher requirements already used sibling
`validated_seller` / `validated_collections` wording in this change’s delta; they were
merged as specified. Main-spec `Voucher lifecycle` now uses that vocabulary. Sibling
artifacts were not archived.

### Leftovers not in the delta (preserved on purpose)

- `collection-allocations` **Purpose** still says “back-office validates or rejects.”
  That Purpose line was not an ADDED/MODIFIED/REMOVED requirement.
- `Input and sheet gates` still mentions voucher `rejected` as an ineligible input. Not
  named in this delta.

## Known warning (not a blocker)

Per `verify-report` at verification time (not current defects):

1. Strict TDD Safety Net was N/A for tasks 4.3 and 4.4 even though existing test files
   were modified.
2. One CSS-class assertion (`oe_stat_button`) on the Vouchers smart button;
   domain/`action_open_vouchers` coverage still holds.

Verdict `pass_with_warnings`; 0 CRITICAL. Archive allowed.

Nebula-agent work was explicitly out of scope. Missing Nebula copy/PRD/eval is not
incomplete archive work.

## Mechanical move

- Change folder was **untracked** (`git ls-files` miss). `git mv` failed with
  `fatal: source directory is empty`. Fallback `mv` succeeded.
- Archive path: `openspec/changes/archive/2026-09-03-allocation-customer-debt/`
- Active path `openspec/changes/allocation-customer-debt/` is gone after the move.
- Pre-move recursive snapshot compared with `diff -r`. Empty diff (exit 0). This report
  is additive and was written after that comparison.
- `state.yaml` moved with the change folder. Orchestrator state was not rewritten here.

## Archive contents

- proposal.md
- exploration.md
- design.md
- tasks.md (18/18 complete; no unchecked implementation tasks)
- specs/collection-allocations/spec.md
- specs/collection-vouchers/spec.md
- apply-progress.md
- verify-report.md
- state.yaml
- archive-report.md (this file; additive after move)

## Out of scope (untouched)

Per launch instructions, this archive did not touch sibling WIP
`openspec/changes/voucher-states-ui/`, application code, tests, manifests, `AGENTS.md`,
or Nebula-agent.

## Risks at close

- Allocations Purpose still mentions back-office validate/reject until a later change
  edits that non-delta section.
- `Input and sheet gates` still names voucher `rejected`; sibling `voucher-states-ui`
  owns that vocabulary when it archives.
- Coordinated Nebula-agent remains out of scope: MCP still accepts optional
  `residual_reason` and ignores it.
- Sibling `voucher-states-ui` is still active (verify). Main specs now contain this
  change’s `validated_seller` wording on overlapping voucher requirements; sibling
  archive must not revert it without a later delta.
