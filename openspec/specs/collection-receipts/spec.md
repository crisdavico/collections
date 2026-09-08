# Collection Receipts Specification

## Purpose

ERP-facing receipt grouping on a collection allocation. Odoo groups voucher amounts by
document kind; the external ERP issues. At most one receipt per kind; applications are
derived from allocation lines.

## Requirements

### Requirement: Receipt header uniqueness

The system MUST persist `collection.receipt` with at most one header per
`(allocation_id, document_kind)`. `document_kind` MUST be `invoice` or `quotation` only.
A receipt MUST belong to exactly one allocation.

#### Scenario: Unique kind per allocation

- GIVEN an allocation with an invoice receipt
- WHEN a second invoice receipt is created for that allocation
- THEN MUST refuse
- AND a quotation receipt on the same allocation MUST persist

#### Scenario: Kind selection

- GIVEN a new receipt
- WHEN `document_kind` is omitted or set to a value other than `invoice` or `quotation`
- THEN omitted MUST default `invoice`; other values MUST refuse

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

### Requirement: Derived applications

Receipt applications MUST be the allocation `line_ids` with the same `document_kind` and
`amount_applied` > 0. The system MUST NOT persist a third model for receipt-to-document
pairing.

#### Scenario: Derived from lines

- GIVEN invoice lines with applied 50 and 0, and a quotation line applied 20
- WHEN the invoice receipt applications are read
- THEN only the applied-50 invoice line MUST appear
- AND MUST NOT create a junction row

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

### Requirement: Explicit receipts persist

When MCP create includes `receipts[]`, persist MUST write those values onto the matching
kind headers. Empty `applications[]` MUST still persist the receipt (on account).
Rebuild MUST use explicit values (MUST NOT FIFO-compat from invoices).

#### Scenario: Explicit invoice receipt values

- GIVEN create with an invoice receipt whose values equal the payment amount
- WHEN persist succeeds
- THEN exactly one invoice receipt MUST exist
- AND value amounts MUST match the payload

#### Scenario: Empty applications on account

- GIVEN create with one invoice receipt, full values, and `applications: []`
- WHEN persist succeeds
- THEN the allocation MUST still have that invoice receipt

### Requirement: Freeze and issued immutability

When the sheet is `closed` or `cancelled`, receipt and value create, write, and unlink
MUST be refused except audited Close (`draft` → `closed`), Cancel (`closed` → `draft`),
and Reinstate. A receipt in `issued` MUST be immutable (create of values, write, and
unlink refused) even if the allocation is later drafted. MUST NOT `sudo()`. (Previously:
Freeze refused write and unlink only; Close issued via `create_receipt`.)

#### Scenario: Closed sheet refuses receipt write

- GIVEN a closed or cancelled sheet with receipts
- WHEN receipt or value write or unlink is attempted
- THEN MUST refuse and stored rows MUST be unchanged

#### Scenario: Issued receipt immutable

- GIVEN an issued receipt
- WHEN write or unlink is attempted
- THEN MUST refuse

#### Scenario: Frozen sheet refuses receipt create

- GIVEN a closed or cancelled sheet
- WHEN receipt or value create is attempted
- THEN MUST refuse with no persist

#### Scenario: Cancel reopens closed not issued

- GIVEN a closed sheet with a `closed` receipt and an `issued` receipt
- WHEN Cancel runs
- THEN the `closed` receipt MUST become `draft` with no `external_receipt_id`
- AND the `issued` receipt MUST remain `issued`

### Requirement: Draft unlink cascades receipts

Unlink of a `draft` allocation MUST cascade receipts and values. Linked vouchers MUST
survive with `allocation_id` unset.

#### Scenario: Draft unlink drops receipts keeps vouchers

- GIVEN a draft allocation with receipts, values, and linked vouchers
- WHEN the allocation is deleted
- THEN receipts and values MUST be gone
- AND vouchers MUST persist unassigned

### Requirement: ERP identity and state

`external_receipt_id` MUST be unique among non-null values. Receipt `state` MUST be
`draft`, `closed`, or `issued` only. Default MUST be `draft`. Close MUST set local
`draft` receipts to `closed` and MUST NOT stamp `external_receipt_id`. Historical
`issued` receipts MUST keep `issued` and their external identity. Raw `state` write MUST
be rejected except audited `draft` → `closed` and `closed` → `draft`. (Previously:
`state` was `draft` or `issued` only; Close stamped `issued` via `create_receipt`.)

