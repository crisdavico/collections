# collection-allocations Specification

## Purpose

Seller-validated allocations of sheet vouchers vs external invoices; Odoo revalidates
ERP debt; back-office validates or rejects.

## Requirements

### Requirement: MCP create_collection_allocation

MUST expose MCP write `create_collection_allocation` for Enabled Seller internal callers
(`category=write`, `registry=mcp`, method-discovered; MUST NOT add a `muk_mcp.tool`
row). Input MUST be:

| Key                     | Rule                                                                                                                                                                                                                                                                     |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| seller_id               | int > 0                                                                                                                                                                                                                                                                  |
| customer_identification | stripped string; top-level only; MUST NOT on payment items                                                                                                                                                                                                               |
| request_id              | required                                                                                                                                                                                                                                                                 |
| payments[]              | minItems 1; each item requires `document_id` and `seller_confirmed`; optional `raw_ocr` and `attachment`; voucher fields MUST come from `seller_confirmed`; `seller_confirmed.document_type` MUST be one of the seven catalog codes; amount MUST accept a decimal string |
| receipts[]              | REQUIRED; minItems 1; each item requires `document_kind` and `values[]`; `applications[]` MAY be empty (on account); amounts MUST accept decimal strings                                                                                                                 |

MUST NOT accept `invoices`, `splits`, `total_debt`, or `residual_reason`. Unknown keys
at any nested level MUST be rejected (see Strict nested-key parse).

`seller_confirmed.document_type` `unsupported` MUST raise `UserError` with no writes.
The six dump types `bank_transfer`, `check`, `echeck`, `cash_deposit`,
`retention_certificate`, and `cash` MUST persist when otherwise valid. Seller-declared
`cash` MUST persist with `attachment` and `raw_ocr` omitted or null.

Success output MUST be exactly `{sheet_id, vouchers, allocation}`: `vouchers[]` one
`{id,name,state,document_id}` row per submitted payment IN SEND ORDER; `allocation`
exactly seven keys `{id,name,state,revision,total_vouchers,total_applied,residual}` with
`revision` a JSON int (MUST NOT be bool, float, or str). Persist `draft` revision-1;
`UNIQUE(sheet_id, partner_id)`. Unbound identification MUST lazy-resolve via
`resolve_customer_partner` on this write. When `company.auto_create_sheet` is False,
MUST raise a named `UserError` and write zero rows. Exact same-company `document_id` set
MUST reuse rows and continue to allocation (MUST NOT voucher-style early-return).
Partial overlap or other-company hit MUST raise generic conflict with no writes.
Revalidation failure MUST roll back vouchers and allocation. Errors MUST be raised,
NEVER `{"error":...}` bodies. MUST NOT `sudo()`. (Previously: Four-type
`seller_confirmed`; amounts advertised as numbers only; `unsupported` reject was not
stated on this requirement; extra nested keys were ignored on payment objects.)

#### Scenario: First create

- GIVEN valid enabled-seller payload with inline `payments` and required `receipts`
  (`applications` MAY be `[]`)
- WHEN create with a new `request_id`
- THEN `draft`, `revision` 1 (int), matching totals, `sheet_id`, and `vouchers[]` in
  send order
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

- GIVEN a partial same-company `document_id` overlap, or a hit only in another company
- WHEN `create_collection_allocation` runs
- THEN MUST raise generic conflict with no writes and no ids disclosed

#### Scenario: Revalidation rolls back vouchers

- GIVEN inline payments that would create vouchers and receipts that fail ERP
  revalidation
- WHEN create runs
- THEN MUST raise and MUST write zero vouchers and zero allocation

#### Scenario: Unsupported payment write rejected

- GIVEN a payment whose `seller_confirmed.document_type` is `unsupported`
- WHEN `create_collection_allocation` runs
- THEN MUST raise `UserError`
- AND MUST write zero vouchers, receipts, and allocations

#### Scenario: Six dump types persist with decimal-string amounts

- GIVEN a valid one-customer dump for `bank_transfer`, `check`, `echeck`,
  `cash_deposit`, `retention_certificate`, or `cash` whose amounts are decimal strings
