# Apply Progress: Sheet Form Allocations Only

**Change**: `sheet-form-allocations-only` **Mode**: Strict TDD **Work unit**: Phase 3
docs and quality **Request id**: `apply-phase-3-docs-20260902`

Phase 1 RED and Phase 2 GREEN are preserved below. This batch is Phase 3 only
(`AGENTS.md` UI/map docs + quality). Production model/XML were not reopened.

## Completed Tasks

- [x] 1.1 Invert notebook test → `test_sheet_form_notebook_allocations_only`
- [x] 1.2 Invert statusbar test (drop `voucher_ids`); leave partner_id uniqueness
- [x] 1.3 Add stat-button arch test
- [x] 1.4 Add voucher `sheet_id` arch test (list/form/search; kanban must not add)
- [x] 1.5 Add `voucher_count` + `action_open_vouchers` model tests
- [x] 1.6 Add unsaved `.new()` `UserError`; keep Document Review `.new()`; run suite RED
- [x] 2.1 Model: `voucher_count`, `action_open_vouchers`, generalize
      `_ensure_saved_sheet`
- [x] 2.2 Sheet form XML: button box, drop Vouchers page, allocations `partner_id`
- [x] 2.3 Voucher XML: list/form/search `sheet_id`; leave kanban
- [x] 2.4 Run suite — GREEN
- [x] 3.1 `AGENTS.md` UI bullet + repository map row
- [x] 3.2 Scoped pre-commit + re-run tests

## TDD Cycle Evidence

| Task | Test File                                                                        | Layer               | Safety Net                                                 | RED                                                                                            | GREEN                                                                                    | TRIANGULATE                                                                                 | REFACTOR                                                               |
| ---- | -------------------------------------------------------------------------------- | ------------------- | ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| 1.1  | `tests/test_collection_ui.py`                                                    | Unit (arch)         | ✅ unmodified UI tests still pass (501/509)                | ✅ Written — FAIL `['Vouchers', 'Allocations'] != ['Allocations']`                             | ✅ Passed — notebook `['Allocations']` only                                              | ✅ Allocations-only + absence of `SHEET_NOTEBOOK_VOUCHERS` / `voucher_ids` + Customer order | ➖ None needed                                                         |
| 1.2  | `tests/test_collection_ui.py`                                                    | Unit (arch)         | ✅ invert-by-removal; statusbar still GREEN                | ✅ Written — dropped `voucher_ids` required/many2many asserts so Phase 2 XML can drop the page | ✅ Passed leftover Close/Reopen/DR after XML drop                                        | ➖ Single — invert of existing statusbar; absence covered by 1.1                            | ➖ None needed                                                         |
| 1.3  | `tests/test_collection_ui.py`                                                    | Unit (arch)         | ✅ existing file                                           | ✅ Written — FAIL first child `'field' != 'div'`                                               | ✅ Passed — first `<sheet>` child is `oe_button_box`                                     | ✅ button box + `oe_stat_button` + `statinfo` + `invisible="not id"`                        | ➖ None needed                                                         |
| 1.4  | `tests/test_collection_ui.py`                                                    | Unit (arch)         | ✅ existing file                                           | ✅ Written — FAIL list `sheet_id` count `0 != 1`                                               | ✅ Passed — list/form/search expose `sheet_id`; kanban does not                          | ✅ list optional-hide + form after `seller_id` + search field/groupby + kanban must not add | ➖ None needed                                                         |
| 1.5  | `tests/test_collection_sheet.py`                                                 | Unit (model)        | ✅ existing file                                           | ✅ Written — ERROR `KeyError: voucher_count` and `AttributeError: action_open_vouchers`        | ✅ Passed — non-stored count + hand-built act_window                                     | ✅ empty 0 + N=2 members + per-sheet domain/context                                         | ➖ None needed                                                         |
| 1.6  | `tests/test_collection_sheet.py`                                                 | Unit (model)        | ✅ Document Review `.new()` still passes                   | ✅ Written — ERROR `AttributeError: action_open_vouchers` on `.new()`                          | ✅ Passed — unsaved `.new()` raises `UserError`                                          | ➖ Single unsaved path; Document Review `.new()` kept as companion                          | ➖ None needed                                                         |
| 2.1  | `tests/test_collection_sheet.py`                                                 | Unit (model)        | ✅ Phase 1 RED already failing (5 errors)                  | ✅ Inherited Phase 1.5/1.6 — no test rewrite                                                   | ✅ Passed — `voucher_count` + `action_open_vouchers` + generalized `_ensure_saved_sheet` | ✅ empty 0 + N=2 + two-sheet domain/context (Phase 1 cases)                                 | ➖ None needed — matches design.md dict                                |
| 2.2  | `tests/test_collection_ui.py`                                                    | Unit (arch)         | ✅ Phase 1 RED already failing (notebook + stat button)    | ✅ Inherited Phase 1.1–1.3 — no test rewrite                                                   | ✅ Passed — button box first; Allocations-only; one `partner_id`                         | ✅ Allocations Customer order + no `voucher_ids` + statinfo/`invisible="not id"`            | ➖ None needed                                                         |
| 2.3  | `tests/test_collection_ui.py`                                                    | Unit (arch)         | ✅ Phase 1 RED already failing (`sheet_id` list count)     | ✅ Inherited Phase 1.4 — no test rewrite                                                       | ✅ Passed — list optional-hide, form after `seller_id`, search field+groupby             | ✅ list + form + search + kanban-must-not-add                                               | ➖ None needed                                                         |
| 2.4  | `tests/test_collection_ui.py`, `tests/test_collection_sheet.py` plus full module | Unit (module suite) | ✅ freeze/reassign/dates/Document Review remained in suite | ✅ N/A — execution gate for 2.1–2.3                                                            | ✅ Passed — `0 failed, 0 error(s) of 509 tests`                                          | ➖ Suite gate, not a new behavior                                                           | ➖ None needed                                                         |
| 3.1  | `AGENTS.md`                                                                      | Docs                | N/A (docs one-liner)                                       | N/A — no new test; docs only                                                                   | ✅ UI bullet + repository map updated                                                    | ➖ Triangulation skipped: purely structural docs one-liner                                  | ➖ Prettier wrap on the UI paragraph only                              |
| 3.2  | quality gate                                                                     | Quality             | ✅ Phase 2 GREEN 509/509                                   | N/A — no new tests                                                                             | ✅ Owned-files pre-commit exit 0; `invoke test` exit 0                                   | ➖ Single quality gate                                                                      | ➖ Reverted prettier drive-by on archive + main specs + unrelated test |

