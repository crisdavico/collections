# Apply Progress: typed-voucher-line-views

**Change**: typed-voucher-line-views **Mode**: Strict TDD **Work unit**:
phase-3-quality-gate — complete **Updated**: 2026-08-11 **Delivery**: single PR OK
(ask-on-risk resolved; Medium 400-line risk; Chained PRs: No)

## Completed Tasks

### Phase 1 / unit-1-typed-form-tables

- [x] 1.1 RED: three stacked typed lists UI arch tests
- [x] 1.2 RED: default_document_type context persistence (arch + ORM)
- [x] 1.3 GREEN: voucher form stacked typed editable lists; mono list removed
- [x] 1.4 GREEN helpers: skipped — design approach A (triple `payment_ids`) sufficient
- [x] 1.5 Verify: `invoke install -m collection` exit 0; focused tests green

### Phase 2 / unit-2-payment-lines-menu

- [x] 2.1 RED: Payment Lines menu/action UI tests (res_model, create/edit false, search
      fields)
- [x] 2.2 RED: unsupported absent from typed form domains; Payment Lines unsupported
      filter
- [x] 2.3 GREEN: line list + search views, act_window, menuitem under Collections
- [x] 2.4 Verify: `invoke install -m collection` exit 0;
      `invoke test -m collection --mode=update` green

### Phase 3 / phase-3-quality-gate

- [x] 3.1 Scoped pre-commit clean (after autofix + docstring E501 fix)
- [x] 3.2 `invoke test -m collection --mode=update` green including MCP suite
- [x] 3.3 Manual smoke N/A — `seedian-odoo-1` Exited (137); TransactionCase UI coverage
      used

## Files Changed

| File                                                          | Action   | What Was Done                                                  |
| ------------------------------------------------------------- | -------- | -------------------------------------------------------------- |
| `tests/test_collection_ui.py`                                 | Modified | Phase 1–2 tests; Phase 3 shortened docstring for ruff E501     |
| `views/collection_views.xml`                                  | Modified | Phase 1 typed form lists; Phase 2 line list/search/action/menu |
| `README.md`                                                   | Modified | Phase 3 trailing-whitespace autofix via pre-commit             |
| `openspec/changes/typed-voucher-line-views/tasks.md`          | Modified | Phase 1–3 tasks marked `[x]`                                   |
| `openspec/changes/typed-voucher-line-views/state.yaml`        | Modified | apply done; next verify; phase-3 completed                     |
| `openspec/changes/typed-voucher-line-views/apply-progress.md` | Updated  | Cumulative Phase 1–3 evidence                                  |

## TDD Cycle Evidence

| Task    | Test File                                 | Layer                       | Safety Net                                           | RED                                                                                   | GREEN                                        | TRIANGULATE                                          | REFACTOR                                |
| ------- | ----------------------------------------- | --------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------- | -------------------------------------------- | ---------------------------------------------------- | --------------------------------------- |
| 1.1     | `tests/test_collection_ui.py`             | Unit (TransactionCase arch) | ✅ 46/46 (`invoke test -m collection --mode=update`) | ✅ Written — 4 fail + 1 error before views                                            | ✅ Passed after form update                  | ✅ `test_form_typed_lists_field_sets_differ_by_type` | ✅ `_field_names` → `.//field` (scoped) |
| 1.2     | `tests/test_collection_ui.py`             | Unit (arch + ORM create)    | ✅ included above                                    | ✅ Written — failed until typed arch contexts exist                                   | ✅ Passed (`default_document_type` persists) | ✅ omit `document_id` cash_deposit path              | ➖ None needed                          |
| 1.3     | (production) `views/collection_views.xml` | —                           | —                                                    | —                                                                                     | ✅ Minimal typed lists + separators          | —                                                    | ➖ Clean as-designed                    |
| 1.4     | N/A                                       | —                           | —                                                    | ➖ Not needed                                                                         | ➖ Skipped (A sufficient)                    | ➖                                                   | ➖                                      |
| 1.5     | verify                                    | Integration harness         | —                                                    | —                                                                                     | ✅ install + tests                           | —                                                    | —                                       |
| 2.1     | `tests/test_collection_ui.py`             | Unit (TransactionCase arch) | ✅ 0 failed / 50 tests (Phase 1 baseline)            | ✅ Written — 3 ERROR (missing xmlids) before views                                    | ✅ Passed after line views/action/menu       | ✅ `test_payment_lines_search_exposes_filter_fields` | ➖ None needed                          |
| 2.2     | `tests/test_collection_ui.py`             | Unit (arch + ORM domain)    | ✅ included above                                    | ✅ Written — filter xmlid ERROR; absent-from-typed already green from Phase 1 domains | ✅ Passed after unsupported search filter    | ✅ ORM search by `document_type=unsupported`         | ➖ None needed                          |
| 2.3     | (production) `views/collection_views.xml` | —                           | —                                                    | —                                                                                     | ✅ list/search/action/menu                   | —                                                    | ➖ Optional type columns on list        |
| 2.4     | verify                                    | Integration harness         | —                                                    | —                                                                                     | ✅ install + `--mode=update` tests           | —                                                    | —                                       |
| 3.1–3.3 | quality gate                              | Lint + full suite           | ✅ see Phase 3 evidence                              | ➖ N/A (gate)                                                                         | ✅ pre-commit + tests                        | ➖                                                   | ✅ E501 docstring shorten               |

### Test Summary

- **Total new/updated behavioral tests (Phase 2)**: 4 methods
  (`test_payment_lines_menu_and_action_read_only`,
  `test_payment_lines_search_exposes_filter_fields`,
  `test_unsupported_absent_from_typed_form_tables`,
  `test_unsupported_findable_via_payment_lines_filter`)
