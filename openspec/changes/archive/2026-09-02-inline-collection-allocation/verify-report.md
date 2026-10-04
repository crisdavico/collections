```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:a6ec1465373baa7de021d60843422333120d8ee8cd1400293632956efcd978d8
verdict: pass
blockers: 0
critical_findings: 0
requirements: 10/10
scenarios: 31/31
test_command: invoke test -m collection --mode=update
test_exit_code: 0
test_output_hash: sha256:38f22cd9d67f4a7080b060a0df61e67e8b99b62de871e79d1a71eeeaf96b8443
build_command: pre-commit run --files odoo/custom/src/private/collection/**
build_exit_code: 0
build_output_hash: sha256:76a4aa0f2c61e2f7fb830fb39df83bf3cce52aa55473be2bac73e042ab985bf1
```

## Verification Report

**Change**: `inline-collection-allocation` **Version**: collection `19.0.1.27.0` (delta
specs `collection-allocations` + `collection-connectors` + `collection-vouchers`)
**Mode**: Strict TDD

Delta spec counts (actual `### Requirement:` / `#### Scenario:` blocks): allocations
ADDED 1/4 + MODIFIED 3/12; connectors MODIFIED 1/2; vouchers ADDED 1/2 + MODIFIED 3/11 +
REMOVED 1/0 = **10 requirements**; **31 scenarios**. Matches the authoritative totals
passed to the validator.

### Completeness

| Metric           | Value |
| ---------------- | ----- |
| Tasks total      | 32    |
| Tasks complete   | 32    |
| Tasks incomplete | 0     |

All `tasks.md` items 1.1–3.5 are `[x]`. Full spec verification proceeded.

### Build & Tests Execution

**Build**: ✅ Passed (scoped pre-commit; `invoke img-build` skipped as not this MCP-only
Python change; module upgrade ran inside the test command)

```text
pre-commit run --files odoo/custom/src/private/collection/**
exit 0
output sha256:76a4aa0f2c61e2f7fb830fb39df83bf3cce52aa55473be2bac73e042ab985bf1
ruff, prettier, OCA checks, mandatory pylint-odoo: Passed
optional pylint_odoo: C8101 manifest-required-author on __manifest__.py (author Seedian)
```

**Tests**: ✅ 520 passed / ❌ 0 failed / ⚠️ 0 skipped

```text
invoke test -m collection --mode=update
exit 0
output sha256:38f22cd9d67f4a7080b060a0df61e67e8b99b62de871e79d1a71eeeaf96b8443
odoo.tests.result: 0 failed, 0 error(s) of 520 tests when loading database 'devel'
odoo.tests.stats: collection: 576 tests 25.27s 42462 queries
```

**Coverage**: ➖ Not available — Coverage analysis skipped — no coverage tool detected

### Spec Compliance Matrix

