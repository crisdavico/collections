# Apply Progress: Auto-assign Open Sheet

**Change**: auto-assign-open-sheet **Mode**: Strict TDD (Units 1–3); Phase 4 TDD N/A —
verification/hygiene only; Phase 5 TDD N/A — AGENTS.md domain-rule docs only **Work
unit**: Phase 5 / AGENTS.md **Branch**: feat/auto-assign-open-sheet-04-docs-verify
**Chain strategy**: stacked-to-main **Engram**: skipped (unavailable)

## Completed Tasks

- [x] 1.1 RED `tests/test_collection_sheet.py`: drop `assertNotIn("state")`; default
      `open`; Close/Reopen; raw `state` write rejected except
      `collection_sheet_audited_state`.
- [x] 1.2 GREEN `__manifest__.py` `19.0.1.12.0`. `models/collection_sheet.py`: `state`
      default `open`; `action_close`/`action_reopen`; intercept `write` like voucher
      audited state.
- [x] 1.3 RED/GREEN `tests/test_collection_ui.py` + `views/collection_views.xml`:
      replace `test_collection_sheets_form_without_statusbar`; non-clickable statusbar,
      Close/Reopen, list/search `state`.
- [x] 1.4 Full collection test run (docker exec `--test-tags /collection`; invoke
      skipped as slower, recorded below).
- [x] 2.1 RED `tests/test_collection_sheet.py`: second open create rejected; Reopen
      rejected if another open; leftover `>1` still Closeable; Action reject if open ≥1;
      freeze add/remove/reassign. Rewrite two-open same-seller tests (close-first or
      `_other_internal_seller`).
- [x] 2.2 GREEN `models/collection_sheet.py`: `_open_sheets_for_seller`; guard
      create-if-open and `action_reopen`; freeze `voucher_ids`; unlink via
      `collection_sheet_unlinking`. GREEN `models/collection_voucher.py`: after
      `_seller_for_sheet_action` reject open ≥1; reject add to closed or remove/reassign
      off closed.
- [x] 2.3 RED/GREEN membership readonly when closed (`tests/test_collection_ui.py`,
      `views/collection_views.xml`). RED/GREEN
      `tests/test_collection_document_review.py` two-sheet cases close-first or two
      sellers.
- [x] 2.4 Full collection test run (docker exec `--test-tags /collection`; invoke
      skipped as slower, recorded below).
- [x] 3.1 RED `tests/test_collection_sheet.py`: unique open assigns; none → create then
      assign; `>1` no voucher; explicit open `sheet_id` honored; closed `sheet_id`
      fails; null seller unassigned; later `seller_id` write does not assign.
      Unassigned: omit seller / unassign / unlink.
- [x] 3.2 GREEN `collection.voucher.create` before `super`: seller set + omitted/falsey
      `sheet_id` → lock then `_open_sheets_for_seller` (0 create open / 1 use / >1
      UserError). Same lock on sheet create-open. Batch: one resolve per seller in
      vals_list.
- [x] 3.3 RED `tests/test_collection_mcp_tool.py`: all-new unique open assigns all
      payments; none creates one sheet and assigns all; `>1` no writes; exact replay
      leaves `sheet_id`/`write_date`; response `{id,name,state,document_id}` only (no
      sheet_id).
- [x] 3.4 Full collection test run (docker exec `--test-tags /collection`; invoke
      skipped as slower, recorded below).
- [x] 4.1 Scoped `pre-commit run --files` on Unit 1–3 paths. Full `/collection` tests.
      Hygiene wrap of E501 docstring. Ready for apply.
- [x] 5.1 `AGENTS.md`: sheet `open`/`closed`; one-open on new ops (leftover Close OK);
      freeze; ORM create auto-assign; MCP inherit, no payload `sheet_id`.

## Remaining Tasks

None. All tasks 1.1–5.1 complete.

## Files Changed

### Unit 1 (retained)

