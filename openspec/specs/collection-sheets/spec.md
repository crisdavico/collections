# Collection Sheets Specification

## Purpose

Group a seller’s vouchers on `collection.sheet`. Open or closed state; no other
workflow. One sheet per voucher.

## Requirements

### Requirement: Sheet sequence identity

Each new sheet MUST get a unique persisted name `CS/<year>/<number>` via sequence code
`collection.sheet`. Numbering MUST be isolated per company. Sheets MUST have `state`
`open`, `proposal`, `closed`, or `cancelled` and MUST NOT have any other workflow.
(Previously: `state` was `open` or `closed` only.)

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

A voucher MUST belong to at most one sheet. Membership MUST be editable only while
`open` and frozen while `proposal`, `closed`, or `cancelled`. Empty sheets MUST be
allowed. `date_from`/`date_to` MUST be UTC min/max of member `create_date` (empty if no
members); MUST NOT use `received_date`. Unlink of an `open` sheet MUST unlink its draft
allocations first (vouchers MUST persist unassigned; MUST NOT be destroyed), then delete
the sheet. Unlink of a `proposal`, `closed`, or `cancelled` sheet MUST be refused even
when the sheet has no allocations or members.
(Previously: Membership frozen only while closed; unlink refused only for closed.)

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

#### Scenario: Unlink proposal or cancelled refused

- GIVEN a proposal or cancelled sheet, empty or with members
- WHEN deleted
- THEN delete MUST fail and the sheet MUST remain

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
edit. Form MUST show name, required `seller_id` (readonly after create), dates, a
non-clickable statusbar (`open`, `proposal`, `closed`, `cancelled`), chatter/activity
composer, and the three-page notebook. Header MUST show Document Review and Confirm when
saved and `open`; Close and Cancel when `proposal`; Cancel when `closed`; Open when
`cancelled`. Reopen MUST NOT exist. Export XLSX MUST remain available in every state.
Membership MUST be editable only when `open`. List/search MUST show name, seller, dates,
and `state`.
(Previously: Statusbar `open,closed`; Close when open; Reopen when closed; Document
Review including closed.)

#### Scenario: Menu and form behaviors

- GIVEN the module installed
- WHEN an internal user opens Collections → Collection Sheets then a form
- THEN list/search MUST show name, seller, dates, and `state`
- AND form MUST show name, required seller, dates, a non-clickable four-state statusbar
- AND membership MUST be editable when open and readonly when not open
- AND form MUST include chatter/activity composer

#### Scenario: Header actions by state

- GIVEN a saved sheet in each of the four states
- WHEN the form opens
- THEN Open MUST show Document Review and Confirm; Proposal Close and Cancel; Closed
  Cancel; Cancelled Open
- AND Reopen MUST NOT appear
- AND Export XLSX MUST appear in every state

#### Scenario: Illegal header action refused

- GIVEN an open sheet
- WHEN Close or Cancel is invoked
- THEN MUST refuse and `state` MUST remain `open`

### Requirement: Mail thread and activities

`collection.sheet` MUST inherit `mail.thread` and `mail.activity.mixin`. Operators MAY
post messages and schedule activities on a sheet. Confirm, Close, Cancel, and Open
SHOULD be tracked in chatter.
(Previously: Close and Reopen SHOULD be tracked.)

#### Scenario: Message persists on sheet

- GIVEN a saved collection sheet
- WHEN an operator posts a chatter comment
- THEN that comment MUST persist on the sheet thread

#### Scenario: Confirm tracks state in chatter

- GIVEN an open sheet
- WHEN an internal user Confirms it
- THEN chatter MUST record the state change from Open to Proposal

#### Scenario: Close tracks state in chatter

- GIVEN a proposal sheet
- WHEN an internal user Closes it
- THEN chatter MUST record the state change from Proposal to Closed

#### Scenario: Cancel tracks state in chatter

- GIVEN a proposal or closed sheet
- WHEN an internal user Cancels it
- THEN chatter MUST record the state change to Cancelled

