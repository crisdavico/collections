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
`amount` > 0. UNIQUE(receipt, voucher) MUST hold. Sum of value amounts per voucher
across that allocation's receipts MUST be `<=` the voucher amount. The voucher's
`allocation_id` MUST equal the receipt's `allocation_id`.

#### Scenario: Split across two receipts

- GIVEN voucher V amount 100 on allocation A
- WHEN values 40 on A's invoice receipt and 60 on A's quotation receipt
- THEN both MUST persist

#### Scenario: Over-split or mismatched allocation refused

- GIVEN voucher V amount 100 on A, or V allocated to B
- WHEN values summing > 100 on A, amount `<=` 0, duplicate (receipt, V), or V linked to
  A's receipt while allocated to B
- THEN MUST refuse

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

#### Scenario: Surplus on account

- GIVEN values 100 and derived applied 70
- WHEN totals compute
- THEN `total_values` MUST be 100, `total_applied` 70, `amount_on_account` 30

#### Scenario: Equal totals allowed

- GIVEN values 50 and derived applied 50
- WHEN totals compute
- THEN `amount_on_account` MUST be 0
- AND persist MUST succeed

### Requirement: Compat create grouping

When MCP create has non-empty `invoices[]` and no splits, persist MUST create exactly
one `invoice` receipt. Unsplit voucher remainder MUST belong to no receipt. Empty
`invoices[]` MUST create zero receipts.

#### Scenario: Non-empty invoices no splits

- GIVEN create with invoices applying amounts and no splits
- WHEN persist succeeds
- THEN exactly one invoice receipt MUST exist
- AND unsplit leftover voucher amount MUST have no value row

#### Scenario: Empty invoices

- GIVEN create with `invoices: []` and no splits
- WHEN persist succeeds
- THEN the allocation MUST have zero receipts

### Requirement: Freeze and issued immutability

When the sheet is `closed` or `cancelled`, receipt and value write and unlink MUST be
refused. A receipt in `issued` MUST be immutable (write and unlink refused) even if the
allocation is later drafted. MUST NOT `sudo()`.

#### Scenario: Closed sheet refuses receipt write

- GIVEN a closed or cancelled sheet with receipts
- WHEN receipt or value write or unlink is attempted
- THEN MUST refuse and stored rows MUST be unchanged

#### Scenario: Issued receipt immutable

- GIVEN an issued receipt
- WHEN write or unlink is attempted
- THEN MUST refuse

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
`draft` or `issued` only. Default MUST be `draft`. After successful `create_receipt`,
the receipt MUST store that id and `issued`.

#### Scenario: Unique external id

- GIVEN a receipt with `external_receipt_id` E
- WHEN another receipt is stored with the same non-null E
- THEN MUST refuse
- AND a second null `external_receipt_id` MUST persist

#### Scenario: Draft until issued

- GIVEN a grouped draft receipt
- WHEN Close dispatches `create_receipt` successfully
- THEN `state` MUST be `issued` and `external_receipt_id` MUST be the returned id

### Requirement: Close dispatches create_receipt

Sheet Close MUST dispatch connector op `create_receipt` for each draft receipt that has
at least one value. Grouping MUST already exist from persist. The system MUST use the
company active connector. Failure MUST raise and MUST roll back Close (MUST NOT leave
issued ids without matching persist).

#### Scenario: Close issues draft receipts

- GIVEN a proposal sheet whose allocations have draft receipts with values
- WHEN Close runs
- THEN each such receipt MUST be dispatched via `create_receipt`
- AND on success those receipts MUST be `issued`

#### Scenario: Close with zero receipts

- GIVEN a proposal sheet whose allocations have zero receipts
- WHEN Close runs
- THEN Close MUST still confirm allocations and close the sheet
- AND MUST NOT dispatch `create_receipt`

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

Receipt UI MUST be read-mostly. Issuance (`external_receipt_id`, `issued`) MUST be owned
by the ERP hand-off, not by operator form edit. Collection Receipts list, search, and
form MUST NOT expose `external_receipt_id`. The allocation form Receipts list MUST NOT
expose `external_receipt_id`. List tags MUST be `<list>` (MUST NOT `<tree>`).

#### Scenario: Form does not issue

- GIVEN a draft receipt on a draft allocation
- WHEN an operator opens the receipt or allocation form
- THEN they MUST NOT stamp `issued` or set `external_receipt_id` as a normal form edit
- AND Collection Receipts views and the allocation Receipts list MUST NOT show
  `external_receipt_id`
