# collection-vouchers Specification

## Purpose

Manual vouchers: sequence, pending→approved/rejected, chatter/activities, one voucher
per payment. No WhatsApp/API/agent.

## Requirements

### Requirement: Voucher sequence naming

The system MUST assign each new voucher a unique persisted name matching
`COL/<year>/<number>` via sequence code `collection.voucher`. Each payment MUST consume
one sequence number. (Previously: Sequence applied to a header voucher that could cover
multiple lines.)

#### Scenario: Sequence assigned on create

- GIVEN an internal user creates a voucher
- WHEN saved the first time
- THEN name MUST match `COL/<current-year>/<number>` and be unique

### Requirement: Mail thread and activities

Each voucher MUST support messaging and activities. Voucher fields including `state`
SHOULD be tracked in chatter. (Previously: Chatter lived on the header; scenarios used
header state `new`.)

#### Scenario: Chatter and activities available

- GIVEN an open voucher form
- WHEN a message is posted or an activity scheduled
- THEN it MUST persist on that voucher

#### Scenario: State change tracked

- GIVEN a voucher in `pending`
- WHEN approved or rejected
- THEN chatter MUST record the state change

### Requirement: Authorization for internal users

Internal users (`base.group_user`) MUST have full CRUD on vouchers. The system MUST NOT
grant ACL on `collection.voucher.line`. No dedicated groups or record rules.
(Previously: Full CRUD on vouchers and payment lines.)

#### Scenario: Internal user CRUD

- GIVEN an authenticated internal user
- WHEN they CRUD a voucher
- THEN ACL MUST allow the operation

#### Scenario: Non-internal user denied

- GIVEN a user without internal-user privileges
- WHEN they attempt voucher CRUD
- THEN the system MUST deny access

### Requirement: Deferred integrations not required

Completeness MUST NOT require HTTP API, WhatsApp metadata, partner/CRM linkage, or agent
calls. Optional per-voucher image/PDF attachments are an allowed capability and MUST NOT
be required for completeness of unrelated voucher features. (Previously: Completeness
referred to vouchers with payment lines.)

#### Scenario: Completeness without deferred features

- GIVEN backend-only voucher management
- WHEN operators create, edit, approve, or reject vouchers
- THEN success MUST NOT depend on deferred integrations
- AND success MUST NOT require that vouchers have attachments

### Requirement: Payment document_id uniqueness

Vouchers MUST support nullable Char `document_id` unique among non-null values. UI
vouchers without `document_id` MUST remain allowed. MCP MUST require non-empty
`document_id` per payment. (Previously: Uniqueness and UI omit applied to payment
lines.)

#### Scenario: Manual payment without document_id still OK

- GIVEN a user saving a UI voucher without `document_id`
- WHEN saved
- THEN the voucher MUST persist

### Requirement: MCP optional payment attachment on create

`create_collection_vouchers` MAY accept one optional nested attachment per payment with
required `name`, `mimetype`, and base64 `datas` when present. Declared `mimetype` MUST
match content detection (`image/*` or PDF only); mismatch or bad base64 MUST raise
`UserError` with no writes. Create with attachments MUST persist all vouchers and files
atomically under a savepoint. Exact-retry by `document_id` MUST return all matching
vouchers and MUST NOT add, replace, or compare attachments (even when a voucher has
none). All-new and conflict rules MUST remain unchanged. (Previously: Nested attachments
on singular `create_collection_voucher`; exact-retry returned one header voucher.)

#### Scenario: MCP create with nested attachment

- GIVEN unused `document_id`s and a payment with valid nested attachment
- WHEN `create_collection_vouchers` runs
- THEN vouchers and attachments MUST persist atomically under a savepoint

#### Scenario: MCP attachment MIME mismatch rejected

- GIVEN nested attachment with mismatched or non-image/non-PDF `mimetype`
- WHEN `create_collection_vouchers` runs
- THEN MUST raise `UserError` with no writes

#### Scenario: Exact-retry skips attachment writes

