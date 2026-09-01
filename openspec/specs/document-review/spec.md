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
identified sheet has no eligible members, the client MUST show an
empty/no-remaining-work state and MUST NOT fall back to a company-wide or other-sheet
queue. (Previously: Eligibility used Binary `attachment != False`, not designated
proof.)

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

The client MUST render image and PDF proofs via authenticated `/web/content/{id}` for
the designated proof `ir.attachment`. The route MUST NOT use `field=attachment`. The OWL
layer MUST NOT embed attachment base64. The viewer MUST present distinct loading, error,
and empty-proof states. (Previously: Binary URLs used `model=collection.voucher` with
`field=attachment`.)

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
files that do not change designated proof MUST NOT reset rotation. (Previously: Rotation
reset on Binary attachment replace or clear.)

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

### Requirement: Document Review authorization

Only internal users (`base.group_user`) MUST access Document Review queue and
approve/reject actions.

#### Scenario: Non-internal user denied Document Review

- GIVEN a user without internal-user privileges
- WHEN they attempt Document Review queue access or approve/reject
- THEN the system MUST deny access

### Requirement: Per-company Document Review flag

Each company MUST have a boolean Document Review flag defaulting to OFF. Settings admins
MUST toggle it at `/odoo/settings#collections` under Collection Settings. When ON,
existing Document Review requirements MUST still apply. Voucher `state` and review audit
columns MUST remain on Payment Vouchers views regardless of the flag. Saving other
Collection Settings MUST preserve this flag. The flag MUST still gate review queue and
mutation operations as today. (Previously: Settings labels were "Settings"; other
Collection Settings fields did not exist.)

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

#### Scenario: Flag preserved when Collection Settings are saved

- GIVEN Document Review ON or OFF and other Collection Settings edited
- WHEN Collection Settings are saved
- THEN `document_review_enabled` MUST remain the prior value unless the admin changed
  that flag in the same save

#### Scenario: Flag still gates review when ON or OFF

- GIVEN Document Review OFF
- WHEN an internal user calls `get_review_queue`, `action_review_approve`,
  `action_review_reject`, or `action_review_set_rotation`
- THEN the system MUST refuse (not empty-queue success)
- AND when the flag is ON those operations MUST still run for internal users on an
  allowed-company sheet

### Requirement: Document Review menu and RPCs when flag is off

The Collections menu MUST NOT include Document Review, whether the current company's
flag is ON or OFF. When OFF, operations `get_review_queue`, `action_review_approve`,
`action_review_reject`, and `action_review_set_rotation` MUST refuse, including for
internal users and including leftover `/odoo/document-review`, with or without a sheet
identifier, and MUST NOT succeed as an empty queue. When ON, only internal users MUST
access them. (Previously: When OFF the Document Review menu was hidden; when ON,
Collections → Document Review was available as a standalone menu.)

#### Scenario: Menu absence

- GIVEN the module installed and Document Review ON or OFF
- WHEN menus load
- THEN Collections → Document Review MUST NOT appear

#### Scenario: Review operations refuse when off

- GIVEN Document Review is OFF
- WHEN an internal user calls `get_review_queue`, `action_review_approve`,
  `action_review_reject`, or `action_review_set_rotation`, with or without a sheet
  identifier, including via leftover `/odoo/document-review`
- THEN the system MUST refuse (not empty-queue success)

#### Scenario: Internal ACL when on

- GIVEN Document Review is ON
- WHEN a non-internal user attempts those review operations
- THEN the system MUST deny access

### Requirement: Sheet identifier required on review operations

Queue and mutation operations `get_review_queue`, `action_review_approve`,
`action_review_reject`, and `action_review_set_rotation` MUST require a validated sheet
identifier and MUST operate only on that sheet (`sheet_id`). Direct or global review
MUST NOT succeed. Missing or invalid identifiers MUST be refused (not empty-queue
success). Mutations MUST refuse vouchers that are not current members of that sheet. OWL
MUST pass the identifier on queue, approve, reject, and rotation.

#### Scenario: Required sheet context

- GIVEN Document Review is ON
- WHEN an internal user calls a review queue or mutation operation with a missing or
  invalid sheet identifier
- THEN the system MUST refuse
- AND MUST NOT succeed as an empty queue

#### Scenario: Stale membership

- GIVEN Document Review is ON and a voucher that is no longer a member of the identified
  saved sheet
