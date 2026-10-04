# Delta for collection-allocations

## ADDED Requirements

### Requirement: Customer Debt snapshot and form

MUST snapshot every outstanding ERP invoice onto `line_ids` (including
`amount_applied` 0) via `collection_connector_id` plus customer binding. MUST NOT call
`_collection_active_connector()`. Onchange of Customer or Sheet MUST replace `line_ids`
when not confirmed. `create` MUST snapshot only when `line_ids` is omitted. Missing
connector or binding MUST yield empty lines and MUST NOT raise UserError. Upgrade MUST
NOT backfill existing allocations.

| Surface       | MUST                                                                                       |
| ------------- | ------------------------------------------------------------------------------------------ |
| Vouchers      | existing-only many2many (`no_create`); list includes `document_type`; row remove unassigns |
| Customer Debt | rename Invoices; parent-arch `document_kind` before `invoice_number`                       |
| Header        | Vouchers smart button domain `allocation_id`; no Residual Reason; six totals with helpers  |

#### Scenario: Full outstanding including zeros

- GIVEN binding, connector, ERP I1 (applied) and I2 (none)
- WHEN MCP create/amend or form snapshot runs
- THEN both lines MUST persist; I2 `amount_applied` MUST be 0

#### Scenario: Empty lines without connector

- GIVEN no connector or no customer binding
- WHEN Customer/Sheet onchanges or create omits `line_ids`
- THEN `line_ids` MUST be empty; MUST NOT raise UserError

#### Scenario: Create omitted vs supplied; no backfill

- GIVEN a binding
- WHEN `line_ids` omitted, snapshot MUST persist; WHEN supplied, those lines MUST
  persist without a second fetch
- THEN existing allocations MUST keep prior lines (no backfill)

#### Scenario: Existing-only vouchers and smart button

- GIVEN a draft allocation form
- WHEN Vouchers tab or smart button is used
- THEN selector MUST be existing-only same customer+sheet; button domain MUST be
  `allocation_id`; row remove MUST unassign

#### Scenario: Customer Debt parent arch

- GIVEN the parent allocation form
- WHEN notebook and totals are inspected
- THEN page MUST be Customer Debt with parent-arch `document_kind` before
  `invoice_number`, helpers on six totals, and no Residual Reason

### Requirement: Totals and residual formula

| Field                                 | MUST                                                              |
| ------------------------------------- | ----------------------------------------------------------------- |
| `total_debt`                          | sum(`invoice_balance`); computed; MUST NOT store MCP `total_debt` |
| `total_invoices` / `total_quotations` | sum balance where `document_kind` is invoice / quotation          |
| `total_vouchers` / `total_applied`    | sum voucher amounts / sum `amount_applied`                        |
| `residual`                            | `total_debt − total_applied`; negative MUST be allowed            |
| `amount_applied`                      | default 0; MUST be `>= 0`                                         |

Allocation and revision MUST NOT persist `residual_reason`. Sheet report MUST NOT read
it. MCP create MAY send `residual_reason` and MUST ignore it.

#### Scenario: Residual and zeros

- GIVEN debt 150 applied 40, or applied > debt, or a zero-applied line
- WHEN totals compute or save
- THEN residual MUST be 110, or negative MUST save, and zero-applied MUST persist

#### Scenario: Reason dropped from persist

- GIVEN MCP create with `residual_reason` or a sheet print
- WHEN persist or report runs
- THEN reason MUST NOT be stored or read

## MODIFIED Requirements

### Requirement: Idempotency and amend

MUST replay identical `request_id` (zero writes) with
`{sheet_id, vouchers[], allocation}` in submit order. Matching `content_hash` (new
`request_id`, no extra revision) MUST NOT include `residual_reason`. Amend MUST be
voucher SUPERSET (`revision`+1) only while `draft`. MUST reject subset/partial overlap
and `state != draft`. `UniqueViolation` MUST invalidate then replay or generic-conflict
with no ids. (Previously: Hash included `residual_reason`; reason-only retry was not a
no-op.)

#### Scenario: Replay by request_id, content_hash, or UniqueViolation

