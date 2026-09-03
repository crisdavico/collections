# Tasks: Allocation Customer Debt

## Review Workload Forecast

| Field                   | Value                     |
| ----------------------- | ------------------------- |
| Estimated changed lines | 700–950                   |
| Suggested split         | PR 1 → PR 2 → PR 3 → PR 4 |
| Delivery strategy       | ask-on-risk               |

Decision needed before apply: Yes Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

### Suggested Work Units

Harness: `invoke install -m collection`. Focused tests:
`invoke test -m collection --mode=update` on the files named per unit.

| Unit | Goal                                                  | Likely PR | Focused test command                                                                                                | Runtime harness | Rollback boundary                                                                          |
| ---- | ----------------------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------- | --------------- | ------------------------------------------------------------------------------------------ |
| 1    | Totals, CHECK `>= 0`, drop reason, migrate 1.32.0     | PR 1      | `test_collection_allocation.py`, `test_collection_company_migration.py`                                             | same            | allocation compute/constraint; line/revision; `__manifest__.py`; `migrations/19.0.1.32.0/` |
| 2    | MCP expand, ignore reason, get `document_kind`        | PR 2      | `test_collection_mcp_allocation.py`, `test_collection_mcp_allocation_lookup.py`                                     | same            | `tools/collection_allocation.py`; `tools/allocation_lookup.py`                             |
| 3    | Form snapshot, many2many, Customer Debt, smart button | PR 3      | `test_collection_allocation.py`, `test_collection_ui.py`                                                            | same            | helper/onchange/`action_open_vouchers`; `views/collection_allocation_views.xml`            |
| 4    | Detach, report `""`, parent-arch kind, docs           | PR 4      | `test_collection_voucher.py`, `test_collection_sheet_report_data.py`, `test_collection_allocation_document_kind.py` | same            | voucher + sheet report models; `views/collection_sheet_report_views.xml`; `AGENTS.md`      |

## Phase 1: Foundation

- [x] 1.1 RED `tests/test_collection_allocation.py`: residual debt−applied (150−40=110);
      negative saves; zero applied persists; no `residual_reason`.
- [x] 1.2 RED `tests/test_collection_company_migration.py`: manifest `19.0.1.32.0`;
      `migrations/19.0.1.32.0/post-migrate.py` DROP `residual_reason` on
      allocation+revision; keep 1.31.0.
- [x] 1.3 GREEN `models/collection_allocation.py`: compute
      `total_debt`/`total_invoices`/`total_quotations`; residual=debt−applied; drop
      `residual_reason` + `_check_residual`. `models/collection_allocation_line.py`:
      default 0 + CHECK `>= 0`. Revision drops reason.
- [x] 1.4 GREEN `__manifest__.py` `19.0.1.32.0` + migrate. Strip leftover
      `residual_reason` writes in `tests/test_collection_*.py`. Drop
      `tools/collection_allocation.py` persist keys `residual_reason`/`total_debt`
      (expand/hash stay Phase 2).
- [x] 1.5 REFACTOR: `invoke install -m collection` then focused allocation +
      company_migration tests and scoped pre-commit on files touched.

## Phase 2: MCP

- [x] 2.1 RED `tests/test_collection_mcp_allocation.py`: I1+I2 zeros; empty `invoices[]`
      expands; ignore reason; hash reason-only no-op; parse `>= 0`.
- [x] 2.2 RED `tests/test_collection_mcp_allocation_lookup.py`: omit reason; invoices
      include `document_kind`.
- [x] 2.3 GREEN `tools/collection_allocation.py`: parse `>= 0`; expand in revalidate;
      ignore reason after enum; drop hash reason,
      `_collection_allocation_check_residual`, amend placeholder.
      `tools/allocation_lookup.py`: drop reason; add `document_kind`.
- [x] 2.4 REFACTOR: install; MCP tests; update-mode; pre-commit.

## Phase 3: UI / form

- [x] 3.1 RED `tests/test_collection_allocation.py`: helper; onchange replaces lines
      unless confirmed; missing connector/binding → empty, no UserError; snapshot iff
      `"line_ids"` omitted.
- [x] 3.2 RED `tests/test_collection_ui.py`: many2many `no_create`/`no_create_edit` +
      `document_type`; Customer Debt; helpers; no Residual Reason; smart button domain
      `allocation_id`.
- [x] 3.3 GREEN `models/collection_allocation.py`: helper via
      `collection_connector_id`+binding (never `_collection_active_connector()`);
      onchange; create-if-omitted; `action_open_vouchers`. Match
      `views/collection_allocation_views.xml`.
- [x] 3.4 REFACTOR: install; allocation/ui tests; update-mode; pre-commit.

## Phase 4: Detach / report / docs

- [x] 4.1 RED `tests/test_collection_voucher.py`: draft detach/unlink/partner-write at
      residual 0 and leftover < amount succeed; residual unchanged; confirmed refused.
- [x] 4.2 GREEN `models/collection_voucher.py`: stop residual ± voucher amount; drop
      `_allocation_residual_holds` reason branch.
- [x] 4.3 RED/GREEN `tests/test_collection_sheet_report_data.py` +
      `models/collection_sheet_report.py`: stop `_fields["residual_reason"]`; payload
      `""`. Leave XLSX/PDF copy.
- [x] 4.4 RED/GREEN `tests/test_collection_allocation_document_kind.py`: parent-arch
      `document_kind` before `invoice_number` on `<list>`; get returns kind. Delete
      `views/collection_sheet_report_views.xml`; drop from `__manifest__.py`. Update
      `AGENTS.md` (`19.0.1.32.0`).
- [x] 4.5 REFACTOR: install; `invoke test -m collection --mode=update`;
      `pre-commit run --files odoo/custom/src/private/collection/**`.
