# Apply Progress: Auto-assign Open Sheet

**Change**: auto-assign-open-sheet
**Mode**: Strict TDD
**Work unit**: Unit 3 / PR3 / Phase 3
**Branch**: feat/auto-assign-open-sheet-03-auto-assign
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
- [x] 3.1 RED `tests/test_collection_sheet.py`: unique open assigns; none → create then assign; `>1` no voucher; explicit open `sheet_id` honored; closed `sheet_id` fails; null seller unassigned; later `seller_id` write does not assign. Unassigned fixtures: omit seller / unassign while open / unlink.
- [x] 3.2 GREEN `collection.voucher.create` before `super`: seller set + omitted/falsey `sheet_id` → lock then `_open_sheets_for_seller` (0 create open / 1 use / >1 UserError). Same lock on sheet create-open. Batch: one resolve per seller in vals_list.
- [x] 3.3 RED `tests/test_collection_mcp_tool.py`: all-new unique open assigns all payments; none creates one sheet and assigns all; `>1` no writes; exact replay leaves `sheet_id`/`write_date`; response `{id,name,state,document_id}` only (no sheet_id).
- [x] 3.4 Full collection test run (docker exec `--test-tags /collection`; invoke skipped as slower, recorded below).

## Remaining Tasks

- [ ] Phase 4 (verify / pre-commit) — not this batch
- [ ] Phase 5 (AGENTS.md) — not this batch

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

### Unit 2 (retained)

| File | Action | What Was Done |
|------|--------|---------------|
| `tests/test_collection_sheet.py` | Modified | One-open / leftover Close / Action ≥1 / freeze / unlink-closed tests; two-open same-seller fixtures rewritten (close-first or `_other_internal_seller`) |
| `models/collection_sheet.py` | Modified | `_open_sheets_for_seller` + create/reopen guards (no UNIQUE, no constrains); freeze `voucher_ids`; `unlink` via `collection_sheet_unlinking` |
| `models/collection_voucher.py` | Modified | Action rejects open ≥1 after `_seller_for_sheet_action`; freeze add/remove/reassign on `sheet_id` |
| `tests/test_collection_ui.py` | Modified | Membership `readonly="state == 'closed'"` |
| `views/collection_views.xml` | Modified | `voucher_ids` readonly when closed |
| `tests/test_collection_document_review.py` | Modified | Two-sheet cases: two sellers or close-first; review RPCs unchanged |
| `openspec/changes/auto-assign-open-sheet/tasks.md` | Modified | Marked 2.1–2.4 `[x]` |

### Unit 3 (this batch)

| File | Action | What Was Done |
|------|--------|---------------|
| `tests/test_collection_sheet.py` | Modified | Auto-assign RED/GREEN: unique open, none→create, `>1` no write, explicit/falsey `sheet_id`, closed fails, null seller, later `seller_id` write, batch-per-seller. Unassigned Action/dates/freeze/leftover fixtures: omit seller then stamp / unassign while open / unlink. |
| `models/collection_sheet.py` | Modified | `pg_advisory_xact_lock(hashtext('collection.sheet.open'), seller_id)` on create-open; `_lock_open_sheet_for_seller`; `_resolve_open_sheet_id_for_create` (0/1/>1) |
| `models/collection_voucher.py` | Modified | `create` auto-assign before `super` when seller set and `sheet_id` omitted/falsey; one resolve per seller; `_apply_open_sheet_auto_assign` |
| `tests/test_collection_mcp_tool.py` | Modified | MCP inherit: unique open assigns batch; none creates one sheet; `>1` no writes; exact replay leaves `sheet_id`/`write_date`; payload keys `{id,name,state,document_id}` only |
| `openspec/changes/auto-assign-open-sheet/tasks.md` | Modified | Marked 3.1–3.4 `[x]` |

Not edited: `tools/collection_voucher.py` (ORM inherit only; no schema/`sheet_id` payload). No Phase 4 pre-commit. No Phase 5 AGENTS.md. Unit 1 lifecycle and Unit 2 one-open/freeze left in place.

## TDD Cycle Evidence

### Unit 1 (retained)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_collection_sheet.py` | Unit (TransactionCase) | ✅ 21/21 | ✅ Written (9 errors: no `state`/actions) | ✅ 28/28 after 1.2 | ✅ default open (1+2 sheets); Close from open vs already closed; Reopen from closed vs already open; routed write vs invalid transition vs audited context | ✅ Clean (line wrap only) |
| 1.2 | `tests/test_collection_sheet.py` | Unit (TransactionCase) | N/A (implementation for 1.1) | ✅ Covered by 1.1 | ✅ 28/28 `TestCollectionSheet` | ➖ Single (structural field/actions for 1.1 scenarios) | ✅ Matches voucher intercept pattern |
| 1.3 | `tests/test_collection_ui.py` | Unit (arch/registry) | ✅ 29/29 | ✅ Written (2 failed: no statusbar, list missing `state`) | ✅ 29/29 | ✅ list+search `state`; Close vs Reopen invisibles; Document Review remains | ✅ xpath wrap |
| 1.4 | `/collection` | Unit (TransactionCase) | N/A (full suite) | N/A | ✅ 0 failed, 0 error(s) of 201 tests | N/A | N/A |

