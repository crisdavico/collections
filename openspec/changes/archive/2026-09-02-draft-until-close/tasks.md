# Tasks: Draft Until Sheet Close

## Review Workload Forecast

| Field                   | Value           |
| ----------------------- | --------------- |
| Estimated changed lines | 900–1400        |
| 400-line budget risk    | High            |
| Chained PRs recommended | Yes             |
| Suggested split         | PR1–PR6         |
| Delivery strategy       | auto-chain      |
| Chain strategy          | stacked-to-main |

Decision needed before apply: No Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

### Suggested Work Units

`T` = `invoke test -m collection --mode=update`. `I` = `invoke install -m collection`.
No invoke class filter.

| Unit | Goal                      | Likely PR | Focused test command | Runtime harness | Rollback boundary                                       |
| ---- | ------------------------- | --------- | -------------------- | --------------- | ------------------------------------------------------- |
| 1    | Allocation lifecycle      | PR 1      | T                    | I               | allocation/revision models, ACL, those tests            |
| 2    | Sheet sync + delete       | PR 2      | T                    | I               | sheet model + tests                                     |
| 3    | Voucher invert            | PR 3      | T                    | I               | voucher model + those tests                             |
| 4    | MCP draft/amend           | PR 4      | T                    | I               | MCP tool + both MCP tests                               |
| 5    | Migrate, views, AGENTS.md | PR 5      | T                    | I               | migrate, manifest, views, AGENTS.md, UI/migration tests |
| 6    | Module test + pre-commit  | PR 6      | T                    | N/A verify only | No code slice                                           |

## Phase 1: Allocation lifecycle (draft default, freeze invert, drop Validate/Reject)

- [x] 1.1 RED `tests/test_collection_allocation.py`: default draft; freeze iff
      confirmed; residual both; drop Validate/Reject; draft unlink with revisions;
      confirmed unlink refused; iff skip; direct revision UserError.
- [x] 1.2 RED `tests/test_collection_allocation_acl.py`: revision ACL `1,0,1,1`;
      parent-unlink gated.
- [x] 1.3 GREEN `models/collection_allocation.py`,
      `models/collection_allocation_revision.py`, `security/ir.model.access.csv`:
      default draft; freeze invert; drop validate/reject; residual both; iff skip;
      parent-unlink; ACL `1,0,1,1`.

## Phase 2: Sheet close/reopen sync and open-sheet delete

- [x] 2.1 RED `tests/test_collection_sheet.py`: Close confirms then closes; Reopen opens
      then drafts; blocked reopen stays confirmed; open unlink cascades drafts; closed
      empty refuse.
- [x] 2.2 GREEN `models/collection_sheet.py`: confirm-then-close, open-then-draft via
      `collection_allocation_audited_state` then iff recheck; cascade open unlink.

## Phase 3: Voucher pending delete and membership invert

- [x] 3.1 RED `tests/test_collection_voucher.py` + membership cases in
      `tests/test_collection_allocation.py`: pending unlink draft/unset if residual ≥ 0;
      refuse confirmed and residual `< 0` (no line edits); membership invert.
- [x] 3.2 GREEN `models/collection_voucher.py`: drop `_unlink_if_unallocated`; pending
      unlink unset/draft with residual guard; helper → draft-or-unset; confirmed refuse.

## Phase 4: MCP persist draft and amend invert

- [x] 4.1 RED `tests/test_collection_mcp_allocation.py` +
      `tests/test_collection_mcp_allocation_lookup.py`: persist draft revision 1; amend
      only while draft; revalidation draft+confirmed; found `state` `"draft"`. Keep
      `tools/allocation_lookup.py`.
- [x] 4.2 GREEN `tools/collection_allocation.py`: omit `state` on create; amend iff
      draft; revalidation draft+confirmed; tool description.

## Phase 5: Migration, views, AGENTS.md

- [x] 5.1 RED `tests/test_collection_company_migration.py` +
      `tests/test_collection_ui.py`: `19.0.1.28.0` + migrate folder (no `CA/`); drop
      Validate/Reject UI; readonly invert.
- [x] 5.2 GREEN `migrations/19.0.1.28.0/post-migrate.py`, `__manifest__.py`,
      `views/collection_allocation_views.xml`, `AGENTS.md`: SQL open→draft,
      closed→confirmed; collapse validated/rejected; bump 1.28.0; drop
      buttons/filters/reviewed; invert readonly; revision `delete="false"`.

## Phase 6: Module test + scoped pre-commit

- [x] 6.1 Run T.
- [x] 6.2 `pre-commit run --files` on collection paths touched.
