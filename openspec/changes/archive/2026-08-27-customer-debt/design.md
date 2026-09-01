# Design: Add customer_debt MCP Tool

## Technical Approach

MCP `customer_debt` lives on `muk_mcp.mixin` beside `list_collection_customers`. It
requires integer `seller_id` and non-empty `customer_identification`, resolves the
internal seller, then calls `collection.connector.get_customer_debt()`. That method
reuses enabled-seller + binding resolution, dispatches
`get_customer_debt(external_seller_id, identification)` to `_<type>_get_customer_debt`,
and formats the payload. SQLite implements the adapter only.

## Architecture Decisions

| Decision                          | Choice                                                     | Alternatives considered                         | Rationale                                     |
| --------------------------------- | ---------------------------------------------------------- | ----------------------------------------------- | --------------------------------------------- |
| Tool name                         | `customer_debt`                                            | `get_customer_debt`, `list_collection_invoices` | Plan contract; one customer, not a list tool  |
| Dispatcher op                     | `get_customer_debt` on existing allowlist                  | New mixin override per adapter                  | Same plugin pattern as `list_customers`       |
| Inactive / unknown / other seller | One generic `UserError`                                    | Distinct messages                               | No existence oracle or seller leak            |
| Zero debt                         | Success with zero totals and `invoices: []`                | Error “no debt”                                 | Active customer is valid; nothing outstanding |
| Invoice filter                    | Generic layer: `balance > 0` and state in `open`/`overdue` | Adapter-only filter                             | Storage-agnostic contract; paid/zero dropped  |
| Invoice id field                  | `external_invoice_id`                                      | `id`                                            | Matches `external_customer_id`                |
| Order                             | `due_date`, `number`, `external_invoice_id`                | Amount desc                                     | Deterministic; oldest due first for cobranzas |
| SQLite schema                     | Existing `invoices` columns; do not change `database.sql`  | New view / JSON                                 | Sample already has the required schema        |

## Data Flow

```
MCP caller ──customer_debt(seller_id, identification)──► muk_mcp.mixin
                    internal user; no sudo
                    _collection_require_internal_seller
                    env.company._collection_active_connector()
                              ▼
                    connector.get_customer_debt(internal_id, identification)
                    enabled + binding → external seller id
                    _dispatch get_customer_debt
                              ▼
                    _sqlite_get_customer_debt (or _test_*)
                    parameterized seller+identification lookup
                              ▼
         no/inactive customer → UserError
         else filter outstanding invoices, totals, source
```

## File Changes

### Unit 1 — collection facade

| File                                                    | Action | Description                                |
| ------------------------------------------------------- | ------ | ------------------------------------------ |
| `openspec/changes/customer-debt/**`                     | Create | Proposal, spec delta, design, tasks        |
| `tests/common_connector.py`                             | Modify | Test invoices + `_test_get_customer_debt`  |
| `tests/test_collection_connector.py`                    | Modify | Dispatch, shape, isolation, no SQLite      |
| `tests/test_collection_mcp_customer_debt.py`            | Create | Discovery, auth, payload, no leak, no sudo |
| `tests/__init__.py`                                     | Modify | Import MCP tests                           |
| `models/collection_connector.py`                        | Modify | Allowlist, resolve, format                 |
| `tools/customer_debt.py`                                | Create | `@mcp_tool` `customer_debt`                |
| `tools/__init__.py`                                     | Modify | Import tool                                |
| `__manifest__.py`, `AGENTS.md`, `readme/DESCRIPTION.md` | Modify | Version 19.0.1.22.0 + docs                 |
| `openspec/specs/collection-connectors/spec.md`          | Modify | Canonical contract (after GREEN)           |

### Unit 2 — sqlite adapter

| File                                                                   | Action | Description                                       |
| ---------------------------------------------------------------------- | ------ | ------------------------------------------------- |
| `collection_connector_sqlite/models/collection_connector.py`           | Modify | `_sqlite_get_customer_debt` + invoices schema     |
| `collection_connector_sqlite/tests/test_sqlite_connector.py`           | Modify | Success, zero debt, reject, schema, sample, bytes |
| `collection_connector_sqlite/__manifest__.py`, `readme/DESCRIPTION.md` | Modify | Version 19.0.1.5.0 + invoices contract            |

Unchanged: `data/database.sql`, voucher MCP, `get_seller_id`,
`list_collection_customers`.

## Interfaces / Contracts

MCP `customer_debt` (`category=read`, `registry=mcp`, method). Required: `seller_id`
(int), `customer_identification` (non-empty string).

Success:

```
{
  customer: {external_customer_id, name, identification, customer_code},
  summary: {total_balance, overdue_balance, open_balance, invoice_count},
  invoices: [{external_invoice_id, number, issue_date, due_date, amount, balance, state}],
  source: {connector_id, connector_type, connector_name, company_id}
}
```

`invoice_count` is the length of `invoices`. SQLite `invoices` columns: `id`,
`customer_id`, `number`, `issue_date`, `due_date`, `amount`, `balance`, `state`. Connect
remains `sqlite3.connect('file:%s?mode=ro' % path, uri=True)` after path checks.

## Testing Strategy

| Layer         | What to Test                                                                           | Approach                                                   |
| ------------- | -------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| Unit          | allowlist, binding gate, payload, inactive/unknown, isolation, no sqlite in collection | `invoke test -m collection --mode=update`                  |
| Integration   | sqlite schema, seller scope, zero debt, sample fixture, file bytes unchanged           | `invoke test -m collection_connector_sqlite --mode=update` |
| No-regression | `list_customers`, `get_seller_id`, voucher MCP                                         | existing tests                                             |

## Threat Matrix

| Boundary | Minimum adversarial cases              | Design response                   | RED tests          |
| -------- | -------------------------------------- | --------------------------------- | ------------------ |
| Auth     | portal/public; disabled/unbound seller | AccessError / generic UserError   | MCP tests          |
| Leak     | unknown/other/inactive; SQL errors     | one generic message; no path/SQL  | MCP + sqlite       |
| Scope    | other seller identification            | seller_id + identification lookup | connector + sqlite |
| Write    | sqlite file mutation                   | `mode=ro`; compare bytes          | sqlite success     |
| sudo     | MCP/tool source                        | never `sudo()`                    | source inspection  |

## Migration / Rollout

Bump collection `19.0.1.22.0` and sqlite `19.0.1.5.0`. No data migration. Rollback: stop
calling `customer_debt`; clear connector / uninstall sqlite leaves existing tools.

## Open Questions

None.
