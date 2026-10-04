# Delta for collection-connectors

## ADDED Requirements

### Requirement: Write path may create partners and bindings

`create_collection_vouchers` MAY create `res.partner` records and
`collection.connector.customer.binding` rows through `resolve_customer_partner`. MCP
read tools `list_collection_customers` and `customer_debt` MUST NOT create partners or
bindings.

#### Scenario: Write path provisions on all-new create

- GIVEN an all-new MCP payment for an unbound listable identification
- WHEN `create_collection_vouchers` runs
- THEN a partner and customer binding MAY be created
- AND `list_collection_customers` and `customer_debt` MUST still create neither

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
identification. VAT matching MUST use the exact stripped string (MUST NOT normalize
CUIT): one `res.partner.vat` match MUST bind that partner and MUST NOT create a new
partner; zero matches MUST create a partner (`vat` equals identification, `name` from
the ERP row, `company_id` from the connector, `customer_rank` 1, no extra tag) and a
binding; more than one match MUST raise the generic `UserError`. Unknown, inactive, or
other-seller identifications MUST raise the same generic `UserError`
(`The requested customer is not available.`) with no partner or binding writes.
Concurrent first-sighting UniqueViolation MUST converge on one partner and MUST NOT be
reported as a payment `document_id` conflict. Calls MUST NOT `sudo()`.

#### Scenario: Enabled Seller gate before lookup

- GIVEN an internal caller and a seller that is not enabled or not bound on the active
  connector
- WHEN `resolve_customer_partner` runs
- THEN the system MUST raise `UserError` before binding lookup or adapter dispatch
- AND MUST NOT create a partner or binding

#### Scenario: Binding fast path skips adapter

- GIVEN an Enabled Seller and an existing customer binding for identification I
- WHEN `resolve_customer_partner` runs with I
- THEN it MUST return that binding's partner
- AND MUST NOT call the adapter

#### Scenario: Unique vat binds existing partner

- GIVEN no binding for I, exactly one active ERP row for I, and exactly one partner
  whose `vat` equals I
- WHEN `resolve_customer_partner` runs
- THEN it MUST bind that partner and MUST NOT create a new partner

#### Scenario: No vat match creates partner

- GIVEN no binding for I, exactly one active ERP row for I, and no partner whose `vat`
  equals I
- WHEN `resolve_customer_partner` runs
- THEN it MUST create a partner with `vat` I, ERP name, connector company,
  `customer_rank` 1, and no extra tag
- AND MUST create a binding for that partner

#### Scenario: Ambiguous vat fails closed

- GIVEN no binding for I and more than one partner whose `vat` equals I
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

Internal users (`base.group_user`) MUST have read and create on
`collection.connector.customer.binding` and MUST NOT write or unlink (`1,0,1,0`).
`base.group_system` MUST have full CRUD. Allowed-company `ir.rule`
`[('company_id', 'in', company_ids)]` MUST hide other-company bindings. Dedicated groups
MUST NOT be added. Calls MUST NOT `sudo()`.

#### Scenario: User can create not mutate

- GIVEN an authenticated internal user
- WHEN they create a customer binding of an allowed company
- THEN ACL MUST allow create
- AND write or unlink MUST be denied

#### Scenario: Other-company bindings hidden

- GIVEN a customer binding in a company the user is not allowed
- WHEN they search bindings
- THEN that binding MUST NOT be visible

## MODIFIED Requirements

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
Success MUST return `{customer, summary, invoices}` with no `source` and no
`partner_id`. The tool MUST NOT create `res.partner` records or customer bindings.
Payload keys and values MUST remain byte-identical to the prior contract. (Previously:
Success forbade partner create as a global customer rule, without stating the payload
stays without `partner_id`.)

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
`issue_date`, `due_date`, `amount`, `balance`, and `state`. `get_customer_debt()` MUST
also attach `source` with `connector_id`, `connector_type`, `connector_name`, and
`company_id`. `customer_debt` MUST omit `source` and MUST NOT include `partner_id`. Paid
or zero-balance invoices MUST be omitted. An active customer with no outstanding
invoices MUST succeed with zero totals and an empty invoice list. Invoice order MUST be
deterministic (`due_date`, `number`, `external_invoice_id`). `get_customer_debt()` and
`customer_debt` MUST NOT create `res.partner` records or customer bindings. (Previously:
Customers remained connector data for every path, forbidding all partner and binding
creates.)

#### Scenario: Debt shape

- GIVEN an active customer with open, overdue, paid, and zero-balance invoices
- WHEN `get_customer_debt()` runs for the bound Enabled Seller
- THEN the payload MUST include that customer, outstanding open and overdue invoices
  only, matching totals, source metadata, and MUST NOT create partners or customer
  bindings

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
