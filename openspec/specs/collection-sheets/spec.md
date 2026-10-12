# Collection Sheets Specification

## Purpose

Group a seller’s vouchers on `collection.sheet`. Open or closed state; no other
workflow. One sheet per voucher.

## Requirements

### Requirement: Sheet sequence identity

Each new sheet MUST get a unique persisted name `CS/<year>/<number>` via sequence code
`collection.sheet`. Numbering MUST be isolated per company. Sheets MUST have `state`
`open`, `submitted`, `proposal`, `closed`, or `cancelled` and MUST NOT have any other
workflow. The `submitted` key MUST display as Submitted by Seller. (Previously: Four
keys `open`, `proposal`, `closed`, `cancelled` only.)

#### Scenario: Sequence assigned on create

- GIVEN a Collections User creates a sheet with a valid seller
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

A voucher MUST belong to at most one sheet. Membership MUST be editable while `open` or
`submitted` and frozen while `proposal`, `closed`, or `cancelled`. Empty sheets MUST be
allowed. `date_from`/`date_to` MUST be UTC min/max of member `create_date` (empty if no
members); MUST NOT use `received_date`. Unlink of an `open` sheet MUST unlink its draft
allocations first (vouchers MUST persist unassigned; MUST NOT be destroyed), then delete
the sheet; it MUST be refused with no change when any allocation has a revision, a cash
replacement, or an issued receipt (cancel the sheet instead). Unlink of a `submitted`,
`proposal`, `closed`, or `cancelled` sheet MUST be
refused even when the sheet has no allocations or members. (Previously: Membership
editable only while `open`; unlink refused for non-open except `submitted` did not
exist.)

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

- GIVEN an open sheet with draft allocations (no revisions, cash replacements, or issued
  receipts) and linked vouchers
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

#### Scenario: Submitted membership add and remove

- GIVEN a submitted sheet
- WHEN a Collections User adds or removes a same-seller member
- THEN membership MUST persist
- AND chatter MUST record the membership change

#### Scenario: Unlink submitted refused

- GIVEN a submitted sheet, empty or with members
- WHEN deleted
- THEN delete MUST fail and the sheet MUST remain `submitted`

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

### Requirement: Authorization for Collections Users

Collections Users (`collection.group_collection_user`) MUST have full CRUD on sheets of
companies they are allowed. Collections Manager MUST imply Collections User, and the
administrator MUST be a Collections Manager on install. Plain internal users MUST have
no sheet access and MUST NOT see the Collections menus. Allowed-company record rules MUST
hide other companies. (Previously: every internal user, `base.group_user`, had CRUD and
dedicated groups were forbidden; before that, no record rules made sheets
company-blind.)

#### Scenario: Collections User CRUD

- GIVEN an authenticated Collections User
- WHEN they CRUD a sheet of an allowed company
- THEN ACL MUST allow it

#### Scenario: User without Collections User denied

- GIVEN an internal user without the Collections User group
- WHEN they attempt sheet CRUD
- THEN access MUST be denied

### Requirement: Collection Sheets UI

Collections → Collection Sheets MUST provide list, form, and search with create and
edit. Form MUST show name, required `seller_id` (readonly after create), dates, a
non-clickable statusbar (`open`, `submitted`, `proposal`, `closed`, `cancelled`),
chatter/activity composer, and the three-page notebook. Header MUST show Seller Close
immediately before Confirm, plus Document Review, when saved and `open`; Document Review
and Confirm when `submitted`; Close and Cancel when `proposal`; Cancel when `closed`;
Reinstate when `cancelled`; Mark/Unmark Entered in the ERP when `closed`. Confirm and
Document Review MUST show only to Collections Users; Close, Cancel, Reinstate, and
Mark/Unmark only to Collections Managers. Open and Reopen MUST NOT exist. Export XLSX
MUST remain available in every state. Membership MUST be editable when `open` or
`submitted`.
List/search MUST show name, seller, dates, and `state`. (Previously: Four-state
statusbar; Confirm on `open`; Open when `cancelled`; membership only when `open`.)

#### Scenario: Menu and form behaviors

- GIVEN the module installed
- WHEN a Collections User opens Collections → Collection Sheets then a form
- THEN list/search MUST show name, seller, dates, and `state`
- AND form MUST show name, required seller, dates, a non-clickable five-state statusbar
  including Submitted by Seller
- AND membership MUST be editable when open or submitted and readonly otherwise
- AND form MUST include chatter/activity composer

#### Scenario: Header actions by state

- GIVEN a Collections Manager and a saved sheet in each of the five states
- WHEN the form opens
- THEN Open MUST show Seller Close immediately before Confirm, plus Document Review;
  Submitted Document Review and Confirm; Proposal Close and Cancel; Closed Cancel;
  Cancelled Reinstate
- AND Open and Reopen MUST NOT appear
- AND Export XLSX MUST appear in every state

#### Scenario: Illegal header action refused

- GIVEN an open sheet
- WHEN Close, Cancel, Confirm, or Reinstate is invoked
- THEN MUST refuse and `state` MUST remain `open`

### Requirement: Mail thread and activities

`collection.sheet` MUST inherit `mail.thread` and `mail.activity.mixin`. Operators MAY
post messages and schedule activities on a sheet. Seller Close, Declare Cash, Confirm,
Close, Cancel, and Reinstate SHOULD be tracked in chatter. (Previously: Seller Close
chatter also recorded declared `cash_on_hand` and `commission_withheld` on the close
write.)