- WHEN an internal user attempts approve, reject, or rotation for that voucher with that
  sheet identifier
- THEN the system MUST refuse the mutation

#### Scenario: OWL and RPC arguments include the sheet identifier

- GIVEN Document Review opened from a saved sheet
- WHEN the client loads the queue or performs approve, reject, or rotation
- THEN each corresponding RPC MUST include that sheet's identifier

### Requirement: Three-way raw, seller, and current comparison

Payment Vouchers form and Document Review MUST present raw OCR, seller-confirmed, and
current payment fields side by side. Current MUST remain the editable copy. Raw and
seller-confirmed MUST be readonly. Type-specific visibility MUST apply to all three
layers. Document Review MUST NOT show `document_id`. Empty provenance MUST still load.

#### Scenario: Type-specific visibility and hidden document_id

- GIVEN a queued `bank_transfer`, `check`, or `cash_deposit` voucher
- WHEN shown in Document Review or on the voucher form
- THEN type-specific fields MUST follow existing visibility on all three layers
- AND Document Review MUST NOT show `document_id`

#### Scenario: Reviewer correction diverges current only

- GIVEN an eligible pending voucher with stored raw and seller-confirmed copies
- WHEN the reviewer edits current fields and Document Review approve completes
- THEN current MUST persist the correction
- AND raw and seller-confirmed MUST remain unchanged
- AND the appended snapshot MUST match current

### Requirement: Queue payload includes readonly provenance

The Document Review queue MUST include readonly raw and seller-confirmed payment fields
for each eligible voucher. Missing provenance MUST be represented as empty, not
fabricated.

#### Scenario: Queue exposes provenance without fabricating

- GIVEN eligible vouchers with and without stored provenance
- WHEN the queue loads
- THEN each item MUST include readonly raw and seller-confirmed copies
- AND empty provenance MUST remain empty

### Requirement: Document Review decisions append immutable snapshots

Document Review approve MUST append a snapshot of the typed current payment fields even
when those fields are unchanged. Document Review reject MUST also append a snapshot.
Each snapshot MUST record revision, reviewer, time, and decision. Form Approve and
Reject MUST NOT satisfy this requirement.

#### Scenario: Unchanged Document Review approval still snapshots

- GIVEN an eligible pending voucher with unchanged current fields
- WHEN the reviewer approves in Document Review
- THEN a snapshot MUST be appended
- AND it MUST match the current payment fields

#### Scenario: Document Review reject also snapshots

- GIVEN an eligible pending voucher
- WHEN the reviewer rejects in Document Review
- THEN a snapshot MUST be appended
- AND voucher state MUST become `rejected`

### Requirement: Repeated Document Review appends another revision

After a decided voucher is reopened to `pending`, a later Document Review approve or
reject MUST append a new snapshot. Earlier snapshots MUST remain unchanged.

#### Scenario: Reopen then re-review appends another revision

- GIVEN a voucher with an existing snapshot that is `pending` again after reopen
- WHEN Document Review approve or reject runs
- THEN a new snapshot revision MUST be appended
- AND earlier snapshots MUST remain unchanged

### Requirement: Voucher review history is visible

Payment Vouchers form MUST show the voucher's Document Review snapshot history in
revision order. History rows MUST be readonly.

#### Scenario: History list on the voucher form

- GIVEN a voucher with one or more snapshots
- WHEN an internal user opens the Payment Vouchers form
- THEN the history MUST list those snapshots in revision order
- AND the rows MUST be readonly

### Requirement: Review snapshots isolated by company

Each Document Review snapshot MUST belong to the same company as its voucher. Users MUST
see snapshots only for companies they are allowed, the same as vouchers. Dedicated
groups MUST NOT be added. Write and unlink of snapshots MUST remain denied.

#### Scenario: Snapshot follows voucher company

- GIVEN a voucher in company A with a snapshot
- WHEN the snapshot is read
- THEN it MUST belong to company A

#### Scenario: Other-company snapshots hidden

- GIVEN a snapshot of a company B voucher and a user not allowed company B
- WHEN they read review history
- THEN that snapshot MUST NOT be visible
- AND its id MUST NOT be disclosed

#### Scenario: Allowed-company history still readable

- GIVEN an internal user allowed company A and snapshots on an A voucher
- WHEN they open Payment Vouchers history
- THEN those snapshots MUST be listed readonly in revision order
