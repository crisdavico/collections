# Delta for Collection Sheets

## ADDED Requirements

### Requirement: Seller Close from open

Seller Close MUST run only from `open` and MUST write `submitted`. The system MUST
refuse and MUST NOT change sheet or allocation `state` if any member voucher is `draft`;
the error MUST list those offenders. An empty member set MUST pass. Members in
`validated_seller` or `validated_collections` MUST pass. Seller Close MUST NOT require
an allocation and MUST NOT require every member to be `validated_collections`. The same
close write MUST persist seller-declared `cash_on_hand` and `commission_withheld`. Close
MUST NOT confirm allocations. A disabled seller MUST still be allowed to close an
existing `open` sheet.

#### Scenario: Open sheet closes to submitted

- GIVEN an open sheet with no `draft` members and optional draft allocations
- WHEN Seller Close runs with declared `cash_on_hand` and `commission_withheld`
- THEN `state` MUST become `submitted`
- AND those two amounts MUST persist on that write
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
`seller_id` and seller declaration amounts `cash_on_hand` and `commission_withheld`
(decimal strings MUST be accepted; numbers MAY be accepted). The tool MUST NOT accept
`sheet_id`, `model`, `domain`, `fields`, `context`, or `order`. The tool MUST resolve
the seller's own `open` sheet on `env.company` and MUST run Seller Close on that sheet.
Portal or public callers MUST receive `AccessError`. Errors MUST be raised, never
returned as `{"error":...}`. On success the body MUST include
`{sheet:{id,name,state,seller_id,date_from,date_to,voucher_count}}` with `state`
`submitted` and MUST NOT include report bytes. Zero `open` sheets (including when only
`submitted` exists) MUST raise `UserError` and MUST NOT return `{sheet: null}`. More
than one `open` sheet MUST raise the existing multi-open `UserError`. A later MCP
allocation create for that seller MUST persist on a new `open` sheet.

#### Scenario: Internal seller closes the open sheet

- GIVEN an internal caller and an internal seller with exactly one `open` sheet
- WHEN `close_collection_sheet` runs with that `seller_id` and declaration amounts
- THEN that sheet MUST be `submitted` with those amounts persisted
- AND the response `sheet.state` MUST be `submitted`
- AND no `sudo()` MUST occur

#### Scenario: Zero open sheets raise not null

- GIVEN an internal seller with no `open` sheet (none, or only `submitted` / `proposal`
  / `closed` / `cancelled`)
- WHEN `close_collection_sheet` runs with that `seller_id`
- THEN MUST raise `UserError`
- AND MUST NOT return `{sheet: null}`
- AND MUST NOT write declarations

#### Scenario: sheet_id rejected

- GIVEN an internal caller
- WHEN `close_collection_sheet` is invoked with a `sheet_id`
- THEN MUST refuse
- AND no sheet MUST change state

#### Scenario: Next write uses a new open sheet

- GIVEN the seller's sheet is `submitted` after close
- WHEN `create_collection_allocation` later runs for that seller with a valid payload
- THEN persist MUST be on a new `open` sheet
- AND the submitted sheet MUST remain `submitted`

#### Scenario: Non-internal close refused

- GIVEN a portal or public caller
- WHEN `close_collection_sheet` runs with any `seller_id`
- THEN MUST raise `AccessError`
- AND no sheet MUST change state

## MODIFIED Requirements

### Requirement: Sheet sequence identity

Each new sheet MUST get a unique persisted name `CS/<year>/<number>` via sequence code
`collection.sheet`. Numbering MUST be isolated per company. Sheets MUST have `state`
`open`, `submitted`, `proposal`, `closed`, or `cancelled` and MUST NOT have any other
workflow. The `submitted` key MUST display as Submitted by Seller. (Previously: Four
keys `open`, `proposal`, `closed`, `cancelled` only.)

#### Scenario: Sequence assigned on create

- GIVEN an internal user creates a sheet with a valid seller
- WHEN saved the first time
- THEN name MUST match `CS/<current-year>/<number>` and be unique
- AND `state` MUST be `open`

#### Scenario: Numbers isolated per company

- GIVEN companies A and B each create a new sheet
- WHEN both saves complete
- THEN each company's names MUST number independently of the other

### Requirement: Membership, dates, and deletion

