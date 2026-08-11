# collection-vouchers Specification

## Purpose

Manual vouchers: sequence, New→Validated/Rejected, chatter/activities, payment lines. No
WhatsApp/API/agent.

## Requirements

### Requirement: Voucher sequence naming

The system MUST assign each new voucher a unique persisted name matching
`COL/<year>/<number>`.

#### Scenario: Sequence assigned on create

- GIVEN an internal user creates a voucher
- WHEN saved the first time
- THEN name MUST match `COL/<current-year>/<number>` and be unique

### Requirement: Voucher header fields and defaults

The system MUST require `customer_identification`. The system MUST NOT store or accept
`received_date`. Registration time MUST be automatic ORM `create_date` (readonly; MUST
NOT be overridable by MCP, create vals, or editable views). On create, `state` MUST
default to `new`. Currency MUST be the company default (no multi-currency UX).
(Previously: Required `received_date` defaulting to today.)

#### Scenario: Defaults on create

- GIVEN a new voucher saved without overriding defaults
- WHEN create completes
- THEN `create_date` MUST be automatic, `state` `new`, currency company default
- AND `received_date` MUST NOT exist

#### Scenario: Required header fields

- GIVEN a voucher missing `customer_identification`
- WHEN saved
- THEN the system MUST reject the save

#### Scenario: create_date not overridable

- GIVEN a create that supplies custom creation time or `received_date`
- WHEN create runs via UI or MCP
- THEN creation time MUST NOT be caller-overridable and `received_date` MUST NOT persist

### Requirement: Voucher state transitions

States MUST be `new`, `validated`, and `rejected`. Validate and Reject MUST apply only
from `new` and MUST NOT alter terminal states.

#### Scenario: Validate from new

- GIVEN a voucher in `new`
- WHEN validated
- THEN `state` MUST become `validated`

#### Scenario: Reject from new

- GIVEN a voucher in `new`
- WHEN rejected
- THEN `state` MUST become `rejected`

#### Scenario: Terminal states block transitions

- GIVEN a voucher in `validated` or `rejected`
- WHEN Validate or Reject is attempted
- THEN `state` MUST NOT change

### Requirement: Mail thread and activities

Each voucher MUST support messaging and activities. Header fields including `state`
SHOULD be tracked in chatter.

#### Scenario: Chatter and activities available

- GIVEN an open voucher form
- WHEN a message is posted or an activity scheduled
- THEN it MUST persist on that voucher

#### Scenario: State change tracked

- GIVEN a voucher in `new`
- WHEN validated or rejected
- THEN chatter MUST record the state change

### Requirement: Payment lines and payment field contract

Vouchers MUST allow zero or more payment lines with `document_type` `bank_transfer` |
`check` | `cash_deposit` | `unsupported`. Persist nullable fields (OCR validators NOT
required): `amount`, `from_account`, `to_account`, `voucher_number`, `voucher_date`,
`check_number`, `check_bank`, `check_issue_date`, `check_payment_date`, `check_type`
Selection `common`/`deferred`. `unsupported` MUST persist without other payment fields.

#### Scenario: Persist type-specific fields

- GIVEN `bank_transfer`, `check`, and `cash_deposit` lines with payment fields filled
  (`check_type` `common` or `deferred`)
- WHEN saved
- THEN each line MUST persist those values

#### Scenario: Unsupported and partial entry

- GIVEN an `unsupported` line plus a partial supported-type line
- WHEN saved
- THEN both MUST persist

### Requirement: Authorization for internal users

Internal users (`base.group_user`) MUST have full CRUD on vouchers and payment lines. No
dedicated groups or record rules.

#### Scenario: Internal user CRUD

- GIVEN an authenticated internal user
- WHEN they CRUD a voucher or payment line
- THEN ACL MUST allow the operation

#### Scenario: Non-internal user denied