### Unit 2 (retained)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.1 | `tests/test_collection_sheet.py` | Unit (TransactionCase) | ✅ 28/28 (Ui 29/29, Review 36/36) | ✅ Written (5 failed: second create, reopen-if-open, leftover new-ops, Action ≥1, freeze) | ✅ 35/35 after 2.2 | ✅ same-seller reject vs other-seller allow; leftover Close vs leftover create/reopen/Action; freeze add/remove/reassign/create; unlink closed vs unlink open | ✅ Helpers `_open_sheets_for_seller` / `_raise_if_seller_has_open_sheet` |
| 2.2 | `tests/test_collection_sheet.py` | Unit (TransactionCase) | N/A (implementation for 2.1) | ✅ Covered by 2.1 | ✅ 35/35 `TestCollectionSheet` | ✅ create-open / reopen / Action / freeze sheet+voucher paths | ✅ Shared one-open raise + membership unlock helper |
| 2.3 | `tests/test_collection_ui.py`, `tests/test_collection_document_review.py` | Unit (arch + TransactionCase) | ✅ Ui 29/29, Review 36/36 before edits | ✅ Ui membership readonly assertion; Review two-sheet fixtures rewritten | ✅ Ui 29/29, Review 36/36 | ✅ two sellers (isolation, cross-sheet) vs close-first (empty/ineligible/other); review still works on closed | ➖ Views already matched form pattern |
| 2.4 | `/collection` | Unit (TransactionCase) | N/A (full suite) | N/A | ✅ 0 failed, 0 error(s) of 208 tests | N/A | N/A |

### Unit 3 (this batch)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 3.1 | `tests/test_collection_sheet.py` | Unit (TransactionCase) | ✅ 35/35 | ✅ Written (5 failed: unique assign, none→create, `>1` no raise, falsey `sheet_id`, batch sheets) | ✅ 43/43 after 3.2 | ✅ unique vs none vs `>1`; explicit vs falsey `sheet_id`; closed create; omit vs `seller_id=False`; later write via omit / unassign / unlink; batch two sellers | ✅ Unassigned Action/dates/freeze fixtures rewritten before GREEN |
| 3.2 | `tests/test_collection_sheet.py` | Unit (TransactionCase) | N/A (implementation for 3.1) | ✅ Covered by 3.1 | ✅ 43/43 `TestCollectionSheet` | ✅ 0 create / 1 use / `>1` UserError; lock on voucher resolve and sheet create-open; one resolve per seller | ✅ `_lock_open_sheet_for_seller`, `_resolve_open_sheet_id_for_create`, `_apply_open_sheet_auto_assign` |
| 3.3 | `tests/test_collection_mcp_tool.py` | Unit (TransactionCase / MCP `_call`) | ✅ existing MCP class still passing under 3.2 inherit | ✅ Written (unique/none/`>1`/replay/payload keys) | ✅ 23/23 `TestCollectionMcpTool` (inherit already GREEN from 3.2; tool file unchanged) | ✅ unique open assigns 2 payments; none creates 1 sheet for 2 payments; leftover `>1` no writes; replay assigned + leftover unassigned `sheet_id`/`write_date`; keys only `{id,name,state,document_id}` | ➖ No MCP tool edits by design |
| 3.4 | `/collection` | Unit (TransactionCase) | N/A (full suite) | N/A | ✅ 0 failed, 0 error(s) of 220 tests | N/A | N/A |

### Test Summary

- **Total tests written**: Unit 1+2 as before; Unit 3 added 8 `TestCollectionSheet` methods and 4 `TestCollectionMcpTool` methods; Action/dates/freeze/leftover fixtures rewritten to stay unassigned
- **Total tests passing**: 220 collection tests (full `/collection` tag); stats `collection: 244 tests 5.03s 8052 queries`
- **Layers used**: Unit (TransactionCase / MCP in-process `_call`), Integration (0), E2E (0)
- **Approval tests** (refactoring): later `seller_id` write does not assign; create without seller stays unassigned; closed explicit `sheet_id` still freeze-fails; MCP exact replay leftover unassigned
- **Pure functions created**: 0 (ORM model methods)

## Work Unit Evidence

### Unit 1 (retained)