#### Scenario: Open tracks state in chatter

- GIVEN a cancelled sheet that can be opened
- WHEN an internal user Opens it
- THEN chatter MUST record the state change from Cancelled to Open

### Requirement: Saved-sheet header action opens Document Review

A saved `open` collection sheet MUST expose a header action that opens Document Review
with that sheet's mandatory identifier. The action MUST be available when the current
company's flag is ON and `state` is `open`, MUST be hidden and refused when the flag is
OFF or `state` is not `open`, and MUST NOT open from an unsaved sheet.
(Previously: Available on saved sheets including closed when the company flag is ON.)

#### Scenario: Header action available when flag is on

- GIVEN a saved open collection sheet and Document Review ON for the current company
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

- GIVEN a saved open collection sheet and Document Review ON
- WHEN the header action runs
- THEN it MUST open the Document Review client action
- AND it MUST supply that sheet's identifier as a mandatory parameter

#### Scenario: Non-open sheet hides and refuses review

- GIVEN a saved proposal, closed, or cancelled sheet and Document Review ON
- WHEN an internal user views the form or invokes the header action
- THEN the action MUST be hidden and invocation MUST be refused

### Requirement: Open/closed lifecycle

Sheets MUST have required `state` `open`, `proposal`, `closed`, or `cancelled`, default
`open`. Existing `open` and `closed` rows MUST stay unchanged on upgrade (MUST NOT
remap). Legal transitions MUST be: `open` → Confirm → `proposal`; `proposal` → Close →
`closed`; `proposal` → Cancel → `cancelled`; `closed` → Cancel → `cancelled`;
`cancelled` → Open → `open`. Create MUST persist `open` and MUST reject any other
`state`. Close MUST succeed only from `proposal` and MUST confirm every allocation then
close. Cancel MUST succeed from `proposal` or `closed` and MUST return every allocation
to `draft`. Open MUST succeed from `cancelled` if that seller has no other open sheet in
that company, and MUST leave allocations `draft`. Confirm MUST NOT confirm allocations.
Any internal user MAY run those audited actions. Write of raw `state` MUST be rejected
except via Confirm, Close, Cancel, or Open. Open of a historical cancelled sheet MUST
remain allowed even if the seller is later disabled. Reopen MUST NOT exist.
(Previously: Two states; Close from open confirmed allocations; Reopen from closed
drafted allocations.)

#### Scenario: Default open on create

- GIVEN an internal user creates a sheet with a valid seller
- WHEN saved
- THEN `state` MUST be `open`

#### Scenario: Close when proposal

- GIVEN a proposal sheet with zero or more draft allocations
- WHEN an internal user Closes it
- THEN `state` MUST become `closed`
- AND every allocation MUST be `confirmed`

#### Scenario: Open when no other open

- GIVEN a cancelled sheet with draft allocations and that seller has no other open sheet
  in that company
- WHEN an internal user Opens it
- THEN `state` MUST become `open`
- AND every allocation MUST remain `draft`

#### Scenario: Raw state write rejected

- GIVEN a sheet
- WHEN `state` is written except via Confirm, Close, Cancel, or Open
- THEN the write MUST be rejected

#### Scenario: Open rejected if another open exists

- GIVEN a cancelled sheet and that seller has another open sheet in the same company
- WHEN Open runs
- THEN the action MUST be rejected and `state` MUST remain `cancelled`
- AND allocations MUST remain `draft`

#### Scenario: Cancel from proposal or closed

- GIVEN a proposal sheet with draft allocations, or a closed sheet with confirmed
  allocations
- WHEN Cancel runs
- THEN `state` MUST become `cancelled`
- AND every allocation MUST be `draft`

#### Scenario: Illegal transition refused

- GIVEN an open sheet
- WHEN Close, Cancel, or Open is invoked
- THEN MUST refuse and `state` MUST remain `open`

#### Scenario: Non-open create rejected

