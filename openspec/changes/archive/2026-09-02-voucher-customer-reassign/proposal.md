# Proposal: Voucher Customer Reassign

Closed plan used instead of a question round.

## Intent

Operators reassign a sheet voucher's Customer by dragging between columns. Today
`partner_id` write ignores closed freeze, leaves `allocation_id` stale, and allocation
constrain misses voucher writes.

**User impact:** open-sheet header opens a customer-grouped kanban; drop writes Customer
and re-attaches a confirmed same-sheet allocation if residual holds, else unallocated.
Closed sheets reuse membership UserError.

## Scope

### In Scope

- New reassign kanban + open-sheet header action; columns = allocation customers ∪ stray
  voucher customers
- `partner_id.group_expand` method; identity unless `collection_reassign_sheet_id` is
  readable
- `write()`: closed freeze; same-`super().write` `partner_id`+`allocation_id`; source
  residual block; target attach iff confirmed same-sheet residual OK
- Voucher-side `@api.constrains("partner_id", "allocation_id")`
- Manifest `19.0.1.26.0`; no migrate

### Out of Scope

- Creating allocations; revising `line_ids`; bulk multi-select
- Document Review OWL; MCP; Nebula; editing state kanban

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `collection-vouchers`: `partner_id` write follows allocation; voucher-side partner
  match; context-gated `group_expand`; any state MAY move while sheet `open`
- `collection-sheets`: closed freeze includes `partner_id` (reuse membership UserError);
  reassign header action + new kanban
- `collection-allocations`: source detach with residual `< 0` MUST refuse the move;
  partner match MUST hold after voucher `partner_id`/`allocation_id` write

## Approach

Plan-as-written. Same-`super().write` `partner_id`+`allocation_id` (per-record). Project
source residual first; fully applied sources block. Attach iff unique confirmed
same-sheet allocation satisfies `_check_residual`; else unallocated + `message_post`. No
`sudo()`. Action: saved + `open` only; `views` list (reassign kanban, form). Kanban:
draggable, create/group off, `partner_id` writable.

## Affected Areas

| Area                           | Impact   | Description                      |
| ------------------------------ | -------- | -------------------------------- |
| `models/collection_voucher.py` | Modified | `group_expand`; write; constrain |
| `models/collection_sheet.py`   | Modified | `action_open_voucher_reassign`   |
| `views/collection_views.xml`   | Modified | New kanban; header button        |
| `__manifest__.py`              | Modified | `19.0.1.26.0`                    |
| `tests/test_collection_*.py`   | Modified | UI, freeze, residual             |

## Risks

| Risk                                   | Likelihood | Mitigation                             |
| -------------------------------------- | ---------- | -------------------------------------- |
| Two-step write trips constrain         | High       | Same-vals `partner_id`+`allocation_id` |
| Fully applied source vs any-state move | High       | Specs refuse the drop                  |
| Empty target / `group_expand=True`     | Med        | Unallocated + chatter; method name     |
| Review size / frozen kanban            | Med        | New XMLID; no OWL/MCP                  |

## Rollback Plan

Revert `19.0.1.26.0`: drop new view/action, `write()` branch, `group_expand`, voucher
constrain. No stored field; kanban/MCP/allocations stay.

## Dependencies

- Residual rules; Odoo 19 Many2one `group_expand`; membership UserError

## Success Criteria

- [ ] Open header: customer kanban; empty allocation columns; stray extras
- [ ] Open drop writes Customer; attach if residual OK else unallocated; fully applied
      source refused
- [ ] Closed `partner_id` reuses membership UserError; state kanban unchanged
- [ ] `invoke test -m collection --mode=update` and scoped pre-commit
