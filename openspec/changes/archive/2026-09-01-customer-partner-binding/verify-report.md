```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:a741eaec7a723d87d92ad70f99d073c96b4dd6aa49bb95b6d261ba08dcd2634e
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 13/13
scenarios: 50/50
test_command: invoke test -m collection --mode=update
test_exit_code: 0
test_output_hash: sha256:254308a1973e8133fd303715984706a805d5b8ad728286d882023b164d280afc
build_command: invoke install -m collection
build_exit_code: 0
build_output_hash: sha256:a72663beeb11a2a3b488a40b3bef88d0a9f5e1a7c50336ff6e85023151c19a65
```

## Verification Report

**Change**: `customer-partner-binding` **Version**: collection `19.0.1.24.0` (delta
specs `collection-connectors` + `collection-vouchers`) **Mode**: Strict TDD

Delta spec counts (actual `### Requirement:` / `#### Scenario:` blocks): 8 + 5 = **13
requirements**; 18 + 32 = **50 scenarios**.

### Completeness

| Metric           | Value |
| ---------------- | ----- |
| Tasks total      | 16    |
| Tasks complete   | 16    |
| Tasks incomplete | 0     |

All `tasks.md` items 1.1–5.3 are `[x]`. Full spec verification proceeded.

### Build & Tests Execution

**Build**: ✅ Passed (cheap equivalent of configured `invoke img-build`; Python/XML
addon change, no image deps)

```text
invoke install -m collection
exit 0
output sha256:a72663beeb11a2a3b488a40b3bef88d0a9f5e1a7c50336ff6e85023151c19a65
odoo: Modules loaded.
schema: Missing not-null constraint on collection.voucher.partner_id (design D4)
```

**Tests**: ✅ 452 passed / ❌ 0 failed / ⚠️ 0 skipped (declared collection command)

```text
invoke test -m collection --mode=update
exit 0
output sha256:254308a1973e8133fd303715984706a805d5b8ad728286d882023b164d280afc
odoo.tests.result: 0 failed, 0 error(s) of 452 tests when loading database 'devel'
odoo.tests.stats: collection: 502 tests 20.63s 33624 queries
schema ERROR then WARNING: column partner_id contains null values; Missing not-null constraint on collection.voucher.partner_id (design D4)
```

**Lint** (not envelope): scoped
`pre-commit run --files odoo/custom/src/private/collection/**` exit 0. Optional pylint
`C8101` (`manifest-required-author`, author `Eynes`) on `__manifest__.py`. Mandatory
pylint-odoo hook passed.

**Coverage**: ➖ Not available — Coverage analysis skipped — no coverage tool detected

### Spec Compliance Matrix

