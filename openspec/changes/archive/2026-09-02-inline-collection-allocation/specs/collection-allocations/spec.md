# Delta for collection-allocations

## ADDED Requirements

### Requirement: MCP get_collection_allocation

MUST expose `get_collection_allocation` via `@mcp_tool` on `muk_mcp.mixin`
(`category=read`, `registry=mcp`), method-discovered; MUST NOT add a
`muk_mcp.tool` row. Input MUST be `{seller_id, customer_identification}`.
Portal/public MUST receive `AccessError`. Internal callers MUST pass Enabled
Seller plus active-connector seller-binding gates. Open sheet MUST be resolved
via `_open_sheets_for_seller` and MUST NOT use
`_resolve_open_sheet_id_for_create`. Unbound identification, no open sheet, or
no allocation MUST return `{allocation: null}` and MUST NOT create partner,
binding, or sheet. Found MUST return residual_reason plus `vouchers` and
`invoices` as lists (even empty); MUST NEVER include attachments or base64.
More than one open sheet MUST raise the existing multi-open `UserError`.
Errors MUST be raised, NEVER `{"error":...}` bodies. Every branch MUST write
zero rows. `validated` allocations MUST be returned with that `state`. MUST
NOT `sudo()`.

#### Scenario: Registered read tool

- GIVEN the MCP registry for `registry=mcp`
- WHEN tools are discovered
- THEN `get_collection_allocation` MUST appear as method/read/mcp
- AND MUST NOT have a `muk_mcp.tool` row

#### Scenario: Unbound or missing returns null

- GIVEN an enabled seller and an unbound identification, or no open sheet, or
  an open sheet with no allocation
- WHEN `get_collection_allocation` runs
- THEN the body MUST be `{allocation: null}`
- AND MUST NOT create partner, binding, or sheet

#### Scenario: Found payload and validated state

- GIVEN one open sheet and an allocation (including `validated`)
- WHEN `get_collection_allocation` runs
- THEN payload MUST include residual_reason and list `vouchers` and `invoices`
  (even empty), never attachments or base64
- AND `state` MUST be the stored allocation state with zero writes

#### Scenario: Multi-open sheet and auth fail closed

- GIVEN more than one open sheet, or a non-internal / non-enabled seller
- WHEN `get_collection_allocation` runs
- THEN MUST raise (multi-open `UserError` or AccessError/UserError)
- AND MUST NOT return `{"error":...}` and MUST write zero rows

## MODIFIED Requirements

### Requirement: MCP create_collection_allocation

MUST expose MCP write `create_collection_allocation` for Enabled Seller
internal callers (`category=write`, `registry=mcp`, method-discovered; MUST
NOT add a `muk_mcp.tool` row). Input MUST be:

| Key | Rule |
| --- | --- |
| seller_id | int > 0 |
| customer_identification | stripped string; top-level only; MUST NOT on payment items |
| request_id | required |
| payments[] | minItems 1; payment shape without customer_identification |
| invoices[] | REQUIRED; MAY be empty |
| residual_reason | nullable |
| total_debt | MAY be present; MUST be ignored |

Success output MUST be exactly `{sheet_id, vouchers, allocation}`:
`vouchers[]` one `{id,name,state,document_id}` row per submitted payment IN
SEND ORDER; `allocation` exactly seven keys
`{id,name,state,revision,total_vouchers,total_applied,residual}` with
`revision` a JSON int (MUST NOT be bool, float, or str). Persist `confirmed`
revision-1; `UNIQUE(sheet_id, partner_id)`. Unbound identification MUST
lazy-resolve via `resolve_customer_partner` on this write. When
`company.auto_create_sheet` is False, MUST raise a named `UserError` and
write zero rows. Exact same-company `document_id` set MUST reuse rows and
continue to allocation (MUST NOT voucher-style early-return). Partial overlap
or other-company hit MUST raise generic conflict with no writes. Revalidation
failure MUST roll back vouchers and allocation. Errors MUST be raised, NEVER
`{"error":...}` bodies. MUST NOT `sudo()`.
(Previously: Input used `vouchers` document_id strings and optional invoices;
output was `{allocation:{...}}` only; partner was binding-only; exact
document_id reuse was voucher-tool early-return.)

#### Scenario: First create

- GIVEN valid enabled-seller payload with inline `payments` and required
  `invoices` (MAY be `[]`)
- WHEN create with a new `request_id`
- THEN `confirmed`, `revision` 1 (int), matching totals, `sheet_id`, and
  `vouchers[]` in send order
