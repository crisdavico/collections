# Apply Progress: document-review-feature-flag

**Change**: document-review-feature-flag **Mode**: Strict TDD **Work unit**: 4 / PR 4
(Phase 4 confirmation only; Phase 1–3 retained) **Chain strategy**: stacked-to-main

## Completed Tasks

- [x] 1.1 RED: flag test — `env.company.document_review_enabled` is False
- [x] 1.2 GREEN: `res.company` Boolean default False
- [x] 1.3 RED: Settings related write persists on `company_id`
- [x] 1.4 GREEN: related field, Settings view `#collections`, manifest `19.0.1.8.0`
- [x] 1.5 GREEN: `_document_review_enabled()` + `write` cache clear
- [x] 1.6 REFACTOR: AGPL headers, tests, upgrade, pre-commit
- [x] 2.1 RED: flag test — OFF `action_validate()` succeeds with pending attached line
- [x] 2.2 GREEN: `_ensure_no_pending_attached_review` returns when helper is false
- [x] 2.3 RED: flag test — OFF four review RPCs raise `UserError` not `[]`
- [x] 2.4 GREEN: four RPCs raise `UserError("Document Review is not enabled.")` before
      queue/lock
- [x] 2.5 GREEN opt-in: review `setUp`, validate-blocked voucher test, ACL review tests
- [x] 2.6 REFACTOR: extracted `_ensure_document_review_enabled`; full module tests
- [x] 3.1 RED: settings arch `name="collections"` + related field; `load_menus` OFF/ON
- [x] 3.2 GREEN: `ir.ui.menu._load_menus_blacklist` appends review menu id when helper
      false
- [x] 3.3 RED/GREEN: payment-line views still show `state` / audit when OFF
- [x] 3.4 REFACTOR: full tests, upgrade, pre-commit
- [x] 4.1 Confirm `views/collection_document_review_views.xml` untouched; no
      `menu.active`; no voucher `company_id`

## Files Changed

### Phase 1 (PR 1)

| File                                                     | Action   | What Was Done                                     |
| -------------------------------------------------------- | -------- | ------------------------------------------------- |
| `tests/test_collection_document_review_flag.py`          | Created  | Default-off, Settings persist, helper/write tests |
| `tests/__init__.py`                                      | Modified | Import flag tests                                 |
| `models/res_company.py`                                  | Created  | Boolean, private helper, cache-clearing `write`   |
| `models/res_config_settings.py`                          | Created  | Related Boolean `readonly=False`                  |
| `models/__init__.py`                                     | Modified | Import company + settings models                  |
| `views/res_config_settings_views.xml`                    | Created  | Inherit Settings form; `<app name="collections">` |
| `__manifest__.py`                                        | Modified | Data entry + version `19.0.1.7.0` → `19.0.1.8.0`  |
| `openspec/changes/document-review-feature-flag/tasks.md` | Modified | Marked 1.1–1.6 complete                           |

### Phase 2 (PR 2)

| File                                                     | Action   | What Was Done                                                            |
| -------------------------------------------------------- | -------- | ------------------------------------------------------------------------ |
| `tests/test_collection_document_review_flag.py`          | Modified | OFF validate-succeeds + four RPC UserError cases                         |
| `models/collection_voucher.py`                           | Modified | `_ensure_no_pending_attached_review` returns when helper is false        |
| `models/collection_voucher_line.py`                      | Modified | Four RPCs refuse via `_ensure_document_review_enabled` before queue/lock |
| `tests/test_collection_voucher.py`                       | Modified | Opt-in `test_action_validate_blocked_when_attached_line_pending`         |
| `tests/test_collection_document_review.py`               | Modified | `setUp` enables flag (covers `_neutralize_preexisting_queue`)            |
| `tests/test_collection_acl.py`                           | Modified | Review helper enables flag so portal stays `AccessError`                 |
| `openspec/changes/document-review-feature-flag/tasks.md` | Modified | Marked 2.1–2.6 complete                                                  |

### Phase 3 (PR 3)