#### Scenario: Message persists on sheet

- GIVEN a saved collection sheet
- WHEN an operator posts a chatter comment
- THEN that comment MUST persist on the sheet thread

#### Scenario: Confirm tracks state in chatter

- GIVEN a submitted sheet
- WHEN a Collections User Confirms it
- THEN chatter MUST record the state change from Submitted by Seller to Proposal

#### Scenario: Close tracks state in chatter

- GIVEN a proposal sheet
- WHEN a Collections Manager Closes it
- THEN chatter MUST record the state change from Proposal to Closed

#### Scenario: Cancel tracks state in chatter

- GIVEN a submitted, proposal, or closed sheet
- WHEN a Collections Manager Cancels it
- THEN chatter MUST record the state change to Cancelled

#### Scenario: Seller Close tracks state in chatter

- GIVEN an open sheet
- WHEN a Collections User runs Seller Close
- THEN chatter MUST record the state change from Open to Submitted by Seller
- AND MUST NOT require a declared `commission_withheld` on that write

#### Scenario: Declare Cash tracks declarations in chatter

- GIVEN a submitted sheet carrying `cash` vouchers
- WHEN Declare Cash runs with `commission_withheld`
- THEN chatter MUST record `commission_withheld` and the recomputed `cash_on_hand`

#### Scenario: Reinstate tracks state in chatter

- GIVEN a cancelled sheet
- WHEN a Collections Manager Reinstates it
- THEN chatter MUST record the state change from Cancelled to Submitted by Seller

### Requirement: Saved-sheet header action opens Document Review

A saved `open` or `submitted` collection sheet MUST expose a header action that opens
Document Review with that sheet's mandatory identifier. The action MUST be available
when the current company's flag is ON and `state` is `open` or `submitted`, MUST be
hidden and refused when the flag is OFF or `state` is not `open` or `submitted`, and
MUST NOT open from an unsaved sheet. (Previously: Available only when saved and `open`.)

#### Scenario: Header action available when flag is on

- GIVEN a saved open collection sheet and Document Review ON for the current company
- WHEN a Collections User views the sheet form
- THEN the header action that opens Document Review MUST be available

#### Scenario: Header action hidden or refused when flag is off

- GIVEN a saved collection sheet and Document Review OFF for the current company
- WHEN a Collections User views the sheet form or invokes the header action
- THEN the action MUST be hidden
- AND invocation MUST be refused

#### Scenario: Unsaved sheet must not open review

- GIVEN a new unsaved collection sheet and Document Review ON
- WHEN a Collections User attempts to open Document Review from that form
- THEN Document Review MUST NOT open

#### Scenario: Sheet action parameters

- GIVEN a saved open collection sheet and Document Review ON
- WHEN the header action runs
- THEN it MUST open the Document Review client action
- AND it MUST supply that sheet's identifier as a mandatory parameter

#### Scenario: Submitted sheet opens review

- GIVEN a saved submitted collection sheet and Document Review ON
- WHEN a Collections User views the form or runs the header action
- THEN the action MUST be available
- AND it MUST open Document Review with that sheet identifier

#### Scenario: Non-reviewable sheet hides and refuses review

- GIVEN a saved proposal, closed, or cancelled sheet and Document Review ON
- WHEN a Collections User views the form or invokes the header action
- THEN the action MUST be hidden and invocation MUST be refused

### Requirement: Open/closed lifecycle

Sheets MUST have required `state` `open`, `submitted`, `proposal`, `closed`, or
`cancelled`, default `open`. Existing `open` and `closed` rows MUST stay unchanged on
upgrade (MUST NOT remap). Legal transitions MUST be: `open` → Seller Close →
`submitted`; `submitted` → Confirm → `proposal`; `proposal` → Close → `closed`;
`submitted` or `proposal` or `closed` → Cancel → `cancelled`; `cancelled` → Reinstate →
`submitted`. Create MUST persist `open` and MUST reject any other `state`. `open` MUST
be reachable only via create. Close (`action_close`) MUST succeed only from `proposal`,
MUST NOT consult the connector, and MUST NOT call `create_receipt`. Close MUST, in one
transaction, set every local `draft` receipt to `closed` with no `external_receipt_id`,
confirm every allocation, and close the sheet. Member vouchers MUST remain
`validated_collections`. Cancel MUST succeed from `submitted`, `proposal`, or `closed`
and MUST return every allocation to `draft`. Cancel from `closed` MUST reopen local
`closed` receipts to `draft` and MUST NOT change `issued` receipts. While `cancelled`,
the sheet MUST remain frozen until Reinstate. Reinstate MUST succeed from `cancelled`
without checking one-open, MUST write `submitted` (MUST NOT write `open`), and MUST
leave allocations `draft`. Confirm MUST run only from `submitted` and MUST NOT confirm
allocations. Confirm MUST require a Collections User; Close, Cancel, and Reinstate MUST
require a Collections Manager (`AccessError`), including when reached through a raw
`state` write. Close MUST refuse a sheet whose allocations apply more than their
`total_vouchers`, and Reinstate MUST re-check the per-document applied cap. Cancel MUST
clear the Entered in the ERP mark. Write of raw `state` MUST be rejected except via
Seller Close, Confirm, Close, Cancel, or Reinstate. Reinstate of
a historical cancelled sheet MUST remain allowed even if the seller is later disabled.
Open and Reopen MUST NOT exist. (Previously: Close dispatched connector `create_receipt`
then confirmed allocations.)

