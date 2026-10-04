```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:859e001c29fb0591dcb677f106c64fcda93e0b6f412c1dd34dd5d97eb4c6d45f
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 11/11
scenarios: 26/26
test_command: invoke test -m collection --mode=update
test_exit_code: 0
test_output_hash: sha256:b185d03ade7553989d9e13c1cd21e177c3da6dcbe1cfb51393e639956fb96607
build_command: pre-commit run --files odoo/custom/src/private/collection/**
build_exit_code: 0
build_output_hash: sha256:c6766937534f3e41b1d49ddf2b3217d50787659a5b22654d2eae25cc4f4dde6c
```

## Verification Report

**Change**: `collection-sheet-report` **Version**: collection `19.0.1.30.0` (delta specs
`collection-sheet-report` + `collection-allocations` ADDED) **Mode**: Strict TDD

Delta spec counts (actual `### Requirement:` / `#### Scenario:` blocks): report spec 10
requirements / 21 scenarios; allocations ADDED 1 requirement / 5 scenarios = **11
requirements**; **26 scenarios**. Matches the authoritative totals passed to the
validator.

### Completeness

| Metric           | Value |
| ---------------- | ----- |
| Tasks total      | 10    |
| Tasks complete   | 10    |
| Tasks incomplete | 0     |

All `tasks.md` items 1.1–4.2 are `[x]`. Full spec verification proceeded.

### Build & Tests Execution

**Build**: ✅ Passed (scoped pre-commit; `invoke img-build` skipped — no new Python/apt
deps; module upgrade ran inside the test command)

```text
pre-commit run --files odoo/custom/src/private/collection/**
exit 0
output sha256:c6766937534f3e41b1d49ddf2b3217d50787659a5b22654d2eae25cc4f4dde6c
ruff, prettier, OCA checks, mandatory pylint-odoo: Passed
optional pylint_odoo: C8101 manifest-required-author on __manifest__.py (author Seedian)
```

**Tests**: ✅ 597 passed / ❌ 0 failed / ⚠️ 0 skipped

```text
invoke test -m collection --mode=update
exit 0
output sha256:b185d03ade7553989d9e13c1cd21e177c3da6dcbe1cfb51393e639956fb96607
odoo.tests.result: 0 failed, 0 error(s) of 597 tests when loading database 'devel'
odoo.tests.stats: collection: 661 tests 31.31s 50937 queries
```

Invoke `-d` is `--debugpy`, not a database name. The gate therefore ran
`invoke test -m collection --mode=update` (same command as the archived sibling report).
Compose `db_filter` already defaults to `^devel$`. Prompt `-d devel` was not passed so a
debugpy session was not started. Live `seedian-odoo-1` on container 8069 was not killed;
`docker compose run --rm` did not bind host 8069.

Covering tests for this change all started in this run: 5 document-kind, 17 payload, 6
QWeb HTML, 12 XLSX, plus `test_manifest_version_is_1_30_0`.

**Coverage**: ➖ Not available — Coverage analysis skipped — no coverage tool detected

Optional smoke: `_render_qweb_html` and XLSX `PK`/zip are already asserted in
TransactionCase. `_render_qweb_pdf` (wkhtmltopdf) and browser Print menu were not
exercised (no cheap odoo-shell PDF; no working browser session).

### Spec Compliance Matrix

