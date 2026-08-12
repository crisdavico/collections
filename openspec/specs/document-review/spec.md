# Document Review Specification

## Purpose

Internal-user Document Review client: queue eligible payment-line proofs, correct OCR’d
fields against the attachment, and approve/reject without mock data.

## Requirements

### Requirement: Eligible review queue

The system MUST queue only `collection.voucher.line` records where the parent voucher
`state` is `new`, the line `state` is `pending`, and an attachment is present. Lines
missing any eligibility criterion MUST NOT appear. Confidence scores, per-field stamps,
and reviewer-note persistence MUST NOT be required.

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
- THEN voucher reference and queue position MUST be readonly
- AND `document_id` MUST NOT be shown

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

### Requirement: Viewer fit and cursor-anchored zoom

The viewer MUST offer a control that expands the current image or PDF to the tray size
while preserving aspect ratio, and MUST support cursor-anchored wheel zoom while the
pointer hovers the tray. While the proof is zoomed, left-button drag MUST pan the image
or PDF with the pointer. PDF proofs MUST still load from the authenticated binary URL.
Fit, zoom, and pan MUST reset when the reviewer navigates to another document.

#### Scenario: Fit to pane

- GIVEN a ready image or PDF proof in Document Review
- WHEN the reviewer activates the fit control
- THEN the proof MUST expand to fill the viewer tray without cropping
- AND any wheel zoom MUST reset

#### Scenario: Wheel zoom on hover

- GIVEN a ready image or PDF proof
- WHEN the reviewer hovers the tray and scrolls the mouse wheel
- THEN the proof MUST zoom in or out around the cursor
- AND the page MUST NOT scroll

#### Scenario: Drag pan while zoomed

- GIVEN a ready image or PDF proof that has been zoomed
- WHEN the reviewer left-clicks the tray and moves the pointer
- THEN the proof MUST pan with the pointer
- AND the PDF iframe MUST NOT capture the drag (hitbox stays on top)

#### Scenario: Fit and zoom reset on navigation

- GIVEN a proof that has been fitted, zoomed, or panned
- WHEN the reviewer moves to another queued document
- THEN fit, zoom, and pan MUST return to the default for that document

### Requirement: Viewer rotation

The viewer MUST offer controls that rotate the current image or PDF 90 degrees clockwise
and counterclockwise. Rotation MUST be a view transform: it MUST NOT rewrite the stored
attachment bytes. The chosen angle MUST persist on the payment line and MUST be restored
when the reviewer views that same proof again (including after queue navigation or
reopening Document Review). PDF proofs MUST still load from the authenticated binary
URL. Replacing or clearing the attachment MUST reset rotation to 0 degrees.

#### Scenario: Rotate clockwise and counterclockwise

- GIVEN a ready image or PDF proof in Document Review
- WHEN the reviewer activates rotate-right or rotate-left
- THEN the proof MUST rotate 90 degrees in that direction
- AND the stored attachment bytes MUST remain unchanged
- AND the new angle MUST be saved on the payment line

#### Scenario: Restore saved rotation

- GIVEN a proof whose rotation was previously saved
- WHEN the reviewer views that proof again
- THEN the viewer MUST show it at the saved angle

#### Scenario: Attachment replace resets rotation

- GIVEN a line with a saved non-zero rotation
- WHEN its attachment is replaced or cleared
- THEN rotation MUST reset to 0 degrees

### Requirement: Approve and reject without mocks

Approve and reject MUST call real server actions (no mock handlers). Approve MUST
persist field corrections before updating line `state`. Reject and approve outcomes for
voucher aggregate state are governed by `collection-vouchers`.

#### Scenario: Correction persistence on approve

- GIVEN an eligible pending line with edited payment fields
- WHEN the reviewer approves
- THEN corrected field values MUST persist on the line
- AND line `state` MUST become `approved`

#### Scenario: Reject invokes real action

- GIVEN an eligible pending line
- WHEN the reviewer rejects
- THEN the server reject action MUST run (no mock)
- AND the line `state` MUST become `rejected`

### Requirement: Document Review authorization

Only internal users (`base.group_user`) MUST access Document Review queue and
approve/reject actions.

#### Scenario: Non-internal user denied Document Review

- GIVEN a user without internal-user privileges
- WHEN they attempt Document Review queue access or approve/reject
- THEN the system MUST deny access

### Requirement: Per-company Document Review flag

Each company MUST have a boolean Document Review flag defaulting to OFF. Settings
admins MUST toggle it at `/odoo/settings#collections`. When ON, existing Document
Review requirements MUST still apply. Line `state` and review audit columns MUST
remain on payment-line views regardless of the flag.

#### Scenario: Default off

- GIVEN a fresh install or upgrade
- WHEN the current company's flag is read
- THEN Document Review MUST be OFF

#### Scenario: Settings admin toggle

- GIVEN a Settings administrator
- WHEN they change Document Review at `/odoo/settings#collections`
- THEN the current company's flag MUST persist that value

#### Scenario: Line state and audit remain

- GIVEN Document Review is OFF
- WHEN an internal user opens payment-line views
- THEN line `state` and review audit columns MUST still appear

### Requirement: Document Review menu and RPCs when flag is off

When OFF, the Document Review menu MUST NOT appear. Operations `get_review_queue`,
`action_review_approve`, `action_review_reject`, and `action_review_set_rotation`
MUST refuse, including for internal users, and MUST NOT succeed as an empty queue.
Direct `/odoo/document-review` MUST still be refused via those operations. When ON,
only internal users MUST access them.

#### Scenario: Menu hidden when off

- GIVEN Document Review is OFF
- WHEN menus load
- THEN Document Review MUST NOT appear

#### Scenario: Review operations refuse when off

- GIVEN Document Review is OFF
- WHEN an internal user calls `get_review_queue`, `action_review_approve`,
  `action_review_reject`, or `action_review_set_rotation`, including via
  `/odoo/document-review`
- THEN the system MUST refuse (not empty-queue success)

#### Scenario: Internal ACL when on

- GIVEN Document Review is ON
- WHEN a non-internal user attempts those review operations
- THEN the system MUST deny access
