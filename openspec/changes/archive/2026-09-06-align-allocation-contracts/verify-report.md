```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:1fc4b80603f478f14e010c11d85b156789b7de4c97ea2569f3d3aa5a39c98072
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 9/9
scenarios: 44/44
test_command:
  docker exec -i seedian-odoo-1 odoo -d devel -u collection --test-enable
  --stop-after-init --workers=0 --http-port=18069 --gevent-port=18072 --log-level=test
  --test-tags /collection
test_exit_code: 0
test_output_hash: sha256:1fc4b80603f478f14e010c11d85b156789b7de4c97ea2569f3d3aa5a39c98072
build_command:
  docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init
  --workers=0 --http-port=18069 --gevent-port=18072
build_exit_code: 0
build_output_hash: sha256:c159accd83297f67ff4374c93176cad36958baf285a3cfdf64d816c067f84e98
```

## Verification Report

**Change**: align-allocation-contracts **Version**: 19.0.1.40.0 **Mode**: Strict TDD

### Completeness

| Metric           | Value |
| ---------------- | ----- |
| Tasks total      | 21    |
| Tasks complete   | 21    |
| Tasks incomplete | 0     |

Counted from delta specs (`### Requirement:` / `#### Scenario:`): **9 requirements**,
**44 scenarios** (collection-vouchers 6/28 + collection-allocations 3/16).

### Build & Tests Execution

**Build**: ✅ Passed (exit 0)

```text
docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --workers=0 --http-port=18069 --gevent-port=18072
Modules loaded. Registry loaded. Shutdown. Hash sha256:c159accd83297f67ff4374c93176cad36958baf285a3cfdf64d816c067f84e98
```

**Tests**: ✅ 779 passed / 0 failed / 0 error(s)

```text
docker exec -i seedian-odoo-1 odoo -d devel -u collection --test-enable --stop-after-init --workers=0 --http-port=18069 --gevent-port=18072 --log-level=test --test-tags /collection
Exit 0. Hash sha256:1fc4b80603f478f14e010c11d85b156789b7de4c97ea2569f3d3aa5a39c98072
odoo.tests.result: 0 failed, 0 error(s) of 779 tests when loading database 'devel'
Covering tests started and completed without FAIL/ERROR, including TestCollectionDocumentReview.test_queue_includes_readonly_provenance_without_fabricating.
Sibling collection_receipt_proposal FIFO / document_numbers tests were not in this envelope.
```

Consumer regressions (not envelope `test_command`): from
`/home/crisd/projects/nebula/nebula-agent`, `uv run make test` → 506 passed (exit 0);
`uv run make integration_tests` → 24 passed (exit 0).

**Coverage**: ➖ Not available / threshold: 0% → ➖ Not available (openspec
`coverage_threshold: 0`; no coverage tool)

### Spec Compliance Matrix

