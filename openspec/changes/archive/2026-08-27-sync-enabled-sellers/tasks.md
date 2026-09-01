# Tasks: Sync Enabled Sellers from connector

## Review Workload Forecast

| Field                   | Value           |
| ----------------------- | --------------- |
| Estimated changed lines | 350–450         |
| 400-line budget risk    | Medium          |
| Chained PRs recommended | No              |
| Suggested split         | Single PR       |
| Delivery strategy       | ask-on-risk     |
| Chain strategy          | stacked-to-main |

Edits stay in collection (optional sqlite test in `collection_connector_sqlite`). Nebula
out of scope. Invoke/pre-commit from Seedian root.

## Phase 1: OpenSpec

- [x] 1.1 Proposal, design, tasks, state, spec deltas (`collection-connectors`,
      `seller-lookup`).

## Phase 2: Sync tests (RED)

- [x] 2.1 Add `tests/test_collection_seller_sync.py` and import it.
- [x] 2.2 RED: create vs phone-match vs binding reuse; replace-all drops extras;
      inactive omitted; missing connector unchanged; duplicate phone aborts; two source
      ids → same user aborts; second Import idempotent.

## Phase 3: Sync implementation (GREEN)

- [x] 3.1 `res.company._sync_enabled_sellers_from_connector()`; never `sudo()`; reuse
      `list_sellers()`.
- [x] 3.2 Settings Import button + `action_import_enabled_sellers` notification;
      invisible without connector; `base.group_system`.

## Phase 4: Lookup filter

- [x] 4.1 Invert the three unfiltered `get_seller_id` tests; enable the seller on
      remaining unique-match tests.
- [x] 4.2 Filter `get_seller_id` to `env.company.enabled_seller_ids`.

## Phase 5: Docs + verify

- [x] 5.1 Bump manifest `19.0.1.19.0`; update `AGENTS.md` and `readme/DESCRIPTION.md`.
- [x] 5.2 Optional sqlite Import TransactionCase (5 sample users, replace-all).
- [x] 5.3 `invoke test -m collection --mode=update` (+ sqlite if added); scoped
      pre-commit.
