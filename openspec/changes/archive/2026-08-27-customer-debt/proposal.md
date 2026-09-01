# Proposal: Add customer_debt MCP Tool

Sellers need one customer’s outstanding invoices and balances from the company
connector, without listing other sellers’ customers or writing the source.

## Intent

`list_collection_customers` can name customers. There is no read tool that returns one
active customer’s open and overdue invoices plus totals. Agents must not invent debt
from chat; the connector must answer.

## Scope

### In Scope

- Method-discovered MCP `customer_debt` (`category=read`, `registry=mcp`)
- Generic connector op `get_customer_debt` on the existing dispatcher allowlist
- Enabled-seller + connector-binding gates; dispatch external seller id + identification
- Normalized `{customer, summary, invoices, source}` payload
- SQLite read-only `invoices` lookup in `collection_connector_sqlite`
- OpenSpec delta on `collection-connectors` and canonical spec update on completion

### Out of Scope

- Nebula/LangGraph wrapper or first-party tool
- Database `muk_mcp.tool` row
- Creating `res.partner` or customer bindings
- Changing `database.sql` / sample schema
- Write-back, payments against invoices, or listing all customers’ debt

## Capabilities

### New Capabilities

- None (extends `collection-connectors`)

### Modified Capabilities

- `collection-connectors`: add seller-scoped customer debt read

## Approach

Keep the MCP contract in `collection`. Reuse `_collection_require_internal_seller`,
`_collection_active_connector`, and the same enabled/bound seller resolution as
`list_customers()`. Adapters return raw customer + invoice rows. The generic layer
rejects unknown, other-seller, and inactive customers with one generic `UserError`;
filters to positive-balance `open`/`overdue` invoices; computes totals; attaches source.
SQLite stays in the sibling addon: parameterized `mode=ro` reads, fixed `invoices`
schema, no path/SQL leakage, no file writes.

## Affected Areas

- Modified: `models/collection_connector.py` (`get_customer_debt` + format + allowlist)
- New: `tools/customer_debt.py`; `tests/test_collection_mcp_customer_debt.py`
- Modified: `tests/common_connector.py`, `tests/test_collection_connector.py`,
  `tests/__init__.py`, `tools/__init__.py`, `AGENTS.md`, `readme/DESCRIPTION.md`,
  `__manifest__.py`
- Modified (parent git): `collection_connector_sqlite` adapter, tests, readme, version
- Unchanged: voucher/sheet writes, `get_seller_id`, `list_collection_customers`
  contract, `database.sql`

## Risks

- Path/SQL leakage on SQLite errors (Med): generic `UserError`, no path/SQL in messages
- Cross-seller identification leak (Med): seller-scope the lookup; same generic error
- Combined PR over 400 lines (Med): collection facade then sqlite adapter as units
- Inactive customer with debt treated as collectable (Med): reject inactive like unknown

## Rollback Plan

Leave the new tool unused. Clearing `collection_connector_id` and uninstalling
`collection_connector_sqlite` leaves vouchers, sheets, `get_seller_id`,
`create_collection_vouchers`, and `list_collection_customers` unchanged.

## Dependencies

- `collection` + `muk_mcp`; sqlite addon already depends on `collection`; stdlib
  `sqlite3`; existing `customers`/`invoices` sample schema

## Success Criteria

- [ ] `customer_debt` is method-discovered read/mcp with no `muk_mcp.tool` row
- [ ] Enabled bound seller + active customer returns customer, summary, outstanding
      invoices, and source; zero-debt active customer returns zeros and `[]`
- [ ] Unknown, other-seller, and inactive customers raise generic `UserError` with no
      leak; portal/public get `AccessError`; never `sudo()`
- [ ] SQLite is read-only, parameterized, schema-checked, and does not write the file
- [ ] `database.sql` is unchanged; collection stays storage-agnostic
