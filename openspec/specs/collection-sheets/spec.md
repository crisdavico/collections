# Collection Sheets Specification

## Purpose

Group a seller’s vouchers on `collection.sheet`. Open or closed state; no other
workflow. One sheet per voucher.

## Requirements

### Requirement: Sheet sequence identity

Each new sheet MUST get a unique persisted name `CS/<year>/<number>` via sequence code
`collection.sheet`. Sheets MUST have `state` `open` or `closed` and MUST NOT have any
other workflow. (Previously: Sheets MUST NOT have `state` or workflow.)

#### Scenario: Sequence assigned on create

- GIVEN an internal user creates a sheet with a valid seller
- WHEN saved the first time
- THEN name MUST match `CS/<current-year>/<number>` and be unique
- AND `state` MUST be `open`

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
edit. Form MUST show name, required `seller_id` (readonly after create), dates,
membership, a non-clickable statusbar, Close when `open`, Reopen when `closed`, and
chatter/activity composer. Membership MUST be readonly when closed. List/search MUST
show name, seller, dates, and `state`. Document Review header action MUST remain
available on saved sheets (including closed) when the company flag is ON. (Previously:
Form had editable membership, no workflow statusbar, and no chatter.)

#### Scenario: Menu and form behaviors

- GIVEN the module installed
- WHEN an internal user opens Collections → Collection Sheets then a form
- THEN list/search MUST show name, seller, dates, and `state`
- AND form MUST show name, required seller, dates, a non-clickable statusbar, Close when
  open, and Reopen when closed
- AND membership MUST be editable when open and readonly when closed
- AND form MUST include chatter/activity composer

### Requirement: Mail thread and activities

`collection.sheet` MUST inherit `mail.thread` and `mail.activity.mixin`. Operators MAY
post messages and schedule activities on a sheet. Close and Reopen SHOULD be tracked in
chatter.

#### Scenario: Message persists on sheet

- GIVEN a saved collection sheet
- WHEN an operator posts a chatter comment
- THEN that comment MUST persist on the sheet thread

#### Scenario: Close tracks state in chatter

- GIVEN an open sheet
- WHEN an internal user Closes it
- THEN chatter MUST record the state change from Open to Closed

#### Scenario: Reopen tracks state in chatter

- GIVEN a closed sheet that can be reopened
- WHEN an internal user Reopens it
- THEN chatter MUST record the state change from Closed to Open

### Requirement: Saved-sheet header action opens Document Review

A saved collection sheet MUST expose a header action that opens Document Review with
that sheet's mandatory identifier. The action MUST be available when the current
company's flag is ON, MUST be hidden and refused when OFF, and MUST NOT open from an
unsaved sheet.

#### Scenario: Header action available when flag is on

- GIVEN a saved collection sheet and Document Review ON for the current company
- WHEN an internal user views the sheet form
- THEN the header action that opens Document Review MUST be available

#### Scenario: Header action hidden or refused when flag is off

- GIVEN a saved collection sheet and Document Review OFF for the current company
- WHEN an internal user views the sheet form or invokes the header action
- THEN the action MUST be hidden
- AND invocation MUST be refused

#### Scenario: Unsaved sheet must not open review

- GIVEN a new unsaved collection sheet and Document Review ON
- WHEN an internal user attempts to open Document Review from that form
- THEN Document Review MUST NOT open

#### Scenario: Sheet action parameters

- GIVEN a saved collection sheet and Document Review ON
- WHEN the header action runs
- THEN it MUST open the Document Review client action
- AND it MUST supply that sheet's identifier as a mandatory parameter

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
