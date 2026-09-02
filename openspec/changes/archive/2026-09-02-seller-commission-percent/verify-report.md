```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:4ddfab83b6fce6d4514d4ff204606de7765e70e27f84d87f3bd25ef8ece0490b
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 8/8
scenarios: 21/21
test_command: "docker compose run --rm -e DB_FILTER='^devel$' odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags=/collection:TestCollectionSellerSync,/collection:TestCollectionConnector,/collection:TestCollectionUi,/collection:TestCollectionCustomerBinding,/collection:TestCollectionCompanyMigration,/collection:TestCollectionMcpSellerLookup -d devel && docker compose run --rm -e DB_FILTER='^devel$' odoo odoo --test-enable --stop-after-init --workers=0 -u collection_connector_sqlite --test-tags=/collection_connector_sqlite,-collection_connector_sqlite:TestSqliteConnector.test_rollback_vouchers_sheets_mcp_unchanged -d devel"
test_exit_code: 0
test_output_hash: sha256:cf432f31ac1a2b16c18d30d8a2d33607d0b52e0f270b79755555cfb17c5d471c
build_command: "pre-commit run --files odoo/custom/src/private/collection_connector_sqlite/tests/test_sqlite_connector.py odoo/custom/src/private/collection_connector_sqlite/models/collection_connector.py odoo/custom/src/private/collection_connector_sqlite/data/database.sql odoo/custom/src/private/collection_connector_sqlite/migrations/19.0.1.6.0/post-migrate.py odoo/custom/src/private/collection_connector_sqlite/__manifest__.py odoo/custom/src/private/collection_connector_sqlite/readme/DESCRIPTION.md odoo/custom/src/private/collection_connector_sqlite/README.rst odoo/custom/src/private/collection_connector_sqlite/static/description/index.html odoo/custom/src/private/collection/tests/test_collection_connector.py odoo/custom/src/private/collection/tests/test_collection_seller_sync.py odoo/custom/src/private/collection/tests/common_connector.py odoo/custom/src/private/collection/models/collection_connector.py odoo/custom/src/private/collection/models/res_company.py odoo/custom/src/private/collection/models/collection_connector_seller_binding.py odoo/custom/src/private/collection/tests/test_collection_ui.py odoo/custom/src/private/collection/tests/test_collection_customer_binding.py odoo/custom/src/private/collection/models/res_config_settings.py odoo/custom/src/private/collection/views/collection_connector_views.xml odoo/custom/src/private/collection/views/res_config_settings_views.xml odoo/custom/src/private/collection/tests/test_collection_company_migration.py odoo/custom/src/private/collection/__manifest__.py odoo/custom/src/private/collection/AGENTS.md"
build_exit_code: 0
build_output_hash: sha256:22f282be0dead85be6137e0803604fd5821b88887af1b5c63a759aad601d6f54
```

## Verification Report

**Change**: seller-commission-percent
**Version**: collection `19.0.1.29.0` / collection_connector_sqlite `19.0.1.6.0`
**Mode**: Strict TDD

Delta spec counted from `openspec/changes/seller-commission-percent/specs/collection-connectors/spec.md`: **8 requirements**, **21 scenarios** (4 ADDED + 4 MODIFIED; 2+3+1+1 ADDED scenarios, 2+6+3+3 MODIFIED scenarios).

`evidence_revision` is the SHA-256 of unchanged `apply-progress.md`.

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 8 |
| Tasks complete | 8 |
| Tasks incomplete | 0 |

All tasks 1.1–4.2 are `[x]` in `tasks.md` and recorded complete in `apply-progress.md`.

### Build & Tests Execution
**Build**: ✅ Passed (exit 0)
```text
pre-commit run --files <22 change-owned files listed in envelope>
PRECOMMIT_EXIT:0
Hooks: ruff, ruff-format, prettier+xml, pylint_odoo mandatory, OCA module checks, oca-gen-addon-readme — Passed.
pylint optional C8101 (manifest-required-author Eynes) on both __manifest__.py files — informational; hook still Passed.
Did not run invoke img-build (no Dockerfile/deps change).
```