| Requirement                                     | Scenario                                           | Test                                                                                                     | Result       |
| ----------------------------------------------- | -------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ------------ |
| Catalog XMLIDs and 19.0.1.40.0 allow-list union | Seven catalog XMLIDs exist                         | `tests/test_collection_company_settings.py` > `test_catalog_xmlids_exist_with_expected_codes`            | ✅ COMPLIANT |
| Catalog XMLIDs and 19.0.1.40.0 allow-list union | Upgrade unions without dropping extras             | `tests/test_collection_company_migration.py` > `test_upgrade_140_unions_three_types_keeps_extras`        | ✅ COMPLIANT |
| Catalog XMLIDs and 19.0.1.40.0 allow-list union | New company starts with seven types                | `tests/test_collection_company_settings.py` > `test_new_company_enables_all_seven_document_types`        | ✅ COMPLIANT |
| Payment field contract                          | Persist type-specific fields                       | `tests/test_collection_voucher.py` > `test_persist_type_specific_collection_fields`                      | ✅ COMPLIANT |
| Payment field contract                          | Unsupported and partial entry                      | `tests/test_collection_voucher.py` > `test_unsupported_and_partial_payment_fields`                       | ✅ COMPLIANT |
| Payment field contract                          | Persist echeck cash and retention_certificate      | `tests/test_collection_voucher.py` > `test_persist_echeck_cash_and_retention_certificate`                | ✅ COMPLIANT |
| Payment field contract                          | Cash persists without proof                        | `tests/test_collection_voucher.py` > `test_cash_persists_without_proof`                                  | ✅ COMPLIANT |
| MCP optional payment attachment on create       | MCP create with nested attachment                  | `tests/test_collection_mcp_tool.py` > `test_create_with_valid_png_nest_becomes_chatter_proof`            | ✅ COMPLIANT |
| MCP optional payment attachment on create       | MCP attachment MIME mismatch rejected              | `tests/test_collection_mcp_tool.py` > `test_create_mime_mismatch_rejects_no_writes`                      | ✅ COMPLIANT |
| MCP optional payment attachment on create       | Exact-retry skips attachment writes                | `tests/test_collection_mcp_tool.py` > `test_exact_retry_with_nest_does_not_replace_attachment`           | ✅ COMPLIANT |
| MCP optional payment attachment on create       | image/jpg aliases to jpeg                          | `tests/test_collection_mcp_tool.py` > `test_image_jpg_aliases_to_jpeg`                                   | ✅ COMPLIANT |
| MCP optional payment attachment on create       | Cash attachment null or omit is valid              | `tests/test_collection_mcp_tool.py` > `test_cash_omit_and_null_attachment_raw_ocr`                       | ✅ COMPLIANT |
| Typed provenance copies of payment fields       | Identity and proof stay outside provenance         | `tests/test_collection_mcp_tool.py` > `test_omitted_nests_with_attachment_keep_base64_out_of_provenance` | ✅ COMPLIANT |
| Typed provenance copies of payment fields       | Cash-deposit extra keys stored in all layers       | `tests/test_collection_mcp_tool.py` > `test_cash_deposit_stores_voucher_number_and_date_in_all_layers`   | ✅ COMPLIANT |
| Typed provenance copies of payment fields       | Voucher write rejects provenance keys              | `tests/test_collection_voucher.py` > `test_write_rejects_ocr_and_seller_keys`                            | ✅ COMPLIANT |
| Typed provenance copies of payment fields       | retention_kind stamps all three layers             | `tests/test_collection_mcp_tool.py` > `test_retention_kind_stamps_current_seller_and_ocr_layers`         | ✅ COMPLIANT |
| MCP nested provenance on all-new create         | Unchanged seller confirmation                      | `tests/test_collection_mcp_tool.py` > `test_unchanged_seller_stamps_all_three_layers_equal`              | ✅ COMPLIANT |
| MCP nested provenance on all-new create         | Seller correction with optional raw                | `tests/test_collection_mcp_tool.py` > `test_seller_correction_keeps_raw_and_aligns_current`              | ✅ COMPLIANT |
| MCP nested provenance on all-new create         | Seller-only nest stamps seller fields              | `tests/test_collection_mcp_allocation.py` > `test_seller_confirmed_optional_raw_ocr_stamps`              | ✅ COMPLIANT |
| MCP nested provenance on all-new create         | UI create without nests leaves empty provenance    | `tests/test_collection_mcp_tool.py` > `test_orm_create_without_nests_leaves_null_provenance`             | ✅ COMPLIANT |
| MCP nested provenance on all-new create         | Bad provenance fails the batch                     | `tests/test_collection_mcp_tool.py` > `test_one_sided_nests_reject_with_no_writes`                       | ✅ COMPLIANT |
| MCP nested provenance on all-new create         | Exact replay ignores provenance nests              | `tests/test_collection_mcp_tool.py` > `test_exact_replay_ignores_different_and_omitted_nests`            | ✅ COMPLIANT |
| MCP nested provenance on all-new create         | Cash dump without raw_ocr                          | `tests/test_collection_mcp_tool.py` > `test_cash_omit_and_null_attachment_raw_ocr`                       | ✅ COMPLIANT |
| MCP nested provenance on all-new create         | Explicit null optional nest fields are omit        | `tests/test_collection_mcp_tool.py` > `test_json_null_optional_nest_fields_are_omit`                     | ✅ COMPLIANT |
| Collection Settings persistence                 | Collection Settings labels                         | `tests/test_collection_ui.py` > `test_configuration_settings_menu_and_action`                            | ✅ COMPLIANT |
| Collection Settings persistence                 | Empty enabled sellers means none for new work      | `tests/test_collection_voucher.py` > `test_empty_enabled_sellers_rejects_voucher_create`                 | ✅ COMPLIANT |
| Collection Settings persistence                 | Defaults enable auto-create and all seven types    | `tests/test_collection_company_settings.py` > `test_env_company_allows_all_seven_document_types`         | ✅ COMPLIANT |
| Collection Settings persistence                 | Unsupported is configurable                        | `tests/test_collection_company_settings.py` > `test_unsupported_can_be_disabled_independently`           | ✅ COMPLIANT |
| Strict nested-key parse of dump payloads        | Unknown key on payment or request rejected         | `tests/test_collection_mcp_allocation.py` > `test_extra_keys_on_request_payment_receipt_value_rejected`  | ✅ COMPLIANT |
| Strict nested-key parse of dump payloads        | Unknown key on nested receipt objects rejected     | `tests/test_collection_mcp_tool.py` > `test_extra_keys_on_nests_rejected`                                | ✅ COMPLIANT |
| Strict nested-key parse of dump payloads        | Type-foreign nest fields rejected                  | `tests/test_collection_mcp_tool.py` > `test_type_foreign_nest_fields_rejected`                           | ✅ COMPLIANT |
| Strict nested-key parse of dump payloads        | Explicit nulls accepted as omit                    | `tests/test_collection_mcp_tool.py` > `test_json_null_optional_nest_fields_are_omit`                     | ✅ COMPLIANT |
| MCP create_collection_allocation                | First create                                       | `tests/test_collection_mcp_allocation.py` > `test_first_create_draft_revision_one_totals`                | ✅ COMPLIANT |
| MCP create_collection_allocation                | Authorization denied                               | `tests/test_collection_mcp_allocation.py` > `test_empty_payments_and_authorization_denied`               | ✅ COMPLIANT |
| MCP create_collection_allocation                | Response shape freeze                              | `tests/test_collection_mcp_allocation.py` > `test_response_shape_freeze_ordered_vouchers`                | ✅ COMPLIANT |
| MCP create_collection_allocation                | Exact document_id reuse continues                  | `tests/test_collection_mcp_allocation.py` > `test_exact_document_id_reuse_continues_to_allocation`       | ✅ COMPLIANT |
| MCP create_collection_allocation                | Partial overlap or other-company conflict          | `tests/test_collection_mcp_allocation.py` > `test_partial_overlap_conflict_no_writes`                    | ✅ COMPLIANT |
| MCP create_collection_allocation                | Revalidation rolls back vouchers                   | `tests/test_collection_mcp_allocation.py` > `test_revalidation_rolls_back_vouchers`                      | ✅ COMPLIANT |
| MCP create_collection_allocation                | Unsupported payment write rejected                 | `tests/test_collection_mcp_allocation.py` > `test_unsupported_dump_raises_with_zero_writes`              | ✅ COMPLIANT |
| MCP create_collection_allocation                | Six dump types persist with decimal-string amounts | `tests/test_collection_mcp_allocation.py` > `test_six_dump_types_persist_draft_with_decimal_strings`     | ✅ COMPLIANT |
| MCP receipts payload                            | Split one voucher two kinds                        | `tests/test_collection_mcp_allocation.py` > `test_split_values_land_on_matching_receipts`                | ✅ COMPLIANT |
| MCP receipts payload                            | Empty applications is on account                   | `tests/test_collection_mcp_allocation.py` > `test_empty_applications_on_account`                         | ✅ COMPLIANT |
| MCP receipts payload                            | Over-split refused                                 | `tests/test_collection_mcp_allocation.py` > `test_applications_exceeding_funded_values_refused`          | ⚠️ PARTIAL   |
| MCP receipts payload                            | Decimal-string receipt amounts persist             | `tests/test_collection_mcp_allocation.py` > `test_decimal_string_receipt_amounts_persist`                | ✅ COMPLIANT |

