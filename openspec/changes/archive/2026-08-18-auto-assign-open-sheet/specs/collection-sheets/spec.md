# Delta for Collection Sheets

## ADDED Requirements

### Requirement: Open/closed lifecycle

Sheets MUST have required `state` `open` or `closed`, default `open`. Existing sheets
MUST become `open` on upgrade. Close MUST succeed when `open`. Reopen MUST succeed when
`closed` if the seller has no other open sheet. Any internal user MAY Close or Reopen.
Write of raw `state` MUST be rejected except via Close or Reopen.

#### Scenario: Default open on create

- GIVEN an internal user creates a sheet with a valid seller
- WHEN saved
- THEN `state` MUST be `open`

#### Scenario: Close when open

- GIVEN an open sheet
- WHEN an internal user Closes it
- THEN `state` MUST become `closed`

#### Scenario: Reopen when no other open

- GIVEN a closed sheet and that seller has no other open sheet
- WHEN an internal user Reopens it
- THEN `state` MUST become `open`

#### Scenario: Raw state write rejected

- GIVEN a sheet
- WHEN `state` is written except via Close or Reopen
- THEN the write MUST be rejected

### Requirement: At most one open sheet per seller (new operations)

Create of an open sheet, Reopen, and the Create Collection Sheet Action MUST count that
seller’s open sheets: 0 MAY proceed; 1 MUST reject a second open; greater than 1 MUST
raise `UserError` with no new open sheet (MUST NOT pick one). Close of extras MUST still
succeed. The system MUST NOT add a UNIQUE SQL constraint.

#### Scenario: Create second open rejected

- GIVEN a seller already has one open sheet
- WHEN another sheet is created for that seller
- THEN the create MUST be rejected

#### Scenario: Reopen rejected if another open exists

- GIVEN a closed sheet and that seller has another open sheet
- WHEN Reopen runs
- THEN the action MUST be rejected and `state` MUST remain `closed`

#### Scenario: More than one open fail-closed on new operations

- GIVEN a seller has more than one open sheet
- WHEN create of an open sheet, Reopen, or the Create Collection Sheet Action runs
- THEN the operation MUST raise `UserError` with no new open sheet

#### Scenario: Closing extras still succeeds

- GIVEN a seller has more than one open sheet
- WHEN Close runs on one of them
- THEN that sheet MUST become `closed`

### Requirement: Closed sheet membership freeze

While a sheet is `closed`, membership MUST NOT be added, removed, or reassigned via
sheet members or voucher `sheet_id`. Operators MUST Reopen first. Freeze applies while
the sheet exists; sheet delete is not a membership edit.

#### Scenario: Freeze add, remove, and reassign

- GIVEN a closed sheet with members
- WHEN add, remove, or reassign of membership is attempted
- THEN the write MUST be rejected and membership MUST be unchanged

## MODIFIED Requirements

### Requirement: Sheet sequence identity

Each new sheet MUST get a unique persisted name `CS/<year>/<number>` via sequence code
`collection.sheet`. Sheets MUST have `state` `open` or `closed` and MUST NOT have any
other workflow. (Previously: Sheets MUST NOT have `state` or workflow.)

#### Scenario: Sequence assigned on create

- GIVEN an internal user creates a sheet with a valid seller
- WHEN saved the first time
- THEN name MUST match `CS/<current-year>/<number>` and be unique
- AND `state` MUST be `open`

### Requirement: Membership, dates, and deletion

A voucher MUST belong to at most one sheet. Membership MUST be editable only while the
sheet is `open`. While `closed`, membership MUST be frozen (no add, remove, or
reassign). Empty sheets MUST be allowed. `date_from`/`date_to` MUST be the UTC calendar
min/max of member `create_date`; empty sheets MUST have both dates empty; MUST NOT use
`received_date`. Deleting a sheet (open or closed) MUST unassign members (`ondelete` set
null) and MUST NOT delete those vouchers. Freeze MUST NOT trap vouchers: unlink of a
closed sheet MUST still unassign. (Previously: Membership MUST be editable at any time;
sheets had no open/closed freeze.)

#### Scenario: Assign and reassign

- GIVEN an unassigned voucher of the sheet’s seller, and open sheet B with the same
  seller, and the source sheet open
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

- GIVEN an open or closed sheet with member vouchers
- WHEN the sheet is deleted
- THEN those vouchers MUST persist with no sheet

### Requirement: Create sheet Action

Payment Vouchers MUST expose a list-bound Action with no wizard. It MUST create one
sheet when the selection is unassigned, same non-null seller, any voucher state; MUST
set that seller; and MUST assign the selection. It MUST succeed only when that seller’s
open-sheet count is 0. It MUST reject if the seller already has any open sheet (count
greater than or equal to 1), including when count is greater than 1. (Previously: Action
always created a new sheet regardless of existing open sheets.)

#### Scenario: Unassigned same-seller any state

- GIVEN two unassigned vouchers of the same seller in `pending` and `approved`, and that
  seller has zero open sheets
- WHEN the list Action runs
- THEN one open sheet MUST be created with that seller and both vouchers as members

#### Scenario: Ineligible selection rejected

- GIVEN mixed sellers, an already assigned voucher, or an empty selection
- WHEN the Action runs
- THEN the Action MUST be rejected with no sheet created

#### Scenario: Action rejected when an open sheet exists

- GIVEN unassigned same-seller vouchers and that seller has one or more open sheets
- WHEN the list Action runs
- THEN the Action MUST be rejected with no sheet created

### Requirement: Collection Sheets UI

Collections → Collection Sheets MUST provide list, form, and search with create and
edit. Form MUST show name, required `seller_id` (readonly after create), dates,
membership, a non-clickable statusbar, Close when `open`, and Reopen when `closed`.
Membership MUST be readonly when closed. List/search MUST show name, seller, dates, and
`state`. Document Review header action MUST remain available on saved sheets (including
closed) when the company flag is ON. (Previously: Form had editable membership and no
workflow statusbar.)

#### Scenario: Menu and form behaviors

- GIVEN the module installed
- WHEN an internal user opens Collections → Collection Sheets then a form
- THEN list/search MUST show name, seller, dates, and `state`
- AND form MUST show name, required seller, dates, a non-clickable statusbar, Close when
  open, and Reopen when closed
- AND membership MUST be editable when open and readonly when closed
