# Delta for collection-vouchers

## MODIFIED Requirements

### Requirement: Voucher lifecycle

States MUST be `pending`, `approved`, and `rejected`. Approve and Reject MUST apply only
from `pending` and MUST NOT alter terminal states. Delete MUST be allowed only when
`state` is `pending` and `allocation_id` is unset or `draft`. Pending plus `confirmed`
MUST be refused. Removing a pending voucher from a draft allocation MUST refuse when
projected residual (current residual minus voucher amount, currency compare) is `< 0`
and MUST NOT auto-edit invoice lines. Any user-driven change from `pending` to
`approved` or `rejected` (including kanban drag) MUST record reviewer and review time
the same as Approve/Reject. Approve/Reject on Payment Vouchers MUST remain available
whether Document Review is ON or OFF. Review queue RPCs remain governed by
`document-review`. Confidence, per-field stamps, and reviewer-note persistence MUST
NOT be required.
(Previously: Delete allowed for any pending voucher; allocated unlink was refused.)

#### Scenario: Approve from pending

- GIVEN a voucher in `pending`
- WHEN approved
- THEN `state` MUST become `approved`
- AND reviewer and review time MUST be recorded

#### Scenario: Reject from pending

- GIVEN a voucher in `pending`
- WHEN rejected
- THEN `state` MUST become `rejected`
- AND reviewer and review time MUST be recorded

#### Scenario: Terminal states block transitions

- GIVEN a voucher in `approved` or `rejected`
- WHEN Approve or Reject is attempted
- THEN `state` MUST NOT change

#### Scenario: Delete from pending

- GIVEN a voucher in `pending` with allocation unset or `draft` and projected
  residual ≥ 0
- WHEN deleted
- THEN the system MUST allow the delete

#### Scenario: Delete blocked when not pending

- GIVEN a voucher in `approved` or `rejected`
- WHEN deleted
- THEN the system MUST refuse the delete

#### Scenario: Delete pending on confirmed allocation refused

- GIVEN a pending voucher on a confirmed allocation
- WHEN deleted
- THEN the system MUST refuse the delete
- AND the voucher and allocation MUST remain

#### Scenario: Delete pending on draft with negative residual refused

- GIVEN a pending voucher on a draft allocation whose residual would become
  `< 0`
- WHEN deleted
- THEN the system MUST refuse the delete
- AND invoice lines MUST NOT be auto-edited

#### Scenario: Kanban drag is audited

- GIVEN a `pending` voucher on a state-grouped kanban
- WHEN an internal user drags it to `approved` or `rejected`
- THEN `state` MUST change to that value
- AND reviewer and review time MUST be recorded as for Approve/Reject

#### Scenario: Approve and Reject remain when review is off

- GIVEN Document Review is OFF and a voucher in `pending`
- WHEN Approve or Reject is used on Payment Vouchers
- THEN `state` MUST become `approved` or `rejected` respectively

#### Scenario: Default pending

- GIVEN a newly created voucher
- WHEN `state` is read without a prior decision
- THEN `state` MUST be `pending`

### Requirement: Voucher allocation membership

Each voucher MAY have `allocation_id`. Write of `allocation_id` MUST be refused
unless current and target (if set) are both `draft` or unset. Unlink MUST be
allowed when `state` is `pending` and `allocation_id` is unset or `draft`,
subject to residual projection. Unlink MUST be refused when allocation is
`confirmed`. Removing a voucher from a draft allocation MUST project residual
as current residual minus that voucher's amount (currency compare). If
projected residual is `< 0`, unlink MUST be refused; invoice lines MUST NOT be
auto-edited.
(Previously: Write required current and target confirmed or unset; unlink
refused while allocated.)

#### Scenario: allocation_id write on draft or unset

- GIVEN current and target are both `draft` or unset
- WHEN `allocation_id` is written
- THEN the write MUST succeed

#### Scenario: Confirmed membership write refused

- GIVEN current or target is `confirmed`
- WHEN `allocation_id` is written
- THEN the write MUST be refused
- AND stored `allocation_id` MUST be unchanged

#### Scenario: Pending unlink on draft or unset

- GIVEN a pending voucher with allocation unset or `draft` and projected
  residual ≥ 0
- WHEN deleted
- THEN the system MUST allow the delete

#### Scenario: Draft residual underflow refuses unlink

- GIVEN a pending voucher on a draft allocation whose residual would become
  `< 0`
- WHEN the voucher is deleted
- THEN unlink MUST be refused
- AND invoice lines MUST NOT be auto-edited

### Requirement: Partner write follows allocation

When `partner_id` changes, the system MUST compute `allocation_id` before persist
and MUST write `partner_id` and `allocation_id` in the same vals (per record when
outcomes differ). MUST NOT `sudo()`. While the sheet is `open`, any voucher state
MAY change Customer. Same-value `partner_id` MUST NOT recompute allocation.

`confirmed` current allocation MUST refuse the move with no field change.
Draft source with projected residual (current residual minus voucher amount,
currency compare) `< 0` MUST refuse with no field change.

MUST attach the unique draft same-sheet allocation for the new partner when
projected residual satisfies residual rules; otherwise MUST leave unallocated and
MUST post chatter for that outcome.
(Previously: Attach/detach used confirmed allocations; non-confirmed
`validated`/`rejected` sources refused the move.)

#### Scenario: Same-write partner and allocation

- GIVEN an open-sheet voucher on draft allocation A (partner P) and unique
  draft same-sheet allocation B (partner Q) with attachable residual
- WHEN `partner_id` is written to Q
- THEN `partner_id` MUST be Q and `allocation_id` MUST be B
- AND both fields MUST persist in one write

#### Scenario: Fully applied source refused

- GIVEN an open-sheet voucher on a draft allocation whose residual is 0
- WHEN `partner_id` is written to another customer
- THEN the write MUST be refused
- AND `partner_id` and `allocation_id` MUST be unchanged

#### Scenario: Target attaches when residual holds

- GIVEN an open-sheet unallocated voucher and unique draft same-sheet
  allocation for Q with attachable residual
- WHEN `partner_id` is written to Q
- THEN `allocation_id` MUST become that allocation

#### Scenario: Target left unallocated when residual does not hold

- GIVEN an open-sheet voucher and no unique draft same-sheet allocation for Q
  that satisfies residual rules (including empty allocation, residual 0, no
  `residual_reason`)
- WHEN `partner_id` is written to Q
- THEN `partner_id` MUST be Q and `allocation_id` MUST be unset
- AND chatter MUST record that the voucher was left unallocated

#### Scenario: Confirmed source refused

- GIVEN an open-sheet voucher whose `allocation_id` is `confirmed`
- WHEN `partner_id` is written
- THEN the write MUST be refused
- AND `partner_id` and `allocation_id` MUST be unchanged

#### Scenario: Approved or rejected voucher may move

- GIVEN an open-sheet voucher in `approved` or `rejected` with no blocking residual
- WHEN `partner_id` is written to another customer
- THEN the write MUST succeed
- AND `state` MUST stay `approved` or `rejected`
