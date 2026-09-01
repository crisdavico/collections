# Apply Progress: add-pluggable-collection-connectors

**Change**: add-pluggable-collection-connectors **Mode**: Strict TDD **Work unit**: Unit
2 sqlite + apply.roots (tasks 3.1–3.16); Phase 1 (1.1–1.4) and Phase 2 (2.1–2.15)
retained **Attempt token**:
`sha256:7cc8ef03a16078034607667cdd3e432fbe69f3edea34545c16095d4c0a37e1b9` **Acquire**:
`state: proceed` (same token, `--request-id acquire-phase-3-sqlite-01`, work-unit
`phase-3-unit-2-sqlite`) **Prior attempt (retained)**:
`sha256:dded688923d8773bb9989d93dcb8f95f0ee1a203e74f7fd99788d073d9125998` (Phase 2 MCP)

## Completed Tasks

### Phase 1 (retained)

- [x] 1.1 RED Persist connector (`tests/test_collection_company_settings.py`): A saves;
      B unchanged; keep XMLID (`tests/test_collection_ui.py`).
- [x] 1.2 GREEN `models/collection_connector.py`, `res_company.py`,
      `res_config_settings.py`, `views/res_config_settings_views.xml`,
      `models/__init__.py`.
- [x] 1.3 RED ACL (`tests/test_collection_acl.py`): user read, system write, company
      `ir.rule`, portal denied.
- [x] 1.4 GREEN `security/collection_security.xml`, `ir.model.access.csv`,
      `views/collection_connector_views.xml`.

### Phase 2

- [x] 2.1 RED dispatch miss (`tests/test_collection_connector.py`): unknown op →
      `UserError`.
- [x] 2.2 GREEN `_dispatch` allowlist (`models/collection_connector.py`).
- [x] 2.3 RED uniqueness: reject reuse E, U, other-company.
- [x] 2.4 GREEN `models/collection_connector_seller_binding.py` UNIQUE + stored
      `company_id`.
- [x] 2.5 RED missing connector (`tests/test_collection_mcp_list_sellers.py`) →
      `UserError`, no leak.
- [x] 2.6 RED inactive connector → `UserError`, no leak.
- [x] 2.7 RED misconfigured connector → `UserError`, no leak.
- [x] 2.8 RED Active company: list from C; no caller `company_id`.
- [x] 2.9 RED Isolation: A MUST NOT list B.
- [x] 2.10 RED Auth: method-discovered; no sudo; no `muk_mcp.tool`; portal denied.
- [x] 2.11 RED List shape: bound/unbound/inactive-omitted + source.
- [x] 2.12 RED No collect: listed seller fails `_assert_new_work`.
- [x] 2.13 GREEN `tools/collection_connector.py` + `tools/__init__.py`.
- [x] 2.14 No-regression: `tests/test_collection_mcp_seller_lookup.py`,
      `tests/test_collection_mcp_tool.py`.
- [x] 2.15 Manifest `19.0.1.18.0`; `tests/__init__.py`; upgrade collection; scoped
      pre-commit; `AGENTS.md` + `readme/`. Verify `--mode=update`.

### Phase 3

- [x] 3.1 FIRST: `openspec/config.yaml` apply.roots += sqlite addon + parent private.
- [x] 3.2 RED `requirements.txt` → `UserError`, not executed, no leak.
- [x] 3.3 RED `CMakeLists.txt` → same.
- [x] 3.4 RED executable Markdown/MDX → same.
- [x] 3.5 RED `README.sh` → same.
- [x] 3.6 RED relative path → `UserError`, no leak.
- [x] 3.7 RED `path?mode=rw` → `UserError`, no leak.
- [x] 3.8 GREEN reject non-absolute / `?` `#` NUL before `sqlite3.connect`.
- [x] 3.9 RED missing file → `UserError`, no path/SQL.
- [x] 3.10 RED unreadable file → `UserError`, no path/SQL.
- [x] 3.11 RED invalid schema → `UserError`, no path/SQL.
- [x] 3.12 GREEN `_sqlite_*` `mode=ro` after checks; `UserError`.
- [x] 3.13 RED Sqlite success: list + connection-test; file not written.
- [x] 3.14 GREEN `selection_add`, `sqlite_path`, views, manifest
      `depends: ['collection']`.
- [x] 3.15 RED Rollback: vouchers/sheets/`get_seller_id`/`create_collection_vouchers`
      unchanged.
