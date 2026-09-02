# Apply Progress: voucher-customer-reassign

**Mode**: Strict TDD **Work unit**: phase-3-group-expand-docs (PR 3, stacked-to-main)
**Tasks**: 15/15 complete (Phase 1–3 done)

## Completed Tasks

### Phase 1 (kept)

- [x] 1.1 RED voucher/sheet write tests
- [x] 1.2 RED constrain mismatch
- [x] 1.3 RED allocation residual/partner tests
- [x] 1.4 RED manifest version 1.26.0
- [x] 1.5 GREEN collection_voucher.py write follow-up + constrain
- [x] 1.6 GREEN manifest 19.0.1.26.0
- [x] 1.7 REFACTOR + invoke tests + scoped pre-commit

### Phase 2 (kept)

- [x] 2.1 RED `tests/test_collection_sheet.py` `action_open_voucher_reassign` shape /
      unsaved / closed
- [x] 2.2 RED `tests/test_collection_ui.py` reassign kanban + header + partner_id counts
- [x] 2.3 GREEN `models/collection_sheet.py` `action_open_voucher_reassign`
- [x] 2.4 GREEN `views/collection_views.xml` new XMLID + header after Document Review
- [x] 2.5 REFACTOR; `-u collection`; full update tests; scoped pre-commit

### Phase 3

- [x] 3.1 RED `tests/test_collection_ui.py` `formatted_read_group` +
      `read_group_expand=True`
- [x] 3.2 GREEN `models/collection_voucher.py`
      `partner_id.group_expand="_read_group_partner_ids"`
- [x] 3.3 REFACTOR + `AGENTS.md`; `-u collection`; full update tests; scoped pre-commit

## Files Changed

### Phase 1 (kept)

| File                                         | Action   | What Was Done                                                                                  |
| -------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------- |
| `tests/test_collection_voucher.py`           | Modified | Sheet/allocation helpers; partner follow-up, residual, chatter, decided-state, constrain tests |
| `tests/test_collection_sheet.py`             | Modified | Closed `partner_id` reuses membership UserError                                                |
| `tests/test_collection_allocation.py`        | Modified | Fully applied / projected residual refuse; mismatch; same-vals Q+B                             |
| `tests/test_collection_company_migration.py` | Modified | `test_manifest_version_is_1_26_0`; keep 1.25.0 migrate asserts; no 1.26.0 folder               |
| `models/collection_voucher.py`               | Modified | Partner write follow-up before allocation gate; same-vals inject; constrain; no sudo           |
| `__manifest__.py`                            | Modified | `19.0.1.26.0`                                                                                  |

### Phase 2 (kept)

| File                             | Action   | What Was Done                                                                                               |
| -------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------- |
| `tests/test_collection_sheet.py` | Modified | Reassign action shape, two-sheet bind, unsaved `_ensure_saved_sheet`, closed membership UserError           |
| `tests/test_collection_ui.py`    | Modified | Reassign kanban arch; header after Document Review; xmlid added to `partner_id` counts; state kanban freeze |
| `models/collection_sheet.py`     | Modified | `action_open_voucher_reassign` (`views` only; no `view_mode`/`view_id`/`path`)                              |
| `views/collection_views.xml`     | Modified | New `view_collection_voucher_reassign_kanban`; header button. State kanban unchanged                        |

### Phase 3

| File                           | Action   | What Was Done                                                                                                |
| ------------------------------ | -------- | ------------------------------------------------------------------------------------------------------------ |
| `tests/test_collection_ui.py`  | Modified | Identity / empty-allocation / stray `formatted_read_group` expand tests                                      |
| `models/collection_voucher.py` | Modified | `partner_id.group_expand="_read_group_partner_ids"`; identity unless readable sheet; no sudo                 |
| `AGENTS.md`                    | Modified | UI header+kanban; closed freeze includes `partner_id`; write follow-up; version `19.0.1.26.0`; views map row |

## TDD Cycle Evidence

### Phase 1 (kept)