#### Scenario: Unique external id

- GIVEN a receipt with `external_receipt_id` E
- WHEN another receipt is stored with the same non-null E
- THEN MUST refuse
- AND a second null `external_receipt_id` MUST persist

#### Scenario: Close leaves draft receipts closed locally

- GIVEN a grouped draft receipt on a proposal sheet
- WHEN Close runs
- THEN `state` MUST be `closed` and `external_receipt_id` MUST remain unset
- AND MUST NOT call `create_receipt`

#### Scenario: Historical issued keeps identity

- GIVEN an issued receipt with non-null `external_receipt_id`
- WHEN Close, Cancel, or Reinstate runs on its sheet
- THEN `state` MUST remain `issued` and `external_receipt_id` MUST be unchanged

#### Scenario: Raw receipt state write rejected

- GIVEN a draft or closed receipt
- WHEN `state` is written except via audited Close or Cancel
- THEN the write MUST be rejected and stored `state` MUST be unchanged

### Requirement: Company ACL and no sudo

`company_id` on receipt and value MUST be required, stored, and indexed, and MUST match
the allocation company. Allowed-company `ir.rule` `[('company_id', 'in', company_ids)]`
MUST apply. Internal users (`base.group_user`) MUST have CRUD `1,1,1,1` on receipt and
value. Dedicated groups MUST NOT be added. Calls MUST NOT `sudo()`.

#### Scenario: Other-company hidden

- GIVEN a receipt in a company the user is not allowed
- WHEN they search receipts
- THEN that receipt MUST NOT be visible

#### Scenario: Internal CRUD without sudo

- GIVEN an authenticated internal user of an allowed company
- WHEN they create, read, write, or unlink a draft receipt in that company
- THEN ACL MUST allow it without `sudo()`
- AND a dedicated receipt group MUST NOT exist

### Requirement: Additive migration without backfill

Manifest MUST bump to `19.0.1.34.0`. Upgrade MUST add receipt and value tables
additively. Upgrade MUST NOT backfill receipts on existing allocations. Forbidden prior
migrate folders MUST NOT be added.

#### Scenario: Upgrade leaves old allocations empty

- GIVEN existing allocations at `19.0.1.33.0` with lines and vouchers
- WHEN upgraded to `19.0.1.34.0`
- THEN those allocations MUST have zero receipts
- AND new tables MUST exist

### Requirement: Read-mostly views

Receipt UI MUST be read-mostly. Historical `issued` and `external_receipt_id` MUST NOT
be stamped by operator form edit or by Close. Collection Receipts list, search, and form
MUST NOT expose `external_receipt_id`. The allocation form Receipts list MUST NOT expose
`external_receipt_id`. List tags MUST be `<list>` (MUST NOT `<tree>`). (Previously:
Issuance was owned by the ERP Close hand-off.)

#### Scenario: Form does not issue

- GIVEN a draft receipt on a draft allocation
- WHEN an operator opens the receipt or allocation form
- THEN they MUST NOT stamp `issued` or set `external_receipt_id` as a normal form edit
- AND Collection Receipts views and the allocation Receipts list MUST NOT show
  `external_receipt_id`

#### Scenario: Closed is a legal receipt state

- GIVEN a closed receipt after Close
- WHEN an operator opens the receipt form
- THEN `state` MUST show `closed`
- AND they MUST NOT stamp `issued` or `external_receipt_id`

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

### Requirement: Frozen sheet refuses cash replacement create

When the sheet is `closed` or `cancelled`, create of `collection.cash.replacement` MUST
be refused. Audited Close, Cancel, and Reinstate MUST NOT create replacement rows. MUST
NOT `sudo()`. (Previously: Replacement create was context-gated only.)

#### Scenario: Frozen sheet refuses replacement create

- GIVEN a closed or cancelled sheet
- WHEN a cash replacement create is attempted
- THEN MUST refuse with no persist

#### Scenario: Cancel still does not reverse

- GIVEN replacement rows on a closed sheet
- WHEN Cancel then Reinstate run
- THEN no replacement create MUST occur
- AND existing `replace` rows MUST remain
