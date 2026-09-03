# Tasks: Voucher States UI

## Review Workload Forecast

| Field                   | Value                     |
| ----------------------- | ------------------------- |
| Estimated changed lines | 750–950                   |
| 400-line budget risk    | High                      |
| Chained PRs recommended | Yes                       |
| Suggested split         | PR 1 → PR 2 → PR 3 → PR 4 |
| Delivery strategy       | auto-chain                |
| Chain strategy          | stacked-to-main           |

Decision needed before apply: No Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

### Suggested Work Units

| Unit | Goal                                          | Likely PR | Focused test command                                                                             | Runtime harness      | Rollback boundary                                                                 |
| ---- | --------------------------------------------- | --------- | ------------------------------------------------------------------------------------------------ | -------------------- | --------------------------------------------------------------------------------- |
| 1    | Lifecycle + MCP + allocation + migrate 1.31.0 | PR 1      | `invoke test -m collection --mode=update` (voucher, mcp_tool, mcp_allocation, company_migration) | install + same tests | voucher model; MCP/allocation tools; `migrations/19.0.1.31.0/`; `__manifest__.py` |
| 2    | Review queue + Approve split + drop Reject    | PR 2      | `invoke test -m collection --mode=update` (`test_collection_document_review.py`)                 | install + same tests | review methods; `static/src/document_review/*`                                    |
| 3    | Views + chatter + report keys                 | PR 3      | `invoke test -m collection --mode=update` (ui, mail, sheet_report_data)                          | install + same tests | `views/collection_views.xml`; those tests                                         |
| 4    | Leftover AGENTS.md + readme                   | PR 4      | `pre-commit run --files` collection `AGENTS.md` + `readme/DESCRIPTION.md`                        | N/A docs-only        | `AGENTS.md`; `readme/DESCRIPTION.md`                                              |

## Phase 1: Lifecycle + migrate

- [x] 1.1 RED `tests/test_collection_voucher.py`: default `draft`; seller action;
      intercept; unlink; attachment reopen. Specs: Defaults on create; Attachment
      replacement resets.
- [x] 1.2 RED `tests/test_collection_mcp_tool.py` +
      `tests/test_collection_mcp_allocation.py`: MCP stamp `validated_seller`; all
      states may allocate. Specs: MCP create stamps.
- [x] 1.3 RED `tests/test_collection_company_migration.py`: manifest `19.0.1.31.0`;
      `migrations/19.0.1.31.0/` exists; no leftover 1.26–1.30. Spec: Remap before ORM.
- [x] 1.4 GREEN `models/collection_voucher.py`: Selection + default draft;
      `action_validate_seller`; drop approve/reject; intercept; draft-only unlink; drop
      `group_expand`; attachment reopen.
- [x] 1.5 GREEN `tools/collection_voucher.py` stamp `"validated_seller"`;
      `tools/collection_allocation.py` drop rejected gate.
- [x] 1.6 GREEN `__manifest__.py` → `19.0.1.31.0`; add
      `migrations/19.0.1.31.0/post-migrate.py` SQL CASE (copy `19.0.1.28.0`); no
      snapshot rewrite.
- [x] 1.7 Remap leftover old-key literals in other tests; install + full update-mode
      tests; scoped pre-commit.

## Phase 2: Document Review

- [x] 2.1 RED `tests/test_collection_document_review.py`: queue
      `validated_seller`+proof; Approve split write; no reject RPC. Specs: Queue
      eligibility; Reject invokes real action.
- [x] 2.2 GREEN `models/collection_voucher.py`: queue/`_is_review_eligible` =
      `validated_seller`; drop `action_review_reject`; split `_write_review_decision`.
- [x] 2.3 RED/GREEN drop `reject()` + Rechazar in
      `static/src/document_review/document_review_action.esm.js` + `.xml`; keep approve.
- [x] 2.4 Verify: install + review tests; scoped pre-commit.

## Phase 3: Views + report

- [x] 3.1 RED `tests/test_collection_ui.py`: delete stages kanban; `list,form`; keep
      reassign; filters; statusbar; no History; menu 10. Spec: Payment Vouchers UI.
- [x] 3.2 GREEN `views/collection_views.xml` to match 3.1; drop
      History/`review_snapshot_ids`.
- [x] 3.3 RED/GREEN `tests/test_collection_mail.py` + `tracking=True` on
      seller/sheet/type/amount. Spec: State change tracked.
- [x] 3.4 RED/GREEN `tests/test_collection_sheet_report_data.py` print-includes new
      keys. Spec: Open sheet prints drafts.
- [x] 3.5 Verify: install + ui/mail/report tests; scoped pre-commit.

## Phase 4: Docs

- [x] 4.1 Replace pending/approved/rejected keys in `AGENTS.md` and
      `readme/DESCRIPTION.md`; lock migrate-folder rules to `19.0.1.31.0`.
- [x] 4.2 Verify: scoped pre-commit. Harness N/A (docs-only).