| Requirement                                 | Scenario                                               | Test                                                                                                                                                                                                                                                                                                                                                                      | Result       |
| ------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| MCP get_collection_allocation               | Registered read tool                                   | `test_collection_mcp_allocation_lookup.py` > `test_discovered_as_method_read_mcp`                                                                                                                                                                                                                                                                                         | ✅ COMPLIANT |
| MCP get_collection_allocation               | Unbound or missing returns null                        | `test_collection_mcp_allocation_lookup.py` > `test_unbound_identification_returns_null_without_creating_partner`, `test_unknown_identification_returns_null_without_creating_partner`, `test_no_open_sheet_returns_null`, `test_closed_sheet_only_returns_null`, `test_open_sheet_without_allocation_returns_null`, `test_read_does_not_create_sheet_when_auto_create_on` | ✅ COMPLIANT |
| MCP get_collection_allocation               | Found payload and validated state                      | `test_collection_mcp_allocation_lookup.py` > `test_confirmed_payload_includes_lists_and_residual_reason`, `test_on_account_empty_invoices_still_present_as_list`, `test_validated_allocation_returned_with_stored_state`, `test_found_payload_omits_attachments_and_base64`                                                                                               | ✅ COMPLIANT |
| MCP get_collection_allocation               | Multi-open sheet and auth fail closed                  | `test_collection_mcp_allocation_lookup.py` > `test_multi_open_raises_existing_user_error`, `test_portal_and_public_callers_denied_access_error`, `test_non_enabled_seller_fails_closed`, `test_unbound_enabled_seller_fails_closed`                                                                                                                                       | ✅ COMPLIANT |
| MCP create_collection_allocation            | First create                                           | `test_collection_mcp_allocation.py` > `test_first_create_confirmed_revision_one_totals`, `test_empty_invoices_on_account`; `test_collection_allocation.py` > `test_unique_sheet_partner_rejected`                                                                                                                                                                         | ✅ COMPLIANT |
| MCP create_collection_allocation            | Authorization denied                                   | `test_collection_mcp_allocation.py` > `test_empty_payments_and_authorization_denied`                                                                                                                                                                                                                                                                                      | ✅ COMPLIANT |
| MCP create_collection_allocation            | Response shape freeze                                  | `test_collection_mcp_allocation.py` > `test_response_shape_freeze_ordered_vouchers`                                                                                                                                                                                                                                                                                       | ✅ COMPLIANT |
| MCP create_collection_allocation            | Exact document_id reuse continues                      | `test_collection_mcp_allocation.py` > `test_exact_document_id_reuse_continues_to_allocation`                                                                                                                                                                                                                                                                              | ✅ COMPLIANT |
| MCP create_collection_allocation            | Partial overlap or other-company conflict              | `test_collection_mcp_allocation.py` > `test_partial_overlap_conflict_no_writes`, `test_other_company_document_id_conflict`                                                                                                                                                                                                                                                | ✅ COMPLIANT |
| MCP create_collection_allocation            | Revalidation rolls back vouchers                       | `test_collection_mcp_allocation.py` > `test_revalidation_rolls_back_vouchers`                                                                                                                                                                                                                                                                                             | ✅ COMPLIANT |
| Input and sheet gates                       | Ineligible input rejected                              | `test_collection_mcp_allocation.py` > `test_amount_null_or_non_positive_rejected`, `test_rejected_voucher_other_company_other_sheet_mixed_rejected`, `test_unbound_reuse_and_partner_mismatch_rejected_no_create`, `test_disallowed_document_type_rejected`                                                                                                               | ✅ COMPLIANT |
| Input and sheet gates                       | Unbound write lazy-creates partner                     | `test_collection_mcp_allocation.py` > `test_unbound_write_lazy_creates_partner_and_binding`; `test_collection_mcp_partner_resolve.py` > `test_all_new_resolves_after_classify_inside_savepoint`                                                                                                                                                                           | ✅ COMPLIANT |
| Input and sheet gates                       | auto_create_sheet off fail-closed                      | `test_collection_mcp_allocation.py` > `test_auto_create_sheet_off_named_error_zero_writes`                                                                                                                                                                                                                                                                                | ✅ COMPLIANT |
| Idempotency and amend                       | Replay by request_id, content_hash, or UniqueViolation | `test_collection_mcp_allocation.py` > `test_request_id_replay_zero_writes`, `test_content_hash_replay_new_request_id_no_extra_revision`, `test_unique_violation_same_company_replays`, `test_unique_violation_hidden_other_company_generic_no_ids`                                                                                                                        | ✅ COMPLIANT |
| Idempotency and amend                       | Amend voucher superset or overlap                      | `test_collection_mcp_allocation.py` > `test_amend_superset_bumps_revision`, `test_subset_and_partial_overlap_rejected`, `test_destination_not_confirmed_refuses_amend`                                                                                                                                                                                                    | ✅ COMPLIANT |
| Idempotency and amend                       | Residual reason participates in content_hash           | `test_collection_mcp_allocation.py` > `test_reason_only_retry_not_noop_hash_includes_reason`                                                                                                                                                                                                                                                                              | ✅ COMPLIANT |
| Write path may create partners and bindings | Write path provisions on all-new create                | `test_collection_mcp_allocation.py` > `test_unbound_write_lazy_creates_partner_and_binding`; `test_collection_mcp_allocation_lookup.py` > `test_unbound_identification_returns_null_without_creating_partner`; `test_collection_mcp_customer_list.py` / `test_collection_mcp_customer_debt.py` read tools (suite passed; no `resolve_customer_partner`)                   | ✅ COMPLIANT |
| Write path may create partners and bindings | Get unbound does not provision                         | `test_collection_mcp_allocation_lookup.py` > `test_unbound_identification_returns_null_without_creating_partner`, `test_unknown_identification_returns_null_without_creating_partner`                                                                                                                                                                                     | ✅ COMPLIANT |
| Internal collection payment helpers         | Helpers not discovered as MCP tools                    | `test_collection_mcp_allocation.py` > `test_create_collection_vouchers_absent_from_mcp_registry`                                                                                                                                                                                                                                                                          | ✅ COMPLIANT |
| Internal collection payment helpers         | Allocation reuses helpers                              | `test_collection_mcp_allocation.py` > `test_payment_schema_and_parse_replicate_top_level_identification`, `test_discovered_as_method_write_mcp`                                                                                                                                                                                                                           | ✅ COMPLIANT |
| MCP optional payment attachment on create   | MCP create with nested attachment                      | `test_collection_mcp_tool.py` > `test_create_with_valid_png_nest_becomes_chatter_proof`, `test_create_with_valid_pdf_nest_persists`                                                                                                                                                                                                                                       | ✅ COMPLIANT |
| MCP optional payment attachment on create   | MCP attachment MIME mismatch rejected                  | `test_collection_mcp_tool.py` > `test_create_mime_mismatch_rejects_no_writes`, `test_create_text_mime_rejects_no_writes`, `test_create_bad_base64_rejects_no_writes`                                                                                                                                                                                                      | ✅ COMPLIANT |
| MCP optional payment attachment on create   | Exact-retry skips attachment writes                    | `test_collection_mcp_tool.py` > `test_exact_retry_with_nest_does_not_replace_attachment`, `test_exact_retry_with_nest_does_not_add_when_voucher_has_none`, `test_exact_retry_without_nest_leaves_existing_attachment`                                                                                                                                                     | ✅ COMPLIANT |
| MCP nested provenance on all-new create     | Unchanged seller confirmation                          | `test_collection_mcp_tool.py` > `test_unchanged_seller_stamps_all_three_layers_equal`                                                                                                                                                                                                                                                                                     | ✅ COMPLIANT |
| MCP nested provenance on all-new create     | Seller correction                                      | `test_collection_mcp_tool.py` > `test_seller_correction_keeps_raw_and_aligns_current`                                                                                                                                                                                                                                                                                     | ✅ COMPLIANT |
| MCP nested provenance on all-new create     | Both nests omitted leave empty provenance              | `test_collection_mcp_tool.py` > `test_omitted_nests_leave_null_provenance`, `test_orm_create_without_nests_leaves_null_provenance`                                                                                                                                                                                                                                        | ✅ COMPLIANT |
| MCP nested provenance on all-new create     | Bad provenance fails the batch                         | `test_collection_mcp_tool.py` > `test_one_sided_nests_reject_with_no_writes`, `test_malformed_and_mismatch_nests_reject_with_no_writes`, `test_batch_one_sided_second_payment_writes_nothing`                                                                                                                                                                             | ✅ COMPLIANT |
| MCP nested provenance on all-new create     | Exact replay ignores provenance nests                  | `test_collection_mcp_tool.py` > `test_exact_replay_ignores_different_and_omitted_nests`, `test_exact_replay_ignores_malformed_nests`                                                                                                                                                                                                                                      | ✅ COMPLIANT |
| Cross-company document_id reject not replay | Global uniqueness still holds                          | `test_collection_payment.py` > `test_duplicate_non_null_document_id_raises_integrity_error`                                                                                                                                                                                                                                                                               | ✅ COMPLIANT |
| Cross-company document_id reject not replay | Other-company collision undisclosed                    | `test_collection_mcp_allocation.py` > `test_other_company_document_id_conflict`                                                                                                                                                                                                                                                                                           | ✅ COMPLIANT |
| Cross-company document_id reject not replay | Multi-company reader must not replay the other company | `test_collection_mcp_allocation.py` > `test_other_company_document_id_conflict`, `test_unique_violation_hidden_other_company_generic_no_ids`                                                                                                                                                                                                                              | ✅ COMPLIANT |