- GIVEN create vals with `state` `proposal`, `closed`, or `cancelled`
- WHEN create runs
- THEN MUST be rejected with no write

### Requirement: At most one open sheet per seller (new operations)

Create of an open sheet, Open from Cancelled, and the Create Collection Sheet Action
MUST count that seller’s open sheets in that company: 0 MAY proceed; 1 MUST reject a
second open in the same company; greater than 1 in that company MUST raise `UserError`
with no new open sheet (MUST NOT pick one). Sheets in `proposal`, `closed`, or
`cancelled` MUST NOT count toward that limit. Two companies MAY each have one open sheet
for the same seller. Confirm of extras MUST still succeed. Explicit sheet create MUST
remain available when `auto_create_sheet` is OFF. The system MUST NOT add a UNIQUE SQL
constraint.
(Previously: Counted Reopen as an open-creating operation; did not exclude Proposal from
the open count.)

#### Scenario: Create second open rejected

- GIVEN a seller already has one open sheet in company A
- WHEN another sheet is created for that seller in company A
- THEN the create MUST be rejected

#### Scenario: Open rejected if another open exists

- GIVEN a cancelled sheet and that seller has another open sheet in the same company
- WHEN Open runs
- THEN the action MUST be rejected and `state` MUST remain `cancelled`

#### Scenario: More than one open fail-closed on new operations

- GIVEN a seller has more than one open sheet in that company
- WHEN create of an open sheet, Open from Cancelled, or the Create Collection Sheet
  Action runs
- THEN the operation MUST raise `UserError` with no new open sheet

#### Scenario: Confirming extras still succeeds

- GIVEN a seller has more than one open sheet in that company
- WHEN Confirm runs on one of them whose members satisfy the Confirm gate
- THEN that sheet MUST become `proposal`

#### Scenario: Same seller may be open in two companies

- GIVEN seller S already has one open sheet in company A
- WHEN an open sheet is created for S in company B
- THEN the create MUST succeed
- AND company A’s open sheet MUST remain open

#### Scenario: Explicit create remains when auto-create is off

- GIVEN `auto_create_sheet` OFF, an enabled seller, and zero open sheets in that company
- WHEN an internal user creates a sheet explicitly
- THEN the sheet MUST persist as `open`

#### Scenario: Proposal does not occupy one-open

- GIVEN a seller with one proposal sheet and zero open sheets in that company
- WHEN an open sheet is created for that seller in that company
- THEN the create MUST succeed
- AND the proposal sheet MUST remain `proposal`

### Requirement: Closed sheet membership freeze

While a sheet is `proposal`, `closed`, or `cancelled`, membership MUST NOT be added,
removed, or reassigned via sheet members or voucher `sheet_id`, and voucher `partner_id`
MUST NOT change. Operators MUST Open from Cancelled before membership edits. Freeze
applies while the sheet exists. Unlink of those states MUST be refused even when empty.
`partner_id` writes MUST raise the same membership `UserError` as `sheet_id` membership
writes.
(Previously: Freeze applied only while closed; operators Reopen first.)

#### Scenario: Freeze add, remove, and reassign

- GIVEN a proposal, closed, or cancelled sheet with members
- WHEN add, remove, or reassign of membership is attempted
- THEN the write MUST be rejected and membership MUST be unchanged

#### Scenario: Closed partner_id reuses membership UserError

- GIVEN a voucher on a proposal, closed, or cancelled sheet
- WHEN `partner_id` is written
- THEN the write MUST raise the membership `UserError`
- AND `partner_id` MUST be unchanged

#### Scenario: Closed empty unlink refused

- GIVEN a closed sheet with no members
- WHEN deleted
- THEN delete MUST fail
- AND the sheet MUST remain

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
system MUST NOT hide or delete them for that reason. Confirm from `open` MUST still
succeed when the Confirm gate is met.
(Previously: Close MUST still succeed from open.)

#### Scenario: Disabled-seller sheet stays visible and confirmable

