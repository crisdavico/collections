# Delta for Collection Allocations

## ADDED Requirements

### Requirement: MCP splits payload

`create_collection_allocation` MAY include splits: a list of values each linking one
submitted payment (same identity as `payments[]`) to a receipt `document_kind`
(`invoice` or `quotation`) and an amount > 0. Omitted splits MUST follow compat create
grouping. A payment MAY appear on both kinds. Sum of split amounts per payment MUST NOT
exceed that payment's amount.

#### Scenario: Split one voucher two kinds

- GIVEN a valid create payload with one payment amount 100 and splits 40 invoice plus 60
  quotation
- WHEN create succeeds
- THEN both values MUST persist on the matching receipts

#### Scenario: Omitted splits uses compat

- GIVEN a valid create with non-empty `invoices[]` and no splits key
- WHEN create succeeds
- THEN exactly one invoice receipt MUST exist (compat)

#### Scenario: Over-split refused

- GIVEN a payment amount 50 and splits summing to 51
- WHEN create runs
- THEN MUST raise with no allocation persist

### Requirement: Persist receipt grouping on create and amend

On successful create or amend, the system MUST group receipts on the allocation: at most
one receipt per `document_kind` present in splits or implied by compat. Persist MUST
write values from splits, or the compat default when splits are omitted. Amend MUST
rebuild receipts and values to match the new payload while the allocation is `draft`.
Persist and amend MUST keep each line's `document_kind` (MUST NOT wipe quotations).

#### Scenario: Amend rebuilds receipts

- GIVEN a draft allocation with one invoice receipt from compat
- WHEN amend supplies splits that add a quotation value
- THEN a quotation receipt MUST persist and the invoice receipt MUST remain unique for
  that kind

#### Scenario: Amend without splits keeps compat

- GIVEN a draft allocation created with non-empty invoices and no splits
- WHEN amend sends a voucher superset still without splits
- THEN exactly one invoice receipt MUST remain
- AND unsplit remainder MUST stay on no receipt

## MODIFIED Requirements

### Requirement: Idempotency and amend

MUST replay identical `request_id` (zero writes) with
`{sheet_id, vouchers[], allocation}` in submit order. Matching `content_hash` (new
`request_id`, no extra revision) MUST NOT include `residual_reason`. Content hash MUST
include splits (payment identity, receipt `document_kind`, amount) and invoice
`document_kind`. Payloads that omit splits MUST hash as they do today so identical
pre-receipt content MUST still replay with zero writes. Stored hashes from before this
change MUST still match those old payloads. Amend MUST be voucher SUPERSET
(`revision`+1) only while `draft`. MUST reject subset/partial overlap and
`state != draft`. `UniqueViolation` MUST invalidate then replay or generic-conflict with
no ids. (Previously: Hash omitted splits and invoice `document_kind`; reason-only retry
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
- WHEN retry uses the same vouchers/invoices and a different `residual_reason`
- THEN MUST treat content as unchanged (MUST NOT amend for reason alone)

#### Scenario: Splits and kind enter content_hash

- GIVEN a draft allocation hashed from a payload without splits
- WHEN retry uses the same vouchers/invoices but different splits or invoice
  `document_kind`
- THEN MUST NOT treat content as unchanged

#### Scenario: Payload without splits replays as today

- GIVEN a prior create whose payload omitted splits
- WHEN identical content is retried with a new `request_id`
- THEN MUST replay with zero writes and no extra revision

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
`create_collection_allocation` `invoices[]` items MAY include `document_kind`; omitted
kind on first persist MUST persist `invoice`. Persist and amend MUST keep each line's
`document_kind` (MUST NOT wipe operator-set or payload quotations). On amend, omitted
kind for an existing external invoice MUST keep the stored kind; payload `document_kind`
MUST win when present. Write response MAY omit `document_kind`. Get invoice rows MUST
include `document_kind`. (Previously: MCP create payload and write response MUST NOT
gain `document_kind`; persist defaulted omitted kind to invoice and amend wiped
quotations.)

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
- THEN each created line MUST have `document_kind` `invoice`; write response MAY omit
  kind; get invoice rows MUST include it

#### Scenario: MCP create may send kind

- GIVEN a valid create payload whose `invoices[]` items include `document_kind`
  `quotation`
- WHEN the write tool succeeds
- THEN those lines MUST persist `quotation`

#### Scenario: Amend keeps quotation kind

- GIVEN a draft line with `document_kind` `quotation`
- WHEN MCP amend recreates lines from a payload that omits kind for that invoice
- THEN stored `document_kind` MUST remain `quotation` (MUST NOT wipe to `invoice`)

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
