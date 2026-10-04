# Archive Report: collection-receipts

**Archived**: 2026-09-04 **Change**: `collection-receipts` **Store**: openspec
(filesystem only; Engram not used) **Status**: success **reviewGate**: absent (no review
discovered; archive proceeded under ordinary policy)

## Final state at close

These facts outrank intermediate `apply-progress` / `verify-report` / `state.yaml`
snapshots.

| Fact                        | Value                                        | Authority                                                                |
| --------------------------- | -------------------------------------------- | ------------------------------------------------------------------------ |
| Implementation tasks        | 27/27 `[x]` (1.1–4.3); pending 0             | persisted archived `tasks.md` + launch final-state                       |
| applyState                  | `all_done`                                   | launch structured status                                                 |
| Verify verdict              | `pass_with_warnings`                         | launch final-state (matches verify-report envelope at verification time) |
| Requirements / scenarios    | 25/25, 66/66                                 | launch final-state                                                       |
| CRITICAL findings           | 0                                            | launch final-state                                                       |
| Blockers                    | 0                                            | launch final-state                                                       |
| Module tests at close       | 736 passed, exit 0 (`collection: 804 tests`) | launch final-state (same as verify-report at verification time)          |
| Image build at close        | `invoke img-build` exit 0                    | launch final-state                                                       |
| Shipped manifest            | `19.0.1.34.0`                                | launch final-state / verify-report at verification time                  |
| Coordinated sqlite + Nebula | out of this apply                            | launch + verify-report at verification time                              |

CRITICAL findings: none. Archive was not blocked. Versions were not bumped at archive.

Archived `state.yaml` still records `phase: verify-blocked-maintainer-decision` and
`artifacts.apply/verify: missing`. That file is an earlier cycle snapshot. It does
**not** describe close: tasks are complete, verify admitted `pass_with_warnings`, and
this folder is the archive. The file was not rewritten (audit trail).

## Task Completion Gate

Inspected `openspec/changes/collection-receipts/tasks.md` before merge/move. Zero
`- [ ]` implementation tasks. Phases 1–4 (1.1–4.3) are all `[x]` (27/27). Gate passed;
no archive-time checkbox reconciliation. Archived `tasks.md` still shows 27/27 `[x]`.

## Native Review Receipt Gate

Structured status `reviewGate` is structurally absent. No review
transaction/ledger/receipt was read. Archive proceeded under ordinary repository policy.
The post-verify offer is not a gate.

Parent acquire revision
`sha256:69e6dacae246f1501a9dca64911a007c3c5bd2a893e364bfa5dc2d4ab43a4e94` matches live
`sdd-attempt status` ordinal 6 (`work_unit`: Archive collection-receipts, `outcome`:
running). A same-process acquire with a new `--request-id` returned
`invalid_continuation` and was not retried. This executor does not settle.

## Destructive / backward-incompatible deltas (warned; archive proceeded)

`openspec/config.yaml` `rules.archive` requires a warning before merging destructive or
backward-incompatible deltas. No `REMOVED` / `RENAMED` sections. No large unrelated
requirement blocks were deleted. Deltas ADDED and MODIFIED only. The orchestrator
launched archive with these facts already known. They were merged; they were not
re-asked.

Behavioral expansions (not section deletions) now in main specs:

1. **Receipt grouping on allocations.** Persist/amend writes at most one receipt per
   `document_kind`; MCP `splits` optional; omitted splits keep compat FIFO.
2. **Freeze and unlink include receipts.** Confirmed/`closed`/`cancelled` freeze
   `receipt_ids`; draft unlink cascades receipts and values.
3. **MCP get always lists `receipts[]`.** Found payload includes receipts (even empty).
4. **Invoice `document_kind` on create/amend.** MCP MAY send kind; omitted kind on first
   persist is `invoice`; amend keeps stored kind unless payload sets it.
5. **`content_hash` includes splits and invoice kind** when present; omitted-splits
   payloads still hash as before.
6. **Dispatcher allowlist adds `create_receipt`.** SQLite stub returns a fake id without
   writing the sqlite file. Close issues draft receipts through that op.
7. **Customer debt rows MAY include `document_kind`** (default `invoice`); quotations
   MAY appear as outstanding debt rows.

## Specs synced to source of truth

