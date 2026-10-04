# Delta for document-review

## MODIFIED Requirements

### Requirement: Eligible review queue

MUST queue only sheet-member vouchers with `state` `validated_seller` and designated
proof (`message_main_attachment_id`). Ineligible or other-sheet vouchers MUST NOT
appear. Parent `state == new` MUST NOT be eligibility. Confidence, per-field stamps, and
reviewer-note persistence MUST NOT be required. Empty sheet queue MUST show
no-remaining-work and MUST NOT fall back to another sheet or company-wide queue.
(Previously: Queue required `state` `pending`.)

#### Scenario: Queue eligibility

- GIVEN a saved sheet with `validated_seller` members that have proof plus ineligible
  members
- WHEN Document Review opens for that sheet
- THEN only that sheet's eligible members MUST appear

#### Scenario: Empty queue

- GIVEN a saved sheet with no eligible members and other sheets with eligible
  `validated_seller` proofs
- WHEN Document Review opens for that sheet
- THEN MUST show empty/no-remaining-work and MUST NOT show other-sheet vouchers

#### Scenario: Cross-sheet isolation

- GIVEN two saved sheets each with eligible `validated_seller` proofs
- WHEN Review opens for sheet A, or approve/rotation of a sheet B voucher uses A's
  identifier
- THEN only A's members MUST appear, B MUST NOT appear, and the cross-sheet mutation
  MUST be refused

### Requirement: OWL client loads real ORM data

The Document Review OWL client MUST load queue and voucher data via ORM (no mocks) from
`collection.voucher`. MUST support typed editable inputs, queue navigation, and advance
to the next eligible record after a successful approve. Reject MUST NOT exist.
(Previously: Advance after approve or reject.)

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
- THEN voucher reference and queue position MUST be readonly and `document_id` MUST NOT
  be shown

#### Scenario: Navigate and next record after decision

- GIVEN more than one eligible queued voucher
- WHEN the reviewer navigates or successfully approves the current voucher
- THEN the client MUST move to the requested or next eligible record without mocks

### Requirement: Approve and reject without mocks

Approve MUST call a real server action (no mocks). Approve MUST persist field
corrections then set voucher `state` to `validated_collections`. Reject MUST NOT exist
(`action_review_reject` and OWL reject MUST be removed). (Previously: Approve set
`approved`; reject set `rejected`.)

#### Scenario: Correction persistence on approve

- GIVEN an eligible `validated_seller` voucher with edited payment fields
- WHEN the reviewer approves
- THEN corrections MUST persist and `state` MUST be `validated_collections`

#### Scenario: Reject invokes real action

- GIVEN an eligible `validated_seller` voucher
- WHEN reject is invoked
- THEN Reject MUST NOT exist and `state` MUST stay `validated_seller`

### Requirement: Document Review authorization

Only internal users (`base.group_user`) MUST access Document Review queue and approve
actions.

#### Scenario: Non-internal user denied Document Review

- GIVEN a user without internal-user privileges
- WHEN they attempt Document Review queue access or approve
- THEN the system MUST deny access

### Requirement: Per-company Document Review flag

Each company MUST have a boolean Document Review flag defaulting to OFF. Settings admins
MUST toggle it at `/odoo/settings#collections` under Collection Settings. When ON,
existing Document Review requirements MUST still apply. Voucher `state` and review audit
columns MUST remain on Payment Vouchers views regardless of the flag. Saving other
Collection Settings MUST preserve this flag. The flag MUST still gate review queue and
mutation operations as today, except Reject MUST NOT exist. (Previously: Gated
operations included `action_review_reject`.)

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
- WHEN an internal user calls `get_review_queue`, `action_review_approve`, or
  `action_review_set_rotation`
- THEN MUST refuse (not empty-queue success)
- AND when ON those operations MUST still run for internal users on an allowed-company
  sheet

### Requirement: Document Review menu and RPCs when flag is off

The Collections menu MUST NOT include Document Review, whether the flag is ON or OFF.
When OFF, `get_review_queue`, `action_review_approve`, and `action_review_set_rotation`
MUST refuse, including leftover `/odoo/document-review`, with or without a sheet
identifier, and MUST NOT succeed as an empty queue. When ON, only internal users MUST
access them. `action_review_reject` MUST NOT remain. (Previously: Gated operations
included `action_review_reject`.)

#### Scenario: Menu absence

- GIVEN the module installed and Document Review ON or OFF
- WHEN menus load
- THEN Collections → Document Review MUST NOT appear

#### Scenario: Review operations refuse when off

- GIVEN Document Review is OFF
- WHEN an internal user calls `get_review_queue`, `action_review_approve`, or
  `action_review_set_rotation`, with or without a sheet identifier, including via
  leftover `/odoo/document-review`
- THEN the system MUST refuse (not empty-queue success)

#### Scenario: Internal ACL when on

- GIVEN Document Review is ON
- WHEN a non-internal user attempts those review operations
- THEN the system MUST deny access

### Requirement: Sheet identifier required on review operations

