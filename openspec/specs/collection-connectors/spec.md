# Collection Connectors Specification

## Purpose

Company-scoped seller sources imported into Enabled Sellers via `list_sellers()`. MCP
MUST NOT expose a seller-list tool. MCP MAY expose seller-scoped customer listing
through `list_collection_customers` and seller-scoped customer debt through
`customer_debt`. Read tools MUST NOT create `res.partner` records or customer bindings.
The voucher-create path and `resolve_customer_partner` MAY create `res.partner` records
and `collection.connector.customer.binding` rows.

## Requirements

### Requirement: Company-scoped connector

Each company MUST have at most one active company-scoped connector, settable from
Collection Settings.

#### Scenario: Persist connector

- GIVEN a company A administrator
- WHEN they save A's active connector in Collection Settings
- THEN A MUST use that connector and others MUST keep theirs

### Requirement: Active-company list routing

`list_sellers()`, Import, `list_customers()`, and `get_customer_debt()` MUST use only
`env.company.collection_connector_id` and MUST NOT accept caller `company_id`.

#### Scenario: Active company

- GIVEN company A's active connector is C
- WHEN an administrator with `env.company` A lists or Imports sellers, lists customers,
  or reads customer debt
- THEN the list MUST come from C and a caller company id MUST NOT be used

### Requirement: Fail closed without leakage

Missing, inactive, or misconfigured connectors MUST raise `UserError` with no path, SQL,
or secrets.

#### Scenario: Fail closed

- GIVEN the active company has no connector, or an inactive or misconfigured one
- WHEN `list_sellers()`, Import, `list_customers()`, or `get_customer_debt()` runs
- THEN it MUST raise `UserError` with no path, SQL, or secret and MUST NOT return
  sellers, customers, or debt

### Requirement: No MCP seller list

The system MUST NOT expose `list_collection_sellers` (or any other MCP tool that lists
connector sellers). Seller listing is ORM `collection.connector.list_sellers()` for
Import and Test Connection only.

#### Scenario: Not registered

- GIVEN the MCP registry for `registry=mcp`
- WHEN tools are discovered
- THEN `list_collection_sellers` MUST NOT appear and MUST NOT have a `muk_mcp.tool` row

### Requirement: Normalized seller list output

Success MUST return normalized sellers with source metadata, `odoo_seller_id` when bound
else unbound, and `commission_percent` as a float 0–100, and MUST exclude inactive
external sellers. A missing `commission_percent` key from the adapter MUST coerce to
`0.0`. (Previously: success rows had no `commission_percent`; extra adapter keys were
dropped.)

#### Scenario: List shape

- GIVEN one bound active seller, one unbound active seller, and one inactive external
  seller
- WHEN `list_sellers()` runs
- THEN active rows MUST include source metadata, bound `odoo_seller_id`, and
  `commission_percent` (float 0–100); inactive MUST be omitted

#### Scenario: Missing commission key coerces to zero

- GIVEN an active adapter seller row without `commission_percent`
- WHEN `list_sellers()` runs
- THEN that row MUST include `commission_percent` `0.0`
- AND inactive rows MUST still be omitted

### Requirement: Binding uniqueness

Bindings MUST be 1:1 external id to `res.users` per connector and company. Duplicates
MUST be rejected.

#### Scenario: Uniqueness

- GIVEN a binding of external id E to user U on connector C of company A
- WHEN a second binding on C reuses E or U, or uses another company
- THEN that binding MUST be rejected

### Requirement: List is not collect permission

Listing MUST NOT grant collect permission. A bound user MAY be absent from
`enabled_seller_ids` until Import. `_assert_new_work` MUST still gate NEW voucher
create.

#### Scenario: No collect

- GIVEN a bound listed seller not in `enabled_seller_ids`
- WHEN NEW voucher create is attempted for that seller
- THEN `_assert_new_work` MUST reject create while the list still includes them

### Requirement: Import enables connector sellers