| File                                                     | Action   | What Was Done                                                                         |
| -------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------- |
| `tests/test_collection_ui.py`                            | Modified | Settings arch + `load_menus` OFF/ON; xmlid tests unchanged                            |
| `models/ir_ui_menu.py`                                   | Created  | `_load_menus_blacklist` appends review menu id when helper is false (no `@api.model`) |
| `models/__init__.py`                                     | Modified | Import `ir_ui_menu`                                                                   |
| `tests/test_collection_document_review_flag.py`          | Modified | Payment-line list/search still expose `state` when OFF and ON                         |
| `openspec/changes/document-review-feature-flag/tasks.md` | Modified | Marked 3.1–3.4 complete                                                               |

### Phase 4 (PR 4)

| File                                                              | Action    | What Was Done                          |
| ----------------------------------------------------------------- | --------- | -------------------------------------- |
| (production)                                                      | Unchanged | no production edits; confirmation only |
| `openspec/changes/document-review-feature-flag/tasks.md`          | Modified  | Marked 4.1 complete                    |
| `openspec/changes/document-review-feature-flag/apply-progress.md` | Modified  | Merged Phase 4 evidence                |

## TDD Cycle Evidence

### Phase 1

| Task | Test File                                       | Layer | Safety Net         | RED                                                                                         | GREEN                                                             | TRIANGULATE                                | REFACTOR                           |
| ---- | ----------------------------------------------- | ----- | ------------------ | ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- | ------------------------------------------ | ---------------------------------- |
| 1.1  | `tests/test_collection_document_review_flag.py` | Unit  | ✅ 113/113         | ✅ Written — `AttributeError` on missing field                                              | ✅ Passed after 1.2                                               | ✅ env.company + browsed/`new()` company   | ➖ None needed                     |
| 1.2  | same                                            | Unit  | N/A (new model)    | ✅ Covered by 1.1                                                                           | ✅ `invoke test -m collection --mode=update` 0 failed / 114 tests | ✅ Second default-off path                 | ➖ Minimal Boolean only            |
| 1.3  | same                                            | Unit  | N/A (new field)    | ✅ Written — `ValueError: Invalid field 'document_review_enabled' in 'res.config.settings'` | ✅ Passed after 1.4                                               | ✅ True then back to False                 | ➖ None needed                     |
| 1.4  | same                                            | Unit  | N/A (new settings) | ✅ Covered by 1.3                                                                           | ✅ 0 failed / 116 tests; view loaded on `-u`                      | ✅ OFF persist after ON                    | ✅ Prettier XML indent             |
| 1.5  | same                                            | Unit  | N/A (new helper)   | ✅ Written — `AttributeError: no attribute '_document_review_enabled'`                      | ✅ 0 failed / 119 tests                                           | ✅ helper False → True → False via `write` | ➖ None needed                     |
| 1.6  | same                                            | Unit  | ✅ 119/119         | ➖ Refactor task                                                                            | ✅ 0 failed / 119 tests                                           | ➖ N/A                                     | ✅ AGPL headers; pre-commit passed |

### Phase 2

| Task | Test File                                                | Layer | Safety Net      | RED                                                                                        | GREEN                                                                  | TRIANGULATE                                                                             | REFACTOR                                       |
| ---- | -------------------------------------------------------- | ----- | --------------- | ------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ---------------------------------------------- |
| 2.1  | `tests/test_collection_document_review_flag.py`          | Unit  | ✅ 119/119      | ✅ Written — `UserError: Cannot validate while attached payment lines are pending review.` | ✅ Passed after 2.2                                                    | ✅ pending-attached OFF succeeds; unattached-pending-allows kept as-is                  | ➖ None needed                                 |
| 2.2  | `models/collection_voucher.py`                           | Unit  | ✅ 119/119      | ✅ Covered by 2.1                                                                          | ✅ focused 0 failed / 3 tests (OFF validate + ON blocked + unattached) | ✅ ON blocked still refuses after opt-in                                                | ➖ Early return only                           |
| 2.3  | `tests/test_collection_document_review_flag.py`          | Unit  | N/A (new cases) | ✅ Written — 4 failed, `UserError not raised`                                              | ✅ Passed after 2.4                                                    | ✅ queue/approve/reject/rotation; approve leaves `pending`; reject leaves voucher `new` | ➖ None needed                                 |
| 2.4  | `models/collection_voucher_line.py`                      | Unit  | N/A (new gates) | ✅ Covered by 2.3                                                                          | ✅ focused 0 failed / 17 tests                                         | ✅ all four RPCs raise exact message                                                    | ✅ Extracted `_ensure_document_review_enabled` |
| 2.5  | `tests/test_collection_{voucher,document_review,acl}.py` | Unit  | N/A (opt-in)    | ➖ Opt-in with GREEN 2.2/2.4                                                               | ✅ ON validate-blocked, review suite `setUp`, ACL portal `AccessError` | ✅ portal AccessError vs internal allow                                                 | ➖ None needed                                 |
| 2.6  | same                                                     | Unit  | ✅ 124/124      | ➖ Refactor task                                                                           | ✅ `invoke test -m collection --mode=update` 0 failed / 124 tests      | ➖ N/A                                                                                  | ✅ Deduped RPC flag check                      |

