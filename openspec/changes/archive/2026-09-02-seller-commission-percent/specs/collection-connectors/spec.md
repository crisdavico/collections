# Delta for collection-connectors

## ADDED Requirements

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
`external_seller_id`, `user_id`, and `commission_percent`. Collection Settings MUST
show a related readonly One2many of the active connector `seller_binding_ids` with
user and `commission_percent`, and MUST hide that list when no connector is set.

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

## MODIFIED Requirements

### Requirement: Normalized seller list output

Success MUST return normalized sellers with source metadata, `odoo_seller_id` when bound
else unbound, and `commission_percent` as a float 0–100, and MUST exclude inactive
external sellers. A missing `commission_percent` key from the adapter MUST coerce to
`0.0`.
(Previously: success rows had no `commission_percent`; extra adapter keys were dropped.)

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

### Requirement: Import replaces Enabled Sellers

Administrators MUST be able to Import sellers from the company's active connector into
Collection Settings. Import MUST call `list_sellers()` (MUST NOT add a new dispatcher
op). For each _active_ connector seller, the system MUST reuse an existing binding, else
reuse a unique internal user with the same normalized AR phone, else create an internal
user (name + phone, `no_reset_password`, `base.group_user`, login
`collection.{company_id}.{external_seller_id}`). The system MUST upsert
`collection.connector.seller.binding` (`external_seller_id` 1:1 `user_id` per connector)
and MUST set `company_ids` to include this company. Import MUST persist
`commission_percent` on `collection.connector.seller.binding`. A later Import MUST
overwrite the stored rate without creating a new user. Rate `0.0` is valid. An invalid
rate (`<0`, `>100`, or non-numeric) MUST raise `UserError` BEFORE any write, leaving
bindings and `enabled_seller_ids` unchanged. After a successful fetch,
`enabled_seller_ids` MUST be replaced (`Command.set`) with the imported users. Manual
extras MUST drop unless they appear in the source. Inactive external rows MUST be
omitted (same as `list_sellers()`). Users and old bindings MUST NOT be deleted when they
fall off the list. The Import button MUST be `base.group_system`, next to Enabled
Sellers, and MUST be invisible without a connector. Calls MUST NOT `sudo()`.
(Previously: upsert did not persist or overwrite `commission_percent`; invalid rates
were not a fail-closed Import case.)

#### Scenario: Create match and bind then replace all

- GIVEN an active connector with two active sellers (one unbound, one whose phone
  matches an existing internal user) and one inactive external seller, and a manual
  extra on Enabled Sellers
- WHEN an administrator runs Import
- THEN the system MUST create or reuse users, upsert bindings, omit the inactive row,
  and replace Enabled Sellers with exactly the imported users

#### Scenario: Binding reuse on re-import

- GIVEN a prior Import created users and bindings
- WHEN Import runs again with the same source
- THEN the same `res.users` ids MUST be reused (idempotent)

#### Scenario: Fail closed leaves the list unchanged

- GIVEN no connector, or an inactive or misconfigured one, or a source with duplicate
  phones, or two source ids that resolve to the same user
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

### Requirement: SQLite read-only sellers source

SQLite MUST be read-only against fixed `sellers` (`id`, `name`, `mobile`, `active`,
`commission_percent`) with `commission_percent` REAL 0–100 CHECK. Admins MUST run a
connection-test against that same schema. Missing, unreadable, or invalid schema
(including a missing `commission_percent` column) MUST raise `UserError` with no path
or SQL. The file MUST NOT be written.
(Previously: four columns `id`, `name`, `mobile`, `active`.)

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

### Requirement: SQLite read-only customer debt source

SQLite MUST be read-only against fixed `customers` and `invoices` (`id`, `customer_id`,
`number`, `issue_date`, `due_date`, `amount`, `balance`, `state`). Reads MUST filter by
the dispatched external seller id and identification with parameterized SQL. Missing,
unreadable, or invalid `invoices` schema MUST raise `UserError` with no path or SQL.
Seller listing, connection-test, and customer listing MUST remain compatible. The file
MUST NOT be written.
(Previously: froze database.sql.)

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