- [x] 3.16 GREEN cascade + company M2O `set null`. sqlite readme. Upgrade sqlite; scoped
      pre-commit. Verify sqlite + collection MCP.

## Files Changed

### Phase 1 (retained)

| File                                           | Action   | What Was Done                                                                                  |
| ---------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------- |
| `models/collection_connector.py`               | Created  | Company-scoped `collection.connector` (`name`, `company_id`, `active`, empty `type` Selection) |
| `models/__init__.py`                           | Modified | Import `collection_connector`                                                                  |
| `models/res_company.py`                        | Modified | `collection_connector_id` M2O (`ondelete='set null'`, `check_company`, company domain)         |
| `models/res_config_settings.py`                | Modified | Related writable `collection_connector_id`                                                     |
| `views/res_config_settings_views.xml`          | Modified | Collection Settings selector; XMLID `action_collection_config_settings` unchanged              |
| `views/collection_connector_views.xml`         | Created  | `<list>`/form/search, action, `group_system` menu                                              |
| `security/collection_security.xml`             | Modified | Global company `ir.rule` on `collection.connector`                                             |
| `security/ir.model.access.csv`                 | Modified | `group_user` read; `group_system` write                                                        |
| `__manifest__.py`                              | Modified | Added connector views to `data` (version left `19.0.1.17.0` in Phase 1)                        |
| `tests/test_collection_company_settings.py`    | Modified | Persist A / isolate B / related writable                                                       |
| `tests/test_collection_acl.py`                 | Modified | User read, system write, company rule, portal deny                                             |
| `tests/test_collection_ui.py`                  | Modified | `collection_connector_id` in Settings arch; connector list/menu XMLIDs                         |
| `README.rst` / `static/description/index.html` | Modified | oca-gen-addon-readme source digest only                                                        |

### Phase 2

| File                                            | Action   | What Was Done                                                                                                                |
| ----------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `models/collection_connector.py`                | Modified | `_dispatch` allowlist; `list_sellers` / `test_connection`; format list; One2many bindings                                    |
| `models/collection_connector_seller_binding.py` | Created  | Related-stored `company_id`; UNIQUE `(connector_id, external_seller_id)` and `(connector_id, user_id)`; reject other-company |
| `models/__init__.py`                            | Modified | Import seller binding                                                                                                        |
| `tools/collection_connector.py`                 | Created  | Method-discovered `list_collection_sellers` (no args, no sudo)                                                               |
| `tools/__init__.py`                             | Modified | Import connector tool                                                                                                        |
| `security/collection_security.xml`              | Modified | Company `ir.rule` on seller binding                                                                                          |
| `security/ir.model.access.csv`                  | Modified | Binding: `group_user` read; `group_system` write                                                                             |
| `tests/test_collection_connector.py`            | Created  | Dispatch miss + uniqueness                                                                                                   |
| `tests/test_collection_mcp_list_sellers.py`     | Created  | Separate fail-closed 2.5/2.6/2.7; isolation; shape; no-collect; auth                                                         |
| `tests/common_connector.py`                     | Created  | Test-only `selection_add` `test` type + `_test_list_sellers` / `_test_test_connection`                                       |
| `tests/__init__.py`                             | Modified | Import Phase 2 tests                                                                                                         |
| `tests/test_collection_company_migration.py`    | Modified | Manifest version assert `19.0.1.18.0`                                                                                        |
| `__manifest__.py`                               | Modified | Version `19.0.1.18.0`                                                                                                        |
| `AGENTS.md`                                     | Modified | Connector models, `list_collection_sellers` MCP, version                                                                     |
| `readme/DESCRIPTION.md`                         | Modified | Connector + list MCP                                                                                                         |
| `README.rst` / `static/description/index.html`  | Modified | oca-gen-addon-readme digest                                                                                                  |

Not edited: nebula-agent, `tools/seller_lookup.py`.

### Phase 3 (Unit 2 — parent Seedian git unless noted)