`get_review_queue`, `action_review_approve`, and `action_review_set_rotation` MUST
require a validated sheet identifier and MUST operate only on that sheet. Direct or
global review MUST NOT succeed. Missing or invalid identifiers MUST be refused (not
empty-queue success). Mutations MUST refuse non-members of that sheet. OWL MUST pass the
identifier on queue, approve, and rotation. Reject MUST NOT be an operation.
(Previously: Operations included `action_review_reject`.)

#### Scenario: Required sheet context

- GIVEN Document Review is ON
- WHEN a review queue or mutation runs with a missing or invalid sheet identifier
- THEN MUST refuse and MUST NOT succeed as an empty queue

#### Scenario: Stale membership

- GIVEN Document Review ON and a voucher that is no longer a member of the identified
  sheet
- WHEN approve or rotation runs with that sheet identifier
- THEN the mutation MUST be refused

#### Scenario: OWL and RPC arguments include the sheet identifier

- GIVEN Document Review opened from a saved sheet
- WHEN the client loads the queue or performs approve or rotation
- THEN each corresponding RPC MUST include that sheet's identifier

### Requirement: Three-way raw, seller, and current comparison

Payment Vouchers form and Document Review MUST present raw OCR, seller-confirmed, and
current payment fields side by side. Current MUST remain the editable copy. Raw and
seller-confirmed MUST be readonly. Type-specific visibility MUST apply to all three
layers. Document Review MUST NOT show `document_id`. Empty provenance MUST still load.
(Previously: Approve scenario used an eligible pending voucher.)

#### Scenario: Type-specific visibility and hidden document_id

- GIVEN a queued `bank_transfer`, `check`, or `cash_deposit` voucher
- WHEN shown in Document Review or on the voucher form
- THEN type-specific fields MUST follow existing visibility on all three layers and
  Document Review MUST NOT show `document_id`

#### Scenario: Reviewer correction diverges current only

- GIVEN an eligible `validated_seller` voucher with stored raw and seller-confirmed
  copies
- WHEN the reviewer edits current fields and Document Review approve completes
- THEN current MUST persist the correction, raw and seller-confirmed MUST stay
  unchanged, and the snapshot MUST match current with `decision` `approved`

### Requirement: Document Review decisions append immutable snapshots

Document Review approve MUST append a snapshot of typed current payment fields even when
unchanged. Each snapshot MUST record revision, reviewer, time, and `decision`. New
Approve snapshots MUST store `decision="approved"` while voucher `state` becomes
`validated_collections`. Snapshot `decision` Selection MUST stay `approved`\|`rejected`.
Historical `rejected` rows MAY remain. Document Review reject MUST NOT exist and MUST
NOT append. Form Validate by Seller MUST NOT satisfy this requirement. (Previously:
Reject also appended; voucher `state` and snapshot `decision` used the same string.)

#### Scenario: Unchanged Document Review approval still snapshots

- GIVEN an eligible `validated_seller` voucher with unchanged current fields
- WHEN the reviewer approves in Document Review
- THEN a snapshot MUST be appended with `decision` `approved`, matching current fields,
  and voucher `state` MUST be `validated_collections`

#### Scenario: Document Review reject also snapshots

- GIVEN an eligible `validated_seller` voucher
- WHEN reject is invoked in Document Review
- THEN Reject MUST NOT exist and no new snapshot MUST be appended

### Requirement: Repeated Document Review appends another revision

After a decided voucher is reopened to `validated_seller`, a later Document Review
approve MUST append a new snapshot. Earlier snapshots MUST remain unchanged.
(Previously: Reopen to `pending`; approve or reject.)

#### Scenario: Reopen then re-review appends another revision

- GIVEN a voucher with an existing snapshot that is `validated_seller` again after
  reopen
- WHEN Document Review approve runs
- THEN a new snapshot revision MUST be appended with `decision` `approved` and earlier
  snapshots MUST stay unchanged

### Requirement: Review snapshots isolated by company

Each Document Review snapshot MUST belong to the same company as its voucher. Users MUST
see snapshots only for companies they are allowed. Dedicated groups MUST NOT be added.
Write and unlink MUST remain denied. Snapshots MUST remain in the database after the
form History tab is removed. (Previously: Allowed-company history was listed on Payment
Vouchers History.)

#### Scenario: Snapshot follows voucher company

- GIVEN a voucher in company A with a snapshot
- WHEN the snapshot is read
- THEN it MUST belong to company A

#### Scenario: Other-company snapshots hidden

- GIVEN a snapshot of a company B voucher and a user not allowed company B
- WHEN they read snapshots
- THEN that snapshot MUST NOT be visible and its id MUST NOT be disclosed

#### Scenario: Allowed-company history still readable

- GIVEN an internal user allowed company A and snapshots on an A voucher
- WHEN they read snapshots via ACL
- THEN those snapshots MUST be readable and MUST NOT require a Payment Vouchers History
  tab

## REMOVED Requirements

### Requirement: Voucher review history is visible

(Reason: History notebook page is dropped so operators are not shown snapshot rows on
the voucher form.) (Migration: Snapshot rows stay in the database with `decision`
`approved`\|`rejected`; ACL read remains; form MUST NOT bind `review_snapshot_ids`.)