**Compliance summary**: 31/31 scenarios compliant

REMOVED requirement `MCP tool create_collection_vouchers` has no Given/When/Then
scenarios; retirement is proven by
`test_create_collection_vouchers_absent_from_mcp_registry` (same covering test as
Internal helpers).

### Correctness (Static Evidence)

| Requirement                                   | Status         | Notes                                                                                                                                                                                                        |
| --------------------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| MCP get_collection_allocation                 | ✅ Implemented | `tools/allocation_lookup.py` `@mcp_tool` category=read; `_open_sheets_for_seller`; binding-only search; `{allocation: null}`; no `sudo()` / `resolve_customer_partner` / `_resolve_open_sheet_id_for_create` |
| MCP create_collection_allocation              | ✅ Implemented | Schema required `{seller_id, customer_identification, request_id, payments, invoices}`; payload `{sheet_id, vouchers, allocation}` seven alloc keys; classify None→create / dict→continue                    |
| Input and sheet gates                         | ✅ Implemented | Fail-closed `auto_create_sheet` named UserError before write; lazy create via `_collection_create_vouchers`; identity assert `_collection_allocation_bound_partner`                                          |
| Idempotency and amend                         | ✅ Implemented | `request_id` replay returns full payload; `content_hash` includes `residual_reason`; SUPERSET amend; UniqueViolation invalidate then replay/conflict                                                         |
| Write path may create partners and bindings   | ✅ Implemented | Write uses `_collection_create_vouchers` / `resolve_customer_partner`; get/list/debt do not                                                                                                                  |
| Internal collection payment helpers           | ✅ Implemented | `_collection_*` remain on mixin; `_PAYMENT_SCHEMA` omits ident; parse replicates top-level ident; no `@mcp_tool` on helpers or `create_collection_vouchers`                                                  |
| MCP optional payment attachment on create     | ✅ Implemented | Nests parsed only when classify is None; exact reuse continues to allocation without attachment mutate                                                                                                       |
| MCP nested provenance on all-new create       | ✅ Implemented | Same nest parsers reused on fused write; exact reuse ignores nests                                                                                                                                           |
| Cross-company document_id reject not replay   | ✅ Implemented | Global UNIQUE; classify/UniqueViolation map to generic conflict with no ids                                                                                                                                  |
| MCP tool create_collection_vouchers (REMOVED) | ✅ Implemented | Decorated method+schema dropped; helpers kept; registry absence asserted                                                                                                                                     |

