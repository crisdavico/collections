# Apply Progress: Auto-assign Open Sheet

**Change**: auto-assign-open-sheet
**Mode**: Strict TDD
**Work unit**: Unit 1 / PR1 / Phase 1
**Branch**: feat/auto-assign-open-sheet-01-lifecycle
**Chain strategy**: stacked-to-main
**Engram**: skipped (unavailable)

## Completed Tasks

- [x] 1.1 RED `tests/test_collection_sheet.py`: drop `assertNotIn("state")`; default `open`; Close/Reopen; raw `state` write rejected except `collection_sheet_audited_state`.
- [x] 1.2 GREEN `__manifest__.py` `19.0.1.12.0`. `models/collection_sheet.py`: `state` default `open`; `action_close`/`action_reopen`; intercept `write` like voucher audited state.
- [x] 1.3 RED/GREEN `tests/test_collection_ui.py` + `views/collection_views.xml`: replace `test_collection_sheets_form_without_statusbar`; non-clickable statusbar, Close/Reopen, list/search `state`.
- [x] 1.4 Full collection test run (docker exec `--test-tags /collection`; invoke skipped as slower, recorded below).

## Remaining Tasks

- [ ] Phase 2 (Unit 2 / PR2): one-open + freeze
- [ ] Phase 3 (Unit 3 / PR3): auto-assign + MCP
- [ ] Phase 4: verify / pre-commit
- [ ] Phase 5: AGENTS.md

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `tests/test_collection_sheet.py` | Modified | Dropped `assertNotIn("state")`; default `open`; Close/Reopen; intercept tests |
| `models/collection_sheet.py` | Modified | `state` Selection `open`/`closed`; `action_close`/`action_reopen`; `write` intercept via `collection_sheet_audited_state` |
| `__manifest__.py` | Modified | Version `19.0.1.12.0` |
| `tests/test_collection_ui.py` | Modified | Replaced no-statusbar test; list/search `state`; kept Document Review |
| `views/collection_views.xml` | Modified | Non-clickable statusbar; Close/Reopen; list/search `state` |
| `openspec/changes/auto-assign-open-sheet/tasks.md` | Modified | Marked 1.1–1.4 `[x]` |

Not edited: `tools/collection_voucher.py`. Unrelated WIP (document review, seller lookup) left untouched. No one-open, freeze, auto-assign, or advisory lock.

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_collection_sheet.py` | Unit (TransactionCase) | ✅ 21/21 | ✅ Written (9 errors: no `state`/actions) | ✅ 28/28 after 1.2 | ✅ default open (1+2 sheets); Close from open vs already closed; Reopen from closed vs already open; routed write vs invalid transition vs audited context | ✅ Clean (line wrap only) |
| 1.2 | `tests/test_collection_sheet.py` | Unit (TransactionCase) | N/A (implementation for 1.1) | ✅ Covered by 1.1 | ✅ 28/28 `TestCollectionSheet` | ➖ Single (structural field/actions for 1.1 scenarios) | ✅ Matches voucher intercept pattern |
| 1.3 | `tests/test_collection_ui.py` | Unit (arch/registry) | ✅ 29/29 | ✅ Written (2 failed: no statusbar, list missing `state`) | ✅ 29/29 | ✅ list+search `state`; Close vs Reopen invisibles; Document Review remains | ✅ xpath wrap |
| 1.4 | `/collection` | Unit (TransactionCase) | N/A (full suite) | N/A | ✅ 0 failed, 0 error(s) of 201 tests | N/A | N/A |

### Test Summary

- **Total tests written**: 7 new `TestCollectionSheet` methods; 1 replaced UI form test; list/search + Document Review assertions updated
- **Total tests passing**: 201 collection tests (full `/collection` tag)
- **Layers used**: Unit (TransactionCase / view arch), Integration (0), E2E (0)
- **Approval tests** (refactoring): None — no refactoring-only tasks
- **Pure functions created**: 0 (ORM model methods)

## Work Unit Evidence

| Evidence | Required value |
|---|---|
| Focused test command and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection:TestCollectionSheet` → exit 0, `0 failed, 0 error(s) of 28 tests`. Same for `TestCollectionUi` → exit 0, `0 failed, 0 error(s) of 29 tests`. `--http-port=18069` because the running odoo already binds 8069. |
| Runtime harness command/scenario and exact result | N/A — Odoo TransactionCase in container; threat matrix N/A; no separate runtime/process boundary. |
| Rollback boundary | Revert `__manifest__.py` to `19.0.1.11.0`; `models/collection_sheet.py` state/actions/intercept; sheet list/search/form in `views/collection_views.xml`; `tests/test_collection_{sheet,ui}.py` Unit 1 diffs. Leave unrelated WIP (document review, seller lookup) in place. Drop `state` via reverse upgrade or DB snapshot if needed. |

### 1.4 Full suite

Command (allowed substitute for `invoke test -m collection`; recorded exactly):

```bash
docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection
```

Result: **exit 0**. `0 failed, 0 error(s) of 201 tests when loading database 'devel'`. Stats: `collection: 225 tests 4.73s 6810 queries`.

`invoke test -m collection` was not used: it starts a new compose `odoo` with `-i` and is slower; docker exec against `seedian-odoo-1` / `devel` is the allowed equivalent.

## Deviations from Design

None for Unit 1 — `state` default `open`, Close/Reopen, intercept via `collection_sheet_audited_state` mirroring voucher `collection_audited_state`, non-clickable statusbar, list/search `state`. One-open, freeze, auto-assign, and advisory lock deferred to Phase 2/3 as assigned. Creating two open sheets for the same seller still succeeds.

## Issues Found

None. Pre-existing TestCollectionSheet 21/21 and TestCollectionUi 29/29 passed before Unit 1 edits.

## Workload / PR Boundary

- Mode: stacked PR slice
- Current work unit: Unit 1 / PR1 / Phase 1
- Boundary: sheet lifecycle + UI only; no Phase 2/3/4/5
- Estimated review budget impact: small Unit 1 slice (field, two actions, intercept, views, tests)