- GIVEN a user without internal-user privileges
- WHEN they attempt voucher or payment CRUD
- THEN the system MUST deny access

### Requirement: Menu and backend UI

The system MUST expose Collections → Payment Vouchers. List/search MUST show reference,
customer identification, readonly `create_date`, and status. Form MUST show statusbar,
Validate/Reject when `new`, editable payment lines, readonly `create_date`, and
chatter/activity controls. Views MUST NOT show `received_date`. (Previously: Views
showed `received_date` instead of `create_date`.)

#### Scenario: Menu and form behaviors

- GIVEN the module installed and a voucher in `new`
- WHEN an internal user opens Collections → Payment Vouchers then the form
- THEN list/search MUST show reference, customer identification, `create_date`, status
- AND form MUST show statusbar, Validate/Reject, editable lines, readonly `create_date`,
  chatter/activity UI without `received_date`

#### Scenario: UI create_date visibility

- GIVEN an existing voucher
- WHEN list, search, kanban, or form is opened
- THEN readonly `create_date` MUST be visible and not editable

### Requirement: Deferred integrations not required

Completeness MUST NOT require HTTP API, WhatsApp metadata, attachments, partner/CRM
linkage, or agent calls.

#### Scenario: Completeness without deferred features

- GIVEN backend-only voucher management
- WHEN operators create, edit, validate, or reject vouchers with payment lines
- THEN success MUST NOT depend on deferred integrations

### Requirement: MCP tool create_collection_voucher

The system MUST expose `create_collection_voucher` via `@mcp_tool` on `muk_mcp.mixin`
(`category=write`, `registry=mcp`), method-discovered — MUST NOT use a DB `muk_mcp.tool`
record. Calls MUST use the authenticated user (MUST NOT `sudo()`); voucher/payment ACL
MUST apply. Input MUST require `customer_identification` and non-empty `payments`; MUST
NOT accept `received_date`. Each MCP payment MUST include non-empty `document_id` and
existing payment fields (`document_type` required). Create MUST persist voucher + lines
atomically (`state=new`, company currency). Response MUST include voucher
`id`/`name`/`state` and payment `id`/`document_id`. Idempotency by `document_id`:
all-new → create; full same-voucher match → return existing; in-call duplicate, partial
overlap, or cross-voucher match → reject with no writes.

#### Scenario: All-new create

- GIVEN an internal user and unused payment `document_id`s
- WHEN `create_collection_voucher` runs with valid customer and payments
- THEN one voucher and those lines MUST be created
- AND response MUST include voucher `id`/`name`/`state` and payment `id`/`document_id`

#### Scenario: Exact-retry same voucher

- GIVEN all submitted `document_id`s belong to one existing voucher
- WHEN the same payload is retried
- THEN that voucher and payments MUST return unchanged with no new rows

#### Scenario: Duplicate document_id in call

- GIVEN two payments in one call share a `document_id`
- WHEN `create_collection_voucher` runs
- THEN the call MUST be rejected with no writes

#### Scenario: Partial-conflict

- GIVEN some submitted `document_id`s exist and others do not
- WHEN `create_collection_voucher` runs
- THEN the call MUST be rejected with no writes

#### Scenario: Cross-voucher-conflict

- GIVEN submitted `document_id`s span more than one voucher
- WHEN `create_collection_voucher` runs
- THEN the call MUST be rejected with no writes

#### Scenario: ACL denial for non-permitted user

- GIVEN a caller without voucher/payment create rights
- WHEN `create_collection_voucher` runs
- THEN access MUST be denied with no writes

### Requirement: Payment document_id uniqueness

Payment lines MUST support nullable Char `document_id` unique among non-null values. UI
lines without `document_id` MUST remain allowed. MCP MUST require non-empty
`document_id` per payment.

#### Scenario: Manual payment without document_id still OK

- GIVEN a user saving a UI payment line without `document_id`
- WHEN saved
- THEN the line MUST persist
