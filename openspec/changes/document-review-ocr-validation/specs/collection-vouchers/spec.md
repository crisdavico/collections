# Delta for collection-vouchers

## ADDED Requirements

### Requirement: Payment line review status and audit

Each `collection.voucher.line` MUST track review status `pending` | `approved` |
`rejected`, defaulting to `pending` (including on additive upgrade for existing lines).
When review status leaves `pending`, the system MUST record reviewer and review time
audit fields. Confidence, per-field stamps, and reviewer-note persistence MUST NOT be
required.

#### Scenario: Default pending including upgrade

- GIVEN a newly created line or an existing line after additive upgrade
- WHEN review status is read without a prior decision
- THEN status MUST be `pending`

#### Scenario: Audit on decision

- GIVEN a pending line
- WHEN approved or rejected
- THEN reviewer and review time MUST be recorded

### Requirement: Approve may validate voucher when all attached lines approved

When a line is approved, if the parent voucher is `new` and every attachment-bearing
line on that voucher is `approved`, the system MAY transition the voucher to
`validated`. Lines without attachments MUST NOT block that aggregate approval path.

#### Scenario: Aggregate voucher validation

- GIVEN a `new` voucher whose every attachment-bearing line becomes `approved`
- WHEN the last such line is approved
- THEN the voucher `state` MUST become `validated`

### Requirement: Line reject immediately rejects voucher

Rejecting a payment line MUST set that line to `rejected` and, when the parent voucher
is `new`, MUST immediately set the voucher to `rejected`.

#### Scenario: Immediate voucher rejection on line reject

- GIVEN a `new` voucher with a pending attached line
- WHEN that line is rejected
- THEN the line MUST be `rejected` and the voucher MUST become `rejected`

### Requirement: Concurrent and stale review attempts

Approve and reject MUST refuse stale or concurrent attempts when the line is no longer
eligible (not `pending`, voucher not `new`, or attachment no longer present) and MUST
NOT corrupt review or voucher state.

#### Scenario: Concurrent or stale review attempt

- GIVEN a line already decided or otherwise ineligible for review
- WHEN approve or reject is attempted again
- THEN the system MUST refuse the action and MUST NOT alter terminal or decided state

### Requirement: Attachment replacement resets review to pending

Replacing a payment-line attachment (write of new Binary content) MUST reset that
line’s review status to `pending` and MUST clear prior reviewer/time audit for a fresh
review. Omit/empty and MIME validation rules remain unchanged.

#### Scenario: Attachment replacement resets review status

- GIVEN a line previously `approved` or `rejected` with an attachment
- WHEN a new valid attachment replaces the prior file
- THEN review status MUST become `pending`
- AND prior reviewer/time audit MUST be cleared for re-review

## MODIFIED Requirements

### Requirement: Voucher state transitions

States MUST be `new`, `validated`, and `rejected`. Validate and Reject MUST apply only
from `new` and MUST NOT alter terminal states. `action_validate()` MUST refuse while any
attachment-bearing payment line on the voucher still has review status `pending`.
(Previously: Validate from `new` had no attachment-line review gate.)

#### Scenario: Validate from new

- GIVEN a voucher in `new` with no attachment-bearing lines still `pending`
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

#### Scenario: Validate blocked while attached lines pending

- GIVEN a voucher in `new` with at least one attachment-bearing line still `pending`
- WHEN `action_validate()` is invoked
- THEN validation MUST be refused and `state` MUST remain `new`