| File                                               | Action   | What Was Done                                                                                                             |
| -------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------- |
| `tests/test_collection_sheet.py`                   | Modified | Dropped `assertNotIn("state")`; default `open`; Close/Reopen; intercept tests                                             |
| `models/collection_sheet.py`                       | Modified | `state` Selection `open`/`closed`; `action_close`/`action_reopen`; `write` intercept via `collection_sheet_audited_state` |
| `__manifest__.py`                                  | Modified | Version `19.0.1.12.0`                                                                                                     |
| `tests/test_collection_ui.py`                      | Modified | Replaced no-statusbar test; list/search `state`; kept Document Review                                                     |
| `views/collection_views.xml`                       | Modified | Non-clickable statusbar; Close/Reopen; list/search `state`                                                                |
| `openspec/changes/auto-assign-open-sheet/tasks.md` | Modified | Marked 1.1–1.4 `[x]`                                                                                                      |

### Unit 2 (retained)

| File                                               | Action   | What Was Done                                                                                                                                           |
| -------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/test_collection_sheet.py`                   | Modified | One-open / leftover Close / Action ≥1 / freeze / unlink-closed tests; two-open same-seller fixtures rewritten (close-first or `_other_internal_seller`) |
| `models/collection_sheet.py`                       | Modified | `_open_sheets_for_seller` + create/reopen guards (no UNIQUE, no constrains); freeze `voucher_ids`; `unlink` via `collection_sheet_unlinking`            |
| `models/collection_voucher.py`                     | Modified | Action rejects open ≥1 after `_seller_for_sheet_action`; freeze add/remove/reassign on `sheet_id`                                                       |
| `tests/test_collection_ui.py`                      | Modified | Membership `readonly="state == 'closed'"`                                                                                                               |
| `views/collection_views.xml`                       | Modified | `voucher_ids` readonly when closed                                                                                                                      |
| `tests/test_collection_document_review.py`         | Modified | Two-sheet cases: two sellers or close-first; review RPCs unchanged                                                                                      |
| `openspec/changes/auto-assign-open-sheet/tasks.md` | Modified | Marked 2.1–2.4 `[x]`                                                                                                                                    |

### Unit 3 (retained)

| File                                               | Action   | What Was Done                                                                                                                                                                                                                                                              |
| -------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/test_collection_sheet.py`                   | Modified | Auto-assign RED/GREEN: unique open, none→create, `>1` no write, explicit/falsey `sheet_id`, closed fails, null seller, later `seller_id` write, batch-per-seller. Unassigned Action/dates/freeze/leftover fixtures: omit seller then stamp / unassign while open / unlink. |
| `models/collection_sheet.py`                       | Modified | `pg_advisory_xact_lock(hashtext('collection.sheet.open'), seller_id)` on create-open; `_lock_open_sheet_for_seller`; `_resolve_open_sheet_id_for_create` (0/1/>1)                                                                                                          |
| `models/collection_voucher.py`                     | Modified | `create` auto-assign before `super` when seller set and `sheet_id` omitted/falsey; one resolve per seller; `_apply_open_sheet_auto_assign`                                                                                                                                 |
| `tests/test_collection_mcp_tool.py`                | Modified | MCP inherit: unique open assigns batch; none creates one sheet; `>1` no writes; exact replay leaves `sheet_id`/`write_date`; payload keys `{id,name,state,document_id}` only                                                                                               |
| `openspec/changes/auto-assign-open-sheet/tasks.md` | Modified | Marked 3.1–3.4 `[x]`                                                                                                                                                                                                                                                       |

### Phase 4 (retained)

| File                                                        | Action   | What Was Done                                                                                                                       |
| ----------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `tests/test_collection_sheet.py`                            | Modified | Hygiene wrap of `test_raw_state_write_routes_to_close_and_reopen` docstring to satisfy ruff E501 (90→under 88). No behavior change. |
| `openspec/changes/auto-assign-open-sheet/tasks.md`          | Modified | Marked 4.1 `[x]`                                                                                                                    |
| `openspec/changes/auto-assign-open-sheet/apply-progress.md` | Modified | Merged Phase 4 evidence; Units 1–3 retained                                                                                         |

