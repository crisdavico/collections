# Delta for collection-allocations

Expose net allocatable balances on MCP `customer_debt` without changing gross connector
`balance` or existing summary totals. Write-path available math reuses the same
reservation lookup.

## ADDED Requirements

### Requirement: MCP customer_debt allocatable balances

MCP `customer_debt` MUST keep each invoice's gross connector `balance` and existing
summary fields (`total_balance`, `overdue_balance`, `open_balance`, `invoice_count`)
unchanged. It MUST add `invoices[].allocatable_balance` and summary
`total_allocatable_balance`, `open_allocatable_balance`, and
`overdue_allocatable_balance`.

Allocatable MUST be the gross connector `balance` minus ALL same-company
`collection.allocation.line.amount_applied` on allocations whose `state` is `draft` OR
`confirmed`, INCLUDING allocations on proposal, closed, or cancelled sheets that
`get_collection_allocation` does not expose. The result MUST be clamped at zero (MUST
NEVER be negative). No reservations MUST mean allocatable equals gross. Empty `invoices`
MUST still return the three allocatable summary keys as `0`. MUST NOT `sudo()`.

Write-path revalidation MUST reuse the same reservation lookup, MUST still exclude the
destination allocation, and MUST still raise `UserError`
`Applied amount exceeds available invoice balance.` when applied exceeds available.
`balance_seen` revalidation MUST still compare against GROSS connector `balance` via
`currency.compare_amounts` (MUST NOT switch that check to allocatable).

#### Scenario: Gross unchanged when no reservations

- GIVEN an enabled bound seller and outstanding overdue 100 plus open 50 with no draft
  or confirmed applications
- WHEN `customer_debt` runs
- THEN each invoice `balance` MUST stay 100 and 50
- AND each `allocatable_balance` MUST equal that gross
- AND summary `total_balance` / `overdue_balance` / `open_balance` MUST stay 150 / 100 /
  50
- AND `total_allocatable_balance` MUST be 150, `overdue_allocatable_balance` 100, and
  `open_allocatable_balance` 50

#### Scenario: Hidden draft on a proposal sheet reduces allocatable

- GIVEN a draft allocation on a **proposal** sheet applying 40 to the open invoice
  (`inv-bound-open`, gross 50) that `get_collection_allocation` does not expose
- WHEN `customer_debt` runs for identification `20-11111111-1`
- THEN the open invoice `balance` MUST stay 50 and `allocatable_balance` MUST be 10
- AND the overdue invoice MUST stay 100 / 100
- AND summary gross totals MUST stay 150 / 100 / 50
- AND `open_allocatable_balance` MUST be 10 and `total_allocatable_balance` MUST be 110

#### Scenario: Confirmed consumption on a closed sheet reduces allocatable

- GIVEN a confirmed allocation on a **closed** sheet applying 40 to the open invoice
- WHEN `customer_debt` runs
- THEN gross `balance` MUST stay 50 and `allocatable_balance` MUST be 10
- AND summary gross totals MUST be unchanged

#### Scenario: Over-reservation reports zero never negative

- GIVEN draft or confirmed applications whose sum exceeds the open invoice gross 50
- WHEN `customer_debt` runs
- THEN that invoice `allocatable_balance` MUST be 0
- AND MUST NOT be negative

#### Scenario: Write-path available still excludes destination

- GIVEN a hidden proposal-sheet draft reservation of the full open-invoice balance
- WHEN `create_collection_allocation` on a new open sheet applies 1 to that invoice
- THEN MUST raise `UserError` `Applied amount exceeds available invoice balance.` with
  no writes
- AND an amendment of the DESTINATION allocation MUST still exclude dest from reserved
  amounts
- AND `balance_seen` MUST still be revalidated against GROSS connector `balance` via
  `currency.compare_amounts`
