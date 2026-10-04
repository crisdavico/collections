# Design: Seller Commission Percent

## Technical Approach

Store-only 0–100 `commission_percent` (UI **Commission %**) on
`collection.connector.seller.binding`. SQLite → `list_sellers()` → Import
validate/upsert → readonly UI. Delta: `collection-connectors`. Non-goals: MCP,
nebula-agent, allocation math, `_DISPATCH_OPS`, `res.users`.

## Architecture Decisions

| Decision             | Options                                                   | Tradeoff                                                                             | Choice                                                                                                                                                                    |
| -------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Home                 | Binding vs `res.users` vs live-list                       | Users reused across companies; live-list has no Import audit                         | **`collection.connector.seller.binding`**. Users stay name/phone.                                                                                                         |
| Upsert               | Create-only (`res_company.py` L171–187) vs create+`write` | Create-only leaves `0.0` after first Import                                          | **Create missing + `write` existing** `commission_percent`. Pass formatted `rows` into upsert (resolved is `(ext_id, user)`).                                             |
| Missing key          | Coerce `0.0` vs fail                                      | Fail breaks adapters that omit the key                                               | **Coerce in `_format_seller_list`**. Invalid (`<0`, `>100`, non-numeric) fails in `_collection_validate_connector_seller_rows` **before any write**.                      |
| Sample rematerialize | `post_init_hook` every upgrade vs `migrations/19.0.1.6.0` | Hook is install-only (`hooks.py` L52–53); hook-on-upgrade would rewrite custom files | **sqlite `migrations/19.0.1.6.0/post-migrate.py`** → `ensure_sample_sqlite_source`. Hook stays install-only. Custom `sqlite_path` not rewritten (fail-close until ALTER). |
| UI                   | Editable vs readonly                                      | Rate is source-of-truth                                                              | **Readonly** connector Seller Bindings notebook + Settings related One2many.                                                                                              |

## Data Flow

```mermaid
sequenceDiagram
    participant SQL as SQLite sellers
    participant Fetch as _sqlite_fetch_sellers
    participant Fmt as _format_seller_list
    participant Val as _collection_validate_connector_seller_rows
    participant Ups as _collection_upsert_seller_bindings
    participant UI as Notebook / Settings O2M
    SQL->>Fetch: SELECT id,name,mobile,active,commission_percent
    Note over Fetch: _SQLITE_REQUIRED_COLUMNS issubset; missing col → UserError
    Fetch->>Fmt: row dicts
    Fmt->>Fmt: drop inactive; missing key → 0.0
    Fmt->>Val: sellers[] + source
    alt invalid rate
        Val-->>Val: UserError; zero writes
    else ok
        Val->>Ups: resolved + rates from rows
        Ups->>UI: create missing; write existing; readonly O2M
    end
```

Import: `action_import_enabled_sellers` → `_sync_enabled_sellers_from_connector`
(validate → resolve → upsert → `Command.set` `enabled_seller_ids`).

## File Changes