### Coherence (Design)

| Decision                                       | Followed? | Notes                                                                                                                                                                                                      |
| ---------------------------------------------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| No extra savepoint layer                       | ✅ Yes    | Existing persist savepoint expanded to cover voucher create + revalidate + persist (apply-progress). Nested binding savepoints remain. Spec rollback still holds (`test_revalidation_rolls_back_vouchers`) |
| Classify then continue on exact set            | ✅ Yes    | `_collection_classify_visible`: None→create; raise→stop; dict→keep and continue                                                                                                                            |
| Lazy resolve via `_collection_create_vouchers` | ✅ Yes    | Bound-partner is identity assert after create                                                                                                                                                              |
| Read via `_open_sheets_for_seller`             | ✅ Yes    | Get never calls `_resolve_open_sheet_id_for_create`                                                                                                                                                        |
| Hash includes `residual_reason`                | ✅ Yes    | `_collection_allocation_content_hash` payload key                                                                                                                                                          |
| Retire voucher `@mcp_tool` in unit 3           | ✅ Yes    | Method gone; `tools/__init__.py` still imports helpers module                                                                                                                                              |
| Manifest `19.0.1.27.0`; no migrate folder      | ✅ Yes    | `test_manifest_version_is_1_27_0`; no `migrations/19.0.1.27.0/`                                                                                                                                            |
| Errors raised, never error-as-body             | ✅ Yes    | Source scans omit `{"error"`; UserError/AccessError                                                                                                                                                        |
| Invert tests before GREEN                      | ✅ Yes    | apply-progress RED then GREEN for Phases 1–3                                                                                                                                                               |

Apply-progress deviations (expanded persist savepoint; hidden other-company via
UniqueViolation; key-walk media assertion; deleted mixed-customer and
UniqueViolation-invalid-nest wrap) match the fused contract and do not change remaining
spec outcomes.

### Issues Found

**CRITICAL**: None **WARNING**: None **SUGGESTION**:

- Optional pylint `C8101` (`manifest-required-author`, author `Seedian`) on
  `__manifest__.py`; mandatory pylint hook still Passed.
