# Delta for collection-connectors

## MODIFIED Requirements

### Requirement: Active-company list routing

`list_sellers()`, Import, `list_customers()`, and `get_customer_debt()` MUST use only
`env.company.collection_connector_id` and MUST NOT accept caller `company_id`.

#### Scenario: Active company

- GIVEN company A's active connector is C
- WHEN an administrator with `env.company` A lists or Imports sellers, lists customers,
  or reads customer debt
- THEN the result MUST come from C and a caller company id MUST NOT be used

### Requirement: Fail closed without leakage

Missing, inactive, or misconfigured connectors MUST raise `UserError` with no path, SQL,
or secrets.

#### Scenario: Fail closed

- GIVEN the active company has no connector, or an inactive or misconfigured one
- WHEN `list_sellers()`, Import, `list_customers()`, or `get_customer_debt()` runs
- THEN it MUST raise `UserError` with no path, SQL, or secret and MUST NOT return
  sellers, customers, or debt

### Requirement: Storage-agnostic collection addon

The `collection` addon MUST remain storage-agnostic. It MUST NOT import `sqlite3`, open
database files, contain SQLite paths/table names/SQL, or otherwise connect to SQLite.
SQLite customer and invoice reads MUST live only in `collection_connector_sqlite`.

#### Scenario: No SQLite in collection

- GIVEN the `collection` addon source
- WHEN it is inspected for customer or invoice retrieval
- THEN it MUST contain no SQLite import, connection, path, table, or SQL implementation

### Requirement: Company isolation

Company A MUST NOT list or use company B's connector.

#### Scenario: Isolation

- GIVEN company B has an active connector that A does not select
- WHEN a caller with `env.company` A lists sellers or customers, or reads customer debt
- THEN the result MUST NOT come from B's connector

### Requirement: Rollback unchanged

Clearing active connectors and uninstalling SQLite MUST leave vouchers, sheets,
`get_seller_id`, `create_collection_vouchers`, and `list_collection_customers`
unchanged.

#### Scenario: Rollback

- GIVEN existing vouchers, sheets, and working `get_seller_id`, create MCP, and
  `list_collection_customers`
- WHEN connectors are cleared and SQLite is uninstalled
- THEN those records and tools MUST stay unchanged

## ADDED Requirements

### Requirement: Read-only MCP tool customer_debt

The system MUST expose `customer_debt` via `@mcp_tool` on `muk_mcp.mixin`
(`category=read`, `registry=mcp`), method-discovered; MUST NOT add a DB `muk_mcp.tool`
record. Input MUST require integer `seller_id` and non-empty string
`customer_identification`. Calls MUST use the authenticated user and MUST NOT `sudo()`.
Success MUST return `{customer, summary, invoices, source}` with no `res.partner` create
and no customer bindings.

#### Scenario: Registered read tool

- GIVEN the MCP registry for `registry=mcp`
- WHEN tools are discovered
- THEN `customer_debt` MUST appear as method/read/mcp and MUST NOT have a `muk_mcp.tool`
  row
- AND `list_collection_sellers` MUST still be absent

### Requirement: Internal caller and Enabled Seller for customer_debt

Portal and public callers MUST receive `AccessError`. Internal callers MUST be allowed.
`seller_id` MUST be an Enabled Seller on `env.company.enabled_seller_ids`. A missing
seller binding on the active connector MUST raise `UserError`. Empty
`customer_identification` MUST raise `UserError`. Failures MUST use generic messages
with no path, SQL, or secrets.

#### Scenario: Portal or public caller denied

- GIVEN a portal or public caller
- WHEN `customer_debt` runs
- THEN the system MUST raise `AccessError` and MUST NOT return debt

#### Scenario: Non-enabled or unbound seller rejected

- GIVEN an internal caller and a seller that is not on the current company's enabled
  list, or that has no binding on the active connector
- WHEN `customer_debt` runs with that `seller_id`
- THEN the system MUST raise `UserError` and MUST NOT return debt

### Requirement: Unknown inactive or other-seller customer rejected

Unknown identification, a customer bound to another seller, and an inactive customer
MUST all raise the same generic `UserError`. The system MUST NOT reveal which case
matched, MUST NOT return invoices, and MUST NOT leak path or SQL.

