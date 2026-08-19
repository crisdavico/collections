# Delta for collection-sheets

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Sheet sequence identity

Each new sheet MUST get a unique persisted name `CS/<year>/<number>` via sequence code
`collection.sheet`. Numbering MUST be isolated per company. Sheets MUST have `state`
`open` or `closed` and MUST NOT have any other workflow.
(Previously: One global sequence numbered all companies together.)

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
Null-seller vouchers MUST NOT be assignable.
(Previously: Seller was required but not gated by the company enabled list.)

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

### Requirement: Create sheet Action

Payment Vouchers MUST expose a list-bound Action with no wizard. It MUST create one
sheet when the selection is unassigned, same non-null seller, any voucher state; MUST
set that seller and the vouchers' company; and MUST assign the selection. It MUST
succeed only when that seller’s open-sheet count in that company is 0. It MUST reject if
that seller already has any open sheet in that company (count greater than or equal to
1), including when count is greater than 1. The Action MUST remain available when
`auto_create_sheet` is OFF. The seller MUST be enabled for that company.
(Previously: Open-sheet count was per seller across all companies; auto-create was not
a flag.)

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
other companies.
(Previously: No record rules; sheets were company-blind.)

#### Scenario: Internal user CRUD

- GIVEN an authenticated internal user
- WHEN they CRUD a sheet of an allowed company
- THEN ACL MUST allow it

#### Scenario: Non-internal user denied

- GIVEN a user without internal-user privileges
- WHEN they attempt sheet CRUD
- THEN access MUST be denied

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