- WHEN create runs with a new `request_id`
- THEN allocation MUST persist `draft` with response `{sheet_id, vouchers, allocation}`
- AND `cash` MAY omit proof; the other five MAY include valid proof

### Requirement: Idempotency and amend

MUST replay identical `request_id` (zero writes) with
`{sheet_id, vouchers[], allocation}` in submit order. Matching `content_hash` (new
`request_id`, no extra revision) MUST NOT include `residual_reason`. Content hash MUST
include receipts (`document_kind`, values, applications including `balance_seen`). Amend
MUST be voucher SUPERSET (`revision`+1) only while `draft`. MUST reject subset/partial
overlap and `state != draft`. `UniqueViolation` MUST invalidate then replay or
generic-conflict with no ids. (Previously: Hash used invoices/splits; reason-only retry
was a no-op.)

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
- WHEN retry uses the same vouchers and receipts
- THEN MUST treat content as unchanged (MUST NOT amend for reason alone)

#### Scenario: Receipts enter content_hash

- GIVEN a draft allocation hashed from one invoice receipt
- WHEN retry uses the same payments but different receipt values, applications, or
  `document_kind`
- THEN MUST NOT treat content as unchanged

### Requirement: Input and sheet gates

Vouchers MUST be caller-company, amount > 0, one partner, one caller seller, one sheet.
All three voucher states (`draft`, `validated_seller`, `validated_collections`) MAY
allocate. MUST NOT refuse a voucher because it is not `rejected` (that state MUST NOT
exist). Those single-customer and single-sheet gates MUST remain and MUST be reachable
via `document_id` reuse. Customer MUST resolve via `resolve_customer_partner` on this
write (MAY create partner/binding); MUST match voucher partner after resolve. Sheet MUST
be `open` and same company. Successful persist MUST leave the allocation `draft` on that
open sheet. When `auto_create_sheet` is False, MUST raise a named `UserError` (company
requires a sheet chosen in Odoo) with zero writes. (Previously: Vouchers MUST be not
`rejected`.)

#### Scenario: Ineligible input rejected

- GIVEN amount null/≤0, other company, other sheet, mixed partner/seller/sheet via
  reused `document_id`, partner mismatch after resolve, closed sheet, or other company
  sheet
- WHEN allocated
- THEN MUST error
- AND mixed-reuse and mismatch MUST NOT create a partner or binding

#### Scenario: All voucher states may allocate

- GIVEN a caller-company voucher in `draft`, `validated_seller`, or
  `validated_collections` with amount > 0
- WHEN allocated
- THEN voucher state MUST NOT by itself refuse the allocation

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

### Requirement: Revalidation and residual

Each payload application with `amount_applied > 0` MUST remain in fresh ERP debt.
`balance_seen` MUST match the fresh connector invoice `balance` via
`currency.compare_amounts`; a stale snapshot MUST raise with no writes. Available =
fresh balance − other `draft`/`confirmed` applications. `amount_applied` MUST be `> 0`
and `<=` available and `<= balance_seen`. Persist MUST then expand to every currently
outstanding ERP invoice: payload applied amount, else 0. Empty `applications[]` MUST
expand to all outstanding zeros (on account). `total_debt` MUST be the computed line
sum, MUST NOT be written from ERP summary, MUST NOT require caller equality. Residual
MUST be `total_debt − total_applied`; negative MUST be allowed; MUST NOT require
`residual_reason`. (Previously: Payload-only lines; empty `invoices[]` meant on account;
MCP wrote `total_debt`.)

#### Scenario: Fresh debt, residual, and both-state constraint

- GIVEN invoice I in fresh debt, other draft or confirmed apply A, caller omits
  `total_debt`
- WHEN apply B, empty applications, residual > 0 or < 0
- THEN available = fresh − A; B > available errors; stale `balance_seen` errors;
  `total_debt` is computed; empty applications expand to outstanding zeros; residual MAY
  be negative; MUST NOT require `residual_reason` while `draft` or `confirmed`

#### Scenario: Residual holds on draft and confirmed

- GIVEN residual any sign and no `residual_reason`
- WHEN the allocation is `draft` or `confirmed`
- THEN persist MUST succeed

#### Scenario: Expand applied-only payload

