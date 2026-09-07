# Design: Expose allocatable customer debt

## Technical Approach

Keep connector `get_customer_debt` unchanged. After the MCP tool defaults
`document_kind`, annotate each outstanding invoice with net `allocatable_balance` and
add three summary totals. Reservations come from one batched private mixin helper shared
with write-path revalidation.

Allocatable = `max(0, gross connector balance − Σ amount_applied)` on same-company
`collection.allocation.line` whose `allocation_id.state` is `draft` or `confirmed`.
Sheet state is irrelevant: proposal, closed, and cancelled allocations still reserve.
`get_collection_allocation` stays open-sheet-only.

## Architecture Decisions

| Option                            | Tradeoff                                     | Decision                                                   |
| --------------------------------- | -------------------------------------------- | ---------------------------------------------------------- |
| Subtract only open-sheet drafts   | Matches get-allocation; understates reserved | **Reject** — write-path already counts all draft+confirmed |
| Replace gross `balance` with net  | Breaks `balance_seen` and existing clients   | **Reject** — add net keys; keep gross                      |
| Per-invoice `Line.search`         | Existing N+1 in revalidate                   | **Reject** — one `_read_group` (or one `search` + sum)     |
| Stored computed field on the line | Schema + migrate                             | **Reject** — response-only; manifest `19.0.1.40.1`         |

## Data Flow

```
customer_debt
  → connector.get_customer_debt (gross invoices + summary)
  → default document_kind
  → _collection_reserved_amounts(invoice ids)   # no dest exclude
  → invoices[].allocatable_balance = max(0, balance − reserved)
  → summary allocatable totals by state

create_collection_allocation revalidate
  → connector.get_customer_debt (GROSS balance_seen check)
  → _collection_reserved_amounts(ids, exclude_allocation_id=dest)
  → available = gross balance − reserved; applied > available → UserError
```

## File Changes

| File                                            | Action | Description                                                       |
| ----------------------------------------------- | ------ | ----------------------------------------------------------------- |
| `tools/collection_allocation.py`                | Modify | `@api.private` `_collection_reserved_amounts`; revalidate uses it |
| `tools/customer_debt.py`                        | Modify | Annotate invoices + summary; `@mcp_tool` description              |
| `__manifest__.py`                               | Modify | `19.0.1.40.1`                                                     |
| `tests/test_collection_mcp_customer_debt.py`    | Modify | Keys + reservation / over-reserve / zero-debt                     |
| `tests/test_collection_mcp_allocation.py`       | Modify | Hidden proposal reservation refuses new-open apply                |
| `tests/test_collection_company_migration.py`    | Modify | Version `19.0.1.40.1`; no `migrations/19.0.1.40.1/`               |
| `AGENTS.md`, `readme/DESCRIPTION.md`            | Modify | Payload + version pin                                             |
| `openspec/specs/collection-allocations/spec.md` | Modify | Merge ADDED requirement                                           |

No `migrations/19.0.1.40.1/`. Never `sudo()`.

## Interfaces / Contracts

```python
@api.model
@api.private
def _collection_reserved_amounts(
    self,
    external_invoice_ids,
    exclude_allocation_id=False,
) -> dict[str, float]:
```

Domain: `external_invoice_id in ids`, `company_id = env.company.id`,
`allocation_id.state in ('draft', 'confirmed')`. When `exclude_allocation_id` is a
truthy id, omit that allocation (amendments). One query:
`collection.allocation.line._read_group` grouped by `external_invoice_id` aggregating
`amount_applied:sum`. Missing ids → `0.0`.

`customer_debt` success (additive keys in **bold**):

```
{customer, summary: {
  total_balance, overdue_balance, open_balance, invoice_count,
  total_allocatable_balance, open_allocatable_balance,
  overdue_allocatable_balance
}, invoices: [{..., balance, allocatable_balance, document_kind}]}
```

Write-path UserError string MUST remain
`Applied amount exceeds available invoice balance.` `balance_seen` MUST still use
`currency.compare_amounts` against GROSS `fresh_invoices[id]['balance']`.

## Risks / Trade-offs

Over-applied draft+confirmed lines can exceed gross; clamp at zero so the read tool
never emits a negative. Write path still refuses a new apply that exceeds remaining
available (including hidden reservations).

## Migration / Rollback

No migration script. Revert the mixin/tool/docs/tests and restore `19.0.1.40.0`.

## Open Questions

None — destination exclusion and the UserError string stay as today.