Administrators (Collection Settings) and Collections Managers (Company Collection
Settings, scoped to their company) MUST be able to Import sellers from the company's
active connector; both MUST share one implementation,
`res.company._sync_enabled_sellers_from_connector`. Import MUST call `list_sellers()`
(MUST NOT add a new dispatcher op). An empty answer MUST raise `UserError` and change
nothing. For each _active_ connector seller, the system MUST reuse an existing binding
(refused with `UserError` when its user does not belong to this company), else reuse a
unique internal user of this company with the same normalized AR phone, else create an
internal user in this company (name + phone, `no_reset_password`, `base.group_user`,
login `collection.{company_id}.{external_seller_id}`). The system MUST upsert
`collection.connector.seller.binding` (`external_seller_id` 1:1 `user_id` per connector)
and MUST NOT give any existing user access to another company. Import MUST persist
`commission_percent` on `collection.connector.seller.binding`. A later Import MUST
overwrite the stored rate without creating a new user. Rate `0.0` is valid. An invalid
rate (`<0`, `>100`, or non-numeric) MUST raise `UserError` BEFORE any write, leaving
bindings and `enabled_seller_ids` unchanged. After a successful fetch, the imported
users MUST be added to `enabled_seller_ids` (`Command.link`). Enabled sellers missing
from the source MUST stay enabled and MUST be listed in a warning notification for a
manager to disable explicitly. Inactive external rows MUST be omitted (same as
`list_sellers()`). Users and old bindings MUST NOT be deleted when they fall off the
list. The settings Import button MUST be `base.group_system`, next to Enabled Sellers,
and MUST be invisible without a connector. Calls MUST NOT `sudo()` (the manager wizard
runs the import elevated, scoped to the checked company). (Previously: a successful
fetch replaced `enabled_seller_ids` (`Command.set`), so a partial answer disabled
sellers; the admin path also linked the company to matched users. Before that: upsert
did not persist or overwrite `commission_percent`; invalid rates were not a fail-closed
Import case.)

#### Scenario: Create match and bind, keep extras

- GIVEN an active connector with two active sellers (one unbound, one whose phone
  matches an existing internal user) and one inactive external seller, and a manual
  extra on Enabled Sellers
- WHEN an administrator runs Import
- THEN the system MUST create or reuse users, upsert bindings, omit the inactive row,
  and add the imported users to Enabled Sellers
- AND the manual extra MUST stay enabled and be named in a warning

#### Scenario: Binding reuse on re-import

- GIVEN a prior Import created users and bindings
- WHEN Import runs again with the same source
- THEN the same `res.users` ids MUST be reused (idempotent)

#### Scenario: Fail closed leaves the list unchanged

- GIVEN no connector, or an inactive or misconfigured one, an empty seller list, a
  source with duplicate phones, two source ids that resolve to the same user, or a
  binding to another company's user
- WHEN Import runs
- THEN the system MUST raise `UserError` and MUST NOT change `enabled_seller_ids` or
  create a partial user/binding set

#### Scenario: Persist and overwrite commission percent

- GIVEN a prior Import stored `commission_percent` `5.0` on a binding
- WHEN Import runs again with the same source id and rate `7.5`
- THEN the same `res.users` MUST be reused
- AND the binding `commission_percent` MUST become `7.5`

#### Scenario: Invalid commission fails closed before write

- GIVEN an active connector whose `list_sellers()` includes a rate `<0`, `>100`, or
  non-numeric
- WHEN Import runs
- THEN the system MUST raise `UserError` BEFORE any write
- AND bindings and `enabled_seller_ids` MUST be unchanged

#### Scenario: Zero commission is valid

- GIVEN an active connector seller with `commission_percent` `0.0`
- WHEN Import runs
- THEN the binding MUST store `0.0`
- AND Import MUST succeed

### Requirement: Read-only MCP tool list_collection_customers