- GIVEN fresh ERP I1 and I2 and payload applying only I1
- WHEN create or amend runs
- THEN I1 MUST keep payload `amount_applied` and I2 MUST persist at 0; a payload row
  with `amount_applied > 0` missing from ERP MUST refuse

### Requirement: Freeze, revisions, ACL, back-office

When `state` is `confirmed`, freeze `line_ids`/`voucher_ids`/`receipt_ids`/
`partner_id`/`sheet_id`. When `state` is `draft`, those fields MUST remain writable
subject to other rules. O2M Command.DELETE MUST NOT destroy vouchers. Revisions
immutable, `UNIQUE(request_id)`, company `ir.rule`, no sudo. Direct revision write and
unlink MUST remain forbidden. MUST NOT delete a `confirmed` allocation. Draft unlink
with revisions is specified under Draft unlink with revisions. MUST NOT expose Validate
or Reject; `action_validate` and `action_reject` MUST NOT remain; `validated` and
`rejected` MUST NOT remain as states. (Previously: Freeze omitted `receipt_ids`; freeze
when `state != confirmed`; unlink with revisions refused; back-office validate/reject
then amend refused.)

#### Scenario: Freeze when confirmed

- GIVEN a confirmed allocation with linked vouchers
- WHEN frozen fields are written or O2M Command.DELETE runs
- THEN frozen writes MUST be refused
- AND vouchers MUST persist (DELETE MUST unassign, not destroy)

#### Scenario: Draft membership remains writable

- GIVEN a draft allocation
- WHEN `line_ids`, `voucher_ids`, `receipt_ids`, `partner_id`, or `sheet_id` are written
  lawfully
- THEN the write MUST persist

#### Scenario: Direct revision mutation forbidden

- GIVEN a stored revision
- WHEN revision write, unlink, or duplicate `request_id` is attempted
- THEN the operation MUST fail under company `ir.rule` with no sudo

#### Scenario: Validate and Reject gone

- GIVEN an allocation in `draft` or `confirmed`
- WHEN Validate or Reject is invoked
- THEN the action MUST NOT exist
- AND `state` MUST stay `draft` or `confirmed`

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

### Requirement: Partner match after voucher write

Every allocated voucher's `partner_id` MUST equal the allocation `partner_id` after
voucher `partner_id` or `allocation_id` writes, not only after allocation `partner_id`
or `voucher_ids` writes. A mismatch MUST be refused with no persist. (Previously:
Same-write attach used a confirmed same-sheet target.)

#### Scenario: Voucher partner write mismatch refused

- GIVEN a voucher linked to an allocation for partner P
- WHEN `partner_id` is written to Q without a matching `allocation_id` in the same vals
- THEN the write MUST be refused
- AND the voucher MUST remain on P and that allocation

#### Scenario: Same-write matching partner and allocation

- GIVEN a voucher on allocation A (partner P) and draft same-sheet allocation B (partner
  Q) with attachable residual
- WHEN `partner_id` is written to Q with `allocation_id` B in the same vals
- THEN partner match MUST hold
- AND the voucher MUST belong to B

### Requirement: MCP get_collection_allocation

MUST expose `get_collection_allocation` via `@mcp_tool` on `muk_mcp.mixin`
(`category=read`, `registry=mcp`), method-discovered; MUST NOT add a `muk_mcp.tool` row.
Input MUST be `{seller_id, customer_identification}`. Portal/public MUST receive
`AccessError`. Internal callers MUST pass Enabled Seller plus active-connector
seller-binding gates. Open sheet MUST use `_open_sheets_for_seller`, MUST NOT
`_resolve_open_sheet_id_for_create`. Unbound identification, no open sheet, or no
allocation MUST return `{allocation: null}` and MUST NOT create partner, binding, or
sheet. Found MUST return list `vouchers`, `invoices`, and `receipts` (even empty); MUST
NOT return `residual_reason`; invoice rows MUST include `document_kind` (default
`invoice`) plus existing keys; each receipts item MUST include `document_kind`, `state`,
`external_receipt_id`, totals, and values (payment identity + amount); MUST NEVER
include attachments or base64. Found open-sheet `state` MUST be `draft`. MUST NOT return
`validated` or `rejected`. Multi-open MUST raise existing multi-open `UserError`. Errors
MUST be raised, NEVER `{"error":...}`. Every branch MUST write zero rows. MUST NOT
`sudo()`. (Previously: Found returned `vouchers` and `invoices` only; no `receipts`
list.)

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
- THEN payload MUST list `vouchers`, `invoices`, and `receipts` (even empty), include
  invoice `document_kind`, omit `residual_reason`, never attachments or base64; `state`
  MUST be `draft` with zero writes