### Phase 3

| Task | Test File                                       | Layer | Safety Net      | RED                                                                                                                                              | GREEN                                                             | TRIANGULATE                                                                                | REFACTOR                                                   |
| ---- | ----------------------------------------------- | ----- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ---------------------------------------------------------- |
| 3.1  | `tests/test_collection_ui.py`                   | Unit  | ✅ 124/124      | ✅ Written — `test_load_menus_omits_document_review_when_flag_off` failed (`377 unexpectedly found`); settings arch already present from Phase 1 | ✅ Passed after 3.2                                               | ✅ inherit arch + `get_view()`; OFF omit + ON include; other Collections menus stay        | ➖ None needed                                             |
| 3.2  | `models/ir_ui_menu.py`                          | Unit  | N/A (new model) | ✅ Covered by 3.1                                                                                                                                | ✅ focused 0 failed / 4 tests after `-u collection`               | ✅ OFF hides review menu; ON shows it; Payment Vouchers/Lines remain                       | ➖ Matches hr/core (no `@api.model`)                       |
| 3.3  | `tests/test_collection_document_review_flag.py` | Unit  | N/A (new cases) | ✅ Written — missing assertion until added                                                                                                       | ✅ Already passing (0 failed / 2 tests); no view change           | ✅ OFF + ON; list `state` + search filters/group_by; arch has no `document_review_enabled` | ➖ None needed — did not modify payment-line views         |
| 3.4  | same                                            | Unit  | ✅ 130/130      | ➖ Refactor task                                                                                                                                 | ✅ `invoke test -m collection --mode=update` 0 failed / 130 tests | ➖ N/A                                                                                     | ✅ AGPL header; pre-commit passed; no further code cleanup |

### Phase 4

| Task | Test File               | Layer | Safety Net | RED                     | GREEN                   | TRIANGULATE                                                             | REFACTOR                               |
| ---- | ----------------------- | ----- | ---------- | ----------------------- | ----------------------- | ----------------------------------------------------------------------- | -------------------------------------- |
| 4.1  | N/A — confirmation only | N/A   | N/A        | ➖ No production change | ➖ No production change | ✅ views HEAD-identical; no `menu.active`; no voucher/line `company_id` | ➖ None — no leftover accidental edits |

### Test Summary

- **Total tests written (Phase 3)**: 6 (4 UI: settings inherit, combined `get_view`,
  load_menus OFF, load_menus ON; 2 flag: payment-line views OFF + ON)
- **Total tests passing**: 130 collection tests (0 failed, 0 errors); was 124 after
  Phase 2
- **Layers used**: Unit (6 new), Integration (0), E2E (0)
- **Approval tests** (refactoring): 2 — payment-line list/search still expose `state`
  with flag OFF (and ON); `reviewed_by`/`reviewed_at` are not declared on those views so
  they were not asserted as present
- **Pure functions created**: 0

## Work Unit Evidence

### Phase 1