| Requirement                        | Scenario                                 | Test                                                                                                                                                                                                                                                                                                         | Result       |
| ---------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------ |
| Sheet reconciliation inputs        | Percent range                            | `test_collection_sheet_report_data.py` > `test_percent_range_persists_bounds`, `test_percent_outside_range_raises`                                                                                                                                                                                           | ✅ COMPLIANT |
| Sheet reconciliation inputs        | Closed write guard                       | `test_collection_sheet_report_data.py` > `test_closed_write_guard`                                                                                                                                                                                                                                           | ✅ COMPLIANT |
| Sheet reconciliation inputs        | Open edit then reopen keeps values       | `test_collection_sheet_report_data.py` > `test_reopen_keeps_recon_values`                                                                                                                                                                                                                                    | ✅ COMPLIANT |
| Shared report payload              | Primitive nested values                  | `test_collection_sheet_report_data.py` > `test_payload_keys_and_primitives`                                                                                                                                                                                                                                  | ✅ COMPLIANT |
| Shared report payload              | Open sheet prints drafts                 | `test_collection_sheet_report_data.py` > `test_open_sheet_prints_drafts`                                                                                                                                                                                                                                     | ✅ COMPLIANT |
| Customer codes and sort            | Binding code vs blank last               | `test_collection_sheet_report_data.py` > `test_binding_code_vs_blank_last`                                                                                                                                                                                                                                   | ✅ COMPLIANT |
| Document blocks and commission     | Kind split drops empty                   | `test_collection_sheet_report_data.py` > `test_kind_split_drops_empty`                                                                                                                                                                                                                                       | ✅ COMPLIANT |
| Document blocks and commission     | Round per row then sum                   | `test_collection_sheet_report_data.py` > `test_round_per_row_then_sum`                                                                                                                                                                                                                                       | ✅ COMPLIANT |
| Document blocks and commission     | Zero percent                             | `test_collection_sheet_report_data.py` > `test_zero_percent`                                                                                                                                                                                                                                                 | ✅ COMPLIANT |
| Voucher blocks and tendered        | Catalog order and empty drop             | `test_collection_sheet_report_data.py` > `test_catalog_order_and_empty_drop`                                                                                                                                                                                                                                 | ✅ COMPLIANT |
| Voucher blocks and tendered        | Tendered includes cash on hand           | `test_collection_sheet_report_data.py` > `test_tendered_includes_cash_on_hand`                                                                                                                                                                                                                               | ✅ COMPLIANT |
| Reconciliation status and mismatch | Tri-state via compare_amounts            | `test_collection_sheet_report_data.py` > `test_recon_tri_state`                                                                                                                                                                                                                                              | ✅ COMPLIANT |
| Reconciliation status and mismatch | Unallocated voucher mismatch             | `test_collection_sheet_report_data.py` > `test_unallocated_voucher_mismatch`                                                                                                                                                                                                                                 | ✅ COMPLIANT |
| Unsaved sheet and mixed currency   | Unsaved sheet refused                    | `test_collection_sheet_report_data.py` > `test_unsaved_sheet_refused`                                                                                                                                                                                                                                        | ✅ COMPLIANT |
| Unsaved sheet and mixed currency   | Mixed currency refused                   | `test_collection_sheet_report_data.py` > `test_mixed_currency_refused`                                                                                                                                                                                                                                       | ✅ COMPLIANT |
| PDF Print menu and QWeb            | Print menu binding                       | `test_collection_sheet_report.py` > `test_report_action_is_qweb_pdf_bound_a4_landscape`                                                                                                                                                                                                                      | ✅ COMPLIANT |
| PDF Print menu and QWeb            | HTML contains names numbers banner       | `test_collection_sheet_report.py` > `test_html_contains_reference_seller_partners_docs_banner`, `test_qweb_arch_uses_external_layout_and_t_out`                                                                                                                                                              | ✅ COMPLIANT |
| XLSX workbook and percent scale    | Zip freeze and cached SUM                | `test_collection_sheet_xlsx.py` > `test_xlsx_bytes_are_zip_with_workbook`, `test_xlsx_print_setup_freeze_and_column_width`, `test_xlsx_cached_subtotals_match_payload`                                                                                                                                       | ✅ COMPLIANT |
| XLSX workbook and percent scale    | Percent scale 0–100 to 0.0%              | `test_collection_sheet_xlsx.py` > `test_xlsx_percent_scale_4_5_is_excel_fraction`                                                                                                                                                                                                                            | ✅ COMPLIANT |
| XLSX workbook and percent scale    | Header button last and one notebook page | `test_collection_sheet_xlsx.py` > `test_header_xlsx_button_last_before_state`, `test_sheet_form_one_notebook_page_recon_second_group`                                                                                                                                                                        | ✅ COMPLIANT |
| Company ACL and no sudo            | Company-B AccessError                    | `test_collection_sheet_report.py` > `test_company_b_access_error_on_data_and_render`; `test_collection_sheet_xlsx.py` > `test_company_b_access_error_on_xlsx`; `test_collection_sheet_report_data.py` > `test_report_source_has_no_sudo`; `test_collection_sheet_xlsx.py` > `test_xlsx_sources_have_no_sudo` | ✅ COMPLIANT |
| Allocation line document_kind      | Default invoice                          | `test_collection_allocation_document_kind.py` > `test_default_invoice`                                                                                                                                                                                                                                       | ✅ COMPLIANT |
| Allocation line document_kind      | Required selection                       | `test_collection_allocation_document_kind.py` > `test_required_selection`                                                                                                                                                                                                                                    | ✅ COMPLIANT |
| Allocation line document_kind      | Quotation round-trip on draft            | `test_collection_allocation_document_kind.py` > `test_quotation_round_trip_on_draft`                                                                                                                                                                                                                         | ✅ COMPLIANT |
| Allocation line document_kind      | Inherited view before invoice_number     | `test_collection_allocation_document_kind.py` > `test_inherited_view_before_invoice_number`                                                                                                                                                                                                                  | ✅ COMPLIANT |
| Allocation line document_kind      | MCP create omits kind                    | `test_collection_allocation_document_kind.py` > `test_mcp_create_omits_kind_defaults_invoice`                                                                                                                                                                                                                | ✅ COMPLIANT |

**Compliance summary**: 26/26 scenarios compliant