#### Scenario: Inactive or foreign customer fails closed

- GIVEN an Enabled Seller bound to external id E, an inactive customer of E, an active
  customer of another seller, and an unknown identification
- WHEN `customer_debt` or `get_customer_debt()` runs for E with any of those
  identifications
- THEN the system MUST raise `UserError` with no leak and MUST NOT return debt

### Requirement: Binding resolution and adapter dispatch for customer debt

`get_customer_debt()` MUST resolve the internal user through the connector's
`seller_binding_ids`, dispatch the **external** seller id plus the identification to the
adapter selected by connector `type` (`get_customer_debt` dispatcher op), and MUST NOT
send the Odoo user id to the adapter. Adapter methods MUST return a raw customer row and
raw invoice rows. The generic `collection` layer MUST reject missing or inactive
customers, keep only invoices with positive balance and state `open` or `overdue`,
normalize fields, compute summary totals, and attach connector source metadata.

#### Scenario: External seller id forwarded

- GIVEN an Enabled Seller bound to external id E and raw rows for E and for another
  seller
- WHEN `get_customer_debt()` runs for that internal user and E's customer identification
- THEN the adapter MUST receive E plus that identification and the result MUST include
  only that customer's outstanding invoices

### Requirement: Normalized customer debt output

Success MUST return `customer` with `external_customer_id`, `name`, `identification`,
and `customer_code`; `summary` with `total_balance`, `overdue_balance`, `open_balance`,
and outstanding `invoice_count`; `invoices` with `external_invoice_id`, `number`,
`issue_date`, `due_date`, `amount`, `balance`, and `state`; plus `source` with
`connector_id`, `connector_type`, `connector_name`, and `company_id`. Paid or
zero-balance invoices MUST be omitted. An active customer with no outstanding invoices
MUST succeed with zero totals and an empty invoice list. Invoice order MUST be
deterministic (`due_date`, `number`, `external_invoice_id`). Customers MUST remain
connector data: the system MUST NOT create `res.partner` records or customer bindings.

#### Scenario: Debt shape

- GIVEN an active customer with open, overdue, paid, and zero-balance invoices
- WHEN `get_customer_debt()` or `customer_debt` runs for the bound Enabled Seller
- THEN the payload MUST include that customer, outstanding open and overdue invoices
  only, matching totals, source metadata, and MUST NOT create partners or customer
  bindings

#### Scenario: Zero debt succeeds

- GIVEN an active customer with no outstanding invoices
- WHEN `get_customer_debt()` or `customer_debt` runs
- THEN the payload MUST include that customer, zero totals, `invoice_count` 0, and
  `invoices: []`

### Requirement: SQLite read-only customer debt source

SQLite MUST be read-only against fixed `customers` and `invoices` (`id`, `customer_id`,
`number`, `issue_date`, `due_date`, `amount`, `balance`, `state`). Reads MUST filter by
the dispatched external seller id and identification with parameterized SQL. Missing,
unreadable, or invalid `invoices` schema MUST raise `UserError` with no path or SQL.
Seller listing, connection-test, and customer listing MUST remain compatible. The file
MUST NOT be written. `database.sql` MUST NOT change.

#### Scenario: Sqlite seller-scoped debt

- GIVEN a readable file with the fixed sellers, customers, and invoices schemas, an
  active customer of seller E with mixed invoices, an inactive customer of E with debt,
  and a customer of another seller
- WHEN `get_customer_debt()` runs for the Enabled Seller bound to E and the active
  customer's identification
- THEN only that customer's outstanding invoices MUST be returned and the file MUST NOT
  be written

#### Scenario: Sqlite zero debt

- GIVEN an active customer of E with no outstanding invoices
- WHEN `get_customer_debt()` runs for that identification
- THEN totals MUST be zero, `invoices` MUST be empty, and the file MUST NOT be written

#### Scenario: Sqlite invalid invoices schema

- GIVEN the file is missing the fixed `invoices` schema
- WHEN `get_customer_debt()` runs
- THEN it MUST raise `UserError` with no path or SQL
- AND `list_sellers()`, connection-test, and `list_customers()` MUST still succeed when
  those schemas are valid