| Evidence                                          | Result                                                                                                                                                                                                                      |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `invoke test -m collection --mode=update` — exit 0; `0 failed, 0 error(s) of 119 tests when loading database 'devel'`                                                                                                       |
| Runtime harness command/scenario and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init` — exit 0; `creating or updating database tables`; loaded `collection/views/res_config_settings_views.xml`; `Modules loaded.`                  |
| Rollback boundary                                 | `models/res_company.py`, `models/res_config_settings.py`, `views/res_config_settings_views.xml`, `__manifest__.py` data/version, `models/__init__.py`, `tests/__init__.py`, `tests/test_collection_document_review_flag.py` |

### Phase 2

| Evidence                                          | Result                                                                                                                                                                                                                                                                                                                                                        |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `invoke test -m collection --mode=update` — exit 0; `0 failed, 0 error(s) of 124 tests when loading database 'devel'`. Prior focused GREEN: 2.2 `0 failed / 3 tests`; 2.4 `0 failed / 17 tests`. RED 2.1: `UserError: Cannot validate while attached payment lines are pending review.`; RED 2.3: `4 failed, 0 error(s) of 4 tests` (`UserError not raised`). |
| Runtime harness command/scenario and exact result | N/A — TransactionCase Python gates; no new XML/data in this work unit                                                                                                                                                                                                                                                                                         |
| Rollback boundary                                 | `models/collection_voucher.py` skip, `models/collection_voucher_line.py` RPC refuse, opt-in in `tests/test_collection_{document_review,voucher,acl}.py`, OFF cases in `tests/test_collection_document_review_flag.py`                                                                                                                                         |

### Phase 3

| Evidence                                          | Result                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `invoke test -m collection --mode=update` — exit 0; `0 failed, 0 error(s) of 130 tests when loading database 'devel'`. RED 3.1: `1 failed, 0 error(s) of 4 tests` (`test_load_menus_omits_document_review_when_flag_off`: review menu id unexpectedly found). GREEN 3.2: `0 failed, 0 error(s) of 4 tests` after `-u collection`. GREEN 3.3: `0 failed, 0 error(s) of 2 tests` with no payment-line view edits. |
| Runtime harness command/scenario and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --http-port=8070` — exit 0; `creating or updating database tables`; `Modules loaded.` (new `models/ir_ui_menu.py` loaded). Combined with GREEN 3.2 `-u collection --test-enable`.                                                                                                                                                  |
| Rollback boundary                                 | `models/ir_ui_menu.py`, `models/__init__.py` import, `tests/test_collection_ui.py` load_menus/settings arch cases, `tests/test_collection_document_review_flag.py` payment-line view cases                                                                                                                                                                                                                      |

### Phase 4

| Evidence                                          | Result                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Focused test command and exact result             | Nested-git `git diff HEAD -- views/collection_document_review_views.xml` empty; `git show HEAD:views/collection_document_review_views.xml \| cmp - views/collection_document_review_views.xml` → `HEAD blob identical to working tree`. `rg` `menu.active` / `.active = False` / `active="False"` / `"active":` in `*.{py,xml}`: no matches. `rg company_id` in `models/collection_voucher.py` and `models/collection_voucher_line.py`: no matches. Menu xmlid `menu_collection_document_review` present; no `active` attribute. Phase 1–3 file lists never include the review views file. Full test suite not run (no production edits; confirmation only). |
| Runtime harness command/scenario and exact result | N/A — confirmation only; no runtime boundary and no production edits                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| Rollback boundary                                 | N/A — no files changed in production; no revert required                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |

## Deviations from Design

- Default-off triangulation uses `search()`/`browse()` plus `res.company.new(...)`
  instead of `create()`. Creating a second `res.company` in this database raises
  `null value in column "autopost_bills"` on `res_partner`. `new()` still applies
  `default=False` without that insert.
- Four RPC flag checks were extracted to `@api.private`
  `_ensure_document_review_enabled` during 2.6 so the exact UserError is raised in one
  place. Behavior matches design (raise before queue/lock).
- `_load_menus_blacklist` has **no** `@api.model`. Design guessed `@api.model`; Odoo 19
  core (`base/models/ir_ui_menu.py`) and `hr/models/ir_ui_menu.py` define it without
  that decorator. Implementation follows hr/core. Never set `menu.active`.

## Issues Found

None blocking Phase 4.

## Remaining Tasks

None — Phase 4 / 4.1 complete. Ready for verify.