#### Scenario: Default open on create

- GIVEN a Collections User creates a sheet with a valid seller
- WHEN saved
- THEN `state` MUST be `open`

#### Scenario: Close when proposal

- GIVEN a proposal sheet with zero or more draft allocations and optional draft receipts
- WHEN a Collections Manager Closes it
- THEN `state` MUST become `closed`
- AND every allocation MUST be `confirmed`
- AND every draft receipt MUST be `closed` with no `external_receipt_id`

#### Scenario: Close without connector succeeds

- GIVEN a proposal sheet and no company active connector
- WHEN Close runs
- THEN MUST succeed and MUST NOT call `create_receipt`

#### Scenario: Close without receipts still closes

- GIVEN a proposal sheet whose allocations have zero receipts
- WHEN Close runs
- THEN allocations MUST be `confirmed` and the sheet MUST be `closed`

#### Scenario: Close keeps voucher documentary state

- GIVEN a proposal sheet whose members are `validated_collections`
- WHEN Close runs
- THEN those vouchers MUST remain `validated_collections`

#### Scenario: Close does not rewrite issued receipts

- GIVEN a proposal sheet with a historical `issued` receipt
- WHEN Close runs
- THEN that receipt MUST remain `issued` with its `external_receipt_id`

#### Scenario: Cancel from closed reopens local receipts only

- GIVEN a closed sheet with local `closed` receipts and historical `issued` receipts
- WHEN Cancel runs
- THEN local `closed` receipts MUST be `draft` with no `external_receipt_id`
- AND `issued` receipts MUST remain `issued`
- AND freeze MUST remain until Reinstate

#### Scenario: Reinstate from cancelled to submitted

- GIVEN a cancelled sheet with draft allocations and that seller already has an `open`
  sheet in that company
- WHEN a Collections Manager Reinstates it
- THEN `state` MUST become `submitted`
- AND every allocation MUST remain `draft`
- AND the other `open` sheet MUST remain `open`

#### Scenario: Raw state write rejected

- GIVEN a sheet
- WHEN `state` is written except via Seller Close, Confirm, Close, Cancel, or Reinstate
- THEN the write MUST be rejected

#### Scenario: Cancel from submitted proposal or closed

- GIVEN a submitted sheet with draft allocations, a proposal sheet with draft
  allocations, or a closed sheet with confirmed allocations
- WHEN Cancel runs
- THEN `state` MUST become `cancelled`
- AND every allocation MUST be `draft`

#### Scenario: Confirm from open refused

- GIVEN an open sheet whose every member is `validated_collections`
- WHEN Confirm runs
- THEN MUST refuse and `state` MUST remain `open`

#### Scenario: Submitted cannot return to open

- GIVEN a submitted sheet
- WHEN Open or a raw write of `state` `open` is attempted
- THEN MUST refuse and `state` MUST remain `submitted`

#### Scenario: Cancelled cannot return to open

- GIVEN a cancelled sheet
- WHEN Open or a raw write of `state` `open` is attempted
- THEN MUST refuse
- AND Reinstate MUST write `submitted` not `open`

#### Scenario: Proposal cannot return to submitted

- GIVEN a proposal sheet
- WHEN Seller Close or Reinstate is invoked
- THEN MUST refuse and `state` MUST remain `proposal`

#### Scenario: Illegal transition from open refused

- GIVEN an open sheet
- WHEN Close, Cancel, or Open is invoked
- THEN MUST refuse and `state` MUST remain `open`

#### Scenario: Non-open create rejected

- GIVEN create vals with `state` `submitted`, `proposal`, `closed`, or `cancelled`
- WHEN create runs
- THEN MUST be rejected with no write

### Requirement: At most one open sheet per seller (new operations)

Create of an open sheet and the Create Collection Sheet Action MUST count that seller’s
open sheets in that company: 0 MAY proceed; 1 MUST reject a second open in the same
company; greater than 1 in that company MUST raise `UserError` with no new open sheet
(MUST NOT pick one). Sheets in `submitted`, `proposal`, `closed`, or `cancelled` MUST
NOT count toward that limit. Reinstate MUST NOT check one-open. Two companies MAY each
have one open sheet for the same seller. Confirm of leftover `open` extras MUST NOT
succeed (Confirm is from `submitted` only); those extras MAY still Seller Close.
Explicit sheet create MUST remain available when `auto_create_sheet` is OFF. The system
MUST NOT add a UNIQUE SQL constraint. (Previously: Open from Cancelled counted as an
open-creating operation; `submitted` did not exist; leftover opens were Confirmable.)

#### Scenario: Create second open rejected

- GIVEN a seller already has one open sheet in company A
- WHEN another sheet is created for that seller in company A
- THEN the create MUST be rejected

#### Scenario: Reinstate ignores one-open

- GIVEN a cancelled sheet and that seller has another open sheet in the same company
- WHEN Reinstate runs
- THEN the cancelled sheet MUST become `submitted`
- AND the existing `open` sheet MUST remain `open`

#### Scenario: More than one open fail-closed on new operations

- GIVEN a seller has more than one open sheet in that company
- WHEN create of an open sheet or the Create Collection Sheet Action runs
- THEN the operation MUST raise `UserError` with no new open sheet

#### Scenario: Leftover open extras cannot Confirm

- GIVEN a seller has more than one open sheet in that company
- WHEN Confirm runs on one of them whose members satisfy the Confirm member gate
- THEN MUST refuse and that sheet MUST remain `open`

