# Document Review Specification

## Purpose

Internal-user Document Review client: queue eligible voucher proofs, correct OCR’d
fields against the attachment, and approve/reject without mock data.

## Requirements

### Requirement: Eligible review queue

The system MUST queue only `collection.voucher` records that are members of the review
session's saved collection sheet, where `state` is `pending` and designated proof
(`message_main_attachment_id`) is present. Vouchers missing any eligibility criterion
MUST NOT appear. Vouchers that are not members of that sheet MUST NOT appear.
Parent-voucher `state == new` MUST NOT be an eligibility criterion. Confidence scores,
per-field stamps, and reviewer-note persistence MUST NOT be required. When the
identified sheet has no eligible members, the client MUST show an empty/no-remaining-work
state and MUST NOT fall back to a company-wide or other-sheet queue.
(Previously: Eligibility used Binary `attachment != False`, not designated proof.)

#### Scenario: Queue eligibility

- GIVEN a saved sheet with pending members that have designated proof plus ineligible
  members (non-pending or no designated proof)
- WHEN an internal user opens Document Review for that sheet
- THEN only that sheet's eligible members MUST appear in the queue

#### Scenario: Empty queue

- GIVEN a saved sheet with no eligible members, and other sheets that have eligible
  pending vouchers with designated proof
- WHEN Document Review opens for that sheet
- THEN the client MUST show an empty/no-remaining-work state
- AND MUST NOT show vouchers from other sheets

#### Scenario: Cross-sheet isolation

- GIVEN two saved sheets that each have eligible pending vouchers with designated proof
- WHEN an internal user opens Document Review for sheet A, or attempts approve, reject,
  or rotation of a sheet B voucher using sheet A's identifier
- THEN only sheet A's eligible members MUST appear
- AND sheet B's vouchers MUST NOT appear
- AND the cross-sheet mutation MUST be refused

### Requirement: OWL client loads real ORM data

The Document Review OWL client MUST load queue and voucher data via ORM (no mocks) from
`collection.voucher`. It MUST support typed editable inputs, queue navigation, and
advance to the next eligible record after a successful approve or reject.
(Previously: Loaded `collection.voucher.line`; readonly voucher reference was the parent
header name.)

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

The client MUST render image and PDF proofs via authenticated `/web/content/{id}` for
the designated proof `ir.attachment`. The route MUST NOT use `field=attachment`. The OWL
layer MUST NOT embed attachment base64. The viewer MUST present distinct loading, error,
and empty-proof states.
(Previously: Binary URLs used `model=collection.voucher` with `field=attachment`.)

#### Scenario: Image via authenticated binary route

- GIVEN an eligible voucher with an image designated proof
- WHEN Document Review shows the proof
- THEN the image MUST load from `/web/content/{id}` of that designated proof
- AND OWL MUST NOT hold the attachment as base64

#### Scenario: PDF via authenticated binary route

- GIVEN an eligible voucher with a PDF designated proof
- WHEN Document Review shows the proof
- THEN the PDF MUST load from `/web/content/{id}` of that designated proof
- AND OWL MUST NOT hold the attachment as base64

#### Scenario: Viewer loading, error, and empty states

- GIVEN a voucher whose designated proof is loading, fails to load, or is absent/empty
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
attachment bytes. The chosen angle MUST persist on the voucher and MUST be restored when
the reviewer views that same proof again (including after queue navigation or reopening
Document Review). PDF proofs MUST still load from the authenticated binary URL. Changing
or clearing `message_main_attachment_id` MUST reset rotation to 0 degrees. Extra chatter
files that do not change designated proof MUST NOT reset rotation.
(Previously: Rotation reset on Binary attachment replace or clear.)

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
- WHEN `message_main_attachment_id` is changed or cleared
- THEN rotation MUST reset to 0 degrees

#### Scenario: Extra chatter files do not reset rotation

- GIVEN a voucher with a saved non-zero rotation and designated proof
- WHEN an extra chatter file is added without changing `message_main_attachment_id`
- THEN rotation MUST remain the saved angle

### Requirement: Approve and reject without mocks

Approve and reject MUST call real server actions (no mock handlers). Approve MUST
persist field corrections before updating voucher `state`. Reject and approve outcomes
for voucher `state` are governed by `collection-vouchers`.
(Previously: Corrections and `state` were persisted on the payment line; aggregate
header state was also implied.)

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
Review requirements MUST still apply. Voucher `state` and review audit columns MUST
remain on Payment Vouchers views regardless of the flag.
(Previously: Line `state` and review audit columns remained on payment-line views.)

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
