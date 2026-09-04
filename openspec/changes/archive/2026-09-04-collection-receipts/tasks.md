# Tasks: Collection Receipts

## Review Workload Forecast

| Field                   | Value                     |
| ----------------------- | ------------------------- |
| Estimated changed lines | 900–1300                  |
| 400-line budget risk    | High                      |
| Chained PRs recommended | Yes                       |
| Suggested split         | PR 1 → PR 2 → PR 3 → PR 4 |
| Delivery strategy       | auto-chain                |
| Chain strategy          | stacked-to-main           |

Decision needed before apply: No Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

Upgrade: `invoke install -m collection` / `-u collection`.

### Suggested Work Units

| Unit | Goal              | Likely PR | Focused test command                      | Runtime harness                    | Rollback boundary                                   |
| ---- | ----------------- | --------- | ----------------------------------------- | ---------------------------------- | --------------------------------------------------- |
| 1    | Models/ACL/1.34.0 | PR 1      | `invoke test -m collection --mode=update` | Odoo TransactionCase in containers | models, security, migrate 1.34.0                    |
| 2    | Kind/hash/persist | PR 2      | same                                      | same                               | `tools/collection_allocation.py`, debt kind         |
| 3    | Close/get/views   | PR 3      | same                                      | same                               | Close, `create_receipt`, lookup, views, `AGENTS.md` |
| 4    | Tests/lint        | PR 4      | same + scoped pre-commit                  | same                               | leftover tests                                      |

## Phase 1: Models

- [x] 1.1 RED `tests/test_collection_receipt.py`: uniqueness, values, derived apps,
      totals.
- [x] 1.2 GREEN `models/collection_receipt.py`, `models/collection_receipt_value.py`,
      `models/__init__.py` (Constraint; `company_id`).
- [x] 1.3 RED `tests/test_collection_receipt.py`: freeze, issued, unlink, external id,
      ACL.
- [x] 1.4 GREEN freeze from `models/collection_allocation_line.py`; `receipt_ids` on
      `models/collection_allocation.py`; cascade unlink.
- [x] 1.5 GREEN `security/collection_security.xml` ir.rule;
      `security/ir.model.access.csv` `1,1,1,1`.
- [x] 1.6 RED `tests/test_collection_company_migration.py`: 1.34.0; no backfill.
- [x] 1.7 GREEN `__manifest__.py` `19.0.1.34.0`;
      `migrations/19.0.1.34.0/post-migrate.py`.

## Phase 2: MCP persist

- [x] 2.1 RED `tests/test_collection_allocation_document_kind.py`: send/omit/keep kind;
      get returns kind.
- [x] 2.2 GREEN `tools/collection_allocation.py`: optional kind; persist keeps stored;
      payload wins.
- [x] 2.3 RED `tests/test_collection_receipt.py`,
      `tests/test_collection_receipt_split.py`: compat, splits, over-split.
- [x] 2.4 GREEN `tools/collection_allocation.py` persist: FIFO compat; splits; amend
      rebuild.
- [x] 2.5 RED `tests/test_collection_mcp_allocation.py`,
      `tests/test_collection_receipt_split.py`: hash omit vs extras.
- [x] 2.6 GREEN `tools/collection_allocation.py` hash extras only if present.
- [x] 2.7 RED `tests/test_collection_mcp_customer_debt.py`,
      `tests/test_collection_connector.py`: debt `document_kind`.
- [x] 2.8 GREEN `models/collection_connector.py`, `tools/customer_debt.py`: kind default
      invoice. No `create_receipt`.

## Phase 3: Close / UI

- [x] 3.1 RED `tests/test_collection_connector.py`: allowlist `create_receipt`; unknown
      fail-closed; Import `list_sellers`.
- [x] 3.2 GREEN `models/collection_connector.py` `_DISPATCH_OPS`;
      `tests/common_connector.py` `_test_create_receipt`.
- [x] 3.3 RED `tests/test_collection_receipt.py`: Close issues; zero receipts; draft
      until issued.
- [x] 3.4 GREEN `models/collection_sheet.py` `action_close` dispatch; ctx
      `collection_receipt_issuing`.
- [x] 3.5 RED `tests/test_collection_mcp_allocation_lookup.py`: `_TOP_KEYS` includes
      `receipts`.
- [x] 3.6 GREEN `tools/allocation_lookup.py` always `receipts[]`.
- [x] 3.7 RED `tests/test_collection_ui.py`: Form does not issue; `<list>`; Receipts
      page.
- [x] 3.8 GREEN `views/collection_receipt_views.xml`, `__manifest__.py`,
      `views/collection_allocation_views.xml`.
- [x] 3.9 GREEN `AGENTS.md`: lift `_DISPATCH_OPS`/kind bans; `19.0.1.34.0`.

## Phase 4: Tests

- [x] 4.1 RED/GREEN `tests/test_collection_allocation.py`: freeze `receipt_ids`;
      closed/cancelled guards; unlink cascade.
- [x] 4.2 RED/GREEN `tests/test_collection_receipt_split.py`: amend rebuilds; amend
      without splits.
- [x] 4.3 `tests/__init__.py`; scoped `pre-commit run --files`.

## Coordinated follow-ups (not this apply)

Sqlite: kind seed; stub `create_receipt` id, no file write. Nebula: `InvoiceApplication`
kind; splits; hash extras iff present.
