# Tasks: Collection Sheet Workflow

## Review Workload Forecast

| Field                   | Value           |
| ----------------------- | --------------- |
| Estimated changed lines | 900–1400        |
| 400-line budget risk    | High            |
| Chained PRs recommended | Yes             |
| Suggested split         | PR1→PR5         |
| Delivery strategy       | auto-chain      |
| Chain strategy          | stacked-to-main |

Decision needed before apply: No Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

### Suggested Work Units

`invoke test -m collection --mode=update` on named files. Harness
`invoke install -m collection`.

| Unit | Goal                              | Likely PR | Focused test command                                      | Runtime harness                               | Rollback boundary                                                         |
| ---- | --------------------------------- | --------- | --------------------------------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------- |
| 1    | Lifecycle+iff+gate+migrate-1.33.0 | PR1→main  | sheet+allocation+document_review+mail+company_migration   | devel Confirm/Close/Cancel/Open               | sheet/allocation-models;voucher-review;manifest;`migrations/19.0.1.33.0/` |
| 2    | Tabs+debt+allocation-views        | PR2→main  | ui+allocation                                             | three-page sheet form                         | line-relateds;`debt_line_ids`;notebook;allocation-views                   |
| 3    | Drop-Reassign;voucher-freeze      | PR3→main  | voucher+ui+sheet                                          | no-Reassign;allocated-partner-UserError       | follow/`group_expand`;reassign-XMLID;freeze-writes                        |
| 4    | Recon+PDF/XLSX+MCP+header         | PR4→main  | sheet_report_data+mcp_allocation+mcp_allocation_lookup+ui | Print/XLSX-on-proposal;MCP-get-while-proposal | sheet_report;header;MCP-tests-only (`tools/` unchanged)                   |
| 5    | Docs+verify                       | PR5→main  | scoped-pre-commit                                         | N/A-docs;full-update-mode                     | `AGENTS.md`;`readme/DESCRIPTION.md`                                       |

## Phase 1: Lifecycle + iff + gate + migrate 1.33.0

- [x] 1.1 RED `tests/test_collection_sheet.py`: four-state, Confirm gate, unlink,
      one-open. Specs: Confirm review gate; lifecycle; one-open.
- [x] 1.2 RED `tests/test_collection_allocation.py`: iff; Close confirms; Cancel drafts;
      Open leaves draft; Confirm does not confirm. Spec: confirm-on-close.
- [x] 1.3 RED review+mail+migration: non-open Review refused; chatter; `19.0.1.33.0`;
      migrate exists; no remap. Specs: Non-open identifier; Mail thread.
- [x] 1.4 GREEN `models/collection_sheet.py` four actions (drop Reopen), gate, freeze,
      unlink, one-open. Allocation iff. Review Open-only. Manifest `19.0.1.33.0`;
      `migrations/19.0.1.33.0/post-migrate.py` unlink reassign XMLID; no remap.
- [x] 1.5 REFACTOR.

## Phase 2: Tabs + debt + allocation views

- [x] 2.1 RED `tests/test_collection_ui.py`: three pages; Allocations columns (no
      state/`total_applied`); Vouchers no create/remove/delete; Debt `amount_applied`
      only. Spec: notebook.
- [x] 2.2 RED `tests/test_collection_allocation.py`: related stored line
      `sheet_id`/`partner_id`; Closed/Cancelled line write/unlink refused. Spec: write
      guards.
- [x] 2.3 GREEN line relateds+guards; sheet `debt_line_ids`; notebook;
      `views/collection_allocation_views.xml` readonly from `sheet_id.state`; voucher
      M2M Open-only.
- [x] 2.4 REFACTOR.

## Phase 3: Remove Reassign + voucher guards

- [x] 3.1 RED ui+sheet: no Reassign header/XMLID; no `group_expand`. Specs: Reassign
      removed; Payment Vouchers UI.
- [x] 3.2 RED `tests/test_collection_voucher.py`: no auto-follow; allocated partner
      UserError; freeze membership+business fields on non-open; chatter. Specs:
      partner-write; field-guards.
- [x] 3.3 GREEN drop `_read_group_partner_ids`/follow; freeze writes; keep constraint.
      Drop reassign action. `views/collection_views.xml` `<delete>` reassign kanban
      XMLID.
- [x] 3.4 REFACTOR.

## Phase 4: Report + MCP + UI leftover

- [x] 4.1 RED report_data+ui: recon freeze Closed+Cancelled; Proposal editable; PDF/XLSX
      all states; header by state; no Reopen; XLSX last; statusbar keys. Specs:
      PDF/XLSX; Sheets UI.
- [x] 4.2 RED mcp_allocation_lookup + mcp_allocation: Proposal does not occupy MCP open;
      new open while proposal. Spec: MCP open is `open` only. Do not change `tools/`.
- [x] 4.3 GREEN `models/collection_sheet_report.py` freeze Closed+Cancelled;
      `views/collection_views.xml` buttons/statusbar/XLSX last.

## Phase 5: Docs + verify

- [x] 5.1 RED leftover Reopen/Reassign/two-state strings in tests. GREEN `AGENTS.md` +
      `readme/DESCRIPTION.md`: four-state, tabs, drop Reassign, `19.0.1.33.0`.
- [x] 5.2 Verify: `invoke install -m collection`;
      `invoke test -m collection --mode=update`;
      `pre-commit run --files odoo/custom/src/private/collection/**`.