| File                                                                          | Action   | What Was Done                                                                                   |
| ----------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------- |
| `openspec/config.yaml` (collection git)                                       | Modified | `apply.roots` += parent private + `collection_connector_sqlite`; guideline for sibling addon    |
| `../collection_connector_sqlite/__manifest__.py`                              | Created  | `depends: ['collection']`; views data; AGPL-3                                                   |
| `../collection_connector_sqlite/__init__.py`                                  | Created  | Import models                                                                                   |
| `../collection_connector_sqlite/models/__init__.py`                           | Created  | Import connector inherit                                                                        |
| `../collection_connector_sqlite/models/collection_connector.py`               | Created  | `selection_add` sqlite cascade; `sqlite_path`; `sqlite_path_is_rejected`; `_sqlite_*` `mode=ro` |
| `../collection_connector_sqlite/views/collection_connector_views.xml`         | Created  | Form inherit: `sqlite_path` + Test Connection                                                   |
| `../collection_connector_sqlite/tests/__init__.py`                            | Created  | Import sqlite tests                                                                             |
| `../collection_connector_sqlite/tests/test_sqlite_connector.py`               | Created  | Threat-matrix, schema, success, views, rollback, set-null                                       |
| `../collection_connector_sqlite/readme/DESCRIPTION.md`                        | Created  | Read-only sqlite seller source                                                                  |
| `../collection_connector_sqlite/README.rst` / `static/description/index.html` | Created  | oca-gen-addon-readme digest                                                                     |

## TDD Cycle Evidence

### Phase 1 (retained)

| Task | Test File                                                                  | Layer                         | Safety Net                                                                                                           | RED                                                                                                                                                                                                        | GREEN                                                              | TRIANGULATE                                                                                     | REFACTOR                                                               |
| ---- | -------------------------------------------------------------------------- | ----------------------------- | -------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| 1.1  | `tests/test_collection_company_settings.py`, `tests/test_collection_ui.py` | Integration (TransactionCase) | ✅ 53 tests, 0 failed (`TestCollectionCompanySettings` + `TestCollectionUi`)                                         | ✅ Written — `KeyError: 'collection.connector'` / `'collection_connector_id'`; Settings arch `0 != 1` for `collection_connector_id`. XMLID keep test stayed green. Result: 2 failed, 3 error(s) of 6 tests | ✅ Passed with 1.2 (0 failed, 0 error(s) of 6)                     | ✅ 3 persist cases (related writable, A saves, B unchanged) + 2 Settings arch cases             | ✅ Company/settings M2O domains                                        |
| 1.2  | same                                                                       | Integration                   | N/A (new model) + 1.1 baseline                                                                                       | Covered by 1.1 RED                                                                                                                                                                                         | ✅ Persist + Settings tests green                                  | ✅ Covered by 1.1 cases                                                                         | ✅ Dropped redundant `string="Type"` (pylint W8113); tests still green |
| 1.3  | `tests/test_collection_acl.py`, `tests/test_collection_ui.py`              | Integration                   | Existing ACL tests green in proving suite (366/366). Pre-edit ACL-only class run was not repeated after 1.1 baseline | ✅ Written — 3 failures, 4 errors of 7 tests (missing ACL rows, AccessError on internal read/system write, missing `ir.rule`, missing view XMLIDs)                                                         | ✅ Passed with 1.4                                                 | ✅ User read+write-deny, system CRUD, portal deny, A visible / B hidden, list tag + system menu | ➖ None needed beyond 1.2 domain/pylint                                |
| 1.4  | same                                                                       | Integration                   | N/A (security/views GREEN for 1.3 RED)                                                                               | Covered by 1.3 RED                                                                                                                                                                                         | ✅ 0 failed, 0 error(s) of 13 focused tests; proving suite 366/366 | ✅ Covered by 1.3 cases                                                                         | ➖ Structural XML; digest regen from oca-gen-addon-readme              |

### Phase 2