A voucher MUST belong to at most one sheet. Membership MUST be editable while `open` or
`submitted` and frozen while `proposal`, `closed`, or `cancelled`. Empty sheets MUST be
allowed. `date_from`/`date_to` MUST be UTC min/max of member `create_date` (empty if no
members); MUST NOT use `received_date`. Unlink of an `open` sheet MUST unlink its draft
allocations first (vouchers MUST persist unassigned; MUST NOT be destroyed), then delete
the sheet. Unlink of a `submitted`, `proposal`, `closed`, or `cancelled` sheet MUST be
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

#### Scenario: Submitted membership add and remove

- GIVEN a submitted sheet
- WHEN an internal user adds or removes a same-seller member
- THEN membership MUST persist
- AND chatter MUST record the membership change

#### Scenario: Unlink submitted refused

- GIVEN a submitted sheet, empty or with members
- WHEN deleted
- THEN delete MUST fail and the sheet MUST remain `submitted`

### Requirement: Collection Sheets UI

Collections → Collection Sheets MUST provide list, form, and search with create and
edit. Form MUST show name, required `seller_id` (readonly after create), dates, a
non-clickable statusbar (`open`, `submitted`, `proposal`, `closed`, `cancelled`),
chatter/activity composer, and the three-page notebook. Header MUST show Seller Close
immediately before Confirm, plus Document Review, when saved and `open`; Document Review
and Confirm when `submitted`; Close and Cancel when `proposal`; Cancel when `closed`;
Reinstate when `cancelled`. Open and Reopen MUST NOT exist. Export XLSX MUST remain
available in every state. Membership MUST be editable when `open` or `submitted`.
List/search MUST show name, seller, dates, and `state`. (Previously: Four-state
statusbar; Confirm on `open`; Open when `cancelled`; membership only when `open`.)

#### Scenario: Menu and form behaviors

- GIVEN the module installed
- WHEN an internal user opens Collections → Collection Sheets then a form
- THEN list/search MUST show name, seller, dates, and `state`
- AND form MUST show name, required seller, dates, a non-clickable five-state statusbar
  including Submitted by Seller
- AND membership MUST be editable when open or submitted and readonly otherwise
- AND form MUST include chatter/activity composer

#### Scenario: Header actions by state

- GIVEN a saved sheet in each of the five states
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
post messages and schedule activities on a sheet. Seller Close, Confirm, Close, Cancel,
and Reinstate SHOULD be tracked in chatter. (Previously: Confirm, Close, Cancel, and
Open SHOULD be tracked.)

#### Scenario: Message persists on sheet

- GIVEN a saved collection sheet
- WHEN an operator posts a chatter comment
- THEN that comment MUST persist on the sheet thread

#### Scenario: Confirm tracks state in chatter

- GIVEN a submitted sheet
- WHEN an internal user Confirms it
- THEN chatter MUST record the state change from Submitted by Seller to Proposal

#### Scenario: Close tracks state in chatter

- GIVEN a proposal sheet
- WHEN an internal user Closes it
- THEN chatter MUST record the state change from Proposal to Closed

#### Scenario: Cancel tracks state in chatter

- GIVEN a submitted, proposal, or closed sheet
- WHEN an internal user Cancels it
- THEN chatter MUST record the state change to Cancelled

#### Scenario: Seller Close tracks state in chatter

- GIVEN an open sheet
- WHEN an internal user runs Seller Close
- THEN chatter MUST record the state change from Open to Submitted by Seller
- AND MUST record the declared `cash_on_hand` and `commission_withheld`

#### Scenario: Reinstate tracks state in chatter

- GIVEN a cancelled sheet
- WHEN an internal user Reinstates it
- THEN chatter MUST record the state change from Cancelled to Submitted by Seller

### Requirement: Saved-sheet header action opens Document Review

A saved `open` or `submitted` collection sheet MUST expose a header action that opens
Document Review with that sheet's mandatory identifier. The action MUST be available
when the current company's flag is ON and `state` is `open` or `submitted`, MUST be
hidden and refused when the flag is OFF or `state` is not `open` or `submitted`, and
MUST NOT open from an unsaved sheet. (Previously: Available only when saved and `open`.)

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

#### Scenario: Submitted sheet opens review

- GIVEN a saved submitted collection sheet and Document Review ON
- WHEN an internal user views the form or runs the header action
- THEN the action MUST be available
- AND it MUST open Document Review with that sheet identifier

#### Scenario: Non-reviewable sheet hides and refuses review

- GIVEN a saved proposal, closed, or cancelled sheet and Document Review ON
- WHEN an internal user views the form or invokes the header action
- THEN the action MUST be hidden and invocation MUST be refused

### Requirement: Open/closed lifecycle