**Tests**: ✅ 164 passed / ❌ 0 failed / ⚠️ 1 excluded by tag (not executed)
```text
Collection (exit 0): 0 failed, 0 error(s) of 136 tests when loading database 'devel'
  stats: collection: 148 tests
SQLite (exit 0): 0 failed, 0 error(s) of 28 tests when loading database 'devel'
  stats: collection_connector_sqlite: 30 tests
Excluded: TestSqliteConnector.test_rollback_vouchers_sheets_mcp_unchanged
  (pre-existing ERROR: collection.voucher has no customer_identification).
  Confirmed not started (tag appears only on the command line).
```

**Coverage**: ➖ Not available — `openspec/config.yaml` `testing.coverage.available: false`

### Spec Compliance Matrix
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Seller binding stores commission percent | Stored on binding not user | `tests/test_collection_seller_sync.py > test_import_persists_ana_commission_percent` | ✅ COMPLIANT |
| Seller binding stores commission percent | Out of range binding rejected | `tests/test_collection_connector.py > test_binding_commission_percent_below_zero_rejected` / `test_binding_commission_percent_above_100_rejected` / `test_binding_commission_percent_write_out_of_range_rejected` | ✅ COMPLIANT |
| Readonly commission UI | Connector notebook | `tests/test_collection_customer_binding.py > test_connector_seller_binding_notebook_readonly` | ✅ COMPLIANT |
| Readonly commission UI | Settings hidden without connector | `tests/test_collection_ui.py > test_settings_seller_binding_ids_is_readonly_and_hidden_without_connector` + `test_settings_seller_binding_ids_empty_without_connector` | ✅ COMPLIANT |
| Readonly commission UI | Settings shows stored rates | `tests/test_collection_ui.py > test_settings_seller_binding_ids_shows_stored_rates` | ✅ COMPLIANT |
| MCP get_seller_id omits commission | Lookup payload unchanged | `tests/test_collection_mcp_seller_lookup.py > test_unique_internal_match_returns_seller_id_only` (`assertEqual(result, {"seller_id": ...})`) | ✅ COMPLIANT |
| Sample seller commission rates | Sample rates listed and imported | `collection_connector_sqlite/tests/test_sqlite_connector.py > test_sample_sqlite_seller_commission_percent_rates` + `test_import_from_sample_connector_creates_five_users_and_replaces_list` + `tests/test_collection_seller_sync.py > test_import_persists_ana_commission_percent` | ✅ COMPLIANT |
| Normalized seller list output | List shape | `tests/test_collection_connector.py > test_list_sellers_shape_bound_unbound_inactive_omitted` | ✅ COMPLIANT |
| Normalized seller list output | Missing commission key coerces to zero | `tests/test_collection_connector.py > test_list_sellers_missing_commission_percent_coerces_to_zero` | ✅ COMPLIANT |
| Import replaces Enabled Sellers | Create match and bind then replace all | `tests/test_collection_seller_sync.py > test_import_creates_user_and_binding_for_unbound_seller` / `test_import_matches_existing_user_by_normalized_phone` / `test_import_replaces_enabled_list_and_omits_inactive` | ✅ COMPLIANT |
| Import replaces Enabled Sellers | Binding reuse on re-import | `tests/test_collection_seller_sync.py > test_import_reuses_existing_binding` / `test_second_import_is_idempotent` | ✅ COMPLIANT |
| Import replaces Enabled Sellers | Fail closed leaves the list unchanged | `tests/test_collection_seller_sync.py > test_missing_connector_leaves_enabled_list_unchanged` / `test_inactive_connector_leaves_enabled_list_unchanged` / `test_misconfigured_connector_leaves_enabled_list_unchanged` / `test_duplicate_source_phone_aborts_without_partial_write` / `test_two_source_ids_mapping_to_same_user_aborts` | ✅ COMPLIANT |
| Import replaces Enabled Sellers | Persist and overwrite commission percent | `tests/test_collection_seller_sync.py > test_import_overwrites_commission_percent_same_user` | ✅ COMPLIANT |
| Import replaces Enabled Sellers | Invalid commission fails closed before write | `tests/test_collection_seller_sync.py > test_invalid_commission_percent_fails_closed_before_write` | ✅ COMPLIANT |
| Import replaces Enabled Sellers | Zero commission is valid | `tests/test_collection_seller_sync.py > test_import_zero_commission_percent_is_valid` | ✅ COMPLIANT |
| SQLite read-only sellers source | Sqlite success | `collection_connector_sqlite/tests/test_sqlite_connector.py > test_sqlite_success_list_and_connection_test_does_not_write` | ✅ COMPLIANT |
| SQLite read-only sellers source | Sqlite invalid | `test_missing_file_raises_user_error_no_path_sql` / `test_unreadable_file_raises_user_error_no_path_sql` / `test_invalid_schema_raises_user_error_no_path_sql` | ✅ COMPLIANT |
| SQLite read-only sellers source | Sqlite missing commission column | `test_missing_commission_percent_column_raises_user_error_no_path_sql` | ✅ COMPLIANT |
| SQLite read-only customer debt source | Sqlite seller-scoped debt | `test_sqlite_get_customer_debt_outstanding_only_and_does_not_write` | ✅ COMPLIANT |
| SQLite read-only customer debt source | Sqlite zero debt | `test_sqlite_get_customer_debt_zero_debt_succeeds` | ✅ COMPLIANT |
| SQLite read-only customer debt source | Sqlite invalid invoices schema | `test_sqlite_get_customer_debt_malformed_schema_raises_user_error` | ✅ COMPLIANT |