### Test Summary

- **Total tests written / inverted (Phase 1)**: 8 methods (unchanged this batch)
- **Total tests passing this unit**: 509/509 (`0 failed, 0 error(s)`)
- **Suite (Phase 3 re-run)**: `collection: 565 tests 23.92s 40453 queries`; result line
  `0 failed, 0 error(s) of 509 tests when loading database 'devel'`
- **Layers used**: Unit (8 RED cases now GREEN), Integration (0 new), E2E (0), Docs (1),
  Quality (1)
- **Approval tests** (refactoring): 1.2 invert-by-removal of statusbar membership
  asserts (Phase 1)
- **Pure functions created**: 0 (Odoo compute + act_window dict)

### Phase 1 RED proof (historical; now GREEN)

**FAIL (3)** — Phase 1 only

- `TestCollectionUi.test_sheet_form_notebook_allocations_only` — notebook still
  `['Vouchers', 'Allocations']`
- `TestCollectionUi.test_sheet_form_stat_button_opens_vouchers` — first `<sheet>` child
  is `field`, not `oe_button_box`
- `TestCollectionUi.test_voucher_list_form_search_expose_sheet_id` — list has no
  `sheet_id`

**ERROR (5)** — Phase 1 only

- `TestCollectionSheet.test_empty_sheet_voucher_count_is_zero` —
  `KeyError: 'voucher_count'`
- `TestCollectionSheet.test_voucher_count_matches_member_count` —
  `KeyError: 'voucher_count'`
- `TestCollectionSheet.test_action_open_vouchers_returns_filtered_act_window` — no
  `action_open_vouchers`
- `TestCollectionSheet.test_action_open_vouchers_domain_matches_each_saved_sheet` — no
  `action_open_vouchers`
- `TestCollectionSheet.test_action_open_vouchers_refused_on_new_id` — no
  `action_open_vouchers`

Preserved GREEN throughout: `test_collection_sheets_form_statusbar_close_reopen`,
`test_customer_field_is_partner_id_without_domain`,
`test_action_open_document_review_refused_on_new_id`, freeze/reassign/dates/Document
Review.

## Work Unit Evidence

