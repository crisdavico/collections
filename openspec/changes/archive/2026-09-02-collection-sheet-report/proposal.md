# Proposal: Collection Sheet Report

## Intent

Operators cannot print a *Planilla de Cobranza*. From `collection.sheet` they
MUST print PDF and download XLSX with identical totals, plus recon inputs for
Diferencia.

## Scope

### In Scope

- Line `document_kind` (`invoice`/`quotation`, default `invoice`, `_init_column`)
- Sheet `commission_percent` (0–100), `cash_on_hand`, `commission_withheld` on
  a second `_inherit`; freeze while closed
- Shared `_collection_report_data()`; bound `qweb-pdf`; `action_print_xlsx`
- Print all allocations/vouchers including drafts; `mismatch` when voucher SUM
  ≠ allocation `total_vouchers`
- TDD tests; last PR: `web` depend, report `data`, version `19.0.1.30.0`

### Out of Scope

- Nebula/MCP/connector classification; OCA `report_xlsx`; controller/JS
- Editing `collection_sheet.py` or `collection_allocation_views.xml`
- `migrations/`; seller-binding commission; manifest until last PR

## Capabilities

### New Capabilities

- `collection-sheet-report`: payload, PDF, XLSX, recon inputs, print-all,
  mismatch, no sudo

### Modified Capabilities

- `collection-allocations`: required line `document_kind`; inherited view
  before `invoice_number`; MCP create unchanged

## Approach

Approach 1. New `collection_sheet_report.py` inherit. Inject `document_kind`
via inherited view. QWeb `t-out` + `web.external_layout`. XLSX xlsxwriter with
cached formulas; Python recon banner; percent/100 in XLSX. Catalog labels by `code`.
`_ensure_saved_sheet()`; mixed-currency `UserError`. Strict TDD. PRs: A
fields+payload, B PDF, C XLSX+button, D `19.0.1.30.0`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `models/collection_sheet_report.py` | New | Recon fields, payload, XLSX action |
| `models/collection_allocation_line.py` | Modified | `document_kind` |
| `report/` | New | Paperformat, action, QWeb, writer |
| `views/collection_sheet_report_views.xml` | New | Inject `document_kind` |
| `views/collection_views.xml` | Modified | XLSX button last; recon second group |
| `__manifest__.py` | Modified | Last PR: `web`, `data`, `19.0.1.30.0` |
| `tests/test_collection_sheet_*.py` | New | Payload, HTML, XLSX, kind |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Sibling claimed files | High | Second inherit; last-PR manifest |
| Dual Total Cobrado | Med | `mismatch`; test unallocated vouchers |
| PDF vs workbook membrete | Med | Accept `web.external_layout` |
| wkhtmltopdf flake | Med | HTML in tests; PDF via shell |

## Rollback Plan

Revert or uninstall new `report/` and inherit. Unused columns remain until
uninstall. No migrate. Manifest rollback: pre-D (`19.0.1.29.0`).

## Dependencies

- In-flight `draft-until-close`, `seller-commission-percent` (do not edit)
- Explicit `web` in last PR; image xlsxwriter/openpyxl; workbook template

## Success Criteria

- [ ] Print menu PDF; header XLSX matching template geometry
- [ ] Identical Total Cobrado/Aplicado/Remanente/Comisión/Diferencia
- [ ] Open-sheet prints include drafts; closed freeze recon writes
- [ ] `document_kind` before `invoice_number`; default invoice
- [ ] New TransactionCase files pass (HTML, not wkhtmltopdf)

## Proposal question round

Skipped — answers already in source plan: (1) kind human-settable; (2) cash
and withheld on sheet; (3) percent on sheet; (4) header XLSX; (5) print
drafts; (6) second inherit; (7) inherited view.