**Compliance summary**: 43/44 COMPLIANT + 1 PARTIAL (envelope 44/44 covered; PARTIAL
still has a passing covering test)

### Correctness (Static Evidence)

| Requirement                                     | Status                | Notes                                                                                                                                |
| ----------------------------------------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Catalog XMLIDs and 19.0.1.40.0 allow-list union | ✅ Implemented        | Seven XMLIDs; `migrations/19.0.1.40.0/post-migrate.py` unions via `_collection_enable_all_document_types()`                          |
| Payment field contract                          | ✅ Implemented        | Seven-type Selection; `retention_kind`; ORM persist including cash without proof                                                     |
| MCP optional payment attachment on create       | ✅ Implemented        | MIME `image/jpg`↔`image/jpeg` alias; cash omit/null proof                                                                            |
| Typed provenance copies of payment fields       | ✅ Implemented        | `retention_kind` on current/ocr/seller; Document Review queue now fills current keys from `_REVIEW_EDITABLE_FIELD_ORDER`             |
| MCP nested provenance on all-new create         | ✅ Implemented        | Seven-type nests; decimal strings; cash without raw_ocr; exact replay ignores nests                                                  |
| Collection Settings persistence                 | ✅ Implemented        | Seven-type allow-list defaults; empty sellers still reject new work                                                                  |
| Strict nested-key parse of dump payloads        | ✅ Implemented        | extra=forbid on request/payment/receipt/value/application/nests                                                                      |
| MCP create_collection_allocation                | ✅ Implemented        | Six dump types persist draft; `unsupported` zero writes; replay/response unchanged                                                   |
| MCP receipts payload                            | ⚠️ Partial test cover | Decimal strings and empty applications covered; values-sum≠payment (50 vs 51) has no dedicated GREEN test; applied>funded is covered |

