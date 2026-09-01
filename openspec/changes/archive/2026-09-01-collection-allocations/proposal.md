# Proposal: Collection Allocations

Closed plan used instead of a question round.

## Intent

Sellers persist a validated allocation of sheet vouchers against external
invoices. Odoo enforces invariants and revalidates read-only ERP debt;
back-office validates or rejects.

**User impact:** one allocation per customer per sheet via MCP; operators see
totals, residual, chatter; allocated sheets cannot be deleted.

## Scope

### In Scope

- `collection.allocation` / `.line` / `.revision`; `CA/` sequence; ACL; `ir.rule`
- MCP `create_collection_allocation` (create/amend; `request_id` idempotency)
- Voucher `allocation_id` guards; sheet notebook; unlink restrict when allocated
- Back-office validate/reject; stacked TDD

### Out of Scope

- Nebula FIFO; ERP write-back; `_DISPATCH_OPS` unchanged
- Retention OCR; sheet-report tools; multi-currency; `revision.line`; extra MCP writes

## Capabilities

### New Capabilities

- `collection-allocations`: persist seller-validated allocations; MCP
  create/amend; binding-only resolve (MUST NOT call
  `resolve_customer_partner`); validate/reject; residual `>= 0` only while
  `confirmed` so later amount edits are not blocked

### Modified Capabilities

- `collection-vouchers`: `allocation_id`; freeze when not `confirmed`; unlink
  refused while allocated
- `collection-sheets`: unlink still unassigns when no allocations;
  `allocation.sheet_id ondelete="restrict"` when allocations exist; sheet
  notebook
- None for `collection-connectors` (read-only non-goal), `document-review`,
  `seller-lookup`

## Approach

Reuse snapshot immutability, voucher MCP order, sheet lock, UniqueViolation
reclassify. `UNIQUE(sheet_id, partner_id)`; fungible money; PUT voucher
superset; subtract other confirmed/validated applications of the same
`external_invoice_id`. Manifest `19.0.1.25.0`; migrate `CA/`. Strict TDD;
four stacked units.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `models/collection_allocation*.py` | New | Header, line, revision |
| voucher/sheet models | Modified | `allocation_id`; unlink restrict |
| sequence + migrate `19.0.1.25.0` | Modified | `CA/` |
| `tools/collection_allocation.py` | New | MCP write |
| security, views, manifest | Modified | ACL, notebook, menu 30 |
| `tests/test_collection_allocation*.py` | New | Model/ACL/MCP |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Unlink tests vs restrict | High | Delta empty vs allocated |
| Re-apply ERP balance | High | Subtract other allocations |
| `UNIQUE(request_id)` leak | Med | Related `company_id`; generic UniqueViolation |
| Review amount vs residual | Med | Constrain residual only while `confirmed` |
| Optional `amount`; size | Med | MCP reject null/≤0; stacked units |

## Rollback Plan

Revert `19.0.1.25.0`: drop allocation models, `allocation_id`, `CA/`, MCP,
views. Vouchers/sheets remain. Empty sheets still unlink-unassign. No ERP
effects.

## Dependencies

- Read-only `customer_debt`; customer bindings; open sheet with
  positive-amount vouchers

## Success Criteria

- [ ] MCP create/amend/replay persist `confirmed` allocations; prior
      applications reduce available balance
- [ ] Allocated sheets cannot be deleted; empty sheets still unassign;
      allocated vouchers cannot be unlinked; freeze when not `confirmed`
- [ ] Back-office validate/reject; amend refused after decision
- [ ] `invoke test -m collection --mode=update` and scoped pre-commit pass
