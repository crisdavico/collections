# Apply Progress: Auto-assign Open Sheet

**Change**: auto-assign-open-sheet
**Mode**: Strict TDD
**Work unit**: Unit 2 / PR2 / Phase 2
**Branch**: feat/auto-assign-open-sheet-02-one-open
**Chain strategy**: stacked-to-main
**Engram**: skipped (unavailable)

## Completed Tasks

- [x] 1.1 RED `tests/test_collection_sheet.py`: drop `assertNotIn("state")`; default `open`; Close/Reopen; raw `state` write rejected except `collection_sheet_audited_state`.
- [x] 1.2 GREEN `__manifest__.py` `19.0.1.12.0`. `models/collection_sheet.py`: `state` default `open`; `action_close`/`action_reopen`; intercept `write` like voucher audited state.
- [x] 1.3 RED/GREEN `tests/test_collection_ui.py` + `views/collection_views.xml`: replace `test_collection_sheets_form_without_statusbar`; non-clickable statusbar, Close/Reopen, list/search `state`.
- [x] 1.4 Full collection test run (docker exec `--test-tags /collection`; invoke skipped as slower, recorded below).
- [x] 2.1 RED `tests/test_collection_sheet.py`: second open create rejected; Reopen rejected if another open; leftover `>1` still Closeable; Action reject if open ≥1; freeze add/remove/reassign. Rewrite two-open same-seller tests (close-first or `_other_internal_seller`).
- [x] 2.2 GREEN `models/collection_sheet.py`: `_open_sheets_for_seller`; guard create-if-open and `action_reopen`; freeze `voucher_ids`; unlink via `collection_sheet_unlinking`. GREEN `models/collection_voucher.py`: after `_seller_for_sheet_action` reject open ≥1; reject add to closed or remove/reassign off closed.
- [x] 2.3 RED/GREEN membership readonly when closed (`tests/test_collection_ui.py`, `views/collection_views.xml`). RED/GREEN `tests/test_collection_document_review.py` two-sheet cases close-first or two sellers.
- [x] 2.4 Full collection test run (docker exec `--test-tags /collection`; invoke skipped as slower, recorded below).

## Remaining Tasks

- [ ] Phase 3 (Unit 3 / PR3): auto-assign + MCP
- [ ] Phase 4: verify / pre-commit
- [ ] Phase 5: AGENTS.md

## Files Changed

### Unit 1 (retained)

| File | Action | What Was Done |
|------|--------|---------------|
| `tests/test_collection_sheet.py` | Modified | Dropped `assertNotIn("state")`; default `open`; Close/Reopen; intercept tests |
| `models/collection_sheet.py` | Modified | `state` Selection `open`/`closed`; `action_close`/`action_reopen`; `write` intercept via `collection_sheet_audited_state` |
| `__manifest__.py` | Modified | Version `19.0.1.12.0` |
| `tests/test_collection_ui.py` | Modified | Replaced no-statusbar test; list/search `state`; kept Document Review |
| `views/collection_views.xml` | Modified | Non-clickable statusbar; Close/Reopen; list/search `state` |
| `openspec/changes/auto-assign-open-sheet/tasks.md` | Modified | Marked 1.1–1.4 `[x]` |

### Unit 2 (this batch)

| File | Action | What Was Done |
|------|--------|---------------|
| `tests/test_collection_sheet.py` | Modified | One-open / leftover Close / Action ≥1 / freeze / unlink-closed tests; two-open same-seller fixtures rewritten (close-first or `_other_internal_seller`) |
| `models/collection_sheet.py` | Modified | `_open_sheets_for_seller` + create/reopen guards (no UNIQUE, no constrains); freeze `voucher_ids`; `unlink` via `collection_sheet_unlinking` |
| `models/collection_voucher.py` | Modified | Action rejects open ≥1 after `_seller_for_sheet_action`; freeze add/remove/reassign on `sheet_id` |
| `tests/test_collection_ui.py` | Modified | Membership `readonly="state == 'closed'"` |
| `views/collection_views.xml` | Modified | `voucher_ids` readonly when closed |
| `tests/test_collection_document_review.py` | Modified | Two-sheet cases: two sellers or close-first; review RPCs unchanged |
| `openspec/changes/auto-assign-open-sheet/tasks.md` | Modified | Marked 2.1–2.4 `[x]` |