| Task | Test File                                                            | Layer                         | Safety Net                                                    | RED                                                                                                               | GREEN                                                                                                          | TRIANGULATE                                                                                                 | REFACTOR                                                                                                          |
| ---- | -------------------------------------------------------------------- | ----------------------------- | ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| 1.1  | `tests/test_collection_voucher.py`, `tests/test_collection_sheet.py` | Integration (TransactionCase) | ✅ Prior voucher/sheet tests green (full suite later 521/521) | ✅ Written — attach/unallocated/chatter/residual 0/non-confirmed/decided/closed freeze failed before write branch | ✅ 13 focused tests 0 failed                                                                                   | ✅ Attach vs unallocated+chatter; validated vs rejected source; approved vs rejected voucher; closed freeze | ✅ Shared closed-membership error + residual helpers                                                              |
| 1.2  | `tests/test_collection_voucher.py`                                   | Integration                   | ✅ Same                                                       | ✅ Written — allocation_id without matching partner                                                               | ✅ Passed after constrain                                                                                      | ✅ Allocation-only mismatch + 1.3 stale same-vals Q+A                                                       | ➖ Covered by voucher constrain helper                                                                            |
| 1.3  | `tests/test_collection_allocation.py`                                | Integration                   | ✅ Same                                                       | ✅ Written — fully applied and projected residual did not raise; stale Q+A succeeded                              | ✅ Passed                                                                                                      | ✅ Residual 0 vs residual < amount; mismatch vs same-vals Q+B                                               | ➖ None needed in allocation tests                                                                                |
| 1.4  | `tests/test_collection_company_migration.py`                         | Unit (file read)              | N/A (rename)                                                  | ✅ Written — asserted 19.0.1.26.0 and no migrate folder                                                           | ✅ Manifest bump                                                                                               | ➖ Single — version constant                                                                                | ➖ None needed                                                                                                    |
| 1.5  | `models/collection_voucher.py`                                       | Implementation                | ✅                                                            | ✅ Tests first                                                                                                    | ✅ Focused GREEN then full suite                                                                               | ✅ See 1.1–1.3                                                                                              | ✅ Extract `_prepare_partner_reassign_write` / `_intercept_state_write` (C901); keep `super().write` in `write()` |
| 1.6  | `__manifest__.py`                                                    | Structural                    | N/A                                                           | ✅ Version test first                                                                                             | ✅ `"19.0.1.26.0"`                                                                                             | ➖ Single                                                                                                   | ➖ None needed                                                                                                    |
| 1.7  | Phase 1 paths                                                        | Quality                       | ✅                                                            | N/A                                                                                                               | ✅ `invoke test -m collection --mode=update` → **0 failed, 0 error(s) of 521 tests**; scoped pre-commit Passed | N/A                                                                                                         | ✅ Ruff C901/E501 and pylint W8106 resolved                                                                       |

### Phase 2 (kept)

| Task | Test File                        | Layer                         | Safety Net                                                        | RED                                                                      | GREEN                                                                           | TRIANGULATE                                                                                                         | REFACTOR                                                                              |
| ---- | -------------------------------- | ----------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| 2.1  | `tests/test_collection_sheet.py` | Integration (TransactionCase) | ✅ 8 existing action/kanban/header tests **0 failed, 0 error(s)** | ✅ Written — `action_open_voucher_reassign` AttributeError before method | ✅ Method + XMLID; focused 11 tests **0 failed**                                | ✅ Open saved vs two sheets vs `.new()` saved-sheet error vs closed membership error                                | ➖ Action already matches `action_open_vouchers` style; ruff collapsed UserError line |
| 2.2  | `tests/test_collection_ui.py`    | Integration (arch/lxml)       | ✅ Same safety net                                                | ✅ Written — missing XMLID ValueError; header `assertIn` failed          | ✅ New kanban + header button                                                   | ✅ Reassign attrs vs frozen state kanban; `partner_id` counts include new xmlid (`2`); header after Document Review | ✅ Docstring E501; prettier XML; removed trivial arch `id` compare                    |
| 2.3  | `models/collection_sheet.py`     | Implementation                | ✅                                                                | ✅ Tests first                                                           | ✅ `views` list, context `collection_reassign_sheet_id` + `group_by` + defaults | ✅ See 2.1                                                                                                          | ➖ None needed beyond format                                                          |
| 2.4  | `views/collection_views.xml`     | Implementation                | ✅                                                                | ✅ Tests first                                                           | ✅ Distinct XMLID; state kanban `default_group_by="state"` untouched            | ✅ See 2.2                                                                                                          | ✅ Prettier XML Passed                                                                |
| 2.5  | Phase 2 paths                    | Quality                       | ✅                                                                | N/A                                                                      | ✅ Full suite **0 failed, 0 error(s) of 527 tests**; scoped pre-commit Passed   | N/A                                                                                                                 | ✅ E501 docstring; no `group_expand` / AGENTS.md                                      |

### Phase 3