- GIVEN every submitted `document_id` already exists
- WHEN retried with or without nested attachments
- THEN all matching vouchers return unchanged; attachments MUST NOT be
  written/replaced/compared

### Requirement: Concurrent and stale review attempts

Approve and reject MUST refuse stale or concurrent attempts when the voucher is no
longer eligible (not `pending`, or attachment no longer present) and MUST NOT corrupt
review or voucher state. (Previously: Eligibility also required a parent voucher in
`new` and a line record.)

#### Scenario: Concurrent or stale review attempt

- GIVEN a voucher already decided or otherwise ineligible for review
- WHEN approve or reject is attempted again
- THEN the system MUST refuse the action and MUST NOT alter terminal or decided state

### Requirement: Attachment replacement resets review to pending

Replacing a voucher attachment (write of new Binary content) MUST reset that voucher’s
`state` to `pending` and MUST clear prior reviewer/time audit for a fresh review.
Omit/empty and MIME validation rules remain unchanged. (Previously: Replacement reset
the payment line’s `state` and audit.)

#### Scenario: Attachment replacement resets voucher state

- GIVEN a voucher previously `approved` or `rejected` with an attachment
- WHEN a new valid attachment replaces the prior file
- THEN `state` MUST become `pending`
- AND prior reviewer/time audit MUST be cleared for re-review

### Requirement: Voucher fields and defaults

Each `collection.voucher` MUST represent one payment. The system MUST require
`customer_identification`. The system MUST NOT store or accept `received_date`.
Registration time MUST be automatic ORM `create_date` (readonly; MUST NOT be overridable
by MCP, create vals, or editable views). On create, `state` MUST default to `pending`.
Currency MUST be the company default (no multi-currency UX).

#### Scenario: Defaults on create

- GIVEN a new voucher saved without overriding defaults
- WHEN create completes
- THEN `create_date` MUST be automatic, `state` `pending`, currency company default
- AND `received_date` MUST NOT exist

#### Scenario: Required fields

- GIVEN a voucher missing `customer_identification`
- WHEN saved
- THEN the system MUST reject the save

#### Scenario: create_date not overridable

- GIVEN a create that supplies custom creation time or `received_date`
- WHEN create runs via UI or MCP
- THEN creation time MUST NOT be caller-overridable and `received_date` MUST NOT persist

### Requirement: Voucher lifecycle

States MUST be `pending`, `approved`, and `rejected`. Approve and Reject MUST apply only
from `pending` and MUST NOT alter terminal states. Delete MUST be allowed only when
`state` is `pending`. Any user-driven change from `pending` to `approved` or `rejected`
(including kanban drag) MUST record reviewer and review time the same as Approve/Reject.
Approve/Reject on Payment Vouchers MUST remain available whether Document Review is ON
or OFF. Review queue RPCs remain governed by `document-review`. Confidence, per-field
stamps, and reviewer-note persistence MUST NOT be required.

#### Scenario: Approve from pending

- GIVEN a voucher in `pending`
- WHEN approved
- THEN `state` MUST become `approved`
- AND reviewer and review time MUST be recorded

#### Scenario: Reject from pending

- GIVEN a voucher in `pending`
- WHEN rejected
- THEN `state` MUST become `rejected`
- AND reviewer and review time MUST be recorded

#### Scenario: Terminal states block transitions

- GIVEN a voucher in `approved` or `rejected`
- WHEN Approve or Reject is attempted
- THEN `state` MUST NOT change

#### Scenario: Delete from pending

- GIVEN a voucher in `pending`
- WHEN deleted
- THEN the system MUST allow the delete

#### Scenario: Delete blocked when not pending

- GIVEN a voucher in `approved` or `rejected`
- WHEN deleted
- THEN the system MUST refuse the delete

#### Scenario: Kanban drag is audited

- GIVEN a `pending` voucher on a state-grouped kanban
- WHEN an internal user drags it to `approved` or `rejected`
- THEN `state` MUST change to that value
- AND reviewer and review time MUST be recorded as for Approve/Reject

