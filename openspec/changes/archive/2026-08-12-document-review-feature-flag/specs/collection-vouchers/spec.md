# Delta for collection-vouchers

## MODIFIED Requirements

### Requirement: Voucher state transitions

States MUST be `new`, `validated`, and `rejected`. Validate and Reject MUST apply only
from `new` and MUST NOT alter terminal states. When Document Review is ON,
`action_validate()` MUST refuse while any attachment-bearing line is `pending`. When
OFF, Validate MUST succeed from `new` even with pending attached lines.
(Previously: Validate always refused while any attached line was `pending`.)

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

- GIVEN Document Review is ON and a voucher in `new` with at least one
  attachment-bearing line still `pending`
- WHEN `action_validate()` is invoked
- THEN validation MUST be refused and `state` MUST remain `new`

#### Scenario: Validate succeeds with pending attachments when review is off

- GIVEN Document Review is OFF and a voucher in `new` with at least one
  attachment-bearing line still `pending`
- WHEN `action_validate()` is invoked
- THEN validation MUST succeed and `state` MUST become `validated`

### Requirement: Approve may validate voucher when all attached lines approved

When Document Review is ON and a line is approved, if the parent voucher is `new` and
every attachment-bearing line is `approved`, the system MAY set the voucher to
`validated`. Unattached lines MUST NOT block that path. When OFF, review approve MUST
NOT run.
(Previously: Last attached-line approve MAY validate with no company flag.)

#### Scenario: Aggregate voucher validation

- GIVEN a `new` voucher whose every attachment-bearing line becomes `approved`
- WHEN the last such line is approved
- THEN the voucher `state` MUST become `validated`

#### Scenario: Review approve does not run when off

- GIVEN Document Review is OFF
- WHEN review approve is attempted
- THEN approve MUST NOT run and the voucher MUST NOT validate via review

### Requirement: Line reject immediately rejects voucher

When Document Review is ON, rejecting a line MUST set it to `rejected` and, if the
parent voucher is `new`, MUST set the voucher to `rejected`. When OFF, review reject
MUST NOT run.
(Previously: Line reject always rejected a `new` parent voucher with no company flag.)

#### Scenario: Immediate voucher rejection on line reject

- GIVEN a `new` voucher with a pending attached line
- WHEN that line is rejected
- THEN the line MUST be `rejected` and the voucher MUST become `rejected`

#### Scenario: Review reject does not run when off

- GIVEN Document Review is OFF and a `new` voucher with a pending attached line
- WHEN review reject is attempted
- THEN reject MUST NOT run and the voucher MUST remain `new`