Delta specs merged into existing main specs. Requirements not named in a delta were
preserved (byte-identical after span rstrip). MODIFIED blocks were replaced with the
delta’s full requirement text (byte-identical to the delta after span rstrip). New
capability `collection-receipts` had no main spec: mechanical `cp` + `diff -r` + `mv`
(never Read→Write of spec bytes).

| Domain                 | Action  | Details                                                                                                                                                                                                                                                                                                                                                                                                |
| ---------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| collection-receipts    | Created | Full spec copied (12 requirements). Main spec did not exist.                                                                                                                                                                                                                                                                                                                                           |
| collection-allocations | Updated | ADDED 2 (`MCP splits payload`, `Persist receipt grouping on create and amend`); MODIFIED 6 (`Idempotency and amend`, `Freeze, revisions, ACL, back-office`, `MCP get_collection_allocation`, `Draft unlink with revisions`, `Allocation line document_kind`, `Cancelled and Closed allocation write guards`); REMOVED 0; RENAMED 0. Untouched 9 of 15 original requirements. Main now 17 requirements. |
| collection-connectors  | Updated | ADDED 2 (`Dispatcher allowlist includes create_receipt`, `SQLite stub create_receipt`); MODIFIED 3 (`Read-only MCP tool customer_debt`, `Normalized customer debt output`, `SQLite read-only customer debt source`); REMOVED 0; RENAMED 0. Untouched 28 of 31 original requirements. Main now 33 requirements.                                                                                         |

Main spec paths:

- `openspec/specs/collection-receipts/spec.md`
- `openspec/specs/collection-allocations/spec.md`
- `openspec/specs/collection-connectors/spec.md`

## Known warning (not a blocker)

Per `verify-report` at verification time (not a current defect, not CRITICAL):

1. Strict TDD Safety Net evidence table in `apply-progress` covered Phase 4 only (tasks
   4.1–4.3). Phases 1–3 were prior slices without RED/GREEN rows in that artifact. TDD
   Compliance 5/6 checks. Verdict `pass_with_warnings`.

Archive allowed. Coordinated sqlite seed/stub file I/O and Nebula `InvoiceApplication`
were labeled not-this-apply and do not make this archive partial.

## Mechanical copy and move

- New spec: `cp` to `mktemp` under `openspec/specs/collection-receipts/`, `diff -r` vs
  change spec (empty, exit 0), `mv` to `openspec/specs/collection-receipts/spec.md`,
  `diff -r` again (empty, exit 0). Byte size 7769 both sides.
- Change folder was **untracked** (`git ls-files` empty). `git mv` failed with
  `fatal: source directory is empty`. Fallback `mv` succeeded.
- Archive path: `openspec/changes/archive/2026-09-04-collection-receipts/`
- Active path `openspec/changes/collection-receipts/` is gone after the move.
- Pre-move recursive snapshot compared with `diff -r`. Empty diff (exit 0). This report
  is additive and was written after that comparison.
- `state.yaml` moved with the change folder. Orchestrator state was not rewritten here.
- Did not touch `.codegraph/`, `__pycache__/`, or `.gentle-ai-instance`.

## Archive contents

- proposal.md
- exploration.md
- design.md
- tasks.md (27/27 complete; no unchecked implementation tasks)
- specs/collection-receipts/spec.md
- specs/collection-allocations/spec.md
- specs/collection-connectors/spec.md
- apply-progress.md
- verify-report.md
- state.yaml (stale intermediate phase label; not rewritten)
- archive-report.md (this file; additive after move)

## Out of scope (untouched)

This archive did not edit application code, tests, manifests, `AGENTS.md`, the sqlite
connector addon, or nebula-agent. Coordinated follow-ups remain outside this change.

## Risks at close

- Archived `state.yaml` still says apply/verify missing; readers must use this report
  and `tasks.md` / `verify-report.md` for close state.
- SQLite `create_receipt` is a non-writing stub with a fake external id. A real ERP
  adapter is still future work.
- Customer-debt `document_kind` / quotation rows depend on adapter payload; sqlite
  seed/file I/O coordination was out of this apply.
- Nebula `InvoiceApplication` / splits UX was out of this apply.
- Allocations Purpose still says “back-office validates or rejects.” That Purpose line
  was not an ADDED/MODIFIED/REMOVED requirement.
