# Delta for collection-sheets

## ADDED Requirements

### Requirement: Sheet form notebook

Sheet form MUST expose vouchers and allocations in a notebook.

#### Scenario: Sheet form notebook

- GIVEN a saved sheet
- WHEN form opens
- THEN notebook shows vouchers and allocations

## MODIFIED Requirements

### Requirement: Membership, dates, and deletion

A voucher MUST belong to at most one sheet. Membership MUST be editable only while
`open` and frozen while `closed`. Empty sheets MUST be allowed. `date_from`/`date_to`
MUST be UTC min/max of member `create_date` (empty if no members); MUST NOT use
`received_date`. Unlink with no allocations MUST unassign members and MUST NOT delete
vouchers. Unlink MUST fail when allocations exist (restrict). (Previously: Deleting any
sheet unassigned members regardless of allocations.)

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

#### Scenario: Unlink unassigns when no allocations

- GIVEN sheet with members, no allocations
- WHEN deleted
- THEN vouchers persist unassigned

#### Scenario: Unlink refused when allocations exist

- GIVEN sheet with allocations
- WHEN deleted
- THEN delete fails; members stay assigned