#### Scenario: Same seller may be open in two companies

- GIVEN seller S already has one open sheet in company A
- WHEN an open sheet is created for S in company B
- THEN the create MUST succeed
- AND company A’s open sheet MUST remain open

#### Scenario: Explicit create remains when auto-create is off

- GIVEN `auto_create_sheet` OFF, an enabled seller, and zero open sheets in that company
- WHEN a Collections User creates a sheet explicitly
- THEN the sheet MUST persist as `open`

#### Scenario: Submitted does not occupy one-open

- GIVEN a seller with one submitted sheet and zero open sheets in that company
- WHEN an open sheet is created for that seller in that company
- THEN the create MUST succeed
- AND the submitted sheet MUST remain `submitted`

#### Scenario: Proposal does not occupy one-open

- GIVEN a seller with one proposal sheet and zero open sheets in that company
- WHEN an open sheet is created for that seller in that company
- THEN the create MUST succeed
- AND the proposal sheet MUST remain `proposal`

### Requirement: Closed sheet membership freeze

While a sheet is `proposal`, `closed`, or `cancelled`, membership MUST NOT be added,
removed, or reassigned via sheet members or voucher `sheet_id`, and voucher `partner_id`
MUST NOT change. Operators MUST edit membership while `open` or `submitted`. Freeze
applies while the sheet exists. Unlink of frozen states MUST be refused even when empty.
`partner_id` writes MUST raise the same membership `UserError` as `sheet_id` membership
writes. That membership `UserError` text MUST remain unchanged. (Previously: Freeze
applied while not `open`; operators Open from Cancelled first.)

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

#### Scenario: Submitted membership not frozen

- GIVEN a submitted sheet with members
- WHEN add, remove, or reassign of membership is attempted lawfully
- THEN the write MUST persist

### Requirement: Company ownership of sheets

Every sheet MUST have a required company. Users MUST see and operate only sheets of
companies they are allowed. The company MUST NOT change once the sheet has vouchers or
allocations (`UserError`), and vouchers, receipt values, cash replacements, and
connector bindings MUST check their company against the records they link.

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
system MUST NOT hide or delete them for that reason. Seller Close from `open` and
Confirm from `submitted` MUST still succeed when their gates are met. (Previously:
Seller Close from `open` required declarations on the same write.)

#### Scenario: Disabled-seller sheet stays visible and confirmable

- GIVEN a submitted sheet whose seller is later removed from the enabled list
- WHEN an allowed-company user opens Collection Sheets and Confirms it (members
  eligible)
- THEN the sheet MUST still be listed
- AND `state` MUST become `proposal`
- AND the sheet MUST NOT be deleted

#### Scenario: Disabled-seller open sheet remains closeable

- GIVEN an open sheet whose seller is later removed from the enabled list
- WHEN Seller Close runs without declarations
- THEN `state` MUST become `submitted`

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
`total_applied`. Draft allocations MUST be addable and editable when `open`,
`submitted`, or `proposal`, and deletable only when `open` or `submitted` (see
collection-allocations), opening the allocation form. Vouchers MUST show all
`voucher_ids`; operators MAY open existing members only when `open` or `submitted`; the
tab MUST NOT create, remove, or delete vouchers. Debt MUST list all allocation
invoice/debt lines for the sheet; only `amount_applied` MUST be editable when `open`,
`submitted`, or `proposal`; create and delete MUST be disabled. Unlink of membership
MUST remain via voucher `sheet_id` while `open` or `submitted`. (Previously: Draft
allocations and debt editable when `open` or `proposal`; voucher members openable only
when `open`.)

#### Scenario: Three-page notebook with Allocations columns

- GIVEN a saved sheet
- WHEN the form opens
- THEN the notebook MUST show Allocations, Vouchers, and Debt
- AND allocations MUST show name, Customer, `total_debt`, `total_vouchers`, Residual
- AND MUST NOT show `state` or `total_applied`

#### Scenario: Vouchers tab opens existing members only in Open or Submitted

- GIVEN a saved open or submitted sheet with members
- WHEN the Vouchers page is used
- THEN those `voucher_ids` MUST appear
- AND create, remove, and delete from the tab MUST be unavailable

#### Scenario: Debt tab amount_applied only in Open Submitted or Proposal

- GIVEN a saved open, submitted, or proposal sheet with allocation lines
- WHEN the Debt page is used
- THEN only `amount_applied` MUST be editable
- AND create and delete MUST be disabled

### Requirement: Confirm review gate

Confirm MUST run only from `submitted`. The system MUST raise `UserError` and MUST NOT
change sheet or allocation `state` unless every member voucher has `state`
`validated_collections`, except that members whose `document_type` is in
`CONFIRM_REVIEW_EXEMPT_TYPES` MUST be accepted at `validated_seller` or
`validated_collections`. That set MUST be exactly `cash` and `seller_commission`:
neither carries a designated proof, so Document Review can never reach them and a gate
on `validated_collections` would deadlock. `draft` MUST still block. `seller_deposit`
MUST stay non-exempt because its remittance slip is reviewable, and MUST reach
`validated_collections`. An empty member set MUST pass. Missing designated proof,
Document Review OFF, or any non-exempt member not `validated_collections` MUST block
Confirm. The `UserError` MUST name the offending vouchers. Confirm MUST set the sheet to
`proposal` and MUST NOT confirm allocations. (Previously: The exempt set was `cash`
alone. Before that: every member, `cash` included, had to be `validated_collections`;
the error did not name offenders. Before that: Confirm ran only from `open`.)