The system MUST expose `list_collection_customers` via `@mcp_tool` on `muk_mcp.mixin`
(`category=read`, `registry=mcp`), method-discovered; MUST NOT add a DB `muk_mcp.tool`
record. Input MUST require integer `seller_id` (an internal `res.users` id). Calls MUST
use the authenticated user and MUST NOT `sudo()`. Success MUST return
`{customers: [...]}` with no `source` and no `partner_id`. The tool MUST NOT create
`res.partner` records or customer bindings. Payload keys and values MUST remain
byte-identical to the prior contract. (Previously: Success forbade partner create as a
global customer rule, without stating the payload stays without `partner_id`.)

#### Scenario: Registered read tool

- GIVEN the MCP registry for `registry=mcp`
- WHEN tools are discovered
- THEN `list_collection_customers` MUST appear as method/read/mcp and MUST NOT have a
  `muk_mcp.tool` row
- AND `list_collection_sellers` MUST still be absent

### Requirement: Collections User caller and Enabled Seller

Callers without Collections User (portal, public, plain internal) MUST receive
`AccessError`. Collections Users MUST be allowed.
`seller_id` MUST be an Enabled Seller on `env.company.enabled_seller_ids`. A missing
seller binding on the active connector MUST raise `UserError`. Failures MUST use generic
messages with no path, SQL, or secrets.

#### Scenario: Portal or public caller denied

- GIVEN a portal or public caller
- WHEN `list_collection_customers` runs
- THEN the system MUST raise `AccessError` and MUST NOT return customers

#### Scenario: Non-enabled or unbound seller rejected

- GIVEN a Collections User caller and a seller that is not on the current company's
  enabled list, or that has no binding on the active connector
- WHEN `list_collection_customers` runs with that `seller_id`
- THEN the system MUST raise `UserError` and MUST NOT return customers

### Requirement: Binding resolution and adapter dispatch

`list_customers()` MUST resolve the internal user through the connector's
`seller_binding_ids`, dispatch the **external** seller id to the adapter selected by
connector `type` (`list_customers` dispatcher op), and MUST NOT send the Odoo user id to
the adapter. Adapter methods MUST return raw customer rows. The generic `collection`
layer MUST filter inactive rows, normalize MCP fields, and attach connector source
metadata.

#### Scenario: External seller id forwarded

- GIVEN an Enabled Seller bound to external id E and raw rows for E and for another
  seller
- WHEN `list_customers()` runs for that internal user
- THEN the adapter MUST receive E and the result MUST include only E's active customers

### Requirement: Normalized customer list output

Success MUST return active customers only, each with `external_customer_id`, `name`,
`identification`, and `customer_code`. `list_customers()` MUST also attach `source` with
`connector_id`, `connector_type`, `connector_name`, and `company_id`.
`list_collection_customers` MUST omit `source` and MUST NOT include `partner_id`.
Inactive external customers MUST be omitted. `list_customers()` and
`list_collection_customers` MUST NOT create `res.partner` records or customer bindings.
(Previously: Customers remained connector data for every path, forbidding all partner
and binding creates.)

#### Scenario: List shape

- GIVEN one active and one inactive customer for the bound seller, and active customers
  for another seller
- WHEN `list_customers()` runs for the bound Enabled Seller
- THEN the payload MUST include only the bound seller's active customer, source
  metadata, and MUST NOT create partners or customer bindings

#### Scenario: MCP list omits source

- GIVEN one active customer for the bound seller
- WHEN `list_collection_customers` runs for the bound Enabled Seller
- THEN the payload MUST include that customer and MUST NOT include `source` or
  `partner_id`
- AND MUST NOT create partners or customer bindings

### Requirement: Read-only MCP tool customer_debt

