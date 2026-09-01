# Tasks: Add customer_debt MCP Tool

## Review Workload Forecast

Estimated changed lines: 500–800. Delivery strategy: ask-on-risk.

Decision needed before apply: No (user asked to build the plan) Chained PRs recommended:
Optional Chain strategy: stacked-to-main 400-line budget risk: Medium

### Suggested Work Units

**Unit 1 — facade** (collection). Focused test command:
`invoke test -m collection --mode=update`. Rollback: collection git only.

**Unit 2 — sqlite**. Focused test command:
`invoke test -m collection_connector_sqlite --mode=update`. Rollback: sqlite adapter
methods + tests; `database.sql` untouched.

## Phase 1: OpenSpec + RED facade

- [x] 1.1 Write change proposal, design, tasks, and `collection-connectors` delta.
- [x] 1.2 RED test adapter + connector tests for `get_customer_debt` dispatch, shape,
      isolation, unknown/inactive/other-seller, zero debt, no SQLite in collection.
- [x] 1.3 RED MCP tests: discovery, schema, auth, payload, no leak, no `sudo()`, no
      `muk_mcp.tool` row. Import from `tests/__init__.py`.

## Phase 2: GREEN facade

- [x] 2.1 GREEN `collection.connector` allowlist, seller-binding resolution, payload
      formatting.
- [x] 2.2 GREEN `tools/customer_debt.py` + `tools/__init__.py`.
- [x] 2.3 Manifest `19.0.1.22.0`; `AGENTS.md`; `readme/DESCRIPTION.md`.

## Phase 3: SQLite adapter

- [x] 3.1 RED sqlite tests: success, zero debt, inactive/other-seller, malformed
      invoices schema, sample fixture, unchanged file bytes.
- [x] 3.2 GREEN parameterized read-only `_sqlite_get_customer_debt` + invoices schema
      check. Do not edit `database.sql`.
- [x] 3.3 Sqlite manifest `19.0.1.5.0` + `readme/DESCRIPTION.md`.

## Phase 4: Canonical spec + verify

- [x] 4.1 Update `openspec/specs/collection-connectors/spec.md`.
- [x] 4.2 Scoped pre-commit on collection and sqlite paths.
- [x] 4.3 `invoke test -m collection --mode=update`.
- [x] 4.4 `invoke test -m collection_connector_sqlite --mode=update`.
- [x] 4.5 Upgrade both modules in devel if the stack is available.