Not edited: `tools/collection_voucher.py`, `__manifest__.py` (already `19.0.1.12.0`). No voucher.create auto-assign, no `pg_advisory_xact_lock`. Unit 1 lifecycle left in place.

## TDD Cycle Evidence

### Unit 1 (retained)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_collection_sheet.py` | Unit (TransactionCase) | ✅ 21/21 | ✅ Written (9 errors: no `state`/actions) | ✅ 28/28 after 1.2 | ✅ default open (1+2 sheets); Close from open vs already closed; Reopen from closed vs already open; routed write vs invalid transition vs audited context | ✅ Clean (line wrap only) |
| 1.2 | `tests/test_collection_sheet.py` | Unit (TransactionCase) | N/A (implementation for 1.1) | ✅ Covered by 1.1 | ✅ 28/28 `TestCollectionSheet` | ➖ Single (structural field/actions for 1.1 scenarios) | ✅ Matches voucher intercept pattern |
| 1.3 | `tests/test_collection_ui.py` | Unit (arch/registry) | ✅ 29/29 | ✅ Written (2 failed: no statusbar, list missing `state`) | ✅ 29/29 | ✅ list+search `state`; Close vs Reopen invisibles; Document Review remains | ✅ xpath wrap |
| 1.4 | `/collection` | Unit (TransactionCase) | N/A (full suite) | N/A | ✅ 0 failed, 0 error(s) of 201 tests | N/A | N/A |

### Unit 2 (this batch)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.1 | `tests/test_collection_sheet.py` | Unit (TransactionCase) | ✅ 28/28 (Ui 29/29, Review 36/36) | ✅ Written (5 failed: second create, reopen-if-open, leftover new-ops, Action ≥1, freeze) | ✅ 35/35 after 2.2 | ✅ same-seller reject vs other-seller allow; leftover Close vs leftover create/reopen/Action; freeze add/remove/reassign/create; unlink closed vs unlink open | ✅ Helpers `_open_sheets_for_seller` / `_raise_if_seller_has_open_sheet` |
| 2.2 | `tests/test_collection_sheet.py` | Unit (TransactionCase) | N/A (implementation for 2.1) | ✅ Covered by 2.1 | ✅ 35/35 `TestCollectionSheet` | ✅ create-open / reopen / Action / freeze sheet+voucher paths | ✅ Shared one-open raise + membership unlock helper |
| 2.3 | `tests/test_collection_ui.py`, `tests/test_collection_document_review.py` | Unit (arch + TransactionCase) | ✅ Ui 29/29, Review 36/36 before edits | ✅ Ui membership readonly assertion; Review two-sheet fixtures rewritten | ✅ Ui 29/29, Review 36/36 | ✅ two sellers (isolation, cross-sheet) vs close-first (empty/ineligible/other); review still works on closed | ➖ Views already matched form pattern |
| 2.4 | `/collection` | Unit (TransactionCase) | N/A (full suite) | N/A | ✅ 0 failed, 0 error(s) of 208 tests | N/A | N/A |

### Test Summary

- **Total tests written**: Unit 1 as before; Unit 2 added 7 `TestCollectionSheet` methods and 1 UI membership assertion; Review two-sheet fixtures rewritten (no new review RPC tests)
- **Total tests passing**: 208 collection tests (full `/collection` tag); stats `collection: 232 tests 4.64s 7192 queries`
- **Layers used**: Unit (TransactionCase / view arch), Integration (0), E2E (0)
- **Approval tests** (refactoring): leftover `>1` Close still succeeds (documents that Close is not blocked by one-open)
- **Pure functions created**: 0 (ORM model methods)