| Task | Test File                                                                         | Layer       | Safety Net                                    | RED                                                                            | GREEN                                                                                                | TRIANGULATE                                                            | REFACTOR                                                                              |
| ---- | --------------------------------------------------------------------------------- | ----------- | --------------------------------------------- | ------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| 2.1  | `tests/test_collection_connector.py`                                              | Integration | N/A (new tests; connector model from Phase 1) | ✅ Written — `AttributeError: no attribute '_dispatch'` (2 errors of 2)        | ✅ Passed with 2.2                                                                                   | ✅ Second unknown op `__class__`                                       | ➖ Dispatch kept allowlist-only                                                       |
| 2.2  | same                                                                              | Integration | 2.1 RED baseline                              | Covered by 2.1 RED                                                             | ✅ 0 failed, 0 error(s) of 3 dispatch tests                                                          | ✅ Empty type + allowed `list_sellers`/`test_connection` → `UserError` | ➖ None needed                                                                        |
| 2.3  | same                                                                              | Integration | Dispatch 3/3 green                            | ✅ Written — `KeyError: 'collection.connector.seller.binding'` (3 errors of 3) | ✅ Passed with 2.4                                                                                   | ✅ Reuse E, reuse U, other-company; distinct E+U succeeds              | ✅ Autopost company helper; `assertRaises(UserError)` (Odoo rejects exception tuples) |
| 2.4  | same + security                                                                   | Integration | N/A (new model)                               | Covered by 2.3 RED                                                             | ✅ 0 failed, 0 error(s) of 6 `TestCollectionConnector`                                               | ✅ Covered by 2.3 cases                                                | ➖ Related-stored `company_id` + `models.Constraint` as designed                      |
| 2.5  | `tests/test_collection_mcp_list_sellers.py`                                       | Integration | N/A (new)                                     | ✅ Separate missing-connector test; tool missing then fail-closed              | ✅ Passed with 2.13                                                                                  | ➖ Pair is 2.6/2.7 (must stay separate)                                | ➖ Fail-closed requires discovered tool first                                         |
| 2.6  | same                                                                              | Integration | N/A (new)                                     | ✅ Separate inactive-connector test                                            | ✅ Passed with 2.13                                                                                  | ➖ Separate from 2.5/2.7                                               | ➖ `active_test=False` browse                                                         |
| 2.7  | same                                                                              | Integration | N/A (new)                                     | ✅ Separate empty-type misconfigured test                                      | ✅ Passed with 2.13                                                                                  | ➖ Separate from 2.5/2.6                                               | ➖ None needed                                                                        |
| 2.8  | same                                                                              | Integration | N/A (new)                                     | ✅ Tool not found / method missing                                             | ✅ List from C; no `company_id` arg                                                                  | ✅ Non-empty sellers + source ids                                      | ➖ Test-only `selection_add`                                                          |
| 2.9  | same                                                                              | Integration | N/A (new)                                     | ✅ Tool not found                                                              | ✅ A's `source.connector_id` ≠ B                                                                     | ✅ Distinct companies/connectors                                       | ➖ None needed                                                                        |
| 2.10 | same                                                                              | Integration | N/A (new)                                     | ✅ Tool not in registry / file missing                                         | ✅ `kind=method`, no DB row, no sudo, portal `AccessError`                                           | ✅ Portal + public                                                     | ➖ Matches `get_seller_id` tests                                                      |
| 2.11 | same                                                                              | Integration | N/A (new)                                     | ✅ Tool not found                                                              | ✅ Bound int / unbound null / inactive omitted                                                       | ✅ Source metadata                                                     | ➖ `_seller_row_is_active` helper                                                     |
| 2.12 | same                                                                              | Integration | N/A (new)                                     | ✅ Tool not found                                                              | ✅ Listed bound seller fails `_assert_new_work`                                                      | ✅ Empty enabled list vs listed id                                     | ➖ None needed                                                                        |
| 2.13 | `tools/collection_connector.py`                                                   | Integration | MCP RED suite                                 | Covered by 2.5–2.12 RED                                                        | ✅ 0 failed, 0 error(s) of 15 focused (6 connector + 9 MCP list)                                     | ✅ Covered by 2.5–2.12                                                 | ➖ Format on `list_sellers` after dispatch                                            |
| 2.14 | `tests/test_collection_mcp_seller_lookup.py`, `tests/test_collection_mcp_tool.py` | Integration | Approval: existing MCP                        | ➖ No-regression                                                               | ✅ 0 failed, 0 error(s) of 45                                                                        | ➖ Existing suite                                                      | ➖ None — `seller_lookup.py` untouched                                                |
| 2.15 | manifest / AGENTS / readme / `__init__`                                           | Integration | 366 prior + Phase 2                           | ➖ Structural                                                                  | ✅ `invoke test -m collection --mode=update` → 0 failed, 0 error(s) of 381; scoped pre-commit passed | ➖ Manifest version test updated to `19.0.1.18.0`                      | ➖ README digest via oca-gen-addon-readme                                             |

### Phase 3

