# Delta for Collection Allocations

## MODIFIED Requirements

### Requirement: Draft default and confirm-on-close invariant

Allocation `state` MUST be `draft` or `confirmed` only. Default MUST be `draft`. `draft`
MUST hold iff the sheet is `open`, `submitted`, `proposal`, or `cancelled`. `confirmed`
MUST hold iff the sheet is `closed`. MCP and ORM create MUST persist `draft` and
revision 1 on first persist. Confirm MUST NOT change allocation `state`. Close MUST
confirm every allocation then close the sheet. Cancel MUST return every allocation to
`draft` (no-op if already `draft`). Reinstate from Cancelled MUST leave allocations
`draft`. Raw allocation `state` write MUST be refused except audited Close, Cancel, or
Reinstate transitions. A `UserError` that enumerates draft sheet states MUST include
`submitted`.
(Previously: `draft` iff sheet `open`, `proposal`, or `cancelled`; Open from Cancelled
left draft; Confirm from `open`.)

#### Scenario: Create defaults to draft

- GIVEN an open sheet
- WHEN an allocation is created via MCP or ORM
- THEN `state` MUST be `draft`
- AND first persist MUST store revision 1

#### Scenario: Draft legal on submitted

- GIVEN a submitted sheet
- WHEN an allocation is created or kept `draft` via ORM
- THEN `state` MUST be `draft`
- AND the sheet MUST remain `submitted`

#### Scenario: Close confirms then closes

- GIVEN a proposal sheet with draft allocations
- WHEN Close runs
- THEN every allocation MUST be `confirmed`
- AND the sheet MUST be `closed`

#### Scenario: Cancel drafts allocations

- GIVEN a submitted or proposal sheet with draft allocations, or a closed sheet with
  confirmed allocations
- WHEN Cancel runs
- THEN the sheet MUST be `cancelled`
- AND every allocation MUST be `draft`

#### Scenario: Reinstate from cancelled leaves draft

- GIVEN a cancelled sheet with draft allocations
- WHEN Reinstate runs
- THEN the sheet MUST be `submitted`
- AND every allocation MUST be `draft`

#### Scenario: Confirm does not confirm allocations

- GIVEN a submitted sheet with draft allocations
- WHEN Confirm runs
- THEN the sheet MUST be `proposal`
- AND every allocation MUST remain `draft`

#### Scenario: Invariant-breaking state write refused

- GIVEN an allocation whose `state` would not match its sheet (`draft` on closed, or
  `confirmed` on open, submitted, proposal, or cancelled)
- WHEN a non-audited `state` write is attempted
- THEN the write MUST be refused
- AND stored `state` MUST be unchanged

#### Scenario: Draft-state error names submitted

- GIVEN a write that would break the draft-versus-confirmed sheet-state pairing
- WHEN the system raises `UserError`
- THEN the message MUST name `submitted` among the draft sheet states

### Requirement: Cancelled and Closed allocation write guards

When the sheet is `closed` or `cancelled`, writes to allocation `line_ids` (including
`amount_applied`), `voucher_ids`, `receipt_ids`, `partner_id`, and `sheet_id` MUST be
refused even if the allocation is `draft`. Direct line `write` or `unlink` MUST be
refused. When the sheet is `open`, `submitted`, or `proposal`, draft allocations MUST
remain writable subject to other rules. MUST NOT `sudo()`.
(Previously: Draft allocations writable when the sheet is `open` or `proposal`.)

#### Scenario: Cancelled draft line write refused

- GIVEN a cancelled sheet with a draft allocation and debt lines
- WHEN `amount_applied` or other line fields are written via form or RPC
- THEN MUST refuse and stored values MUST be unchanged

#### Scenario: Closed allocation writes refused

- GIVEN a closed sheet with confirmed allocations
- WHEN `line_ids`, `voucher_ids`, `receipt_ids`, `partner_id`, or `sheet_id` are written
- THEN MUST refuse and stored values MUST be unchanged

#### Scenario: Proposal draft remains writable

- GIVEN a proposal sheet with a draft allocation
- WHEN `line_ids` or `voucher_ids` are written lawfully
- THEN the write MUST persist

#### Scenario: Submitted draft remains writable

- GIVEN a submitted sheet with a draft allocation
- WHEN `line_ids` or `voucher_ids` are written lawfully
- THEN the write MUST persist
- AND MUST NOT `sudo()`

#### Scenario: Cancelled line unlink refused

- GIVEN a debt line on a cancelled sheet
- WHEN the line is unlinked
- THEN MUST refuse and the line MUST remain

### Requirement: MCP open sheet is state open only

`create_collection_allocation` and `get_collection_allocation` MUST resolve sheets only
where `state` is `open`. A sheet in `submitted`, `proposal`, `closed`, or `cancelled`
MUST NOT satisfy lookup or auto-assign. A seller MAY obtain a new `open` sheet while
another sheet is `submitted` or `proposal`. MUST NOT `sudo()`.
(Previously: Non-open list omitted `submitted`.)

#### Scenario: Proposal does not occupy MCP open

- GIVEN a seller with one proposal sheet and zero open sheets in that company
- WHEN `get_collection_allocation` runs
- THEN the body MUST be `{allocation: null}` with zero writes

#### Scenario: Submitted does not occupy MCP open

- GIVEN a seller with one submitted sheet and zero open sheets in that company
- WHEN `get_collection_allocation` runs
- THEN the body MUST be `{allocation: null}` with zero writes
- AND MUST NOT `sudo()`

#### Scenario: New open while submitted exists

- GIVEN a seller with one submitted sheet and zero open sheets, `auto_create_sheet` ON
- WHEN `create_collection_allocation` runs with valid payload
- THEN a new `open` sheet MAY be created and allocation MUST persist `draft` on that
  open sheet
- AND the submitted sheet MUST remain `submitted`

#### Scenario: New open while proposal exists

- GIVEN a seller with one proposal sheet and zero open sheets, `auto_create_sheet` ON
- WHEN `create_collection_allocation` runs with valid payload
- THEN a new `open` sheet MAY be created and allocation MUST persist `draft` on that
  open sheet
- AND the proposal sheet MUST remain `proposal`

#### Scenario: Closed or cancelled not used as open

- GIVEN only a closed or cancelled sheet for that seller in that company
- WHEN `get_collection_allocation` runs
- THEN MUST return `{allocation: null}` with zero writes