## Work Unit Evidence

### Unit 1 (retained)

| Evidence | Required value |
|---|---|
| Focused test command and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection:TestCollectionSheet` → exit 0, `0 failed, 0 error(s) of 28 tests`. Same for `TestCollectionUi` → exit 0, `0 failed, 0 error(s) of 29 tests`. `--http-port=18069` because the running odoo already binds 8069. |
| Runtime harness command/scenario and exact result | N/A — Odoo TransactionCase in container; threat matrix N/A; no separate runtime/process boundary. |
| Rollback boundary | Revert `__manifest__.py` to `19.0.1.11.0`; `models/collection_sheet.py` state/actions/intercept; sheet list/search/form in `views/collection_views.xml`; `tests/test_collection_{sheet,ui}.py` Unit 1 diffs. Leave unrelated WIP (document review, seller lookup) in place. Drop `state` via reverse upgrade or DB snapshot if needed. |

### Unit 2 (this batch)

| Evidence | Required value |
|---|---|
| Focused test command and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection:TestCollectionSheet` → exit 0, `0 failed, 0 error(s) of 35 tests`. `TestCollectionUi` → exit 0, `0 failed, 0 error(s) of 29 tests`. `TestCollectionDocumentReview` → exit 0, `0 failed, 0 error(s) of 36 tests`. `--http-port=18069` because the running odoo already binds 8069. |
| Runtime harness command/scenario and exact result | N/A — Odoo TransactionCase in container; threat matrix N/A; no separate runtime/process boundary. |
| Rollback boundary | Revert Unit 2 diffs only: one-open/freeze in `models/collection_{sheet,voucher}.py`; membership readonly on sheet form; `tests/test_collection_{sheet,ui,document_review}.py` Unit 2 diffs. Keep Unit 1 lifecycle (`state`, Close/Reopen, statusbar). Do not revert commit c7bcbb7. |

### 1.4 Full suite (retained)

Command (allowed substitute for `invoke test -m collection`; recorded exactly):

```bash
docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection
```

Result: **exit 0**. `0 failed, 0 error(s) of 201 tests when loading database 'devel'`. Stats: `collection: 225 tests 4.73s 6810 queries`.

`invoke test -m collection` was not used: it starts a new compose `odoo` with `-i` and is slower; docker exec against `seedian-odoo-1` / `devel` is the allowed equivalent.

### 2.4 Full suite

Command (allowed substitute for `invoke test -m collection`; recorded exactly):

```bash
docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection
```

Result: **exit 0**. `0 failed, 0 error(s) of 208 tests when loading database 'devel'`. Stats: `collection: 232 tests 4.64s 7192 queries`.

`invoke test -m collection` was not used: same reason as 1.4.

## Deviations from Design

None for Unit 2 — one-open is a count on create-if-open, `action_reopen`, and Action only (not `@api.constrains` / UNIQUE). Leftover `>1` seeded with `state='closed'` then `collection_sheet_audited_state` write to `open`; Close of extras still works. Freeze rejects add/remove/reassign; closed-sheet `unlink` still unassigns via `collection_sheet_unlinking`. Action still creates a new sheet and rejects if open ≥1. Membership view is readonly when closed. Document Review RPCs unchanged. Auto-assign and `pg_advisory_xact_lock` deferred to Phase 3 as assigned.

## Issues Found

None. Pre-existing TestCollectionSheet 28/28, TestCollectionUi 29/29, and TestCollectionDocumentReview 36/36 passed before Unit 2 edits.

## Workload / PR Boundary

- Mode: stacked PR slice
- Current work unit: Unit 2 / PR2 / Phase 2
- Boundary: one-open + freeze + Action reject-if-open + membership readonly; no Phase 3 auto-assign/MCP/advisory lock; no Phase 4/5
- Estimated review budget impact: medium Unit 2 slice (guards, freeze, tests, one view attribute)