- **Total tests passing (module run, Phase 3)**: 0 failed, 0 error(s) of 54 tests
  (`collection` stats reported 66)
- **MCP suite (`test_collection_mcp_tool`)**: 12 tests started; all green within the
  module run (no MCP intentional changes)
- **Layers used**: Unit/TransactionCase (arch + ORM); Integration
  (`invoke test --mode=update`)
- **Approval tests**: None — behavior change, not pure refactor
- **Pure functions created**: 0 (Odoo view/ORM surface)

## Work Unit Evidence

### Unit 1 (retained)

| Evidence                                          | Value                                                                          |
| ------------------------------------------------- | ------------------------------------------------------------------------------ |
| Focused test command and exact result             | `invoke test -m collection --mode=update` → `0 failed, 0 error(s) of 50 tests` |
| Runtime harness command/scenario and exact result | `invoke install -m collection` → exit 0                                        |
| Rollback boundary                                 | Revert form views + UI tests; no model/schema/MCP changes                      |

### Unit 2 (retained)

| Evidence                                          | Value                                                                                                                                                                                                                              |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `invoke test -m collection --mode=update` → RED `0 failed, 3 error(s) of 54 tests` (missing xmlids); GREEN `0 failed, 0 error(s) of 54 tests`                                                                                      |
| Runtime harness command/scenario and exact result | `invoke install -m collection` → exit 0. Note: doodba install uses `--init` (may no-op when already installed); view load confirmed via test-mode `-u`. Live `docker exec … -u collection` skipped — `seedian-odoo-1` not running. |
| Rollback boundary                                 | Revert Payment Lines list/search/action/menu in `views/collection_views.xml` + Phase 2 methods in `tests/test_collection_ui.py` (+ OpenSpec progress); leaves Phase 1 typed form intact; no model/schema/MCP changes               |

### Phase 3 quality gate (this batch)

| Evidence                                          | Value                                                                                                                                                                       |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `invoke test -m collection --mode=update` → exit 0; `0 failed, 0 error(s) of 54 tests`; MCP: 12 `TestCollectionMcpTool.*` methods green                                     |
| Runtime harness command/scenario and exact result | Manual UI smoke N/A — `seedian-odoo-1` status `exited` (exit 137). Relied on TransactionCase UI arch/ORM tests already green.                                               |
| Rollback boundary                                 | Phase 3 lint-only fix: docstring in `tests/test_collection_ui.py` + trailing-whitespace in `README.md` / apply-progress; feature rollback remains Units 1–2 view/test files |

## Phase 3 Evidence (commands + exit codes)

### 3.1 pre-commit

```bash
# from seedian root; explicit file list (glob ** not expanded by shell)
pre-commit run --files odoo/custom/src/private/collection/...
```

| Run                           | Exit | Notes                                                                                          |
| ----------------------------- | ---- | ---------------------------------------------------------------------------------------------- |
| 1st                           | 1    | ruff E501 docstring line 391; trailing-whitespace autofixed `apply-progress.md`, `README.md`   |
| 2nd (after docstring shorten) | 0    | All hooks Passed. Optional pylint C8101 `manifest-required-author` warning only (hook Passed). |

### 3.2 tests (incl. MCP)

```bash
invoke test -m collection --mode=update
```

| Result    | Value                                                                  |
| --------- | ---------------------------------------------------------------------- |
| Exit code | 0                                                                      |
| Summary   | `0 failed, 0 error(s) of 54 tests when loading database 'devel'`       |
| Stats     | `collection: 66 tests 1.40s 1880 queries`                              |
| MCP file  | `tests/test_collection_mcp_tool.py` — 12 methods executed, no failures |

MCP methods observed green:

1. `test_all_new_create_returns_voucher_and_payments`
2. `test_create_rejects_empty_document_id`
3. `test_create_rejects_empty_payments`
4. `test_create_rejects_missing_document_id`
5. `test_cross_voucher_conflict_rejects_no_writes`
6. `test_exact_retry_returns_same_ids_no_new_rows`
7. `test_in_call_duplicate_document_id_rejects_no_writes`
8. `test_partial_conflict_rejects_no_writes`
9. `test_portal_user_denied_no_writes`
10. `test_tool_discovered_with_write_registry_and_schema`
11. `test_unique_violation_full_match_replays`
12. `test_unique_violation_partial_match_rejects`

### 3.3 manual smoke

N/A — `docker inspect seedian-odoo-1` → `State.Status=exited` (prior exit 137). Did not
start long-running UI for browser E2E. Coverage from `test_collection_ui.py` (typed form
stacks, Payment Lines menu/filters, unsupported filter) under 3.2.

## Deviations from Design

None — Payment Lines menu is read-only via action context
`{'create': False, 'edit': False}` plus list `create="false" edit="false"`; `view_mode`
is `list` only (design allowed list-only). Unsupported filter present on line search.

## Issues Found

None blocking. Live odoo container stopped during Phase 3; quality gate used invoke test
harness + TransactionCase UI. Optional pylint C8101 author warning pre-exists on
`__manifest__.py` (not introduced by this change; mandatory pylint Passed).

## Remaining Tasks

None for apply. Next: `sdd-verify`.

## Workload / PR Boundary

- Mode: single PR
- Current work unit: phase-3-quality-gate (complete)
- Boundary: lint fix + verification only; Units 1+2 feature work retained
- Estimated review budget impact: still Medium 400-line risk for single PR
- Next: `sdd-verify`