- GIVEN a prior create or concurrent `UNIQUE(request_id)` insert
- WHEN identical `request_id`, same content with a new `request_id`, or race
- THEN zero writes, no extra revision, or invalidate-replay/generic-conflict with no
  ids; `request_id` replay MUST return `sheet_id` plus ordered `vouchers[]`

#### Scenario: Amend voucher superset or overlap

- GIVEN draft {V1,V2} or destination `confirmed`
- WHEN payload is {V1,V2,V3}, {V1}, {V2,V3}, or amend after confirm
- THEN SUPERSET on draft MUST `revision`+1 and link V3; else MUST error with no writes

#### Scenario: Residual reason excluded from content_hash

- GIVEN a draft allocation whose hash omits `residual_reason`
- WHEN retry uses the same vouchers/invoices and a different `residual_reason`
- THEN MUST treat content as unchanged (MUST NOT amend for reason alone)

### Requirement: Revalidation and residual

Each payload `external_invoice_id` with `amount_applied > 0` MUST remain in fresh ERP
debt. Available = fresh balance − other `draft`/`confirmed` applications.
`amount_applied` MUST be `>= 0` and `<=` available. Persist MUST then expand to every
currently outstanding ERP invoice: payload applied amount, else 0. MUST ignore (not
refuse) payload rows with `amount_applied` 0 that are not outstanding. Empty
`invoices[]` MUST expand to all outstanding zeros. `total_debt` MUST be the computed
line sum, MUST NOT be written from ERP summary, MUST NOT require caller equality.
Residual MUST be `total_debt − total_applied`; negative MUST be allowed; MUST NOT
require `residual_reason`. (Previously: Payload-only lines; `amount_applied > 0`;
residual = vouchers − applied `>= 0` with reason iff > 0; MCP wrote `total_debt`.)

#### Scenario: Fresh debt, residual, and both-state constraint

- GIVEN invoice I in fresh debt, other draft or confirmed apply A, caller `total_debt` ≠
  fresh snapshot
- WHEN apply B, empty invoices, residual > 0 or < 0
- THEN available = fresh − A; B > available errors; `total_debt` is computed; empty
  invoices expand to outstanding zeros; residual MAY be negative; MUST NOT require
  `residual_reason` while `draft` or `confirmed`

#### Scenario: Residual holds on draft and confirmed

- GIVEN residual any sign and no `residual_reason`
- WHEN the allocation is `draft` or `confirmed`
- THEN persist MUST succeed

#### Scenario: Expand applied-only payload

- GIVEN fresh ERP I1 and I2 and payload applying only I1
- WHEN create or amend runs
- THEN I1 MUST keep payload `amount_applied` and I2 MUST persist at 0; a payload row
  with `amount_applied > 0` missing from ERP MUST refuse; a zero-applied missing row
  MUST NOT refuse

### Requirement: Source detach residual refuse

When a voucher would leave a `draft` allocation, the system MUST NOT project residual as
current residual minus that voucher's amount. Residual MUST stay
`total_debt − total_applied`. Draft detach/attach MUST NOT refuse because
leftover-voucher residual would be `< 0` or because residual is 0. MUST NOT unallocate a
voucher solely to avoid a negative residual. Detach from a `confirmed` allocation MUST
be refused. (Previously: Projected residual − voucher amount; fully applied and leftover
underflow refused on draft.)

#### Scenario: Fully applied source detach allowed

- GIVEN a draft allocation with residual 0 and a linked voucher
- WHEN that voucher is moved off (including via `partner_id` write)
- THEN the move MUST succeed and residual MUST be unchanged (MUST NOT ± voucher amount)

#### Scenario: Leftover-voucher residual MUST NOT refuse detach

- GIVEN a draft allocation whose residual is less than the voucher amount
- WHEN that voucher is detached
- THEN the move MUST succeed and residual MUST stay `total_debt − total_applied`

#### Scenario: Draft detach without leftover projection

- GIVEN a draft allocation
- WHEN that voucher is detached
- THEN the move MUST succeed and residual MUST NOT be projected as residual ± voucher
  amount

#### Scenario: Confirmed source detach refused

- GIVEN a confirmed allocation with a linked voucher
- WHEN that voucher is detached
- THEN the move MUST be refused and `voucher_ids` MUST be unchanged

### Requirement: MCP get_collection_allocation