| Task | Test File                        | Layer              | Safety Net                                                  | RED                                                               | GREEN                                                                               | TRIANGULATE                                  | REFACTOR                                                   |
| ---- | -------------------------------- | ------------------ | ----------------------------------------------------------- | ----------------------------------------------------------------- | ----------------------------------------------------------------------------------- | -------------------------------------------- | ---------------------------------------------------------- |
| 3.1  | `openspec/config.yaml`           | Structural         | N/A                                                         | ➖ Config                                                         | ✅ apply.roots include sqlite + parent private                                      | ➖ Single                                    | ➖ None                                                    |
| 3.2  | `tests/test_sqlite_connector.py` | Integration        | N/A (new addon)                                             | ✅ Written first — 6 errors of 6 (`Invalid field sqlite_path`)    | ✅ UserError, sentinel not written, no path/SQL                                     | ✅ list + test_connection                    | ➖ Generic UserError                                       |
| 3.3  | same                             | Integration        | N/A                                                         | ✅ Separate CMakeLists.txt method                                 | ✅ Same                                                                             | ✅ list + test_connection                    | ➖ None                                                    |
| 3.4  | same                             | Integration        | N/A                                                         | ✅ Separate executable Markdown/MDX method                        | ✅ Same                                                                             | ✅ `.md` and `.mdx`                          | ➖ None                                                    |
| 3.5  | same                             | Integration        | N/A                                                         | ✅ Separate README.sh method                                      | ✅ Same                                                                             | ✅ list + test_connection                    | ➖ None                                                    |
| 3.6  | same                             | Integration        | N/A                                                         | ✅ Relative path; `sqlite3.connect` not called                    | ✅ Passed with 3.8                                                                  | ✅ `sellers.db` and `./sellers.db`           | ✅ Evaluate `_sqlite_safe_path` before method lookup       |
| 3.7  | same                             | Integration        | N/A                                                         | ✅ `path?mode=rw`; connect not called                             | ✅ Passed with 3.8                                                                  | ✅ URI query rejected                        | ➖ `%` URI after checks (`# noqa: UP031`)                  |
| 3.8  | `models/collection_connector.py` | Unit + Integration | 3.2–3.7 RED 6/6 errors                                      | Covered by 3.6/3.7 + hash/NUL                                     | ✅ 4 path tests green before connect                                                | ✅ `#` fragment + NUL pure function          | ✅ Split nested fetch lookup so path check runs first      |
| 3.9  | same tests                       | Integration        | After 3.8: 7 errors of 11 (`_sqlite_fetch_sellers` missing) | ✅ Separate missing-file method                                   | ✅ Passed with 3.12                                                                 | ✅ list + test_connection                    | ➖ isfile check before connect                             |
| 3.10 | same                             | Integration        | same RED gate                                               | ✅ Separate unreadable method                                     | ✅ Passed with 3.12                                                                 | ✅ list + test_connection                    | ✅ `_()` on model method (module-level `_()` logged ERROR) |
| 3.11 | same                             | Integration        | same RED gate                                               | ✅ Separate invalid-schema method                                 | ✅ Passed with 3.12                                                                 | ✅ list + test_connection                    | ➖ PRAGMA table_info required columns                      |
| 3.12 | `models/collection_connector.py` | Integration        | Threat-matrix RED written before `sqlite3.connect`          | Covered by 3.2–3.5, 3.9–3.11                                      | ✅ `file:%s?mode=ro` `uri=True`                                                     | ✅ missing / unreadable / invalid vs success | ➖ Private `_sqlite_*`                                     |
| 3.13 | same tests                       | Integration        | N/A                                                         | ✅ Success list + bytes unchanged                                 | ✅ Active listed, inactive omitted, file bytes identical                            | ✅ two active + one inactive                 | ➖ Parent `_format_seller_list`                            |
| 3.14 | same                             | Integration        | N/A                                                         | ✅ selection/view/manifest asserts                                | ✅ `ondelete={'sqlite':'cascade'}`; form XMLID; `depends` collection                | ✅ path field + Test Connection button       | ➖ Odoo 19 `invisible=`                                    |
| 3.15 | same                             | Integration        | Collection MCP 54/54 later                                  | ✅ Rollback method (missing `customer_identification` then fixed) | ✅ Voucher/sheet/`get_seller_id`/create MCP                                         | ✅ Unique phone + new document_id            | ➖ Did not edit `seller_lookup.py`                         |
| 3.16 | same + readme                    | Integration        | sqlite 16/16                                                | ✅ Unlink set-null + ondelete asserts                             | ✅ README via oca-gen-addon-readme; scoped pre-commit passed (optional C8101 Eynes) | ✅ company field `ondelete='set null'`       | ➖ Generated README digest                                 |

### Test Summary