Not edited in Units 1–4: `tools/collection_voucher.py`. No git commit. No Engram write.

### Phase 5 (this batch)

| File                                                        | Action   | What Was Done                                                                                                                                                                                                                  |
| ----------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `AGENTS.md`                                                 | Modified | Models include `collection.sheet`; repo map adds `models/collection_sheet.py`; domain rules for lifecycle, one-open, freeze, auto-assign, list Action, MCP inherit/replay; tests table mentions existing sheet/UI/MCP coverage |
| `openspec/changes/auto-assign-open-sheet/tasks.md`          | Modified | Marked 5.1 `[x]`                                                                                                                                                                                                               |
| `openspec/changes/auto-assign-open-sheet/apply-progress.md` | Modified | Merged Phase 5 evidence; Units 1–4 retained                                                                                                                                                                                    |

Not edited: `tools/collection_voucher.py`, models, views, tests. No git commit. No
Engram write.

## TDD Cycle Evidence

### Unit 1 (retained)

| Task | Test File                        | Layer                  | Safety Net                   | RED                                                       | GREEN                                | TRIANGULATE                                                                                                                                                | REFACTOR                             |
| ---- | -------------------------------- | ---------------------- | ---------------------------- | --------------------------------------------------------- | ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| 1.1  | `tests/test_collection_sheet.py` | Unit (TransactionCase) | ✅ 21/21                     | ✅ Written (9 errors: no `state`/actions)                 | ✅ 28/28 after 1.2                   | ✅ default open (1+2 sheets); Close from open vs already closed; Reopen from closed vs already open; routed write vs invalid transition vs audited context | ✅ Clean (line wrap only)            |
| 1.2  | `tests/test_collection_sheet.py` | Unit (TransactionCase) | N/A (implementation for 1.1) | ✅ Covered by 1.1                                         | ✅ 28/28 `TestCollectionSheet`       | ➖ Single (structural field/actions for 1.1 scenarios)                                                                                                     | ✅ Matches voucher intercept pattern |
| 1.3  | `tests/test_collection_ui.py`    | Unit (arch/registry)   | ✅ 29/29                     | ✅ Written (2 failed: no statusbar, list missing `state`) | ✅ 29/29                             | ✅ list+search `state`; Close vs Reopen invisibles; Document Review remains                                                                                | ✅ xpath wrap                        |
| 1.4  | `/collection`                    | Unit (TransactionCase) | N/A (full suite)             | N/A                                                       | ✅ 0 failed, 0 error(s) of 201 tests | N/A                                                                                                                                                        | N/A                                  |

### Unit 2 (retained)

| Task | Test File                                                                 | Layer                         | Safety Net                             | RED                                                                                       | GREEN                                | TRIANGULATE                                                                                                                                                   | REFACTOR                                                                 |
| ---- | ------------------------------------------------------------------------- | ----------------------------- | -------------------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| 2.1  | `tests/test_collection_sheet.py`                                          | Unit (TransactionCase)        | ✅ 28/28 (Ui 29/29, Review 36/36)      | ✅ Written (5 failed: second create, reopen-if-open, leftover new-ops, Action ≥1, freeze) | ✅ 35/35 after 2.2                   | ✅ same-seller reject vs other-seller allow; leftover Close vs leftover create/reopen/Action; freeze add/remove/reassign/create; unlink closed vs unlink open | ✅ Helpers `_open_sheets_for_seller` / `_raise_if_seller_has_open_sheet` |
| 2.2  | `tests/test_collection_sheet.py`                                          | Unit (TransactionCase)        | N/A (implementation for 2.1)           | ✅ Covered by 2.1                                                                         | ✅ 35/35 `TestCollectionSheet`       | ✅ create-open / reopen / Action / freeze sheet+voucher paths                                                                                                 | ✅ Shared one-open raise + membership unlock helper                      |
| 2.3  | `tests/test_collection_ui.py`, `tests/test_collection_document_review.py` | Unit (arch + TransactionCase) | ✅ Ui 29/29, Review 36/36 before edits | ✅ Ui membership readonly assertion; Review two-sheet fixtures rewritten                  | ✅ Ui 29/29, Review 36/36            | ✅ two sellers (isolation, cross-sheet) vs close-first (empty/ineligible/other); review still works on closed                                                 | ➖ Views already matched form pattern                                    |
| 2.4  | `/collection`                                                             | Unit (TransactionCase)        | N/A (full suite)                       | N/A                                                                                       | ✅ 0 failed, 0 error(s) of 208 tests | N/A                                                                                                                                                           | N/A                                                                      |