#### Scenario: Approve and Reject remain when review is off

- GIVEN Document Review is OFF and a voucher in `pending`
- WHEN Approve or Reject is used on Payment Vouchers
- THEN `state` MUST become `approved` or `rejected` respectively

#### Scenario: Default pending

- GIVEN a newly created voucher
- WHEN `state` is read without a prior decision
- THEN `state` MUST be `pending`

### Requirement: Payment field contract

Each voucher MUST persist `document_type` `bank_transfer` | `check` | `cash_deposit` |
`unsupported` and nullable payment fields (OCR validators NOT required): `amount`,
`from_account`, `to_account`, `voucher_number`, `voucher_date`, `check_number`,
`check_bank`, `check_issue_date`, `check_payment_date`, `check_type` Selection
`common`/`deferred`. `unsupported` MUST persist without other payment fields.

#### Scenario: Persist type-specific fields

- GIVEN `bank_transfer`, `check`, and `cash_deposit` vouchers with payment fields filled
  (`check_type` `common` or `deferred`)
- WHEN saved
- THEN each voucher MUST persist those values

#### Scenario: Unsupported and partial entry

- GIVEN an `unsupported` voucher plus a partial supported-type voucher
- WHEN saved
- THEN both MUST persist

### Requirement: Payment Vouchers UI

The system MUST expose Collections → Payment Vouchers as the only create/edit surface
(kanban, list, and form; create and edit enabled). Kanban MUST group by `state`.
List/search MUST show reference, customer identification, readonly `create_date`,
status, and payment fields. Form MUST show statusbar, Approve/Reject when `pending`,
readonly `create_date`, payment fields for the voucher’s `document_type`, chatter and
activity controls, and MUST NOT show `received_date`. The system MUST NOT expose
Collections → Payment Lines or typed embedded payment-line tables.

#### Scenario: Menu and form behaviors

- GIVEN the module installed and a voucher in `pending`
- WHEN an internal user opens Collections → Payment Vouchers then the form
- THEN list/search MUST show reference, customer identification, `create_date`, status
- AND form MUST show statusbar, Approve/Reject, readonly `create_date`, chatter/activity
  UI without `received_date`
- AND form MUST show that voucher’s payment fields and MUST NOT show payment-line tables

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

### Requirement: Unsupported vouchers remain persistable

`unsupported` vouchers MUST remain persistable (e.g. MCP) and MUST be findable via
Collections → Payment Vouchers (e.g. filter `document_type=unsupported`).

#### Scenario: Unsupported voucher visible in Payment Vouchers

- GIVEN an `unsupported` voucher exists
- WHEN an internal user opens Collections → Payment Vouchers and filters to
  `unsupported`
- THEN that voucher MUST be listed

### Requirement: MCP tool create_collection_vouchers

The system MUST expose `create_collection_vouchers` via `@mcp_tool` on `muk_mcp.mixin`
(`category=write`, `registry=mcp`), method-discovered — MUST NOT use a DB `muk_mcp.tool`
record. Calls MUST use the authenticated user (MUST NOT `sudo()`); voucher ACL MUST
apply. Input MUST require `customer_identification`, non-empty `payments`, and top-level
`seller_id`; MUST NOT accept `received_date`. `seller_id` MUST identify an existing
internal user; missing, portal/share, or unknown ids MUST be rejected with no writes.
Each MCP payment MUST include non-empty `document_id` and existing payment fields
(`document_type` required). Create MUST persist one voucher per payment atomically
(`state=pending`, company currency) and MUST stamp `seller_id` only on all-new create.
All-new create MUST auto-assign sheets via the same ORM create rules as UI voucher
create (`seller_id` set, `sheet_id` omitted). Exact replay MUST NOT attach, move, or
clear sheets (including leftover unassigned). The tool MUST NOT accept `sheet_id` in the
payload and MUST NOT return `sheet_id`. Response MUST include each voucher
`id`/`name`/`state` and `document_id` (`state` is voucher state). Idempotency by
`document_id`: all-new → create N vouchers; every submitted `document_id` already exists
→ return ALL those vouchers unchanged; in-call duplicate or partial overlap → reject
with no writes. Submitted `document_id`s that already exist on different vouchers MUST
succeed as exact replay (MUST NOT reject as a cross-voucher conflict). Exact replay MUST
ignore `customer_identification`, nested attachments, and `seller_id`, and MUST NOT
mutate matching vouchers (including legacy null `seller_id` and `sheet_id`). Attachment
atomicity and `document_id` uniqueness rules remain unchanged.
(Previously: All-new stamped `seller_id` but did not assign sheets; exact replay ignored
customer, attachments, and `seller_id` with no sheet attach or move.)

