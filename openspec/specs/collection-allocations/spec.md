# collection-allocations Specification

## Purpose

Seller-validated allocations of sheet vouchers vs external invoices; Odoo
revalidates ERP debt; back-office validates or rejects.

## Requirements

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
`revision` a JSON int (MUST NOT be bool, float, or str). Persist `draft`
revision-1; `UNIQUE(sheet_id, partner_id)`. Unbound identification MUST
lazy-resolve via `resolve_customer_partner` on this write. When
`company.auto_create_sheet` is False, MUST raise a named `UserError` and
write zero rows. Exact same-company `document_id` set MUST reuse rows and
continue to allocation (MUST NOT voucher-style early-return). Partial overlap
or other-company hit MUST raise generic conflict with no writes. Revalidation
failure MUST roll back vouchers and allocation. Errors MUST be raised, NEVER
`{"error":...}` bodies. MUST NOT `sudo()`.
(Previously: Persist `confirmed` revision-1.)

#### Scenario: First create

- GIVEN valid enabled-seller payload with inline `payments` and required
  `invoices` (MAY be `[]`)
- WHEN create with a new `request_id`
- THEN `draft`, `revision` 1 (int), matching totals, `sheet_id`, and
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

### Requirement: Idempotency and amend

MUST replay identical `request_id` (zero writes) with the full
`{sheet_id, vouchers[], allocation}` payload, `vouchers[]` in submitted
order. Matching `content_hash` (new `request_id`, no extra revision) MUST
include `residual_reason` so a reason-only retry is not a silent no-op.
Amend MUST be voucher SUPERSET (`revision`+1) and MUST be allowed only while
`draft`. MUST reject subset/partial overlap and `state != draft`
(`confirmed` MUST refuse amend). `UniqueViolation` MUST invalidate then
replay or generic-conflict with no ids.
(Previously: Amend required `confirmed`; `validated`/`rejected` refused as
already reviewed.)

#### Scenario: Replay by request_id, content_hash, or UniqueViolation

- GIVEN a prior create or concurrent `UNIQUE(request_id)` insert
- WHEN identical `request_id`, same content with a new `request_id`, or race
- THEN zero writes, no extra revision, or invalidate-replay/generic-conflict
  with no ids
- AND `request_id` replay MUST return `sheet_id` plus ordered `vouchers[]`

#### Scenario: Amend voucher superset or overlap

- GIVEN draft {V1,V2} or destination `confirmed`
- WHEN payload is {V1,V2,V3}, {V1}, {V2,V3}, or amend after confirm
- THEN SUPERSET on draft MUST `revision`+1 and link V3; else MUST error with
  no writes

#### Scenario: Residual reason participates in content_hash

- GIVEN a draft allocation whose hash includes residual_reason R
- WHEN amend retries with the same vouchers/invoices and a different reason
- THEN MUST NOT silent no-op; MUST treat content as changed

### Requirement: Input and sheet gates

Vouchers MUST be caller-company, amount > 0, not `rejected`, one partner, one
caller seller, one sheet. Those single-customer and single-sheet gates MUST
remain and MUST be reachable via `document_id` reuse. Customer MUST resolve
via `resolve_customer_partner` on this write (MAY create partner/binding);
MUST match voucher partner after resolve. Sheet MUST be `open` and same
company. Successful persist MUST leave the allocation `draft` on that open
sheet. When `auto_create_sheet` is False, MUST raise a named `UserError`
(company requires a sheet chosen in Odoo) with zero writes.
(Previously: Persist implied confirmed on the open sheet.)

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

### Requirement: Revalidation and residual

Each `external_invoice_id` MUST remain in fresh ERP debt. Available = fresh
balance − other `draft`/`confirmed` applications of that id.
`amount_applied` ≤ available (currency compare). `total_debt` is fresh
snapshot, MUST NOT require caller equality. Residual ≥ 0 (currency compare);
`residual_reason` iff residual > 0; empty invoices allowed. Residual
constraint MUST apply while `draft` and while `confirmed`.
(Previously: Subtracted other `confirmed`/`validated`; residual only while
`confirmed`.)

#### Scenario: Fresh debt, residual, and both-state constraint

- GIVEN invoice I in fresh debt, other draft or confirmed apply A, caller
  `total_debt` ≠ fresh snapshot
- WHEN apply B, empty invoices, residual > 0 or < 0
- THEN available = fresh − A; B > available errors; `total_debt` is fresh;
  empty invoices persist as all on account; residual_reason iff residual > 0;
  residual < 0 MUST error while `draft` and while `confirmed`

#### Scenario: Residual holds on draft and confirmed

- GIVEN residual ≥ 0 with `residual_reason` when residual > 0
- WHEN the allocation is `draft` or `confirmed`
- THEN persist MUST succeed

### Requirement: Freeze, revisions, ACL, back-office

When `state` is `confirmed`, freeze `line_ids`/`voucher_ids`/`partner_id`/
`sheet_id`. When `state` is `draft`, those fields MUST remain writable
subject to other rules. O2M Command.DELETE MUST NOT destroy vouchers.
Revisions immutable, `UNIQUE(request_id)`, company `ir.rule`, no sudo.
Direct revision write and unlink MUST remain forbidden. MUST NOT delete a
`confirmed` allocation. Draft unlink with revisions is specified under Draft
unlink with revisions. MUST NOT expose Validate or Reject; `action_validate`
and `action_reject` MUST NOT remain; `validated` and `rejected` MUST NOT
remain as states.
(Previously: Freeze when `state != confirmed`; unlink with revisions
refused; back-office validate/reject then amend refused.)

#### Scenario: Freeze when confirmed