#### Scenario: Multi-open sheet and auth fail closed

- GIVEN more than one open sheet, or a non-internal / non-enabled seller
- WHEN `get_collection_allocation` runs
- THEN MUST raise (multi-open `UserError` or AccessError/UserError) with zero writes and
  MUST NOT return `{"error":...}`

### Requirement: Draft default and confirm-on-close invariant

Allocation `state` MUST be `draft` or `confirmed` only. Default MUST be `draft`. `draft`
MUST hold iff the sheet is `open`, `proposal`, or `cancelled`. `confirmed` MUST hold iff
the sheet is `closed`. MCP and ORM create MUST persist `draft` and revision 1 on first
persist. Confirm MUST NOT change allocation `state`. Close MUST confirm every allocation
then close the sheet. Cancel MUST return every allocation to `draft` (no-op if already
`draft`). Open from Cancelled MUST leave allocations `draft`. Raw allocation `state`
write MUST be refused except audited Close, Cancel, or Open transitions. (Previously:
`draft` iff sheet `open`; `confirmed` iff sheet `closed`; Reopen drafted after open.)

#### Scenario: Create defaults to draft

- GIVEN an open sheet
- WHEN an allocation is created via MCP or ORM
- THEN `state` MUST be `draft`
- AND first persist MUST store revision 1

#### Scenario: Close confirms then closes

- GIVEN a proposal sheet with draft allocations
- WHEN Close runs
- THEN every allocation MUST be `confirmed`
- AND the sheet MUST be `closed`

#### Scenario: Cancel drafts allocations

- GIVEN a proposal sheet with draft allocations, or a closed sheet with confirmed
  allocations
- WHEN Cancel runs
- THEN the sheet MUST be `cancelled`
- AND every allocation MUST be `draft`

#### Scenario: Open from cancelled leaves draft

- GIVEN a cancelled sheet with draft allocations and no other open sheet for that seller
  in that company
- WHEN Open runs
- THEN the sheet MUST be `open`
- AND every allocation MUST be `draft`

#### Scenario: Confirm does not confirm allocations

- GIVEN an open sheet with draft allocations
- WHEN Confirm runs
- THEN the sheet MUST be `proposal`
- AND every allocation MUST remain `draft`

#### Scenario: Invariant-breaking state write refused

- GIVEN an allocation whose `state` would not match its sheet (`draft` on closed, or
  `confirmed` on open, proposal, or cancelled)
- WHEN a non-audited `state` write is attempted
- THEN the write MUST be refused
- AND stored `state` MUST be unchanged

### Requirement: Draft unlink with revisions

The system MUST allow unlinking a `draft` allocation even when revision rows exist. That
unlink MUST unassign linked vouchers (MUST NOT destroy them), MUST cascade invoice
lines, receipts, and receipt values, and MUST delete revision snapshots only as a
consequence of deleting that parent. Direct revision write and unlink MUST remain
forbidden. Unlink of a `confirmed` allocation MUST be refused even with zero revisions.
(Previously: Cascade covered lines and revisions only; receipts/values did not exist.)

#### Scenario: Draft with revisions unlinks

- GIVEN a draft allocation with revision rows, receipts, values, and linked vouchers
- WHEN the allocation is deleted
- THEN the allocation, its lines, its receipts, its values, and its revisions MUST be
  gone
- AND vouchers MUST persist with `allocation_id` unset

#### Scenario: Confirmed unlink refused

- GIVEN a confirmed allocation (with or without revisions)
- WHEN deleted
- THEN the delete MUST be refused
- AND vouchers and revisions MUST remain

#### Scenario: Direct revision unlink still forbidden

- GIVEN a revision row on a draft allocation
- WHEN an operator writes or unlinks that revision directly
- THEN the operation MUST be refused
- AND the parent draft MUST remain