| Requirement                                  | Scenario                                                    | Test                                                                                                                                                                                                                                                                                                    | Result       |
| -------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| Write path may create partners and bindings  | Write path provisions on all-new create                     | `test_collection_mcp_partner_resolve.py` > `test_all_new_resolves_after_classify_inside_savepoint`; `test_collection_mcp_customer_list.py` > `test_success_returns_normalized_customers_without_source`; `test_collection_mcp_customer_debt.py` > `test_success_returns_normalized_debt_without_source` | ✅ COMPLIANT |
| Customer binding uniqueness                  | Uniqueness on three axes                                    | `test_collection_customer_binding.py` > `test_binding_reuse_external_customer_id_rejected`, `test_binding_reuse_identification_rejected`, `test_binding_reuse_partner_rejected`, `test_binding_other_company_rejected`                                                                                  | ✅ COMPLIANT |
| Customer partner resolution                  | Enabled Seller gate before lookup                           | `test_collection_customer_resolution.py` > `test_disabled_or_unbound_seller_raises_before_lookup`                                                                                                                                                                                                       | ✅ COMPLIANT |
| Customer partner resolution                  | Binding fast path skips adapter                             | `test_collection_customer_resolution.py` > `test_binding_fast_path_skips_adapter`                                                                                                                                                                                                                       | ✅ COMPLIANT |
| Customer partner resolution                  | Unique vat binds existing partner                           | `test_collection_customer_resolution.py` > `test_unique_vat_binds_existing_partner`                                                                                                                                                                                                                     | ✅ COMPLIANT |
| Customer partner resolution                  | No vat match creates partner                                | `test_collection_customer_resolution.py` > `test_no_vat_match_creates_partner_and_binding`                                                                                                                                                                                                              | ✅ COMPLIANT |
| Customer partner resolution                  | Ambiguous vat fails closed                                  | `test_collection_customer_resolution.py` > `test_ambiguous_vat_fails_closed`                                                                                                                                                                                                                            | ✅ COMPLIANT |
| Customer partner resolution                  | Unknown inactive or other-seller fails closed               | `test_collection_customer_resolution.py` > `test_unknown_inactive_other_seller_fails_closed`                                                                                                                                                                                                            | ✅ COMPLIANT |
| Customer partner resolution                  | Concurrent first-sighting converges                         | `test_collection_customer_resolution.py` > `test_nested_unique_violation_converges_without_document_conflict`; `test_collection_mcp_partner_resolve.py` > `test_binding_unique_violation_with_winner_creates`                                                                                           | ✅ COMPLIANT |
| Customer binding ACL                         | User can create not mutate                                  | `test_collection_customer_binding.py` > `test_user_can_create_not_write_or_unlink`, `test_acl_rows_user_create_system_full`                                                                                                                                                                             | ✅ COMPLIANT |
| Customer binding ACL                         | Other-company bindings hidden                               | `test_collection_customer_binding.py` > `test_other_company_bindings_hidden`                                                                                                                                                                                                                            | ✅ COMPLIANT |
| Read-only MCP tool list_collection_customers | Registered read tool                                        | `test_collection_mcp_customer_list.py` > `test_list_collection_customers_discovered_as_method_read_mcp`                                                                                                                                                                                                 | ✅ COMPLIANT |
| Normalized customer list output              | List shape                                                  | `test_collection_connector.py` > `test_list_customers_shape_active_only_with_source`                                                                                                                                                                                                                    | ✅ COMPLIANT |
| Normalized customer list output              | MCP list omits source                                       | `test_collection_mcp_customer_list.py` > `test_success_returns_normalized_customers_without_source`                                                                                                                                                                                                     | ✅ COMPLIANT |
| Read-only MCP tool customer_debt             | Registered read tool                                        | `test_collection_mcp_customer_debt.py` > `test_customer_debt_discovered_as_method_read_mcp`                                                                                                                                                                                                             | ✅ COMPLIANT |
| Normalized customer debt output              | Debt shape                                                  | `test_collection_connector.py` > `test_get_customer_debt_shape_outstanding_only_with_source`                                                                                                                                                                                                            | ✅ COMPLIANT |
| Normalized customer debt output              | MCP debt omits source                                       | `test_collection_mcp_customer_debt.py` > `test_success_returns_normalized_debt_without_source`                                                                                                                                                                                                          | ✅ COMPLIANT |
| Normalized customer debt output              | Zero debt succeeds                                          | `test_collection_mcp_customer_debt.py` > `test_zero_debt_returns_empty_invoices`; `test_collection_connector.py` > `test_get_customer_debt_zero_debt_succeeds`                                                                                                                                          | ✅ COMPLIANT |
| Deferred integrations not required           | Completeness without deferred features                      | `test_collection_voucher.py` > approve/reject/create paths; no HTTP/WhatsApp/agent deps                                                                                                                                                                                                                 | ✅ COMPLIANT |
| Voucher fields and defaults                  | Defaults on create                                          | `test_collection_voucher.py` > `test_defaults_on_create`                                                                                                                                                                                                                                                | ✅ COMPLIANT |
| Voucher fields and defaults                  | Required fields                                             | `test_collection_voucher.py` > `test_partner_required` (ORM required; IntegrityError when SQL NOT NULL exists)                                                                                                                                                                                          | ✅ COMPLIANT |
| Voucher fields and defaults                  | create_date not overridable                                 | `test_collection_voucher.py` > `test_create_date_not_overridable`, `test_create_rejects_received_date_vals`                                                                                                                                                                                             | ✅ COMPLIANT |
| Voucher fields and defaults                  | Char customer_identification gone                           | `test_collection_voucher.py` > `test_partner_required`; `test_collection_ui.py` > `test_customer_field_is_partner_id_without_domain`                                                                                                                                                                    | ✅ COMPLIANT |
| Payment Vouchers UI                          | Menu and form behaviors                                     | `test_collection_ui.py` > `test_list_and_search_show_required_fields`, `test_form_statusbar_approve_reject_when_pending`, `test_views_have_no_received_date`                                                                                                                                            | ✅ COMPLIANT |
| Payment Vouchers UI                          | Kanban grouped by state                                     | `test_collection_ui.py` > `test_kanban_groups_by_state_and_shows_card_fields`                                                                                                                                                                                                                           | ✅ COMPLIANT |
| Payment Vouchers UI                          | Payment Lines menu absent                                   | `test_collection_ui.py` > `test_load_menus_omits_payment_lines`, `test_payment_line_xmlids_removed`                                                                                                                                                                                                     | ✅ COMPLIANT |
| Payment Vouchers UI                          | UI create_date visibility                                   | `test_collection_ui.py` > `test_list_and_search_show_required_fields`, `test_views_have_no_received_date`                                                                                                                                                                                               | ✅ COMPLIANT |
| Payment Vouchers UI                          | Customer field has no domain                                | `test_collection_ui.py` > `test_customer_field_is_partner_id_without_domain`                                                                                                                                                                                                                            | ✅ COMPLIANT |
| MCP tool create_collection_vouchers          | All-new create                                              | `test_collection_mcp_tool.py` > `test_all_new_create_returns_vouchers_in_payment_order`                                                                                                                                                                                                                 | ✅ COMPLIANT |
| MCP tool create_collection_vouchers          | Mixed-customer batch create                                 | `test_collection_mcp_partner_resolve.py` > `test_mixed_customer_batch_stamps_distinct_partners`; `test_collection_mcp_tool.py` > `test_mixed_customers_create_one_voucher_each`                                                                                                                         | ✅ COMPLIANT |
| MCP tool create_collection_vouchers          | Mixed-customer batch atomic failure                         | `test_collection_mcp_partner_resolve.py` > `test_invalid_customer_batch_rolls_back_partners_and_bindings`                                                                                                                                                                                               | ✅ COMPLIANT |
| MCP tool create_collection_vouchers          | Missing or blank per-payment customer rejected              | `test_collection_mcp_tool.py` > `test_create_rejects_missing_per_payment_customer`, `test_create_rejects_blank_per_payment_customer`                                                                                                                                                                    | ✅ COMPLIANT |
| MCP tool create_collection_vouchers          | Old top-level customer shape rejected                       | `test_collection_mcp_tool.py` > `test_create_rejects_top_level_customer_without_per_payment_customer`                                                                                                                                                                                                   | ✅ COMPLIANT |
| MCP tool create_collection_vouchers          | All-new resolves after classify inside savepoint            | `test_collection_mcp_partner_resolve.py` > `test_all_new_resolves_after_classify_inside_savepoint`                                                                                                                                                                                                      | ✅ COMPLIANT |
| MCP tool create_collection_vouchers          | Exact-retry returns all vouchers                            | `test_collection_mcp_tool.py` > `test_exact_retry_returns_all_vouchers_ignores_customer`                                                                                                                                                                                                                | ✅ COMPLIANT |
| MCP tool create_collection_vouchers          | Exact replay performs no customer resolution                | `test_collection_mcp_partner_resolve.py` > `test_exact_replay_skips_adapter_keeps_first_partner`                                                                                                                                                                                                        | ✅ COMPLIANT |
| MCP tool create_collection_vouchers          | Duplicate document_id in call                               | `test_collection_mcp_tool.py` > `test_in_call_duplicate_document_id_rejects_no_writes`                                                                                                                                                                                                                  | ✅ COMPLIANT |
| MCP tool create_collection_vouchers          | Partial-conflict                                            | `test_collection_mcp_tool.py` > `test_partial_conflict_rejects_no_writes`                                                                                                                                                                                                                               | ✅ COMPLIANT |
| MCP tool create_collection_vouchers          | Existing document_ids on different vouchers succeed         | `test_collection_mcp_tool.py` > `test_existing_document_ids_on_different_vouchers_succeed`                                                                                                                                                                                                              | ✅ COMPLIANT |
| MCP tool create_collection_vouchers          | ACL denial for non-permitted user                           | `test_collection_mcp_tool.py` > `test_portal_user_denied_no_writes`                                                                                                                                                                                                                                     | ✅ COMPLIANT |
| MCP tool create_collection_vouchers          | Missing or invalid seller_id rejected                       | `test_collection_mcp_tool.py` > `test_missing_seller_id_rejects_no_writes`, `test_portal_seller_id_rejects_no_writes`, `test_unknown_seller_id_rejects_no_writes`                                                                                                                                       | ✅ COMPLIANT |
| MCP tool create_collection_vouchers          | All-new with unique open assigns the batch                  | `test_collection_mcp_tool.py` > `test_all_new_unique_open_assigns_all_payments`                                                                                                                                                                                                                         | ✅ COMPLIANT |
| MCP tool create_collection_vouchers          | All-new with no open creates one open sheet and assigns all | `test_collection_mcp_tool.py` > `test_all_new_no_open_creates_one_sheet_and_assigns_all`                                                                                                                                                                                                                | ✅ COMPLIANT |
| MCP tool create_collection_vouchers          | All-new with more than one open rejected                    | `test_collection_mcp_tool.py` > `test_all_new_multiple_opens_rejects_no_writes`                                                                                                                                                                                                                         | ✅ COMPLIANT |
| MCP tool create_collection_vouchers          | Exact replay does not change sheet_id                       | `test_collection_mcp_tool.py` > `test_exact_replay_leaves_sheet_id_and_write_date`                                                                                                                                                                                                                      | ✅ COMPLIANT |
| MCP tool create_collection_vouchers          | All-new empty or disabled seller rejected                   | `test_collection_mcp_tool.py` > `test_all_new_empty_enabled_sellers_rejects_no_writes`, `test_all_new_disabled_seller_rejects_no_writes`                                                                                                                                                                | ✅ COMPLIANT |
| MCP tool create_collection_vouchers          | All-new disallowed type rejected                            | `test_collection_mcp_tool.py` > `test_all_new_disallowed_type_rejects_no_writes`                                                                                                                                                                                                                        | ✅ COMPLIANT |
| MCP tool create_collection_vouchers          | All-new with auto_create_sheet off stays unassigned         | `test_collection_mcp_tool.py` > `test_all_new_auto_create_off_stays_unassigned`                                                                                                                                                                                                                         | ✅ COMPLIANT |
| Typed provenance copies of payment fields    | Identity and proof stay outside provenance                  | `test_collection_mcp_tool.py` > `test_schema_exposes_nests_without_identity_or_base64`, `test_omitted_nests_with_attachment_keep_base64_out_of_provenance`                                                                                                                                              | ✅ COMPLIANT |
| Typed provenance copies of payment fields    | Cash-deposit extra keys stored in all layers                | `test_collection_mcp_tool.py` > `test_cash_deposit_stores_voucher_number_and_date_in_all_layers`                                                                                                                                                                                                        | ✅ COMPLIANT |
| Typed provenance copies of payment fields    | Voucher write rejects provenance keys                       | `test_collection_voucher.py` > `test_write_rejects_ocr_and_seller_keys`                                                                                                                                                                                                                                 | ✅ COMPLIANT |