- **Total tests written (Phase 3)**: 16 methods on `TestSqliteConnector` (6
  threat-matrix, 2 path extras, 3 invalid, 1 success, 2 structural, 1 rollback, 1
  set-null)
- **Total tests passing**: sqlite 16/16; collection MCP no-regression 54/54
  (`TestCollectionMcpSellerLookup` + `TestCollectionMcpTool` +
  `TestCollectionMcpListSellers`)
- **Layers used**: Unit (1 pure helper `sqlite_path_is_rejected`), Integration (16), E2E
  (0)
- **Approval tests** (refactoring): 3.15 MCP/voucher/sheet no-regression
- **Pure functions created**: 1 (`sqlite_path_is_rejected`) plus Phase 2's
  `_seller_row_is_active`

## Work Unit Evidence

### Unit 1 (retained)

| Evidence                                          | Required value                                                                                                                                                                                                                                                                        |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | Phase 2 focused: `docker exec … odoo -d devel -u collection --test-tags /collection:TestCollectionConnector,/collection:TestCollectionMcpListSellers` → `0 failed, 0 error(s) of 15 tests`. Proving: `invoke test -m collection --mode=update` → `0 failed, 0 error(s) of 381 tests`. |
| Runtime harness command/scenario and exact result | N/A — container Odoo tests are the runtime                                                                                                                                                                                                                                            |
| Rollback boundary                                 | Revert collection git Phase 2 files listed above; keep Phase 1. Manifest `19.0.1.18.0` → `19.0.1.17.0`.                                                                                                                                                                               |

### Unit 2 (this batch)

| Evidence                                          | Required value                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Focused test command and exact result             | `docker exec seedian-odoo-1 odoo -d devel -u collection_connector_sqlite --stop-after-init --test-enable --test-tags /collection_connector_sqlite --workers=0 --http-port=18069 --gevent-port=18072` → `0 failed, 0 error(s) of 16 tests`. RED gates: 3.2–3.7 first run `0 failed, 6 error(s) of 6` (`Invalid field sqlite_path` / missing models); after path-check `0 failed, 7 error(s) of 11` (`_sqlite_fetch_sellers` missing) while 3.6/3.7/hash/NUL green. Collection MCP no-regression: `--test-tags /collection:TestCollectionMcpSellerLookup,/collection:TestCollectionMcpTool,/collection:TestCollectionMcpListSellers` → `0 failed, 0 error(s) of 54 tests`. |
| Runtime harness command/scenario and exact result | N/A — container Odoo tests are the runtime (no separate HTTP/E2E harness)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Rollback boundary                                 | Revert collection `openspec/config.yaml` apply.roots; remove `odoo/custom/src/private/collection_connector_sqlite/` from parent Seedian git. Clear `collection_connector_id` then uninstall `collection_connector_sqlite` (`selection_add` ondelete cascade + company M2O set null). Do not revert Unit 1 collection facade/MCP.                                                                                                                                                                                                                                                                                                                                         |

## Deviations from Design

None — SQLite inherit uses
`selection_add=[('sqlite','SQLite')], ondelete={'sqlite':'cascade'}`; connect is
`sqlite3.connect('file:%s?mode=ro' % path, uri=True)` only after absolute path with no
`?` `#` NUL; schema `sellers(id, name, mobile, active)`; generic `UserError` with no
path/SQL; read-only success does not write the file. Company M2O remains
`ondelete='set null'`. `tools/seller_lookup.py` untouched.

## Issues Found

- Python evaluates `self._sqlite_fetch_sellers(self._sqlite_safe_path())` by looking up
  the method first; path checks must be a separate statement so relative/`?`/`#` reject
  before AttributeError.
- Module-level `_()` logs ERROR (`no translation language detected`) which Odoo treats
  as a test error; keep `_()` on the model method.
- Optional pylint `C8101` (manifest author `Eynes`) matches collection; not in the
  mandatory hook.
- Design percent-format URI triggers ruff UP031; kept with `# noqa: UP031` to match the
  design contract.

## Workload / PR Boundary

- Mode: stacked PR slice (`stacked-to-main`)
- Current work unit: Unit 2 sqlite + apply.roots
- Boundary: sibling `collection_connector_sqlite` addon + collection
  `openspec/config.yaml` apply.roots. Does not change voucher write or `get_seller_id`.
- Estimated review budget impact: ~544 authored lines in the sqlite addon plus small
  collection config.yaml (~under 800 attempt cap)
