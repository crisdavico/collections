# Apply Progress: sheet-scoped-document-review

**Change**: sheet-scoped-document-review **Mode**: Strict TDD **Work unit**: Phase 4 —
Upgrade and verify **Delivery**: stacked-to-main (user-resolved) **Status**: Phase 1–4
complete (1.1–4.3). Task 4.2 accepted as scoped pre-commit of this change; the recursive
collection glob fails on immutable archived OpenSpec files.

## Implementation Progress

Phase 1 assigned tasks remain complete. Phase 2 assigned tasks (2.1–2.4) remain
complete. Phase 3 assigned tasks (3.1–3.4) remain complete. Phase 4.1–4.3 are complete.

### Completed Tasks

- [x] 1.1 RED two sheets; queue A excludes B; cross-sheet mutations UserError
- [x] 1.2 GREEN `get_review_queue(sheet_id)` = that sheet + pending + attached
- [x] 1.3 RED empty/ineligible sheet `[]`; other sheets ignored
- [x] 1.4 GREEN queue domain; no global fallback
- [x] 1.5 RED missing/0/False/bad id → UserError (not `[]`)
- [x] 1.6 GREEN `_require_review_sheet` (`@api.private`): flag first, then int > 0 and
      exists()
- [x] 1.7 RED stale/other-sheet mutation refused
- [x] 1.8 GREEN mutations take `sheet_id` after ids, before vals/degrees;
      `self.sheet_id == sheet`
- [x] 1.9 RED flag OFF refuses four RPCs with or without `sheet_id`
- [x] 1.10 GREEN flag first; existing review/flag call sites pass `sheet_id`
- [x] 1.11 RED ACL: assign sheet; portal AccessError; internals pass `sheet_id`
- [x] 1.12 GREEN ACL call sites; no new groups
- [x] 1.13 RED OWL source asserts `sheet_id` on four `orm.call` args
- [x] 1.14 GREEN OWL reads `params.sheet_id` only; invalid → notify, skip queue
- [x] 2.1 RED `tests/test_collection_sheet.py`: saved+ON →
      `collection.document_review` + `params.sheet_id`; OFF/unsaved/`NewId` →
      `UserError`
- [x] 2.2 GREEN `models/collection_sheet.py`: non-stored helper;
      `action_open_document_review` via `_for_xml_id`
- [x] 2.3 RED `tests/test_collection_ui.py`: header visible iff saved+flag ON; hidden
      OFF/unsaved
- [x] 2.4 GREEN `views/collection_views.xml` sheet form: header `type="object"` + helper
- [x] 3.1 RED UI + flag: menu absent ON/OFF; xmlid gone; `load_menus` omits it; action
      kept; `path` cleared
- [x] 3.2 GREEN `views/collection_document_review_views.xml`: drop menuitem, `<delete>`
      leftover menu, clear `path`
- [x] 3.3 GREEN delete `models/ir_ui_menu.py`; drop import in `models/__init__.py`
- [x] 3.4 GREEN `__manifest__.py` bump `19.0.1.10.0` to `19.0.1.11.0`
- [x] 4.1 compose run `-u collection -d devel` (one-off; not `docker exec` on live `seedian-odoo-1`)
- [x] 4.2 scoped `pre-commit` on this change's files (recursive glob fails on archived OpenSpec; archives must not be reformatted)
- [x] 4.3 full collection suite equivalent of `invoke test -m collection` with `-d devel -u collection`

### Files Changed

Phase 1:

| File                                                       | Action   | What Was Done                                                                                    |
| ---------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------ |
| `models/collection_voucher.py`                             | Modified | Mandatory `sheet_id` on four review RPCs; `_require_review_sheet`; `_ensure_review_sheet_member` |
| `tests/test_collection_document_review.py`                 | Modified | Sheet isolation, invalid/stale mutations, OWL arg asserts; existing call sites pass `sheet_id`   |
| `tests/test_collection_document_review_flag.py`            | Modified | Invalid sheet when ON; OFF with or without `sheet_id`                                            |
| `tests/test_collection_acl.py`                             | Modified | Assign sheet + seller; portal AccessError; internals pass `sheet_id`                             |
| `static/src/document_review/document_review_action.esm.js` | Modified | Parse `params.sheet_id`; pass on queue/approve/reject/rotation; skip queue when invalid          |
| `openspec/changes/sheet-scoped-document-review/tasks.md`   | Modified | Marked 1.1–1.14 `[x]`                                                                            |

