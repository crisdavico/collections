# Apply Progress: collection-receipts

**Mode**: Strict TDD **Work unit**: Phase 4 Tests (tasks 4.1–4.3) **Delivery**:
auto-chain / stacked-to-main **Attempt token**:
`sha256:9dd4f6c625141de7b805e3a2265678c38d0441bf88622ce2f0fd58cc7544e084` (not settled)

## Completed Tasks

- [x] 1.1–1.7 Phase 1 models/ACL/1.34.0 (prior slice; not reverted)
- [x] 2.1–2.8 Phase 2 MCP persist (prior slice; not reverted)
- [x] 3.1–3.9 Phase 3 Close / UI (prior slice; not reverted)
- [x] 4.1 RED/GREEN `tests/test_collection_allocation.py`: freeze `receipt_ids`;
      closed/cancelled guards; unlink cascade.
- [x] 4.2 RED/GREEN `tests/test_collection_receipt_split.py`: amend rebuilds; amend
      without splits.
- [x] 4.3 `tests/__init__.py` already imports `test_collection_receipt` +
      `test_collection_receipt_split`; scoped pre-commit.

## Remaining

None — 27/27 tasks `[x]`.

## TDD Cycle Evidence

| Task | Test File                                | Layer       | Safety Net                                          | RED                                                            | GREEN                | TRIANGULATE                                                                                                             | REFACTOR                                         |
| ---- | ---------------------------------------- | ----------- | --------------------------------------------------- | -------------------------------------------------------------- | -------------------- | ----------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| 4.1  | `tests/test_collection_allocation.py`    | Integration | existing freeze/closed/unlink without `receipt_ids` | ✅ Written (`receipt_ids` Command.create/unlink; cascade ids)  | ✅ Passed            | ✅ confirmed freeze vs draft writable; closed vs cancelled refuse vs proposal writable; draft cascade vs confirmed keep | ✅ B023 default-arg on receipt `line_ids` lambda |
| 4.2  | `tests/test_collection_receipt_split.py` | Integration | existing amend-with-splits                          | ✅ Written (rebuild drops old receipt ids; no-splits superset) | ✅ Passed            | ✅ splits add quotation uniquely vs no-splits keeps one invoice + unsplit extra                                         | ➖ None needed                                   |
| 4.3  | `tests/__init__.py`                      | Structural  | both modules already imported                       | ➖ Import already present                                      | ✅ pre-commit exit 0 | ➖ Single: import + lint                                                                                                | ➖ None needed                                   |

### Test Summary

- **Total tests written (Phase 4)**: 7 allocation freeze/guard/unlink + 1
  amend-without-splits (plus rebuild-id asserts on existing amend-with-splits)
- **Total tests passing**: `invoke test -m collection --mode=update` → **0 failed, 0
  error(s) of 736 tests** (`collection: 804 tests 38.29s`)
- **Layers used**: Unit (0), Integration (Odoo TransactionCase), E2E (0)
- **Approval tests** (refactoring): existing freeze/closed/unlink without receipts;
  existing amend-with-splits
- **Pure functions created**: 0

## Work Unit Evidence

| Evidence                                          | Required value                                                                                                                                                                                                                                                                                                                                                                      |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `invoke test -m collection --mode=update` → exit 0, **0 failed, 0 error(s) of 736 tests** (`collection: 804 tests 38.29s`)                                                                                                                                                                                                                                                          |
| Runtime harness command/scenario and exact result | Same command `-u collection` then TransactionCase freeze `receipt_ids`, closed/cancelled guards, draft unlink cascade, MCP amend rebuild / no-splits compat                                                                                                                                                                                                                         |
| Rollback boundary                                 | `tests/test_collection_allocation.py` (receipt freeze/guard/unlink cases + helpers); `tests/test_collection_receipt_split.py` (amend rebuild ids + no-splits); `tests/__init__.py` (already imported); `tests/test_collection_company_migration.py` whitespace-collapsed AGENTS pin; `models/collection_receipt.py` B023 default-arg. Do not revert Phase 1–3 models/persist/views. |

## Deviations

None — leftover tests match design freeze `receipt_ids`, closed/cancelled guards, draft
unlink cascade, and amend rebuild / compat-without-splits. Pin
`test_agents_md_four_state_workflow` now collapses whitespace (same as `one-open`) so
prettier wrap of AGENTS.md cannot fail the suite. Minimal B023 default-arg on derived
`line_ids` lambda.
