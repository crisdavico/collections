# Tasks: Collection Sheet Report

## Review Workload Forecast

| Field                   | Value           |
| ----------------------- | --------------- |
| Estimated changed lines | 800–1200        |
| 400-line budget risk    | High            |
| Chained PRs recommended | Yes             |
| Suggested split         | A → B → C → D   |
| Delivery strategy       | auto-chain      |
| Chain strategy          | stacked-to-main |

Decision needed before apply: No Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

Focused:
`docker exec -i seedian-odoo-1 odoo -d devel --test-enable --stop-after-init --test-tags /collection:ClassName`.
Gate: `invoke test -m collection --mode=update -d devel`. Pre-commit on touched files.
No version A–C. Never edit `collection_sheet.py`, `collection_allocation_views.xml`,
allocation model/tests, `test_collection_ui.py`.

### Suggested Work Units

| Unit | Goal                   | Likely PR                          | Focused test command                                                                         | Runtime harness                      | Rollback boundary                                                                      |
| ---- | ---------------------- | ---------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------ | -------------------------------------------------------------------------------------- |
| A    | Kind + recon + payload | PR 1                               | `/collection:TestCollectionAllocationDocumentKind,/collection:TestCollectionSheetReportData` | N/A (payload tests)                  | line model, `collection_sheet_report.py`, inherit views, two tests, `__init__` imports |
| B    | QWeb PDF               | PR 2 after A                       | `/collection:TestCollectionSheetReport`                                                      | `_render_qweb_html` (no wkhtmltopdf) | `report/` + 3 XML; `web`+3 `data` (no version). C skips `__manifest__.py`              |
| C    | XLSX + button          | PR 3 after B                       | `/collection:TestCollectionSheetXlsx`                                                        | `action_print_xlsx` → `PK` zip       | xlsx model, `action_print_xlsx`, `collection_views.xml`                                |
| D    | `19.0.1.30.0`          | PR 4 after A–C + sibling manifests | `/collection:TestCollectionCompanyMigration`                                                 | `-u collection`                      | version, inherit-view `data`, `AGENTS.md`, `readme/DESCRIPTION.md`, one assertion      |

## Phase 1: Fields and payload (PR A)

- [x] 1.1 RED `tests/test_collection_allocation_document_kind.py`: default `invoice`;
      selection required; quotation round-trip; xpath before `invoice_number`; `<list>`;
      MCP omit → `invoice`.
- [x] 1.2 GREEN `document_kind` + `_init_column` in
      `models/collection_allocation_line.py`; `views/collection_sheet_report_views.xml`;
      `models/__init__.py` after `collection_sheet`; `tests/__init__.py`.
- [x] 1.3 RED `tests/test_collection_sheet_report_data.py`: % 0/100 vs OOB; closed
      freeze; reopen keeps; keys+primitives; drafts; code vs blank last; kind split;
      round-then-sum; zero %; catalog order; tendered cash; recon tri-state; `mismatch`;
      unsaved/mixed-currency `UserError`; no `sudo()`.
- [x] 1.4 GREEN `models/collection_sheet_report.py`: currency, %, cash, withheld,
      Constraint, freeze `write`→`super()`, `_collection_report_data()` + `@api.private`
      helpers. No `report` import. No version.

## Phase 2: PDF (PR B, after A)

- [x] 2.1 RED `tests/test_collection_sheet_report.py`: XMLID `qweb-pdf` bound + A4
      landscape; HTML reference/seller/partners/docs/banner; `web.external_layout`;
      company-B `AccessError`.
- [x] 2.2 GREEN `report/` package + render; paperformat/action/templates (`t-out`);
      `__init__.py` `from . import report`; `web` + 3 `data`. No version.

## Phase 3: XLSX (PR C, after B)

- [x] 3.1 RED `tests/test_collection_sheet_xlsx.py`: `PK`+`workbook.xml`; freeze `A6`;
      cached SUM; 4.5%→`0.045`; banner; `act_url`; no dup; button last before `state`;
      one notebook page; company-B `AccessError`; no `sudo()`.
- [x] 3.2 GREEN `report/collection_sheet_xlsx.py`; `action_print_xlsx`; XLSX last in
      `views/collection_views.xml` header; recon second inner `<group>`. No manifest. No
      version.

## Phase 4: Version and docs (PR D, after A–C + sibling manifests)

- [x] 4.1 RED `tests/test_collection_company_migration.py`: one assert
      `"version": "19.0.1.30.0"`; no `migrations/19.0.1.30.0/`.
- [x] 4.2 GREEN version `19.0.1.30.0`; `data` += inherit views after report XML;
      `AGENTS.md`; `readme/DESCRIPTION.md`. Do not re-add `web`.