| Task | Test File                      | Layer                         | Safety Net                                                           | RED                                                                                                                                                    | GREEN                                                                                                                                                                | TRIANGULATE                                                                                                                 | REFACTOR                                                                   |
| ---- | ------------------------------ | ----------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| 3.1  | `tests/test_collection_ui.py`  | Integration (TransactionCase) | ✅ 4 existing UI expand/kanban/header tests **0 failed, 0 error(s)** | ✅ Written — **3 failed, 0 error(s) of 3 tests**: `group_expand` was `None`; empty allocation partner absent; stray-only list ≠ partner `_order` union | ✅ After method + field: focused 4 tests **0 failed**                                                                                                                | ✅ Missing key vs True/False/`"12"`/0/−1/missing sheet; empty alloc `__count` 0; stray `__count` 1 + `res.partner` `_order` | ✅ Tuple vs recordset group value helper                                   |
| 3.2  | `models/collection_voucher.py` | Implementation                | ✅                                                                   | ✅ Tests first                                                                                                                                         | ✅ `group_expand="_read_group_partner_ids"`; `search` not sudo; identity unless readable positive int sheet                                                          | ✅ See 3.1                                                                                                                  | ✅ Extract `_readable_reassign_sheet`; bool excluded from `int`            |
| 3.3  | `AGENTS.md` + Phase 3 paths    | Quality                       | ✅                                                                   | N/A                                                                                                                                                    | ✅ `docker exec … -u collection` exit 0, Modules loaded; `invoke test -m collection --mode=update` → **0 failed, 0 error(s) of 530 tests**; scoped pre-commit Passed | N/A                                                                                                                         | ✅ E501 docstring; no `view_collection_voucher_kanban` / no migrate 1.26.0 |

### Test Summary

- **Total tests written (Phase 1)**: 13 (7 voucher + 1 sheet + 4 allocation + 1 renamed
  version)
- **Total tests written (Phase 2)**: 6 (4 sheet action + 2 UI; plus `partner_id` counts
  gained the new xmlid)
- **Total tests written (Phase 3)**: 3 (identity, empty allocation columns, stray
  voucher customers)
- **Total tests passing**: 530 collection module
  (`invoke test -m collection --mode=update`); was 527 after Phase 2
- **Layers used**: Unit (1 version file-read), Integration (TransactionCase/arch), E2E
  (0)
- **Approval tests** (refactoring): State-kanban freeze in 2.2 locks
  `view_collection_voucher_kanban`; Phase 3 identity expand locks Payment Vouchers
  grouping without readable sheet context
- **Pure functions created (Phase 1)**: `_projected_residual`,
  `_allocation_residual_holds` (record helpers, no sudo)
- **Pure functions created (Phase 2)**: 0 — window action + XML only
- **Pure functions created (Phase 3)**: `_readable_reassign_sheet` (context gate, no
  sudo)

## Work Unit Evidence

### Phase 1 (kept)

| Evidence                                          | Required value                                                                                                                                                                                                                                                                                                                                                               |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `docker compose run --rm odoo odoo --test-enable --stop-after-init -u collection --test-tags '.test_partner_write_.../.test_freeze_rejects_closed_partner_id.../.test_fully_applied_source_detach.../.test_manifest_version_is_1_26_0'` → **0 failed, 0 error(s) of 13 tests**. Full unit: `invoke test -m collection --mode=update` → **0 failed, 0 error(s) of 521 tests** |
| Runtime harness command/scenario and exact result | N/A — TransactionCase covers write/residual (per tasks.md). No HTTP/kanban runtime in Phase 1                                                                                                                                                                                                                                                                                |
| Rollback boundary                                 | Revert `models/collection_voucher.py` write/constrain helpers, the Phase 1 tests above, and `__manifest__.py` to `19.0.1.25.0`. No stored field; no `migrations/19.0.1.26.0/`; Phase 2/3 UI not in this slice                                                                                                                                                                |

### Phase 2 (kept)

| Evidence                                          | Required value                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | RED: `docker compose run --rm odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags '.test_action_open_voucher_reassign_.../.test_reassign_kanban_.../.test_customer_field_is_partner_id_without_domain/.test_sheet_form_header_reassign_...'` → **1 failed, 6 error(s) of 7 tests** (AttributeError / missing XMLID). GREEN: same tags plus state-kanban/header freezes → **0 failed, 0 error(s) of 11 tests**. Full: `invoke test -m collection --mode=update` → **0 failed, 0 error(s) of 527 tests** |
| Runtime harness command/scenario and exact result | `docker exec seedian-odoo-1 odoo -d devel -u collection --stop-after-init --workers=0` → exit 0; `module collection: creating or updating database tables`; `Modules loaded.` Also `docker compose run --rm --no-deps odoo odoo -d devel -u collection --stop-after-init --workers=0` → exit 0, same load. Open-sheet header exposes **Reassign Customers** after Document Review (`invisible="not id or state != 'open'"`).                                                                                                       |
| Rollback boundary                                 | Revert `action_open_voucher_reassign` in `models/collection_sheet.py`, XMLID `view_collection_voucher_reassign_kanban`, header button, and the Phase 2 tests above. Do **not** revert Phase 1 write/constrain/manifest `19.0.1.26.0`. Do not touch `view_collection_voucher_kanban`, `group_expand`, or `AGENTS.md`.                                                                                                                                                                                                               |

