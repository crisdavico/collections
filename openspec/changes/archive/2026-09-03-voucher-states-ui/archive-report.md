# Archive Report: voucher-states-ui

**Archived**: 2026-09-03
**Change**: `voucher-states-ui`
**Store**: openspec (filesystem only; Engram namespace unavailable)
**Status**: success
**reviewGate**: absent (receipt-driven review off; archive proceeded under ordinary repository policy)

## Final state at close

These facts outrank intermediate `apply-progress` / `verify-report` snapshots. Launch
final-state facts outrank those snapshots when they disagree.

| Fact | Value | Authority |
| ---- | ----- | --------- |
| Implementation tasks | 18/18 `[x]` (1.1–4.2); pending 0 | persisted `tasks.md` + launch final-state |
| applyState | `all_done` | launch structured status |
| remediationState.required | false | launch structured status |
| Verify verdict | `pass_with_warnings` | launch final-state (matches verify-report envelope at verification time) |
| Requirements / scenarios | 26/26, 82/82 | launch final-state |
| CRITICAL findings | 0 | launch final-state |
| Blockers | 0 | launch final-state |
| Module tests at close | 0 failed / 0 error of 665; `test_exit_code` 0 | launch final-state |
| evidence_revision (envelope) | `sha256:beae7049f7e8c728571ed6f4d533e5c1aa7edc645ea8919ea815661abfaeecbc` | launch final-state |
| verify-report file hash | `sha256:d4761eff8c6d9d3666471ddfe2f27870139a44c47262b086ee08c141b5f51a95` | launch final-state; confirmed on archived file |
| Shipped manifest | `19.0.1.32.0` with `migrations/19.0.1.31.0/` (state remap) **and** `migrations/19.0.1.32.0/` (sibling residual_reason drop) | launch final-state |
| Leftover residual | production: residual = debt − applied; no `_projected_residual`; unlink / partner-write MUST NOT refuse leftover residual 0 / underflow | launch final-state (delta remapped to match) |
| Form audit columns | `reviewed_by` / `reviewed_at` remain on form; list `optional="hide"` | launch final-state (shipped, not pending) |

CRITICAL findings: none. Archive was not blocked. Versions were not bumped at archive.

## Task Completion Gate

Inspected `openspec/changes/voucher-states-ui/tasks.md` before merge/move. Zero `- [ ]`
implementation tasks. Phases 1–4 (1.1–4.2) are all `[x]`. Gate passed; no archive-time
checkbox reconciliation. Archived `tasks.md` still has zero unchecked implementation
tasks. Proposal.md still has unchecked *success-criteria* bullets; those are not
implementation tasks and were not treated as a gate.

## Native Review Receipt Gate

Structured status `reviewGate` / `reviewOffer` are structurally absent. No review
transaction/ledger/receipt was read. Archive proceeded under ordinary repository
policy. Absence of the gate is not a defect.

Parent acquire token
`sha256:7c5b57e91b5a1a9f5209385c5e9cffa456cd1f7dd51d26d9b5a6ecb5dd5040b7` is held by the
orchestrator. This executor did not acquire and does not settle.

## Destructive / backward-incompatible deltas (warned; archive proceeded)

`openspec/config.yaml` `rules.archive` requires a warning before merging destructive or
backward-incompatible deltas. The orchestrator launched archive with these facts already
known. They were merged; they were not re-asked.

1. **Voucher states remapped.** `pending`/`approved`/`rejected` are gone.
   `draft` / `validated_seller` / `validated_collections`. Reject and form Approve are
   gone. Stages kanban is gone. Unlink is draft-only. MCP stamps `validated_seller`.
2. **REMOVED `Voucher review history is visible`.** History notebook is dropped from
   Payment Vouchers. Reason and Migration present in the delta: snapshot rows stay in
   the database with `decision` `approved`\|`rejected`; ACL read remains; form MUST NOT
   bind `review_snapshot_ids`.
3. **Document Review reject removed.** Queue is `validated_seller` + proof; Approve
   writes `validated_collections` and snapshot `decision="approved"`; Reject RPC/OWL
   MUST NOT exist.
4. **Allocation input gate.** All three voucher states MAY allocate; MUST NOT refuse
   because a voucher is not `rejected` (that state MUST NOT exist).

No large unrelated requirement blocks were deleted. Requirements not named in a delta
were preserved.

## Specs synced to source of truth

Delta specs merged into existing main specs **before** the folder move. Requirements not
named in a delta were preserved. MODIFIED blocks were replaced with the delta’s full
requirement text (post-merge requirement bodies byte-identical to the delta). ADDED
`Voucher state SQL remap` was appended. REMOVED History requirement was deleted after
recording Reason/Migration.

