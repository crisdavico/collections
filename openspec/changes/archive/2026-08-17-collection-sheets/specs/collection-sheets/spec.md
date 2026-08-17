# Collection Sheets Specification

## Purpose

Group a seller’s vouchers on `collection.sheet`. No workflow. One sheet per voucher.

## Requirements

### Requirement: Sheet sequence identity

Each new sheet MUST get a unique persisted name `CS/<year>/<number>` via sequence code
`collection.sheet`. Sheets MUST NOT have `state` or workflow.

#### Scenario: Sequence assigned on create

- GIVEN an internal user creates a sheet with a valid seller
- WHEN saved the first time
- THEN name MUST match `CS/<current-year>/<number>` and be unique with no `state`

### Requirement: Sheet seller and same-seller invariant

Sheet `seller_id` MUST be a required internal user (not portal/share), readonly after
create, and MUST NOT default from the creator. Assigned vouchers MUST match the sheet
seller. Null-seller vouchers MUST NOT be assignable.

#### Scenario: Seller required and frozen

- GIVEN a new sheet without `seller_id`, or an existing sheet seller change
- WHEN saved
- THEN the write MUST be rejected and seller MUST NOT be copied from the creator

#### Scenario: Mixed or null seller rejected

- GIVEN mixed-seller vouchers or a null-seller voucher
- WHEN assigned to one sheet
- THEN the write MUST be rejected

### Requirement: Membership, dates, and deletion

A voucher MUST belong to at most one sheet. Membership MUST be editable. Empty sheets
MUST be allowed. `date_from`/`date_to` MUST be the UTC calendar min/max of member
`create_date`; empty sheets MUST have both dates empty; MUST NOT use `received_date`.
Deleting a sheet MUST unassign members and MUST NOT delete those vouchers.

#### Scenario: Assign and reassign

- GIVEN an unassigned voucher of the sheet’s seller, and sheet B with the same seller
- WHEN assigned then moved to sheet B
- THEN the voucher MUST belong to sheet B only

#### Scenario: Empty sheet

- GIVEN a sheet with a valid seller and no members
- WHEN saved
- THEN the sheet MUST persist with empty `date_from` and `date_to`

#### Scenario: Dates from member create_date

- GIVEN a sheet whose members’ `create_date` span two UTC days
- WHEN dates are read
- THEN `date_from` MUST be the earliest UTC date and `date_to` the latest

#### Scenario: Unlink unassigns

- GIVEN a sheet with member vouchers
- WHEN the sheet is deleted
- THEN those vouchers MUST persist with no sheet

### Requirement: Create sheet Action

Payment Vouchers MUST expose a list-bound Action with no wizard. It MUST create one
sheet when the selection is unassigned, same non-null seller, any voucher state; MUST
set that seller; and MUST assign the selection.

#### Scenario: Unassigned same-seller any state

- GIVEN two unassigned vouchers of the same seller in `pending` and `approved`
- WHEN the list Action runs
- THEN one sheet MUST be created with that seller and both vouchers as members

#### Scenario: Ineligible selection rejected

- GIVEN mixed sellers, an already assigned voucher, or an empty selection
- WHEN the Action runs
- THEN the Action MUST be rejected with no sheet created

### Requirement: Authorization for internal users

Internal users (`base.group_user`) MUST have full CRUD on sheets. Dedicated groups and
record rules MUST NOT be added.

#### Scenario: Internal user CRUD

- GIVEN an authenticated internal user
- WHEN they CRUD a sheet
- THEN ACL MUST allow it

#### Scenario: Non-internal user denied

- GIVEN a user without internal-user privileges
- WHEN they attempt sheet CRUD
- THEN access MUST be denied

### Requirement: Collection Sheets UI

Collections → Collection Sheets MUST provide list, form, and search with create and
edit. Form MUST show name, required `seller_id` (readonly after create), dates, and
editable membership without a workflow statusbar. List/search MUST show name, seller,
and dates.

#### Scenario: Menu and form behaviors

- GIVEN the module installed
- WHEN an internal user opens Collections → Collection Sheets then a form
- THEN list/search MUST show name, seller, and dates
- AND form MUST show name, required seller, dates, and membership without a workflow
  statusbar
