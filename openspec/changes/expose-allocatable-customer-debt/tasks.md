# Tasks: Expose allocatable customer debt

Apply root: `odoo/custom/src/private/collection`. No migrate folder. Threat matrix N/A.

## Review Workload Forecast

| Field                   | Value             |
| ----------------------- | ----------------- |
| Estimated changed lines | ~350–500 authored |
| 400-line budget risk    | Medium            |
| Chained PRs recommended | No                |
| Delivery strategy       | ask-on-risk       |

### Suggested Work Units

| Unit | Goal                                | Focused test command                         |
| ---- | ----------------------------------- | -------------------------------------------- |
| 1    | OpenSpec + RED tests                | `invoke test -m collection --mode=update`    |
| 2    | Helper + customer_debt + revalidate | same                                         |
| 3    | Manifest 1.40.1 + docs              | `tests/test_collection_company_migration.py` |

## Phase 1: RED tests

- [x] 1.1 `tests/test_collection_mcp_customer_debt.py`: success payload includes
      `allocatable_balance` and the three summary keys; no reservations → allocatable
      equals gross (100 overdue + 50 open).
- [x] 1.2 Hidden draft on a **proposal** sheet reduces allocatable; gross unchanged
      (`inv-bound-open` 50/10; overdue 100/100; open allocatable 10; total allocatable
      110).
- [x] 1.3 Confirmed consumption on a **closed** sheet reduces allocatable.
- [x] 1.4 Over-reservation reports `allocatable_balance` 0, never negative.
- [x] 1.5 Zero-debt path still succeeds; allocatable summary keys are 0.
- [x] 1.6 `tests/test_collection_mcp_allocation.py`: hidden proposal-sheet draft of the
      full open-invoice balance refuses a new-open-sheet apply of 1 peso with
      `Applied amount exceeds available invoice balance.` and no writes; destination
      amend still excludes dest.

## Phase 2: GREEN implementation

- [x] 2.1 Extract
      `_collection_reserved_amounts(external_invoice_ids, exclude_allocation_id=False) -> dict[str, float]`
      (`@api.model` + `@api.private`); one query; domain draft+confirmed, current
      company.
- [x] 2.2 `_collection_allocation_revalidate` uses the helper, still excludes dest,
      still raises the same UserError, still compares `balance_seen` to GROSS `balance`.
- [x] 2.3 `customer_debt` annotates invoices and summary after connector fetch +
      `document_kind` default; never `sudo()`; update `@mcp_tool` description.

## Phase 3: Version + docs

- [x] 3.1 Bump `__manifest__.py` to `19.0.1.40.1`. MUST NOT add
      `migrations/19.0.1.40.1/`.
- [x] 3.2 `tests/test_collection_company_migration.py`: version `19.0.1.40.1`; keep
      `migrations/19.0.1.40.0/post-migrate.py`; assert no 1.40.1 folder; AGENTS.md pin
      `19.0.1.40.1`.
- [x] 3.3 `AGENTS.md` + `readme/DESCRIPTION.md`: allocatable payload; version; no 1.40.1
      migrate.
- [x] 3.4 Merge ADDED requirement into `openspec/specs/collection-allocations/spec.md`.
- [x] 3.5 `invoke test -m collection --mode=update`.