- GIVEN an open sheet whose seller is later removed from the enabled list
- WHEN an allowed-company user opens Collection Sheets and Confirms it (members eligible)
- THEN the sheet MUST still be listed
- AND `state` MUST become `proposal`
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

Sheet form MUST show three notebook pages: Allocations, Vouchers, and Debt (MUST NOT
hide them). Allocations MUST list Reference (`name`), Customer (`partner_id`),
`total_debt`, `total_vouchers`, and Residual, and MUST NOT list `state` or
`total_applied`. Draft allocations MUST be addable, editable, and deletable when `open`
or `proposal`, opening the allocation form. Vouchers MUST show all `voucher_ids`;
operators MAY open existing members only when `open`; the tab MUST NOT create, remove, or
delete vouchers. Debt MUST list all allocation invoice/debt lines for the sheet; only
`amount_applied` MUST be editable when `open` or `proposal`; create and delete MUST be
disabled. Unlink of membership MUST remain via voucher `sheet_id` while `open`.
(Previously: Allocations-only notebook; `voucher_ids` hidden; counted Vouchers stat
button; columns included `state` and `total_applied`.)

#### Scenario: Three-page notebook with Allocations columns

- GIVEN a saved sheet
- WHEN the form opens
- THEN the notebook MUST show Allocations, Vouchers, and Debt
- AND allocations MUST show name, Customer, `total_debt`, `total_vouchers`, Residual
- AND MUST NOT show `state` or `total_applied`

#### Scenario: Vouchers tab opens existing members only in Open

- GIVEN a saved open sheet with members
- WHEN the Vouchers page is used
- THEN those `voucher_ids` MUST appear
- AND create, remove, and delete from the tab MUST be unavailable

#### Scenario: Debt tab amount_applied only in Open or Proposal

- GIVEN a saved open or proposal sheet with allocation lines
- WHEN the Debt page is used
- THEN only `amount_applied` MUST be editable
- AND create and delete MUST be disabled

### Requirement: Confirm review gate

Confirm MUST run only from `open`. The system MUST raise `UserError` and MUST NOT
change sheet or allocation `state` unless every member voucher has `state`
`validated_collections`. An empty member set MUST pass. Missing designated proof,
Document Review OFF, or any member not `validated_collections` MUST block Confirm.
Confirm MUST set the sheet to `proposal` and MUST NOT confirm allocations.

#### Scenario: All members validated_collections

- GIVEN an open sheet whose every member is `validated_collections`
- WHEN Confirm runs
- THEN `state` MUST become `proposal`
- AND every allocation MUST remain `draft`

#### Scenario: Empty members pass Confirm

- GIVEN an open sheet with no member vouchers
- WHEN Confirm runs
- THEN `state` MUST become `proposal`

#### Scenario: Unreviewed member blocks Confirm

- GIVEN an open sheet with at least one member not `validated_collections`
- WHEN Confirm runs
- THEN MUST raise `UserError` and `state` MUST remain `open`

### Requirement: Four-state sheet editability

Allocations, debt `amount_applied`, and reconciliation inputs MUST be editable when
the sheet is `open` or `proposal`. Voucher membership and voucher business fields MUST
be editable only when `open`. When `closed` or `cancelled`, those records MUST be
read-only except chatter and PDF/XLSX. Confirm MUST NOT confirm allocations.

#### Scenario: Proposal keeps allocation and debt editable

- GIVEN a proposal sheet with draft allocations and debt lines
- WHEN allocation fields or line `amount_applied` are written lawfully
- THEN the writes MUST persist

#### Scenario: Closed and Cancelled freeze business writes

- GIVEN a closed or cancelled sheet
- WHEN allocation fields, debt `amount_applied`, or recon inputs are written
- THEN MUST refuse and stored values MUST be unchanged

#### Scenario: Proposal freezes voucher membership

- GIVEN a proposal sheet with members
- WHEN add, remove, or reassign of membership is attempted
- THEN the write MUST be rejected and membership MUST be unchanged
