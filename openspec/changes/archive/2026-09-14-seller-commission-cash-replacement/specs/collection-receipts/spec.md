# Delta for Collection Receipts

## MODIFIED Requirements

### Requirement: Value-preserving cash replacement

Replacement MUST shrink a cash receipt value by X and grow the replacing voucher's value
by the same X on the same receipt so that receipt `total_values` and `amount_applied`
MUST remain unchanged. The replacing voucher MUST be a `seller_deposit` or a
`seller_commission`; both MUST use one shared engine driven by `CASH_REPLACEMENT_TYPES`.
Slices MUST be exact cents: the system MUST skip a slice that rounds to zero, and MUST
shrink a value only when the slice equals that value amount or leaves at least one cent.
Cash, replacing voucher, and receipt currencies MUST agree; a mismatch MUST refuse with
no persist.

The candidate walk MUST exclude `issued` receipts before the kind buckets. Bucket order
MUST be `quotation` then `invoice`; within a kind, earliest application due date then
invoice number; within a bucket, oldest-uploaded `cash` values first. Multiple replacing
vouchers MUST consume remaining cash in that order, so a `seller_deposit` and a
`seller_commission` on the same sheet MUST compete for one pool and MUST NOT
double-consume a value.

When a `seller_deposit` cannot spend its whole amount because replaceable cash ran out,
the remainder MUST be silently dropped as today. When a `seller_commission` cannot spend
its whole amount, the system MUST raise `UserError`: a commission larger than the cash
still held by the seller is an impossible declaration. When the sheet has no allocations
or no cash values, `seller_deposit` replacement MUST be a silent no-op. (Previously: The
engine matched `seller_deposit` only, walked `issued` receipts — where shrinking a value
raises and aborts the whole promotion — and always dropped an unspent remainder
silently.)

#### Scenario: Issued receipt skipped, not aborted

- GIVEN a sheet with an `issued` receipt holding a `cash` value and a `draft` receipt
  holding another `cash` value
- WHEN a `seller_deposit` reaches `validated_collections`
- THEN the `draft` receipt cash MUST be replaced
- AND the `issued` receipt MUST be untouched
- AND MUST NOT raise

#### Scenario: Commission replaces cash preserving totals

- GIVEN an invoice receipt funded by cash 100 with applied 70
- WHEN 30 of that cash is replaced by a `seller_commission`
- THEN that receipt `total_values` MUST remain 100
- AND `amount_applied` MUST remain 70
- AND one `replace` row MUST name the commission as `deposit_voucher_id`

#### Scenario: Deposit and commission share one cash pool

- GIVEN replaceable cash 100, a `seller_deposit` 70, and a `seller_commission` 30
- WHEN both reach `validated_collections`
- THEN total replaced MUST equal 100
- AND no cash value MUST be consumed twice

#### Scenario: Over-declared commission refused

- GIVEN replaceable cash 50 and a `seller_commission` 80
- WHEN that commission reaches `validated_collections`
- THEN MUST raise `UserError`

#### Scenario: Excess deposit still silently drops

- GIVEN replaceable cash 50 and a `seller_deposit` 80
- WHEN that deposit reaches `validated_collections`
- THEN 50 MUST be replaced
- AND MUST NOT raise

### Requirement: Cash replacement ledger

The system MUST persist immutable `collection.cash.replacement` rows with required
`receipt_id` (`ondelete` cascade), `cash_voucher_id`, `deposit_voucher_id` (`ondelete`
restrict), `amount` > 0, and `direction` `replace` or `reverse`. `deposit_voucher_id`
MUST hold the replacing voucher, which MAY be a `seller_deposit` or a
`seller_commission`; the column MUST NOT be renamed, and the replacing type MUST be
recovered by joining `deposit_voucher_id.document_type`. `sheet_id` and `currency_id`
MUST be related stored from the receipt. `company_id` MUST be related stored, required,
precomputed, and indexed. `created_by` and `created_at` MUST be required.
`replaced_amount` of a cash voucher MUST equal Σ `replace` minus Σ `reverse` for that
cash voucher. Create MUST be context-gated. Write MUST raise. Unlink MUST raise except
when a draft allocation parent-unlink cascades receipts. Internal users
(`base.group_user`) MUST have ACL `1,0,1,0`. Allowed-company `ir.rule`
`[('company_id', 'in', company_ids)]` MUST apply. Dedicated groups MUST NOT be added.
Calls MUST NOT `sudo()`. Cancel MUST NOT write `reverse` rows. Reinstate MUST NOT
re-replace. Because a commission is minted once by Confirm against a declaration that is
locked by the same transition, no code path MUST write a `reverse` row for a
`seller_commission`. (Previously: `deposit_voucher_id` could only be a
`seller_deposit`.)

#### Scenario: Commission replace row is distinguishable

- GIVEN a `replace` row created by a `seller_commission`
- WHEN `deposit_voucher_id.document_type` is read
- THEN it MUST be `seller_commission`
- AND `direction` MUST be `replace`

#### Scenario: Commission voucher survives its ledger rows

- GIVEN a `seller_commission` referenced by a `replace` row
- WHEN unlink of that voucher is attempted
- THEN MUST refuse on `ondelete` restrict