#### Scenario: All-new create

- GIVEN an internal user, unused payment `document_id`s, and a valid internal
  `seller_id`
- WHEN `create_collection_vouchers` runs with valid customer, payments, and `seller_id`
- THEN one voucher per payment MUST be created atomically with that `seller_id`
- AND response MUST include each voucher `id`/`name`/`state` and `document_id`

#### Scenario: Exact-retry returns all vouchers

- GIVEN every submitted `document_id` already exists, including legacy null `seller_id`
- WHEN the same payload is retried with any `seller_id`
- THEN all matching vouchers MUST return unchanged with no new rows
- AND customer identification, nested attachments, and `seller_id` MUST be ignored
- AND matching vouchers MUST NOT be mutated

#### Scenario: Duplicate document_id in call

- GIVEN two payments in one call share a `document_id`
- WHEN `create_collection_vouchers` runs
- THEN the call MUST be rejected with no writes

#### Scenario: Partial-conflict

- GIVEN some submitted `document_id`s exist and others do not
- WHEN `create_collection_vouchers` runs
- THEN the call MUST be rejected with no writes

#### Scenario: Existing document_ids on different vouchers succeed

- GIVEN submitted `document_id`s already exist on more than one voucher
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

- GIVEN unused `document_id`s, a valid `seller_id`, and that seller has exactly one open
  sheet
- WHEN `create_collection_vouchers` runs
- THEN every created voucher MUST be assigned to that sheet
- AND response MUST include each voucher `id`/`name`/`state` and `document_id`
- AND MUST NOT include `sheet_id`

#### Scenario: All-new with no open creates one open sheet and assigns all

- GIVEN unused `document_id`s, a valid `seller_id`, and that seller has zero open sheets
- WHEN `create_collection_vouchers` runs
- THEN one open sheet MUST be created
- AND every created voucher MUST be assigned to it

#### Scenario: All-new with more than one open rejected

- GIVEN unused `document_id`s, a valid `seller_id`, and that seller has more than one
  open sheet
- WHEN `create_collection_vouchers` runs
- THEN the call MUST raise `UserError` with no vouchers written

#### Scenario: Exact replay does not change sheet_id

- GIVEN every submitted `document_id` already exists, including leftover unassigned
  vouchers
- WHEN the payload is retried
- THEN each matching voucher’s `sheet_id` MUST be unchanged
- AND no sheet MUST be created or attached

### Requirement: Optional image or PDF attachment per voucher

Each `collection.voucher` MAY store one optional proof as Binary (`attachment=True`)
plus filename via `ir.attachment`. Omit/empty MUST remain valid. Fields MUST be
optional, `copy=False`, under existing internal-user voucher ACL. MUST validate base64
and detected MIME (`image/*` or PDF only); MUST raise `UserError` otherwise.

#### Scenario: Omit attachment valid

- GIVEN a voucher with no attachment
- WHEN saved
- THEN the voucher MUST persist

#### Scenario: Valid file persists

- GIVEN a voucher with valid base64 image/PDF and filename
- WHEN saved
- THEN Binary and filename MUST persist via `ir.attachment`

#### Scenario: Invalid content rejected

- GIVEN invalid base64 or non-image/non-PDF MIME
- WHEN saved
- THEN MUST raise `UserError` and MUST NOT persist the file

