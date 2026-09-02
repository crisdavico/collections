# Tasks: Seller Commission Percent

## Review Workload Forecast

| Field                   | Value                                        |
| ----------------------- | -------------------------------------------- |
| Estimated changed lines | 550–800                                      |
| 400-line budget risk    | High                                         |
| Chained PRs recommended | Yes                                          |
| Suggested split         | PR1 sqlite → PR2 persist → PR3 UI → PR4 docs |
| Delivery strategy       | ask-on-risk                                  |
| Chain strategy          | stacked-to-main                              |

Decision needed before apply: Yes Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

### Suggested Work Units

Seedian root: `S` = `invoke test -m collection_connector_sqlite --mode=update`; `C` =
`invoke test -m collection --mode=update`. Never `invoke resetdb`.

| Unit | Goal                   | Likely PR         | Focused test command | Runtime harness                                 | Rollback boundary                                          |
| ---- | ---------------------- | ----------------- | -------------------- | ----------------------------------------------- | ---------------------------------------------------------- |
| 1    | SQLite column + sample | PR 1 (sqlite)     | S                    | `invoke install -m collection_connector_sqlite` | sqlite schema, 19.0.1.6.0, fixtures, tests                 |
| 2    | Import persist         | PR 2 (collection) | C                    | `invoke install -m collection`                  | Float+Constraint, formatter, validate, upsert write, tests |
| 3    | Readonly UI            | PR 3 (collection) | C                    | `invoke install -m collection`                  | notebook, Settings O2M, UI tests                           |
| 4    | Manifest/docs          | PR 4 (collection) | C                    | N/A version+docs                                | `__manifest__.py`, `AGENTS.md`, migration test             |

Do not edit: `models/collection_allocation.py`, `tests/test_collection_allocation.py`,
`tests/test_collection_allocation_acl.py`, `openspec/changes/draft-until-close/`,
`openspec/changes/inline-collection-allocation/`, nebula-agent. Threat N/A.

## Phase 1: SQLite schema + tests

- [x] 1.1 RED `collection_connector_sqlite/tests/test_sqlite_connector.py`: missing
      `commission_percent` → `UserError` no path/SQL (`_assert_user_error_no_leak`);
      sample Ana 5.0, Bruno 7.5, Carla 10.0, Diego 0.0, Elena 3.0; Facundo omitted.
      Verify: `S` fails those tests.
- [x] 1.2 GREEN `collection_connector_sqlite/models/collection_connector.py`:
      `_SQLITE_REQUIRED_COLUMNS` += `commission_percent`; SELECT five columns + row
      dict. Grow `_write_sellers_db`/`_write_debt_db` 5-tuples. `data/database.sql` REAL
      DEFAULT 0 CHECK 0–100 + fixtures. Create `migrations/19.0.1.6.0/post-migrate.py` →
      `ensure_sample_sqlite_source`. Manifest `19.0.1.6.0` keep hook.
      `readme/DESCRIPTION.md`. Verify: `S`. Lint sqlite files.

## Phase 2: Collection persist

- [x] 2.1 RED `tests/test_collection_connector.py`: list shape float
      `commission_percent`; missing key → `0.0`. RED
      `tests/test_collection_seller_sync.py`: ANA 5.0 persist; re-Import overwrite 7.5
      same user; invalid `<0`/`>100`/non-numeric `UserError` zero writes; `0.0` valid.
      RED binding Constraint `<0`/`>100`. Verify: `C` fails those tests.
- [x] 2.2 GREEN `tests/common_connector.py` `TEST_SELLERS` rates (`_test_list_sellers`
      still `dict(row)`). GREEN `models/collection_connector.py` `_format_seller_list`
      copy/coerce `0.0` (no `_DISPATCH_OPS`). GREEN `models/res_company.py`: validate in
      `_collection_validate_connector_seller_rows`; upsert create **and** `write` from
      rows. GREEN `models/collection_connector_seller_binding.py`
      `Float(digits=(16, 2), required=True, default=0.0)` + `_commission_percent_range`
      `models.Constraint` CHECK 0–100. Verify: `C`. Lint.

## Phase 3: UI

- [x] 3.1 RED `tests/test_collection_ui.py` `SETTINGS_FIELD_NAMES` +=
      `seller_binding_ids`. RED `tests/test_collection_customer_binding.py` Seller
      Bindings notebook: readonly `external_seller_id`, `user_id`, `commission_percent`;
      keep Customer Bindings. Verify: `C` fails those tests.
- [x] 3.2 GREEN `models/res_config_settings.py` related readonly `seller_binding_ids`.
      GREEN `views/collection_connector_views.xml` Seller Bindings `<list>` those three
      readonly. GREEN `views/res_config_settings_views.xml` readonly O2M
      `invisible="not collection_connector_id"`. Verify: `C`. Lint.

## Phase 4: Docs / manifests / AGENTS.md

- [x] 4.1 RED `tests/test_collection_company_migration.py`: next unused version
      (`19.0.1.28.0`, or `19.0.1.29.0` if sibling took 1.28.0); no collection migrate
      folder. Verify: `C` fails until bump.
- [x] 4.2 GREEN `__manifest__.py` that version (no migrate folder). GREEN `AGENTS.md`
      one-liner: binding stores `commission_percent`. Lint. Verify: `C`.
