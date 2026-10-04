# Archive Report: align-allocation-contracts

**Archived**: 2026-09-06 **Change**: `align-allocation-contracts` **Store**: openspec
(filesystem only; Engram not used) **Status**: success **reviewGate**: absent (kill
switch off / no review started; archive proceeded under ordinary repository policy)

## Final state at close

These facts outrank intermediate `apply-progress` / `verify-report` / `state.yaml`
snapshots.

| Fact                           | Value                                                                                                      | Authority                                                      |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| Implementation tasks           | 21/21 `[x]` (1.1–4.4); pending 0                                                                           | persisted archived `tasks.md` + launch final-state             |
| applyState                     | `all_done`                                                                                                 | launch structured status                                       |
| Verify verdict                 | `pass_with_warnings` (admitted)                                                                            | launch final-state (matches verify-report envelope at close)   |
| Delta requirements / scenarios | 9/9, 44/44 (vouchers 6/28 + allocations 3/16)                                                              | launch final-state + archived delta specs                      |
| Envelope                       | `--test-tags /collection`                                                                                  | launch final-state + verify-report envelope                    |
| CRITICAL findings              | 0                                                                                                          | launch final-state                                             |
| Module tests at close          | 0 failed, 0 error(s) of 779; test exit 0                                                                   | launch final-state                                             |
| Image / module build at close  | build exit 0                                                                                               | launch final-state                                             |
| Shipped manifest               | `19.0.1.40.0`                                                                                              | launch / verify-report at verification time                    |
| Document Review queue payload  | `_review_queue_payload` fills current keys from `_REVIEW_EDITABLE_FIELD_ORDER` (includes `retention_kind`) | launch final-state (remediating apply after first verify FAIL) |
| Sibling FIFO tests             | `collection_receipt_proposal` FIFO tests out of scope and out of the envelope                              | launch final-state                                             |

CRITICAL findings: none. Archive was not blocked.

Archived `state.yaml` still records `phase: tasks`,
`tasks_progress.pending: ["1.1-4.4"]`, `applyState: blocked`, and
`blocked(edit_authority_missing)` for nebula-agent. That file is an earlier cycle
snapshot. It does **not** describe close: tasks are 21/21 `[x]`, verify admitted
`pass_with_warnings`, and this folder is the archive. The file was not rewritten
(immutable audit trail).

## Task Completion Gate

Inspected `openspec/changes/align-allocation-contracts/tasks.md` before merge/move. Zero
`- [ ]` implementation tasks. Phases 1–4 (1.1–4.4) are all `[x]` (21/21). Gate passed;
no archive-time checkbox reconciliation. Archived `tasks.md` still shows 21/21 `[x]`.

## Native Review Receipt Gate

Structured status `reviewGate` is structurally absent. No review
transaction/ledger/receipt was read and none was invented. Archive proceeded under
ordinary repository policy. No `sdd-attempt acquire` (archive is not runtime-bearing).

## Destructive / backward-incompatible deltas

`openspec/config.yaml` `rules.archive` requires a warning before merging destructive or
backward-incompatible deltas. No `REMOVED` / `RENAMED` sections. No large unrelated
requirement blocks were deleted. Deltas ADDED and MODIFIED only. Merge proceeded.

Behavioral expansions now in main specs (not section deletions):

1. **Seven catalog XMLIDs + 19.0.1.40.0 allow-list union.** `echeck`, `cash`, and
   `retention_certificate` join the four prior codes; upgrade unions without dropping
   extras; new companies start with all seven enabled.
2. **Payment field contract expands.** Seven `document_type` codes plus
   `retention_kind`; cash persists without designated proof.
3. **MCP proof MIME alias and cash omit.** `image/jpg` equals `image/jpeg`; cash may
   omit or null attachment.
4. **Provenance includes `retention_kind`.** Nested dumps accept decimal-string amounts
   and JSON null-as-omit; cash may omit `raw_ocr`.
5. **Strict nested-key parse.** `extra=forbid` on request/payment/receipt/value/
   application/nests; type-foreign nest keys rejected.
6. **MCP write accepts six dump types.** `unsupported` still `UserError` with zero
   writes.
7. **Receipt amounts accept decimal strings.** Application `number` MAY be JSON null.

## Specs synced to source of truth

Main specs **already existed**. Deltas were **merged** by requirement name (not created,
not blindly overwritten). Requirements not named in a delta were preserved
(byte-identical to the pre-merge backup). MODIFIED blocks were replaced with the delta’s
full requirement text (byte-identical to the delta section block after span rstrip).
ADDED blocks were appended.

