# Delta for Collection Allocations

## ADDED Requirements

### Requirement: Source detach residual refuse

When a voucher would leave a `confirmed` allocation, the system MUST project residual as
current residual minus that voucher's amount (currency compare). If projected residual
is `< 0`, the system MUST refuse the move with no `partner_id` or `allocation_id`
change. Fully applied sources MUST be refused. The system MUST NOT unallocate the
voucher to avoid a negative residual.

#### Scenario: Fully applied source detach refused

- GIVEN a confirmed allocation with residual 0 and a linked voucher
- WHEN that voucher is moved off the allocation (including via `partner_id` write)
- THEN the move MUST be refused
- AND allocation `voucher_ids` MUST be unchanged

#### Scenario: Negative projected residual refused

- GIVEN a confirmed allocation whose residual is less than the voucher amount
- WHEN that voucher is detached
- THEN the move MUST be refused
- AND residual MUST be unchanged

### Requirement: Partner match after voucher write

Every allocated voucher's `partner_id` MUST equal the allocation `partner_id` after
voucher `partner_id` or `allocation_id` writes, not only after allocation `partner_id`
or `voucher_ids` writes. A mismatch MUST be refused with no persist.

#### Scenario: Voucher partner write mismatch refused

- GIVEN a voucher linked to an allocation for partner P
- WHEN `partner_id` is written to Q without a matching `allocation_id` in the same vals
- THEN the write MUST be refused
- AND the voucher MUST remain on P and that allocation

#### Scenario: Same-write matching partner and allocation

- GIVEN a voucher on allocation A (partner P) and confirmed same-sheet allocation B
  (partner Q) with attachable residual
- WHEN `partner_id` is written to Q with `allocation_id` B in the same vals
- THEN partner match MUST hold
- AND the voucher MUST belong to B
