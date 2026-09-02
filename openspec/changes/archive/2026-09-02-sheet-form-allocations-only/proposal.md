# Proposal: Sheet Form Allocations Only

## Intent

Sheet form notebooks Vouchers (`voucher_ids` many2many) and Allocations. The Vouchers
page duplicates Payment Vouchers. Operators need allocations-first reading, a counted
voucher drill-down, and a UI to unlink membership.

## Assumptions

Settled; not reopened:

- Remove Vouchers page; keep one-page Allocations notebook (do not hide).
- Stat button "N Vouchers" → hand-built `action_open_vouchers` (`list,kanban,form`;
  domain `sheet_id`; defaults `sheet_id`/`seller_id`). Do not `_for_xml_id`
  `collection.action_collection_voucher` (`path="payment-vouchers"`).
- Allocations: `partner_id` after `name`, before `state`.
- Voucher `sheet_id`: list `optional="hide"`; form editable (server guards); search
  field + group-by. Kanban unchanged.
- Keep `voucher_ids`. Non-stored `voucher_count`. No migration.
- Generalize `_ensure_saved_sheet`. Stat button `invisible="not id"`.

## Scope

### In Scope

- Allocations-only notebook + Customer + voucher stat button
- `sheet_id` on voucher list/form/search; generalize `_ensure_saved_sheet`
- TDD: UI arch, `voucher_count`, `action_open_vouchers`

### Out of Scope

Document Review OWL/header/client action; `action_create_collection_sheet`; ACLs; MCP;
mass-unlink / `multi_edit`; Nebula; kanban `sheet_id`; DDL.

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `collection-sheets`: **Sheet form notebook** — allocations only (with Customer); MUST
  NOT expose `voucher_ids`; saved-sheet stat button opens filtered vouchers.
- `collection-vouchers`: **Payment Vouchers UI** — MUST expose `sheet_id` on list
  (`optional="hide"`), form (editable), search (field + group-by). Drop "sheet member
  list" as a voucher UI surface.

`collection-allocations` unchanged.

## Approach

Strict TDD. Invert `tests/test_collection_ui.py` first (rename
`test_sheet_form_notebook_allocations_only`; keep `SHEET_NOTEBOOK_VOUCHERS` for
absence). Then: non-stored `voucher_count`; dict `action_open_vouchers`; reuse
`_ensure_saved_sheet`; XML button box; drop Vouchers page; `partner_id` on
`allocation_ids`; `sheet_id` on voucher list/form/search. Leave `voucher_ids`, dates,
freeze, MCP, Document Review intact. Odoo 19: `<list>`; no XMLID reuse.

## Affected Areas

| Area                                         | Impact   | Description                              |
| -------------------------------------------- | -------- | ---------------------------------------- |
| `models/collection_sheet.py`                 | Modified | count, action, generalize helper         |
| `views/collection_views.xml`                 | Modified | notebook, button box, voucher `sheet_id` |
| `tests/test_collection_ui.py`                | Modified | notebook / stat-button / `sheet_id` arch |
| `tests/test_collection_sheet.py`             | Modified | count + `action_open_vouchers`           |
| `openspec/specs/collection-sheets/spec.md`   | Modified | delta Sheet form notebook                |
| `openspec/specs/collection-vouchers/spec.md` | Modified | delta Payment Vouchers UI                |
| `AGENTS.md`                                  | Modified | apply/archive UI bullet                  |

## Risks

| Risk                                         | Likelihood | Mitigation           |
| -------------------------------------------- | ---------- | -------------------- |
| Mass unlink lost                             | Med        | defer `multi_edit`   |
| Unsaved error still Document Review–specific | Low        | generalize helper    |
| Sheet form `partner_id` count ≠ 1            | Low        | one allocations node |
| Arch tests fail until inverted               | High       | update tests first   |
| 400-line review budget                       | Med        | watch at tasks/apply |

## Rollback Plan

Revert view, model, and test commit. No stored field or migration. Restoring the
Vouchers page recovers the many2many unlink widget.

## Dependencies

None external. Module `-u collection`. Freeze/seller guards exist. Nebula out of scope.

## Success Criteria

- [ ] One Allocations notebook page with Customer; no Vouchers page / no `voucher_ids`
      in arch
- [ ] Stat button shows `voucher_count` and opens `[("sheet_id", "=", sheet.id)]`
      without rewriting `payment-vouchers`
- [ ] Unsaved sheet: button hidden; action raises generalized `UserError`
- [ ] Voucher list/form/search expose `sheet_id`; open-sheet unlink works; closed-sheet
      membership write blocked
- [ ] Dates still recompute; Document Review header works
- [ ] `invoke test -m collection --mode=update` and scoped pre-commit pass