**Compliance summary**: 21/21 scenarios compliant

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| Seller binding stores commission percent | ✅ Implemented | `Float(digits=(16, 2), required=True, default=0.0)` + `_commission_percent_range` `models.Constraint` on `collection.connector.seller.binding`; no field on `res.users` |
| Readonly commission UI | ✅ Implemented | Connector Seller Bindings `<list>` three readonly fields; Settings related readonly O2M `invisible="not collection_connector_id"` |
| MCP get_seller_id omits commission | ✅ Implemented | `tools/seller_lookup.py` not edited; runtime dict equality is `{seller_id}` only |
| Sample seller commission rates | ✅ Implemented | `database.sql` Ana 5.0, Bruno 7.5, Carla 10.0, Diego 0.0, Elena 3.0, Facundo 5.0 inactive |
| Normalized seller list output | ✅ Implemented | `_format_seller_list` copies/coerces missing key to `0.0` |
| Import replaces Enabled Sellers | ✅ Implemented | validate-then-write; upsert create **and** `write` of `commission_percent` |
| SQLite read-only sellers source | ✅ Implemented | `_SQLITE_REQUIRED_COLUMNS` includes `commission_percent`; SELECT five columns |
| SQLite read-only customer debt source | ✅ Implemented | debt helpers grown to 5-tuples; existing debt tests passed after exclusion |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| Store on binding not `res.users` | ✅ Yes | |
| Upsert create + write existing rates | ✅ Yes | `res_company.py` |
| Missing key coerce `0.0`; invalid fail before write | ✅ Yes | formatter + `_collection_validate_connector_seller_rows` |
| sqlite `19.0.1.6.0` post-migrate rematerialize sample | ✅ Yes | `migrations/19.0.1.6.0/post-migrate.py` |
| Readonly UI notebook + Settings O2M | ✅ Yes | |
| collection bump `19.0.1.28.0` no migrate folder | ⚠️ Fallback | Sibling `draft-until-close` took `19.0.1.28.0` + migrate folder; this change used documented fallback `19.0.1.29.0` with **no** `migrations/19.0.1.29.0/` |
| No `_DISPATCH_OPS` / MCP / nebula-agent / allocation edits | ✅ Yes | Collision guard held |

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | Found in apply-progress TDD Cycle Evidence table (8/8 tasks) |
| All tasks have tests | ✅ | 8/8 tasks have test files on disk |
| RED confirmed (tests exist) | ✅ | 8/8 listed test files exist (`test_sqlite_connector.py`, `test_collection_connector.py`, `test_collection_seller_sync.py`, `test_collection_ui.py`, `test_collection_customer_binding.py`, `test_collection_company_migration.py`) |
| GREEN confirmed (tests pass) | ✅ | Covering tests started and passed in this verify run (collection 136, sqlite 28 excluding rollback) |
| Triangulation adequate | ✅ | 7 triangulated; 1 single-case (task 4.2 version string — design-only, not a delta scenario) |
| Safety Net for modified files | ✅ | Apply-progress records pre-edit baselines for all four phases; sqlite 26/27 plus known ERROR; collection persist 33/33; UI sibling allocation failures noted then later 66/66 |

