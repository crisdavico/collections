# Collection Sheets Specification

## Purpose

Group a seller’s vouchers on `collection.sheet`. Open or closed state; no other
workflow. One sheet per voucher.

## Requirements

### Requirement: Sheet sequence identity

Each new sheet MUST get a unique persisted name `CS/<year>/<number>` via sequence code
`collection.sheet`. Numbering MUST be isolated per company. Sheets MUST have `state`
`open` or `closed` and MUST NOT have any other workflow. (Previously: One global
sequence numbered all companies together.)

#### Scenario: Sequence assigned on create

- GIVEN an internal user creates a sheet with a valid seller
- WHEN saved the first time
- THEN name MUST match `CS/<current-year>/<number>` and be unique
- AND `state` MUST be `open`

#### Scenario: Numbers isolated per company

- GIVEN companies A and B each create a new sheet
- WHEN both saves complete
- THEN each company's names MUST number independently of the other

### Requirement: Sheet seller and same-seller invariant

Sheet `seller_id` MUST be a required internal user (not portal/share), readonly after
create, and MUST NOT default from the creator. NEW sheet create MUST require that seller
to be enabled for the sheet's company. Assigned vouchers MUST match the sheet seller.
Null-seller vouchers MUST NOT be assignable. (Previously: Seller was required but not
gated by the company enabled list.)

#### Scenario: Seller required and frozen

- GIVEN a new sheet without `seller_id`, or an existing sheet seller change
- WHEN saved
- THEN the write MUST be rejected and seller MUST NOT be copied from the creator

#### Scenario: Mixed or null seller rejected

- GIVEN mixed-seller vouchers or a null-seller voucher
- WHEN assigned to one sheet
- THEN the write MUST be rejected

#### Scenario: New sheet requires an enabled seller

- GIVEN a seller not on the company's enabled list (including an empty list)
- WHEN a new sheet is created with that seller via UI, ORM, or import
- THEN the create MUST be rejected with no write

### Requirement: Membership, dates, and deletion

A voucher MUST belong to at most one sheet. Membership MUST be editable only
while `open` and frozen while `closed`. Empty sheets MUST be allowed.
`date_from`/`date_to` MUST be UTC min/max of member `create_date` (empty if no
members); MUST NOT use `received_date`. Unlink with no allocations MUST
unassign members and MUST NOT delete vouchers. Unlink MUST fail when
allocations exist (restrict).
(Previously: Deleting any sheet unassigned members regardless of allocations.)

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

### Requirement: Create sheet Action

Payment Vouchers MUST expose a list-bound Action with no wizard. It MUST create one
sheet when the selection is unassigned, same non-null seller, any voucher state; MUST
set that seller and the vouchers' company; and MUST assign the selection. It MUST
succeed only when that seller’s open-sheet count in that company is 0. It MUST reject if
that seller already has any open sheet in that company (count greater than or equal to
1), including when count is greater than 1. The Action MUST remain available when
`auto_create_sheet` is OFF. The seller MUST be enabled for that company. (Previously:
Open-sheet count was per seller across all companies; auto-create was not a flag.)

#### Scenario: Unassigned same-seller any state

- GIVEN two unassigned vouchers of the same enabled seller in `pending` and `approved`,
  and that seller has zero open sheets in that company
- WHEN the list Action runs
- THEN one open sheet MUST be created with that seller and both vouchers as members

#### Scenario: Ineligible selection rejected

- GIVEN mixed sellers, an already assigned voucher, or an empty selection
- WHEN the Action runs
- THEN the Action MUST be rejected with no sheet created

#### Scenario: Action rejected when an open sheet exists

- GIVEN unassigned same-seller vouchers and that seller has one or more open sheets in
  that company
- WHEN the list Action runs
- THEN the Action MUST be rejected with no sheet created

#### Scenario: Action remains when auto-create is off

- GIVEN `auto_create_sheet` OFF, unassigned same-seller vouchers, an enabled seller, and
  zero open sheets in that company
- WHEN the list Action runs
- THEN one open sheet MUST be created and the selection assigned

#### Scenario: Action rejected for a disabled seller

- GIVEN unassigned vouchers of a seller not on the company's enabled list
- WHEN the list Action runs
- THEN the Action MUST be rejected with no sheet created

### Requirement: Authorization for internal users

Internal users (`base.group_user`) MUST have full CRUD on sheets of companies they are
allowed. Dedicated groups MUST NOT be added. Allowed-company record rules MUST hide
other companies. (Previously: No record rules; sheets were company-blind.)

#### Scenario: Internal user CRUD

- GIVEN an authenticated internal user
- WHEN they CRUD a sheet of an allowed company
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
`closed` if that seller has no other open sheet in that company. Any internal user MAY
Close or Reopen. Write of raw `state` MUST be rejected except via Close or Reopen.
Reopen of a historical sheet MUST remain allowed even if the seller is later disabled.
(Previously: Reopen counted open sheets per seller across all companies.)

#### Scenario: Default open on create

- GIVEN an internal user creates a sheet with a valid seller
- WHEN saved
- THEN `state` MUST be `open`

#### Scenario: Close when open

- GIVEN an open sheet
- WHEN an internal user Closes it
- THEN `state` MUST become `closed`

#### Scenario: Reopen when no other open

- GIVEN a closed sheet and that seller has no other open sheet in that company
- WHEN an internal user Reopens it
- THEN `state` MUST become `open`

#### Scenario: Raw state write rejected