#### Scenario: All members validated_collections

- GIVEN a submitted sheet whose every member is `validated_collections`
- WHEN Confirm runs
- THEN `state` MUST become `proposal`
- AND every allocation MUST remain `draft`

#### Scenario: Empty members pass Confirm

- GIVEN a submitted sheet with no member vouchers
- WHEN Confirm runs
- THEN `state` MUST become `proposal`

#### Scenario: Unreviewed member blocks Confirm

- GIVEN a submitted sheet with at least one non-exempt member not
  `validated_collections`
- WHEN Confirm runs
- THEN MUST raise `UserError` and `state` MUST remain `submitted`
- AND the message MUST name that voucher

#### Scenario: Seller-validated cash member passes Confirm

- GIVEN a submitted sheet whose only member is a `cash` voucher in `validated_seller`
- AND `cash_declared_at` is set
- WHEN Confirm runs
- THEN `state` MUST become `proposal`
- AND the cash voucher MUST stay `validated_seller`

#### Scenario: Draft cash member blocks Confirm

- GIVEN a submitted sheet with a `draft` `cash` member
- WHEN Confirm runs
- THEN MUST raise `UserError` and `state` MUST remain `submitted`

#### Scenario: Seller-validated seller_deposit member blocks Confirm

- GIVEN a submitted sheet with a `seller_deposit` member in `validated_seller`
- WHEN Confirm runs
- THEN MUST raise `UserError` and `state` MUST remain `submitted`

#### Scenario: Commission at validated_seller does not block Confirm

- GIVEN a submitted sheet whose only non-`validated_collections` member is a
  `seller_commission` at `validated_seller`
- WHEN Confirm runs
- THEN `state` MUST become `proposal`

#### Scenario: Deposit still blocks Confirm

- GIVEN a submitted sheet with a `seller_deposit` at `validated_seller`
- WHEN Confirm runs
- THEN MUST raise `UserError`
- AND `state` MUST remain `submitted`

### Requirement: Four-state sheet editability

Allocations and debt `amount_applied` MUST be editable when the sheet is `open`,
`submitted`, or `proposal`. Voucher membership and voucher business fields MUST be
editable when `open` or `submitted`, except the frozen money fields of a
`validated_collections` voucher. Seller-declared `commission_withheld` MUST be
editable only when `submitted`. `commission_percent` MUST be editable when the sheet is
not `closed` or `cancelled`. `cash_on_hand` MUST never be editable: it is a stored
compute over the sheet vouchers and `commission_withheld`. When `closed` or `cancelled`,
those records MUST be read-only except chatter and PDF/XLSX. Confirm MUST NOT confirm
allocations. (Previously: Seller-declared `cash_on_hand` and `commission_withheld` MUST
be editable only when `submitted`.)

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

#### Scenario: Submitted keeps allocation and membership editable

- GIVEN a submitted sheet with draft allocations and members
- WHEN allocation fields or membership are written lawfully
- THEN the writes MUST persist

#### Scenario: Submitted seller declarations writable

- GIVEN a submitted sheet
- WHEN `commission_withheld` is written lawfully
- THEN the write MUST persist and `cash_on_hand` MUST follow by compute

#### Scenario: Open seller declarations refused

- GIVEN an open sheet
- WHEN `commission_withheld` is written
- THEN MUST refuse and stored values MUST be unchanged

#### Scenario: cash_on_hand write refused in every state

- GIVEN a sheet in any state
- WHEN `cash_on_hand` is written
- THEN MUST refuse and the derived value MUST be unchanged

### Requirement: Seller Close from open

Seller Close MUST run only from `open` and MUST write `submitted`. The system MUST
refuse and MUST NOT change sheet or allocation `state` if any member voucher is `draft`;
the error MUST list those offenders. An empty member set MUST pass. Members in
`validated_seller` or `validated_collections` MUST pass. Seller Close MUST NOT require
an allocation and MUST NOT require every member to be `validated_collections`. Seller
Close MUST NOT persist `commission_withheld` and MUST NOT stamp `cash_declared_at`.
Close MUST NOT confirm allocations. A disabled seller MUST still be allowed to close an
existing `open` sheet. (Previously: The same close write persisted seller-declared
`cash_on_hand` and `commission_withheld`.)

#### Scenario: Open sheet closes to submitted

- GIVEN an open sheet with no `draft` members and optional draft allocations
- WHEN Seller Close runs without declaration amounts
- THEN `state` MUST become `submitted`
- AND `commission_withheld` MUST remain unchanged by that write
- AND `cash_declared_at` MUST remain unset
- AND every allocation MUST remain `draft`

#### Scenario: Empty members pass Seller Close

- GIVEN an open sheet with no member vouchers
- WHEN Seller Close runs
- THEN `state` MUST become `submitted`

#### Scenario: Draft members block Seller Close

- GIVEN an open sheet with at least one member in `draft`
- WHEN Seller Close runs
- THEN MUST raise `UserError` listing those members
- AND `state` MUST remain `open`

#### Scenario: Non-open Seller Close refused

- GIVEN a submitted, proposal, closed, or cancelled sheet
- WHEN Seller Close runs
- THEN MUST refuse and `state` MUST NOT become `submitted` from that action

### Requirement: MCP write close_collection_sheet

