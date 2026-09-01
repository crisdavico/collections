# Tasks: Add Pluggable Collection Connectors

## Review Workload Forecast

Estimated changed lines: 800–1200. Delivery strategy: ask-on-risk.

Decision needed before apply: Yes Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

### Suggested Work Units

**Unit 1 — facade** (PR 1 → main). Focused test command:
`invoke test -m collection --mode=update`. Runtime harness: N/A — container Odoo tests
are the runtime. Rollback: collection git; no sqlite addon.

**Unit 2 — sqlite + apply.roots** (PR 2 → main after PR 1). Focused test command:
`invoke test -m collection_connector_sqlite --mode=update` plus collection MCP
no-regression. Runtime harness: N/A — container Odoo tests are the runtime. Rollback:
`openspec/config.yaml` apply.roots + `collection_connector_sqlite/`; clear connector
then uninstall.

## Phase 1: Unit 1 — foundation

- [x] 1.1 RED Persist connector (`tests/test_collection_company_settings.py`): A saves;
      B unchanged; keep XMLID (`tests/test_collection_ui.py`).
- [x] 1.2 GREEN `models/collection_connector.py`, `res_company.py`,
      `res_config_settings.py`, `views/res_config_settings_views.xml`,
      `models/__init__.py`.
- [x] 1.3 RED ACL (`tests/test_collection_acl.py`): user read, system write, company
      `ir.rule`, portal denied.
- [x] 1.4 GREEN `security/collection_security.xml`, `ir.model.access.csv`,
      `views/collection_connector_views.xml`.

## Phase 2: Unit 1 — MCP

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
- [x] 2.13 GREEN `tools/collection_connector.py` + `tools/__init__.py`. Do not edit
      `tools/seller_lookup.py`.
- [x] 2.14 No-regression: `tests/test_collection_mcp_seller_lookup.py`,
      `tests/test_collection_mcp_tool.py`.
- [x] 2.15 Manifest `19.0.1.18.0`; `tests/__init__.py`; upgrade collection; scoped
      pre-commit; `AGENTS.md` + `readme/`. Verify `--mode=update`.

## Phase 3: Unit 2 — sqlite

- [x] 3.1 FIRST: `openspec/config.yaml` apply.roots +=
      `/home/crisd/projects/seedian/seedian/odoo/custom/src/private/collection_connector_sqlite`
      (+ parent private).
- [x] 3.2 RED `collection_connector_sqlite/tests/test_sqlite_connector.py`:
      `requirements.txt` → `UserError`, not executed, no leak.
- [x] 3.3 RED `CMakeLists.txt` → same.
- [x] 3.4 RED executable Markdown/MDX → same.
- [x] 3.5 RED `README.sh` → same.
- [x] 3.6 RED relative path → `UserError`, no leak.
- [x] 3.7 RED `path?mode=rw` → `UserError`, no leak.
- [x] 3.8 GREEN reject non-absolute / `?` `#` NUL before `sqlite3.connect`
      (`collection_connector_sqlite/models/collection_connector.py`).
- [x] 3.9 RED missing file → `UserError`, no path/SQL.
- [x] 3.10 RED unreadable file → `UserError`, no path/SQL.
- [x] 3.11 RED invalid schema → `UserError`, no path/SQL.
- [x] 3.12 GREEN `_sqlite_*` `mode=ro` after checks; `UserError`.
- [x] 3.13 RED Sqlite success: list + connection-test; file not written.
- [x] 3.14 GREEN `selection_add`, `sqlite_path`, views, manifest
      `depends: ['collection']`.
- [x] 3.15 RED Rollback: vouchers/sheets/`get_seller_id`/`create_collection_vouchers`
      unchanged.
- [x] 3.16 GREEN cascade + `set null`. sqlite `readme/`. Upgrade sqlite; scoped
      pre-commit. Verify sqlite + collection MCP.