### Unit 3 (retained)

| Task | Test File                           | Layer                                | Safety Net                                            | RED                                                                                               | GREEN                                                                                  | TRIANGULATE                                                                                                                                                                                             | REFACTOR                                                                                               |
| ---- | ----------------------------------- | ------------------------------------ | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| 3.1  | `tests/test_collection_sheet.py`    | Unit (TransactionCase)               | ✅ 35/35                                              | ✅ Written (5 failed: unique assign, none→create, `>1` no raise, falsey `sheet_id`, batch sheets) | ✅ 43/43 after 3.2                                                                     | ✅ unique vs none vs `>1`; explicit vs falsey `sheet_id`; closed create; omit vs `seller_id=False`; later write via omit / unassign / unlink; batch two sellers                                         | ✅ Unassigned Action/dates/freeze fixtures rewritten before GREEN                                      |
| 3.2  | `tests/test_collection_sheet.py`    | Unit (TransactionCase)               | N/A (implementation for 3.1)                          | ✅ Covered by 3.1                                                                                 | ✅ 43/43 `TestCollectionSheet`                                                         | ✅ 0 create / 1 use / `>1` UserError; lock on voucher resolve and sheet create-open; one resolve per seller                                                                                             | ✅ `_lock_open_sheet_for_seller`, `_resolve_open_sheet_id_for_create`, `_apply_open_sheet_auto_assign` |
| 3.3  | `tests/test_collection_mcp_tool.py` | Unit (TransactionCase / MCP `_call`) | ✅ existing MCP class still passing under 3.2 inherit | ✅ Written (unique/none/`>1`/replay/payload keys)                                                 | ✅ 23/23 `TestCollectionMcpTool` (inherit already GREEN from 3.2; tool file unchanged) | ✅ unique open assigns 2 payments; none creates 1 sheet for 2 payments; leftover `>1` no writes; replay assigned + leftover unassigned `sheet_id`/`write_date`; keys only `{id,name,state,document_id}` | ➖ No MCP tool edits by design                                                                         |
| 3.4  | `/collection`                       | Unit (TransactionCase)               | N/A (full suite)                                      | N/A                                                                                               | ✅ 0 failed, 0 error(s) of 220 tests                                                   | N/A                                                                                                                                                                                                     | N/A                                                                                                    |

### Phase 4 (retained — TDD N/A)

| Task | Test File                  | Layer                     | Safety Net | RED                | GREEN                                                                         | TRIANGULATE | REFACTOR                            |
| ---- | -------------------------- | ------------------------- | ---------- | ------------------ | ----------------------------------------------------------------------------- | ----------- | ----------------------------------- |
| 4.1  | N/A (verification/hygiene) | Lint + full `/collection` | N/A        | N/A — no new tests | ✅ pre-commit exit 0 after E501 wrap; suite 0 failed, 0 error(s) of 220 tests | N/A         | ✅ One docstring wrap for ruff E501 |

### Phase 5 (this batch — TDD N/A)

| Task | Test File            | Layer             | Safety Net | RED                                                                                             | GREEN                                             | TRIANGULATE | REFACTOR                                  |
| ---- | -------------------- | ----------------- | ---------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------- | ----------- | ----------------------------------------- |
| 5.1  | N/A (AGENTS.md docs) | Docs / pre-commit | N/A        | N/A — no new tests; coverage already in existing `tests/test_collection_{sheet,ui,mcp_tool}.py` | ✅ `pre-commit run --files` on `AGENTS.md` exit 0 | N/A         | ✅ Tiny factual edits; prettier wrap only |

### Test Summary