The system MUST expose `close_collection_sheet` via `@mcp_tool` on `muk_mcp.mixin`
(`category=write`, `registry=mcp`), method-discovered; MUST NOT add a DB tool record.
Calls MUST use the authenticated user and MUST NOT `sudo()`. Input MUST require integer
`seller_id` only. The tool MUST NOT accept `cash_on_hand`, `commission_withheld`,
`sheet_id`, `model`, `domain`, `fields`, `context`, or `order`. The tool MUST resolve
the seller's own `open` sheet on `env.company` and MUST run Seller Close on that sheet.
Callers that are not Collections Users (portal, public, plain internal) MUST receive
`AccessError`. Errors MUST be raised, never
returned as `{"error":...}`. On success the body MUST include
`{sheet:{id,name,state,seller_id,date_from,date_to,voucher_count}, cash:{collected}}`
with `state` `submitted` and MUST NOT include report bytes. `cash.collected` MUST equal
the sheet's collected cash total. Zero `open` sheets (including when only `submitted`
exists) MUST raise `UserError` and MUST NOT return `{sheet: null}`. More than one `open`
sheet MUST raise the existing multi-open `UserError`. A later MCP allocation create for
that seller MUST persist on a new `open` sheet. (Previously: Input required
`cash_on_hand` and `commission_withheld`; success omitted `cash.collected` and persisted
those amounts on close.)

#### Scenario: Internal seller closes the open sheet

- GIVEN a Collections User caller and an internal seller with exactly one `open`
  sheet
- WHEN `close_collection_sheet` runs with that `seller_id` and no declaration amounts
- THEN that sheet MUST be `submitted` without persisting declaration amounts
- AND the response `sheet.state` MUST be `submitted`
- AND the response MUST include `cash.collected`
- AND no `sudo()` MUST occur

#### Scenario: Amounts on close refused

- GIVEN a Collections User caller and an internal seller with exactly one `open`
  sheet
- WHEN `close_collection_sheet` is invoked with `cash_on_hand` or `commission_withheld`
- THEN MUST refuse
- AND that sheet MUST remain `open`

#### Scenario: Zero open sheets raise not null

- GIVEN an internal seller with no `open` sheet (none, or only `submitted` / `proposal`
  / `closed` / `cancelled`)
- WHEN `close_collection_sheet` runs with that `seller_id`
- THEN MUST raise `UserError`
- AND MUST NOT return `{sheet: null}`
- AND MUST NOT write declarations

#### Scenario: sheet_id rejected

- GIVEN a Collections User caller
- WHEN `close_collection_sheet` is invoked with a `sheet_id`
- THEN MUST refuse
- AND no sheet MUST change state

#### Scenario: Next write uses a new open sheet

- GIVEN the seller's sheet is `submitted` after close
- WHEN `create_collection_allocation` later runs for that seller with a valid payload
- THEN persist MUST be on a new `open` sheet
- AND the submitted sheet MUST remain `submitted`

#### Scenario: Close by a non-Collections User refused

- GIVEN a portal, public, or plain internal caller
- WHEN `close_collection_sheet` runs with any `seller_id`
- THEN MUST raise `AccessError`
- AND no sheet MUST change state

### Requirement: Declare Cash on submitted

Declare Cash MUST run only while `state` is `submitted` and MUST persist seller-declared
`commission_withheld` only. `action_declare_cash` MUST take `commission_withheld` and
MUST NOT take `cash_on_hand`, which follows by compute. It MUST stamp `cash_declared_at`
and `cash_declared_by`. It MUST be re-runnable: a later Declare Cash MUST replace the
withheld amount and MUST restamp declared-at/by. It MUST refuse `open`, `proposal`,
`closed`, and `cancelled` with no persist. The stored field name MUST remain
`cash_on_hand`. Declare Cash MUST NOT change sheet or allocation `state`. A disabled
seller MUST still be allowed to declare on an existing `submitted` sheet. Any
Collections User MAY run Declare Cash. A negative `commission_withheld` MUST be refused;
zero MUST be accepted. When the sheet already holds a `seller_commission` voucher, Declare
Cash MUST re-sync it to the new amount (see Confirm mints the seller commission
voucher). (Previously: Declare Cash took and persisted a seller-declared `cash_on_hand`
alongside `commission_withheld`.)

#### Scenario: Submitted sheet accepts Declare Cash

- GIVEN a submitted sheet carrying `cash` vouchers
- WHEN Declare Cash runs with `commission_withheld`
- THEN that amount MUST persist and `cash_on_hand` MUST drop by it
- AND `cash_declared_at` and `cash_declared_by` MUST be set
- AND `state` MUST remain `submitted`

#### Scenario: Declare Cash is re-runnable

- GIVEN a submitted sheet that already has a declared withheld amount
- WHEN Declare Cash runs with a different lawful amount
- THEN the new amount MUST persist and `cash_on_hand` MUST follow
- AND declared-at/by MUST be restamped

#### Scenario: Non-submitted Declare Cash refused

- GIVEN an open, proposal, closed, or cancelled sheet
- WHEN Declare Cash runs
- THEN MUST refuse
- AND stored amounts and `cash_declared_at` MUST be unchanged

#### Scenario: Disabled seller may still declare

- GIVEN a submitted sheet whose seller is later removed from the enabled list
- WHEN Declare Cash runs
- THEN the withheld amount MUST persist
- AND `state` MUST remain `submitted`

### Requirement: Confirm cash declaration gate

