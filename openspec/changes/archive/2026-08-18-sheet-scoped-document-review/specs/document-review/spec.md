# Delta for Document Review

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Eligible review queue

The system MUST queue only `collection.voucher` records that are members of the review
session's saved collection sheet, where `state` is `pending` and an attachment is
present. Vouchers missing any eligibility criterion MUST NOT appear. Vouchers that are
not members of that sheet MUST NOT appear. Parent-voucher `state == new` MUST NOT be an
eligibility criterion. Confidence scores, per-field stamps, and reviewer-note
persistence MUST NOT be required. When the identified sheet has no eligible members, the
client MUST show an empty/no-remaining-work state and MUST NOT fall back to a
company-wide or other-sheet queue. (Previously: Queued every company eligible pending
attached voucher without requiring sheet membership.)

#### Scenario: Queue eligibility

- GIVEN a saved sheet with pending attached members plus ineligible members (non-pending
  or no attachment)
- WHEN an internal user opens Document Review for that sheet
- THEN only that sheet's eligible members MUST appear in the queue

#### Scenario: Empty queue

- GIVEN a saved sheet with no eligible members, and other sheets that have eligible
  pending attached vouchers
- WHEN Document Review opens for that sheet
- THEN the client MUST show an empty/no-remaining-work state
- AND MUST NOT show vouchers from other sheets

#### Scenario: Cross-sheet isolation

- GIVEN two saved sheets that each have eligible pending attached vouchers
- WHEN an internal user opens Document Review for sheet A, or attempts approve, reject,
  or rotation of a sheet B voucher using sheet A's identifier
- THEN only sheet A's eligible members MUST appear
- AND sheet B's vouchers MUST NOT appear
- AND the cross-sheet mutation MUST be refused

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
