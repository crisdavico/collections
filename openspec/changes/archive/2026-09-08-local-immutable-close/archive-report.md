# Archive: local-immutable-close

The change is archived. Specs are the source of truth. The cycle is complete.

## Quick path

1. Task Completion Gate: `tasks.md` 18/18 checked, zero `- [ ]`. Orchestrator final-state facts and `applyState: all_done` agree. No stale-checkbox reconciliation.
2. Delta specs merged into canonical mains: `collection-sheets`, `collection-receipts`, `collection-allocations`.
3. Change folder moved to `openspec/changes/archive/2026-09-08-local-immutable-close/` (`git mv` unavailable for the untracked tree; `mv` used). `diff -r` snapshot vs archive: empty (pass).
4. This report written after the move (additive; excluded from that comparison).

## Final state at close

| Topic | Decision |
| ----- | -------- |
| Verdict | PASS WITH WARNINGS (`pass_with_warnings`) |
| Requirements / scenarios | 9/9, 41/41 COMPLIANT |
| Collection tests | `invoke test -m collection --mode=update` — 0 failed of 950, exit 0 |
| Manifest | `19.0.1.44.0`; no `migrations/19.0.1.44.0/` |
| CRITICAL | none |
| reviewGate | absent — ordinary repository policy |
| Engram | N/A — OpenSpec filesystem only; `capture_prompt` N/A |
| Artifact store | openspec |
| Archive date | 2026-09-08 |

A prior verify FAIL on the AGENTS wrap pin was remediates by wrap-tolerant `" ".join(agents.split())` pins (task R.1). That FAIL is not current state. Satellite `collection_receipt_proposal` 3 failed / 1 error of 140 is pre-existing board drift and a WARNING only, not a Close CRITICAL.

`verify-report.md` Completeness listed 17/17 plus R.1; persisted `tasks.md` is 18/18 including R.1. Task Completion Gate uses the persisted tasks artifact (18/18).

## Specs synced

| Domain | Action | Details |
| ------ | ------ | ------- |
| collection-sheets | Updated | 1 added, 1 modified, 0 removed. 21 unrelated requirements preserved. |
| collection-receipts | Updated | 1 added, 3 modified, 1 removed (Reason + Migration present). 10 unrelated requirements preserved. |
| collection-allocations | Updated | 1 added, 1 modified, 0 removed. 18 unrelated requirements preserved. |

### Added / modified / removed (by name)

| Domain | Added | Modified | Removed |
| ------ | ----- | -------- | ------- |
| collection-sheets | Frozen associate create freeze | Open/closed lifecycle | — |
| collection-receipts | Frozen sheet refuses cash replacement create | Freeze and issued immutability; ERP identity and state; Read-mostly views | Close dispatches create_receipt |
| collection-allocations | Frozen sheet refuses allocation create | Draft default and confirm-on-close invariant | — |

### Removed (with Reason / Migration)

| Requirement | Reason | Migration |
| ----------- | ------ | --------- |
| Close dispatches create_receipt | Close is local-only and MUST NOT consult the connector or call `create_receipt`. | Keep connector `create_receipt` unused from Close. Rewrite tests that expect Close dispatch. Historical `issued` receipts keep state and external identity. Zero-receipt Close success is specified under Open/closed lifecycle. |

Config `rules.archive` warns before merging destructive or backward-incompatible deltas. This single REMOVED requirement is the change's intent (local Close). Reason and Migration are present. Merge proceeded as instructed; it is not a large-section deletion.

## Warnings at close (not blockers)

1. Satellite `collection_receipt_proposal` 3 failed / 1 error of 140 — pre-existing board drift, out of this Close contract.
2. Backward-incompatible spec removal of Close `create_receipt` dispatch — intended; connector op kept unused from Close.

## Archive contents

- proposal.md
- specs/ (three domain deltas: collection-sheets, collection-receipts, collection-allocations)
- design.md
- tasks.md (18/18 complete)
- apply-progress.md
- verify-report.md (`evidence_revision` `sha256:c488019cbdbc2830e4ca2976bfe19a17f45f6700b23199ea7667894e2e63e0a7`, `verdict: pass_with_warnings`)
- state.yaml
- archive-report.md (this file; additive)

## Mechanical copy

- Snapshot: recursive `cp -R` of the active change folder before the move.
- Move: `git mv` failed (`fatal: source directory is empty` — untracked / ignored tree); `mv` succeeded.
- Source `openspec/changes/local-immutable-close/` is gone.
- `diff -r` of snapshot vs archived tree: empty (pass). Archive-report is additive and was not part of that comparison.

## Checklist

- [x] Main specs updated; unrelated requirements preserved
- [x] Change folder moved to dated archive
- [x] Archive contains proposal, specs, design, tasks
- [x] Archived `tasks.md` has no unchecked implementation tasks
- [x] Active changes directory no longer has this change
- [x] Verbatim `diff -r` readback is empty
- [x] Engram skip recorded (openspec store; `capture_prompt` N/A)

## Next step

None. The SDD cycle is complete.
