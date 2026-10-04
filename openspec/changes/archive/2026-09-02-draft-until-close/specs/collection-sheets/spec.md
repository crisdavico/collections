# Delta for collection-sheets

## MODIFIED Requirements

### Requirement: Membership, dates, and deletion

A voucher MUST belong to at most one sheet. Membership MUST be editable only while
`open` and frozen while `closed`. Empty sheets MUST be allowed. `date_from`/`date_to`
MUST be UTC min/max of member `create_date` (empty if no members); MUST NOT use
`received_date`. Unlink of an `open` sheet MUST unlink its draft allocations first
(vouchers MUST persist unassigned; MUST NOT be destroyed), then delete the sheet. Unlink
of a `closed` sheet MUST be refused even when the sheet has no allocations or members.
(Previously: Unlink with no allocations unassigned members; unlink failed when
allocations existed; empty closed sheets were deletable.)

#### Scenario: Assign and reassign

- GIVEN unassigned same-seller voucher, open sheet B
- WHEN moved to B
- THEN voucher belongs to B only

#### Scenario: Empty sheet

- GIVEN seller sheet with no members
- WHEN saved
- THEN `date_from` and `date_to` empty

#### Scenario: Dates from member create_date

- GIVEN members spanning two UTC days
- WHEN dates are read
- THEN `date_from` earliest, `date_to` latest

#### Scenario: Unlink open unassigns when no allocations

- GIVEN an open sheet with members and no allocations
- WHEN deleted
- THEN vouchers persist unassigned

#### Scenario: Unlink open cascades draft allocations

- GIVEN an open sheet with draft allocations and linked vouchers
- WHEN deleted
- THEN the sheet and those allocations MUST be gone
- AND vouchers MUST persist unassigned (MUST NOT be destroyed)

#### Scenario: Unlink closed refused even when empty

- GIVEN a closed sheet with no allocations and no members
- WHEN deleted
- THEN delete MUST fail
- AND the sheet MUST remain `closed`

#### Scenario: Unlink closed with allocations refused

- GIVEN a closed sheet with confirmed allocations
- WHEN deleted
- THEN delete MUST fail
- AND members MUST stay assigned

### Requirement: Open/closed lifecycle

Sheets MUST have required `state` `open` or `closed`, default `open`. Existing sheets
MUST become `open` on upgrade. Close MUST succeed when `open` and MUST confirm every
allocation on that sheet. Reopen MUST succeed when `closed` if that seller has no other
open sheet in that company, and MUST return every allocation to `draft`. Any internal
user MAY Close or Reopen. Write of raw `state` MUST be rejected except via Close or
Reopen. Reopen of a historical sheet MUST remain allowed even if the seller is later
disabled. (Previously: Close and Reopen wrote only sheet `state` and did not sync
allocations.)

#### Scenario: Default open on create

- GIVEN an internal user creates a sheet with a valid seller
- WHEN saved
- THEN `state` MUST be `open`

#### Scenario: Close when open

- GIVEN an open sheet with zero or more draft allocations
- WHEN an internal user Closes it
- THEN `state` MUST become `closed`
- AND every allocation MUST be `confirmed`

#### Scenario: Reopen when no other open

- GIVEN a closed sheet with confirmed allocations and that seller has no other open
  sheet in that company
- WHEN an internal user Reopens it
- THEN `state` MUST become `open`
- AND every allocation MUST be `draft`

#### Scenario: Raw state write rejected

- GIVEN a sheet
- WHEN `state` is written except via Close or Reopen
- THEN the write MUST be rejected

#### Scenario: Reopen rejected if another open exists

- GIVEN a closed sheet and that seller has another open sheet in the same company
- WHEN Reopen runs
- THEN the action MUST be rejected and `state` MUST remain `closed`
- AND allocations MUST remain `confirmed`

### Requirement: Closed sheet membership freeze

While a sheet is `closed`, membership MUST NOT be added, removed, or reassigned via
sheet members or voucher `sheet_id`, and voucher `partner_id` MUST NOT change. Operators
MUST Reopen first. Freeze applies while the sheet exists. Closed unlink MUST be refused
even when empty. Closed `partner_id` writes MUST raise the same membership `UserError`
as closed `sheet_id` membership writes. (Previously: Sheet delete was not a membership
edit, so empty closed sheets could be unlinked.)

#### Scenario: Freeze add, remove, and reassign

- GIVEN a closed sheet with members
- WHEN add, remove, or reassign of membership is attempted
- THEN the write MUST be rejected and membership MUST be unchanged

#### Scenario: Closed partner_id reuses membership UserError

- GIVEN a voucher on a closed sheet
- WHEN `partner_id` is written
- THEN the write MUST raise the membership `UserError`
- AND `partner_id` MUST be unchanged

#### Scenario: Closed empty unlink refused

- GIVEN a closed sheet with no members
- WHEN deleted
- THEN delete MUST fail
- AND the sheet MUST remain