Sheets MUST have required `state` `open`, `submitted`, `proposal`, `closed`, or
`cancelled`, default `open`. Existing `open` and `closed` rows MUST stay unchanged on
upgrade (MUST NOT remap). Legal transitions MUST be: `open` → Seller Close →
`submitted`; `submitted` → Confirm → `proposal`; `proposal` → Close → `closed`;
`submitted` or `proposal` or `closed` → Cancel → `cancelled`; `cancelled` → Reinstate →
`submitted`. Create MUST persist `open` and MUST reject any other `state`. `open` MUST
be reachable only via create. Close MUST succeed only from `proposal` and MUST confirm
every allocation then close. Cancel MUST succeed from `submitted`, `proposal`, or
`closed` and MUST return every allocation to `draft`. Reinstate MUST succeed from
`cancelled` without checking one-open, MUST write `submitted` (MUST NOT write `open`),
and MUST leave allocations `draft`. Confirm MUST run only from `submitted` and MUST NOT
confirm allocations. Any internal user MAY run those audited actions. Write of raw
`state` MUST be rejected except via Seller Close, Confirm, Close, Cancel, or Reinstate.
Reinstate of a historical cancelled sheet MUST remain allowed even if the seller is
later disabled. Open and Reopen MUST NOT exist. (Previously: Confirm from `open`; Open
from `cancelled` to `open` with a one-open check; Cancel from `proposal` or `closed`
only.)

#### Scenario: Default open on create

- GIVEN an internal user creates a sheet with a valid seller
- WHEN saved
- THEN `state` MUST be `open`

#### Scenario: Close when proposal

- GIVEN a proposal sheet with zero or more draft allocations
- WHEN an internal user Closes it
- THEN `state` MUST become `closed`
- AND every allocation MUST be `confirmed`

#### Scenario: Reinstate from cancelled to submitted

- GIVEN a cancelled sheet with draft allocations and that seller already has an `open`
  sheet in that company
- WHEN an internal user Reinstates it
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
- WHEN an internal user creates a sheet explicitly
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

### Requirement: Historical sheets remain operable

Existing sheets MUST stay visible and operable if their seller is later disabled. The
system MUST NOT hide or delete them for that reason. Seller Close from `open` and
Confirm from `submitted` MUST still succeed when their gates are met. (Previously:
Confirm from `open` MUST still succeed.)

#### Scenario: Disabled-seller sheet stays visible and confirmable

- GIVEN a submitted sheet whose seller is later removed from the enabled list
- WHEN an allowed-company user opens Collection Sheets and Confirms it (members
  eligible)
- THEN the sheet MUST still be listed
- AND `state` MUST become `proposal`
- AND the sheet MUST NOT be deleted

#### Scenario: Disabled-seller open sheet remains closeable

- GIVEN an open sheet whose seller is later removed from the enabled list
- WHEN Seller Close runs with declarations
- THEN `state` MUST become `submitted`

### Requirement: Sheet form notebook

Sheet form MUST show three notebook pages: Allocations, Vouchers, and Debt (MUST NOT
hide them). Allocations MUST list Reference (`name`), Customer (`partner_id`),
`total_debt`, `total_vouchers`, and Residual, and MUST NOT list `state` or
`total_applied`. Draft allocations MUST be addable, editable, and deletable when `open`,
`submitted`, or `proposal`, opening the allocation form. Vouchers MUST show all
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
`validated_collections`. An empty member set MUST pass. Missing designated proof,
Document Review OFF, or any member not `validated_collections` MUST block Confirm.
Confirm MUST set the sheet to `proposal` and MUST NOT confirm allocations. (Previously:
Confirm ran only from `open`.)

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

- GIVEN a submitted sheet with at least one member not `validated_collections`
- WHEN Confirm runs
- THEN MUST raise `UserError` and `state` MUST remain `submitted`

### Requirement: Four-state sheet editability

Allocations and debt `amount_applied` MUST be editable when the sheet is `open`,
`submitted`, or `proposal`. Voucher membership and voucher business fields MUST be
editable when `open` or `submitted`. Seller-declared `cash_on_hand` and
`commission_withheld` MUST be editable only when `open`. `commission_percent` MUST be
editable when the sheet is not `closed` or `cancelled`. When `closed` or `cancelled`,
those records MUST be read-only except chatter and PDF/XLSX. Confirm MUST NOT confirm
allocations. (Previously: Allocations, debt, and all three recon inputs editable when
`open` or `proposal`; membership only when `open`.)

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
