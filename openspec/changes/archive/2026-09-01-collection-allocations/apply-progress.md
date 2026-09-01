# Apply Progress: collection-allocations

**Change**: collection-allocations
**Mode**: Strict TDD
**Work unit**: Phase 3 (tasks 3.1–3.3) — views, menu 30, sheet notebook (Phase 1+2 retained)
**Delivery**: auto-chain / stacked-to-main (PR 3 of 3, stacks on PR 2)
**applyState after this batch**: Phase 1+2+3 complete; ready for verify

## Completed Tasks

- [x] 1.1 RED `tests/test_collection_allocation.py`
- [x] 1.2 RED `tests/test_collection_allocation_acl.py`
- [x] 1.3 RED `tests/test_collection_company_migration.py` version `19.0.1.25.0` + `CA/`
- [x] 1.4 RED `tests/test_collection_sheet.py` unlink empty vs allocated
- [x] 1.5 GREEN three allocation models + `models/__init__.py`
- [x] 1.6 GREEN voucher `allocation_id` + sheet `allocation_ids` / restrict
- [x] 1.7 GREEN ACL + three company `ir.rule`s
- [x] 1.8 GREEN sequence, `migrations/19.0.1.25.0/post-migrate.py`, manifest, test imports
- [x] 1.9 REFACTOR + `AGENTS.md` + `-u collection` + full module tests + scoped pre-commit
- [x] 2.1 RED `tests/test_collection_mcp_allocation.py`
- [x] 2.2 GREEN `tools/collection_allocation.py` + `tools/__init__.py` + test import
- [x] 2.3 REFACTOR + `AGENTS.md` MCP row + full module tests + scoped pre-commit
- [x] 3.1 RED `tests/test_collection_ui.py`: allocation `<list>`/form/search; menu sequence 30; sheet form notebook vouchers + allocations
- [x] 3.2 GREEN `views/collection_allocation_views.xml` + sheet notebook + manifest `data`
- [x] 3.3 REFACTOR + `AGENTS.md` UI/tests + `-u collection` + full suite + scoped pre-commit

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_collection_allocation.py` | Unit (TransactionCase) | N/A (new) | ✅ Written (18 cases: UNIQUE, freeze, DELETE sanitizer, residual confirmed-only, validate/reject, revision UNIQUE `request_id` + revision dup, unlink-with-revisions, `allocation_id` write, allocated unlink) | ✅ Passed in full suite | ✅ Happy + edge (other partner/sheet UNIQUE; confirmed still writable; residual 0 / +reason / negative-after-validate; unlink without revisions still allowed) | ✅ Freeze uses other-seller sheet; `allocation_id` write avoids residual side-effect |
| 1.2 | `tests/test_collection_allocation_acl.py` | Unit (TransactionCase) | N/A (new) | ✅ Written (ACL 1,1,1,1 / revision 1,0,1,0; three `ir.rule`s; `inspect.getsource` + file source no `.sudo(`; related stored `company_id`) | ✅ Passed | ✅ Portal deny + other-company hide + internal CRUD | ✅ `Path` import; internal revision write is `UserError` (override before ACL), unlink is `AccessError` |
| 1.3 | `tests/test_collection_company_migration.py` | Unit (TransactionCase) | ✅ Existing migration tests | ✅ Written (`19.0.1.25.0`; `seq_collection_allocation`; SPECS `CA/` not in 1.17.0 `COLLECTION_SEQUENCE_CODES`) | ✅ Passed | ✅ New-company copies `COL`/`CS`/`CA` | ➖ None needed |
| 1.4 | `tests/test_collection_sheet.py` | Unit (TransactionCase) | ✅ Existing unlink tests | ✅ Written (empty unlink unassigns; allocated unlink refused, members stay) | ✅ Passed | ✅ Open + closed empty unlink still unassign | ✅ Allocated refuse via `@api.ondelete` (not raise-in-`unlink`) |
| 1.5 | `tests/test_collection_allocation.py` | Unit | N/A (new models) | ✅ 1.1 tests referenced missing models first | ✅ Models exist and pass | ✅ Line CHECK + related currency/company | ➖ Models already matched design |
| 1.6 | `tests/test_collection_allocation.py` + `tests/test_collection_sheet.py` | Unit | ✅ Voucher/sheet unlink baseline | ✅ 1.1/1.4 cover write/ondelete/restrict | ✅ `allocation_id` set-null + `check_company`; sheet `allocation_ids`; FK restrict + `@api.ondelete` | ✅ Unallocated pending unlink still allowed | ✅ pylint E8140: allocated-sheet guard is `@api.ondelete`, not `unlink()` |
| 1.7 | `tests/test_collection_allocation_acl.py` | Unit | N/A (new ACL rows) | ✅ 1.2 | ✅ CSV + three `ir.rule`s | ✅ Portal + company hide | ➖ None needed |
| 1.8 | `tests/test_collection_company_migration.py` | Unit | ✅ Sequence copy tests | ✅ 1.3 | ✅ XMLID, SPECS padding 4, post-migrate `_collection_copy_sequences()`, manifest `19.0.1.25.0`, tests imported | ✅ Company create copies `CA/` | ➖ None needed |
| 1.9 | `AGENTS.md` + suite | Integration | ✅ 478-test suite | ➖ Docs/verification | ✅ `-u collection` exit 0; `invoke test -m collection --mode=update` → `0 failed, 0 error(s) of 478 tests`; scoped pre-commit Passed | ➖ Single | ✅ `AGENTS.md` models/seq/ACL/tests/version |
| 2.1 | `tests/test_collection_mcp_allocation.py` | Integration (TransactionCase / MCP `_call`) | N/A (new) | ✅ Written first (21 cases referencing missing `create_collection_allocation`); RED `8 failed, 12 error(s) of 21` — tool not found | ➖ RED only | ✅ Create + replay + amend + gates + UniqueViolation + subtract + residual | ➖ RED only |
| 2.2 | `tests/test_collection_mcp_allocation.py` | Integration | N/A (new tool) | ✅ 2.1 | ✅ `0 failed, 0 error(s) of 21 tests` after `-u collection` | ✅ request_id replay vs content_hash; subset vs partial overlap; confirmed vs validated subtract vs rejected ignore; residual reason vs empty invoices | ✅ Amend keeps residual_reason placeholder across `Command.clear()` flush |
| 2.3 | `AGENTS.md` + suite | Integration | ✅ 478 Phase 1 tests | ➖ Docs/verification | ✅ `invoke test -m collection --mode=update` → `0 failed, 0 error(s) of 499 tests`; scoped pre-commit Passed | ➖ Single | ✅ Split invoice form parser; `_collection_allocation_persist_amend`; `AGENTS.md` MCP row |
| 3.1 | `tests/test_collection_ui.py` | Unit (TransactionCase / view arch) | ✅ `TestCollectionUi` `0 failed, 0 error(s) of 43 tests` | ✅ Written first; RED `1 failed, 2 error(s) of 3` — missing xmlids + no sheet notebook | ➖ RED only | ✅ Menu/list/search + form Validate/Reject + sheet notebook pages | ➖ RED only |
| 3.2 | `tests/test_collection_ui.py` | Unit (TransactionCase / view arch) | ✅ Existing sheet Close/Reopen + `voucher_ids` still present | ✅ 3.1 | ✅ After `-u collection`: `TestCollectionUi` `0 failed, 0 error(s) of 46 tests` | ✅ `<list>` not `<tree>`; path `collection-allocations`; menu seq 30 after sheets 20; voucher_ids many2many kept; allocation_ids notebook page | ➖ XML prettier wrap only |
| 3.3 | `AGENTS.md` + suite | Integration | ✅ 499 Phase 2 tests | ➖ Docs/verification | ✅ `invoke test -m collection --mode=update` → `0 failed, 0 error(s) of 502 tests`; scoped pre-commit Passed (optional C8101 author warning pre-existing) | ➖ Single | ✅ Notebook page string constants; `AGENTS.md` UI/tests row + repo map |

### Test Summary

- **Total tests written** (Phase 1 allocation surface): 18 allocation + 6 ACL + migration/sheet deltas
- **Total tests written** (Phase 2 MCP): 21 (`TestCollectionMcpAllocation`)
- **Total tests written** (Phase 3 UI): 3 (`test_collection_allocations_menu_list_form_search`, `test_collection_allocations_form_statusbar_validate_reject`, `test_sheet_form_notebook_vouchers_and_allocations`)
- **Total tests passing**: 502 (`0 failed, 0 error(s) of 502 tests`)
- **Layers used**: Unit (TransactionCase) + Integration MCP, E2E 0
- **Approval tests** (refactoring): sheet empty-unlink tests preserved current unassign behavior; existing sheet form Close/Reopen + `voucher_ids` assertions still pass after notebook wrap
- **Pure functions created**: 0 (ORM / MCP mixin / XML views)

## Work Unit Evidence

### Phase 1 (retained)

| Evidence | Required value |
|---|---|
| Focused test command and exact result | `invoke test -m collection --mode=update` (Seedian root; default `db_filter='^devel$'`) → exit 0; `0 failed, 0 error(s) of 478 tests when loading database 'devel'` |
| Runtime harness command/scenario and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init` → exit 0; `Modules loaded.`; registry loaded; no ERROR/CRITICAL. Invoke update-mode tests reloaded the same module including `@api.ondelete` sheet guard. |
| Rollback boundary | Phase 1 files only: `models/collection_allocation.py`, `models/collection_allocation_line.py`, `models/collection_allocation_revision.py`, `models/__init__.py`, `models/collection_voucher.py` (`allocation_id` + guards), `models/collection_sheet.py` (`allocation_ids` + ondelete), `models/res_company.py` (SPECS), `security/ir.model.access.csv`, `security/collection_security.xml`, `data/ir_sequence_data.xml`, `migrations/19.0.1.25.0/post-migrate.py`, `__manifest__.py` `19.0.1.25.0`, `tests/test_collection_allocation.py`, `tests/test_collection_allocation_acl.py`, `tests/test_collection_company_migration.py`, `tests/test_collection_sheet.py`, `tests/__init__.py`, `AGENTS.md`. Does not include Phase 2 MCP or Phase 3 views. |

### Phase 2 (retained)

| Evidence | Required value |
|---|---|
| Focused test command and exact result | `docker exec -i seedian-odoo-1 odoo --http-port=18069 -d devel --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionMcpAllocation` → exit 0; `0 failed, 0 error(s) of 21 tests when loading database 'devel'`. Full suite: `invoke test -m collection --mode=update` → exit 0; `0 failed, 0 error(s) of 499 tests when loading database 'devel'`. |
| Runtime harness command/scenario and exact result | N/A — no HTTP/UI boundary in this unit. MCP TransactionCase `_call` covers create, `request_id`/`content_hash` replay, SUPERSET amend, UniqueViolation replay/generic (no ids), and input/ERP/residual/freeze gates. Registry load of the new mixin used `-u collection` (bundled with the focused test command above). |
| Rollback boundary | Phase 2 files only: `tools/collection_allocation.py`, `tools/__init__.py`, `tests/test_collection_mcp_allocation.py`, `tests/__init__.py` (MCP test import), `AGENTS.md` MCP row. Does not revert Phase 1 models/ACL/seq or Phase 3 views. |

### Phase 3

| Evidence | Required value |
|---|---|
| Focused test command and exact result | RED: `docker exec -i seedian-odoo-1 odoo --http-port=18069 -d devel --test-enable --stop-after-init --workers=0 --test-tags /collection:TestCollectionUi.test_collection_allocations_menu_list_form_search,/collection:TestCollectionUi.test_collection_allocations_form_statusbar_validate_reject,/collection:TestCollectionUi.test_sheet_form_notebook_vouchers_and_allocations` → `1 failed, 2 error(s) of 3 tests`. GREEN: `--test-tags /collection:TestCollectionUi` → `0 failed, 0 error(s) of 46 tests`. Full suite: `invoke test -m collection --mode=update` → exit 0; `0 failed, 0 error(s) of 502 tests when loading database 'devel'`. |
| Runtime harness command/scenario and exact result | `docker exec -i seedian-odoo-1 odoo --http-port=18069 -d devel -u collection --stop-after-init` → exit 0; loaded `collection/views/collection_allocation_views.xml`; `Modules loaded.`; no ERROR/CRITICAL. Invoke `--mode=update` also `-u collection` and reloaded views. |
| Rollback boundary | Phase 3 files only: `views/collection_allocation_views.xml`, `views/collection_views.xml` (sheet notebook wrap), `__manifest__.py` `data` entry, `tests/test_collection_ui.py` (3 new methods + notebook constants), `AGENTS.md` UI/tests row. Does not revert Phase 1 models/ACL/seq or Phase 2 MCP. |

## Files Changed

### Phase 1 (retained)

| File | Action | What Was Done |
|------|--------|---------------|
| `tests/test_collection_allocation.py` | Created | UNIQUE, freeze, sanitizer, residual, validate/reject, revisions, voucher guards |
| `tests/test_collection_allocation_acl.py` | Created | ACL, ir.rule, no sudo, related company_id |
| `tests/test_collection_company_migration.py` | Modified | Version 1.25.0; `CA/` SPECS/XMLID; not in 1.17.0 codes |
| `tests/test_collection_sheet.py` | Modified | Empty unlink still unassigns; allocated unlink refused |
| `tests/__init__.py` | Modified | Import allocation tests |
| `models/collection_allocation.py` | Created | Header, UNIQUE, freeze, sanitizer, residual confirmed-only, validate/reject |
| `models/collection_allocation_line.py` | Created | Snapshot lines; related currency/company; CHECK/UNIQUE |
| `models/collection_allocation_revision.py` | Created | Immutable; gated create; UNIQUE request_id |
| `models/__init__.py` | Modified | Import allocation models |
| `models/collection_voucher.py` | Modified | `allocation_id` set-null + check_company; write/ondelete |
| `models/collection_sheet.py` | Modified | `allocation_ids`; `@api.ondelete` when allocated |
| `models/res_company.py` | Modified | SPECS `CA/%(year)s/` padding 4 |
| `security/ir.model.access.csv` | Modified | allocation/line `1,1,1,1`; revision `1,0,1,0` |
| `security/collection_security.xml` | Modified | Three company ir.rules |
| `data/ir_sequence_data.xml` | Modified | `seq_collection_allocation` on `base.main_company` |
| `migrations/19.0.1.25.0/post-migrate.py` | Created | `_collection_copy_sequences()` |
| `__manifest__.py` | Modified | `19.0.1.25.0` (no allocation views) |
| `AGENTS.md` | Modified | Models, seq `CA/`, ACL, tests, version 1.25.0 |

### Phase 2 (retained)

| File | Action | What Was Done |
|------|--------|---------------|
| `tests/test_collection_mcp_allocation.py` | Created | MCP create/replay/amend/gates/UniqueViolation/subtract/residual/no-sudo |
| `tests/__init__.py` | Modified | Import `test_collection_mcp_allocation` |
| `tools/collection_allocation.py` | Created | `@mcp_tool` write `create_collection_allocation`; no sudo; binding-only partner |
| `tools/__init__.py` | Modified | Import allocation tool |
| `AGENTS.md` | Modified | MCP write row, repo map, tests table |

### Phase 3

| File | Action | What Was Done |
|------|--------|---------------|
| `tests/test_collection_ui.py` | Modified | Allocation list/form/search/`<list>`; menu seq 30 after sheets; sheet notebook vouchers + allocations; Validate/Reject header |
| `views/collection_allocation_views.xml` | Created | List/form/search; `path` `collection-allocations`; menuitem parent `menu_collection_root` sequence 30 |
| `views/collection_views.xml` | Modified | Sheet form notebook: Vouchers (`voucher_ids` many2many kept) + Allocations (`allocation_ids`) |
| `__manifest__.py` | Modified | `data` includes `views/collection_allocation_views.xml` (existing files kept) |
| `AGENTS.md` | Modified | Repo map allocation views; UI domain (menu 30, notebook, Validate/Reject); tests table row |

## Deviations from Design

- Allocated-sheet delete: design says `sheet_id ondelete="restrict"`. Implemented that **and** `@api.ondelete` `UserError` so UI unlink fails cleanly. Did **not** raise inside `unlink()` (pylint-odoo `E8140 no-raise-unlink`).
- `invoke test ... -d devel` is not an invoke task flag (`-d` is invoke debug). Used `invoke test -m collection --mode=update` with default `db_filter='^devel$'`.
- Same-company UniqueViolation replay is exercised by missing the first `request_id` search then raising `UniqueViolation` from `_collection_allocation_write` (the live UNIQUE(sheet, partner) path hash-replays before insert). Hidden other-company `request_id` still hits a real unique index.
- Amend `Command.clear()` flushes residual before replacement lines exist; persist keeps a placeholder `residual_reason` across that flush (not specified in design; required by confirmed residual constraint).
- Mixed-seller voucher rows on one sheet are refused by existing voucher/sheet seller equality; MCP still rejects `seller_id` ≠ voucher seller.
- Sheet notebook Allocations nested `<list>` omits `partner_id` so `test_customer_field_is_partner_id_without_domain` still counts one unbound `partner_id` on the sheet form (the voucher membership list). Customer is shown on the dedicated allocation list/form.

## Issues Found

- pylint-odoo optional `C8101 manifest-required-author` (Eynes) is pre-existing; mandatory pylint passed.
- Duplicate OCR/seller field labels on `collection.voucher` are pre-existing warnings.
- MuK MCP `get_tools` drops JSON Schema `exclusiveMinimum`; Python still rejects `amount_applied` ≤ 0; the keyword remains on the in-module schema constant.
- Missing filestore blobs on `devel` produce `ir.attachment` `FileNotFoundError` INFO traces during `load_menus`; tests still pass (pre-existing).

## Remaining Tasks

None — all 1.x, 2.x, and 3.x tasks are `[x]`. Ready for verify.