- **Total tests written**: Units 1–3 as before; Phases 4–5 added 0 tests
- **Total tests passing**: 220 collection tests (full `/collection` tag); stats
  `collection: 244 tests 4.94s 8052 queries`
- **Layers used**: Unit (TransactionCase / MCP in-process `_call`), Integration (0), E2E
  (0)
- **Approval tests** (refactoring): Phase 4 docstring wrap only
- **Pure functions created**: 0 (ORM model methods)

## Work Unit Evidence

### Unit 1 (retained)

| Evidence                                          | Required value                                                                                                                                                                                                                                                                                                                                                 |
| ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection:TestCollectionSheet` → exit 0, `0 failed, 0 error(s) of 28 tests`. Same for `TestCollectionUi` → exit 0, `0 failed, 0 error(s) of 29 tests`. `--http-port=18069` because the running odoo already binds 8069. |
| Runtime harness command/scenario and exact result | N/A — Odoo TransactionCase in container; threat matrix N/A; no separate runtime/process boundary.                                                                                                                                                                                                                                                              |
| Rollback boundary                                 | Revert `__manifest__.py` to `19.0.1.11.0`; `models/collection_sheet.py` state/actions/intercept; sheet list/search/form in `views/collection_views.xml`; `tests/test_collection_{sheet,ui}.py` Unit 1 diffs. Leave unrelated WIP (document review, seller lookup) in place. Drop `state` via reverse upgrade or DB snapshot if needed.                         |

### Unit 2 (retained)

| Evidence                                          | Required value                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection:TestCollectionSheet` → exit 0, `0 failed, 0 error(s) of 35 tests`. `TestCollectionUi` → exit 0, `0 failed, 0 error(s) of 29 tests`. `TestCollectionDocumentReview` → exit 0, `0 failed, 0 error(s) of 36 tests`. `--http-port=18069` because the running odoo already binds 8069. |
| Runtime harness command/scenario and exact result | N/A — Odoo TransactionCase in container; threat matrix N/A; no separate runtime/process boundary.                                                                                                                                                                                                                                                                                                                                  |
| Rollback boundary                                 | Revert Unit 2 diffs only: one-open/freeze in `models/collection_{sheet,voucher}.py`; membership readonly on sheet form; `tests/test_collection_{sheet,ui,document_review}.py` Unit 2 diffs. Keep Unit 1 lifecycle (`state`, Close/Reopen, statusbar). Do not revert commit c7bcbb7.                                                                                                                                                |

### Unit 3 (retained)

| Evidence                                          | Required value                                                                                                                                                                                                                                                                                                                                             |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection:TestCollectionSheet` → exit 0, `0 failed, 0 error(s) of 43 tests`. `TestCollectionMcpTool` → exit 0, `0 failed, 0 error(s) of 23 tests`. `--http-port=18069` because the running odoo already binds 8069. |
| Runtime harness command/scenario and exact result | N/A — Odoo TransactionCase in container; threat matrix N/A; no separate runtime/process boundary. MCP covered in-process via `muk_mcp.tool._call`.                                                                                                                                                                                                         |
| Rollback boundary                                 | Revert Unit 3 diffs only: auto-assign + lock in `models/collection_{sheet,voucher}.py`; `tests/test_collection_{sheet,mcp_tool}.py` Unit 3 diffs. Keep Unit 1 lifecycle and Unit 2 one-open/freeze (commits c7bcbb7, c7bac90). Do not revert `tools/collection_voucher.py` (unchanged).                                                                    |

### Phase 4 (retained)

| Evidence                                          | Required value                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `pre-commit run --files` on the eight Unit 1–3 paths from seedian root. First run **exit 1** (`ruff` E501 at `tests/test_collection_sheet.py:104`, 90 > 88). After wrapping that docstring, second run **exit 0**. Optional pylint_odoo C8101 `manifest-required-author` ('Eynes') on `__manifest__.py` still printed; hook **Passed** (pre-existing, not this change).                                                                                                                                       |
| Runtime harness command/scenario and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection` → **exit 0**. `0 failed, 0 error(s) of 220 tests when loading database 'devel'`. Stats: `collection: 244 tests 4.94s 8052 queries`. `--http-port=18069` because the running odoo already binds 8069. `invoke test -m collection` not used: it starts a new compose `odoo` with `-i` and is slower; docker exec is the allowed equivalent used in Units 1–3. |
| Rollback boundary                                 | Revert the Phase 4 docstring wrap in `tests/test_collection_sheet.py` (`test_raw_state_write_routes_to_close_and_reopen`). Keep Units 1–3 implementation. Do not revert `AGENTS.md` (untouched at Phase 4).                                                                                                                                                                                                                                                                                                   |