### Requirement: Allocation line document_kind

Each `collection.allocation.line` MUST have required Selection `document_kind`
`invoice`/`quotation` only, default `invoice`. Snapshotted connector rows MUST default
`invoice`. Operators MUST set `quotation` on a draft line. The form line list MUST show
`document_kind` immediately before `invoice_number` on the parent arch (MUST NOT rely on
inherit). That list MUST use `<list>` (MUST NOT `<tree>`). MCP
`create_collection_allocation` `receipts[]` items MUST include `document_kind`;
applications inherit that kind. Write response MAY omit `document_kind`. Get invoice
rows MUST include `document_kind`. Persist and amend MUST keep each expanded-zero line's
stored `document_kind` when that invoice is not in applications; payload kind MUST win
when the invoice is applied. (Previously: MCP create payload used `invoices[]` with
optional kind.)

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

#### Scenario: MCP create invoice receipt; get returns kind

- GIVEN a valid `create_collection_allocation` payload with an invoice receipt
- WHEN the write tool succeeds and get later runs
- THEN each applied line MUST have `document_kind` `invoice`; write response MAY omit
  kind; get invoice rows MUST include it

#### Scenario: MCP create may send quotation kind

- GIVEN a valid create payload whose `receipts[]` item has `document_kind` `quotation`
- WHEN the write tool succeeds
- THEN those applied lines MUST persist `quotation`

#### Scenario: Amend on-account keeps stored quotation kind

- GIVEN a draft line with `document_kind` `quotation`
- WHEN MCP amend recreates lines from a receipt whose applications omit that invoice
- THEN stored `document_kind` MUST remain `quotation` (MUST NOT wipe to `invoice`)

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
it. MCP create MUST NOT accept `residual_reason`.

#### Scenario: Residual and zeros

- GIVEN debt 150 applied 40, or applied > debt, or a zero-applied line
- WHEN totals compute or save
- THEN residual MUST be 110, or negative MUST save, and zero-applied MUST persist

#### Scenario: Reason dropped from persist

- GIVEN MCP create without `residual_reason` or a sheet print
- WHEN persist or report runs
- THEN reason MUST NOT be stored or read

### Requirement: Cancelled and Closed allocation write guards

When the sheet is `closed` or `cancelled`, writes to allocation `line_ids` (including
`amount_applied`), `voucher_ids`, `receipt_ids`, `partner_id`, and `sheet_id` MUST be
refused even if the allocation is `draft`. Direct line `write` or `unlink` MUST be
refused. When the sheet is `open` or `proposal`, draft allocations MUST remain writable
subject to other rules. MUST NOT `sudo()`. (Previously: Frozen membership omitted
`receipt_ids`.)

#### Scenario: Cancelled draft line write refused

- GIVEN a cancelled sheet with a draft allocation and debt lines
- WHEN `amount_applied` or other line fields are written via form or RPC
- THEN MUST refuse and stored values MUST be unchanged

#### Scenario: Closed allocation writes refused

- GIVEN a closed sheet with confirmed allocations
- WHEN `line_ids`, `voucher_ids`, `receipt_ids`, `partner_id`, or `sheet_id` are written
- THEN MUST refuse and stored values MUST be unchanged

#### Scenario: Proposal draft remains writable

- GIVEN a proposal sheet with a draft allocation
- WHEN `line_ids` or `voucher_ids` are written lawfully
- THEN the write MUST persist

#### Scenario: Cancelled line unlink refused

- GIVEN a debt line on a cancelled sheet
- WHEN the line is unlinked
- THEN MUST refuse and the line MUST remain

### Requirement: MCP open sheet is state open only

`create_collection_allocation` and `get_collection_allocation` MUST resolve sheets only
where `state` is `open`. A sheet in `proposal`, `closed`, or `cancelled` MUST NOT
satisfy lookup or auto-assign. A seller MAY obtain a new `open` sheet while another
sheet is `proposal`.

#### Scenario: Proposal does not occupy MCP open

- GIVEN a seller with one proposal sheet and zero open sheets in that company
- WHEN `get_collection_allocation` runs
- THEN the body MUST be `{allocation: null}` with zero writes

#### Scenario: New open while proposal exists