### Correctness (Static Evidence)

| Requirement                        | Status         | Notes                                                                                                                                                               |
| ---------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Sheet reconciliation inputs        | ✅ Implemented | Second inherit `models/collection_sheet_report.py`: Float `%` default 0, Monetary cash/withheld, `models.Constraint` 0–100, closed `write` UserError then `super()` |
| Shared report payload              | ✅ Implemented | `_collection_report_data()` returns listed keys; nested rows primitives; QWeb-only `sheet`/`currency`; drafts included                                              |
| Customer codes and sort            | ✅ Implemented | Batched binding search on raw `company_id.collection_connector_id`; no `_collection_active_connector`; sort `(code=="", code, name)`                                |
| Document blocks and commission     | ✅ Implemented | invoice then quotation; empty dropped; `currency.round(applied*pct/100)` per row then sum                                                                           |
| Voucher blocks and tendered        | ✅ Implemented | Catalog labels by `code`; order transfer/check/deposit then alpha; tendered cash+deposits+checks+transfers                                                          |
| Reconciliation status and mismatch | ✅ Implemented | `compare_amounts` → balanced/in_favor/outstanding; mismatch when Σ allocation totals ≠ Σ voucher amounts                                                            |
| Unsaved sheet and mixed currency   | ✅ Implemented | `_ensure_saved_sheet()` then mixed-currency UserError before payload                                                                                                |
| PDF Print menu and QWeb            | ✅ Implemented | Bound `qweb-pdf` XMLID; A4 landscape; `t-out`; `web.html_container` + `web.external_layout`                                                                         |
| XLSX workbook and percent scale    | ✅ Implemented | xlsxwriter; freeze A6; cached SUM; percent/100; header Export XLSX last; recon second inner group; `act_url` no sudo                                                |
| Company ACL and no sudo            | ✅ Implemented | `check_access("read")` on render; company `ir.rule`; source scans omit `sudo()`                                                                                     |
| Allocation line document_kind      | ✅ Implemented | required Selection invoice/quotation default invoice; inherit xpath before `invoice_number`; MCP schema unchanged                                                   |

### Coherence (Design)

| Decision                                | Followed? | Notes                                                                                   |
| --------------------------------------- | --------- | --------------------------------------------------------------------------------------- |
| Shared `_collection_report_data()`      | ✅ Yes    | PDF `_get_report_values` and XLSX `_render_xlsx` consume the same payload               |
| Second inherit vs `collection_sheet.py` | ✅ Yes    | `models/collection_sheet_report.py`; `write` → `super()`; sheet model not edited        |
| Inherit xpath vs allocation views       | ✅ Yes    | `views/collection_sheet_report_views.xml`; `collection_allocation_views.xml` not edited |
| QWeb + xlsxwriter vs OCA report_xlsx    | ✅ Yes    | No custom `xlsx` report type; header button + attachment                                |
| `_init_column` vs migrations/           | ✅ Yes    | Selection default+required; no `migrations/19.0.1.30.0/`                                |
| Sheet % vs seller binding               | ✅ Yes    | Sheet Constraint 0–100; not copied from binding                                         |
| Print drafts                            | ✅ Yes    | All `allocation_ids` / `voucher_ids` including draft/pending/rejected                   |
| Dual Total Cobrado mismatch             | ✅ Yes    | `mismatch` when unallocated vouchers make sums differ                                   |
| Cached formulas                         | ✅ Yes    | `write_formula(..., cached_value)`; data_only reads non-None                            |
| XLSX percent/100                        | ✅ Yes    | 4.5 stored as 0.045 with `0.0%`                                                         |
| Catalog labels by code                  | ✅ Yes    | `collection.document.type` search; not `_selection_document_type`                       |
| Manifest last PR `19.0.1.30.0`          | ✅ Yes    | `web` + report `data` + inherit views; version assertion passed                         |
| No sudo                                 | ✅ Yes    | Report inherit, render, and xlsx writer                                                 |

Apply-progress deviations (disk lxml inherit merge; no custom `_init_column`; HTML
`_get_asset_nodes` patch; SQL company insert for AccessError; XLSX omits
`currency_symbol`/`currency_decimals`; `_align_workbook_xml` widths) do not change
remaining spec outcomes.

### Issues Found

**CRITICAL**: None **WARNING**:

- Optional smoke skipped: `_render_qweb_pdf` / wkhtmltopdf and browser Print menu were
  not run (HTML + XLSX zip are covered in-suite).
- TDD Safety Net `N/A` on files that were modified rather than new:
  `collection_allocation_line.py` (1.2), `__manifest__.py` (2.2/4.2),
  `collection_views.xml` (3.2). Additive edits; focused RED/GREEN still exist.
- Inherit-view order is asserted by parsing disk XML and simulating xpath merge, not by
  reading live `ir.ui.view` arch after inherit (D did register the `data` path; upgrade
  loaded the XML). **SUGGESTION**:
- Optional pylint `C8101` (`manifest-required-author`, author `Seedian`) on
  `__manifest__.py`; mandatory pylint hook still Passed.
- Pre-existing duplicate OCR/seller field-label warnings on `collection.voucher` during
  registry load (tests).
- Odoo stats line reports `661 tests` while `odoo.tests.result` reports `597` loaded
  tests; envelope uses the result line (same convention as archived verify).
- Apply-progress recorded 9 pre-existing `fiscalyear_last_day` company-create errors on
  a focused `TestCollectionCompanyMigration` class run. This gate run had **0 failed, 0
  error(s)** including all 12 methods of that class; those errors did not reproduce
  here.
- SQL `ERROR` lines for `collection_voucher_document_id_uniq` appear in the log from
  expected UniqueViolation tests (MCP other-company); they are not test failures.
- HTML `_render_qweb_html` tests patch `ir.qweb._get_asset_nodes` because devel
  `web.report_assets_common` still lists `website/` snippet SCSS while `website` is not
  installed.

### Verdict

PASS WITH WARNINGS All 11 requirements and 26 scenarios have covering tests that started
and passed in this run; design decisions match the implementation. Warnings are skipped
optional PDF/browser smoke, Safety Net N/A on additive edits, and disk-XML inherit
inspection.

### TDD Compliance

| Check                         | Result | Details                                                                                                                                                                                                                               |
| ----------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TDD Evidence reported         | ✅     | TDD Cycle Evidence table in `apply-progress.md` for tasks 1.1–4.2                                                                                                                                                                     |
| All tasks have tests          | ✅     | 10/10 tasks have named test files (`test_collection_allocation_document_kind.py`, `test_collection_sheet_report_data.py`, `test_collection_sheet_report.py`, `test_collection_sheet_xlsx.py`, `test_collection_company_migration.py`) |
| RED confirmed (tests exist)   | ✅     | 5+17+6+12 focused methods plus version assertion exist on disk                                                                                                                                                                        |
| GREEN confirmed (tests pass)  | ✅     | This run: 0 failed, 0 error(s) of 597 tests; all covering methods started                                                                                                                                                             |
| Triangulation adequate        | ✅     | Payload/QWeb/XLSX triangulated; 4.2 version/`data` Single                                                                                                                                                                             |
| Safety Net for modified files | ⚠️     | New test/report files correctly `N/A (new)`; modified line model, sheet form, and manifest recorded N/A for additive slices                                                                                                           |

**TDD Compliance**: 5/6 checks passed (safety net warning on modified-file N/A)

---

### Test Layer Distribution

| Layer       | Tests  | Files | Tools                                                                                                                                                                                |
| ----------- | ------ | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Unit        | 22     | 3     | TransactionCase payload/kind/manifest (`test_collection_sheet_report_data.py` 17, `test_collection_allocation_document_kind.py` 4, `test_collection_company_migration.py` 1 version) |
| Integration | 19     | 3     | MCP `_call` + QWeb HTML + XLSX zip/act_url (`test_collection_allocation_document_kind.py` 1, `test_collection_sheet_report.py` 6, `test_collection_sheet_xlsx.py` 12)                |
| E2E         | 0      | 0     | not installed (browser Print skipped)                                                                                                                                                |
| **Total**   | **41** | **5** | focused tests created/extended for this change                                                                                                                                       |

Envelope run also executed the full collection module suite (597).

---

### Changed File Coverage

Coverage analysis skipped — no coverage tool detected

---

### Assertion Quality

**Assertion quality**: ✅ All assertions verify real behavior

Scanned `tests/test_collection_allocation_document_kind.py`,
`tests/test_collection_sheet_report_data.py`, `tests/test_collection_sheet_report.py`,
`tests/test_collection_sheet_xlsx.py`, and the version assertion in
`tests/test_collection_company_migration.py`. Payload tests call
`_collection_report_data()` and assert keys, primitives, rounding inequality vs naive,
recon statuses, mismatch, and UserError. QWeb tests call `_render_qweb_html` and assert
names/banner/`t-out`/AccessError. XLSX tests call `_render_xlsx` / `action_print_xlsx`
and assert `PK`, freeze `A6`, cached SUM vs payload, 0.045, act_url, and AccessError.
Kind tests persist default/quotation and assert MCP schema omission. Loops over
blocks/percent cells/SUM coords are preceded by non-empty assertions. Source `sudo()`
scans are paired with AccessError behavioral tests. No tautologies, ghost loops, or
production-code-free assertions.

---

### Quality Metrics

**Linter**: ✅ No errors on owned files (scoped pre-commit exit 0). Optional glob
`C8101` on `__manifest__.py` is pre-existing. **Type Checker**: ➖ Not available
