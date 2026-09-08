# Delta for Collection Receipts

## ADDED Requirements

### Requirement: Cash replacement ledger

The system MUST persist immutable `collection.cash.replacement` rows with required
`receipt_id` (`ondelete` cascade), `cash_voucher_id`, `deposit_voucher_id` (`ondelete`
restrict), `amount` > 0, and `direction` `replace` or `reverse`. `sheet_id` and
`currency_id` MUST be related stored from the receipt. `company_id` MUST be related
stored, required, precomputed, and indexed. `created_by` and `created_at` MUST be
required. `replaced_amount` of a cash voucher MUST equal Σ `replace` minus Σ `reverse`
for that cash voucher. Create MUST be context-gated. Write MUST raise. Unlink MUST raise
except when a draft allocation parent-unlink cascades receipts. Internal users
(`base.group_user`) MUST have ACL `1,0,1,0`. Allowed-company `ir.rule`
`[('company_id', 'in', company_ids)]` MUST apply. Dedicated groups MUST NOT be added.
Calls MUST NOT `sudo()`. Cancel MUST NOT write `reverse` rows. Reinstate MUST NOT
re-replace.
(Previously: No replacement ledger.)

#### Scenario: Replace row persists

- GIVEN a lawful replace of cash amount X by a `seller_deposit` on the same receipt
- WHEN replacement completes
- THEN one `replace` row MUST persist with that receipt, cash voucher, deposit, and X
- AND `replaced_amount` on the cash voucher MUST include X

#### Scenario: Write refused

- GIVEN an existing replacement row
- WHEN write is attempted
- THEN MUST refuse and stored fields MUST be unchanged

#### Scenario: Cancel does not reverse

- GIVEN replacement rows on a submitted sheet
- WHEN Cancel then Reinstate run
- THEN no `reverse` row MUST be created
- AND existing `replace` rows MUST remain
- AND replacement MUST NOT run again

#### Scenario: Other-company hidden and ACL

- GIVEN a replacement in a company the user is not allowed
- WHEN they search replacements
- THEN that row MUST NOT be visible
- AND `group_user` MUST be `1,0,1,0` without `sudo()` or a dedicated group

#### Scenario: Draft allocation unlink cascades replacements

- GIVEN a draft allocation whose receipts have replacement rows
- WHEN the allocation is deleted
- THEN those replacement rows MUST be gone
- AND linked vouchers MUST persist

### Requirement: Value-preserving cash replacement

Replacement MUST shrink a cash receipt value by X and grow a `seller_deposit` value by
the same X on the same receipt so that receipt `total_values` and `amount_applied` MUST
remain unchanged. Slices MUST be exact cents: the system MUST skip a slice that rounds
to zero, and MUST shrink a value only when the slice equals that value amount or leaves
at least one cent. Cash, deposit, and receipt currencies MUST agree; a mismatch MUST
refuse with no persist. Bucket order MUST be `quotation` then `invoice`; within a kind,
earliest application due date then invoice number; within a bucket, oldest-uploaded
`cash` values first. Multiple deposits MUST consume remaining cash in that order. When
the sheet has no allocations or no cash values, replacement MUST be a silent no-op.
`create_receipt` serialization is out of scope.
(Previously: No cash-to-deposit replacement.)

#### Scenario: Same-receipt totals unchanged

- GIVEN an invoice receipt funded by cash 100 with applied 70
- WHEN 40 of that cash is replaced by `seller_deposit`
- THEN that receipt `total_values` MUST remain 100
- AND `amount_applied` MUST remain 70

#### Scenario: Quotation before invoice

- GIVEN cash values on both quotation and invoice receipts
- WHEN a deposit smaller than combined cash is validated
- THEN the quotation cash MUST be replaced before invoice cash

#### Scenario: Zero slice skipped

- GIVEN a remaining cash amount that would round a slice to 0.00
- WHEN replacement runs
- THEN that slice MUST be skipped
- AND MUST NOT raise on amount `<=` 0
- AND receipt `total_values` MUST NOT drop below `amount_applied`

#### Scenario: Currency mismatch refused

- GIVEN cash and deposit vouchers whose currencies differ, or differ from the receipt
- WHEN replacement is attempted
- THEN MUST refuse with no persist

#### Scenario: No allocations is a no-op

- GIVEN a submitted sheet with a `seller_deposit` and zero allocations
- WHEN that deposit reaches `validated_collections`
- THEN no replacement row MUST be created
- AND the deposit MUST persist

## MODIFIED Requirements

### Requirement: Receipt values

The system MUST persist `collection.receipt.value` with required `voucher_id` and
`amount` > 0. UNIQUE(receipt, voucher) MUST hold. A value MUST persist only when the
voucher's sheet equals the receipt's sheet. Sum of ALL value amounts of the voucher
(MUST NOT filter by allocation) MUST be compared to the voucher amount with
`currency.compare_amounts` and MUST be `<=` the voucher amount. Same-sheet
cross-customer values MUST persist. Values whose voucher and receipt belong to different
sheets MUST be refused.
(Previously: Cap summed only that allocation's receipts; voucher `allocation_id` MUST
equal receipt `allocation_id`.)

#### Scenario: Split across two receipts

- GIVEN voucher V amount 100 on allocation A
- WHEN values 40 on A's invoice receipt and 60 on A's quotation receipt
- THEN both MUST persist

#### Scenario: Cross-customer same sheet accepted

- GIVEN voucher V amount 100 on sheet S, primarily on customer A
- WHEN values 40 on A's invoice receipt and 60 on customer B's invoice receipt on S
  persist
- THEN both MUST persist

#### Scenario: Cross-sheet refused

- GIVEN voucher V on sheet S1
- WHEN a value linking V to a receipt on sheet S2 is persisted
- THEN MUST refuse
- AND stored rows MUST be unchanged

#### Scenario: Over-split on one allocation refused

- GIVEN voucher V amount 100 on A
- WHEN values summing > 100 on A's receipts, or amount `<=` 0, or duplicate
  (receipt, V)
- THEN MUST refuse

#### Scenario: Over-cap across customers refused

- GIVEN voucher V amount 100 with 40 on A and 50 on B (same sheet)
- WHEN a further 20 on C is persisted
- THEN MUST refuse because 110 exceeds 100

#### Scenario: At-cap allowed

- GIVEN voucher V amount 100 with 40 on A
- WHEN 60 is persisted on B
- THEN both MUST persist

### Requirement: Receipt totals

Each receipt MUST expose `total_values` (sum of value amounts), `total_applied` (sum of
derived application amounts), and `amount_on_account` = `total_values − total_applied`.
`total_values >= total_applied` MUST be allowed. The system MUST NOT require equality.
Totals MUST recompute when stored allocation-line `amount_applied` changes. Recompute
MUST NOT raise because derived applications are a non-stored Many2many.
(Previously: Totals depended on the non-stored `line_ids` inverse, which raised Cannot
convert collection.receipt.line_ids to SQL when an existing `amount_applied` was
written.)

#### Scenario: Surplus on account

- GIVEN values 100 and derived applied 70
- WHEN totals compute
- THEN `total_values` MUST be 100, `total_applied` 70, `amount_on_account` 30

#### Scenario: Equal totals allowed

- GIVEN values 50 and derived applied 50
- WHEN totals compute
- THEN `amount_on_account` MUST be 0
- AND persist MUST succeed

#### Scenario: Existing applied write recomputes

- GIVEN a receipt with values and an existing applied line
- WHEN that line's `amount_applied` is written
- THEN totals MUST recompute
- AND MUST NOT raise a search conversion error
