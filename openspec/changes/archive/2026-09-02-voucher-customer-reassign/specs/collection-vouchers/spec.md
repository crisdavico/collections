# Delta for Collection Vouchers

## ADDED Requirements

### Requirement: Partner write follows allocation

When `partner_id` changes, the system MUST compute `allocation_id` before persist
and MUST write `partner_id` and `allocation_id` in the same vals (per record when
outcomes differ). MUST NOT `sudo()`. While the sheet is `open`, any voucher state
MAY change Customer. Same-value `partner_id` MUST NOT recompute allocation.

Non-`confirmed` current allocation MUST refuse the move with no field change.
Confirmed source with projected residual (current residual minus voucher amount,
currency compare) `< 0` MUST refuse with no field change.

MUST attach the unique confirmed same-sheet allocation for the new partner when
projected residual satisfies residual rules; otherwise MUST leave unallocated and
MUST post chatter for that outcome.

#### Scenario: Same-write partner and allocation

- GIVEN an open-sheet voucher on confirmed allocation A (partner P) and unique
  confirmed same-sheet allocation B (partner Q) with attachable residual
- WHEN `partner_id` is written to Q
- THEN `partner_id` MUST be Q and `allocation_id` MUST be B
- AND both fields MUST persist in one write

#### Scenario: Fully applied source refused

- GIVEN an open-sheet voucher on a confirmed allocation whose residual is 0
- WHEN `partner_id` is written to another customer
- THEN the write MUST be refused
- AND `partner_id` and `allocation_id` MUST be unchanged

#### Scenario: Target attaches when residual holds

- GIVEN an open-sheet unallocated voucher and unique confirmed same-sheet
  allocation for Q with attachable residual
- WHEN `partner_id` is written to Q
- THEN `allocation_id` MUST become that allocation

#### Scenario: Target left unallocated when residual does not hold

- GIVEN an open-sheet voucher and no unique confirmed same-sheet allocation for Q
  that satisfies residual rules (including empty allocation, residual 0, no
  `residual_reason`)
- WHEN `partner_id` is written to Q
- THEN `partner_id` MUST be Q and `allocation_id` MUST be unset
- AND chatter MUST record that the voucher was left unallocated

#### Scenario: Non-confirmed source refused

- GIVEN an open-sheet voucher whose `allocation_id` is `validated` or `rejected`
- WHEN `partner_id` is written
- THEN the write MUST be refused
- AND `partner_id` and `allocation_id` MUST be unchanged

#### Scenario: Approved or rejected voucher may move

- GIVEN an open-sheet voucher in `approved` or `rejected` with no blocking residual
- WHEN `partner_id` is written to another customer
- THEN the write MUST succeed
- AND `state` MUST stay `approved` or `rejected`

### Requirement: Voucher partner-allocation constrain

When `allocation_id` is set, voucher `partner_id` MUST equal that allocation's
`partner_id` after any write of `partner_id` or `allocation_id`. A mismatch MUST
raise `UserError` with no persist.

#### Scenario: Constrain mismatch refused

- GIVEN a voucher and an allocation whose partners differ
- WHEN `allocation_id` is written without matching `partner_id` in the same vals
- THEN the write MUST be refused
- AND stored `partner_id` and `allocation_id` MUST be unchanged

### Requirement: Context-gated partner group_expand

`partner_id` MUST use a `group_expand` method (MUST NOT be boolean `True`). When
context `collection_reassign_sheet_id` is missing, invalid, or unreadable, expand
MUST return the identity groups. When that context names a readable sheet, expand
MUST return that sheet's allocation customers union member-voucher customers
(including empty allocation columns and stray voucher customers), ordered as
`res.partner` default order.

#### Scenario: Identity expand without context

- GIVEN Payment Vouchers grouped by Customer and no readable
  `collection_reassign_sheet_id`
- WHEN group expand runs
- THEN the returned groups MUST equal the identity groups
- AND empty allocation-only customers MUST NOT be added

#### Scenario: Empty allocation columns

- GIVEN reassign context for a readable sheet that has an allocation with no
  vouchers
- WHEN group expand runs
- THEN that allocation's customer MUST appear as a column

#### Scenario: Stray extra columns

- GIVEN reassign context for a readable sheet with a member voucher whose
  customer has no allocation on that sheet
- WHEN group expand runs
- THEN that voucher's customer MUST appear as a column