MUST expose `get_collection_allocation` via `@mcp_tool` on `muk_mcp.mixin`
(`category=read`, `registry=mcp`), method-discovered; MUST NOT add a `muk_mcp.tool` row.
Input MUST be `{seller_id, customer_identification}`. Portal/public MUST receive
`AccessError`. Internal callers MUST pass Enabled Seller plus active-connector
seller-binding gates. Open sheet MUST use `_open_sheets_for_seller`, MUST NOT
`_resolve_open_sheet_id_for_create`. Unbound identification, no open sheet, or no
allocation MUST return `{allocation: null}` and MUST NOT create partner, binding, or
sheet. Found MUST return list `vouchers` and `invoices` (even empty); MUST NOT return
`residual_reason`; invoice rows MUST include `document_kind` (default `invoice`) plus
existing keys; MUST NEVER include attachments or base64. Found open-sheet `state` MUST
be `draft`. MUST NOT return `validated` or `rejected`. Multi-open MUST raise existing
multi-open `UserError`. Errors MUST be raised, NEVER `{"error":...}`. Every branch MUST
write zero rows. MUST NOT `sudo()`. (Previously: Found returned `residual_reason`;
invoice rows omitted `document_kind`.)

#### Scenario: Registered read tool

- GIVEN the MCP registry for `registry=mcp`
- WHEN tools are discovered
- THEN `get_collection_allocation` MUST appear as method/read/mcp and MUST NOT have a
  `muk_mcp.tool` row

#### Scenario: Unbound or missing returns null

- GIVEN an enabled seller and an unbound identification, or no open sheet, or an open
  sheet with no allocation
- WHEN `get_collection_allocation` runs
- THEN the body MUST be `{allocation: null}` with no partner, binding, or sheet create

#### Scenario: Found payload and draft state

- GIVEN one open sheet and an allocation
- WHEN `get_collection_allocation` runs
- THEN payload MUST list `vouchers` and `invoices` (even empty), include invoice
  `document_kind`, omit `residual_reason`, never attachments or base64; `state` MUST be
  `draft` with zero writes

#### Scenario: Multi-open sheet and auth fail closed

- GIVEN more than one open sheet, or a non-internal / non-enabled seller
- WHEN `get_collection_allocation` runs
- THEN MUST raise (multi-open `UserError` or AccessError/UserError) with zero writes and
  MUST NOT return `{"error":...}`

### Requirement: Allocation line document_kind

Each `collection.allocation.line` MUST have required Selection `document_kind`
`invoice`/`quotation` only, default `invoice`. Snapshotted connector rows MUST default
`invoice`. Operators MUST set `quotation` on a draft line. The form line list MUST show
`document_kind` immediately before `invoice_number` on the parent arch (MUST NOT rely on
inherit). That list MUST use `<list>` (MUST NOT `<tree>`). MCP
`create_collection_allocation` payload and write response MUST NOT gain `document_kind`;
omitted kind MUST persist `invoice`. Get invoice rows MUST include `document_kind`.
(Previously: Inherit-only inject; MUST NOT edit `collection_allocation_views.xml`; get
omitted kind.)

#### Scenario: Default invoice

- GIVEN a new allocation line with no `document_kind` in vals
- WHEN the line is created (ORM or MCP)
- THEN `document_kind` MUST be `invoice`

#### Scenario: Required selection

- GIVEN the line field
- WHEN selection and requiredness are inspected
- THEN values MUST be exactly `invoice` and `quotation` and the field MUST be required

#### Scenario: Quotation round-trip on draft

- GIVEN a draft allocation line
- WHEN `document_kind` is written `quotation` and read back
- THEN stored `document_kind` MUST be `quotation`

#### Scenario: Parent arch before invoice_number

- GIVEN the allocation form line list parent arch
- WHEN field order is inspected
- THEN `document_kind` MUST appear immediately before `invoice_number` and the line list
  tag MUST be `<list>`

#### Scenario: MCP create omits kind; get returns kind

- GIVEN a valid `create_collection_allocation` payload with invoices and no
  `document_kind` key
- WHEN the write tool succeeds and get later runs
- THEN each created line MUST have `document_kind` `invoice`; write request/response
  MUST omit kind; get invoice rows MUST include it
