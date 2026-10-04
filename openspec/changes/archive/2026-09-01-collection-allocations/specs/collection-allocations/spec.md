# collection-allocations Specification

## Purpose

Seller-validated allocations of sheet vouchers vs external invoices; Odoo revalidates
ERP debt; back-office validates or rejects.

## Requirements

### Requirement: MCP create_collection_allocation

MUST expose MCP write `create_collection_allocation` for Enabled Seller internal
callers; persist `confirmed` revision-1
`{allocation:{id,name,state,revision,total_vouchers,total_applied,residual}}`;
`UNIQUE(sheet_id, partner_id)`; MUST NOT `sudo()`.

#### Scenario: First create

- GIVEN valid enabled-seller payload
- WHEN create with a new `request_id`
- THEN `confirmed`, `revision` 1, matching totals
- AND a second header for same (sheet, partner) MUST be unique-rejected

#### Scenario: Authorization denied

- GIVEN a non-internal or non-enabled seller
- WHEN the tool runs
- THEN the call MUST fail with no writes

### Requirement: Idempotency and amend

MUST replay identical `request_id` (zero writes) and matching `content_hash` (new
`request_id`, no extra revision). Amend MUST be voucher SUPERSET (`revision`+1). MUST
reject subset/partial overlap and `state != confirmed`. `UniqueViolation` MUST
invalidate then replay or generic-conflict with no ids.

#### Scenario: Replay by request_id, content_hash, or UniqueViolation

- GIVEN a prior create or concurrent `UNIQUE(request_id)` insert
- WHEN identical `request_id`, same content with a new `request_id`, or race
- THEN zero writes, no extra revision, or invalidate-replay/generic-conflict with no ids

#### Scenario: Amend voucher superset or overlap

- GIVEN confirmed {V1,V2} or destination `validated`/`rejected`
- WHEN payload is {V1,V2,V3}, {V1}, {V2,V3}, or amend after decision
- THEN SUPERSET MUST `revision`+1 and link V3; else MUST error with no writes

### Requirement: Input and sheet gates

Vouchers MUST be caller-company, amount > 0, not `rejected`, one partner, one caller
seller, one sheet. Customer MUST resolve via existing
`collection.connector.customer.binding` only; MUST NOT create partner/binding; MUST
match voucher partner. Sheet MUST be `open` and same company.

#### Scenario: Ineligible input rejected

- GIVEN amount null/≤0, `rejected`, other company, other sheet, mixed
  partner/seller/sheet, unbound id, partner mismatch, closed sheet, or other company
  sheet
- WHEN allocated
- THEN MUST error and MUST NOT create a partner or binding

### Requirement: Revalidation and residual

Each `external_invoice_id` MUST remain in fresh ERP debt. Available = fresh balance −
other `confirmed`/`validated` applications of that id. `amount_applied` ≤ available
(currency compare). `total_debt` is fresh snapshot, MUST NOT require caller equality.
Residual ≥ 0 (currency compare); `residual_reason` iff residual > 0; empty invoices
allowed. Residual constraint only while `confirmed`.

#### Scenario: Fresh debt, residual, and confirmed-only constraint

- GIVEN invoice I in fresh debt, other confirmed/validated apply A, caller `total_debt`
  ≠ fresh snapshot
- WHEN apply B, empty invoices, residual > 0 or < 0, or `validated` amount edit drives
  residual negative
- THEN available = fresh − A; B > available errors; `total_debt` is fresh; empty
  invoices persist as all on account; residual_reason iff residual > 0; residual < 0
  errors only while `confirmed`

### Requirement: Freeze, revisions, ACL, back-office

When `state != confirmed`, freeze `line_ids`/`voucher_ids`/`partner_id`/ `sheet_id`. O2M
Command.DELETE MUST NOT destroy vouchers. Revisions immutable, `UNIQUE(request_id)`,
company `ir.rule`, no sudo. MUST NOT delete allocation with revisions. Back-office
validate/reject; then amend refused.

#### Scenario: Freeze, revisions, and back-office

- GIVEN non-confirmed state, linked vouchers, a stored revision, or confirmed
- WHEN frozen fields write, O2M Command.DELETE, revision write/unlink/dup `request_id`,
  allocation unlink, or validate/reject then amend
- THEN frozen writes MUST be refused; vouchers MUST persist; revision ops MUST fail
  under company `ir.rule` with no sudo; unlink with revisions MUST fail; post-decision
  amend MUST error