The system MUST expose `customer_debt` via `@mcp_tool` on `muk_mcp.mixin`
(`category=read`, `registry=mcp`), method-discovered; MUST NOT add a DB `muk_mcp.tool`
record. Input MUST require integer `seller_id` and non-empty string
`customer_identification`. Calls MUST use the authenticated user and MUST NOT `sudo()`.
Success MUST return `{customer, summary, invoices, as_of}` with no `source` and no
`partner_id`; `as_of` is when the connector's copy of the ERP debt was taken (snapshot
refresh time, or read time for a live adapter), ISO 8601 in the company timezone.
Invoice row keys MUST follow Normalized customer debt output (including
`document_kind`). The tool MUST NOT create `res.partner` records or customer bindings.
A connector whose copy is too old MUST raise `ConnectorDataStaleError` (a `UserError`)
instead of answering. Top-level keys MUST remain `{customer, summary, invoices, as_of}`.
(Previously: `{customer, summary, invoices}` only; payload keys and values were
byte-identical to the prior contract.)

#### Scenario: Registered read tool

- GIVEN the MCP registry for `registry=mcp`
- WHEN tools are discovered
- THEN `customer_debt` MUST appear as method/read/mcp and MUST NOT have a `muk_mcp.tool`
  row
- AND `list_collection_sellers` MUST still be absent

### Requirement: Collections User caller and Enabled Seller for customer_debt

Callers without Collections User (portal, public, plain internal) MUST receive
`AccessError`. Collections Users MUST be allowed.
`seller_id` MUST be an Enabled Seller on `env.company.enabled_seller_ids`. A missing
seller binding on the active connector MUST raise `UserError`. Empty
`customer_identification` MUST raise `UserError`. Failures MUST use generic messages
with no path, SQL, or secrets.

#### Scenario: Portal or public caller denied

- GIVEN a portal or public caller
- WHEN `customer_debt` runs
- THEN the system MUST raise `AccessError` and MUST NOT return debt

#### Scenario: Non-enabled or unbound seller rejected

- GIVEN a Collections User caller and a seller that is not on the current company's
  enabled list, or that has no binding on the active connector
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
and `customer_code`; `summary` with `gross_total` (open invoices), `credit_total` (open
credit notes and advances the adapter reports, always positive), `net_total`, NET
`total_balance` (`gross_total − credit_total`; negative when credits exceed invoices),
`overdue_balance`, `open_balance`, and outstanding `invoice_count`; `invoices` with
`external_invoice_id`, `number`,
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

### Requirement: Storage-agnostic collection addon

The `collection` addon MUST remain storage-agnostic. It MUST NOT import `sqlite3`, open
database files, contain SQLite paths/table names/SQL, or otherwise connect to SQLite.
SQLite customer and invoice reads MUST live only in `collection_connector_sqlite`.

#### Scenario: No SQLite in collection

- GIVEN the `collection` addon source
- WHEN it is inspected for customer or invoice retrieval
- THEN it MUST contain no SQLite import, connection, path, table, or SQL implementation

### Requirement: SQLite read-only sellers source

SQLite MUST be read-only against fixed `sellers` (`id`, `name`, `mobile`, `active`,
`commission_percent`) with `commission_percent` REAL 0–100 CHECK. Admins MUST run a
connection-test against that same schema. Missing, unreadable, or invalid schema
(including a missing `commission_percent` column) MUST raise `UserError` with no path or
SQL. The file MUST NOT be written. (Previously: four columns `id`, `name`, `mobile`,
`active`.)

#### Scenario: Sqlite success

- GIVEN a readable file with the fixed schema and active rows
- WHEN list runs or an administrator runs connection-test
- THEN active sellers MUST be listed, the test MUST succeed, and the file MUST NOT be
  written

#### Scenario: Sqlite invalid

- GIVEN the file is missing, unreadable, or lacks the fixed schema
- WHEN list or connection-test runs
- THEN it MUST raise `UserError` with no path or SQL

#### Scenario: Sqlite missing commission column

- GIVEN a readable sellers table without `commission_percent`
- WHEN list or connection-test runs
- THEN it MUST raise `UserError` with no path or SQL
- AND the file MUST NOT be written

### Requirement: SQLite read-only customers source