- GIVEN a seller with one proposal sheet and zero open sheets, `auto_create_sheet` ON
- WHEN `create_collection_allocation` runs with valid payload
- THEN a new `open` sheet MAY be created and allocation MUST persist `draft` on that
  open sheet
- AND the proposal sheet MUST remain `proposal`

#### Scenario: Closed or cancelled not used as open

- GIVEN only a closed or cancelled sheet for that seller in that company
- WHEN `get_collection_allocation` runs
- THEN MUST return `{allocation: null}` with zero writes

### Requirement: MCP receipts payload

`create_collection_allocation` MUST include `receipts[]` (`minItems` 1). Each receipt
MUST have unique `document_kind` (`invoice` or `quotation`), required `values[]`
(`minItems` 1; `{document_id, amount}` amount > 0), and `applications[]` that MAY be
empty (on account). A payment MAY appear on both kinds. Sum of value amounts per payment
across receipts MUST equal that payment's `seller_confirmed` amount. Applied total per
receipt MUST NOT exceed funded values. Unknown `document_id` or duplicate kind /
duplicate payment+kind / duplicate `external_document_id` MUST raise with no writes.
Value `amount`, application `balance_seen`, and `amount_applied` MUST accept decimal
strings (and MAY accept numbers). Application `number` MAY be JSON `null` (omit).
(Previously: Amounts were not required to accept decimal strings; `number` null was not
named.)

#### Scenario: Split one voucher two kinds

- GIVEN a valid create payload with one payment amount 100 and receipt values 40 invoice
  plus 60 quotation
- WHEN create succeeds
- THEN both values MUST persist on the matching receipts

#### Scenario: Empty applications is on account

- GIVEN a valid create with one invoice receipt, full values, and `applications: []`
- WHEN create succeeds
- THEN the invoice receipt MUST persist with those values
- AND allocation lines MUST expand outstanding ERP invoices at applied 0

#### Scenario: Over-split refused

- GIVEN a payment amount 50 and receipt values summing to 51
- WHEN create runs
- THEN MUST raise with no allocation persist

#### Scenario: Decimal-string receipt amounts persist

- GIVEN receipt values and applications whose `amount`, `balance_seen`, and
  `amount_applied` are decimal strings matching fresh ERP `balance_seen`
- WHEN create succeeds
- THEN those receipts and applications MUST persist
- AND `balance_seen` revalidation MUST still use `currency.compare_amounts`

### Requirement: Persist receipt grouping on create and amend

On successful create or amend, the system MUST persist at most one receipt per
`document_kind` from the payload. Persist MUST write values from explicit receipt values
(MUST NOT FIFO-compat from invoices). Amend MUST rebuild receipts and values to match
the new payload while the allocation is `draft`. Persist and amend MUST keep each
applied line's `document_kind` from the parent receipt.

#### Scenario: Amend rebuilds receipts

- GIVEN a draft allocation with one invoice receipt
- WHEN amend supplies receipts that add a quotation value
- THEN a quotation receipt MUST persist and the invoice receipt MUST remain unique for
  that kind

#### Scenario: Amend rebuilds receipt values

- GIVEN a draft allocation with one invoice receipt
- WHEN amend sends a voucher superset with explicit values covering all payments
- THEN receipt values MUST match the new payload

### Requirement: Strict nested-key parse of dump payloads

Runtime parse of `create_collection_allocation` MUST reject unknown keys at every nested
object (`extra=forbid`): request, each payment, `seller_confirmed`, `raw_ocr`,
`attachment`, each receipt, each value, and each application. It MUST reject keys that
do not belong to that payment’s `document_type` (type-owned fields only; see
collection-vouchers). Explicit JSON `null` on optional dump fields MUST be accepted as
omit. Omitted optional keys MUST remain valid. A forbidden key MUST raise `UserError`
with no writes.

#### Scenario: Unknown key on payment or request rejected

- GIVEN a valid dump plus an extra key on the request or a payment object
- WHEN `create_collection_allocation` runs
- THEN MUST raise `UserError` with no writes

#### Scenario: Unknown key on nested receipt objects rejected

- GIVEN a valid dump plus an extra key on a receipt, value, application,
  `seller_confirmed`, `raw_ocr`, or `attachment`
