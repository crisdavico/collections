```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:389ffb2680fc55352a2a39eca2f8a5061cbe6d16e6447f4ff19702d52fd5507f
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 10/10
scenarios: 11/11
test_command: invoke test -m collection --mode=update
test_exit_code: 0
test_output_hash: sha256:d548faf9774a24069b379aa1caa8f01305223d8e910ac797146668f0d58f8791
build_command: invoke img-build
build_exit_code: 0
build_output_hash: sha256:579065a07ee6bf9d16f0c5c75486da45aa19657312dd4db237fb6b81aad7bf1d
```

## Verification Report

**Change**: add-pluggable-collection-connectors **Version**: collection `19.0.1.18.0`
(delta spec `collection-connectors`; Modified Capabilities: none) **Mode**: Strict TDD

### Completeness

| Metric           | Value |
| ---------------- | ----- |
| Tasks total      | 35    |
| Tasks complete   | 35    |
| Tasks incomplete | 0     |

All `tasks.md` items are `[x]`. Full spec verification proceeded.

### Build & Tests Execution

**Build**: ✅ Passed

```text
invoke img-build
exit 0
output sha256:579065a07ee6bf9d16f0c5c75486da45aa19657312dd4db237fb6b81aad7bf1d
terminal: Image registry.eynes.com.ar/seedian/seedian:master-latest Built (140.2s)
```

**Tests**: ✅ 381 passed / ❌ 0 failed / ⚠️ 0 skipped (declared collection command)

```text
invoke test -m collection --mode=update
exit 0
output sha256:d548faf9774a24069b379aa1caa8f01305223d8e910ac797146668f0d58f8791
odoo.tests.result: 0 failed, 0 error(s) of 381 tests when loading database 'devel'
```

Additional sqlite-addon evidence (not the envelope `test_command`):

```text
invoke test -m collection_connector_sqlite --mode=update
exit 0
output sha256:049b6f1f1ed7d17fb6399cdbff88f7eccc1788571d2ca02458bffc43a7af8229
odoo.tests.result: 0 failed, 0 error(s) of 16 tests when loading database 'devel'
```

**Coverage**: ➖ Not available — Coverage analysis skipped — no coverage tool detected

### Spec Compliance Matrix

| Requirement                         | Scenario          | Test                                                                                                                                                                                                                                                        | Result       |
| ----------------------------------- | ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| Company-scoped connector            | Persist connector | `tests/test_collection_company_settings.py` > `test_company_a_saves_connector_via_settings`, `test_company_b_keeps_connector_when_a_saves`, `test_settings_collection_connector_id_is_related_writable`                                                     | ✅ COMPLIANT |
| Active-company list routing         | Active company    | `tests/test_collection_mcp_list_sellers.py` > `test_active_company_lists_from_assigned_connector`                                                                                                                                                           | ✅ COMPLIANT |
| Fail closed without leakage         | Fail closed       | `tests/test_collection_mcp_list_sellers.py` > `test_missing_connector_raises_user_error_no_leak`, `test_inactive_connector_raises_user_error_no_leak`, `test_misconfigured_connector_raises_user_error_no_leak`                                             | ✅ COMPLIANT |
| Internal method-discovered read MCP | Auth              | `tests/test_collection_mcp_list_sellers.py` > `test_list_collection_sellers_discovered_as_method_read_mcp`, `test_portal_and_public_callers_denied_access_error`                                                                                            | ✅ COMPLIANT |
| Normalized seller list output       | List shape        | `tests/test_collection_mcp_list_sellers.py` > `test_list_shape_bound_unbound_inactive_omitted`                                                                                                                                                              | ✅ COMPLIANT |
| Binding uniqueness                  | Uniqueness        | `tests/test_collection_connector.py` > `test_binding_reuse_external_seller_id_rejected`, `test_binding_reuse_user_rejected`, `test_binding_other_company_rejected`                                                                                          | ✅ COMPLIANT |
| List is not collect permission      | No collect        | `tests/test_collection_mcp_list_sellers.py` > `test_listed_seller_still_fails_assert_new_work`                                                                                                                                                              | ✅ COMPLIANT |
| SQLite read-only sellers source     | Sqlite success    | `collection_connector_sqlite/tests/test_sqlite_connector.py` > `test_sqlite_success_list_and_connection_test_does_not_write`                                                                                                                                | ✅ COMPLIANT |
| SQLite read-only sellers source     | Sqlite invalid    | `collection_connector_sqlite/tests/test_sqlite_connector.py` > `test_missing_file_raises_user_error_no_path_sql`, `test_unreadable_file_raises_user_error_no_path_sql`, `test_invalid_schema_raises_user_error_no_path_sql` (plus threat-matrix path tests) | ✅ COMPLIANT |
| Company isolation                   | Isolation         | `tests/test_collection_mcp_list_sellers.py` > `test_company_a_must_not_list_company_b_connector`                                                                                                                                                            | ✅ COMPLIANT |
| Rollback unchanged                  | Rollback          | `collection_connector_sqlite/tests/test_sqlite_connector.py` > `test_rollback_vouchers_sheets_mcp_unchanged`, `test_company_m2o_set_null_when_sqlite_connector_unlinked`, `test_sqlite_selection_add_and_path_field`                                        | ✅ COMPLIANT |

