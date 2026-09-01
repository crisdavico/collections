# Delta for collection-vouchers

## MODIFIED Requirements

### Requirement: Deferred integrations not required

Completeness MUST NOT require HTTP API, WhatsApp metadata, or agent calls. Each
voucher MUST require a `res.partner` Customer (`partner_id`). Optional
per-voucher image/PDF attachments are an allowed capability and MUST NOT be
required for completeness of unrelated voucher features.
(Previously: Completeness MUST NOT require partner/CRM linkage.)

#### Scenario: Completeness without deferred features

- GIVEN backend-only voucher management
- WHEN operators create, edit, approve, or reject vouchers
- THEN success MUST NOT depend on deferred integrations
- AND success MUST NOT require that vouchers have attachments

### Requirement: Voucher fields and defaults

Each `collection.voucher` MUST represent one payment. The system MUST require
`partner_id` (label Customer; tracking; index; `ondelete` restrict). The system
MUST NOT store or accept `customer_identification` or `received_date`.
Registration time MUST be automatic ORM `create_date` (readonly; MUST NOT be
overridable by MCP, create vals, or editable views). On create, `state` MUST
default to `pending`. Currency MUST be the company default (no multi-currency
UX). Upgrade MUST NOT backfill `partner_id`.
(Previously: Required Char `customer_identification`.)

#### Scenario: Defaults on create

- GIVEN a new voucher saved without overriding defaults
- WHEN create completes
- THEN `create_date` MUST be automatic, `state` `pending`, currency company
  default
- AND `received_date` MUST NOT exist

#### Scenario: Required fields

- GIVEN a voucher missing `partner_id`
- WHEN saved
- THEN the system MUST reject the save

#### Scenario: create_date not overridable

- GIVEN a create that supplies custom creation time or `received_date`
- WHEN create runs via UI or MCP
- THEN creation time MUST NOT be caller-overridable and `received_date` MUST NOT
  persist

#### Scenario: Char customer_identification gone

- GIVEN the voucher model after this change
- WHEN fields are inspected
- THEN `customer_identification` MUST NOT exist
- AND `partner_id` MUST be required

### Requirement: Payment Vouchers UI

The system MUST expose Collections → Payment Vouchers as the only create/edit
surface (kanban, list, and form; create and edit enabled). Kanban MUST group by
`state`. List/search MUST show reference, Customer (`partner_id`), readonly
`create_date`, status, and payment fields. Form MUST show statusbar,
Approve/Reject when `pending`, readonly `create_date`, payment fields for the
voucher’s `document_type`, chatter and activity controls, and MUST NOT show
`received_date`. List, search, kanban, form, and sheet member list MUST show
`partner_id` and MUST NOT apply a domain that restricts Customer to bound
partners. The system MUST NOT expose Collections → Payment Lines or typed
embedded payment-line tables.
(Previously: List/search showed customer identification; no partner field.)

#### Scenario: Menu and form behaviors

- GIVEN the module installed and a voucher in `pending`
- WHEN an internal user opens Collections → Payment Vouchers then the form
- THEN list/search MUST show reference, Customer, `create_date`, status
- AND form MUST show statusbar, Approve/Reject, readonly `create_date`,
  chatter/activity UI without `received_date`
- AND form MUST show that voucher’s payment fields and MUST NOT show
  payment-line tables

#### Scenario: Kanban grouped by state

- GIVEN Payment Vouchers kanban
- WHEN an internal user opens it
- THEN vouchers MUST be grouped by `state`
- AND create and edit MUST be enabled

#### Scenario: Payment Lines menu absent

- GIVEN the module installed
- WHEN menus load
- THEN Collections → Payment Lines MUST NOT appear

#### Scenario: UI create_date visibility

- GIVEN an existing voucher
- WHEN list, search, kanban, or form is opened
- THEN readonly `create_date` MUST be visible and not editable

#### Scenario: Customer field has no domain

- GIVEN Payment Vouchers list, search, kanban, form, or sheet member list
- WHEN an internal user opens the Customer field
- THEN the field MUST be `partner_id`
- AND MUST NOT restrict choices to bound connector customers

### Requirement: MCP tool create_collection_vouchers

