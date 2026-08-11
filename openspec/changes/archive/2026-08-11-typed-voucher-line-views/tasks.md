# Tasks: Typed voucher line tables and payment-lines menu

## Review Workload Forecast

| Field                   | Value           |
| ----------------------- | --------------- |
| Estimated changed lines | 250–400         |
| 400-line budget risk    | Medium          |
| Chained PRs recommended | No              |
| Suggested split         | Single PR       |
| Delivery strategy       | ask-on-risk     |
| Chain strategy          | stacked-to-main |

Decision needed before apply: No Chained PRs recommended: No Chain strategy:
stacked-to-main 400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal                                   | Likely PR | Focused test command        | Runtime harness                | Rollback boundary                 |
| ---- | -------------------------------------- | --------- | --------------------------- | ------------------------------ | --------------------------------- |
| 1    | Typed stacked form tables + UI tests   | PR 1      | `invoke test -m collection` | `invoke install -m collection` | form views + UI tests             |
| 2    | Payment Lines menu (read-only) + tests | PR 1      | `invoke test -m collection` | `invoke install -m collection` | line views/action/menu + UI tests |

## Phase 1: Typed form tables (Unit 1)

- [x] 1.1 RED: `tests/test_collection_ui.py` — form MUST have three stacked
      `payment_ids` (or typed) lists for bank_transfer / check / cash_deposit; MUST NOT
      keep the mono all-type editable list; each list MUST omit `document_type` column
      and include the type’s field set + `document_id`.
- [x] 1.2 RED: Creating a line with each table’s default context MUST persist the
      matching `document_type` (ORM/context test acceptable).
- [x] 1.3 GREEN: Update `views/collection_views.xml` voucher form — stacked typed
      editable lists with domains/contexts and type-specific columns; remove old mono
      payment-lines list.
- [x] 1.4 GREEN (only if needed): Add typed One2many helpers on `collection.voucher`
      when triple `payment_ids` proves insufficient. (Skipped — approach A triple
      `payment_ids` sufficient.)
- [x] 1.5 Verify: `invoke install -m collection`; focused UI/model tests green.

## Phase 2: Payment Lines menu (Unit 2)

- [x] 2.1 RED: UI tests for Collections → Payment Lines menu/action —
      `res_model=collection.voucher.line`, create/edit disabled, search fields for
      `document_type`, `document_id`, `amount`, type-specific fields, `voucher_id`.
- [x] 2.2 RED: Arch/behavior note — `unsupported` lines absent from typed form tables;
      findable via Payment Lines filter (assert domain/filter exists).
- [x] 2.3 GREEN: Add line list + search views, act_window, menuitem under Collections.
- [x] 2.4 Verify: `invoke install -m collection`; `invoke test -m collection`.

## Phase 3: Quality gate

- [x] 3.1 `pre-commit run --files odoo/custom/src/private/collection/**`
- [x] 3.2 Confirm MCP tests still green (no intentional MCP changes).
- [x] 3.3 Manual smoke: N/A — `seedian-odoo-1` Exited (137); relied on TransactionCase
      UI coverage (`test_collection_ui.py`) from 3.2.
