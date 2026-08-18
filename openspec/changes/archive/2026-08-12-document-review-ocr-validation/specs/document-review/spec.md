# Document Review Specification

## Purpose

Internal-user Document Review client: queue eligible payment-line proofs, correct OCR’d
fields against the attachment, and approve/reject without mock data.

## Requirements

### Requirement: Eligible review queue

The system MUST queue only `collection.voucher.line` records where the parent voucher
`state` is `new`, the line review status is `pending`, and an attachment is present.
Lines missing any eligibility criterion MUST NOT appear. Confidence scores, per-field
stamps, and reviewer-note persistence MUST NOT be required.

#### Scenario: Queue eligibility

- GIVEN lines on `new` vouchers with pending review and attachment, plus ineligible
  lines (non-`new`, non-pending, or no attachment)
- WHEN an internal user opens Document Review
- THEN only eligible lines MUST appear in the queue

#### Scenario: Empty queue

- GIVEN no eligible pending attached lines on `new` vouchers
- WHEN Document Review opens
- THEN the client MUST show an empty/no-remaining-work state

### Requirement: OWL client loads real ORM data

The Document Review OWL client MUST load queue and line data via ORM (no mocks). It MUST
support typed editable inputs, queue navigation, and advance to the next eligible record
after a successful approve or reject.

#### Scenario: Typed editable fields by document type

- GIVEN a queued `bank_transfer`, `check`, or `cash_deposit` line
- WHEN shown in Document Review
- THEN `document_type` and `amount` MUST be editable
- AND type-specific fields MUST be editable: bank transfer (`from_account`,
  `to_account`, `voucher_number`, `voucher_date`); check (`check_number`, `check_bank`,
  `check_type`, `check_issue_date`, `check_payment_date`); cash deposit
  (amount/`document_type` only beyond shared)

#### Scenario: Readonly context fields

- GIVEN a queued line
- WHEN shown in Document Review
- THEN `document_id`, voucher reference, and queue position MUST be readonly

#### Scenario: Navigate and next record after decision

- GIVEN more than one eligible queued line
- WHEN the reviewer navigates or successfully approves/rejects the current line
- THEN the client MUST move to the requested or next eligible record without mocks

### Requirement: Authenticated binary attachment viewer

The client MUST render image and PDF proofs via an authenticated binary route. The OWL
layer MUST NOT embed attachment base64. The viewer MUST present distinct loading, error,
and empty-attachment states.

#### Scenario: Image via authenticated binary route

- GIVEN an eligible line with an image attachment
- WHEN Document Review shows the proof
- THEN the image MUST load from an authenticated binary URL
- AND OWL MUST NOT hold the attachment as base64

#### Scenario: PDF via authenticated binary route

- GIVEN an eligible line with a PDF attachment
- WHEN Document Review shows the proof
- THEN the PDF MUST load from an authenticated binary URL
- AND OWL MUST NOT hold the attachment as base64

#### Scenario: Viewer loading, error, and empty states

- GIVEN a line whose attachment is loading, fails to load, or is absent/empty
- WHEN the viewer renders
- THEN it MUST show the matching loading, error, or empty state

### Requirement: Approve and reject without mocks

Approve and reject MUST call real server actions (no mock handlers). Approve MUST
persist field corrections before updating review status. Reject and approve outcomes for
voucher aggregate state are governed by `collection-vouchers`.

#### Scenario: Correction persistence on approve

- GIVEN an eligible pending line with edited payment fields
- WHEN the reviewer approves
- THEN corrected field values MUST persist on the line
- AND review status MUST become `approved`

#### Scenario: Reject invokes real action

- GIVEN an eligible pending line
- WHEN the reviewer rejects
- THEN the server reject action MUST run (no mock)
- AND the line review status MUST become `rejected`

### Requirement: Document Review authorization

Only internal users (`base.group_user`) MUST access Document Review queue and
approve/reject actions.

#### Scenario: Non-internal user denied Document Review

- GIVEN a user without internal-user privileges
- WHEN they attempt Document Review queue access or approve/reject
- THEN the system MUST deny access
