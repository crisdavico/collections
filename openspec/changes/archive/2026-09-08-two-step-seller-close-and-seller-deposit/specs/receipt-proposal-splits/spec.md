# Delta for Receipt Proposal Splits

## ADDED Requirements

### Requirement: Replaced cash and remittance board lock

Proposal free amount MUST be `amount − assigned − replaced_amount`. A voucher whose free
amount is `<=` 0 MUST NOT appear in the unassigned pool. `seller_deposit` remittance
vouchers MUST NOT be pool-draggable and MUST NOT receive `allocation_id` from board owner
sync. Replaced cash MUST keep its `allocation_id` after board mutations that do not
assign a remaining free share. Largest-share owner and partner-identity relax MUST remain
in this addon.
(Previously: Free amount was `amount − assigned` only, so replaced cash reappeared in
the pool and remittance could be dragged onto a customer.)

#### Scenario: Replaced cash leaves the pool

- GIVEN a cash voucher whose `replaced_amount` equals its `amount`
- WHEN the proposal board payload is built
- THEN that voucher MUST NOT appear in the unassigned pool

#### Scenario: Partial replace remains only for the free remainder

- GIVEN a cash voucher amount 100, assigned 0, replaced 40
- WHEN the proposal board payload is built
- THEN free amount MUST be 60
- AND the voucher MAY appear in the pool only for 60

#### Scenario: Remittance is not pool-draggable

- GIVEN a `seller_deposit` with free amount greater than zero
- WHEN a board transfer from the pool targets a customer
- THEN MUST refuse
- AND that voucher `allocation_id` MUST remain unset

#### Scenario: Replaced cash keeps allocation_id

- GIVEN replaced cash with `allocation_id` set to customer A and zero remaining values
- WHEN a board mutation runs owner sync
- THEN `allocation_id` MUST remain A's allocation
- AND MUST NOT be cleared

## REMOVED Requirements

### Requirement: Same-sheet split

(Reason: Sheet-boundary receipt values now belong in core `collection-receipts` so
replacement and the board share one invariant.)
(Migration: Replaced by Collection Receipts requirement Receipt values. Satellite
constraint overrides MUST be deleted; `_proposal_card_payload` MAY remain.)

### Requirement: Sheet-wide split cap

(Reason: Sheet-wide voucher split cap now belongs in core `collection-receipts`.)
(Migration: Replaced by Collection Receipts requirement Receipt values. Do not copy the
per-voucher search loop into core; core MUST keep one batched search.)