SQLite MUST be read-only against fixed `customers` (`id`, `seller_id`, `name`,
`identification`, `customer_code`, `active`). Reads MUST filter by the dispatched
external seller id. Missing, unreadable, or invalid `customers` schema MUST raise
`UserError` with no path or SQL. Seller listing and connection-test MUST remain
sellers-only and compatible.

#### Scenario: Sqlite seller-scoped customers

- GIVEN a readable file with the fixed sellers and customers schemas, active and
  inactive customers for seller E, and customers for another seller
- WHEN `list_customers()` runs for the Enabled Seller bound to E
- THEN only E's active customers MUST be returned, the file MUST NOT be written, and
  other sellers' customers MUST be omitted

#### Scenario: Sqlite invalid customers schema

- GIVEN the file is missing the fixed `customers` schema
- WHEN `list_customers()` runs
- THEN it MUST raise `UserError` with no path or SQL
- AND `list_sellers()` and connection-test MUST still succeed when `sellers` is valid

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

- GIVEN existing vouchers, sheets, and working `get_seller_id` plus create MCP and
  `list_collection_customers`
- WHEN connectors are cleared and SQLite is uninstalled
- THEN those records and tools MUST stay unchanged

### Requirement: Write path may create partners and bindings

`create_collection_allocation` (inline `payments[]`) MAY create `res.partner` records
and `collection.connector.customer.binding` rows through `resolve_customer_partner`. MCP
read tools `get_collection_allocation`, `list_collection_customers`, and `customer_debt`
MUST NOT create partners or bindings. (Previously: Only `create_collection_vouchers` MAY
lazy-create; reads listed were `list_collection_customers` and `customer_debt`.)

#### Scenario: Write path provisions on all-new create

- GIVEN an all-new MCP payment for an unbound listable identification
- WHEN `create_collection_allocation` runs
- THEN a partner and customer binding MAY be created
- AND `get_collection_allocation`, `list_collection_customers`, and `customer_debt` MUST
  still create neither

#### Scenario: Get unbound does not provision

- GIVEN an enabled seller and an unbound identification
- WHEN `get_collection_allocation` runs
- THEN MUST return `{allocation: null}`
- AND MUST NOT create a partner or binding

### Requirement: Customer binding uniqueness

The system MUST persist `collection.connector.customer.binding` with UNIQUE
`(connector_id, external_customer_id)`, UNIQUE `(connector_id, identification)`, and
UNIQUE `(connector_id, partner_id)`. Binding company MUST match the connector company.
`customer_code` MAY be stored on the binding and MUST NOT be required on `res.partner`.

#### Scenario: Uniqueness on three axes

- GIVEN a binding of external id E, identification I, and partner P on connector C of
  company A
- WHEN a second binding on C reuses E, I, or P, or uses another company
- THEN that binding MUST be rejected

### Requirement: Customer partner resolution

`resolve_customer_partner(seller_id, identification)` MUST require a non-empty stripped
identification, then apply the Enabled Seller plus active-connector seller-binding gate
BEFORE any customer-binding lookup or adapter call. A binding hit on
`(connector_id, identification)` MUST return that `partner_id` with no adapter call. A
miss MUST dispatch `list_customers` and keep exactly one active row for that
identification. VAT matching MUST compare CUIT digits (dashed, digits-only, and
`AR`-prefixed forms match) among commercial partners only (no `parent_id`): one match
MUST bind that partner and MUST NOT create a new partner; zero matches MUST create a
partner (`vat` equals identification, `name` from the ERP row, `company_id` from the
connector, `customer_rank` 1 when `account` is installed, no extra tag) and a binding;
more than one match MUST raise the generic `UserError`. Unknown, inactive, or
other-seller identifications MUST raise the same generic `UserError`
(`The requested customer is not available.`) with no partner or binding writes.
Concurrent first-sighting UniqueViolation MUST converge on one partner and MUST NOT be
reported as a payment `document_id` conflict; a UniqueViolation on another binding
constraint MUST raise the generic `UserError`, never the raw database error. Collections
Users MAY create the partner (create-only contact rights). Calls MUST NOT `sudo()`.
(Previously: VAT matched the exact stripped string.)