The system MUST expose `create_collection_vouchers` via `@mcp_tool` on
`muk_mcp.mixin` (`category=write`, `registry=mcp`), method-discovered — MUST NOT
use a DB `muk_mcp.tool` record. Calls MUST use the authenticated user (MUST NOT
`sudo()`); voucher ACL and allowed-company rules MUST apply. Input MUST require
non-empty `payments` and top-level `seller_id`. Input MUST NOT accept top-level
`customer_identification` (not a method argument and not a schema
required/property) and MUST NOT accept `received_date`. The MCP input schema
MUST remain unchanged: each payment MUST still send a `customer_identification`
string. `seller_id` MUST identify an existing internal user; missing,
portal/share, or unknown ids MUST be rejected with no writes. All-new create
MUST also require that seller enabled for the voucher company and each payment
`document_type` allowed. Each MCP payment MUST include a non-empty trimmed
`customer_identification`, non-empty `document_id`, and existing payment fields
(`document_type` required). Missing or blank (including whitespace-only)
per-payment `customer_identification` MUST raise `UserError` with no writes. The
old shape (top-level `customer_identification` with payments that omit
per-payment customer) MUST be rejected by schema and at runtime with no writes.
Mixed customers in one `payments` array MUST create one voucher per payment,
each stamped with that payment's resolved `partner_id`. The server MUST resolve
identification to `partner_id` on the create path only, inside the create
savepoint, AFTER exact-replay classification. Replay MUST NOT resolve, MUST NOT
call the adapter, and MUST ignore a changed per-payment
`customer_identification`; stored `partner_id` MUST remain the first-call value.
One invalid customer in a batch MUST fail the whole batch with no voucher,
partner, or binding leftovers. Create MUST persist one voucher per payment
atomically (`state=pending`, company currency) and MUST stamp `seller_id` only
on all-new create. All-new create MUST follow the same ORM sheet rules as UI
voucher create (`seller_id` set, `sheet_id` omitted), including
`auto_create_sheet`. Exact same-company replay MUST skip enabled-seller and
allowed-type gates, MUST NOT attach, move, or clear sheets (including leftover
unassigned), and MUST ignore per-payment `customer_identification` (customer
stays outside provenance equality), nested attachments, provenance nests, and
`seller_id`. The tool MUST NOT accept `sheet_id` in the payload and MUST NOT
return `sheet_id`. Response MUST include each voucher `id`/`name`/`state` and
`document_id` in payment order (`state` is voucher state) and MUST NOT include
`partner_id`. Idempotency by `document_id` is per the current company: all-new
in that company → create N vouchers; every submitted `document_id` already
exists on that company → return ALL those vouchers unchanged; in-call duplicate
or partial overlap in that company → reject with no writes. Submitted
`document_id`s that already exist on different vouchers of that company MUST
succeed as exact replay. A hit only in another company MUST reject, not replay,
with no ids or names disclosed.
(Previously: Each payment's Char `customer_identification` was stored on the
voucher; resolution did not exist.)

#### Scenario: All-new create

- GIVEN an internal user, unused payment `document_id`s, a valid enabled internal
  `seller_id`, allowed types, and listable per-payment customers
- WHEN `create_collection_vouchers` runs with per-payment customers, payments,
  and `seller_id`
- THEN one voucher per payment MUST be created atomically with that `seller_id`
- AND each voucher MUST be stamped with that payment's resolved `partner_id`
- AND response MUST include each voucher `id`/`name`/`state` and `document_id`
  in payment order

#### Scenario: Mixed-customer batch create

- GIVEN two payments with different non-empty `customer_identification` values
  and unused `document_id`s
- WHEN `create_collection_vouchers` runs in one atomic call
- THEN one voucher per payment MUST be created
- AND each voucher MUST keep its own payment's resolved `partner_id`
- AND response MUST be in payment order

#### Scenario: Mixed-customer batch atomic failure

- GIVEN two payments for different customers where one payment is invalid
- WHEN `create_collection_vouchers` runs
- THEN the call MUST raise `UserError` with no vouchers written
- AND MUST NOT leave partners or bindings from the failed batch

#### Scenario: Missing or blank per-payment customer rejected

- GIVEN a payment that omits `customer_identification` or supplies `""` or
  whitespace-only
- WHEN `create_collection_vouchers` runs
- THEN the call MUST raise `UserError` with no writes

#### Scenario: Old top-level customer shape rejected

- GIVEN a payload with top-level `customer_identification` and payments that
  omit per-payment customer
- WHEN `create_collection_vouchers` runs
- THEN schema and runtime MUST reject the call with no writes

#### Scenario: All-new resolves after classify inside savepoint

- GIVEN unused `document_id`s and a listable identification
- WHEN `create_collection_vouchers` runs
- THEN resolution MUST run after exact-replay classification and inside the
  create savepoint
- AND the input schema MUST still require per-payment `customer_identification`

#### Scenario: Exact-retry returns all vouchers

- GIVEN every submitted `document_id` already exists in the same company,
  including legacy null `seller_id` or a now-disabled seller
- WHEN the same payload is retried with any `seller_id`, a now-disallowed type,
  or different per-payment `customer_identification` values
- THEN all matching vouchers MUST return unchanged with no new rows
- AND stored `partner_id` MUST stay the first-call values
- AND nested attachments, `seller_id`, and type gates MUST be skipped
- AND matching vouchers MUST NOT be mutated

#### Scenario: Exact replay performs no customer resolution

