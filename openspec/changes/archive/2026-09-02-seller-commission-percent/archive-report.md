# Archive Report: seller-commission-percent

**Archived**: 2026-09-02 **Change**: `seller-commission-percent` **Store**: openspec
(filesystem only; Engram not used — `mem_save` skipped) **Status**: success
**reviewGate**: structurally absent (no review discovered; archive proceeded under
ordinary policy)

## Final state at close

These facts outrank intermediate `apply-progress` / `verify-report` snapshots.
Launch-prompt final-state facts and persisted `tasks.md` agree; warnings at verify time
remain true at close (no later fix commits).

| Fact                       | Value                                                            | Authority                                        |
| -------------------------- | ---------------------------------------------------------------- | ------------------------------------------------ |
| Implementation tasks       | 8/8 `[x]`; pending 0                                             | persisted `tasks.md` (1.1–4.2)                   |
| Verify verdict             | `pass_with_warnings`; blockers 0; critical_findings 0            | launch final-state + `verify-report.md` envelope |
| Requirements / scenarios   | 8/8, 21/21                                                       | launch final-state + `verify-report.md` header   |
| Collection version shipped | `19.0.1.29.0` (sibling took `19.0.1.28.0`)                       | launch final-state                               |
| SQLite version shipped     | `19.0.1.6.0`                                                     | launch final-state                               |
| Nebula / MCP payload       | no nebula-agent change; `get_seller_id` still `{seller_id}` only | launch final-state                               |

CRITICAL findings: none. Archive was not blocked.

Open non-critical warnings at close (still true; not CRITICAL):

1. Sibling dirty tree remains live (`draft-until-close` / `collection-sheet-report`
   still active; this executor did not touch them).
2. SQLite `TestSqliteConnector.test_rollback_vouchers_sheets_mcp_unchanged` remains
   excluded by test tag (pre-existing ERROR; not started). Per `verify-report.md` at
   verification time, and launch final-state confirms no later fix.

## Task Completion Gate

Inspected `openspec/changes/seller-commission-percent/tasks.md` before merge/move. Zero
`- [ ]` implementation tasks. Phases 1–4 (1.1–4.2) are all `[x]`. Gate passed; no
archive-time checkbox reconciliation.

## Native Review Receipt Gate

Structured status `reviewGate` is structurally absent. No review
transaction/ledger/receipt was read. Archive proceeded under ordinary repository policy.
No review was started.

## Destructive / backward-incompatible deltas (orchestrator authorized)

`openspec/config.yaml` `rules.archive` requires a warning before merging destructive or
backward-incompatible deltas. The orchestrator launch explicitly named this merge and
authorized archive. Merged; not re-asked.

1. **MODIFIED "SQLite read-only customer debt source"** drops
   `` `database.sql` MUST NOT change ``. The freeze is lifted so sample seller
   `commission_percent` may ship in `database.sql`. Invoice/customer schema and
   read-only file behavior remain. Recorded as `(Previously: froze database.sql.)` on
   the main spec.

This is a spec-constraint relaxation, not a large-section deletion. No REMOVED/RENAMED
sections existed.

## Specs synced to source of truth

Delta `openspec/changes/seller-commission-percent/specs/collection-connectors/spec.md`
merged into existing main spec. Requirements not named in the delta were preserved.

| Domain                | Action  | Details                                                                                                                                                                                                                                                                                                                                    |
| --------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| collection-connectors | Updated | ADDED 4 (`Seller binding stores commission percent`, `Readonly commission UI`, `MCP get_seller_id omits commission`, `Sample seller commission rates`); MODIFIED 4 (`Normalized seller list output`, `Import replaces Enabled Sellers`, `SQLite read-only sellers source`, `SQLite read-only customer debt source`). REMOVED 0. RENAMED 0. |

Main spec path:

- `openspec/specs/collection-connectors/spec.md`

Preserved (not in delta): Company-scoped connector; Active-company list routing; Fail
closed without leakage; No MCP seller list; Binding uniqueness; List is not collect
permission; Read-only MCP tool list_collection_customers; Internal caller and Enabled
Seller; Binding resolution and adapter dispatch; Normalized customer list output;
Read-only MCP tool customer_debt; Internal caller and Enabled Seller for customer_debt;
Unknown inactive or other-seller customer rejected; Binding resolution and adapter
dispatch for customer debt; Normalized customer debt output; Storage-agnostic collection
addon; SQLite read-only customers source; Company isolation; Rollback unchanged; Write
path may create partners and bindings; Customer binding uniqueness; Customer partner
resolution; Customer binding ACL.

## Mechanical move

- Change folder was **untracked**. `git mv` failed with
  `fatal: source directory is empty`. Fallback `mv` succeeded.
- Archive path: `openspec/changes/archive/2026-09-02-seller-commission-percent/`
- Active path `openspec/changes/seller-commission-percent/` is gone after the move.
- Pre-move recursive snapshot compared with `diff -r`. Empty diff (exit 0). This report
  is additive and was written after that comparison.

Collision-guarded sibling paths were not edited: `openspec/changes/draft-until-close/`,
`openspec/changes/collection-sheet-report/`, allocation/voucher/sheet models, MCP
allocation tools, security CSV, allocation tests, allocation views,
`migrations/19.0.1.28.0/`, `collection_sheet_template.xlsx`.

## Archive contents

- proposal.md
- exploration.md
- design.md
- tasks.md (8/8 complete; no unchecked implementation tasks)
- specs/collection-connectors/spec.md
- apply-progress.md
- verify-report.md
- state.yaml
- archive-report.md (this file; additive after move)

## Attempt

No new token was present in the archive executor launch (the verify token in the prompt
was explicitly stale). Per orchestrator instruction, this executor did not call
`sdd-attempt acquire` or `settle`. Parent holds the archive acquire for request-id
`seller-commission-percent-archive`.

## Risks at close

- Sibling dirty tree remains; another agent is live on allocation/sheet/voucher
  surfaces. Not a defect of this change.
- SQLite rollback test `test_rollback_vouchers_sheets_mcp_unchanged` remains excluded.
  Pre-existing ERROR (`collection.voucher` has no `customer_identification`); not
  CRITICAL for this change.
- Version bump shipped as `19.0.1.29.0` because sibling occupied `19.0.1.28.0`; design
  text that named 1.28.0 is historical, not an open gap.