| Evidence | Required value |
|---|---|
| Focused test command and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection:TestCollectionSheet` → exit 0, `0 failed, 0 error(s) of 28 tests`. Same for `TestCollectionUi` → exit 0, `0 failed, 0 error(s) of 29 tests`. `--http-port=18069` because the running odoo already binds 8069. |
| Runtime harness command/scenario and exact result | N/A — Odoo TransactionCase in container; threat matrix N/A; no separate runtime/process boundary. |
| Rollback boundary | Revert `__manifest__.py` to `19.0.1.11.0`; `models/collection_sheet.py` state/actions/intercept; sheet list/search/form in `views/collection_views.xml`; `tests/test_collection_{sheet,ui}.py` Unit 1 diffs. Leave unrelated WIP (document review, seller lookup) in place. Drop `state` via reverse upgrade or DB snapshot if needed. |

### Unit 2 (retained)

| Evidence | Required value |
|---|---|
| Focused test command and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection:TestCollectionSheet` → exit 0, `0 failed, 0 error(s) of 35 tests`. `TestCollectionUi` → exit 0, `0 failed, 0 error(s) of 29 tests`. `TestCollectionDocumentReview` → exit 0, `0 failed, 0 error(s) of 36 tests`. `--http-port=18069` because the running odoo already binds 8069. |
| Runtime harness command/scenario and exact result | N/A — Odoo TransactionCase in container; threat matrix N/A; no separate runtime/process boundary. |
| Rollback boundary | Revert Unit 2 diffs only: one-open/freeze in `models/collection_{sheet,voucher}.py`; membership readonly on sheet form; `tests/test_collection_{sheet,ui,document_review}.py` Unit 2 diffs. Keep Unit 1 lifecycle (`state`, Close/Reopen, statusbar). Do not revert commit c7bcbb7. |

### Unit 3 (this batch)

| Evidence | Required value |
|---|---|
| Focused test command and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection:TestCollectionSheet` → exit 0, `0 failed, 0 error(s) of 43 tests`. `TestCollectionMcpTool` → exit 0, `0 failed, 0 error(s) of 23 tests`. `--http-port=18069` because the running odoo already binds 8069. |
| Runtime harness command/scenario and exact result | N/A — Odoo TransactionCase in container; threat matrix N/A; no separate runtime/process boundary. MCP covered in-process via `muk_mcp.tool._call`. |
| Rollback boundary | Revert Unit 3 diffs only: auto-assign + lock in `models/collection_{sheet,voucher}.py`; `tests/test_collection_{sheet,mcp_tool}.py` Unit 3 diffs. Keep Unit 1 lifecycle and Unit 2 one-open/freeze (commits c7bcbb7, c7bac90). Do not revert `tools/collection_voucher.py` (unchanged). |

### 1.4 Full suite (retained)

Command (allowed substitute for `invoke test -m collection`; recorded exactly):

```bash
docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection
```

Result: **exit 0**. `0 failed, 0 error(s) of 201 tests when loading database 'devel'`. Stats: `collection: 225 tests 4.73s 6810 queries`.

`invoke test -m collection` was not used: it starts a new compose `odoo` with `-i` and is slower; docker exec against `seedian-odoo-1` / `devel` is the allowed equivalent.

### 2.4 Full suite (retained)

Command (allowed substitute for `invoke test -m collection`; recorded exactly):

```bash
docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection
```

Result: **exit 0**. `0 failed, 0 error(s) of 208 tests when loading database 'devel'`. Stats: `collection: 232 tests 4.64s 7192 queries`.

`invoke test -m collection` was not used: same reason as 1.4.

### 3.4 Full suite

Command (allowed substitute for `invoke test -m collection`; recorded exactly):

```bash
docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection
```

Result: **exit 0**. `0 failed, 0 error(s) of 220 tests when loading database 'devel'`. Stats: `collection: 244 tests 5.03s 8052 queries`.

`invoke test -m collection` was not used: same reason as 1.4.

## Deviations from Design

None for Unit 3 — auto-assign runs in `collection.voucher.create` before `super` when `seller_id` is set and `sheet_id` is omitted/falsey. Count is 0 create-open / 1 use / `>1` UserError after `pg_advisory_xact_lock(hashtext('collection.sheet.open'), seller_id)`. Same lock on sheet create-open. Batch resolves once per seller. Explicit open `sheet_id` is honored; closed `sheet_id` still freeze-fails. Null seller stays unassigned. Later `seller_id` write does not assign. MCP inherits ORM create; `tools/collection_voucher.py` unchanged; response stays `{id,name,state,document_id}`. Exact replay does not attach or move sheets.

## Issues Found

None. Pre-existing TestCollectionSheet 35/35 passed before Unit 3 edits. Full `/collection` stayed green after fixture updates for unassigned Action/dates/freeze/leftover cases.

## Workload / PR Boundary

- Mode: stacked PR slice
- Current work unit: Unit 3 / PR3 / Phase 3
- Boundary: ORM create auto-assign + advisory lock + MCP inherit tests; no Phase 4 pre-commit; no Phase 5 AGENTS.md
- Estimated review budget impact: medium-high Unit 3 slice (create-assign, lock helpers, sheet+MCP tests, fixture rewrites)