- GIVEN a sheet
- WHEN `state` is written except via Close or Reopen
- THEN the write MUST be rejected

### Requirement: At most one open sheet per seller (new operations)

Create of an open sheet, Reopen, and the Create Collection Sheet Action MUST count that
seller’s open sheets in that company: 0 MAY proceed; 1 MUST reject a second open in the
same company; greater than 1 in that company MUST raise `UserError` with no new open
sheet (MUST NOT pick one). Two companies MAY each have one open sheet for the same
seller. Close of extras MUST still succeed. Explicit sheet create MUST remain available
when `auto_create_sheet` is OFF. The system MUST NOT add a UNIQUE SQL constraint.
(Previously: One-open was per seller across all companies.)

#### Scenario: Create second open rejected

- GIVEN a seller already has one open sheet in company A
- WHEN another sheet is created for that seller in company A
- THEN the create MUST be rejected

#### Scenario: Reopen rejected if another open exists

- GIVEN a closed sheet and that seller has another open sheet in the same company
- WHEN Reopen runs
- THEN the action MUST be rejected and `state` MUST remain `closed`

#### Scenario: More than one open fail-closed on new operations

- GIVEN a seller has more than one open sheet in that company
- WHEN create of an open sheet, Reopen, or the Create Collection Sheet Action runs
- THEN the operation MUST raise `UserError` with no new open sheet

#### Scenario: Closing extras still succeeds

- GIVEN a seller has more than one open sheet in that company
- WHEN Close runs on one of them
- THEN that sheet MUST become `closed`

#### Scenario: Same seller may be open in two companies

- GIVEN seller S already has one open sheet in company A
- WHEN an open sheet is created for S in company B
- THEN the create MUST succeed
- AND company A’s open sheet MUST remain open

#### Scenario: Explicit create remains when auto-create is off

- GIVEN `auto_create_sheet` OFF, an enabled seller, and zero open sheets in that company
- WHEN an internal user creates a sheet explicitly
- THEN the sheet MUST persist as `open`

### Requirement: Closed sheet membership freeze

While a sheet is `closed`, membership MUST NOT be added, removed, or reassigned via
sheet members or voucher `sheet_id`. Operators MUST Reopen first. Freeze applies while
the sheet exists; sheet delete is not a membership edit.

#### Scenario: Freeze add, remove, and reassign

- GIVEN a closed sheet with members
- WHEN add, remove, or reassign of membership is attempted
- THEN the write MUST be rejected and membership MUST be unchanged

### Requirement: Company ownership of sheets

Every sheet MUST have a required company. Users MUST see and operate only sheets of
companies they are allowed. Dedicated groups MUST NOT be added.

#### Scenario: Company required on create

- GIVEN a new sheet with an enabled seller
- WHEN saved
- THEN it MUST belong to a company
- AND that company MUST be one the user is allowed

#### Scenario: Other-company sheets hidden

- GIVEN a sheet in a company the user is not allowed
- WHEN they search or open Collection Sheets
- THEN that sheet MUST NOT be visible
- AND they MUST NOT read its id or name

### Requirement: Historical sheets remain operable

Existing sheets MUST stay visible and operable if their seller is later disabled. The
system MUST NOT hide or delete them for that reason. Close MUST still succeed.

#### Scenario: Disabled-seller sheet stays visible and closeable

- GIVEN an open sheet whose seller is later removed from the enabled list
- WHEN an allowed-company user opens Collection Sheets and Closes it
- THEN the sheet MUST still be listed
- AND `state` MUST become `closed`
- AND the sheet MUST NOT be deleted

### Requirement: Upgrade stamps sheet company and sequences

On upgrade the system MUST stamp each sheet's company from the seller's company when
set, otherwise the database default company, and convert sequences so each company has
its own sheet numbering with no company-less sequence stealing numbers.

#### Scenario: Sheet company from seller or default

- GIVEN a sheet whose seller has a company, and another whose seller has none
- WHEN upgrade runs
- THEN the first MUST take the seller company
- AND the second MUST take the default company

#### Scenario: Per-company sheet sequences without a company-less thief

- GIVEN a former company-less sheet sequence
- WHEN upgrade runs and two companies then create sheets
- THEN each company MUST receive isolated `CS/<year>/<number>` names
- AND a company-less sequence MUST NOT consume either company's numbers

### Requirement: Sheet form notebook

Sheet form MUST show one Allocations notebook page (MUST NOT hide it). That list MUST
show Customer (`partner_id`) after name and before `state`. The form MUST NOT expose
`voucher_ids`. A saved sheet MUST expose a counted Vouchers action for that sheet's
members only. An unsaved sheet MUST hide and refuse that action. Unlink MUST remain via
voucher `sheet_id`.

(Previously: Notebook showed Vouchers (`voucher_ids`) and Allocations.)

#### Scenario: Allocations-only notebook with Customer

- GIVEN a saved sheet
- WHEN the form opens
- THEN the notebook MUST show Allocations only
- AND allocations MUST show Customer after name and before `state`
- AND `voucher_ids` MUST NOT appear on the form

#### Scenario: Saved sheet opens filtered vouchers

- GIVEN a saved sheet with members
- WHEN the Vouchers action runs
- THEN only vouchers with that `sheet_id` MUST appear
- AND Collections → Payment Vouchers MUST remain the menu destination

#### Scenario: Unsaved sheet hides and refuses voucher action

- GIVEN a new unsaved sheet
- WHEN the form is viewed or the Vouchers action invoked
- THEN the action MUST be hidden and invocation MUST be refused
