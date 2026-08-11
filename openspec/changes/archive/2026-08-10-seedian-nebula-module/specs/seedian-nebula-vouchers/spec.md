# seedian-nebula-vouchers Specification

## Purpose

Manual vouchers: sequence, New→Validated/Rejected, chatter/activities, Nebula payment lines. No WhatsApp/API/agent.

## ADDED Requirements

### Requirement: Voucher sequence naming

The system MUST assign each new voucher a unique persisted name matching `NEB/<year>/<number>`.

#### Scenario: Sequence assigned on create

- GIVEN an internal user creates a voucher
- WHEN saved the first time
- THEN name MUST match `NEB/<current-year>/<number>` and be unique

### Requirement: Voucher header fields and defaults

The system MUST require `customer_identification` and `received_date`. On create, `received_date` MUST default to today and `state` to `new`. Currency MUST be the company technical default (no multi-currency UX).

#### Scenario: Defaults on create

- GIVEN a new voucher saved without overriding defaults
- WHEN create completes
- THEN `received_date` MUST be today, `state` `new`, currency company default

#### Scenario: Required header fields

- GIVEN a voucher missing `customer_identification` or `received_date`
- WHEN saved
- THEN the system MUST reject the save

### Requirement: Voucher state transitions

States MUST be `new`, `validated`, and `rejected`. Validate and Reject MUST apply only from `new` and MUST NOT alter terminal states.

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

Each voucher MUST support messaging and activities. Header fields including `state` SHOULD be tracked in chatter.

#### Scenario: Chatter and activities available

- GIVEN an open voucher form
- WHEN a message is posted or an activity scheduled
- THEN it MUST persist on that voucher

#### Scenario: State change tracked

- GIVEN a voucher in `new`
- WHEN validated or rejected
- THEN chatter MUST record the state change

### Requirement: Payment lines and Nebula field contract

Vouchers MUST allow zero or more payment lines with `document_type` `bank_transfer` | `check` | `cash_deposit` | `unsupported`. Persist nullable fields (OCR validators NOT required): `amount`, `from_account`, `to_account`, `voucher_number`, `voucher_date`, `check_number`, `check_bank`, `check_issue_date`, `check_payment_date`, `check_type` Selection `common`/`deferred`. `unsupported` MUST persist without other payment fields.

#### Scenario: Persist type-specific fields

- GIVEN `bank_transfer`, `check`, and `cash_deposit` lines with Nebula fields filled (`check_type` `common` or `deferred`)
- WHEN saved
- THEN each line MUST persist those values

#### Scenario: Unsupported and partial entry

- GIVEN an `unsupported` line plus a partial supported-type line
- WHEN saved
- THEN both MUST persist

### Requirement: Authorization for internal users

Internal users (`base.group_user`) MUST have full CRUD on vouchers and payment lines. No dedicated groups or record rules.

#### Scenario: Internal user CRUD

- GIVEN an authenticated internal user
- WHEN they CRUD a voucher or payment line
- THEN ACL MUST allow the operation

#### Scenario: Non-internal user denied

- GIVEN a user without internal-user privileges
- WHEN they attempt voucher or payment CRUD
- THEN the system MUST deny access

### Requirement: Menu and backend UI

The system MUST expose Nebula → Payment Vouchers. List/search MUST show reference, customer identification, received date, and status. Form MUST show statusbar, Validate/Reject when `new`, editable payment lines, and chatter/activity controls.

#### Scenario: Menu and form behaviors

- GIVEN the module installed and a voucher in `new`
- WHEN an internal user opens Nebula → Payment Vouchers then the form
- THEN list/search MUST show reference, customer identification, received date, and status
- AND form MUST show statusbar, Validate/Reject, editable payment lines, and chatter/activity UI

### Requirement: Deferred integrations not required

Completeness MUST NOT require HTTP API, WhatsApp metadata, attachments, partner/CRM linkage, or Nebula agent calls.

#### Scenario: Completeness without deferred features

- GIVEN backend-only voucher management
- WHEN operators create, edit, validate, or reject vouchers with payment lines
- THEN success MUST NOT depend on deferred integrations