- WHEN `create_collection_allocation` runs
- THEN MUST raise `UserError` with no writes

#### Scenario: Type-foreign nest fields rejected

- GIVEN `seller_confirmed.document_type` `bank_transfer` with `check_number` set (or any
  type-foreign field for that discriminator)
- WHEN `create_collection_allocation` runs
- THEN MUST raise `UserError` with no writes

#### Scenario: Explicit nulls accepted as omit

- GIVEN a dump whose unused typed nest fields, `attachment`, `raw_ocr`, and application
  `number` are JSON `null`
- WHEN `create_collection_allocation` runs with otherwise valid data
- THEN parse MUST treat those nulls as omit and MAY persist

### Requirement: MCP customer_debt allocatable balances

MCP `customer_debt` MUST keep each invoice's gross connector `balance` and existing
summary fields (`total_balance`, `overdue_balance`, `open_balance`, `invoice_count`)
unchanged. It MUST add `invoices[].allocatable_balance` and summary
`total_allocatable_balance`, `open_allocatable_balance`, and
`overdue_allocatable_balance`.

Allocatable MUST be the gross connector `balance` minus ALL same-company
`collection.allocation.line.amount_applied` on allocations whose `state` is `draft` OR
`confirmed`, INCLUDING allocations on proposal, closed, or cancelled sheets that
`get_collection_allocation` does not expose. The result MUST be clamped at zero (MUST
NEVER be negative). No reservations MUST mean allocatable equals gross. Empty `invoices`
MUST still return the three allocatable summary keys as `0`. MUST NOT `sudo()`.

Write-path revalidation MUST reuse the same reservation lookup, MUST still exclude the
destination allocation, and MUST still raise `UserError`
`Applied amount exceeds available invoice balance.` when applied exceeds available.
`balance_seen` revalidation MUST still compare against GROSS connector `balance` via
`currency.compare_amounts` (MUST NOT switch that check to allocatable).

#### Scenario: Gross unchanged when no reservations

- GIVEN an enabled bound seller and outstanding overdue 100 plus open 50 with no draft
  or confirmed applications
- WHEN `customer_debt` runs
- THEN each invoice `balance` MUST stay 100 and 50
- AND each `allocatable_balance` MUST equal that gross
- AND summary `total_balance` / `overdue_balance` / `open_balance` MUST stay 150 / 100 /
  50
- AND `total_allocatable_balance` MUST be 150, `overdue_allocatable_balance` 100, and
  `open_allocatable_balance` 50

#### Scenario: Hidden draft on a proposal sheet reduces allocatable

- GIVEN a draft allocation on a **proposal** sheet applying 40 to the open invoice
  (`inv-bound-open`, gross 50) that `get_collection_allocation` does not expose
- WHEN `customer_debt` runs for identification `20-11111111-1`
- THEN the open invoice `balance` MUST stay 50 and `allocatable_balance` MUST be 10
- AND the overdue invoice MUST stay 100 / 100
- AND summary gross totals MUST stay 150 / 100 / 50
- AND `open_allocatable_balance` MUST be 10 and `total_allocatable_balance` MUST be 110

#### Scenario: Confirmed consumption on a closed sheet reduces allocatable

- GIVEN a confirmed allocation on a **closed** sheet applying 40 to the open invoice
- WHEN `customer_debt` runs
- THEN gross `balance` MUST stay 50 and `allocatable_balance` MUST be 10
- AND summary gross totals MUST be unchanged

#### Scenario: Over-reservation reports zero never negative

- GIVEN draft or confirmed applications whose sum exceeds the open invoice gross 50
- WHEN `customer_debt` runs
- THEN that invoice `allocatable_balance` MUST be 0
- AND MUST NOT be negative

#### Scenario: Write-path available still excludes destination

- GIVEN a hidden proposal-sheet draft reservation of the full open-invoice balance
- WHEN `create_collection_allocation` on a new open sheet applies 1 to that invoice
- THEN MUST raise `UserError` `Applied amount exceeds available invoice balance.` with
  no writes
- AND an amendment of the DESTINATION allocation MUST still exclude dest from reserved
  amounts
- AND `balance_seen` MUST still be revalidated against GROSS connector `balance` via
  `currency.compare_amounts`