**Compliance summary**: 50/50 scenarios compliant

### Correctness (Static Evidence)

| Requirement                                 | Status         | Notes                                                                                                   |
| ------------------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------- |
| Write path may create partners and bindings | ✅ Implemented | MCP all-new `resolve_customer_partner` inside savepoint; list/debt format only                          |
| Customer binding uniqueness                 | ✅ Implemented | Three `models.Constraint` UNIQUE pairs; create-time company-guard                                       |
| Customer partner resolution                 | ✅ Implemented | Ident → enabled-bound seller → binding fast path → `list_customers` → exact vat; nested UniqueViolation |
| Customer binding ACL                        | ✅ Implemented | user `1,0,1,0`; system `1,1,1,1`; company `ir.rule`; no `sudo()`                                        |
| Read-only MCP list_collection_customers     | ✅ Implemented | `@mcp_tool` read/method; payload keys exclude `source`/`partner_id`                                     |
| Normalized customer list output             | ✅ Implemented | Active-only four keys; ORM list attaches `source`; no partner writes                                    |
| Read-only MCP customer_debt                 | ✅ Implemented | `@mcp_tool` read/method; payload excludes `source`/`partner_id`                                         |
| Normalized customer debt output             | ✅ Implemented | Outstanding invoices; zero-debt empty list; no partner writes                                           |
| Deferred integrations not required          | ✅ Implemented | Required `partner_id`; attachments optional                                                             |
| Voucher fields and defaults                 | ✅ Implemented | Char gone; Many2one Customer required/tracking/index/restrict; no `migrations/` (D4)                    |
| Payment Vouchers UI                         | ✅ Implemented | Six `partner_id` nodes, no Customer domain                                                              |
| MCP create_collection_vouchers              | ✅ Implemented | String I/O unchanged; resolve after classify; replay skips resolve; payload omits `partner_id`          |
| Typed provenance copies                     | ✅ Implemented | `_REVIEW_EDITABLE_FIELDS` excludes `partner_id` / identification                                        |

