# Tasks: Voucher Customer Reassign

## Review Workload Forecast

| Field                   | Value                                                              |
| ----------------------- | ------------------------------------------------------------------ |
| Estimated changed lines | 580–840                                                            |
| 400-line budget risk    | High                                                               |
| Chained PRs recommended | Yes                                                                |
| Suggested split         | PR 1 write/constrain → PR 2 action/kanban → PR 3 group_expand/docs |
| Delivery strategy       | auto-chain                                                         |
| Chain strategy          | stacked-to-main                                                    |

Decision needed before apply: No Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

### Suggested Work Units

| Unit | Goal                                         | Likely PR          | Focused test command                      | Runtime harness                                         | Rollback boundary                                      |
| ---- | -------------------------------------------- | ------------------ | ----------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------ |
| 1    | Write follow-up, constrain, residual, 1.26.0 | PR 1 (base `main`) | `invoke test -m collection --mode=update` | N/A — TransactionCase covers write/residual             | Revert voucher write/constrain, tests, manifest 1.26.0 |
| 2    | Reassign action, kanban, header              | PR 2 (on PR 1)     | `invoke test -m collection --mode=update` | `-u collection`; open-sheet header → Reassign Customers | Revert action, new XMLID, header button                |
| 3    | `group_expand` + AGENTS.md                   | PR 3 (on PR 2)     | `invoke test -m collection --mode=update` | `-u collection`; empty allocation + stray columns       | Revert `_read_group_partner_ids` + AGENTS.md           |

Skip OWL, MCP, Nebula, state kanban, migrate 1.26.0.

## Phase 1: Partner write follow-up (PR 1)

- [x] 1.1 RED `tests/test_collection_voucher.py`: same-vals attach; residual 0 refuse;
      attach/unallocated+chatter; non-confirmed source refuse; decided voucher may move.
      RED `tests/test_collection_sheet.py`: closed `partner_id` membership UserError.
- [x] 1.2 RED `tests/test_collection_voucher.py`: constrain mismatch — `allocation_id`
      without matching `partner_id` refuses; fields unchanged.
- [x] 1.3 RED `tests/test_collection_allocation.py`: fully applied detach refused;
      projected residual `<` amount refused; partner write to Q without `allocation_id`
      refused; same-vals Q+B match holds.
- [x] 1.4 RED `tests/test_collection_company_migration.py`: rename
      `test_manifest_version_is_1_25_0` → `1_26_0`; keep `migrations/19.0.1.25.0/`
      asserts; no `19.0.1.26.0/` folder.
- [x] 1.5 GREEN `models/collection_voucher.py`: `partner_id` branch before
      `allocation_id` gate; `_ensure_partner_reassign_unlocked`;
      `_vals_with_partner_allocation` same-`super().write`;
      `_check_voucher_allocation_partner`
      `@api.constrains("partner_id", "allocation_id")`; no `sudo()`.
- [x] 1.6 GREEN `__manifest__.py` `19.0.1.26.0`.
- [x] 1.7 REFACTOR; `invoke test -m collection --mode=update`; `pre-commit run --files`
      on Phase 1 paths.

## Phase 2: Reassign action and kanban (PR 2)

- [x] 2.1 RED `tests/test_collection_sheet.py`: `action_open_voucher_reassign`
      `views`=(reassign kanban, form), domain/context `collection_reassign_sheet_id`, no
      `view_mode`/`view_id`/`path`; name **Reassign Customers**; `.new()` and closed
      raise membership UserError.
- [x] 2.2 RED `tests/test_collection_ui.py`: XMLID
      `view_collection_voucher_reassign_kanban` (group Customer, drag records,
      create/group off, `partner_id` writable, `t-name="card"`); header after Document
      Review `invisible="not id or state != 'open'"`; add xmlid to `partner_id` counts;
      freeze `view_collection_voucher_kanban`.
- [x] 2.3 GREEN `models/collection_sheet.py` `action_open_voucher_reassign` (string
      **Reassign Customers**).
- [x] 2.4 GREEN `views/collection_views.xml`: new XMLID; header after Document Review.
      Do not edit state kanban.
- [x] 2.5 REFACTOR; `-u collection`; `invoke test -m collection --mode=update`;
      `pre-commit run --files` on Phase 2 paths.

## Phase 3: group_expand and docs (PR 3)

- [x] 3.1 RED `tests/test_collection_ui.py`: `formatted_read_group` +
      `read_group_expand=True` — identity without readable
      `collection_reassign_sheet_id`; empty allocation columns; stray voucher customers.
- [x] 3.2 GREEN `models/collection_voucher.py`
      `partner_id.group_expand="_read_group_partner_ids"` (method, not `True`); identity
      unless readable context sheet; allocation ∪ member partners, `res.partner`
      `_order`.
- [x] 3.3 REFACTOR + `AGENTS.md` UI/write/version `19.0.1.26.0`; `-u collection`;
      `invoke test -m collection --mode=update`; `pre-commit run --files` on Phase 3
      paths.
