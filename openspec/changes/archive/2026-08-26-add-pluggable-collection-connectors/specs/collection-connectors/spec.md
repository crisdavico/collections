# Collection Connectors Specification

## Purpose

Company-scoped seller sources listed over a read MCP tool.

## Requirements

### Requirement: Company-scoped connector

Each company MUST have at most one active company-scoped connector, settable from
Collection Settings.

#### Scenario: Persist connector

- GIVEN a company A administrator
- WHEN they save A's active connector in Collection Settings
- THEN A MUST use that connector and others MUST keep theirs

### Requirement: Active-company list routing

`list_collection_sellers` MUST use only `env.company.collection_connector_id` and MUST
NOT accept caller `company_id`.

#### Scenario: Active company

- GIVEN company A's active connector is C
- WHEN an internal caller with `env.company` A lists sellers
- THEN the list MUST come from C and a caller company id MUST NOT be used

### Requirement: Fail closed without leakage

Missing, inactive, or misconfigured connectors MUST raise `UserError` with no path, SQL,
or secrets.

#### Scenario: Fail closed

- GIVEN the active company has no connector, or an inactive or misconfigured one
- WHEN `list_collection_sellers` runs
- THEN it MUST raise `UserError` with no path, SQL, or secret and MUST NOT return
  sellers

### Requirement: Internal method-discovered read MCP

The list tool MUST be method-discovered (`category=read`), MUST NOT `sudo()` or add a
`muk_mcp.tool` row, and MUST deny portal and public callers.

#### Scenario: Auth

- GIVEN an internal user (`base.group_user`) and a portal or public caller
- WHEN each invokes `list_collection_sellers`
- THEN internal MUST run with no `sudo()` and no `muk_mcp.tool` row, and the other MUST
  be denied

### Requirement: Normalized seller list output

Success MUST return normalized sellers with source metadata, `odoo_seller_id` when bound
else unbound, and MUST exclude inactive external sellers.

#### Scenario: List shape

- GIVEN one bound active seller, one unbound active seller, and one inactive external
  seller
- WHEN `list_collection_sellers` runs
- THEN active rows MUST include source metadata and bound `odoo_seller_id`; inactive
  MUST be omitted

### Requirement: Binding uniqueness

Bindings MUST be 1:1 external id to `res.users` per connector and company. Duplicates
MUST be rejected.

#### Scenario: Uniqueness

- GIVEN a binding of external id E to user U on connector C of company A
- WHEN a second binding on C reuses E or U, or uses another company
- THEN that binding MUST be rejected

### Requirement: List is not collect permission

Listing MUST NOT grant collect permission. A bound user MAY be absent from
`enabled_seller_ids`. `_assert_new_work` MUST still gate NEW voucher create.

#### Scenario: No collect

- GIVEN a bound listed seller not in `enabled_seller_ids`
- WHEN NEW voucher create is attempted for that seller
- THEN `_assert_new_work` MUST reject create while the list still includes them

### Requirement: SQLite read-only sellers source

SQLite MUST be read-only against fixed `sellers` (`id`, `name`, `mobile`, `active`).
Admins MUST run a connection-test. Missing, unreadable, or invalid schema MUST raise
`UserError` with no path or SQL.

#### Scenario: Sqlite success

- GIVEN a readable file with the fixed schema and active rows
- WHEN list runs or an administrator runs connection-test
- THEN active sellers MUST be listed, the test MUST succeed, and the file MUST NOT be
  written

#### Scenario: Sqlite invalid

- GIVEN the file is missing, unreadable, or lacks the fixed schema
- WHEN list or connection-test runs
- THEN it MUST raise `UserError` with no path or SQL

### Requirement: Company isolation

Company A MUST NOT list or use company B's connector.

#### Scenario: Isolation

- GIVEN company B has an active connector that A does not select
- WHEN a caller with `env.company` A lists sellers
- THEN the result MUST NOT come from B's connector

### Requirement: Rollback unchanged

Clearing active connectors and uninstalling SQLite MUST leave vouchers, sheets,
`get_seller_id`, and `create_collection_vouchers` unchanged.

#### Scenario: Rollback

- GIVEN existing vouchers, sheets, and working `get_seller_id` plus create MCP
- WHEN connectors are cleared and SQLite is uninstalled
- THEN those records and tools MUST stay unchanged