### Requirement: Attachment widgets on Payment Vouchers views

Payment Vouchers form, list, and kanban MUST include optional Binary attachment and
filename widgets. Browser accept MUST be limited to `image/*` and PDF.

#### Scenario: Payment Vouchers views show Binary widgets

- GIVEN Collections → Payment Vouchers
- WHEN an internal user opens form, list, or kanban
- THEN Binary attachment and filename widgets MUST be present
- AND browser accept MUST allow `image/*` and PDF

### Requirement: Destructive reset of legacy header and line data

On apply, the system MAY discard legacy header vouchers, payment lines, chatter, and
attachments. The system MUST NOT convert header+line rows, chatter, or attachments into
standalone vouchers.

#### Scenario: Upgrade without conversion

- GIVEN a database with header vouchers and payment lines
- WHEN this change is applied
- THEN legacy header/line data MAY be absent
- AND historical vouchers MUST NOT be required as converted standalone records

### Requirement: Voucher seller field

Each `collection.voucher` MUST support nullable `seller_id` targeting an internal user
(not portal/share). The system MUST NOT backfill existing rows. ORM/RPC creates without
seller MUST remain allowed. New Payment Vouchers form creates MUST require `seller_id`.
List, form, and search MUST expose `seller_id`.

#### Scenario: Legacy null remains valid

- GIVEN an existing voucher with null `seller_id`
- WHEN loaded or saved without assigning a sheet
- THEN the voucher MUST persist with null seller

#### Scenario: ORM create without seller

- GIVEN an internal user creates a voucher via ORM without `seller_id`
- WHEN create completes
- THEN the voucher MUST persist with null seller

#### Scenario: Form create requires seller

- GIVEN a new Payment Vouchers form
- WHEN saved without `seller_id`
- THEN the system MUST reject the save

#### Scenario: Seller visible on list form search

- GIVEN an existing voucher with or without seller
- WHEN list, form, or search is opened
- THEN `seller_id` MUST be visible

### Requirement: Create auto-assign to open sheet

On voucher create, when `seller_id` is set and `sheet_id` is omitted, the system MUST
auto-assign: unique open sheet → assign; none → create one open sheet then assign; more
than one open → `UserError` with no write. Null `seller_id` MUST leave the voucher
unassigned. Explicit `sheet_id` MUST be honored when the target is the same seller and
`open`; assign to a closed sheet MUST fail. Write of `seller_id` on an existing voucher
MUST NOT auto-assign. The system MUST NOT backfill existing unassigned vouchers.

#### Scenario: UI or ORM create with seller assigns

- GIVEN a seller with exactly one open sheet
- WHEN a voucher is created with that `seller_id` and omitted `sheet_id`
- THEN the voucher MUST be assigned to that open sheet

#### Scenario: Create without seller stays unassigned

- GIVEN a voucher create with null `seller_id` and omitted `sheet_id`
- WHEN create completes
- THEN the voucher MUST persist unassigned

#### Scenario: Explicit sheet_id honored when open

- GIVEN an open same-seller sheet
- WHEN a voucher is created with that `seller_id` and explicit `sheet_id`
- THEN the voucher MUST be assigned to that sheet

#### Scenario: Assign to closed sheet fails

- GIVEN a closed same-seller sheet
- WHEN a voucher is created or written with that `sheet_id`
- THEN the write MUST fail

#### Scenario: Later seller write does not auto-assign

- GIVEN an existing unassigned voucher
- WHEN `seller_id` is written
- THEN `sheet_id` MUST remain empty

#### Scenario: No open sheet creates then assigns

- GIVEN a seller with zero open sheets
- WHEN a voucher is created with that `seller_id` and omitted `sheet_id`
- THEN one open sheet MUST be created for that seller
- AND the voucher MUST be assigned to it

#### Scenario: More than one open rejects create

- GIVEN a seller with more than one open sheet
- WHEN a voucher is created with that `seller_id` and omitted `sheet_id`
- THEN create MUST raise `UserError` with no voucher written
