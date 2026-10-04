# Delta for Collection Sheets

## ADDED Requirements

### Requirement: Declare Cash on submitted

Declare Cash MUST run only while `state` is `submitted` and MUST persist seller-declared
`cash_on_hand` and `commission_withheld`. It MUST stamp `cash_declared_at` and
`cash_declared_by`. It MUST be re-runnable: a later Declare Cash MUST replace those two
amounts and MUST restamp declared-at/by. It MUST refuse `open`, `proposal`, `closed`,
and `cancelled` with no persist. The persisted field name MUST remain `cash_on_hand`.
Declare Cash MUST NOT change sheet or allocation `state`. A disabled seller MUST still
be allowed to declare on an existing `submitted` sheet. Any internal user MAY run
Declare Cash.

#### Scenario: Submitted sheet accepts Declare Cash

- GIVEN a submitted sheet
- WHEN Declare Cash runs with `cash_on_hand` and `commission_withheld`
- THEN those two amounts MUST persist
- AND `cash_declared_at` and `cash_declared_by` MUST be set
- AND `state` MUST remain `submitted`

#### Scenario: Declare Cash is re-runnable

- GIVEN a submitted sheet that already has declared amounts
- WHEN Declare Cash runs with different lawful amounts
- THEN the new amounts MUST persist
- AND declared-at/by MUST be restamped

#### Scenario: Non-submitted Declare Cash refused

- GIVEN an open, proposal, closed, or cancelled sheet
- WHEN Declare Cash runs
- THEN MUST refuse
- AND stored amounts and `cash_declared_at` MUST be unchanged

#### Scenario: Disabled seller may still declare

- GIVEN a submitted sheet whose seller is later removed from the enabled list
- WHEN Declare Cash runs
- THEN the two amounts MUST persist
- AND `state` MUST remain `submitted`

### Requirement: Confirm cash declaration gate

Confirm MUST refuse when the sheet's collected cash is greater than zero and
`cash_declared_at` is unset. Confirm MUST NOT change sheet or allocation `state` in that
case. When collected cash is zero, Confirm MUST NOT require Declare Cash. Member
`validated_collections` rules in Confirm review gate MUST still apply.

#### Scenario: Undeclared cash blocks Confirm

- GIVEN a submitted sheet with collected cash greater than zero and unset
  `cash_declared_at`, and every member `validated_collections`
- WHEN Confirm runs
- THEN MUST raise `UserError`
- AND `state` MUST remain `submitted`
- AND every allocation MUST remain `draft`

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
`seller_id` plus `cash_on_hand` and `commission_withheld` (decimal strings MUST be
accepted; numbers MAY be accepted). The tool MUST NOT accept `sheet_id`, `model`,
`domain`, `fields`, `context`, or `order`. The tool MUST resolve the seller's own
`submitted` sheet on `env.company` and MUST run Declare Cash on that sheet. It MUST NOT
resolve via the open-sheet helper and MUST NOT declare against an `open` sheet. Portal
or public callers MUST receive `AccessError`. Errors MUST be raised, never returned as
`{"error":...}`. On success the body MUST include
`{sheet:{id,name,state,seller_id,date_from,date_to,voucher_count}}` with `state`
`submitted` and MUST NOT include report bytes. Zero `submitted` sheets MUST raise
`UserError` and MUST NOT return `{sheet: null}`. More than one `submitted` sheet MUST
raise `UserError`.

#### Scenario: Internal seller declares on the submitted sheet

- GIVEN an internal caller and an internal seller with exactly one `submitted` sheet
- WHEN `declare_collection_cash` runs with that `seller_id` and declaration amounts
- THEN those amounts MUST persist on that sheet
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

- GIVEN an internal caller
- WHEN `declare_collection_cash` is invoked with a `sheet_id`
- THEN MUST refuse
- AND no sheet MUST change declarations

#### Scenario: Open sheet is not the declare target

- GIVEN an internal seller with one `open` sheet and zero `submitted` sheets
- WHEN `declare_collection_cash` runs with that `seller_id`
- THEN MUST raise `UserError`
- AND the open sheet MUST NOT receive declarations

#### Scenario: Non-internal declare refused

- GIVEN a portal or public caller
- WHEN `declare_collection_cash` runs with any `seller_id`
- THEN MUST raise `AccessError`
- AND no sheet MUST change declarations

## MODIFIED Requirements

### Requirement: Seller Close from open

Seller Close MUST run only from `open` and MUST write `submitted`. The system MUST
refuse and MUST NOT change sheet or allocation `state` if any member voucher is `draft`;
the error MUST list those offenders. An empty member set MUST pass. Members in
`validated_seller` or `validated_collections` MUST pass. Seller Close MUST NOT require
an allocation and MUST NOT require every member to be `validated_collections`. Seller
Close MUST NOT persist `cash_on_hand` or `commission_withheld` and MUST NOT stamp
`cash_declared_at`. Close MUST NOT confirm allocations. A disabled seller MUST still be
allowed to close an existing `open` sheet. (Previously: The same close write persisted
seller-declared `cash_on_hand` and `commission_withheld`.)

#### Scenario: Open sheet closes to submitted

- GIVEN an open sheet with no `draft` members and optional draft allocations
- WHEN Seller Close runs without declaration amounts
- THEN `state` MUST become `submitted`
- AND `cash_on_hand` and `commission_withheld` MUST remain unchanged by that write
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
Portal or public callers MUST receive `AccessError`. Errors MUST be raised, never
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

- GIVEN an internal caller and an internal seller with exactly one `open` sheet
- WHEN `close_collection_sheet` runs with that `seller_id` and no declaration amounts
- THEN that sheet MUST be `submitted` without persisting declaration amounts
- AND the response `sheet.state` MUST be `submitted`
- AND the response MUST include `cash.collected`
- AND no `sudo()` MUST occur

#### Scenario: Amounts on close refused

- GIVEN an internal caller and an internal seller with exactly one `open` sheet
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
- AND MUST NOT require declared `cash_on_hand` or `commission_withheld` on that write

#### Scenario: Declare Cash tracks declarations in chatter

- GIVEN a submitted sheet
- WHEN Declare Cash runs with `cash_on_hand` and `commission_withheld`
- THEN chatter MUST record those two amounts

#### Scenario: Reinstate tracks state in chatter

- GIVEN a cancelled sheet
- WHEN an internal user Reinstates it
- THEN chatter MUST record the state change from Cancelled to Submitted by Seller

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

### Requirement: Four-state sheet editability

Allocations and debt `amount_applied` MUST be editable when the sheet is `open`,
`submitted`, or `proposal`. Voucher membership and voucher business fields MUST be
editable when `open` or `submitted`. Seller-declared `cash_on_hand` and
`commission_withheld` MUST be editable only when `submitted`. `commission_percent` MUST
be editable when the sheet is not `closed` or `cancelled`. When `closed` or `cancelled`,
those records MUST be read-only except chatter and PDF/XLSX. Confirm MUST NOT confirm
allocations. (Previously: Seller-declared `cash_on_hand` and `commission_withheld` MUST
be editable only when `open`.)

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
- WHEN `cash_on_hand` or `commission_withheld` is written lawfully
- THEN the writes MUST persist

#### Scenario: Open seller declarations refused

- GIVEN an open sheet
- WHEN `cash_on_hand` or `commission_withheld` is written
- THEN MUST refuse and stored values MUST be unchanged
