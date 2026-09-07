# Proposal: Expose allocatable customer debt

## Intent

Sellers (and Nebula) need net remaining invoice capacity on MCP `customer_debt`. Gross
connector `balance` stays as-is. Allocatable is that gross minus every same-company
draft or confirmed application — including allocations on proposal, closed, and
cancelled sheets that `get_collection_allocation` does not expose.

## Scope

### In Scope

- MCP `customer_debt`: `invoices[].allocatable_balance` plus summary
  `total_allocatable_balance`, `open_allocatable_balance`, `overdue_allocatable_balance`
- Batched private mixin helper for draft+confirmed reservations (replace the N+1
  `Line.search` in `_collection_allocation_revalidate`)
- Write-path available math still excludes the destination allocation and still raises
  `Applied amount exceeds available invoice balance.`
- `balance_seen` revalidation still compares to GROSS connector `balance`
- Manifest `19.0.1.40.1` (additive response-only; no migrate folder)
- Tests, OpenSpec, `AGENTS.md`, `readme/DESCRIPTION.md`

### Out of Scope

- Changing `get_collection_allocation` sheet lookup (open only)
- Switching `balance_seen` to allocatable
- Connector adapter payloads / SQLite
- Nebula agent tools or schemas
- `sudo()`, Copier, OCA, or `odoo/custom/src/odoo/`

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `collection-allocations`: `customer_debt` exposes net allocatable balances; write-path
  revalidation reuses the batched reservation lookup

## Approach

Extract one company-scoped `_read_group` (or single `search` + Python sum) of
`collection.allocation.line.amount_applied` for
`allocation_id.state in ('draft', 'confirmed')`. Annotate `customer_debt` after
connector fetch. Revalidate keeps destination exclusion and the same UserError. Clamp
allocatable at zero.

## Affected Areas

| Area                                 | Impact   | Description                                                            |
| ------------------------------------ | -------- | ---------------------------------------------------------------------- |
| `tools/collection_allocation.py`     | Modified | Batched `_collection_reserved_amounts`; revalidate uses it             |
| `tools/customer_debt.py`             | Modified | Annotate invoices + summary; MCP description                           |
| `__manifest__.py`                    | Modified | `19.0.1.40.1`; no `migrations/19.0.1.40.1/`                            |
| MCP tests                            | Modified | Allocatable payload; hidden/closed/over-reserve; write-path regression |
| `AGENTS.md`, `readme/DESCRIPTION.md` | Modified | Success shape and version pin                                          |

## Risks

| Risk                                        | Likelihood | Mitigation                                           |
| ------------------------------------------- | ---------- | ---------------------------------------------------- |
| Clients assume gross == allocatable         | Med        | Keep gross keys; add net keys only                   |
| Hidden proposal/closed reservations ignored | High       | Domain is allocation state, not sheet state          |
| N+1 leftover in revalidate                  | Med        | One batched helper, never search in the invoice loop |
| Diff > 400 lines                            | Low        | Response-only + tests; no migrate                    |

## Rollback Plan

Revert to `19.0.1.40.0`. No stored schema change.

## Dependencies

None outside `collection/`.

## Success Criteria

- [ ] Gross `balance` and existing summary totals unchanged
- [ ] Allocatable = max(0, gross − all same-company draft+confirmed applied)
- [ ] Hidden proposal draft and closed confirmed both reduce allocatable
- [ ] Over-reservation reports 0, never negative
- [ ] Write-path still excludes destination and still raises the same UserError
- [ ] `balance_seen` still vs GROSS `balance`; no `migrations/19.0.1.40.1/`