| File                                                                             | Action    | Description                                                                                                                               |
| -------------------------------------------------------------------------------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `collection_connector_sqlite/data/database.sql`                                  | Modify    | `commission_percent REAL NOT NULL DEFAULT 0` CHECK 0–100; Ana 5.0, Bruno 7.5, Carla 10.0, Diego 0.0, Elena 3.0, Facundo 5.0               |
| `collection_connector_sqlite/models/collection_connector.py`                     | Modify    | `_SQLITE_REQUIRED_COLUMNS`, SELECT, row dict                                                                                              |
| `collection_connector_sqlite/migrations/19.0.1.6.0/post-migrate.py`              | Create    | `migrate(cr, version)` → `ensure_sample_sqlite_source(env)`                                                                               |
| `collection_connector_sqlite/__manifest__.py`                                    | Modify    | `19.0.1.5.0` → `19.0.1.6.0`; keep `post_init_hook`                                                                                        |
| `collection_connector_sqlite/tests/test_sqlite_connector.py`                     | Modify    | Grow `_write_sellers_db` / `_write_debt_db`; RED missing-column + sample Ana 5.0                                                          |
| `collection_connector_sqlite/readme/DESCRIPTION.md`                              | Modify    | Sellers schema; keep customers/invoices                                                                                                   |
| `collection/models/collection_connector_seller_binding.py`                       | Modify    | `Float(digits=(16, 2), required=True, default=0.0)` + CHECK `models.Constraint`; keep `_connector_external_uniq` / `_connector_user_uniq` |
| `collection/models/collection_connector.py`                                      | Modify    | `_format_seller_list` copy/coerce; no `_DISPATCH_OPS`                                                                                     |
| `collection/models/res_company.py`                                               | Modify    | Validate rate; upsert create **and** `write`                                                                                              |
| `collection/models/res_config_settings.py`                                       | Modify    | Related readonly `seller_binding_ids`                                                                                                     |
| `collection/views/collection_connector_views.xml`                                | Modify    | Seller Bindings `<list>`: readonly `external_seller_id`, `user_id`, `commission_percent`                                                  |
| `collection/views/res_config_settings_views.xml`                                 | Modify    | Readonly O2M; `invisible="not collection_connector_id"`                                                                                   |
| `collection/tests/common_connector.py`                                           | Modify    | `TEST_SELLERS` rates; `_test_list_sellers` still `dict(row)`                                                                              |
| `collection/tests/test_collection_seller_sync.py`                                | Modify    | ANA/BRUNO persist/overwrite; invalid zero writes                                                                                          |
| `collection/tests/test_collection_connector.py`                                  | Modify    | List shape + missing-key coerce                                                                                                           |
| `collection/tests/test_collection_ui.py`                                         | Modify    | `SETTINGS_FIELD_NAMES` += `seller_binding_ids`                                                                                            |
| `collection/tests/test_collection_customer_binding.py`                           | Modify    | Notebook xpath (Customer Bindings pattern)                                                                                                |
| `collection/tests/test_collection_company_migration.py`                          | Modify    | `test_manifest_version_is_1_28_0`; no `migrations/19.0.1.28.0/`                                                                           |
| `collection/__manifest__.py`, `AGENTS.md`                                        | Modify    | `19.0.1.27.0` → `19.0.1.28.0`; binding field                                                                                              |
| MCP tools, nebula-agent, allocation files, `openspec/changes/draft-until-close/` | Unchanged | Collision / non-goals                                                                                                                     |

## Interfaces / Contracts

- Binding:
  `commission_percent = fields.Float(string="Commission %", digits=(16, 2), required=True, default=0.0)`
- `_commission_percent_range = models.Constraint("CHECK(commission_percent >= 0 AND commission_percent <= 100)", …)`
  — **not** `_sql_constraints`
- `list_sellers()` rows add `commission_percent` float 0–100
- Settings:
  `seller_binding_ids = fields.One2many(related="collection_connector_id.seller_binding_ids", readonly=True)`
- New helpers `@api.private`; views `<list>` not `<tree>`

## Testing Strategy

Strict TDD: **RED first**, then GREEN.

| Layer      | What                                                                                          | Approach                                                         |
| ---------- | --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Sqlite     | Missing column → `UserError` no path/SQL; sample Ana 5.0…Elena 3.0, Facundo omitted; 5-tuples | `test_sqlite_connector.py` / `_assert_user_error_no_leak`        |
| Collection | Coerce `0.0`; persist/overwrite; invalid zero writes; Constraint; `0.0` valid                 | `test_collection_connector.py`, `test_collection_seller_sync.py` |
| UI         | Notebook; Settings O2M + hide; `SETTINGS_FIELD_NAMES`                                         | `test_collection_customer_binding.py`, `test_collection_ui.py`   |
| MCP        | `{seller_id}` only                                                                            | Existing lookup tests; do not edit `tools/seller_lookup.py`      |
| E2E        | —                                                                                             | N/A                                                              |

## Threat Matrix

N/A — this change does **not** add routing, shell, subprocess, VCS/PR automation,
executable-file classification, or process-integration. Invent no threat tasks.

## Migration / Rollout

Confirmed on disk: sqlite **19.0.1.5.0** (no `migrations/`); collection **19.0.1.27.0**
(existing `19.0.1.17.0` / `19.0.1.25.0` only).

- sqlite → **19.0.1.6.0**: post-migrate rematerializes **sample**
  (`materialize_sample_sqlite` `os.remove` + `executescript`). Custom files: operator
  ALTER.
- collection → **19.0.1.28.0**: ORM Float add only. **No** `migrations/19.0.1.28.0/`.
- Collision: `draft-until-close` also claims `19.0.1.28.0`. If it lands first, this bump
  is `19.0.1.29.0` still without a migrate folder. Do not restage allocation files.

## Open Questions

- [ ] Keep `19.0.1.28.0` unless `draft-until-close` ships first.