| Domain | Action | Details |
| ------ | ------ | ------- |
| collection-vouchers | Updated | ADDED 1 (`Voucher state SQL remap`); MODIFIED 11 (`Mail thread and activities`, `Deferred integrations not required`, `Concurrent and stale review attempts`, `Attachment replacement resets review to pending`, `Voucher fields and defaults`, `Voucher lifecycle`, `Payment Vouchers UI`, `Immutable review snapshots and ACL`, `Historical vouchers remain operable`, `Voucher allocation membership`, `Partner write follows allocation`); REMOVED 0; RENAMED 0. Original remaining 35 + 1 added = 36. |
| collection-allocations | Updated | MODIFIED 1 (`Input and sheet gates`); REMOVED 0; RENAMED 0. Other 12 requirements preserved, including leftover residual formula `total_debt − total_applied`. |
| collection-sheet-report | Updated | MODIFIED 1 (`Shared report payload` — print keys `draft`/`validated_seller`/`validated_collections`); REMOVED 0. Other 9 requirements preserved. |
| document-review | Updated | MODIFIED 11 (queue, OWL, approve/reject, authorization, flag, menu/RPCs, sheet identifier, three-way comparison, snapshots, repeated revision, company isolation); REMOVED 1 (`Voucher review history is visible`); RENAMED 0. Preserved 4 unnamed requirements (`Authenticated binary attachment viewer`, `Viewer fit and cursor-anchored zoom`, `Viewer rotation`, `Queue payload includes readonly provenance`). Count 15. |

Main spec paths:

- `openspec/specs/collection-vouchers/spec.md`
- `openspec/specs/collection-allocations/spec.md`
- `openspec/specs/collection-sheet-report/spec.md`
- `openspec/specs/document-review/spec.md`

Leftover residual language on voucher membership / partner-write / allocation totals
stayed: residual = debt − applied; unlink / partner-write MUST NOT refuse leftover
residual 0 / underflow; `_projected_residual` is absent from those main specs.

### Leftovers not in the delta (preserved on purpose)

- `collection-vouchers` **Purpose** still says `pending→approved/rejected`. That Purpose
  line was not an ADDED/MODIFIED/REMOVED requirement.
- `document-review` **Purpose** still says “approve/reject”. Same rule.

## Shipped warnings (not pending tasks)

Per orchestrator final-state (outrank `verify-report` / design lock at verification
time):

1. Design originally locked manifest `19.0.1.31.0`. Shipped tree is `19.0.1.32.0` with
   `migrations/19.0.1.31.0/` (this change’s state remap) **and** `migrations/19.0.1.32.0/`
   (sibling `residual_reason` drop). Documented as shipped; not rewritten as a pending
   task.
2. Flag spec keeps `reviewed_by` / `reviewed_at` on Payment Vouchers; list
   `optional="hide"`. Design said leave the form; shipped keeps them. Documented as
   shipped, not pending.
3. `collection_connector_sqlite` rollback test remapped in the sibling addon git
   (ORM `partner_id` + `draft`; `create_collection_vouchers` asserted absent). That
   addon is outside the collection git root and was not reverted here.

Per `verify-report` at verification time (not current defects): verdict
`pass_with_warnings`; 0 CRITICAL. Archive allowed.

## Mechanical move

- Change folder was **untracked** (`git ls-files` miss). `git mv` failed with
  `fatal: source directory is empty`. Fallback `mv` succeeded.
- Archive path: `openspec/changes/archive/2026-09-03-voucher-states-ui/`
- Active path `openspec/changes/voucher-states-ui/` is gone after the move.
- Pre-move recursive snapshot compared with `diff -r`. Empty diff (exit 0). This report
  is additive and was written after that comparison.
- `state.yaml` moved with the change folder. Orchestrator state was not rewritten here.

### Verbatim `diff -r` readback (Step 3 — archive move)

```text
===== BEGIN DIFF -r =====
===== END DIFF -r =====
DIFF_STATUS=0
```

Empty diff is the only passing evidence.

## Archive contents

- proposal.md
- exploration.md
- design.md
- tasks.md (18/18 complete; no unchecked implementation tasks)
- specs/collection-vouchers/spec.md
- specs/collection-allocations/spec.md
- specs/collection-sheet-report/spec.md
- specs/document-review/spec.md
- apply-progress.md
- verify-report.md
- state.yaml
- archive-report.md (this file; additive after move)

## Out of scope (untouched)

- `openspec/changes/archive/2026-09-03-allocation-customer-debt/**` (explicitly forbidden)
- `openspec/changes/collection-sheet-workflow/` (unrelated active change)
- `collection_connector_sqlite` (outside collection git root)
- Application code, tests, manifests, `AGENTS.md`, Nebula-agent

## Risks at close

- Main-spec Purpose lines still use old voucher/review vocabulary until a later change
  edits those non-delta sections.
- Concurrent leftover `collection-sheet-workflow` remains active; it was not merged or
  moved.
- Engram persistence skipped: `user-engram` namespace was not available.