### Phase 3

| Evidence                                          | Required value                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | RED: `docker compose run --rm --no-deps odoo odoo --test-enable --stop-after-init --workers=0 -d devel -u collection --test-tags '.test_partner_group_expand_identity_without_readable_sheet,.test_partner_group_expand_empty_allocation_columns,.test_partner_group_expand_stray_voucher_customers'` → **3 failed, 0 error(s) of 3 tests**. GREEN: same tags plus `.test_state_group_expand_shows_all_columns` → **0 failed, 0 error(s) of 4 tests**. Full: `invoke test -m collection --mode=update` → **0 failed, 0 error(s) of 530 tests** (default db-filter `^devel$`; invoke `-d` is `--debugpy`, not database) |
| Runtime harness command/scenario and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --workers=0` → exit 0; `module collection: creating or updating database tables`; `Modules loaded.` Empty allocation + stray columns covered by TransactionCase `formatted_read_group` with `read_group_expand=True` and `collection_reassign_sheet_id`.                                                                                                                                                                                                                                                                                  |
| Rollback boundary                                 | Revert `_read_group_partner_ids` / `_readable_reassign_sheet` / `partner_id.group_expand` in `models/collection_voucher.py`, the three Phase 3 UI tests, and Phase 3 `AGENTS.md` bullets. Do **not** revert Phase 1 write/constrain/manifest or Phase 2 action/kanban. Do not touch `view_collection_voucher_kanban`. No `migrations/19.0.1.26.0/`.                                                                                                                                                                                                                                                                    |

## Deviations from Design

### Phase 1 (kept)

- `allocation_id` is injected only when the caller omitted it, so a same-vals stale pair
  (`partner_id=Q`, `allocation_id=A`) still hits `_check_voucher_allocation_partner`.
  Caller-provided matching Q+B still writes both fields together.
- Non-confirmed source reuses the existing allocation-membership UserError (not a new
  string). Closed freeze reuses
  `"Closed collection sheets cannot change membership. Reopen first."` exactly.
- `write()` complexity was extracted into `_prepare_partner_reassign_write` and
  `_intercept_state_write` so Ruff C901 stays ≤16 and pylint still sees `super().write`
  in `write()`.

None of these change the spec outcomes.

### Phase 2 (kept)

None — implementation matches design: action name **Reassign Customers**; `views` only
(reassign kanban XMLID, then form); domain `sheet_id`; context
`collection_reassign_sheet_id`, `group_by: partner_id`, `default_sheet_id`,
`default_seller_id`; closed reuses membership UserError; unsaved uses
`_ensure_saved_sheet`; no sudo; state kanban not edited.

### Phase 3

None — `group_expand` is the method name `_read_group_partner_ids` (not `True`).
Identity unless context `collection_reassign_sheet_id` is a readable positive int sheet
(`search`, no sudo; bool/`"12"`/≤0/missing sheet stay identity). Expand is allocation ∪
member voucher partners ordered by `res.partner` `_order`. Signature
`(self, groups, domain)`.

## Issues Found

None blocking Phase 3. Optional pylint `manifest-required-author` (Eynes) is
pre-existing (Phase 1 note) and not in the mandatory hook failure path. Invoke
`-d devel` is `--debugpy`, not a database flag; full suite used
`invoke test -m collection --mode=update` with default db-filter `^devel$`.

## Remaining Tasks

None — 15/15 `[x]`.

## Workload / PR Boundary

- Mode: stacked PR slice
- Current work unit: phase-3-group-expand-docs
- Boundary: starts after Phase 2 reassign action/kanban; adds `partner_id.group_expand`
  / `_read_group_partner_ids` and `AGENTS.md` UI/write/version. Ends before sdd-verify.
  Does not edit `view_collection_voucher_kanban` or add `migrations/19.0.1.26.0/`
- Estimated review budget impact: Phase 3 method + tests + docs only; no OWL/MCP; state
  kanban frozen

## Status

15/15 tasks complete (Phase 3 of 3). Ready for sdd-verify.