- Pre-existing duplicate OCR/seller field-label warnings on `collection.voucher` during
  registry load (tests).
- Odoo stats line reports `576 tests` while `odoo.tests.result` reports `520` loaded
  tests; envelope uses the result line (same convention as archived verify).
- Coordinated Nebula deploy remains a product risk after retiring
  `create_collection_vouchers` (proposal; out of this addon scope).
- Task 1.2 recorded Safety Net `N/A (rewrite)` for the rewritten allocation MCP test
  file; RED/GREEN evidence still exists.

### Verdict

PASS All 10 requirements and 31 scenarios have covering tests that started and passed in
this run; design decisions match the implementation.

### TDD Compliance

| Check                         | Result | Details                                                                                                                                                                                                                 |
| ----------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TDD Evidence reported         | ✅     | TDD Cycle Evidence table in `apply-progress.md` for tasks 1.1–3.5                                                                                                                                                       |
| All tasks have tests          | ✅     | 28/32 implementation tasks have named tests; 1.15/2.12/3.5 are module Test+Lint; 3.3 is AGENTS.md                                                                                                                       |
| RED confirmed (tests exist)   | ✅     | Named methods exist in `test_collection_mcp_allocation.py`, `test_collection_mcp_allocation_lookup.py`, `test_collection_mcp_tool.py`, `test_collection_mcp_partner_resolve.py`, `test_collection_company_migration.py` |
| GREEN confirmed (tests pass)  | ✅     | This run: 0 failed, 0 error(s) of 520 tests                                                                                                                                                                             |
| Triangulation adequate        | ✅     | Write/read/attachment/provenance triangulated; 3.3 docs and 3.4 version constant Single                                                                                                                                 |
| Safety Net for modified files | ⚠️     | Most tasks recorded existing suites; 1.2 `N/A (rewrite)` on existing `test_collection_mcp_allocation.py`; 2.1 `N/A (new)` for lookup files is correct                                                                   |

**TDD Compliance**: 5/6 checks passed (safety net warning on rewrite N/A)

---

### Test Layer Distribution

| Layer       | Tests  | Files | Tools                                                                                                                                                                                       |
| ----------- | ------ | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Unit        | 10     | 4     | Discovery/source/schema/manifest (`test_collection_mcp_allocation.py`, `test_collection_mcp_allocation_lookup.py`, `test_collection_mcp_tool.py`, `test_collection_company_migration.py`)   |
| Integration | 75     | 4     | Odoo TransactionCase MCP `_call` (`test_collection_mcp_allocation.py`, `test_collection_mcp_allocation_lookup.py`, `test_collection_mcp_tool.py`, `test_collection_mcp_partner_resolve.py`) |
| E2E         | 0      | 0     | not installed                                                                                                                                                                               |
| **Total**   | **85** | **5** | focused tests created/rewritten for this change                                                                                                                                             |

Envelope run also executed the full collection module suite (520). Cross-company
uniqueness reuses `test_collection_payment.py`. UNIQUE(sheet, partner) reuses
`test_collection_allocation.py`.

---

### Changed File Coverage

Coverage analysis skipped — no coverage tool detected

---

### Assertion Quality

**Assertion quality**: ✅ All assertions verify real behavior

Scanned changed tests in `tests/test_collection_mcp_allocation.py`,
`tests/test_collection_mcp_allocation_lookup.py`, `tests/test_collection_mcp_tool.py`,
`tests/test_collection_mcp_partner_resolve.py`, and
`tests/test_collection_company_migration.py`. Write tests call
`create_collection_allocation` and assert payload keys, revision ints, counts, UserError
strings, and rollback. Read tests call `get_collection_allocation` and assert null vs
found keys, zero writes, and AccessError. Attachment/provenance tests persist chatter
proof or reject with no writes. Registry tests assert tool presence/absence and helper
callability. Media-key walk is preceded by non-empty vouchers/invoices so the walk runs.
Helper-name loop is over a fixed non-empty tuple. No tautologies, ghost loops, or
production-code-free assertions.

---

### Quality Metrics

**Linter**: ✅ No errors on owned files (scoped pre-commit exit 0). Optional glob
`C8101` on `__manifest__.py` is pre-existing. **Type Checker**: ➖ Not available