- GIVEN a confirmed allocation with linked vouchers
- WHEN frozen fields are written or O2M Command.DELETE runs
- THEN frozen writes MUST be refused
- AND vouchers MUST persist (DELETE MUST unassign, not destroy)

#### Scenario: Draft membership remains writable

- GIVEN a draft allocation
- WHEN `line_ids`, `voucher_ids`, `partner_id`, or `sheet_id` are written
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

When a voucher would leave a `draft` allocation, the system MUST project
residual as current residual minus that voucher's amount (currency compare).
If projected residual is `< 0`, the system MUST refuse the move with no
`partner_id` or `allocation_id` change. Fully applied draft sources MUST be
refused. The system MUST NOT unallocate the voucher to avoid a negative
residual. Detach from a `confirmed` allocation MUST be refused.
(Previously: Projection applied only to `confirmed` allocations.)

#### Scenario: Fully applied source detach refused

- GIVEN a draft allocation with residual 0 and a linked voucher
- WHEN that voucher is moved off the allocation (including via `partner_id`
  write)
- THEN the move MUST be refused
- AND allocation `voucher_ids` MUST be unchanged

#### Scenario: Negative projected residual refused

- GIVEN a draft allocation whose residual is less than the voucher amount
- WHEN that voucher is detached
- THEN the move MUST be refused
- AND residual MUST be unchanged

#### Scenario: Draft detach when residual holds

- GIVEN a draft allocation whose residual is greater than the voucher amount
- WHEN that voucher is detached
- THEN the move MUST succeed
- AND projected residual MUST remain ≥ 0

#### Scenario: Confirmed source detach refused

- GIVEN a confirmed allocation with a linked voucher
- WHEN that voucher is detached
- THEN the move MUST be refused
- AND `voucher_ids` MUST be unchanged

### Requirement: Partner match after voucher write

Every allocated voucher's `partner_id` MUST equal the allocation `partner_id`
after voucher `partner_id` or `allocation_id` writes, not only after allocation
`partner_id` or `voucher_ids` writes. A mismatch MUST be refused with no
persist.
(Previously: Same-write attach used a confirmed same-sheet target.)

#### Scenario: Voucher partner write mismatch refused

- GIVEN a voucher linked to an allocation for partner P
- WHEN `partner_id` is written to Q without a matching `allocation_id` in the
  same vals
- THEN the write MUST be refused
- AND the voucher MUST remain on P and that allocation

#### Scenario: Same-write matching partner and allocation

- GIVEN a voucher on allocation A (partner P) and draft same-sheet
  allocation B (partner Q) with attachable residual
- WHEN `partner_id` is written to Q with `allocation_id` B in the same vals
- THEN partner match MUST hold
- AND the voucher MUST belong to B

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
Found open-sheet allocation `state` MUST be `draft`. MUST NOT return
`validated` or `rejected`. More than one open sheet MUST raise the existing
multi-open `UserError`. Errors MUST be raised, NEVER `{"error":...}` bodies.
Every branch MUST write zero rows. MUST NOT `sudo()`.
(Previously: `validated` allocations were returned with that `state`.)

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

#### Scenario: Found payload and draft state

- GIVEN one open sheet and an allocation
- WHEN `get_collection_allocation` runs
- THEN payload MUST include residual_reason and list `vouchers` and `invoices`
  (even empty), never attachments or base64
- AND `state` MUST be `draft` with zero writes

#### Scenario: Multi-open sheet and auth fail closed

- GIVEN more than one open sheet, or a non-internal / non-enabled seller
- WHEN `get_collection_allocation` runs
- THEN MUST raise (multi-open `UserError` or AccessError/UserError)
- AND MUST NOT return `{"error":...}` and MUST write zero rows

### Requirement: Draft default and confirm-on-close invariant

Allocation `state` MUST be `draft` or `confirmed` only. Default MUST be
`draft`. `draft` MUST hold iff the sheet is `open`. `confirmed` MUST hold
iff the sheet is `closed`. MCP and ORM create MUST persist `draft` and
revision 1 on first persist. Close MUST confirm every allocation then close
the sheet. Reopen MUST open the sheet then return every allocation to
`draft`. Raw allocation `state` write MUST be refused except Close/Reopen
audited transitions.

#### Scenario: Create defaults to draft

- GIVEN an open sheet
- WHEN an allocation is created via MCP or ORM
- THEN `state` MUST be `draft`
- AND first persist MUST store revision 1

#### Scenario: Close confirms then closes

- GIVEN an open sheet with draft allocations
- WHEN Close runs
- THEN every allocation MUST be `confirmed`
- AND the sheet MUST be `closed`

#### Scenario: Reopen drafts after open

- GIVEN a closed sheet with confirmed allocations and no other open sheet
  for that seller in that company
- WHEN Reopen runs
- THEN the sheet MUST be `open`
- AND every allocation MUST be `draft`

#### Scenario: Invariant-breaking state write refused

- GIVEN an allocation whose `state` would not match its sheet (`draft` on
  closed, or `confirmed` on open)
- WHEN a non-audited `state` write is attempted
- THEN the write MUST be refused
- AND stored `state` MUST be unchanged

### Requirement: Draft unlink with revisions

The system MUST allow unlinking a `draft` allocation even when revision rows
exist. That unlink MUST unassign linked vouchers (MUST NOT destroy them),
MUST cascade invoice lines, and MUST delete revision snapshots only as a
consequence of deleting that parent. Direct revision write and unlink MUST
remain forbidden. Unlink of a `confirmed` allocation MUST be refused even
with zero revisions.

#### Scenario: Draft with revisions unlinks

- GIVEN a draft allocation with revision rows and linked vouchers
- WHEN the allocation is deleted
- THEN the allocation, its lines, and its revisions MUST be gone
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