#### Scenario: Enabled Seller gate before lookup

- GIVEN a Collections User caller and a seller that is not enabled or not bound on the
  active connector
- WHEN `resolve_customer_partner` runs
- THEN the system MUST raise `UserError` before binding lookup or adapter dispatch
- AND MUST NOT create a partner or binding

#### Scenario: Binding fast path skips adapter

- GIVEN an Enabled Seller and an existing customer binding for identification I
- WHEN `resolve_customer_partner` runs with I
- THEN it MUST return that binding's partner
- AND MUST NOT call the adapter

#### Scenario: Unique vat binds existing partner

- GIVEN no binding for I, exactly one active ERP row for I, and exactly one commercial
  partner whose `vat` digits equal I's
- WHEN `resolve_customer_partner` runs
- THEN it MUST bind that partner and MUST NOT create a new partner

#### Scenario: No vat match creates partner

- GIVEN no binding for I, exactly one active ERP row for I, and no commercial partner
  whose `vat` digits equal I's
- WHEN `resolve_customer_partner` runs
- THEN it MUST create a partner with `vat` I, ERP name, connector company,
  `customer_rank` 1 when `account` is installed, and no extra tag
- AND MUST create a binding for that partner

#### Scenario: Ambiguous vat fails closed

- GIVEN no binding for I and more than one commercial partner whose `vat` digits equal
  I's
- WHEN `resolve_customer_partner` runs
- THEN the system MUST raise `UserError` `The requested customer is not available.`
- AND MUST NOT create a partner or binding

#### Scenario: Unknown inactive or other-seller fails closed

- GIVEN an Enabled Seller and an unknown, inactive, or other-seller identification
- WHEN `resolve_customer_partner` runs
- THEN the system MUST raise `UserError` `The requested customer is not available.`
- AND MUST NOT create a partner or binding

#### Scenario: Concurrent first-sighting converges

- GIVEN two concurrent first-sightings of the same identification
- WHEN both resolve
- THEN exactly one partner and one binding MUST remain
- AND neither call MUST report a payment `document_id` conflict

### Requirement: Customer binding ACL

Collections Users (`collection.group_collection_user`) MUST have read and create on
`collection.connector.customer.binding` and MUST NOT write or unlink (`1,0,1,0`); plain
internal users get no access. `base.group_system` and Collections Managers MUST have
full CRUD. Allowed-company `ir.rule` `[('company_id', 'in', company_ids)]` MUST hide
other-company bindings. Calls MUST NOT `sudo()`.

#### Scenario: User can create not mutate

- GIVEN an authenticated Collections User
- WHEN they create a customer binding of an allowed company
- THEN ACL MUST allow create
- AND write or unlink MUST be denied

#### Scenario: Other-company bindings hidden

- GIVEN a customer binding in a company the user is not allowed
- WHEN they search bindings
- THEN that binding MUST NOT be visible

### Requirement: Seller binding stores commission percent

`collection.connector.seller.binding` MUST store `commission_percent` as a required
Float 0–100, default `0.0`, with an Odoo Constraint. The rate MUST NOT live on
`res.users`.

#### Scenario: Stored on binding not user

- GIVEN a successful Import of a seller with rate `5.0`
- WHEN the binding and user are read
- THEN the binding MUST have `commission_percent` `5.0`
- AND `res.users` MUST NOT have a commission field

#### Scenario: Out of range binding rejected

- GIVEN a seller binding write with `commission_percent` `<0` or `>100`
- WHEN the write is saved
- THEN the Odoo Constraint MUST reject it

### Requirement: Readonly commission UI

The connector form MUST show a Seller Bindings notebook with readonly
`external_seller_id`, `user_id`, and `commission_percent`. Collection Settings MUST show
a related readonly One2many of the active connector `seller_binding_ids` with user and
`commission_percent`, and MUST hide that list when no connector is set.

#### Scenario: Connector notebook