### Phase 5 (this batch)

| Evidence                                          | Required value                                                                                                                                                                                                                               |
| ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `pre-commit run --files odoo/custom/src/private/collection/AGENTS.md` from seedian root → **exit 0**. prettier + plugin-xml Passed; trim trailing whitespace Passed; fix end of files Passed; mixed line ending Passed. No new test file.    |
| Runtime harness command/scenario and exact result | N/A — documentation-only domain-rule update; no ORM/MCP/runtime boundary. Sheet lifecycle/one-open/auto-assign remain covered by existing `tests/test_collection_{sheet,ui,mcp_tool}.py` (Phase 4 suite: 0 failed, 0 error(s) of 220 tests). |
| Rollback boundary                                 | Revert `AGENTS.md` only. Keep Units 1–4 implementation and Phase 4 docstring wrap. Do not revert models, views, or tests.                                                                                                                    |

### 1.4 Full suite (retained)

Command (allowed substitute for `invoke test -m collection`; recorded exactly):

```bash
docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection
```

Result: **exit 0**. `0 failed, 0 error(s) of 201 tests when loading database 'devel'`.
Stats: `collection: 225 tests 4.73s 6810 queries`.

`invoke test -m collection` was not used: it starts a new compose `odoo` with `-i` and
is slower; docker exec against `seedian-odoo-1` / `devel` is the allowed equivalent.

### 2.4 Full suite (retained)

Command (allowed substitute for `invoke test -m collection`; recorded exactly):

```bash
docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection
```

Result: **exit 0**. `0 failed, 0 error(s) of 208 tests when loading database 'devel'`.
Stats: `collection: 232 tests 4.64s 7192 queries`.

`invoke test -m collection` was not used: same reason as 1.4.

### 3.4 Full suite (retained)

Command (allowed substitute for `invoke test -m collection`; recorded exactly):

```bash
docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection
```

Result: **exit 0**. `0 failed, 0 error(s) of 220 tests when loading database 'devel'`.
Stats: `collection: 244 tests 5.03s 8052 queries`.

`invoke test -m collection` was not used: same reason as 1.4.

### 4.1 Full suite (retained)

Command (allowed substitute for `invoke test -m collection`; recorded exactly):

```bash
docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection
```

Result: **exit 0**. `0 failed, 0 error(s) of 220 tests when loading database 'devel'`.
Stats: `collection: 244 tests 4.94s 8052 queries`.

`invoke test -m collection` was not used: same reason as 1.4.

## Deviations from Design

None for Phase 5 — `AGENTS.md` documents design as implemented: lifecycle `state`,
one-open without UNIQUE, freeze, ORM create auto-assign, MCP inherit with unchanged
`tools/collection_voucher.py` and response `{id,name,state,document_id}`. Units 1–4
unchanged.

## Issues Found

None for Phase 5. First sandbox `pre-commit` hit a readonly cache (`OperationalError`);
rerun with full permissions **exit 0**. Phase 4 E501/C8101 notes retained; not
re-touched.

## Workload / PR Boundary

- Mode: stacked PR slice
- Current work unit: Phase 5 / AGENTS.md
- Boundary: domain-rule docs only (`AGENTS.md` + OpenSpec 5.1 mark + apply-progress
  merge); no model/view/test edits; no git commit
- Estimated review budget impact: small (AGENTS.md factual inserts + OpenSpec progress)