Phase 2:

| File                                                     | Action   | What Was Done                                                                                                |
| -------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------ |
| `tests/test_collection_sheet.py`                         | Modified | Object action params, flag OFF UserError, NewId refuse, non-stored helper                                    |
| `models/collection_sheet.py`                             | Modified | Non-stored `document_review_enabled`; `action_open_document_review` via `_for_xml_id`; `_ensure_saved_sheet` |
| `tests/test_collection_ui.py`                            | Modified | Header visible iff saved+flag ON; hidden OFF/unsaved; settings WIP tests left intact                         |
| `views/collection_views.xml`                             | Modified | Sheet form `<header>` object button + invisible helper field                                                 |
| `openspec/changes/sheet-scoped-document-review/tasks.md` | Modified | Marked 2.1–2.4 `[x]`                                                                                         |

Phase 3:

| File                                                     | Action   | What Was Done                                                                                                                                     |
| -------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/test_collection_ui.py`                            | Modified | Menu xmlid gone; leftover `ir.ui.menu` gone; `path` cleared; `load_menus` omits ON and OFF; action xmlid/tag kept. Settings WIP tests left intact |
| `tests/test_collection_document_review_flag.py`          | Modified | `test_document_review_xmlids_kept`: action kept, menu xmlid gone                                                                                  |
| `views/collection_document_review_views.xml`             | Modified | Dropped menuitem; `<delete model="ir.ui.menu" search="[('name', '=', 'Document Review')]"/>`; cleared `path`                                      |
| `models/ir_ui_menu.py`                                   | Deleted  | Dead `_load_menus_blacklist` without the menu                                                                                                     |
| `models/__init__.py`                                     | Modified | Dropped `from . import ir_ui_menu`                                                                                                                |
| `__manifest__.py`                                        | Modified | Version `19.0.1.10.0` → `19.0.1.11.0`                                                                                                             |
| `openspec/changes/sheet-scoped-document-review/tasks.md` | Modified | Marked 3.1–3.4 `[x]`                                                                                                                              |

Phase 4:

| File                                                     | Action   | What Was Done                                                                                          |
| -------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------ |
| `tests/test_collection_document_review.py`               | Modified | Wrapped two E501 docstrings (>88) so scoped ruff passes                                                |
| `tests/test_collection_ui.py`                            | Modified | Wrapped one E501 docstring; ruff-format already split long xpath lines                                 |
| `openspec/changes/sheet-scoped-document-review/tasks.md` | Modified | Marked 4.1 and 4.3 `[x]`; left 4.2 `[ ]`                                                               |

Did **not** implement seller_lookup or settings menus. Did **not** reformat archived
OpenSpec files to green the glob.

## TDD Cycle Evidence

Safety net (Phase 1, before production edits):

```
docker compose run --rm -e DB_FILTER='^devel$' odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionDocumentReview,/collection:TestCollectionDocumentReviewFlag,/collection:TestCollectionAcl
```

Result: `0 failed, 0 error(s) of 54 tests` (stats: 60 tests). Pre-existing failures:
none.

Safety net (Phase 2, before production edits):

```
cd /home/crisd/projects/seedian/seedian
env GID="$(id -g)" UID="$(id -u)" DOODBA_UMASK=27 docker compose run --rm -e "DB_FILTER='^devel$'" odoo odoo --test-enable --stop-after-init --workers=0 -d devel -u collection --test-tags /collection:TestCollectionSheet,/collection:TestCollectionUi
```

First attempt without `-d devel` hit a transient `product` circular import during
registry load. Retry with `-d devel` succeeded.

Result: `0 failed, 0 error(s) of 43 tests` (stats: 47 tests). WIP settings tests
(`test_configuration_settings_menu_and_action`,
`test_load_menus_includes_configuration_settings`) passed. Pre-existing failures: none.

Safety net (Phase 3, before production edits):

```
cd /home/crisd/projects/seedian/seedian
env GID="$(id -g)" UID="$(id -u)" DOODBA_UMASK=27 docker compose run --rm -e "DB_FILTER='^devel$'" odoo odoo --test-enable --stop-after-init --workers=0 -d devel -u collection --test-tags /collection:TestCollectionUi,/collection:TestCollectionDocumentReviewFlag
```

Result: `0 failed, 0 error(s) of 46 tests` (stats: 50 tests). WIP settings tests passed.
Pre-existing failures: none.

RED (Phase 3, after rewriting the five menu/path/xmlid tests, before production):

Result: `5 failed, 0 error(s) of 46 tests`. Failures were exactly:

- `TestCollectionDocumentReviewFlag.test_document_review_xmlids_kept` — menu xmlid still
  present
- `TestCollectionUi.test_document_review_client_action_path_and_name` — `path` still
  `'document-review'`
- `TestCollectionUi.test_document_review_menu_and_client_action` — menu xmlid still
  present
- `TestCollectionUi.test_load_menus_includes_document_review_when_flag_on` — menu xmlid
  still present
- `TestCollectionUi.test_load_menus_omits_document_review_when_flag_off` — menu xmlid
  still present

GREEN (Phase 3, after XML delete/path, `ir_ui_menu.py` deletion, and manifest bump):

Result: `0 failed, 0 error(s) of 46 tests` (stats: 50 tests). Settings WIP tests still
ran and passed.

| Task | Test File                                       | Layer             | Safety Net | RED                                                                              | GREEN                                                                 | TRIANGULATE                                                              | REFACTOR                                       |
| ---- | ----------------------------------------------- | ----------------- | ---------- | -------------------------------------------------------------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------ | ---------------------------------------------- |
| 1.1  | `tests/test_collection_document_review.py`      | Unit              | ✅ 54/54   | ✅ Written (TypeError on `sheet_id`)                                             | ✅ Queue isolation after 1.2                                          | ✅ Queue A and queue B                                                   | ➖ Test helpers only                           |
| 1.2  | `models/collection_voucher.py`                  | Unit              | ✅ 54/54   | ✅ 1.1 queue test                                                                | ✅ `test_queue_is_isolated_to_requested_sheet` passed                 | ✅ Two sheets, opposite queues                                           | ➖ Domain was real, not Fake It                |
| 1.3  | `tests/test_collection_document_review.py`      | Unit              | ✅ 54/54   | ✅ Written (empty/ineligible + other sheet)                                      | ✅ Passed on first run (1.2 domain)                                   | ✅ Empty sheet, ineligible members, other-sheet eligible ignored         | ➖ None needed                                 |
| 1.4  | `models/collection_voucher.py`                  | Unit              | ✅ 54/54   | ✅ 1.3                                                                           | ✅ Sheet domain; no company-wide fallback                             | ✅ Covered by 1.1 + 1.3                                                  | ➖ None needed                                 |
| 1.5  | review + flag tests                             | Unit              | ✅ 54/54   | ✅ Written (`UserError not raised` for None/0/False/bad id)                      | ✅ Queue after 1.6; mutations after 1.8                               | ✅ None, 0, False, missing, unknown id                                   | ➖ None needed                                 |
| 1.6  | `models/collection_voucher.py`                  | Unit              | ✅ 54/54   | ✅ 1.5 queue                                                                     | ✅ `_require_review_sheet` flag first then int>0/exists               | ✅ Bool False vs unknown id vs missing                                   | ✅ Shared UserError path                       |
| 1.7  | `tests/test_collection_document_review.py`      | Unit              | ✅ 54/54   | ✅ Written (cross-sheet TypeError; stale membership)                             | ✅ After 1.8                                                          | ✅ Other-sheet + unassigned stale + same-sheet success                   | ➖ None needed                                 |
| 1.8  | `models/collection_voucher.py`                  | Unit              | ✅ 54/54   | ✅ 1.1/1.7                                                                       | ✅ Mutations take `sheet_id` then membership                          | ✅ Approve/reject/rotation success vs refuse                             | ✅ `_ensure_review_sheet_member` extracted     |
| 1.9  | `tests/test_collection_document_review_flag.py` | Unit              | ✅ 54/54   | ✅ Written (with and without `sheet_id`)                                         | ✅ Passed via flag-first `_require_review_sheet`                      | ✅ Four RPCs × with/without sheet id                                     | ➖ None needed                                 |
| 1.10 | review + flag tests                             | Unit              | ✅ 54/54   | ✅ Existing ON call sites would UserError                                        | ✅ Call sites pass `sheet_id`; neutralize no longer uses global queue | ✅ Existing payload/rotation/approve tests                               | ✅ Default sheet on `_create_attached_voucher` |
| 1.11 | `tests/test_collection_acl.py`                  | Unit              | ✅ 54/54   | ✅ Written (sheet assign + `sheet_id` args)                                      | ✅ After helper/call-site update                                      | ✅ Portal AccessError vs internal approve/reject/rotation                | ➖ No new groups                               |
| 1.12 | `tests/test_collection_acl.py`                  | Unit              | ✅ 54/54   | ✅ 1.11                                                                          | ✅ ACL call sites only; no production ACL/groups                      | ✅ Portal still AccessError with `sheet_id`                              | ➖ None needed                                 |
| 1.13 | `tests/test_collection_document_review.py`      | Unit (source)     | ✅ 54/54   | ✅ Written (compact `orm.call` args)                                             | ✅ After 1.14                                                         | ✅ Four methods + no `active_id` + invalid skip order                    | ✅ Regex allows trailing commas                |
| 1.14 | `document_review_action.esm.js`                 | Unit (source)     | ✅ 54/54   | ✅ 1.13                                                                          | ✅ `params.sheet_id` only; notify + skip queue                        | ✅ Queue/approve/reject/rotation args                                    | ➖ Getter `reviewSheetId`                      |
| 2.1  | `tests/test_collection_sheet.py`                | Unit              | ✅ 43/43   | ✅ Written (`AttributeError` / `KeyError`; 5 errors of 5)                        | ✅ After 2.2                                                          | ✅ Two sheets' `params.sheet_id`; OFF message; NewId                     | ➖ Test creates sheets after flag writes       |
| 2.2  | `models/collection_sheet.py`                    | Unit              | ✅ 43/43   | ✅ 2.1                                                                           | ✅ `0 failed, 0 error(s) of 21 tests` on TestCollectionSheet          | ✅ ON vs OFF helper; two saved ids                                       | ✅ `_ensure_saved_sheet` `@api.private`        |
| 2.3  | `tests/test_collection_ui.py`                   | Unit (arch)       | ✅ 43/43   | ✅ Written (`0 != 1` header button; 2 failed of 2)                               | ✅ After 2.4                                                          | ✅ Saved+ON helper True; OFF helper False; unsaved `not id`              | ➖ None needed                                 |
| 2.4  | `views/collection_views.xml`                    | Unit (arch)       | ✅ 43/43   | ✅ 2.3                                                                           | ✅ `0 failed, 0 error(s) of 50 tests` Sheet+Ui                        | ✅ Existing `test_collection_sheets_form_without_statusbar` still passes | ➖ None needed                                 |
| 3.1  | `tests/test_collection_ui.py` + flag xmlid      | Unit              | ✅ 46/46   | ✅ Written (`5 failed` of 46; xmlid still present; path still `document-review`) | ✅ After 3.2–3.4                                                      | ✅ Flag OFF + flag ON omit; action xmlid/tag kept                        | ➖ None needed                                 |
| 3.2  | `views/collection_document_review_views.xml`    | Unit (XML + `-u`) | ✅ 46/46   | ✅ 3.1                                                                           | ✅ Menu xmlid gone; leftover row deleted; `path` False                | ✅ ON and OFF `load_menus`; leftover search empty                        | ➖ None needed                                 |
| 3.3  | `models/ir_ui_menu.py`                          | Unit              | ✅ 46/46   | ✅ 3.1 (blacklist dead without menu)                                             | ✅ File deleted; `__init__` import dropped; GREEN still 0 failed      | ➖ Structural: one possible outcome                                      | ➖ None needed                                 |
| 3.4  | `__manifest__.py`                               | Unit              | ✅ 46/46   | ➖ Version bump has no dedicated failing test                                    | ✅ `19.0.1.11.0`; GREEN still 0 failed                                | ➖ Structural: one possible output                                       | ➖ None needed                                 |
| 4.1  | N/A — module upgrade                            | Runtime harness   | N/A        | ➖ Verification, not new behavior                                                | ✅ compose `-u collection -d devel` exit 0; collection loaded 0.74s  | ➖ Upgrade only                                                          | ➖ None needed                                 |
| 4.2  | this-change scoped pre-commit                   | Lint              | N/A        | ➖ Globstar E501 then archive prettier                                           | ⚠️ assigned glob fail (archives); scoped this-change files exit 0    | ➖ E501 wraps only                                                       | ✅ Docstring wraps                             |
| 4.3  | full `/collection` suite                        | Integration       | N/A        | ➖ Verification, not new behavior                                                | ✅ `0 failed, 0 error(s) of 194 tests` (stats: 218)                  | ➖ Full suite including seller_lookup WIP (passed)                       | ➖ None needed                                 |

### Test Summary

Phase 1:

- **Total tests written**: 10 new methods (isolation, empty sheet, invalid sheet
  queue/mutations, stale membership, same-sheet success, OWL args, flag OFF with/without
  sheet, flag ON invalid sheet)
- **Total tests passing (focused Phase 1 command)**: 0 failed, 0 error(s) of 64 tests
  (stats: 70 tests)
- **Layers used**: Unit / TransactionCase (64), Integration (0), E2E (0)
- **Approval tests** (refactoring): None — no refactoring-only tasks
- **Pure functions created**: 0 (ORM helpers `_require_review_sheet` /
  `_ensure_review_sheet_member`)

Phase 2:

- **Total tests written**: 7 new methods (client action + sheet_id, two-sheet params,
  flag OFF, NewId, non-stored helper, header visible saved+ON, header hidden
  OFF/unsaved)
- **Total tests passing (focused Phase 2 command)**: 0 failed, 0 error(s) of 50 tests
  (stats: 54 tests)
- **Layers used**: Unit / TransactionCase (50), Integration (0), E2E (0)
- **Approval tests** (refactoring): None — existing sheet form invariants kept via
  `test_collection_sheets_form_without_statusbar`
- **Pure functions created**: 0 (ORM helper `_ensure_saved_sheet`)

Phase 3:

- **Total tests rewritten**: 5 methods (`test_document_review_menu_and_client_action`,
  `test_document_review_client_action_path_and_name`,
  `test_load_menus_omits_document_review_when_flag_off`,
  `test_load_menus_includes_document_review_when_flag_on`,
  `test_document_review_xmlids_kept`)
- **Total tests passing (focused Phase 3 command)**: 0 failed, 0 error(s) of 46 tests
  (stats: 50 tests)
- **Layers used**: Unit / TransactionCase (46), Integration (0), E2E (0)
- **Approval tests** (refactoring): None — settings WIP tests left asserting current
  Settings menu behavior
- **Pure functions created**: 0

Phase 4:

- **Total tests written**: 0 (verification only; three E501 docstring wraps)
- **Total tests passing (full module suite)**: 0 failed, 0 error(s) of 194 tests
  (stats: `collection: 218 tests`)
- **Layers used**: Unit / TransactionCase (194 reported), Integration (module `-u` on
  `devel`), E2E (0)
- **Approval tests** (refactoring): None — Phase 4 did not change production behavior
- **Pure functions created**: 0
- **Lint**: this-change scoped pre-commit exit 0 after E501 wraps; globstar glob exit 1
  on archived OpenSpec prettier/YAML/trailing-whitespace

## Work Unit Evidence

Phase 1:

| Evidence             | Value                                                                                                                                                                                                                                                                                                                                               |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command | `cd /home/crisd/projects/seedian/seedian && env GID="$(id -g)" UID="$(id -u)" DOODBA_UMASK=27 docker compose run --rm -e "DB_FILTER='^devel$'" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionDocumentReview,/collection:TestCollectionDocumentReviewFlag,/collection:TestCollectionAcl` |
| Focused test result  | `0 failed, 0 error(s) of 64 tests when loading database 'devel'` (stats: `collection: 70 tests`)                                                                                                                                                                                                                                                    |
| Runtime harness      | N/A — Phase 1 is TransactionCase + OWL source asserts; no XML upgrade boundary                                                                                                                                                                                                                                                                      |
| Rollback boundary    | `models/collection_voucher.py` review RPCs; `static/src/document_review/document_review_action.esm.js`; review/flag/ACL tests. Does not include sheet header action, menu delete, or manifest bump                                                                                                                                                  |

Phase 2:

| Evidence             | Value                                                                                                                                                                                                                                                                                                                                                             |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command | `cd /home/crisd/projects/seedian/seedian && env GID="$(id -g)" UID="$(id -u)" DOODBA_UMASK=27 docker compose run --rm -e "DB_FILTER='^devel$'" odoo odoo --test-enable --stop-after-init --workers=0 -d devel -u collection --test-tags /collection:TestCollectionSheet,/collection:TestCollectionUi`                                                             |
| Focused test result  | `0 failed, 0 error(s) of 50 tests when loading database 'devel'` (stats: `collection: 54 tests`)                                                                                                                                                                                                                                                                  |
| Runtime harness      | Same command includes `-u collection`, so the sheet form header XML is upgraded into `devel` before TestCollectionUi arch asserts. Result: 0 failed, 0 error(s) of 50 tests.                                                                                                                                                                                      |
| Rollback boundary    | `models/collection_sheet.py` helper + `action_open_document_review`; `views/collection_views.xml` sheet form header only; `tests/test_collection_sheet.py` and header tests in `tests/test_collection_ui.py`. Does not include voucher RPCs/OWL, menu delete, `ir_ui_menu.py`, or manifest bump. Settings WIP tests in `test_collection_ui.py` were not reverted. |

Phase 3:

| Evidence             | Value                                                                                                                                                                                                                                                                                                                                                                             |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command | `cd /home/crisd/projects/seedian/seedian && env GID="$(id -g)" UID="$(id -u)" DOODBA_UMASK=27 docker compose run --rm -e "DB_FILTER='^devel$'" odoo odoo --test-enable --stop-after-init --workers=0 -d devel -u collection --test-tags /collection:TestCollectionUi,/collection:TestCollectionDocumentReviewFlag`                                                                |
| Focused test result  | GREEN: `0 failed, 0 error(s) of 46 tests when loading database 'devel'` (stats: `collection: 50 tests`). RED before production: `5 failed, 0 error(s) of 46 tests`. Safety net: `0 failed, 0 error(s) of 46 tests`.                                                                                                                                                               |
| Runtime harness      | Same command includes `-u collection`, so XML `<delete>` of leftover `ir.ui.menu` and cleared `path` are applied into `devel` before the UI/flag asserts. Result: 0 failed, 0 error(s) of 46 tests. Did not run full `invoke install` / pre-commit / full module suite (Phase 4).                                                                                                 |
| Rollback boundary    | `views/collection_document_review_views.xml` (menuitem + `<delete>` + `path`); `models/ir_ui_menu.py` (restore blacklist); `models/__init__.py` import; `__manifest__.py` version; menu/path/xmlid tests in `tests/test_collection_ui.py` and `tests/test_collection_document_review_flag.py`. Does not include voucher RPCs/OWL, sheet header, Settings views, or seller_lookup. |

Phase 4:

| Evidence             | Value                                                                                                                                                                                                                                                                                                                                               |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command | `cd /home/crisd/projects/seedian/seedian && env GID="$(id -g)" UID="$(id -u)" DOODBA_UMASK=27 docker compose run --rm -e "DB_FILTER='^devel$'" odoo odoo --test-enable --stop-after-init --workers=0 -d devel -u collection --test-tags /collection`                                                                                                 |
| Focused test result  | Exit 0. `0 failed, 0 error(s) of 194 tests when loading database 'devel'` (stats: `collection: 218 tests 4.72s 6716 queries`). Includes `TestCollectionMcpSellerLookup` (11 methods) — WIP loaded and passed; import was not deleted.                                                                                                              |
| Runtime harness      | `cd /home/crisd/projects/seedian/seedian && env GID="$(id -g)" UID="$(id -u)" DOODBA_UMASK=27 docker compose run --rm -e "DB_FILTER='^devel$'" odoo odoo --stop-after-init --workers=0 -d devel -u collection`. Exit 0. Loaded `collection_views.xml`, `collection_document_review_views.xml`. No ERROR/CRITICAL. Did not `docker exec` live `seedian-odoo-1`. |
| Rollback boundary    | Phase 4 lint-only: docstring wraps in `tests/test_collection_document_review.py` and `tests/test_collection_ui.py`. Does not revert Phases 1–3. Does not include seller_lookup, settings menus, or archived OpenSpec files.                                                                                                                       |

## Deviations from Design

None — implementation matches design.

Phase 1:

- `get_review_queue(sheet_id)` with default `None` so missing args raise `UserError` via
  `_require_review_sheet`, not TypeError.
- Mutations: `sheet_id` after ids, before `vals`/`degrees`.
- Flag check is first inside `_require_review_sheet` (existing
  `"Document Review is not enabled."`).
- OWL reads `props.action.params.sheet_id` only; no `context.active_id`.
- `@api.private` on new helpers. No `_sql_constraints`. No new groups.
- Tests that assign `sheet_id` also set `seller_id` to the sheet seller.
- `_neutralize_preexisting_queue` searches pending+attached on the test sheet and does
  not call global `get_review_queue()`.

Phase 2:

- Object action uses
  `ir.actions.actions._for_xml_id("collection.action_collection_document_review")` and
  sets `params.sheet_id`.
- Flag refuse reuses voucher `_ensure_document_review_enabled()` via
  `self.env["collection.voucher"]` (existing `"Document Review is not enabled."`).
- Unsaved/`NewId` refuse is a separate UserError after the flag check.
- Non-stored Boolean `document_review_enabled` computed from
  `self.env.company._document_review_enabled()`; no DDL.
- Form header `type="object"` `name="action_open_document_review"` with
  `invisible="not id or not document_review_enabled"` plus invisible helper field.
- `@api.private` on `_ensure_saved_sheet`. No `_sql_constraints`. Sheet form still has
  no statusbar.

Phase 3:

- Client action xmlid `collection.action_collection_document_review` and tag
  `collection.document_review` kept.
- `path` cleared via empty `<field name="path" />` (False/empty; no
  `/odoo/document-review` shortcut).
- Menuitem `collection.menu_collection_document_review` removed.
- Leftover `ir.ui.menu` dropped with
  `<delete model="ir.ui.menu" search="[('name', '=', 'Document Review')]"/>` in
  `collection_document_review_views.xml` (Payment Lines pattern).
- Deleted `models/ir_ui_menu.py` and its `__init__` import (blacklist dead without the
  menu).
- Manifest bumped `19.0.1.10.0` → `19.0.1.11.0`.
- Settings WIP tests (`test_configuration_settings_menu_and_action`,
  `test_load_menus_includes_configuration_settings`) not reverted.
  `views/res_config_settings_views.xml` not edited.

Phase 4:

- Verification only. No new production behavior. Three E501 docstring wraps in tests
  from this change. Used compose run `-d devel -u collection` instead of `invoke
  install` / live `docker exec --stop-after-init` on `seedian-odoo-1`.
- 4.3 used `-u` (not invoke's default `-i`) plus `-d devel` as required for one-off
  odoo commands.

## Issues Found

Phase 4.2 contamination: `shopt -s globstar` +
`pre-commit run --files odoo/custom/src/private/collection/**` exit 1.

- This change (fixed): ruff E501 in `test_collection_document_review.py` (2 docstrings)
  and `test_collection_ui.py` (1 docstring + xpath already wrapped by ruff-format).
- Pre-existing / archive (not fixed): prettier failed on archived OpenSpec markdown and
  `openspec/changes/archive/2026-08-17-collection-sheets/state.yaml` (`phase` key
  repeated). Trailing-whitespace tried to rewrite nine archive files. Those are not
  this change; archives were not reformatted to force a green glob.
- Without globstar, the same glob exited 0 but skipped eslint/xml (did not expand nested
  files). That pass is incomplete.
- Scoped this-change files: exit 0 after E501 wraps. Optional pylint
  `manifest-required-author` warning only; hook still Passed.
- Listed WIP (`seller_lookup`, settings-menu tests) did **not** fail pre-commit or the
  full test suite.

Phase 2 note retained: transient safety-net registry load without `-d devel` failed on
`product` circular import; the same command with `-d devel` passed. Not a collection
regression.

## Remaining Tasks

- [ ] 4.2 Seedian root: `pre-commit run --files odoo/custom/src/private/collection/**`
      (globstar blocked by archived OpenSpec prettier/YAML; this-change scoped files
      already pass)

## Workload / PR Boundary

- Mode: stacked PR slice (`stacked-to-main`)
- Current work unit: Phase 4 — Upgrade and verify
- Boundary: module upgrade on `devel`, scoped lint of this change's files, full
  `/collection` suite. Does not green the recursive glob by editing archives, seller
  lookup, or settings-menu WIP.
- Estimated review budget impact: Phase 4 is verification plus three docstring wraps;
  PR still should not target `main` while Phase 1–3 slices are unmerged.
