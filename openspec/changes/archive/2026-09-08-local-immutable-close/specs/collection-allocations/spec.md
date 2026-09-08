# Delta for collection-allocations

## ADDED Requirements

### Requirement: Frozen sheet refuses allocation create

When the sheet is `closed` or `cancelled`, create of allocations, allocation lines, and
allocation revisions MUST be refused. Audited Close, Cancel, and Reinstate MAY write
allocation `state` only. MUST NOT `sudo()`. (Previously: Freeze specified write and
unlink only.)

#### Scenario: Frozen sheet refuses allocation create

- GIVEN a closed or cancelled sheet
- WHEN an allocation is created via ORM or UI
- THEN MUST refuse with no persist

#### Scenario: Frozen sheet refuses line create

- GIVEN a closed or cancelled sheet with an allocation
- WHEN an allocation line is created
- THEN MUST refuse with no persist

#### Scenario: Frozen sheet refuses revision create

- GIVEN a closed or cancelled sheet
- WHEN an allocation revision is created
- THEN MUST refuse with no persist

## MODIFIED Requirements

### Requirement: Draft default and confirm-on-close invariant

Allocation `state` MUST be `draft` or `confirmed` only. Default MUST be `draft`. `draft`
MUST hold iff the sheet is `open`, `submitted`, `proposal`, or `cancelled`. `confirmed`
MUST hold iff the sheet is `closed`. MCP and ORM create MUST persist `draft` and
revision 1 on first persist. Confirm MUST NOT change allocation `state`. Close MUST
confirm every allocation then close the sheet and MUST NOT call `create_receipt`. Cancel
MUST return every allocation to `draft` (no-op if already `draft`). Reinstate from
Cancelled MUST leave allocations `draft`. Raw allocation `state` write MUST be refused
except audited Close, Cancel, or Reinstate transitions. A `UserError` that enumerates
draft sheet states MUST include `submitted`. (Previously: Close confirmed allocations
after connector `create_receipt` dispatch.)

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
- AND MUST NOT call `create_receipt`

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