Confirm MUST refuse when the sheet's collected cash is greater than zero and
`cash_declared_at` is unset. Confirm MUST NOT change sheet or allocation `state` in that
case, and MUST NOT mint a `seller_commission` voucher. When collected cash is zero,
Confirm MUST NOT require Declare Cash. Member `validated_collections` rules in Confirm
review gate MUST still apply, and MUST be evaluated before the commission mint.
(Previously: Confirm had no mint, so the gate ordering was unobservable.)

#### Scenario: Undeclared cash blocks Confirm and the mint

- GIVEN a submitted sheet with collected cash greater than zero, unset
  `cash_declared_at`, and every member `validated_collections`
- WHEN Confirm runs
- THEN MUST raise `UserError`
- AND `state` MUST remain `submitted`
- AND every allocation MUST remain `draft`
- AND no `seller_commission` voucher MUST persist

#### Scenario: Zero cash Confirm without declaration

- GIVEN a submitted sheet with collected cash equal to zero, unset `cash_declared_at`,
  and every member `validated_collections`
- WHEN Confirm runs
- THEN `state` MUST become `proposal`
- AND every allocation MUST remain `draft`

#### Scenario: Declared cash allows Confirm

- GIVEN a submitted sheet with collected cash greater than zero, `cash_declared_at` set,
  and every member `validated_collections`
- WHEN Confirm runs
- THEN `state` MUST become `proposal`

### Requirement: MCP write declare_collection_cash

The system MUST expose `declare_collection_cash` via `@mcp_tool` on `muk_mcp.mixin`
(`category=write`, `registry=mcp`), method-discovered; MUST NOT add a DB tool record.
Calls MUST use the authenticated user and MUST NOT `sudo()`. Input MUST require integer
`seller_id` plus `commission_withheld` (decimal strings MUST be accepted; numbers MAY be
accepted). The tool MUST NOT accept `cash_on_hand`, `sheet_id`, `model`, `domain`,
`fields`, `context`, or `order`. The tool MUST resolve the seller's own `submitted`
sheet on `env.company` and MUST run Declare Cash on that sheet. It MUST NOT resolve via
the open-sheet helper and MUST NOT declare against an `open` sheet. Callers that are not
Collections Users (portal, public, plain internal) MUST receive `AccessError`. A negative
`commission_withheld` MUST be refused with a generic `UserError`; numeric zero MUST be
accepted. Errors MUST be raised, never returned as
`{"error":...}`. On success the body MUST include
`{sheet:{id,name,state,seller_id,date_from,date_to,voucher_count}}` with `state`
`submitted` and MUST NOT include report bytes. Zero `submitted` sheets MUST raise
`UserError` and MUST NOT return `{sheet: null}`. More than one `submitted` sheet MUST
raise `UserError`.

#### Scenario: Internal seller declares on the submitted sheet

- GIVEN a Collections User caller and an internal seller with exactly one `submitted`
  sheet
- WHEN `declare_collection_cash` runs with that `seller_id` and `commission_withheld`
- THEN that amount MUST persist on that sheet and `cash_on_hand` MUST follow by compute
- AND `cash_declared_at` MUST be set
- AND the response `sheet.state` MUST be `submitted`
- AND no `sudo()` MUST occur

#### Scenario: Zero submitted sheets raise not null

- GIVEN an internal seller with no `submitted` sheet (none, or only `open` / `proposal`
  / `closed` / `cancelled`)
- WHEN `declare_collection_cash` runs with that `seller_id`
- THEN MUST raise `UserError`
- AND MUST NOT return `{sheet: null}`
- AND MUST NOT write declarations

#### Scenario: sheet_id rejected

- GIVEN a Collections User caller
- WHEN `declare_collection_cash` is invoked with a `sheet_id`
- THEN MUST refuse
- AND no sheet MUST change declarations

#### Scenario: Open sheet is not the declare target

- GIVEN an internal seller with one `open` sheet and zero `submitted` sheets
- WHEN `declare_collection_cash` runs with that `seller_id`
- THEN MUST raise `UserError`
- AND the open sheet MUST NOT receive declarations

#### Scenario: Declare by a non-Collections User refused

- GIVEN a portal, public, or plain internal caller
- WHEN `declare_collection_cash` runs with any `seller_id`
- THEN MUST raise `AccessError`
- AND no sheet MUST change declarations

### Requirement: Frozen associate create freeze

When a sheet is `closed` or `cancelled`, create of business data on that sheet,
allocation, allocation line, receipt, receipt value, allocation revision, or cash
replacement MUST be refused. Audited Close, Cancel, and Reinstate, plus tracking and
chatter, MAY write. Member vouchers MUST freeze via the parent sheet. (Previously:
Freeze covered write and unlink, not create.)

#### Scenario: Frozen sheet refuses associate create

- GIVEN a closed or cancelled sheet
- WHEN create of an allocation, line, receipt, value, revision, or cash replacement runs
- THEN MUST refuse with no persist

#### Scenario: Proposal still allows allocation create

- GIVEN a proposal sheet
- WHEN an allocation is created lawfully
- THEN the create MUST persist

### Requirement: Confirm mints the seller commission voucher

`action_confirm` MUST mint the retained-commission instrument for each sheet it
confirms. The mint MUST run after the Confirm review gate and the Confirm cash
declaration gate have both passed, and MUST run before the `submitted → proposal` state
write, so that a refused Confirm leaves no voucher behind and the sheet is still
unfrozen when the voucher is created.