- AND a second header for same (sheet, partner) MUST be unique-rejected

#### Scenario: Authorization denied

- GIVEN a non-internal or non-enabled seller
- WHEN the tool runs
- THEN the call MUST fail with no writes

#### Scenario: Response shape freeze

- GIVEN a successful create or `request_id` replay
- WHEN the body is inspected
- THEN top-level keys MUST be exactly `sheet_id`, `vouchers`, `allocation`
- AND `allocation` MUST have exactly those seven keys with int `revision`

#### Scenario: Exact document_id reuse continues

- GIVEN every submitted `document_id` already exists in the same company
- WHEN `create_collection_allocation` runs with a new `request_id`
- THEN those voucher rows MUST be reused and allocation MUST still persist
- AND MUST NOT return a voucher-only payload

#### Scenario: Partial overlap or other-company conflict

- GIVEN a partial same-company `document_id` overlap, or a hit only in another
  company
- WHEN `create_collection_allocation` runs
- THEN MUST raise generic conflict with no writes and no ids disclosed

#### Scenario: Revalidation rolls back vouchers

- GIVEN inline payments that would create vouchers and invoices that fail ERP
  revalidation
- WHEN create runs
- THEN MUST raise and MUST write zero vouchers and zero allocation

### Requirement: Input and sheet gates

Vouchers MUST be caller-company, amount > 0, not `rejected`, one partner, one
caller seller, one sheet. Those single-customer and single-sheet gates MUST
remain and MUST be reachable via `document_id` reuse. Customer MUST resolve
via `resolve_customer_partner` on this write (MAY create partner/binding);
MUST match voucher partner after resolve. Sheet MUST be `open` and same
company. When `auto_create_sheet` is False, MUST raise a named `UserError`
(company requires a sheet chosen in Odoo) with zero writes.
(Previously: Customer MUST resolve via existing binding only and MUST NOT
create partner/binding; auto_create_sheet False was not fail-closed here.)

#### Scenario: Ineligible input rejected

- GIVEN amount null/≤0, `rejected`, other company, other sheet, mixed
  partner/seller/sheet via reused `document_id`, partner mismatch after
  resolve, closed sheet, or other company sheet
- WHEN allocated
- THEN MUST error
- AND mixed-reuse and mismatch MUST NOT create a partner or binding

#### Scenario: Unbound write lazy-creates partner

- GIVEN an unbound listable identification and `auto_create_sheet` ON
- WHEN `create_collection_allocation` runs
- THEN a partner and customer binding MAY be created
- AND vouchers MUST share that partner

#### Scenario: auto_create_sheet off fail-closed

- GIVEN `company.auto_create_sheet` is False
- WHEN `create_collection_allocation` runs
- THEN MUST raise a named `UserError`
- AND MUST write zero vouchers, sheets, and allocations

### Requirement: Idempotency and amend

MUST replay identical `request_id` (zero writes) with the full
`{sheet_id, vouchers[], allocation}` payload, `vouchers[]` in submitted
order. Matching `content_hash` (new `request_id`, no extra revision) MUST
include `residual_reason` so a reason-only retry is not a silent no-op.
Amend MUST be voucher SUPERSET (`revision`+1). MUST reject subset/partial
overlap and `state != confirmed` (`validated`/`rejected` refuse amend).
`UniqueViolation` MUST invalidate then replay or generic-conflict with no
ids.
(Previously: Replay returned only `{allocation:{...}}`; `content_hash`
omitted `residual_reason`.)

#### Scenario: Replay by request_id, content_hash, or UniqueViolation

- GIVEN a prior create or concurrent `UNIQUE(request_id)` insert
- WHEN identical `request_id`, same content with a new `request_id`, or race
- THEN zero writes, no extra revision, or invalidate-replay/generic-conflict
  with no ids
- AND `request_id` replay MUST return `sheet_id` plus ordered `vouchers[]`

#### Scenario: Amend voucher superset or overlap

- GIVEN confirmed {V1,V2} or destination `validated`/`rejected`
- WHEN payload is {V1,V2,V3}, {V1}, {V2,V3}, or amend after decision
- THEN SUPERSET MUST `revision`+1 and link V3; else MUST error with no writes

#### Scenario: Residual reason participates in content_hash

- GIVEN a confirmed allocation whose hash includes residual_reason R
- WHEN amend retries with the same vouchers/invoices and a different reason
- THEN MUST NOT silent no-op; MUST treat content as changed
