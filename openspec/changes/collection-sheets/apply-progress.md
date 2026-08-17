# Apply Progress: collection-sheets

**Change**: collection-sheets
**Mode**: Strict TDD
**Batch**: PR 2 of 4 (tasks 2.1–2.3); PR 1 complete
**Branch**: `feat/collection-sheets-02-sheet-sequence` (from `feat/collection-sheets-01-seller-mcp`)
**Chain strategy**: stacked-to-main

## Completed Tasks

- [x] 1.1 RED `tests/test_collection_voucher.py`: ORM create without seller stays null; no backfill.
- [x] 1.2 RED `tests/test_collection_ui.py`: form `required="1"` on `seller_id`; list/form/search show it.
- [x] 1.3 RED `tests/test_collection_mcp_tool.py`: require `seller_id`; all-new stamps; exact replay no mutate (incl. null); missing/portal/unknown reject, no writes.
- [x] 1.4 GREEN `models/collection_voucher.py`: nullable `seller_id` → `res.users`, domain `[('share','=',False)]`.
- [x] 1.5 GREEN `tools/collection_voucher.py`: validate internal `seller_id`; stamp all-new only; replay read-only; no `sudo()`. Voucher seller in `views/collection_views.xml`. REFACTOR.
- [x] 2.1 RED `tests/test_collection_sheet.py`: unique `CS/<year>/<number>`; no `state`; missing seller and post-create seller write rejected; not from `create_uid`.
- [x] 2.2 GREEN create `models/collection_sheet.py`: required frozen `seller_id`; sequence `collection.sheet`.
- [x] 2.3 GREEN `models/__init__.py`; `data/ir_sequence_data.xml` `CS/%(year)s/` pad 4; `security/ir.model.access.csv` one `base.group_user` CRUD row; `tests/__init__.py`. REFACTOR.

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_collection_voucher.py` | Unit | ✅ voucher tests passed (pre-existing 12 flag failures elsewhere) | ✅ Written: field missing / `Invalid field 'seller_id'` | ✅ Passed | ✅ 2 cases (null create + write does not backfill / explicit seller persists) | ➖ None needed |
| 1.2 | `tests/test_collection_ui.py` | Unit (arch) | ✅ UI tests except flag-off menu | ✅ Written: form/list missing `seller_id` | ✅ Passed | ✅ form `required="1"` + list/form/search exposure | ➖ None needed |
| 1.3 | `tests/test_collection_mcp_tool.py` | Integration | ✅ MCP/attachment tests passed | ✅ Written: schema missing `seller_id`; missing seller created rows; stamp TypeError; null replay AttributeError | ✅ Passed | ✅ stamp, null replay, different-seller replay, missing/portal/unknown | ✅ `_collection_require_internal_seller` helper |
| 1.4 | `models/collection_voucher.py` | Unit | same as 1.1 | ✅ 1.1 tests | ✅ nullable Many2one + domain | covered by 1.1 | ➖ Field already minimal |
| 1.5 | `tools/collection_voucher.py`, `views/collection_views.xml` | Integration | same as 1.3 | ✅ 1.2+1.3 tests | ✅ schema/validate/stamp/replay + views | covered by 1.2+1.3 | ✅ seller helper; replay ignores seller |

### Test Summary

- **Total tests written**: 11 (2 voucher + 2 UI + 7 MCP seller, including schema assertion and replay triangulation)
- **Focused tests passing**: 51/51 (`TestCollectionVoucher` + `TestCollectionMcpTool` + `TestCollectionMcpAttachment` + seller UI methods)
- **Layers used**: Unit (voucher/UI arch), Integration (MCP TransactionCase)
- **Approval tests** (refactoring): None — no refactoring-only tasks
- **Pure functions created**: 0 (ORM/MCP helpers on `muk_mcp.mixin`)

## Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command and exact result | `docker compose run --rm odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionVoucher,/collection:TestCollectionMcpTool,/collection:TestCollectionMcpAttachment,.test_form_seller_id_is_required,.test_list_form_search_expose_seller_id` → **0 failed, 0 error(s) of 51 tests** |
| Official runner | `invoke test -m collection --mode=update` → **12 failed, 0 error(s) of 142 tests**. All 12 are pre-existing `document_review_enabled=True` on devel company (`TestCollectionDocumentReviewFlag.*` + `test_load_menus_omits_document_review_when_flag_off`). Same 12 failed on safety net before this slice (132 tests then). No seller/MCP regressions. |
| Runtime harness | `invoke install -m collection` → **exit 0** (module init/upgrade on devel; nullable `seller_id` column added) |
| Rollback boundary | Revert voucher `seller_id` field; MCP `seller_id` schema/validation/stamp; voucher list/form/search `seller_id`; seller tests. Does not revert sheet model, Action, or manifest bump (not in this slice). Unrelated stashed settings menu WIP was not committed. |

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `models/collection_voucher.py` | Modified | Nullable `seller_id` Many2one `res.users`, domain `[('share', '=', False)]` |
| `tools/collection_voucher.py` | Modified | Required top-level `seller_id`; internal-user validation; stamp all-new only; replay read-only; no `sudo()` |
| `views/collection_views.xml` | Modified | List/search expose `seller_id`; form `required="1"` |
| `tests/test_collection_voucher.py` | Modified | Null seller + no-backfill tests |
| `tests/test_collection_ui.py` | Modified | Form required + list/form/search exposure |
| `tests/test_collection_mcp_tool.py` | Modified | Schema, stamp, replay, missing/portal/unknown; payload helper |
| `openspec/changes/collection-sheets/tasks.md` | Modified | Marked 1.1–1.5 `[x]` |
| `openspec/changes/collection-sheets/apply-progress.md` | Created | This file |

Authored diff (implementation): **342 insertions, 8 deletions** (under 400-line budget).

## Deviations from Design

None — implementation matches design.

## Issues Found

- Devel DB has `res.company.document_review_enabled=True`, so flag-off tests fail independently of this slice. Do not treat as PR1 regressions.
- `invoke test -m collection` default `mode=init` ran **0 tests** because the module was already installed; use `--mode=update` (`-u`) to execute tests.

## Remaining Tasks

- [ ] Phase 3 (PR 3): Action, dates, constraints (3.1–3.6)
- [ ] Phase 4 (PR 4): UI, ACL, upgrade (4.1–4.4)

## Workload / PR Boundary

- Mode: stacked PR slice
- Current work unit: PR1 voucher seller + MCP
- Starts at: collection `main` (`744b8d2`)
- Ends with: nullable voucher `seller_id`; form required + list/form/search exposure; MCP requires top-level `seller_id`, stamps all-new only, exact replay does not mutate (incl. null seller); missing/portal/unknown seller rejected with no writes
- Estimated review budget impact: ~350 authored lines (implementation); within 400

---

## PR 2 of 4 — Sheet model + sequence (2.1–2.3)

**Branch**: `feat/collection-sheets-02-sheet-sequence`
**Base**: `feat/collection-sheets-01-seller-mcp` (`1c02e8c`)

### TDD Cycle Evidence (PR2)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.1 | `tests/test_collection_sheet.py` | Unit | N/A (new) | ✅ Written: `KeyError: collection.sheet` (6/6) | ✅ 0 failed, 0 error(s) of 6 | ✅ sequence unique + pattern; missing seller; freeze other/same seller; seller ≠ create_uid | ✅ `_create_sheet` helper |
| 2.2 | `tests/test_collection_sheet.py` | Unit | N/A (new model) | ✅ 2.1 tests | ✅ required frozen `seller_id`; sequence `collection.sheet`; no `state` | covered by 2.1 | ➖ Model already minimal |
| 2.3 | same | Unit | existing `__init__`/ACL/sequence XML | ✅ 2.1 tests | ✅ import, `CS/%(year)s/` pad 4, one `base.group_user` CRUD row | ➖ Structural wiring | ➖ None needed |

### Test Summary (PR2)

- **Total tests written**: 6
- **Focused tests passing**: 6/6
- **Layers used**: Unit (TransactionCase)
- **Approval tests**: None
- **Pure functions created**: 0

### Work Unit Evidence (PR2)

| Evidence | Result |
|---|---|
| Focused test command and exact result | `docker compose run --rm odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionSheet` → **0 failed, 0 error(s) of 6 tests** |
| Official runner | `invoke test -m collection --mode=update` → **12 failed, 0 error(s) of 150 tests**. Same 12 pre-existing `document_review_enabled=True` flag-off failures. Sheet tests all passed. |
| Runtime harness | `invoke install -m collection` → **exit 0** (sheet table, sequence, ACL loaded on devel) |
| Rollback boundary | Revert `models/collection_sheet.py`, sheet import, `seq_collection_sheet`, sheet ACL row, `tests/test_collection_sheet.py` + test import. Does not revert PR1 seller/MCP or PR3 Action/dates/`sheet_id`. |

### Files Changed (PR2)

| File | Action | What Was Done |
|------|--------|---------------|
| `tests/test_collection_sheet.py` | Created | Sequence, no state, required/frozen seller, not from create_uid |
| `models/collection_sheet.py` | Created | Required readonly `seller_id`; sequence on create; write block |
| `models/__init__.py` | Modified | Import sheet |
| `data/ir_sequence_data.xml` | Modified | `collection.sheet` `CS/%(year)s/` pad 4, `company_id=False` |
| `security/ir.model.access.csv` | Modified | One `base.group_user` CRUD row |
| `tests/__init__.py` | Modified | Import sheet tests |
| `openspec/changes/collection-sheets/tasks.md` | Modified | Marked 2.1–2.3 `[x]` |
| `openspec/changes/collection-sheets/apply-progress.md` | Modified | Merged PR2 evidence |

### Deviations from Design (PR2)

None — implementation matches design. No Action, dates, `sheet_id`, constraints, views, or manifest bump.

### Remaining Tasks

- [ ] Phase 3 (PR 3): Action, dates, constraints (3.1–3.6)
- [ ] Phase 4 (PR 4): UI, ACL, upgrade (4.1–4.4)

### Workload / PR Boundary (PR2)

- Mode: stacked PR slice
- Current work unit: PR2 sheet + sequence
- Starts at: `feat/collection-sheets-01-seller-mcp` (`1c02e8c`)
- Ends with: `collection.sheet` with unique `CS/<year>/<number>`, required frozen `seller_id` (not from `create_uid`), no `state`/chatter, one internal-user ACL row
- Follow-up: PR3 Action/dates/constraints from this branch
