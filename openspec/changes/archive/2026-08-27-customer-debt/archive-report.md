# Archive Report

**Change**: `customer-debt` **Archived to**:
`openspec/changes/archive/2026-08-27-customer-debt/` **Date**: 2026-08-27 **Artifact
store**: openspec **Status at close**: success — intentional-with-warnings (missing
`verify-report.md`) **Review gate**: ABSENT (kill switch off / no review discovered) —
archive proceeded under ordinary policy plus explicit user archive instruction

## Final-State Authority

| Source                     | Rank | Fact used                                                                                         |
| -------------------------- | ---- | ------------------------------------------------------------------------------------------------- |
| User / orchestrator launch | 3    | Explicit request to archive done specs in `openspec/changes`                                      |
| Persisted `tasks.md`       | 2    | 14/14 implementation tasks `[x]`                                                                  |
| Filesystem `state.yaml`    | 3    | Apply complete; collection 422 tests / sqlite 27 tests; scoped pre-commit passed; no Nebula files |
| `verify-report.md`         | —    | Absent at close                                                                                   |
| Native review receipts     | —    | `reviewGate` absent                                                                               |

## Final State (at close)

| Fact                 | Final state                                                                                            | Source                                                                        |
| -------------------- | ------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| Implementation tasks | 14/14 complete; 0 unchecked `- [ ]`                                                                    | Archived `tasks.md`                                                           |
| Apply                | all_done                                                                                               | Native `gentle-ai sdd-status`; `state.yaml`                                   |
| Verify artifact      | missing                                                                                                | Native status `verifyReport: []`; no `verify-report.md`                       |
| Tests at apply time  | collection 422 passed; sqlite 27 passed; scoped pre-commit passed                                      | `state.yaml` notes (apply-time snapshot, still the latest recorded counts)    |
| Main spec            | Already contained ADDED + MODIFIED requirements from apply task 4.1; MCP omit-`source` refinement kept | Compare of delta vs `openspec/specs/collection-connectors/spec.md` at archive |

No unrankable contradictions. Native status at archive time: `nextRecommended: verify`,
`dependencies.archive: blocked` solely because `verify-report.md` is missing. User
explicitly instructed archive of done specs; treated as intentional partial archive for
the missing verify artifact. Not CRITICAL (no verify-report exists to carry CRITICAL
findings).

## Specs Synced

| Domain                  | Action          | Details                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ----------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `collection-connectors` | Already present | Apply task 4.1 already updated the canonical spec. ADDED: `customer_debt` MCP, auth, unknown/inactive/other-seller reject, adapter dispatch, normalized debt output, SQLite invoices source. MODIFIED: active-company routing, fail-closed, storage-agnostic, company isolation, rollback. Skipped re-merge: main spec refined MCP success to `{customer, summary, invoices}` with no `source` (plus scenario `MCP debt omits source`); blindly applying the delta would revert that. |

**Destructive deltas**: None (no REMOVED / RENAMED).

## Task Completion Gate

- Tasks total: 14
- Tasks complete: 14
- Unchecked implementation tasks: 0
- Gate: **PASS**

## Archive Contents

- proposal.md ✅
- specs/collection-connectors/spec.md ✅
- design.md ✅
- tasks.md ✅ (14/14)
- state.yaml ✅
- verify-report.md ❌ (never written; recorded as intentional-with-warnings)
- apply-progress.md ❌ (never written)

Active path `openspec/changes/customer-debt/` is gone.

## Mechanical Copy Readback

### Step 2 — main spec merge

Skipped (canonical spec already updated in apply). No `diff -r` for a new main-spec
copy.

### Step 3 — change folder (`diff -r` pre-move snapshot vs archive)

Empty output (no differences). `diff_status=0`.

```text

```

`git mv` failed (`fatal: source directory is empty` — untracked change folder). Fallback
`mv` succeeded. Source path absent after move. Snapshot vs archive identity confirmed by
empty `diff -r`.

`archive-report.md` is additive and was written after the Step 3 comparison; it is
excluded from that readback.

## Source of Truth Updated

- `openspec/specs/collection-connectors/spec.md`

## SDD Cycle Complete

The change has been planned, implemented, and archived (verify-report omitted by
explicit archive instruction). Ready for the next change.