**Compliance summary**: 11/11 scenarios compliant

Rollback covering tests prove voucher/sheet/`get_seller_id`/`create_collection_vouchers`
still work, company M2O `ondelete='set null'` on unlink, and sqlite `selection_add`
cascade. They do not run live `ir.module.module` uninstall inside TransactionCase
(recorded as WARNING below).

### Correctness (Static Evidence)

| Requirement                         | Status         | Notes                                                                                                                      |
| ----------------------------------- | -------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Company-scoped connector            | ✅ Implemented | `collection.connector` + `res.company.collection_connector_id` related writable on Collection Settings                     |
| Active-company list routing         | ✅ Implemented | MCP `list_collection_sellers` has empty schema / no `company_id`; uses `env.company.collection_connector_id`               |
| Fail closed without leakage         | ✅ Implemented | Missing/inactive → generic `UserError`; empty type → dispatcher `UserError`; leak tokens asserted in tests                 |
| Internal method-discovered read MCP | ✅ Implemented | `@mcp_tool` method on `muk_mcp.mixin`; `kind=method`; no `sudo()` in tool source; portal/public `AccessError`              |
| Normalized seller list output       | ✅ Implemented | `_format_seller_list` drops inactive; bound `odoo_seller_id` from bindings; source metadata                                |
| Binding uniqueness                  | ✅ Implemented | `models.Constraint` UNIQUE pairs + create-time other-company `UserError`; related stored `company_id`                      |
| List is not collect permission      | ✅ Implemented | List tool does not call `_assert_new_work`; helper still rejects unbound-from-enabled sellers                              |
| SQLite read-only sellers source     | ✅ Implemented | Sibling addon; absolute path; reject `?` `#` NUL; `file:%s?mode=ro`; generic `UserError`                                   |
| Company isolation                   | ✅ Implemented | Company `ir.rule` + MCP routes only `env.company` connector                                                                |
| Rollback unchanged                  | ✅ Implemented | Company M2O `ondelete='set null'`; sqlite type `ondelete={'sqlite':'cascade'}`; voucher MCP / `seller_lookup.py` untouched |

### Coherence (Design)

| Decision                                          | Followed? | Notes                                                                                                     |
| ------------------------------------------------- | --------- | --------------------------------------------------------------------------------------------------------- |
| Dispatch allowlist `_dispatch(op)`                | ✅ Yes    | `op ∈ {test_connection, list_sellers}`; type in Selection keys; miss → generic `UserError`                |
| SQLite path Char on connector inherit             | ✅ Yes    | `sqlite_path` on sqlite `_inherit`; hidden via view `invisible=`                                          |
| Binding `company_id` related stored               | ✅ Yes    | `required=True`, `precompute=True`, `index=True`                                                          |
| ACL user read / system write                      | ✅ Yes    | ACL tests + `ir.rule` on connector and binding                                                            |
| SQLite `selection_add` cascade + company set-null | ✅ Yes    | Field `ondelete` asserted in tests                                                                        |
| MCP only in collection; no sudo; no DB tool row   | ✅ Yes    | `tools/collection_connector.py`; `seller_lookup.py` last commit is prior provenance work, not this change |
| List skips `_assert_new_work`                     | ✅ Yes    |                                                                                                           |

