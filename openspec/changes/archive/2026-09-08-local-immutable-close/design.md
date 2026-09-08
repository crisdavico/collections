# Design: Local Immutable Close

## Technical Approach

Strip connector dispatch from `action_close()`. Close stays `proposal`-only and one ORM
transaction: draft receipts → `closed` (`external_receipt_id` unset), allocations →
`confirmed`, sheet → `closed`. Keep `create_receipt` unused from Close. Add receipt
Selection `closed` with audited `draft ↔ closed`. Cancel from `closed` reopens those
receipts; `issued` untouched. Call `raise_if_sheet_frozen` on associate CRUD. Manifest
`19.0.1.44.0`; no migrate folder. MCP Seller Close unchanged.

## Architecture Decisions

| Decision      | Options                                  | Tradeoff                                        | Choice                                                                                                                                              |
| ------------- | ---------------------------------------- | ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Close I/O     | Keep `create_receipt` in Close vs strip  | ERP-gated vs local freeze                       | Strip dispatch; keep dispatcher unused                                                                                                              |
| Empty drafts  | Skip empty (today) vs close every draft  | Old dispatch filter vs settled “draft → closed” | Every `state==draft` receipt → `closed`                                                                                                             |
| Receipt state | Context-only vs sheet-style intercept    | Extra RPC vs existing audited pattern           | Intercept raw `state` writes; `collection_receipt_audited_state` for `draft↔closed`; keep `collection_receipt_issuing` for leftover `issued` stamps |
| Freeze        | Copy checks vs `raise_if_sheet_frozen`   | Drift vs one helper                             | Call the helper on create/write/unlink of listed models; voucher membership stays `ADMIN_EDITABLE_SHEET_STATES`                                     |
| Bypass        | `sudo()` vs listed contexts              | Too wide vs chatter breakage                    | Audited sheet/allocation/receipt state, `collection_allocation_parent_unlink`, `collection_sheet_unlinking`. Not `message_post`                     |
| Migration     | SQL remap `issued` vs additive Selection | Backfill vs varchar                             | No SQL; `issued` rows stay                                                                                                                          |

Rejected: feature-flag Close; deleting `create_receipt`; remapping `issued`; routing
voucher freeze through `FROZEN_SHEET_STATES`.

## Data Flow

### Close

```
Admin Close
  → action_close (proposal only; else UserError)
       1. receipt drafts --collection_receipt_audited_state--> closed
          (no external_receipt_id write)
       2. allocations --collection_allocation_audited_state--> confirmed
       3. sheet --collection_sheet_audited_state--> closed
       4. allocations._check_sheet_state_iff()
  connector.create_receipt  ✗ never called
```

One PostgreSQL transaction. Any `UserError` rolls back all three writes.

### Cancel from closed

```
Admin Cancel (submitted | proposal | closed)
  → receipts state==closed --audited--> draft   (issued skipped)
  → sheet --audited--> cancelled
  → allocations --audited--> draft
  → _check_sheet_state_iff()
Frozen until Reinstate → submitted
  (reopened receipts stay draft; issued stay issued)
```

Receipt reopen must use the audited context because the sheet is already
`closed`/`cancelled` (`FROZEN_SHEET_STATES`).

## File Changes

| File                                         | Action | Description                                                              |
| -------------------------------------------- | ------ | ------------------------------------------------------------------------ |
| `models/collection_sheet.py`                 | Modify | Strip Close dispatch; close all drafts; Cancel reopens `closed` receipts |
| `models/collection_receipt.py`               | Modify | Selection `closed`; intercept `state`; freeze on create                  |
| `models/collection_receipt_value.py`         | Modify | Freeze on create                                                         |
| `models/collection_common.py`                | Modify | Document bypass contexts; keep `raise_if_sheet_frozen`                   |
| `models/collection_allocation.py`            | Modify | Freeze on create (`sheet_id`)                                            |
| `models/collection_allocation_line.py`       | Modify | Freeze on create                                                         |
| `models/collection_allocation_revision.py`   | Modify | Freeze on create after revision gate                                     |
| `models/collection_cash_replacement.py`      | Modify | Freeze on create after replacement gate                                  |
| `views/collection_receipt_views.xml`         | Modify | Search filter Closed                                                     |
| `__manifest__.py`                            | Modify | `19.0.1.44.0`                                                            |
| `AGENTS.md`                                  | Modify | Local Close; receipt `closed`; freeze create                             |
| `tests/test_collection_receipt.py`           | Modify | RED first: no connector; `closed`; Cancel reopen; raw state reject       |
| `tests/test_collection_sheet.py`             | Modify | Close/Cancel/Reinstate cycle                                             |
| `tests/test_collection_allocation.py`        | Modify | Frozen create of header/line/revision                                    |
| `tests/test_collection_voucher.py`           | Modify | Preserve membership freeze                                               |
| `tests/test_collection_company_migration.py` | Modify | Pin `19.0.1.44.0`; no `migrations/19.0.1.44.0/`                          |

No deletes. Do not add `migrations/19.0.1.44.0/`.

## Interfaces / Contracts

```python
# collection.receipt.state
("draft", "Draft"), ("closed", "Closed"), ("issued", "Issued")

# Close/Cancel only
collection_receipt_audited_state  # draft ↔ closed
collection_receipt_issuing        # issued stamp; unused from Close
```

Private helpers on `collection.receipt`: `_action_mark_closed()` (draft-only) and
`_action_reopen_closed()` (`closed`-only). Sheet Close/Cancel call them. Raw
`write({"state": ...})` without those contexts MUST `UserError`. `issued` stays
write/unlink-immutable. `UNIQUE(external_receipt_id)` unchanged (NULL allowed). MCP
tools unchanged.

Sheet write when frozen: only audited `state` plus chatter inverses. Recon freeze stays
on `collection_sheet_report.write`.

## Testing Strategy

| Layer                    | What to Test                                                                                                                    | Approach                                                       |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| Unit (`TransactionCase`) | Close without connector; all drafts `closed`; `issued` untouched; audited reject; Cancel reopen; freeze create on listed models | Strict TDD: rewrite receipt Close tests first (RED), then code |
| Integration              | Same transaction; Confirm still `submitted` → `proposal`                                                                        | Existing sheet tests                                           |
| E2E                      | N/A                                                                                                                             | No tours                                                       |

Rewrite `test_close_issues_*` and `test_close_missing_connector_rolls_back`. Empty-draft
test must expect `closed`. Run `invoke test -m collection --mode=update`. Satellite
`collection_receipt_proposal` after upgrade (out of this addon).

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification,
or process-integration boundary.

## Migration / Rollout

No SQL. Additive Selection. `-u collection` to `19.0.1.44.0`. Rollback: revert to
`19.0.1.43.0`; leftover varchar `closed` is unused but valid. Close again requires a
connector.

## Open Questions

- None. Constraints settled.