### Coherence (Design)

| Decision                                          | Followed?       | Notes                                                                                                       |
| ------------------------------------------------- | --------------- | ----------------------------------------------------------------------------------------------------------- |
| Runtime-strict flattened contract (not MuK oneOf) | ✅ Yes          | Shared maps in `tools/collection_voucher.py`; Python extra=forbid                                           |
| Catalog 7 + `retention_kind` + 19.0.1.40.0 union  | ✅ Yes          | XMLIDs, Selection, migrate folder present                                                                   |
| OWL/views/reports unchanged                       | ✅ Yes          | Remediating slice changed `_review_queue_payload` Python only; no OWL/view/report edits                     |
| Amount schema `anyOf` number\|string              | ⚠️ Runtime only | Apply-progress: advertised schema stays MuK-safe `"number"`; `_collection_normalize_amount` accepts strings |
| MCP `unsupported` still UserError, zero writes    | ✅ Yes          | `test_unsupported_dump_raises_with_zero_writes` passed                                                      |
| No nebula-agent `src/agent/**` / schema edits     | ✅ Yes          | Phase 4 edited nebula `AGENTS.md` catalog note only                                                         |

### TDD Compliance

| Check                         | Result | Details                                                                                                                                                                                   |
| ----------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TDD Evidence reported         | ✅     | Found in apply-progress TDD Cycle Evidence table plus remediating queue-payload row                                                                                                       |
| All tasks have tests          | ✅     | 21/21 implementation tasks share Phase 1 goldens; docs 4.1–4.4 have AGENTS/README pins                                                                                                    |
| RED confirmed (tests exist)   | ✅     | Listed test files exist under `tests/` including `test_collection_document_review.py`                                                                                                     |
| GREEN confirmed (tests pass)  | ✅     | Envelope `/collection` is `0 failed, 0 error(s) of 779 tests`; remediating queue test started and the suite stayed green                                                                  |
| Triangulation adequate        | ✅     | 1.1–1.6 report multi-case (xmlids/count/company; six types + unsupported; jpg vs jpeg; omit vs null; extra keys at every nest); remediating notes empty-vs-populated queue covering tests |
| Safety Net for modified files | ✅     | Remediating slice re-ran the focused Document Review queue test before the production edit; this verify re-ran `/collection` after that settlement                                        |

**TDD Compliance**: 6/6 checks passed

Apply-progress TDD Cycle Evidence (Phases 1–3) plus remediating queue-payload row:

| Task                   | Test File                                    | RED                                            | GREEN                                         | TRIANGULATE                                                   |
| ---------------------- | -------------------------------------------- | ---------------------------------------------- | --------------------------------------------- | ------------------------------------------------------------- |
| 1.1                    | `tests/test_collection_company_settings.py`  | ✅ Written                                     | ✅ Passed this verify                         | ✅ xmlids + count + new company                               |
| 1.2                    | `tests/test_collection_company_migration.py` | ✅ Written                                     | ✅ Passed this verify                         | ✅ version + migrate file + extras                            |
| 1.3                    | `tests/test_collection_voucher.py`           | ✅ Written                                     | ✅ Passed this verify                         | ✅ three types + cash no proof                                |
| 1.4                    | `tests/test_collection_mcp_allocation.py`    | ✅ Written                                     | ✅ Passed this verify                         | ✅ six types + unsupported zero writes                        |
| 1.5                    | `tests/test_collection_mcp_tool.py`          | ✅ Written                                     | ✅ Passed this verify                         | ✅ jpg vs jpeg; omit vs null                                  |
| 1.6                    | MCP test modules                             | ✅ Written                                     | ✅ Passed this verify                         | ✅ request/payment/receipt/value/app/nests                    |
| 2.1–2.6                | catalog/migrate                              | ✅ Phase 1                                     | ✅ Passed this verify                         | ➖ Phase 1 cases                                              |
| 3.1–3.3                | parser/schema goldens                        | ✅ Phase 1                                     | ✅ Passed this verify                         | ✅ seven types + extra/type-foreign                           |
| Queue `retention_kind` | `tests/test_collection_document_review.py`   | ✅ Written (`KeyError: 'retention_kind'` then) | ✅ Passed this verify (`/collection` 779/779) | ✅ empty provenance vs populated plus check/cash-deposit keys |

---

### Test Layer Distribution

| Layer       | Tests                         | Files                                                               | Tools                      |
| ----------- | ----------------------------- | ------------------------------------------------------------------- | -------------------------- |
| Unit        | 506 (nebula consumer)         | `tests/unit_tests/`                                                 | pytest                     |
| Integration | 779 `/collection` + 24 nebula | Odoo `TransactionCase` in Docker; nebula `tests/integration_tests/` | Odoo native runner; pytest |
| E2E         | 0                             | 0                                                                   | not installed              |
| **Total**   | **1309 counted surfaces**     |                                                                     |                            |

Change goldens themselves are Integration (containerized Odoo + PostgreSQL).

---

### Changed File Coverage

Coverage analysis skipped — no coverage tool detected

---

### Assertion Quality

**Assertion quality**: ✅ All assertions verify real behavior

Scanned goldens in `test_collection_mcp_allocation.py`, `test_collection_mcp_tool.py`,
`test_collection_voucher.py`, `test_collection_company_settings.py`,
`test_collection_company_migration.py`, and remediating `assertIn(name, payload, name)`
in `test_collection_document_review.py`: persist/UserError/zero-write/catalog/queue-key
asserts; no tautologies, no orphan empty-only checks, no ghost loops.

---

### Quality Metrics

**Linter**: ➖ Not re-run this verify (apply Phase 3.5, 4.4, and remediating slice
recorded scoped pre-commit / focused GREEN) **Type Checker**: ➖ Not available

### Issues Found

**CRITICAL**: None

**WARNING**:

1. Scenario "Over-split refused" is PARTIAL:
   `test_applications_exceeding_funded_values_refused` covers applied > funded (payment
   10 / applied 100), not the spec GIVEN of payment 50 with receipt values summing to 51
   (full-split equality in `_collection_parse_allocation_receipts`).
2. Design advertised amount `anyOf` number|string; discovery schema remains
   `"type": "number"` (documented MuK `to_strict_schema` strip).

**SUGGESTION**:

1. Add a dedicated GOLDEN for payment amount 50 vs values summing to 51 if full-split
   over-split should be independently triangulated.

### Verdict

PASS WITH WARNINGS Envelope `/collection` tests exited 0 (779/779) after the Document
Review queue-payload settlement. All 9 requirements and 44 scenarios have passing
covering tests; Over-split remains PARTIAL (applied>funded, not 50/51 values). Nebula
consumer tests passed. Ready for archive.