### TDD Compliance

| Check                         | Result | Details                                                                                                                                                                                      |
| ----------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TDD Evidence reported         | ✅     | Found Phase 1–3 TDD Cycle Evidence tables in `apply-progress.md`                                                                                                                             |
| All tasks have tests          | ✅     | 35/35 tasks have test files or documented structural/no-regression coverage                                                                                                                  |
| RED confirmed (tests exist)   | ✅     | New files `tests/test_collection_connector.py`, `tests/test_collection_mcp_list_sellers.py`, `tests/common_connector.py`, `collection_connector_sqlite/tests/test_sqlite_connector.py` exist |
| GREEN confirmed (tests pass)  | ✅     | Collection 381/381 and sqlite 16/16 passed on this run                                                                                                                                       |
| Triangulation adequate        | ✅     | Persist 3 cases; fail-closed 3 separate tests; uniqueness E/U/other-company; sqlite invalid 3 classes + threat-matrix paths                                                                  |
| Safety Net for modified files | ⚠️     | Task 1.3 recorded proving suite 366/366 but noted ACL-only pre-edit class run was not repeated after the 1.1 baseline                                                                        |

**TDD Compliance**: 5/6 checks passed (safety-net warning on 1.3)

---

### Test Layer Distribution

| Layer       | Tests  | Files | Tools                                                 |
| ----------- | ------ | ----- | ----------------------------------------------------- |
| Unit        | 4      | 1     | Odoo TransactionCase + pure `sqlite_path_is_rejected` |
| Integration | 37     | 6     | Containerized Odoo TransactionCase / PostgreSQL       |
| E2E         | 0      | 0     | not installed                                         |
| **Total**   | **41** | **6** | focused tests created/modified for this change        |

Focused files: `test_collection_connector.py` (6), `test_collection_mcp_list_sellers.py`
(9), `test_sqlite_connector.py` (16), plus connector cases in
`test_collection_company_settings.py` (3), `test_collection_acl.py` (5),
`test_collection_ui.py` (2). Envelope run also executed the full collection module suite
(381).

---

### Changed File Coverage

Coverage analysis skipped — no coverage tool detected

---

### Assertion Quality

**Assertion quality**: ✅ All assertions verify real behavior

Scanned focused test files for tautologies, empty-only companions, type-only-alone
checks, ghost loops, and smoke-only tests. Leak-token loops iterate a non-empty constant
tuple. `unittest.mock.patch` on `sqlite3.connect` is paired with `assert_not_called`
plus `UserError` (behavior: connect never happens). Portal/public denial uses `subTest`
over two concrete users.

---

### Quality Metrics

**Linter**: ⚠️ 0 errors, 2 optional warnings (`C8101` manifest author `Eynes` on
`collection/__manifest__.py` and `collection_connector_sqlite/__manifest__.py`).
Mandatory pylint-odoo hook passed. Scoped `pre-commit run --files` on changed
collection + sqlite paths: exit 0. **Type Checker**: ➖ Not available

### Issues Found

**CRITICAL**: None **WARNING**:

- Rollback scenario is proven via no-regression + ORM `ondelete` contracts, not a live
  `button_uninstall` of `collection_connector_sqlite` inside the test transaction.
- Strict TDD safety net for task 1.3 was the full proving suite rather than a repeated
  ACL-only pre-edit run after task 1.1. **SUGGESTION**:
- Optional pylint `C8101` (manifest author must include `Eynes`) on both addon
  manifests; matches existing collection convention and is outside the mandatory hook.

### Verdict

PASS WITH WARNINGS All 10 requirements and 11 scenarios have passing covering tests;
collection 381 and sqlite 16 runtime suites are green; remaining notes are TDD
safety-net and uninstall-harness limits, not spec failures.