### Coherence (Design)

| Decision                         | Followed? | Notes                                                                                       |
| -------------------------------- | --------- | ------------------------------------------------------------------------------------------- |
| Lazy D2 on MCP create only       | ✅ Yes    | Read tools do not call `resolve_customer_partner`                                           |
| VAT exact strip, no CUIT (Q1/D3) | ✅ Yes    | `test_no_cuit_normalize_creates_when_digits_differ`                                         |
| MCP string in (D1)               | ✅ Yes    | Schema still requires per-payment `customer_identification`                                 |
| ACL `1,0,1,0` never sudo (P1)    | ✅ Yes    |                                                                                             |
| Rename + extend SQL (P5+Q3)      | ✅ Yes    | `_collection_create_partners` INSERT includes `vat`, `company_id`, `customer_rank`          |
| Nested UniqueViolation savepoint | ✅ Yes    | Connector nested savepoint + MCP wrapper maps escaped UniqueViolation to customer UserError |
| Six views, no domain (P2)        | ✅ Yes    |                                                                                             |
| No data migration (D4)           | ✅ Yes    | Devel missing SQL NOT NULL accepted                                                         |
| Do not restage Q4 connector dirt | ✅ Yes    | Unrelated connector/archive dirt left unstaged                                              |
| Manifest 19.0.1.24.0             | ✅ Yes    | Method renamed to `test_manifest_version_is_1_24_0` (design said bump 1_23_0)               |

