# Archive Report: document-review-ocr-only

**Archived**: 2026-09-04 **Change**: `document-review-ocr-only` **Store**: openspec
(filesystem only; Engram namespace unavailable — `mem_save` not called) **Status**:
success **reviewGate**: absent (no review discovered; archive proceeded under ordinary
repository policy)

## Final state at close

These facts outrank intermediate `apply-progress` / `verify-report` snapshots. Launch
final-state facts outrank those snapshots when they disagree.

| Fact                                            | Value                                                                                          | Authority                                                                |
| ----------------------------------------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Implementation tasks                            | 15/15 `[x]` (1.1–4.3); `allComplete` true                                                      | persisted `tasks.md` + launch structured status                          |
| applyState                                      | `all_done`                                                                                     | launch structured status                                                 |
| Verify verdict                                  | `pass_with_warnings`                                                                           | launch final-state (matches verify-report envelope at verification time) |
| Delta requirements / scenarios                  | 4/4 COMPLIANT, 11/11 COMPLIANT                                                                 | launch final-state                                                       |
| CRITICAL findings                               | 0                                                                                              | launch final-state                                                       |
| Blockers                                        | 0                                                                                              | launch final-state                                                       |
| Tests at close                                  | `invoke test -m collection --mode=update` exit 0; 0 failed of 749                              | launch final-state                                                       |
| Manifest at close                               | `19.0.1.36.0`; no `migrations/19.0.1.36.0/`                                                    | launch final-state                                                       |
| Warnings at close (still true, not fixed later) | no browser sheet URL; Phase 1 TDD safety-net N/A on rewritten test file; optional pylint C8101 | launch final-state                                                       |
| apply-progress "16/16" vs tasks.md 15/15        | `tasks.md` is authority (15 implementation tasks)                                              | launch final-state; do not treat 16/16 as current                        |

CRITICAL findings: none. Archive was not blocked. Versions were not bumped at archive.
`state.yaml` was left as the pre-archive audit trail (`phase: verify`; notes that
archive had not run). Close is recorded here, not by rewriting `state.yaml`.

## Task Completion Gate

Inspected `openspec/changes/document-review-ocr-only/tasks.md` before merge/move. Zero
`- [ ]` implementation tasks. Phases 1–4 (1.1–4.3) are all `[x]`. Gate passed; no
archive-time checkbox reconciliation. Archived `tasks.md` still has zero unchecked
implementation tasks.

## Native Review Receipt Gate

Structured status `reviewGate` is structurally absent. No review transaction, ledger,
receipt, or gate-context was read. Archive proceeded under ordinary repository policy.
Absence of the gate is not a defect and was not treated as a missing receipt.

Parent acquire token
`sha256:5040bd86856521e704d8a006244d840c676812a5c011a4439aef57d9f33bd466` is held by the
orchestrator. This executor did not acquire and does not settle.

## Destructive / backward-incompatible deltas (warned; archive proceeded)

`openspec/config.yaml` `rules.archive` requires a warning before merging destructive or
backward-incompatible deltas. The delta is **ADDED + MODIFIED only** (no REMOVED, no
RENAMED). Replacing entire matching `### Requirement:` blocks is still a
backward-incompatible spec change for Document Review behavior. The orchestrator
launched archive knowing this. They were merged; they were not re-asked.

1. **MODIFIED `OWL client loads real ORM data`.** Document Review MUST present typed
   readonly `ocr_*` controls. MUST NOT present editable current fields or input
   handlers. Dual typed groups when OCR vs seller `document_type` differ.
2. **MODIFIED `Approve and reject without mocks`.** Approve MUST NOT rewrite current.
   Client empty/omit/nonempty `vals` MUST be ignored. Snapshot still matches current
   with `decision` `approved`. Reject still MUST NOT exist.
3. **MODIFIED `Three-way raw, seller, and current comparison`.** Three-way side-by-side
   remains on the Payment Vouchers form only. Document Review is OCR-only plus inline
   seller-change warnings; MUST NOT keep editable current or three widgets.
4. **ADDED `Queue payload includes seller_changed_fields`.** Deterministic OCR vs seller
   map; both-empty omit; else seller value including explicit emptied.