- GIVEN every submitted `document_id` already exists in the same company
- WHEN retried with a different per-payment `customer_identification`
- THEN the call MUST NOT resolve customers or call the adapter
- AND stored `partner_id` MUST stay the first-call value

#### Scenario: Duplicate document_id in call

- GIVEN two payments in one call share a `document_id`
- WHEN `create_collection_vouchers` runs
- THEN the call MUST be rejected with no writes

#### Scenario: Partial-conflict

- GIVEN some submitted `document_id`s exist in the current company and others do
  not
- WHEN `create_collection_vouchers` runs
- THEN the call MUST be rejected with no writes

#### Scenario: Existing document_ids on different vouchers succeed

- GIVEN submitted `document_id`s already exist on more than one voucher of the
  current company
- WHEN `create_collection_vouchers` runs
- THEN the call MUST succeed as exact replay
- AND response MUST include all those vouchers

#### Scenario: ACL denial for non-permitted user

- GIVEN a caller without voucher create rights
- WHEN `create_collection_vouchers` runs
- THEN access MUST be denied with no writes

#### Scenario: Missing or invalid seller_id rejected

- GIVEN a payload missing `seller_id`, or with a portal/share or unknown user
- WHEN `create_collection_vouchers` runs
- THEN the call MUST be rejected with no writes

#### Scenario: All-new with unique open assigns the batch

- GIVEN unused `document_id`s, a valid enabled `seller_id`, `auto_create_sheet`
  ON, and that seller has exactly one open sheet in that company
- WHEN `create_collection_vouchers` runs
- THEN every created voucher MUST be assigned to that sheet
- AND response MUST include each voucher `id`/`name`/`state` and `document_id`
- AND MUST NOT include `sheet_id`

#### Scenario: All-new with no open creates one open sheet and assigns all

- GIVEN unused `document_id`s, a valid enabled `seller_id`, `auto_create_sheet`
  ON, and that seller has zero open sheets in that company
- WHEN `create_collection_vouchers` runs
- THEN one open sheet MUST be created
- AND every created voucher MUST be assigned to it

#### Scenario: All-new with more than one open rejected

- GIVEN unused `document_id`s, a valid enabled `seller_id`, `auto_create_sheet`
  ON, and that seller has more than one open sheet in that company
- WHEN `create_collection_vouchers` runs
- THEN the call MUST raise `UserError` with no vouchers written

#### Scenario: Exact replay does not change sheet_id

- GIVEN every submitted `document_id` already exists in the same company,
  including leftover unassigned vouchers
- WHEN the payload is retried
- THEN each matching voucher’s `sheet_id` MUST be unchanged
- AND no sheet MUST be created, attached, or mutated

#### Scenario: All-new empty or disabled seller rejected

- GIVEN unused `document_id`s and a seller missing from the company's enabled
  list (including an empty list)
- WHEN `create_collection_vouchers` runs
- THEN the call MUST be rejected with no writes

#### Scenario: All-new disallowed type rejected

- GIVEN unused `document_id`s, an enabled seller, and a disabled `document_type`
- WHEN `create_collection_vouchers` runs
- THEN the call MUST be rejected with no writes

#### Scenario: All-new with auto_create_sheet off stays unassigned

- GIVEN unused `document_id`s, an enabled seller, `auto_create_sheet` OFF,
  omitted `sheet_id`, and zero or one open sheet for that seller in that company
- WHEN `create_collection_vouchers` runs
- THEN vouchers MUST be created with no `sheet_id`
- AND no sheet MUST be created or attached

### Requirement: Typed provenance copies of payment fields

Each voucher MUST persist typed raw-OCR and seller-confirmed copies of the
payment review field set. Current columns MUST remain the editable copy.
Provenance MUST NOT include `document_id`, `partner_id`, customer
identification, `seller_id`, attachment, or base64, and MUST NOT copy with the
voucher. Cash-deposit MAY store `voucher_number` and `voucher_date` in all three
layers even when UI hides them. Voucher write MUST reject provenance keys after
create.
(Previously: Exclusion named Char `customer_identification`.)

#### Scenario: Identity and proof stay outside provenance

- GIVEN an all-new MCP payment with `document_id`, customer, seller, and
  attachment
- WHEN create completes
- THEN provenance MUST contain only payment review fields
- AND MUST NOT contain `document_id`, customer, seller, attachment, or base64

#### Scenario: Cash-deposit extra keys stored in all layers

- GIVEN a cash-deposit payment whose nests include `voucher_number` and
  `voucher_date`
- WHEN all-new create completes
- THEN they MUST persist in all three layers
- AND UI MAY hide them for `cash_deposit`

#### Scenario: Voucher write rejects provenance keys

- GIVEN an existing voucher
- WHEN write includes raw or seller-confirmed field keys
- THEN the write MUST be rejected
- AND stored provenance MUST remain unchanged