- GIVEN an active connector with at least one seller binding
- WHEN an administrator opens the connector form
- THEN a Seller Bindings notebook MUST show those three fields readonly

#### Scenario: Settings hidden without connector

- GIVEN a company with no active connector
- WHEN Collection Settings is opened
- THEN the seller-binding commission list MUST be hidden

#### Scenario: Settings shows stored rates

- GIVEN an active connector with imported bindings
- WHEN Collection Settings is opened
- THEN the One2many MUST show each binding's user and `commission_percent` readonly

### Requirement: MCP get_seller_id omits commission

MCP `get_seller_id` MUST still return `{seller_id}` only. The payload MUST NOT include
`commission_percent` or other binding fields.

#### Scenario: Lookup payload unchanged

- GIVEN a unique enabled seller for a mobile
- WHEN `get_seller_id` runs
- THEN the result MUST be `{seller_id}` only
- AND MUST NOT include `commission_percent`

### Requirement: Sample seller commission rates

When the active connector lists sample sellers Ana, Bruno, Carla, Diego, and Elena as
active, `list_sellers()` MUST report `commission_percent` `5.0`, `7.5`, `10.0`, `0.0`,
and `3.0` respectively. Inactive Facundo MUST be omitted. Import MUST persist those
active rates on bindings.

#### Scenario: Sample rates listed and imported

- GIVEN the sample connector source with those six sellers
- WHEN `list_sellers()` then Import runs
- THEN active rows and bindings MUST carry those five rates
- AND Facundo MUST be omitted

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

### Requirement: Connector RPC surface and credentials

`list_sellers`, `list_customers`, `get_customer_debt`, `resolve_customer_partner`, and
`create_receipt` MUST be `@api.private` (server-side callers only: MCP tools, Import,
allocation helpers). `test_connection` MUST stay public for the form button and MUST
check server-side that the caller is an administrator or a Collections Manager of the
connector's company. Connector credentials (user, password) and system settings (web
service URL, insecure TLS, CA bundle, SQLite path) MUST be returned and written only for
`base.group_system`; a Collections Manager's save MUST leave them untouched.
**Configure Connection** MUST open the persistent connector form in the current page.
The connector form MUST be the single configuration interface, using native Save and
Discard controls, with no separate settings transient or popup button. Managers MUST
be able to edit Bejerman company, workstation, branch, timeout and debt query options
on this form. The session deadline MUST remain system-only. Unused seller scenario/view
fields MUST NOT appear. Test Connection and Bejerman Refresh Debt MUST each appear once
for managers and administrators; refresh MUST check management access to the connector's
company before elevating the fixed operation.

#### Scenario: Manager never sees the password

- GIVEN a Collections Manager opens the connector form
- WHEN the form loads and is saved
- THEN the credential and system fields MUST be absent from what the manager reads
- AND the stored values MUST be unchanged after the save
- AND direct RPC reads, creates and writes of system fields MUST be refused

#### Scenario: Existing connectors survive consolidation

- GIVEN a connector configured before the settings popup was removed
- WHEN the collection and adapter addons are upgraded
- THEN connector values MUST be preserved and the retired popup views MUST be removed
- AND Configure Connection MUST open that connector's form

### Requirement: Debt freshness

Every formatted customer debt MUST carry `as_of`. A connector MAY raise
`ConnectorDataStaleError` (a `UserError`) when its copy of the ERP is too old to serve.
The allocation debt helpers MUST let that error through, so the Add Debt picker and a
new allocation refuse stale figures instead of showing an empty list; other connector
errors keep reading as no debt. The Add Debt picker MUST show the debt time
(`debt_as_of`) and the open invoices, open credits, and net (Customer Owes) totals.

#### Scenario: Stale snapshot refused in the picker

- GIVEN a connector whose debt snapshot is older than its configured maximum age
- WHEN a Collections User opens Add Debt on a draft allocation
- THEN the system MUST raise the connector's stale-data `UserError`
- AND MUST NOT show an empty candidate list