No REMOVED/RENAMED requirement blocks. No large unrelated sections were deleted.
Requirements not named in the delta were preserved.

## Specs synced to source of truth

Delta spec merged into the existing main spec **before** the folder move. Requirements
not named in the delta were preserved. MODIFIED blocks were replaced in full by name.
ADDED `Queue payload includes seller_changed_fields` was appended after
`Review snapshots isolated by company`.

| Domain          | Action  | Details                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| --------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| document-review | Updated | ADDED 1 (`Queue payload includes seller_changed_fields`); MODIFIED 3 (`OWL client loads real ORM data`, `Approve and reject without mocks`, `Three-way raw, seller, and current comparison`); REMOVED 0; RENAMED 0. Preserved 12 unnamed requirements (`Eligible review queue`, `Authenticated binary attachment viewer`, `Viewer fit and cursor-anchored zoom`, `Viewer rotation`, `Document Review authorization`, `Per-company Document Review flag`, `Document Review menu and RPCs when flag is off`, `Sheet identifier required on review operations`, `Queue payload includes readonly provenance`, `Document Review decisions append immutable snapshots`, `Repeated Document Review appends another revision`, `Review snapshots isolated by company`). Count 16 requirements / 46 scenarios. |

Main spec path:

- `openspec/specs/document-review/spec.md`

### Leftovers not in the delta (preserved on purpose)

- `document-review` **Purpose** still says “correct OCR’d fields against the attachment,
  and approve/reject without mock data.” That Purpose line was not an
  ADDED/MODIFIED/REMOVED requirement.

## Shipped warnings (not pending tasks)

Per orchestrator final-state (outrank `verify-report` at verification time; still true,
not fixed later):

1. No browser sheet URL was supplied; OWL/nav/viewer contracts are source-string tested.
2. Phase 1 TDD safety-net recorded N/A on rewritten (modified, not new)
   `tests/test_collection_document_review.py`.
3. Optional pylint C8101 `manifest-required-author` (Eynes) on `__manifest__.py`; hook
   still Passed.

Per `verify-report` at verification time (not current defects): verdict
`pass_with_warnings`; 0 CRITICAL; 0 blockers. Archive allowed. Completeness used
`tasks.md` 15/15; `apply-progress.md` “16/16” is not current task count.

## Mechanical move

- Change folder was **untracked** (`git ls-files` miss). `git mv` failed with
  `fatal: source directory is empty, source=openspec/changes/document-review-ocr-only, destination=openspec/changes/archive/2026-09-04-document-review-ocr-only`.
  Fallback `mv` succeeded.
- Archive path: `openspec/changes/archive/2026-09-04-document-review-ocr-only/`
- Active path `openspec/changes/document-review-ocr-only/` is gone after the move.
- Pre-move recursive snapshot compared with `diff -r`. Empty diff (exit 0). This report
  is additive and was written after that comparison.
- `state.yaml` moved with the change folder. Orchestrator state was not rewritten here.

### Verbatim `diff -r` readback (Step 3 — archive move)

```text
=== DIFF -R START ===
=== DIFF -R END ===
DIFF_STATUS=0
```

Empty diff is the only passing evidence.

## Archive contents

- proposal.md
- exploration.md
- design.md
- tasks.md (15/15 complete; no unchecked implementation tasks)
- specs/document-review/spec.md
- apply-progress.md
- verify-report.md
- state.yaml
- archive-report.md (this file; additive after move)

## Out of scope (untouched)

- Receipt models/views/tests, generated `README.rst`
- Leftover `openspec/changes/collection-receipts/` (absent at archive time; archived
  `openspec/changes/archive/2026-09-04-collection-receipts/` not edited)
- `.codegraph/`, `__pycache__`
- Application code, tests, manifests, `AGENTS.md`, Nebula-agent

## Risks at close

- Main-spec Purpose still uses “correct OCR’d fields” / “approve/reject” vocabulary
  until a later change edits that non-delta section.
- Document Review OWL is source-string tested only; browser click-through was never
  executed (WARNING at close, not CRITICAL).
- Engram persistence skipped: Engram was not available.
