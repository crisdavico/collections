# Delta for Document Review

## MODIFIED Requirements

### Requirement: Eligible review queue

The system MUST queue only `collection.voucher` records where `state` is `pending` and
an attachment is present. Vouchers missing any eligibility criterion MUST NOT appear.
Parent-voucher `state == new` MUST NOT be an eligibility criterion. Confidence scores,
per-field stamps, and reviewer-note persistence MUST NOT be required. (Previously:
Queued `collection.voucher.line` records whose parent voucher `state` was `new`, line
`state` was `pending`, and an attachment was present.)

#### Scenario: Queue eligibility

- GIVEN pending vouchers with attachment, plus ineligible vouchers (non-pending or no
  attachment)
- WHEN an internal user opens Document Review
- THEN only eligible vouchers MUST appear in the queue

#### Scenario: Empty queue

- GIVEN no eligible pending attached vouchers
- WHEN Document Review opens
- THEN the client MUST show an empty/no-remaining-work state

### Requirement: OWL client loads real ORM data

The Document Review OWL client MUST load queue and voucher data via ORM (no mocks) from
`collection.voucher`. It MUST support typed editable inputs, queue navigation, and
advance to the next eligible record after a successful approve or reject. (Previously:
Loaded `collection.voucher.line`; readonly voucher reference was the parent header
name.)

#### Scenario: Typed editable fields by document type

- GIVEN a queued `bank_transfer`, `check`, or `cash_deposit` voucher
- WHEN shown in Document Review
- THEN `document_type` and `amount` MUST be editable
- AND type-specific fields MUST be editable: bank transfer (`from_account`,
  `to_account`, `voucher_number`, `voucher_date`); check (`check_number`, `check_bank`,
  `check_type`, `check_issue_date`, `check_payment_date`); cash deposit
  (amount/`document_type` only beyond shared)

#### Scenario: Readonly context fields

- GIVEN a queued voucher
- WHEN shown in Document Review
- THEN voucher reference and queue position MUST be readonly
- AND `document_id` MUST NOT be shown

#### Scenario: Navigate and next record after decision

- GIVEN more than one eligible queued voucher
- WHEN the reviewer navigates or successfully approves/rejects the current voucher
- THEN the client MUST move to the requested or next eligible record without mocks

### Requirement: Authenticated binary attachment viewer

The client MUST render image and PDF proofs via an authenticated binary route whose
model is `collection.voucher`. The OWL layer MUST NOT embed attachment base64. The
viewer MUST present distinct loading, error, and empty-attachment states. (Previously:
Binary URLs used model `collection.voucher.line`.)

#### Scenario: Image via authenticated binary route

- GIVEN an eligible voucher with an image attachment
- WHEN Document Review shows the proof
- THEN the image MUST load from an authenticated binary URL for `collection.voucher`
- AND OWL MUST NOT hold the attachment as base64

#### Scenario: PDF via authenticated binary route

- GIVEN an eligible voucher with a PDF attachment
- WHEN Document Review shows the proof
- THEN the PDF MUST load from an authenticated binary URL for `collection.voucher`
- AND OWL MUST NOT hold the attachment as base64

#### Scenario: Viewer loading, error, and empty states

- GIVEN a voucher whose attachment is loading, fails to load, or is absent/empty
- WHEN the viewer renders
- THEN it MUST show the matching loading, error, or empty state

### Requirement: Viewer rotation

The viewer MUST offer controls that rotate the current image or PDF 90 degrees clockwise
and counterclockwise. Rotation MUST be a view transform: it MUST NOT rewrite the stored
attachment bytes. The chosen angle MUST persist on the voucher and MUST be restored when
the reviewer views that same proof again (including after queue navigation or reopening
Document Review). PDF proofs MUST still load from the authenticated binary URL.
Replacing or clearing the attachment MUST reset rotation to 0 degrees. (Previously:
Rotation persisted on the payment line.)

#### Scenario: Rotate clockwise and counterclockwise

- GIVEN a ready image or PDF proof in Document Review
- WHEN the reviewer activates rotate-right or rotate-left
- THEN the proof MUST rotate 90 degrees in that direction
- AND the stored attachment bytes MUST remain unchanged
- AND the new angle MUST be saved on the voucher

#### Scenario: Restore saved rotation

- GIVEN a proof whose rotation was previously saved
- WHEN the reviewer views that proof again
- THEN the viewer MUST show it at the saved angle

#### Scenario: Attachment replace resets rotation

- GIVEN a voucher with a saved non-zero rotation
- WHEN its attachment is replaced or cleared
- THEN rotation MUST reset to 0 degrees

### Requirement: Approve and reject without mocks

Approve and reject MUST call real server actions (no mock handlers). Approve MUST
persist field corrections before updating voucher `state`. Reject and approve outcomes
for voucher `state` are governed by `collection-vouchers`. (Previously: Corrections and
`state` were persisted on the payment line; aggregate header state was also implied.)

#### Scenario: Correction persistence on approve

- GIVEN an eligible pending voucher with edited payment fields
- WHEN the reviewer approves
- THEN corrected field values MUST persist on the voucher
- AND voucher `state` MUST become `approved`

#### Scenario: Reject invokes real action

- GIVEN an eligible pending voucher
- WHEN the reviewer rejects
- THEN the server reject action MUST run (no mock)
- AND the voucher `state` MUST become `rejected`

### Requirement: Per-company Document Review flag

Each company MUST have a boolean Document Review flag defaulting to OFF. Settings admins
MUST toggle it at `/odoo/settings#collections`. When ON, existing Document Review
requirements MUST still apply. Voucher `state` and review audit columns MUST remain on
Payment Vouchers views regardless of the flag. (Previously: Line `state` and review
audit columns remained on payment-line views.)

#### Scenario: Default off

- GIVEN a fresh install or upgrade
- WHEN the current company's flag is read
- THEN Document Review MUST be OFF

#### Scenario: Settings admin toggle

- GIVEN a Settings administrator
- WHEN they change Document Review at `/odoo/settings#collections`
- THEN the current company's flag MUST persist that value

#### Scenario: Voucher state and audit remain

- GIVEN Document Review is OFF
- WHEN an internal user opens Payment Vouchers views
- THEN voucher `state` and review audit columns MUST still appear