### TDD Compliance

| Check                         | Result | Details                                                                                                                                          |
| ----------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| TDD Evidence reported         | ✅     | TDD Cycle Evidence table in `apply-progress.md` for tasks 1.1–5.3                                                                                |
| All tasks have tests          | ✅     | 16/16 have test files or documented docs/command coverage (5.2 docs, 5.3 verification)                                                           |
| RED confirmed (tests exist)   | ✅     | New: `tests/test_collection_customer_binding.py`, `tests/test_collection_customer_resolution.py`, `tests/test_collection_mcp_partner_resolve.py` |
| GREEN confirmed (tests pass)  | ✅     | This run: 0 failed, 0 error(s) of 452 tests                                                                                                      |
| Triangulation adequate        | ✅     | UNIQUE 3 axes + company-guard; vat 1/0/>1 + CUIT + race; MCP mixed/invalid/replay                                                                |
| Safety Net for modified files | ✅     | Phase 2–5 recorded pre-edit/focused suites; 1.1/1.2 N/A new                                                                                      |

**TDD Compliance**: 6/6 checks passed

---

### Test Layer Distribution

| Layer       | Tests  | Files | Tools                                                                                      |
| ----------- | ------ | ----- | ------------------------------------------------------------------------------------------ |
| Unit        | 1      | 1     | Odoo TransactionCase file-read (`test_manifest_version_is_1_24_0`)                         |
| Integration | 24     | 3     | Containerized Odoo TransactionCase (new binding 8 + resolution 10 + MCP partner-resolve 6) |
| E2E         | 0      | 0     | not installed                                                                              |
| **Total**   | **25** | **4** | focused tests created for this change                                                      |