The mint MUST be a no-op when `commission_withheld` is zero or unset and no member
exists. With an existing `seller_commission` member, Confirm MUST NOT mint again and MUST
re-sync it to `commission_withheld`: reverse its replacement through reverse ledger rows,
rewrite `amount`, and replace cash again for only what the voucher does not already hold
on a receipt. A zero declaration leaves the voucher at zero (its ledger rows keep it).
That idempotency guard MUST key on the existing member voucher, not on replacement
ledger rows, because Cancel does not reverse replacements and
`Confirm → Cancel → Reinstate → Confirm` is a reachable path.

Otherwise the system MUST create exactly one `collection.voucher` with `document_type`
`seller_commission`, `amount` equal to `commission_withheld`, `seller_id` and `sheet_id`
of the sheet, a minted `document_id` matching `sc-<uuid4 hex>`, and `state`
`validated_seller`; then MUST write `validated_collections` inside the internal
`collection_audited_state` privileged scope to trigger cash replacement. The mint MUST
NOT `sudo()`. It
MUST post a chatter note on the sheet naming the voucher and amount.

Because the mint is system bookkeeping on an existing sheet rather than new seller work,
it MUST bypass `_assert_new_work` only inside the internal
`collection_seller_commission_mint` privileged scope; a context key of that name MUST
have no effect. Confirm MUST
therefore stay usable on a historical sheet whose seller has since been removed from
`enabled_seller_ids`. The bypass MUST NOT widen to ORM, UI, or MCP voucher create.

`commission_withheld` is writable only while the sheet is `submitted`, and Reinstate
re-opens `submitted`, so Declare Cash and the next Confirm MUST re-sync the voucher;
after Confirm the voucher `amount` and the declaration MUST agree. (Previously: no
reverse or adjustment path existed, so a declaration changed after Reinstate left the
voucher stale.)

#### Scenario: Confirm mints one commission voucher

- GIVEN a submitted sheet with `commission_withheld` 300, every member
  `validated_collections`, and `cash_declared_at` set
- WHEN Confirm runs
- THEN exactly one `seller_commission` voucher of amount 300 MUST persist on that sheet
- AND its `state` MUST be `validated_collections`
- AND its `document_id` MUST match `sc-<uuid4 hex>`
- AND `state` MUST become `proposal`

#### Scenario: Zero commission mints nothing

- GIVEN a submitted sheet with `commission_withheld` 0 and `cash_declared_at` set
- WHEN Confirm runs
- THEN no `seller_commission` voucher MUST persist
- AND `state` MUST become `proposal`

#### Scenario: Refused Confirm mints nothing

- GIVEN a submitted sheet with `commission_withheld` 300 and a member voucher that
  blocks the Confirm review gate
- WHEN Confirm runs
- THEN MUST raise `UserError`
- AND no `seller_commission` voucher MUST persist
- AND `state` MUST remain `submitted`

#### Scenario: Re-Confirm after Reinstate mints no second voucher

- GIVEN a sheet Confirmed with a `seller_commission`, then Cancelled, then Reinstated
- WHEN Confirm runs again
- THEN exactly one `seller_commission` voucher MUST exist on that sheet
- AND no additional `replace` ledger row MUST be created

#### Scenario: Disabled seller still allows Confirm

- GIVEN a submitted sheet with `commission_withheld` 300 whose `seller_id` is no longer
  in `enabled_seller_ids`
- WHEN Confirm runs
- THEN the `seller_commission` voucher MUST persist
- AND MUST NOT raise "Seller is not enabled for this company"

#### Scenario: Mint does not alter the cash arithmetic

- GIVEN a submitted sheet with `commission_withheld` 300 and `cash_on_hand` X
- WHEN Confirm mints and promotes the commission voucher
- THEN `cash_on_hand` MUST still equal X
- AND `cash_banked` MUST NOT include the commission amount

### Requirement: Entered in the ERP mark

Receipts are typed into the ERP by hand, so a closed sheet MUST carry readonly
`erp_entered_date` and `erp_entered_uid`. They MUST be set only by the manager-only
**Mark as Entered in the ERP** action (`closed` sheets only; a second mark refused) and
cleared only by **Unmark Entered in the ERP** and by Cancel; Reinstate MUST keep them
cleared. Each change MUST post a chatter note. A plain create or write of either field
MUST be refused. Search MUST offer **Pending ERP entry** (closed and not marked). The
connector's reserved amounts read the mark (see collection-allocations).

#### Scenario: Manager marks a closed sheet

- GIVEN a closed sheet with no mark
- WHEN a Collections Manager runs Mark as Entered in the ERP
- THEN `erp_entered_date` and `erp_entered_uid` MUST be set and a chatter note posted
- AND a Collections User running the same action MUST receive `AccessError`

#### Scenario: Cancel clears the mark

- GIVEN a marked closed sheet
- WHEN it is cancelled
- THEN the mark MUST be cleared with a chatter note

### Requirement: Unforgeable workflow guards

Audited state writes, gated creates (revisions, review snapshots, cash replacements, the
commission mint) and cascade unlinks MUST be allowed only inside the server-side
`collection_common.privileged(*scopes)` context variable, which nests and resets on
exit. A key of the same name in `env.context` (JSON-RPC `call_kw` or an MCP tool call)
MUST have no effect. (Previously: the guards read `env.context` keys, which any caller
could set.)

#### Scenario: Forged context key refused

- GIVEN a Collections User
- WHEN they write `state` on a sheet with `collection_sheet_audited_state` in the context
- THEN the write MUST be handled like any raw `state` write (manager check and the
  audited transition), never as an audited write