**TDD Compliance**: 6/6 checks passed (8/8 tasks have complete TDD evidence)

---

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 1 | 1 | Odoo TransactionCase path/manifest assertions (`test_manifest_version_is_1_29_0`) |
| Integration | ~163 executed in tagged suites | 6 | Containerized Odoo TransactionCase + PostgreSQL |
| E2E | 0 | 0 | not installed (`testing.layers.e2e.available: false`) |
| **Total** | **164 result-line tests** | **6** | |

---

### Changed File Coverage
Coverage analysis skipped — no coverage tool detected

---

### Assertion Quality
**Assertion quality**: ✅ All assertions verify real behavior

Scanned change-owned tests: persist/overwrite/invalid/zero rates; Constraint IntegrityError; list shape + missing-key `0.0`; Settings O2M arch+stored 5.0; notebook readonly xpath; MCP exact `{seller_id}` dict; sqlite missing-column/success/debt. Combined `isinstance(..., float)` with value asserts. SubTest loops over non-empty invalid-rate tuples. No tautologies, ghost loops, or production-code-free asserts in new commission tests.

---

### Quality Metrics
**Linter**: ✅ No errors (scoped pre-commit Passed). Optional pylint C8101 author warning on both manifests (pre-existing Eynes vs OCA hook).
**Type Checker**: ➖ Not available

### Issues Found
**CRITICAL**: None
**WARNING**:
1. Sibling dirty-tree contamination: `draft-until-close` is live. Proving used focused tags (not `invoke test -m collection --mode=update`). `TestCollectionUi` still includes sibling allocation methods; they passed in this run (0 failed of 136) but remain sibling-owned surface.
2. Pre-existing sqlite `TestSqliteConnector.test_rollback_vouchers_sheets_mcp_unchanged` excluded (`customer_identification` gone on `collection.voucher`). Not started. 28 sqlite tests passed.
3. Collection version is `19.0.1.29.0` instead of design’s `19.0.1.28.0`, matching the design collision fallback after sibling shipped 1.28.0 + migrate folder.
**SUGGESTION**:
1. `test_sample_sqlite_seller_commission_percent_rates` asserts fetch rates and Facundo omitted from `list_sellers()`, but does not assert `commission_percent` on listed rows or on sample Import bindings; persist coverage is ANA 5.0 via the test connector. Combined covering tests still satisfy the sample scenario.
2. Optional pylint C8101 (`manifest-required-author` Eynes) on both addon manifests — pre-existing, not introduced by this change.

### Verdict
PASS WITH WARNINGS
All 8 requirements / 21 scenarios have passing runtime covering tests; warnings are sibling contamination, excluded pre-existing sqlite rollback ERROR, and the documented 1.29.0 version fallback.