| Evidence                                          | Required value                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `invoke test -m collection --mode=update` from `/home/crisd/projects/seedian/seedian`. Exit code **0**. `0 failed, 0 error(s) of 509 tests when loading database 'devel'`. `collection: 565 tests 23.92s 40453 queries`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Runtime harness command/scenario and exact result | Same Odoo TransactionCase Docker run (`--test-enable --stop-after-init -u collection --test-tags /collection`). Exit code **0**. Not N/A — this is the runtime harness.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Quality command and exact result                  | Literal `pre-commit run --files odoo/custom/src/private/collection/**` exit **1**: prettier `SyntaxError` on archived `state.yaml` with duplicate keys (`openspec/changes/archive/2026-08-26-add-pluggable-collection-connectors/state.yaml`, `openspec/changes/archive/2026-08-17-collection-sheets/state.yaml`). Those files were **not** rewritten (OpenSpec archive is immutable). Owned-files pre-commit (AGENTS.md, Phase 1–2 py/xml/tests, `openspec/changes/sheet-form-allocations-only/**`) exit **0**. A first globstar expansion also prettier-rewrote archive markdown, main specs, and `tests/test_collection_customer_binding.py`; those drive-bys were reverted with `git checkout`. |
| Rollback boundary                                 | Revert `AGENTS.md` docs lines, this `apply-progress.md`, and Phase 3 `[x]` marks in `tasks.md`. Phase 1–2 production/tests stay.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |

### Phase 2 Work Unit Evidence (preserved)

| Evidence                                          | Required value                                                                                                                                                                                                           |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Focused test command and exact result             | `invoke test -m collection --mode=update` from `/home/crisd/projects/seedian/seedian`. Exit code **0**. `0 failed, 0 error(s) of 509 tests when loading database 'devel'`. `collection: 565 tests 23.67s 40453 queries`. |
| Runtime harness command/scenario and exact result | Same Odoo TransactionCase Docker run (`--test-enable --stop-after-init -u collection --test-tags /collection`). Exit code **0**. Not N/A — this is the runtime harness.                                                  |
| Rollback boundary                                 | Revert `models/collection_sheet.py`, `views/collection_views.xml`, plus this `apply-progress.md` and Phase 2 `[x]` marks in `tasks.md`. Phase 1 test files stay; they were not rewritten.                                |

### Phase 1 Work Unit Evidence (preserved)

| Evidence                                          | Required value                                                                                                                                                                                              |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `invoke test -m collection --mode=update` from `/home/crisd/projects/seedian/seedian`. Exit code **1**. `Module collection: 3 failures, 5 errors of 509 tests`. RED as expected.                            |
| Runtime harness command/scenario and exact result | Same Odoo TransactionCase Docker run (`seedian-odoo-run-*`, `--test-enable --stop-after-init -u collection --test-tags /collection`). Exit code 1. Not N/A — this is the runtime harness.                   |
| Rollback boundary                                 | Revert `tests/test_collection_ui.py`, `tests/test_collection_sheet.py`, `openspec/changes/sheet-form-allocations-only/tasks.md`, and this `apply-progress.md`. No production model/view edits in that unit. |

## Deviations from Design

None — implementation matches design contracts (`voucher_count` non-stored
`@api.depends("voucher_ids")`, hand-built `action_open_vouchers` dict with `view_mode`
`list,kanban,form`, domain `[("sheet_id", "=", self.id)]`, context
`default_sheet_id`/`default_seller_id`, no `_for_xml_id` of
`collection.action_collection_voucher`, generalized `_ensure_saved_sheet` message, stat
button first inside `<sheet>`, list `optional="hide"`, form editable after `seller_id`,
search field + group-by, kanban unchanged). `voucher_ids` kept on the model. Phase 3
docs match the UI bullet intent.

## Issues Found

Literal `pre-commit run --files odoo/custom/src/private/collection/**` exits 1 because
prettier parses archived OpenSpec `state.yaml` files that contain duplicate keys.
Archive must not be rewritten. Quality for this change was proven with owned-files
pre-commit (exit 0) plus `invoke test` (exit 0).

## Remaining Tasks

None.

## Workload / PR Boundary

- Mode: single PR (auto-chain; chained PRs not recommended)
- Current work unit: Phase 3 docs and quality
- Boundary: `AGENTS.md` UI/map docs + quality gate; production model/XML not reopened
- Estimated review budget impact: docs-only this batch; still within medium 280–380
  forecast for the full change

## Status

12/12 tasks complete. Ready for verify.