Envelope run also executed the full collection module suite (452). Additional covering
tests live in modified `test_collection_mcp_tool.py`, `test_collection_voucher.py`,
`test_collection_ui.py`, `test_collection_connector.py`, and MCP list/debt files.

---

### Changed File Coverage

Coverage analysis skipped — no coverage tool detected

---

### Assertion Quality

**Assertion quality**: ✅ All assertions verify real behavior

Scanned new/changed focused files. UNIQUE tests raise `IntegrityError`. Resolution tests
assert UserError text, adapter op lists, partner `vat`/`company_id`/`customer_rank`, and
binding counts. MCP partner-resolve asserts classify-before-resolve order, distinct
partners, rollback of partners/bindings, and `list_customers` call counts on replay.
`assertTrue(binding.id)` is paired with partner/identification value checks.
UniqueViolation races mock `create`/`search` but assert production UserError text and
winner `partner_id`.

---

### Quality Metrics

**Linter**: ⚠️ 0 errors, 1 optional warning (`C8101` manifest author `Eynes` on
`collection/__manifest__.py`). Mandatory pylint-odoo hook passed. Scoped pre-commit
exit 0. **Type Checker**: ➖ Not available

### Issues Found

**CRITICAL**: None

**WARNING**:

- D4: devel upgrade cannot apply SQL NOT NULL on `collection.voucher.partner_id` because
  leftover rows contain nulls. Runtime logs
  `column "partner_id" of relation "collection_voucher" contains null values` then
  `Missing not-null constraint on collection.voucher.partner_id`. Accepted design risk;
  ORM `required=True` still holds; no backfill.
- Q4: git working tree still has dirty/untracked unrelated connector, archive, and
  sqlite files outside this change's apply root. Not restaged; not a spec fail.

**SUGGESTION**:

- Optional pylint `C8101` (`manifest-required-author` must include `Eynes`);
  pre-existing convention, hook Passed.
- Concurrent first-sighting is proven by injecting `UniqueViolation` on binding
  `create`, not two live PostgreSQL sessions.
- Configured verify `build_command` is `invoke img-build`; this run used
  `invoke install -m collection` as the proportional addon load check.

### Verdict

PASS WITH WARNINGS All 13 requirements and 50 scenarios have passing covering tests;
collection 452 runtime suite is green; remaining notes are D4 missing SQL NOT NULL, Q4
unrelated dirty files, and optional lint.