| Domain                 | Action           | Details                                                                                                                                                                                                                                                                                                                                                                              |
| ---------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| collection-vouchers    | Updated (merged) | ADDED 1 (`Catalog XMLIDs and 19.0.1.40.0 allow-list union`); MODIFIED 5 (`Payment field contract`, `MCP optional payment attachment on create`, `Typed provenance copies of payment fields`, `MCP nested provenance on all-new create`, `Collection Settings persistence`); REMOVED 0; RENAMED 0. Untouched 31 of 36 original requirements. Main now 37 requirements, 125 scenarios. |
| collection-allocations | Updated (merged) | ADDED 1 (`Strict nested-key parse of dump payloads`); MODIFIED 2 (`MCP create_collection_allocation`, `MCP receipts payload`); REMOVED 0; RENAMED 0. Untouched 15 of 17 original requirements. Main now 18 requirements, 73 scenarios.                                                                                                                                               |

Main spec paths:

- `openspec/specs/collection-vouchers/spec.md`
- `openspec/specs/collection-allocations/spec.md`

## Known warnings at close (not blockers)

Per launch final-state (still true; also recorded in `verify-report` at verification
time). Not CRITICAL. Archive allowed.

1. Scenario "Over-split refused" is PARTIAL: covering test is applied > funded, not the
   spec GIVEN of payment 50 / values summing to 51.
2. Advertised amount schema stays MuK-safe `"number"` while runtime accepts decimal
   strings.

Sibling `collection_receipt_proposal` FIFO tests were out of scope and out of the
envelope. They are not a remaining defect of this change.

A first verify FAIL was remediated before this close by filling Document Review queue
current keys from `_REVIEW_EDITABLE_FIELD_ORDER` (includes `retention_kind`). That
remediation is done. Do not treat the historical FAIL as current state.

## Mechanical copy and move

- Main specs existed: no full-spec `cp` into `openspec/specs/`. Merge was requirement-
  block splice (ADDED append / MODIFIED replace). Unrelated requirements preserved
  byte-for-byte vs `/tmp/sdd-archive-main-spec-backup/`.
- Change folder was **untracked** (`git ls-files` empty). `git mv` failed with
  `fatal: source directory is empty, source=openspec/changes/align-allocation-contracts, destination=openspec/changes/archive/2026-09-06-align-allocation-contracts`.
  Fallback `mv` succeeded.
- Archive path: `openspec/changes/archive/2026-09-06-align-allocation-contracts/`
- Active path `openspec/changes/align-allocation-contracts/` is gone after the move.
- Pre-move recursive snapshot compared with `diff -r`. Empty diff (exit 0). This report
  is additive and was written after that comparison.
- Sibling `openspec/changes/2026-09-04-document-review-editable-ocr/` was not moved or
  edited.
- Archive operations stayed inside the collection OpenSpec tree. nebula-agent was not
  edited by archive.
- `state.yaml` moved with the change folder. Orchestrator state was not rewritten here.

### Verbatim `diff -r` (empty = pass)

DIFF 1 — change folder vs pre-move snapshot after `cp -R` (cmd:
`diff -r openspec/changes/align-allocation-contracts /tmp/sdd-archive.UlI61r/source`):

```
diff1_exit=0
```

(no differences)

DIFF 2 — pre-move snapshot vs archived tree after `mv` (cmd:
`diff -r /tmp/sdd-archive.UlI61r/source openspec/changes/archive/2026-09-06-align-allocation-contracts`):

```
diff2_exit=0
```

(no differences)

## Archive contents

- proposal.md
- exploration.md
- design.md
- tasks.md (21/21 complete; no unchecked implementation tasks)
- specs/collection-vouchers/spec.md
- specs/collection-allocations/spec.md
- apply-progress.md
- verify-report.md
- state.yaml (stale intermediate phase label; not rewritten)
- .gentle-ai-instance
- archive-report.md (this file; additive after move)

## Out of scope (untouched)

This archive did not edit production Python/XML, tests, manifests, or nebula-agent.
Sibling OpenSpec change `2026-09-04-document-review-editable-ocr` remains under
`openspec/changes/`. Coordinated apply already shipped; archive only merged main specs
and moved this change folder.

## Risks at close

- Archived `state.yaml` still says tasks pending / apply blocked; readers must use this
  report and `tasks.md` / `verify-report.md` for close state.
- Over-split full-split equality (payment 50 / values 51) remains PARTIAL coverage.
- Advertised MCP amount JSON schema stays `"number"` while runtime accepts decimal
  strings.
- Document Review OWL labels/views/reports were intentionally unchanged; queue payload
  now includes `retention_kind` among current keys.
