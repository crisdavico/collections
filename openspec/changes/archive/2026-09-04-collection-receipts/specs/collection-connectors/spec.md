# Delta for Collection Connectors

## ADDED Requirements

### Requirement: Dispatcher allowlist includes create_receipt

The connector dispatcher allowlist MUST include `test_connection`, `list_sellers`,
`list_customers`, `get_customer_debt`, and `create_receipt`. Unknown ops MUST fail
closed with `UserError` and no path, SQL, or secrets. `create_receipt` MUST use only
`env.company.collection_connector_id` and MUST NOT accept caller `company_id`. Import
MUST still call `list_sellers()` only (MUST NOT use `create_receipt` for Import).

#### Scenario: create_receipt is allowlisted

- GIVEN an active company connector
- WHEN `create_receipt` is dispatched
- THEN the op MUST be allowed (MUST NOT fail as an unknown dispatcher op)

#### Scenario: Unknown op still fail closed

- GIVEN an active connector
- WHEN an op other than the five allowlisted names is dispatched
- THEN MUST raise `UserError` with no path, SQL, or secret

#### Scenario: Import still uses list_sellers only

- GIVEN an administrator Import
- WHEN Import runs
- THEN it MUST call `list_sellers()` and MUST NOT dispatch `create_receipt`

### Requirement: SQLite stub create_receipt

The SQLite connector MUST implement `create_receipt`. Success MUST return a
deterministic fake external receipt id. The sqlite file MUST NOT be written (MUST NOT
persist a receipts table). Missing, unreadable, or misconfigured sqlite MUST raise
`UserError` with no path or SQL.

#### Scenario: Stub returns fake id without write

- GIVEN a readable sqlite connector and a draft receipt to issue
- WHEN `create_receipt` is dispatched
- THEN the adapter MUST return a deterministic fake id
- AND the sqlite file MUST NOT be written

#### Scenario: Stub fail closed

- GIVEN no sqlite file or an inactive sqlite connector
- WHEN `create_receipt` is dispatched
- THEN MUST raise `UserError` with no path or SQL
- AND MUST NOT write a sqlite file

## MODIFIED Requirements

### Requirement: Read-only MCP tool customer_debt

The system MUST expose `customer_debt` via `@mcp_tool` on `muk_mcp.mixin`
(`category=read`, `registry=mcp`), method-discovered; MUST NOT add a DB `muk_mcp.tool`
record. Input MUST require integer `seller_id` and non-empty string
`customer_identification`. Calls MUST use the authenticated user and MUST NOT `sudo()`.
Success MUST return `{customer, summary, invoices}` with no `source` and no
`partner_id`. Invoice row keys MUST follow Normalized customer debt output (including
`document_kind`). The tool MUST NOT create `res.partner` records or customer bindings.
Top-level keys MUST remain `{customer, summary, invoices}`. (Previously: Payload keys
and values MUST remain byte-identical to the prior contract.)

#### Scenario: Registered read tool

- GIVEN the MCP registry for `registry=mcp`
- WHEN tools are discovered
- THEN `customer_debt` MUST appear as method/read/mcp and MUST NOT have a `muk_mcp.tool`
  row
- AND `list_collection_sellers` MUST still be absent

### Requirement: Normalized customer debt output

Success MUST return `customer` with `external_customer_id`, `name`, `identification`,
and `customer_code`; `summary` with `total_balance`, `overdue_balance`, `open_balance`,
and outstanding `invoice_count`; `invoices` with `external_invoice_id`, `number`,
`issue_date`, `due_date`, `amount`, `balance`, `state`, and `document_kind` (MUST
default `invoice` when the adapter omits it). Existing invoice keys MUST remain.
Quotations MAY appear as outstanding debt rows with `document_kind` `quotation`.
`invoice_count` MUST count outstanding debt rows including quotations.
`get_customer_debt()` MUST also attach `source` with `connector_id`, `connector_type`,
`connector_name`, and `company_id`. `customer_debt` MUST omit `source` and MUST NOT
include `partner_id`. Paid or zero-balance invoices MUST be omitted. An active customer
with no outstanding invoices MUST succeed with zero totals and an empty invoice list.
Invoice order MUST be deterministic (`due_date`, `number`, `external_invoice_id`).
`get_customer_debt()` and `customer_debt` MUST NOT create `res.partner` records or
customer bindings. (Previously: Invoice rows omitted `document_kind`; quotations were
not debt rows; customers remained connector data for every path.)

#### Scenario: Debt shape

- GIVEN an active customer with open, overdue, paid, and zero-balance invoices
- WHEN `get_customer_debt()` runs for the bound Enabled Seller
- THEN the payload MUST include that customer, outstanding open and overdue invoices
  only, matching totals, source metadata, `document_kind` default `invoice` on those
  rows, and MUST NOT create partners or customer bindings

#### Scenario: MCP debt omits source

- GIVEN an active customer with outstanding invoices
- WHEN `customer_debt` runs for the bound Enabled Seller
- THEN the payload MUST include that customer, outstanding invoices, matching totals,
  and MUST NOT include `source` or `partner_id`
- AND MUST NOT create partners or customer bindings

#### Scenario: Zero debt succeeds

- GIVEN an active customer with no outstanding invoices
- WHEN `get_customer_debt()` or `customer_debt` runs
- THEN the payload MUST include that customer, zero totals, `invoice_count` 0, and
  `invoices: []`

#### Scenario: Quotation debt rows

- GIVEN an active customer with an outstanding quotation and an outstanding invoice
- WHEN `get_customer_debt()` runs
- THEN both rows MUST appear; the quotation MUST have `document_kind` `quotation`
- AND existing invoice keys MUST still be present on both rows

### Requirement: SQLite read-only customer debt source

SQLite MUST be read-only against fixed `customers` and `invoices` (`id`, `customer_id`,
`number`, `issue_date`, `due_date`, `amount`, `balance`, `state`). Invoice rows MAY
include `document_kind`; when omitted the adapter MUST treat the row as `invoice`.
Outstanding quotations MAY appear as invoice-table rows with `document_kind` `quotation`
(coordinated adapter seed). Reads MUST filter by the dispatched external seller id and
identification with parameterized SQL. Missing, unreadable, or invalid `invoices` schema
MUST raise `UserError` with no path or SQL. Seller listing, connection-test, and
customer listing MUST remain compatible. The file MUST NOT be written. (Previously:
invoices columns excluded `document_kind`; quotations were not debt rows; froze
database.sql.)

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

#### Scenario: Sqlite kind and quotations without write

- GIVEN an active customer of E with an outstanding invoice and an outstanding quotation
  seed
- WHEN `get_customer_debt()` runs
- THEN both outstanding rows MUST be returned with `document_kind`
- AND the sqlite file MUST NOT be written
