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

The system MUST expose Collections → Payment Vouchers and Collections → Payment Lines.
List/search for vouchers MUST show reference, customer identification, readonly
`create_date`, and status. Form MUST show statusbar, Validate/Reject when `new`,
readonly `create_date`, and chatter/activity controls. Views MUST NOT show
`received_date`.

The voucher form MUST NOT use a single all-type editable payment-lines table. It MUST
show three stacked editable tables for `bank_transfer`, `check`, and `cash_deposit`
(same `collection.voucher.line` model), in that order, each filtered to its
`document_type`. Each table MUST hide `document_type` and MUST default new rows to that
table’s type. Field sets MUST be:

- `bank_transfer`: `document_id`, `amount`, `from_account`, `to_account`,
  `voucher_number`, `voucher_date`
- `check`: `document_id`, `amount`, `check_number`, `check_bank`, `check_type`,
  `check_issue_date`, `check_payment_date`
- `cash_deposit`: `document_id`, `amount`

A voucher MUST still allow mixed supported document types across those tables. The form
MUST NOT provide an editable table for `unsupported` lines. (Previously: Collections →
Payment Vouchers only; form used one editable `payment_ids` list showing `document_type`
and optional mixed columns.)

#### Scenario: Menu and form behaviors

- GIVEN the module installed and a voucher in `new`
- WHEN an internal user opens Collections → Payment Vouchers then the form
- THEN list/search MUST show reference, customer identification, `create_date`, status
- AND form MUST show statusbar, Validate/Reject, readonly `create_date`,
  chatter/activity UI without `received_date`
- AND form MUST show three stacked editable typed line tables (`bank_transfer`, `check`,
  `cash_deposit`) and MUST NOT show a single all-type payment-lines list

#### Scenario: Typed table defaults and fields

- GIVEN a voucher form open for editing
- WHEN an internal user adds a row in the bank transfer, check, or cash deposit table
- THEN the new line MUST receive that table’s `document_type`
- AND the table MUST expose only that type’s field set including `document_id`
- AND MUST NOT show a `document_type` column

#### Scenario: Mixed types on one voucher

- GIVEN a voucher with at least one bank transfer line and one check line
- WHEN the form is opened
- THEN each line MUST appear only in its matching typed table

#### Scenario: Payment Lines menu read-only browse

- GIVEN the module installed and existing payment lines
- WHEN an internal user opens Collections → Payment Lines
- THEN the action MUST list `collection.voucher.line` records
- AND create/edit from that action MUST be disabled
- AND search MUST allow filtering by line fields including `document_type`,
  `document_id`, `amount`, type-specific payment fields, and related voucher

#### Scenario: UI create_date visibility

- GIVEN an existing voucher
- WHEN list, search, kanban, or form is opened
- THEN readonly `create_date` MUST be visible and not editable

### Requirement: Unsupported lines remain non-editable on voucher form

`unsupported` payment lines MUST remain persistable (e.g. MCP) but MUST NOT appear in
the three typed editable form tables. Operators MUST be able to find them via
Collections → Payment Lines (e.g. filter `document_type=unsupported`).

#### Scenario: Unsupported line not in typed form tables

- GIVEN a voucher that has an `unsupported` payment line
- WHEN an internal user opens the voucher form
- THEN that line MUST NOT appear in the bank transfer, check, or cash deposit tables

#### Scenario: Unsupported line visible in Payment Lines menu

- GIVEN an `unsupported` payment line exists
- WHEN an internal user opens Collections → Payment Lines and filters to `unsupported`
- THEN that line MUST be listed

### Requirement: Deferred integrations not required

Completeness MUST NOT require HTTP API, WhatsApp metadata, partner/CRM linkage, or agent
calls. Optional per-line image/PDF attachments are an allowed capability and MUST NOT be
required for completeness of unrelated voucher features. (Previously: Completeness also
MUST NOT require attachments.)

#### Scenario: Completeness without deferred features

- GIVEN backend-only voucher management
- WHEN operators create, edit, validate, or reject vouchers with payment lines
- THEN success MUST NOT depend on deferred integrations
- AND success MUST NOT require that payment lines have attachments

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

### Requirement: Optional image or PDF attachment per payment line

Each `collection.voucher.line` MAY store one optional proof as Binary
(`attachment=True`) plus filename via `ir.attachment`. Omit/empty MUST remain valid.
Fields MUST be optional, `copy=False`, under existing internal-user line ACL. MUST
validate base64 and detected MIME (`image/*` or PDF only); MUST raise `UserError`
otherwise.

#### Scenario: Omit attachment valid

- GIVEN a payment line with no attachment
- WHEN saved
- THEN the line MUST persist

#### Scenario: Valid file persists

- GIVEN a line with valid base64 image/PDF and filename
- WHEN saved
- THEN Binary and filename MUST persist via `ir.attachment`

#### Scenario: Invalid content rejected

- GIVEN invalid base64 or non-image/non-PDF MIME
- WHEN saved
- THEN MUST raise `UserError` and MUST NOT persist the file

### Requirement: Attachment widgets on typed and Payment Lines views

Each typed embedded list field set (`bank_transfer`, `check`, `cash_deposit`) and
Payment Lines views MUST include optional Binary attachment and filename widgets.
Browser accept MUST be limited to `image/*` and PDF.

#### Scenario: Typed tables show Binary widgets

- GIVEN a voucher form open for editing
- WHEN a typed payment-line table is shown
- THEN it MUST include Binary attachment and filename widgets
- AND browser accept MUST allow `image/*` and PDF

#### Scenario: Payment Lines views show Binary widgets

- GIVEN Collections → Payment Lines
- WHEN an internal user opens list or form views for a line
- THEN Binary attachment and filename widgets MUST be present
- AND browser accept MUST allow `image/*` and PDF

### Requirement: MCP optional payment attachment on create

`create_collection_voucher` MAY accept one optional nested attachment per payment with
required `name`, `mimetype`, and base64 `datas` when present. Declared `mimetype` MUST
match content detection (`image/*` or PDF only); mismatch or bad base64 MUST raise
`UserError` with no writes. Create with attachments MUST persist voucher, lines, and
files atomically under a savepoint. Exact-retry by `document_id` MUST return the
existing voucher and MUST NOT add, replace, or compare attachments (even when the line
has none). All-new and conflict rules MUST remain unchanged.

#### Scenario: MCP create with nested attachment

- GIVEN unused `document_id`s and a payment with valid nested attachment
- WHEN `create_collection_voucher` runs
- THEN voucher, lines, and attachment MUST persist atomically under a savepoint

#### Scenario: MCP attachment MIME mismatch rejected

- GIVEN nested attachment with mismatched or non-image/non-PDF `mimetype`
- WHEN `create_collection_voucher` runs
- THEN MUST raise `UserError` with no writes

#### Scenario: Exact-retry skips attachment writes

- GIVEN all submitted `document_id`s belong to one existing voucher
- WHEN retried with or without nested attachments
- THEN voucher returns unchanged; attachments MUST NOT be written/replaced/compared
