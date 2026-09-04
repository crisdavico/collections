# Apply Progress: collection-sheet-workflow

**Mode**: Strict TDD **Work unit**: 5 (Phase 5 Docs + verify) — stacked-to-main;
PR5→main **Batch status**: Phase 1 complete (1.1–1.5). Phase 2 complete (2.1–2.4). Phase
3 complete (3.1–3.4). Phase 4 complete (4.1–4.3). Phase 5 complete (5.1–5.2). All tasks
`[x]`.

## Completed Tasks

- [x] 1.1 RED `tests/test_collection_sheet.py`: four-state, Confirm gate, unlink,
      one-open
- [x] 1.2 RED `tests/test_collection_allocation.py`: iff; Close confirms; Cancel drafts;
      Open leaves draft; Confirm does not confirm
- [x] 1.3 RED review+mail+migration: non-open Review refused; chatter; `19.0.1.33.0`;
      migrate exists; no remap
- [x] 1.4 GREEN sheet four actions (drop Reopen), gate, freeze, unlink, one-open;
      allocation iff; Review Open-only; manifest `19.0.1.33.0`; migrate unlink reassign
      XMLID; no remap
- [x] 1.5 REFACTOR: `_STATE_WRITE_ACTIONS`, `_VALIDATED_COLLECTIONS`,
      `_DRAFT_SHEET_STATES`, `_CONFIRMED_SHEET_STATE`
- [x] 2.1 RED `tests/test_collection_ui.py`: three pages; Allocations columns (no
      state/`total_applied`); Vouchers no create/remove/delete; Debt `amount_applied`
      only
- [x] 2.2 RED `tests/test_collection_allocation.py`: related stored line
      `sheet_id`/`partner_id`; Closed/Cancelled line write/unlink refused
- [x] 2.3 GREEN line relateds+guards; sheet `debt_line_ids`; notebook; allocation views
      readonly from `sheet_id.state`; voucher M2M Open-only
- [x] 2.4 REFACTOR: share `_FROZEN_SHEET_STATES`; line freeze via `sheet_id.filtered`
- [x] 3.1 RED ui+sheet: no Reassign header/XMLID; no `group_expand`
- [x] 3.2 RED `tests/test_collection_voucher.py`: no auto-follow; allocated partner
      UserError; freeze membership+business fields on non-open; chatter
- [x] 3.3 GREEN drop `_read_group_partner_ids`/follow; freeze writes; keep constraint;
      drop reassign action; `<delete>` reassign kanban XMLID
- [x] 3.4 REFACTOR: `_sheet_is_frozen` shared by membership/partner/business-field
      guards
- [x] 4.1 RED report_data+ui: recon freeze Closed+Cancelled; Proposal editable; PDF/XLSX
      all four states; header by state; no Reopen; XLSX last; statusbar four keys
- [x] 4.2 RED mcp_allocation_lookup + mcp_allocation: Proposal does not occupy MCP open;
      new open while proposal; Closed/Cancelled not used as open. Did not change
      `tools/`.
- [x] 4.3 GREEN `models/collection_sheet_report.py` freeze Closed+Cancelled via
      `_FROZEN_SHEET_STATES`; `views/collection_views.xml` statusbar four keys; XLSX
      already last; leftover Reopen/Reassign test names rewritten so GREEN is real
- [x] 5.1 RED leftover Reopen/Reassign/two-state strings in remaining tests + docs.
      GREEN `AGENTS.md` + `readme/DESCRIPTION.md` four-state, three tabs, drop Reassign,
      `19.0.1.33.0`, migrate folder allowed, one-open still `open` only. Leftover
      Close-from-open MCP tests and allocated partner-detach tests rewritten.
- [x] 5.2 Verify: `invoke install -m collection` exit 0; `invoke start` exit 0;
      `invoke test -m collection --mode=update` exit 0
      (`0 failed, 0 error(s) of 682 tests`); scoped pre-commit exit 0

## TDD Cycle Evidence

| Task | Test File                                                                                                                                                                                  | Layer                              | Safety Net                                                                                                                                                            | RED                                                                                                                                                                                                                                          | GREEN                                                                                                                                                                                                | TRIANGULATE                                                                                                                                                                                                                                                                                                                                                                                                                                    | REFACTOR                                                                           |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| 1.1  | `tests/test_collection_sheet.py`                                                                                                                                                           | Integration (Odoo TransactionCase) | ✅ 0 failed, 0 error(s) of 136 (`TestCollectionSheet` + `TestCollectionAllocation` + `TestCollectionMail` + `test_manifest_version_is_1_32_0`)                        | ✅ Written then ran: exit 1, `4 failed, 13 error(s) of 13 tests`                                                                                                                                                                             | ✅ After models: 13 focused then 159 class tests exit 0                                                                                                                                              | ✅ empty Confirm; all `validated_collections`; unreviewed/seller-validated block; Close/Cancel/Open illegal from open; Close from proposal confirms; Cancel drafts; Open leaves draft; blocked Open keeps cancelled+draft; raw write routes; non-open create; proposal does not occupy one-open; leftover Confirm still succeeds; unlink proposal/cancelled; freeze proposal/cancelled; Document Review non-open; disabled seller Confirm/Open | ✅ `_STATE_WRITE_ACTIONS` + `_VALIDATED_COLLECTIONS`                               |
| 1.2  | `tests/test_collection_allocation.py`                                                                                                                                                      | Integration                        | ✅ same 136-test net                                                                                                                                                  | ✅ Written (included in the 13-test RED run; iff still two-state)                                                                                                                                                                            | ✅ `test_iff_draft_on_proposal_passes`, `test_confirm_does_not_confirm_allocations`, `test_cancel_from_closed_drafts_allocations` in GREEN 13 then 159                                               | ✅ iff draft on proposal/cancelled; Close from proposal confirms; Cancel from proposal/closed drafts; Open leaves draft; Confirm does not confirm                                                                                                                                                                                                                                                                                              | ✅ `_DRAFT_SHEET_STATES` + `_CONFIRMED_SHEET_STATE`                                |
| 1.3  | `tests/test_collection_mail.py`, `tests/test_collection_document_review.py`, `tests/test_collection_company_migration.py`                                                                  | Integration                        | ✅ same 136-test net                                                                                                                                                  | ✅ Written (included in 13-test RED: missing Confirm chatter, Review still succeeded on closed, migrate 1.33.0 missing)                                                                                                                      | ✅ `test_confirm_tracks_state_in_chatter`, `test_review_rpcs_refuse_non_open_sheet`, `test_manifest_version_is_1_33_0` exit 0                                                                        | ✅ Confirm/Close/Cancel/Open chatter; Review refused on proposal/closed/cancelled and still succeeds on open; empty-queue stays open; migrate exists, unlinks XMLID, no `UPDATE collection_sheet` / no `THEN 'proposal'`                                                                                                                                                                                                                       | ➖ migrate SQL already matched 1.32.0 unlink pattern                               |
| 1.4  | `models/collection_sheet.py`, `models/collection_allocation.py`, `models/collection_voucher.py`, `__manifest__.py`, `migrations/19.0.1.33.0/post-migrate.py`, `views/collection_views.xml` | Integration                        | ✅ same                                                                                                                                                               | ✅ tests existed first                                                                                                                                                                                                                       | ✅ First `-u` hit ParseError (`action_reopen` on form). After header retarget: 13 focused `0 failed, 0 error(s) of 13 tests`; broader `0 failed, 0 error(s) of 159 tests`                            | ✅ covered by 1.1–1.3 cases                                                                                                                                                                                                                                                                                                                                                                                                                    | ✅ constants in 1.5                                                                |
| 1.5  | same Phase 1 classes                                                                                                                                                                       | Integration                        | N/A (refactor gate)                                                                                                                                                   | ➖ no new RED                                                                                                                                                                                                                                | ✅ after refactor: `0 failed, 0 error(s) of 158 tests`                                                                                                                                               | ➖                                                                                                                                                                                                                                                                                                                                                                                                                                             | ✅ `invoke install -m collection` exit 0                                           |
| 2.1  | `tests/test_collection_ui.py`                                                                                                                                                              | Integration                        | ✅ 0 failed, 0 error(s) of 56 (`TestCollectionAllocation` + three existing UI methods)                                                                                | ✅ Written then ran: exit 1, `9 failed, 2 error(s) of 12 tests` (Allocations-only notebook; `state == 'confirmed'` readonly)                                                                                                                 | ✅ After views: included in 65-test GREEN                                                                                                                                                            | ✅ three-page columns; Vouchers no create/delete Open-only; Debt `amount_applied` only; allocation form `sheet_id.state`; voucher M2M Open-only                                                                                                                                                                                                                                                                                                | ➖ view arch already matched spec after GREEN                                      |
| 2.2  | `tests/test_collection_allocation.py`                                                                                                                                                      | Integration                        | ✅ same 56-test net                                                                                                                                                   | ✅ Written (included in 12-test RED: missing `sheet_id`; Closed/Cancelled line write/unlink not raised)                                                                                                                                      | ✅ related stored + Closed/Cancelled guards in 65-test GREEN                                                                                                                                         | ✅ second partner relateds; cancelled write; closed writes; proposal persist; cancelled unlink; closed unlink                                                                                                                                                                                                                                                                                                                                  | ✅ shared `_FROZEN_SHEET_STATES`                                                   |
| 2.3  | `models/collection_allocation_line.py`, `models/collection_allocation.py`, `models/collection_sheet.py`, `views/collection_views.xml`, `views/collection_allocation_views.xml`             | Integration                        | ✅ same                                                                                                                                                               | ✅ tests existed first                                                                                                                                                                                                                       | ✅ First GREEN: 11/12 (outsider voucher create on closed sheet hit membership freeze). After test setup fix: **exit 0** `0 failed, 0 error(s) of 65 tests`                                           | ✅ covered by 2.1–2.2 cases                                                                                                                                                                                                                                                                                                                                                                                                                    | ✅ 2.4                                                                             |
| 2.4  | line imports `_FROZEN_SHEET_STATES`; `sheet_id.filtered`                                                                                                                                   | Integration                        | N/A (refactor gate)                                                                                                                                                   | ➖ no new RED                                                                                                                                                                                                                                | ✅ after refactor: **exit 0** `0 failed, 0 error(s) of 65 tests`                                                                                                                                     | ➖                                                                                                                                                                                                                                                                                                                                                                                                                                             | ✅ shared frozen-state constant; line freeze via filtered sheets                   |
| 3.1  | `tests/test_collection_ui.py`, `tests/test_collection_sheet.py`                                                                                                                            | Integration                        | ✅ 140/141 (1 pre-existing: sheet-form `partner_id` count after Phase 2 notebook; rewritten in this RED)                                                              | ✅ Written then ran: exit 1, `16 failed, 0 error(s) of 19 tests`                                                                                                                                                                             | ✅ included in 31 then 149                                                                                                                                                                           | ✅ XMLID gone; header gone; `group_expand` off; method gone on saved and unsaved sheets                                                                                                                                                                                                                                                                                                                                                        | ➖ view delete already matched spec                                                |
| 3.2  | `tests/test_collection_voucher.py`                                                                                                                                                         | Integration                        | ✅ same 140/141 net (voucher+sheet classes passed)                                                                                                                    | ✅ Written (included in 19-test RED: auto-follow still attached; freeze not raised)                                                                                                                                                          | ✅ allocated UserError; no auto-follow; freeze proposal/cancelled/closed; chatter; allocation_id on proposal in 31 then 149                                                                          | ✅ residual-0 allocated refuse; unassign-then-change; unassigned no follow; same-value; confirmed source; all states unassigned; constraint; open writable; cancelled sheet_id; proposal partner membership error; amount vs from_account; closed amount; chatter proposal+closed                                                                                                                                                              | ✅ `_sheet_is_frozen`                                                              |
| 3.3  | `models/collection_voucher.py`, `models/collection_sheet.py`, `views/collection_views.xml`                                                                                                 | Integration                        | ✅ same                                                                                                                                                               | ✅ tests existed first                                                                                                                                                                                                                       | ✅ First GREEN focused: **exit 0** `0 failed, 0 error(s) of 31 tests`; class net **exit 0** `0 failed, 0 error(s) of 149 tests`                                                                      | ✅ covered by 3.1–3.2 cases                                                                                                                                                                                                                                                                                                                                                                                                                    | ✅ 3.4                                                                             |
| 3.4  | `_sheet_is_frozen` on voucher freeze helpers                                                                                                                                               | Integration                        | N/A (refactor gate)                                                                                                                                                   | ➖ no new RED                                                                                                                                                                                                                                | ✅ after refactor: **exit 0** `0 failed, 0 error(s) of 149 tests`                                                                                                                                    | ➖                                                                                                                                                                                                                                                                                                                                                                                                                                             | ✅ shared `_sheet_is_frozen` for sheet_id / partner_id / `_REVIEW_EDITABLE_FIELDS` |
| 4.1  | `tests/test_collection_sheet_report_data.py`, `tests/test_collection_sheet_report.py`, `tests/test_collection_sheet_xlsx.py`, `tests/test_collection_ui.py`                                | Integration                        | ✅ 0 failed, 0 error(s) of 10 (`percent`/`payload`/`unsaved`/`xlsx zip`/`act_url`/`qweb values`/`three-page notebook`/`no Reassign`/`MCP first create`/`GET no-open`) | ✅ Written then ran: exit 1, `2 failed, 0 error(s) of 18 tests` (`test_cancelled_write_guard` UserError not raised; statusbar still `open,closed`)                                                                                           | ✅ After freeze+statusbar: focused 18 then class net 69 exit 0                                                                                                                                       | ✅ closed freeze (Confirm then Close); cancelled freeze; proposal editable; Open-from-Cancelled keeps values; PDF/XLSX walk four states; unsaved XLSX; header by state; XLSX last; Document Review `state != 'open'`                                                                                                                                                                                                                           | ➖ leftover Reopen/Reassign/one-page asserts rewritten to match spec               |
| 4.2  | `tests/test_collection_mcp_allocation_lookup.py`, `tests/test_collection_mcp_allocation.py`                                                                                                | Integration                        | ✅ same 10-test net                                                                                                                                                   | ✅ Written (included in 18-test RED: proposal/closed/cancelled GET null and create-while-proposal already passed — `_open_sheets_for_seller` is `open` only; `tools/` unchanged)                                                             | ✅ `test_proposal_sheet_does_not_occupy_mcp_open`, `test_closed_sheet_only_returns_null`, `test_cancelled_sheet_only_returns_null`, `test_create_new_open_while_proposal_exists` in GREEN 18 then 69 | ✅ GET null on proposal (with allocation), closed, cancelled; create new open while proposal remains proposal                                                                                                                                                                                                                                                                                                                                  | ➖ no tool Python to change                                                        |
| 4.3  | `models/collection_sheet_report.py`, `views/collection_views.xml`                                                                                                                          | Integration                        | ✅ same                                                                                                                                                               | ✅ tests existed first                                                                                                                                                                                                                       | ✅ First GREEN focused: **exit 0** `0 failed, 0 error(s) of 18 tests`; class net **exit 0** `0 failed, 0 error(s) of 69 tests`                                                                       | ✅ covered by 4.1–4.2 cases                                                                                                                                                                                                                                                                                                                                                                                                                    | ✅ import `_FROZEN_SHEET_STATES`; after refactor class net still 69/69             |
| 5.1  | `tests/test_collection_company_migration.py`, leftover MCP/allocation tests, `AGENTS.md`, `readme/DESCRIPTION.md`                                                                          | Integration                        | ✅ 0 failed, 0 error(s) of 1 (`test_manifest_version_is_1_33_0`)                                                                                                      | ✅ Written then ran: exit 1, `3 failed, 0 error(s) of 3 tests` (docs still two-state; leftover scanner first matched itself). After skip-self: docs 2 failed. First full suite then found 7 leftover Close-from-open / partner-detach errors | ✅ After docs + leftover rewrites: focused 4 then 7 then full 682 exit 0                                                                                                                             | ✅ AGENTS.md + DESCRIPTION.md; leftover partner-write refuse; proposal extra created before Confirm; MCP `_close_open_sheet` Confirm then Close                                                                                                                                                                                                                                                                                                | ➖ docs copy already matched spec phrasing                                         |
| 5.2  | full suite + scoped pre-commit                                                                                                                                                             | Integration                        | N/A (verify gate)                                                                                                                                                     | ➖                                                                                                                                                                                                                                           | ✅ `invoke install` exit 0; `invoke test --mode=update` **exit 0** `0 failed, 0 error(s) of 682 tests`; scoped pre-commit **exit 0** (first pre-commit exit 1 E501, then wrap + retry)               | ➖                                                                                                                                                                                                                                                                                                                                                                                                                                             | ➖                                                                                 |

### Test Summary

- **Total tests written (Phase 1)**: Confirm gate (empty / all-validated / unreviewed /
  seller-validated); illegal Close/Cancel/Open from open; Close from proposal; Cancel
  from proposal and closed; Open from cancelled; blocked Open; raw write routing;
  non-open create; proposal one-open; leftover Confirm; unlink proposal/cancelled;
  freeze proposal/cancelled; header Review non-open; iff draft on proposal/cancelled;
  Confirm does not confirm allocations; Confirm/Cancel/Open chatter; Review RPCs refuse
  non-open + succeed on open; empty-queue stays open; manifest `19.0.1.33.0` + migrate
  no-remap
- **Total tests written (Phase 2)**: three-page notebook columns (no
  `state`/`total_applied`); Vouchers tab existing-only in Open; Debt tab
  `amount_applied` only; allocation form readonly from `sheet_id.state`; voucher M2M
  Open-only; related stored `sheet_id`/`partner_id` + `debt_line_ids`; second-partner
  relateds; cancelled line write; closed allocation writes; proposal persist; cancelled
  unlink; closed unlink
- **Total tests written (Phase 3)**: Reassign XMLID/header gone;
  `partner_id.group_expand` dropped; allocated partner UserError; residual-0 refuse;
  unassign then Customer; no auto-follow; same-value no recompute; proposal/cancelled
  `sheet_id` freeze; proposal partner membership error; proposal/cancelled/closed
  business fields; open membership+fields writable; `allocation_id` writable on
  proposal; chatter on proposal+closed
- **Total tests written (Phase 4)**: cancelled recon freeze; closed recon freeze via
  Confirm then Close; proposal recon editable; Open-from-Cancelled keeps recon; PDF
  payload + `_get_report_values` + XLSX download in all four states without changing
  collected_total/reference; unsaved XLSX refused; four-state statusbar; header
  Confirm/Close/Cancel/Open + Document Review Open-only + XLSX last; no Reopen; Document
  Review `invisible` includes `state != 'open'`; XLSX leftover Reassign/one-page
  rewritten; MCP GET null on proposal/closed/cancelled; MCP create new open while
  proposal exists
- **Total tests written (Phase 5)**: leftover remaining-tests scanner (no Close/Reopen
  call, no two-state statusbar); AGENTS.md four-state / three tabs / drop Reassign /
  `19.0.1.33.0` / migrate 1.33.0 / one-open still `open` only; DESCRIPTION.md
  four-state + three tabs; leftover MCP Close-from-open rewritten via
  `_close_open_sheet`; leftover allocated partner-detach now refuses; proposal extra
  voucher created before Confirm
- **Total tests passing**: Phase 5 focused **4** then leftover **7**; full suite
  **682**. Phase 4 focused **18** then class net **69**; Phase 3 **149**; Phase 2
  **65**; Phase 1 **158**
- **Layers used**: Unit (0), Integration (682 this batch), E2E (0)
- **Approval tests** (refactoring): leftover remaining-tests scanner (already green
  after skip-self); freeze UserError `"Reopen first."` kept
- **Pure functions created**: none this batch. MCP tests gained `_close_open_sheet`.

### Phase 1 Safety Net (exit 0, before edits)

```bash
cd /home/crisd/projects/seedian/seedian
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionSheet,/collection:TestCollectionAllocation,/collection:TestCollectionMail,/collection:TestCollectionCompanyMigration.test_manifest_version_is_1_32_0
```

Result: **exit 0** — `0 failed, 0 error(s) of 136 tests`.

### Phase 1 RED command (exit 1)

```bash
cd /home/crisd/projects/seedian/seedian
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionSheet.test_sequence_assigned_on_create,/collection:TestCollectionSheet.test_action_confirm_empty_members_pass,/collection:TestCollectionSheet.test_action_confirm_unreviewed_member_blocks,/collection:TestCollectionSheet.test_non_open_create_rejected,/collection:TestCollectionSheet.test_proposal_does_not_occupy_one_open,/collection:TestCollectionSheet.test_unlink_proposal_refused,/collection:TestCollectionSheet.test_freeze_rejects_membership_on_proposal,/collection:TestCollectionAllocation.test_iff_draft_on_proposal_passes,/collection:TestCollectionAllocation.test_confirm_does_not_confirm_allocations,/collection:TestCollectionAllocation.test_cancel_from_closed_drafts_allocations,/collection:TestCollectionMail.test_confirm_tracks_state_in_chatter,/collection:TestCollectionDocumentReview.test_review_rpcs_refuse_non_open_sheet,/collection:TestCollectionCompanyMigration.test_manifest_version_is_1_33_0
```

Result: **exit 1** — `4 failed, 13 error(s) of 13 tests` (missing `action_confirm` /
`action_open`, `action_reopen` still present, Confirm chatter missing, Review still
succeeded on closed, migrate `19.0.1.33.0` missing, closed create still succeeded).

### Phase 1 GREEN / work-unit focused command (exit 0)

```bash
cd /home/crisd/projects/seedian/seedian
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionSheet,/collection:TestCollectionAllocation,/collection:TestCollectionMail,/collection:TestCollectionCompanyMigration.test_manifest_version_is_1_33_0,/collection:TestCollectionDocumentReview.test_review_rpcs_refuse_non_open_sheet,/collection:TestCollectionDocumentReview.test_review_rpcs_still_succeed_on_open_sheet,/collection:TestCollectionDocumentReview.test_queue_empty_for_sheet_with_no_eligible_members
```

Result after view unblock: **exit 0** — `0 failed, 0 error(s) of 159 tests`. After 1.5
refactor (same tags): **exit 0** — `0 failed, 0 error(s) of 158 tests`.

First GREEN `-u` (before view edit) failed with ParseError:
`action_reopen is not a valid action on collection.sheet` (`views/collection_views.xml`
form header). Header retargeted to Confirm/Close/Cancel/Open; Reopen dropped.

### Phase 2 Safety Net (exit 0, before edits)

```bash
cd /home/crisd/projects/seedian/seedian
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionAllocation,/collection:TestCollectionUi.test_sheet_form_notebook_allocations_only,/collection:TestCollectionUi.test_collection_allocations_form_statusbar_no_validate_reject,/collection:TestCollectionUi.test_allocation_form_vouchers_existing_only_many2many
```

Result: **exit 0** — `0 failed, 0 error(s) of 56 tests`. Full `TestCollectionUi` was not
used as the net because Phase 1 leftover Reopen/statusbar asserts remain for Phase 4.

### Phase 2 RED command (exit 1)

```bash
cd /home/crisd/projects/seedian/seedian
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionUi.test_sheet_form_notebook_three_pages_allocations_columns,/collection:TestCollectionUi.test_sheet_form_vouchers_tab_existing_only_in_open,/collection:TestCollectionUi.test_sheet_form_debt_tab_amount_applied_only,/collection:TestCollectionUi.test_collection_allocations_form_statusbar_no_validate_reject,/collection:TestCollectionUi.test_allocation_form_vouchers_existing_only_many2many,/collection:TestCollectionAllocation.test_line_related_stored_sheet_id_and_partner_id,/collection:TestCollectionAllocation.test_line_relateds_follow_second_partner,/collection:TestCollectionAllocation.test_cancelled_draft_line_write_refused,/collection:TestCollectionAllocation.test_closed_allocation_writes_refused,/collection:TestCollectionAllocation.test_proposal_draft_line_and_voucher_writes_persist,/collection:TestCollectionAllocation.test_cancelled_line_unlink_refused,/collection:TestCollectionAllocation.test_closed_line_unlink_refused
```

Result: **exit 1** — `9 failed, 2 error(s) of 12 tests`. Notebook still
Allocations-only; line had no `sheet_id`; Closed/Cancelled line write/unlink not
refused; allocation form still `readonly="state == 'confirmed'"`. Proposal persist
already passed (existing Open/Proposal writability).

### Phase 2 GREEN / work-unit focused command (exit 0)

```bash
cd /home/crisd/projects/seedian/seedian
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionAllocation,/collection:TestCollectionUi.test_sheet_form_notebook_three_pages_allocations_columns,/collection:TestCollectionUi.test_sheet_form_vouchers_tab_existing_only_in_open,/collection:TestCollectionUi.test_sheet_form_debt_tab_amount_applied_only,/collection:TestCollectionUi.test_collection_allocations_form_statusbar_no_validate_reject,/collection:TestCollectionUi.test_allocation_form_vouchers_existing_only_many2many
```

Result after closed-outsider setup fix: **exit 0** — `0 failed, 0 error(s) of 65 tests`.
After 2.4 refactor (same tags): **exit 0** — `0 failed, 0 error(s) of 65 tests`.

First GREEN 12-test run: `0 failed, 1 error(s) of 12` because `_create_voucher` on an
already-closed sheet hit membership freeze. Outsider voucher is now created and
validated before Confirm/Close.

### Phase 3 Safety Net (exit 1, 1 pre-existing leftover)

```bash
cd /home/crisd/projects/seedian/seedian
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionVoucher,/collection:TestCollectionSheet,/collection:TestCollectionUi.test_stages_kanban_deleted_action_is_list_form,/collection:TestCollectionUi.test_reassign_kanban_groups_by_customer_and_disables_create,/collection:TestCollectionUi.test_customer_field_is_partner_id_without_domain,/collection:TestCollectionUi.test_state_group_expand_dropped,/collection:TestCollectionUi.test_partner_group_expand_identity_without_readable_sheet,/collection:TestCollectionUi.test_partner_group_expand_empty_allocation_columns,/collection:TestCollectionUi.test_partner_group_expand_stray_voucher_customers,/collection:TestCollectionUi.test_sheet_form_header_reassign_after_document_review_when_open,/collection:TestCollectionUi.test_voucher_list_form_search_expose_sheet_id
```

Result: **exit 1** — `1 failed, 0 error(s) of 141 tests`. Pre-existing leftover:
`test_customer_field_is_partner_id_without_domain` expected 1 `partner_id` on the sheet
form after Phase 2 added Allocations + Debt columns. Voucher and sheet classes passed.
That UI test was rewritten in 3.1 RED to Payment Vouchers list/search/form only (spec
surface).

### Phase 3 RED command (exit 1)

```bash
cd /home/crisd/projects/seedian/seedian
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionUi.test_stages_kanban_deleted_action_is_list_form,/collection:TestCollectionUi.test_reassign_kanban_xmlid_deleted,/collection:TestCollectionUi.test_customer_field_is_partner_id_without_domain,/collection:TestCollectionUi.test_partner_group_expand_dropped,/collection:TestCollectionUi.test_sheet_form_header_has_no_reassign,/collection:TestCollectionUi.test_voucher_list_form_search_expose_sheet_id,/collection:TestCollectionSheet.test_action_open_voucher_reassign_removed,/collection:TestCollectionSheet.test_action_open_voucher_reassign_removed_on_new_record,/collection:TestCollectionVoucher.test_allocated_partner_write_refused,/collection:TestCollectionVoucher.test_allocated_partner_write_refused_when_residual_zero,/collection:TestCollectionVoucher.test_unassign_then_partner_write,/collection:TestCollectionVoucher.test_unassigned_partner_write_does_not_auto_follow,/collection:TestCollectionVoucher.test_same_value_partner_write_does_not_recompute,/collection:TestCollectionVoucher.test_proposal_membership_sheet_id_refused,/collection:TestCollectionVoucher.test_cancelled_membership_sheet_id_refused,/collection:TestCollectionVoucher.test_proposal_partner_id_reuses_membership_error,/collection:TestCollectionVoucher.test_proposal_business_fields_refused,/collection:TestCollectionVoucher.test_cancelled_business_fields_refused,/collection:TestCollectionVoucher.test_closed_business_fields_refused
```

Result: **exit 1** — `16 failed, 0 error(s) of 19 tests`. Reassign
XMLID/header/`group_expand` still present; auto-follow still attached; freeze not raised
on proposal/cancelled/closed business fields. Three already-green: Payment Vouchers
unbound `partner_id`; list/form/search `sheet_id`; same-value partner write.

### Phase 3 GREEN / work-unit focused command (exit 0)

```bash
cd /home/crisd/projects/seedian/seedian
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionVoucher,/collection:TestCollectionSheet,/collection:TestCollectionUi.test_stages_kanban_deleted_action_is_list_form,/collection:TestCollectionUi.test_reassign_kanban_xmlid_deleted,/collection:TestCollectionUi.test_customer_field_is_partner_id_without_domain,/collection:TestCollectionUi.test_partner_group_expand_dropped,/collection:TestCollectionUi.test_state_group_expand_dropped,/collection:TestCollectionUi.test_sheet_form_header_has_no_reassign,/collection:TestCollectionUi.test_voucher_list_form_search_expose_sheet_id,/collection:TestCollectionUi.test_sheet_form_notebook_three_pages_allocations_columns,/collection:TestCollectionUi.test_sheet_form_vouchers_tab_existing_only_in_open,/collection:TestCollectionUi.test_sheet_form_debt_tab_amount_applied_only
```

Result: **exit 0** — `0 failed, 0 error(s) of 31 tests` (first GREEN focused 31
including freeze/allocation_id/chatter). Same class net after GREEN and after 3.4:
**exit 0** — `0 failed, 0 error(s) of 149 tests`.

### Phase 4 Safety Net (exit 0, before edits)

```bash
cd /home/crisd/projects/seedian/seedian
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionSheetReportData.test_percent_range_persists_bounds,/collection:TestCollectionSheetReportData.test_payload_keys_and_primitives,/collection:TestCollectionSheetReportData.test_unsaved_sheet_refused,/collection:TestCollectionSheetXlsx.test_xlsx_bytes_are_zip_with_workbook,/collection:TestCollectionSheetXlsx.test_action_print_xlsx_act_url_and_attachment,/collection:TestCollectionSheetReport.test_get_report_values_one_payload_per_doc,/collection:TestCollectionUi.test_sheet_form_notebook_three_pages_allocations_columns,/collection:TestCollectionUi.test_sheet_form_header_has_no_reassign,/collection:TestCollectionMcpAllocation.test_first_create_draft_revision_one_totals,/collection:TestCollectionMcpAllocationLookup.test_no_open_sheet_returns_null
```

Result: **exit 0** — `0 failed, 0 error(s) of 10 tests`.

### Phase 4 RED command (exit 1)

```bash
cd /home/crisd/projects/seedian/seedian
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionSheetReportData.test_closed_write_guard,/collection:TestCollectionSheetReportData.test_cancelled_write_guard,/collection:TestCollectionSheetReportData.test_proposal_recon_remains_editable,/collection:TestCollectionSheetReportData.test_open_from_cancelled_keeps_recon_values,/collection:TestCollectionSheetReportData.test_payload_in_all_four_states,/collection:TestCollectionSheetReportData.test_unsaved_sheet_refused,/collection:TestCollectionSheetReport.test_pdf_in_all_four_states,/collection:TestCollectionSheetXlsx.test_xlsx_in_all_four_states,/collection:TestCollectionSheetXlsx.test_unsaved_xlsx_refused,/collection:TestCollectionSheetXlsx.test_header_xlsx_button_last_before_state,/collection:TestCollectionSheetXlsx.test_sheet_form_three_notebook_pages_recon_second_group,/collection:TestCollectionUi.test_collection_sheets_form_statusbar_four_states,/collection:TestCollectionUi.test_sheet_form_header_document_review_visible_when_saved_and_flag_on,/collection:TestCollectionUi.test_sheet_form_header_document_review_hidden_when_flag_off_or_unsaved,/collection:TestCollectionMcpAllocationLookup.test_proposal_sheet_does_not_occupy_mcp_open,/collection:TestCollectionMcpAllocationLookup.test_closed_sheet_only_returns_null,/collection:TestCollectionMcpAllocationLookup.test_cancelled_sheet_only_returns_null,/collection:TestCollectionMcpAllocation.test_create_new_open_while_proposal_exists
```

Result: **exit 1** — `2 failed, 0 error(s) of 18 tests`. Cancelled recon writes did not
raise; statusbar still `open,closed`. PDF/XLSX four-state, proposal recon, MCP
proposal-open, leftover Reopen/Reassign rewrites already matched current production.

### Phase 4 GREEN / work-unit focused command (exit 0)

```bash
cd /home/crisd/projects/seedian/seedian
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionSheetReportData,/collection:TestCollectionSheetReport,/collection:TestCollectionSheetXlsx,/collection:TestCollectionUi.test_collection_sheets_form_statusbar_four_states,/collection:TestCollectionUi.test_sheet_form_header_document_review_visible_when_saved_and_flag_on,/collection:TestCollectionUi.test_sheet_form_header_document_review_hidden_when_flag_off_or_unsaved,/collection:TestCollectionUi.test_sheet_form_header_has_no_reassign,/collection:TestCollectionUi.test_sheet_form_notebook_three_pages_allocations_columns,/collection:TestCollectionMcpAllocationLookup,/collection:TestCollectionMcpAllocation.test_create_new_open_while_proposal_exists,/collection:TestCollectionMcpAllocation.test_first_create_draft_revision_one_totals
```

Result after freeze+statusbar: **exit 0** — `0 failed, 0 error(s) of 18 tests` (first
GREEN focused). Same class net after GREEN and after `_FROZEN_SHEET_STATES` import:
**exit 0** — `0 failed, 0 error(s) of 69 tests`.

### Phase 5 Safety Net (exit 0, before edits)

```bash
cd /home/crisd/projects/seedian/seedian
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionCompanyMigration.test_manifest_version_is_1_33_0
```

Result: **exit 0** — `0 failed, 0 error(s) of 1 tests`.

### Phase 5 RED command (exit 1)

```bash
cd /home/crisd/projects/seedian/seedian
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionCompanyMigration.test_remaining_tests_drop_two_state_leftovers,/collection:TestCollectionCompanyMigration.test_agents_md_four_state_workflow,/collection:TestCollectionCompanyMigration.test_readme_description_four_state_workflow
```

Result: **exit 1** — `3 failed, 0 error(s) of 3 tests` (AGENTS.md still `19.0.1.32.0` /
two-state; DESCRIPTION.md missing `proposal`; leftover scanner matched itself). After
skip-self, docs tests still failed until GREEN.

### Phase 5 GREEN / leftover focused command (exit 0)

```bash
cd /home/crisd/projects/seedian/seedian
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionCompanyMigration.test_remaining_tests_drop_two_state_leftovers,/collection:TestCollectionCompanyMigration.test_agents_md_four_state_workflow,/collection:TestCollectionCompanyMigration.test_readme_description_four_state_workflow,/collection:TestCollectionCompanyMigration.test_manifest_version_is_1_33_0
```

Result after docs: **exit 0** — `0 failed, 0 error(s) of 4 tests`. Leftover 7-test
rewrite: **exit 0** — `0 failed, 0 error(s) of 7 tests`.

## Work Unit Evidence

### Work unit 1 (Phase 1)

| Evidence                | Value                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command    | See Phase 1 GREEN command (`TestCollectionSheet` + `TestCollectionAllocation` + `TestCollectionMail` + migrate 1.33.0 + three Document Review methods)                                                                                                                                                                                                                                                                                               |
| Focused test result     | **exit 0** — `0 failed, 0 error(s) of 159 tests` (GREEN); **exit 0** — `0 failed, 0 error(s) of 158 tests` (after REFACTOR)                                                                                                                                                                                                                                                                                                                          |
| Runtime harness command | `invoke install -m collection` from `/home/crisd/projects/seedian/seedian`                                                                                                                                                                                                                                                                                                                                                                           |
| Runtime harness result  | **exit 0** — `addons init -w collection` / `odoo --stop-after-init --init collection` completed; registry loaded; shutdown clean. Stops `seedian-odoo-1` (invoke install behavior).                                                                                                                                                                                                                                                                  |
| Rollback boundary       | `models/collection_sheet.py`; `models/collection_allocation.py`; `models/collection_voucher.py` (`_require_review_sheet` Open-only); `__manifest__.py` `19.0.1.33.0`; `migrations/19.0.1.33.0/`; Phase 1 tests listed above; `views/collection_views.xml` header buttons (loadable form after dropping `action_reopen`). Does not include notebook/debt tabs (Phase 2), Reassign removal (Phase 3), statusbar/XLSX/MCP (Phase 4), or docs (Phase 5). |

### Work unit 2 (Phase 2)

| Evidence                | Value                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command    | See Phase 2 GREEN command (`TestCollectionAllocation` + five notebook/allocation-view UI methods)                                                                                                                                                                                                                                                                                                                                                                                      |
| Focused test result     | **exit 0** — `0 failed, 0 error(s) of 65 tests` (GREEN and after REFACTOR)                                                                                                                                                                                                                                                                                                                                                                                                             |
| Runtime harness command | `invoke install -m collection` from `/home/crisd/projects/seedian/seedian`; then `invoke start` (install stopped `seedian-odoo-1`)                                                                                                                                                                                                                                                                                                                                                     |
| Runtime harness result  | **exit 0** — `addons init -w collection` / `odoo --stop-after-init --init collection` completed; registry loaded; shutdown clean. `invoke start` restarted `seedian-odoo-1`.                                                                                                                                                                                                                                                                                                           |
| Rollback boundary       | `models/collection_allocation_line.py` relateds+write/`@api.ondelete`; `models/collection_allocation.py` sheet-state `_FROZEN_FIELDS` freeze; `models/collection_sheet.py` `debt_line_ids`; `views/collection_views.xml` three-page notebook only (header/Reassign/statusbar untouched); `views/collection_allocation_views.xml` `sheet_id.state` modifiers; Phase 2 tests listed above. Does not include Reassign removal (Phase 3), statusbar/XLSX/MCP (Phase 4), or docs (Phase 5). |

### Work unit 3 (Phase 3)

| Evidence                | Value                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command    | See Phase 3 GREEN command (`TestCollectionVoucher` + `TestCollectionSheet` + Reassign/group_expand/notebook UI methods)                                                                                                                                                                                                                                                                                               |
| Focused test result     | **exit 0** — `0 failed, 0 error(s) of 31 tests` (first GREEN); **exit 0** — `0 failed, 0 error(s) of 149 tests` (class net GREEN and after REFACTOR)                                                                                                                                                                                                                                                                  |
| Runtime harness command | `invoke install -m collection` from `/home/crisd/projects/seedian/seedian`; then `invoke start` (install stopped `seedian-odoo-1`)                                                                                                                                                                                                                                                                                    |
| Runtime harness result  | **exit 0** — `addons init -w collection` / `odoo --stop-after-init --init collection` completed; registry loaded; shutdown clean. `invoke start` restarted `seedian-odoo-1`.                                                                                                                                                                                                                                          |
| Rollback boundary       | `models/collection_voucher.py` (`group_expand`/follow/freeze writes; keep `_check_voucher_allocation_partner`); `models/collection_sheet.py` drop `action_open_voucher_reassign`; `views/collection_views.xml` `<delete>` reassign kanban + drop header button (notebook/Confirm-Close-Cancel-Open/statusbar untouched); Phase 3 tests listed above. Does not include statusbar/XLSX/MCP (Phase 4) or docs (Phase 5). |

### Work unit 4 (Phase 4)

| Evidence                | Value                                                                                                                                                                                                                                                                                                   |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command    | See Phase 4 GREEN command (`TestCollectionSheetReportData` + `TestCollectionSheetReport` + `TestCollectionSheetXlsx` + MCP lookup class + two MCP create methods + five UI methods)                                                                                                                     |
| Focused test result     | **exit 0** — `0 failed, 0 error(s) of 18 tests` (first GREEN); **exit 0** — `0 failed, 0 error(s) of 69 tests` (class net GREEN and after REFACTOR)                                                                                                                                                     |
| Runtime harness command | `invoke install -m collection` from `/home/crisd/projects/seedian/seedian`; then `invoke start` (install stopped `seedian-odoo-1`)                                                                                                                                                                      |
| Runtime harness result  | **exit 0** — `addons init -w collection` completed; registry loaded; shutdown clean. `invoke start` restarted `seedian-odoo-1`.                                                                                                                                                                         |
| Rollback boundary       | `models/collection_sheet_report.py` recon freeze Closed+Cancelled; `views/collection_views.xml` `statusbar_visible` four keys (header Confirm/Close/Cancel/Open and XLSX-last already present); Phase 4 report/xlsx/ui/MCP tests listed above. Does not include `tools/` (unchanged) or docs (Phase 5). |

### Work unit 5 (Phase 5)

| Evidence                | Value                                                                                                                                                                                                                                                                                                            |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command    | See Phase 5 GREEN command (docs + leftover scanner + `test_manifest_version_is_1_33_0`) then leftover 7-test rewrite                                                                                                                                                                                             |
| Focused test result     | **exit 0** — `0 failed, 0 error(s) of 4 tests` (docs GREEN); **exit 0** — `0 failed, 0 error(s) of 7 tests` (leftover MCP/allocation)                                                                                                                                                                            |
| Runtime harness command | `invoke install -m collection` then `invoke start` then `invoke test -m collection --mode=update` from `/home/crisd/projects/seedian/seedian`; scoped `pre-commit run --files` on changed collection paths                                                                                                       |
| Runtime harness result  | install **exit 0**; start **exit 0**; first full suite **exit 1** `0 failed, 7 error(s) of 682 tests` (leftover Close-from-open / partner-detach); after leftover rewrites full suite **exit 0** `0 failed, 0 error(s) of 682 tests`. First pre-commit **exit 1** (ruff E501); retry **exit 0**.                 |
| Rollback boundary       | `AGENTS.md`; `readme/DESCRIPTION.md`; generated `README.rst` (from fragment, not hand-edited); `tests/test_collection_company_migration.py` docs/leftover scanner; leftover rewrites in `tests/test_collection_allocation.py` and `tests/test_collection_mcp_allocation.py`. Does not include voucher-states-ui. |

## Files Changed

| File                                                           | Action      | What Was Done                                                                                                                                                                                         |
| -------------------------------------------------------------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/test_collection_sheet.py`                               | Modified    | Phase 1 four-state lifecycle; Phase 3 drop `action_open_voucher_reassign` tests                                                                                                                       |
| `tests/test_collection_allocation.py`                          | Modified    | Phase 1 iff; Phase 2 related stored `sheet_id`/`partner_id`, `debt_line_ids`, Closed/Cancelled line write/unlink, proposal persist                                                                    |
| `tests/test_collection_mail.py`                                | Modified    | Confirm/Close/Cancel/Open chatter; drop Reopen tracking                                                                                                                                               |
| `tests/test_collection_document_review.py`                     | Modified    | Non-open Review refused; open still succeeds; empty-queue stays open; `_close_open_sheets` audited write                                                                                              |
| `tests/test_collection_company_migration.py`                   | Modified    | `test_manifest_version_is_1_33_0`; migrate exists, XMLID unlink, no sheet-state remap                                                                                                                 |
| `tests/test_collection_ui.py`                                  | Modified    | Phase 2 notebook; Phase 3 drop Reassign header/XMLID/`group_expand`; Payment Vouchers unbound `partner_id`                                                                                            |
| `tests/test_collection_voucher.py`                             | Modified    | No auto-follow; allocated partner UserError; freeze membership+business fields; chatter; keep constraint                                                                                              |
| `models/collection_sheet.py`                                   | Modified    | Phase 1 four-state actions; Phase 2 `debt_line_ids`; Phase 3 drop `action_open_voucher_reassign`                                                                                                      |
| `models/collection_allocation.py`                              | Modified    | Phase 1 iff; Phase 2 freeze `_FROZEN_FIELDS` when sheet Closed/Cancelled; `_membership_is_frozen`; `_FROZEN_SHEET_STATES`                                                                             |
| `models/collection_allocation_line.py`                         | Modified    | Related stored `sheet_id`/`partner_id`; write + `@api.ondelete` when sheet Closed/Cancelled                                                                                                           |
| `models/collection_voucher.py`                                 | Modified    | Phase 1 `_require_review_sheet` Open-only; Phase 3 drop `group_expand`/follow; freeze `sheet_id`/`partner_id`/`_REVIEW_EDITABLE_FIELDS`; keep `_check_voucher_allocation_partner`; `_sheet_is_frozen` |
| `views/collection_views.xml`                                   | Modified    | Phase 1 header Confirm/Close/Cancel/Open; Phase 2 notebook; Phase 3 `<delete>` reassign kanban XMLID and drop Reassign header (statusbar left for Phase 4)                                            |
| `views/collection_allocation_views.xml`                        | Modified    | `sheet_id`/`partner_id`/`line_ids` readonly from `sheet_id.state`; voucher M2M Open-only                                                                                                              |
| `__manifest__.py`                                              | Modified    | `"version": "19.0.1.33.0"`                                                                                                                                                                            |
| `migrations/19.0.1.33.0/post-migrate.py`                       | Created     | Unlink `view_collection_voucher_reassign_kanban` from `ir_ui_view` + `ir_model_data`; no state remap                                                                                                  |
| `openspec/changes/collection-sheet-workflow/tasks.md`          | Modified    | Marked 1.1–1.5, 2.1–2.4, 3.1–3.4, and 4.1–4.3 `[x]`                                                                                                                                                   |
| `openspec/changes/collection-sheet-workflow/apply-progress.md` | Modified    | Merged Phase 1 + Phase 2 + Phase 3 + Phase 4 evidence                                                                                                                                                 |
| `tests/test_collection_sheet_report_data.py`                   | Modified    | Cancelled+closed recon freeze; proposal editable; Open-from-Cancelled keeps values; PDF payload all four states; drop `action_reopen`                                                                 |
| `tests/test_collection_sheet_report.py`                        | Modified    | `_get_report_values` in all four states                                                                                                                                                               |
| `tests/test_collection_sheet_xlsx.py`                          | Modified    | XLSX all four states; unsaved refused; XLSX last without Reassign; three notebook pages                                                                                                               |
| `tests/test_collection_ui.py`                                  | Modified    | Four-state statusbar and header by state; Document Review Open-only `invisible`; no Reopen                                                                                                            |
| `tests/test_collection_mcp_allocation_lookup.py`               | Modified    | GET null on proposal/closed/cancelled; drop create-with-non-open-state                                                                                                                                |
| `tests/test_collection_mcp_allocation.py`                      | Modified    | Create new open while a proposal sheet exists                                                                                                                                                         |
| `models/collection_sheet_report.py`                            | Modified    | Freeze recon writes when sheet Closed or Cancelled; reuse `_FROZEN_SHEET_STATES`                                                                                                                      |
| `views/collection_views.xml`                                   | Modified    | `statusbar_visible="open,proposal,closed,cancelled"` (XLSX already last object button before `state`)                                                                                                 |
| `tests/test_collection_company_migration.py`                   | Modified    | Leftover remaining-tests scanner; AGENTS.md four-state asserts; DESCRIPTION.md four-state asserts                                                                                                     |
| `tests/test_collection_allocation.py`                          | Modified    | Allocated partner-write leftover now refuses; proposal extra voucher created before Confirm                                                                                                           |
| `tests/test_collection_mcp_allocation.py`                      | Modified    | `_close_open_sheet` Confirm then Close; leftover Close-from-open MCP tests                                                                                                                            |
| `AGENTS.md`                                                    | Modified    | Four-state workflow, three tabs, drop Reassign, `19.0.1.33.0`, migrate 1.33.0, one-open still `open` only                                                                                             |
| `readme/DESCRIPTION.md`                                        | Modified    | Four-state sheet lifecycle and Allocations, Vouchers, and Debt                                                                                                                                        |
| `README.rst`                                                   | Regenerated | oca-gen-addon-readme from `readme/DESCRIPTION.md` (not hand-edited)                                                                                                                                   |
| `openspec/changes/collection-sheet-workflow/tasks.md`          | Modified    | Marked 1.1–5.2 `[x]`                                                                                                                                                                                  |
| `openspec/changes/collection-sheet-workflow/apply-progress.md` | Modified    | Merged Phase 1–5 evidence                                                                                                                                                                             |

## Deviations from Design

- **Header buttons in Phase 1**: `views/collection_views.xml` was retargeted so the form
  no longer calls `action_reopen`. Without that, `-u collection` ParseError blocked
  GREEN. Statusbar four keys landed in Phase 4. Reassign header dropped in Phase 3.
  Document Review `invisible` includes `state != 'open'`, matching the Open-only server
  rule.
- Freeze membership UserError string is unchanged
  (`"Closed collection sheets cannot change membership. Reopen first."`) even after
  dropping `action_reopen`, per spec.
- **Closed outsider voucher in Phase 2 tests**: creating a new voucher after Close hits
  the existing membership freeze. The closed-write test now creates and validates the
  outsider before Confirm/Close, then asserts `Command.link` is refused.
- Allocated `partner_id` writes now raise via `_check_voucher_allocation_partner` (kept)
  instead of auto-follow. Confirmed-source partner writes use that constraint
  `UserError` rather than the allocation-membership detach message.
- **Phase 4 MCP**: no `tools/` edits. Proposal-does-not-occupy-open was already true via
  `_open_sheets_for_seller` (`state = 'open'`). Tests document the spec; GET
  create-with-`state='closed'` leftovers were rewritten to audited Confirm/Close/Cancel.
- **Phase 5 leftover MCP Close-from-open**: remaining MCP tests still called
  `action_close()` from `open`. Helper `_close_open_sheet` stamps members
  `validated_collections`, Confirms, then Closes. Proposal extra voucher is created
  while Open so Confirm gate and membership freeze both hold.

## Issues Found

- First 5.2 full suite: **exit 1** `0 failed, 7 error(s) of 682 tests` — leftover
  Close-from-open in `test_collection_mcp_allocation.py` and leftover allocated
  partner-detach success in `test_collection_allocation.py`. Fixed in 5.1 leftover
  rewrite, then full suite **exit 0**.
- First scoped pre-commit: **exit 1** ruff E501 on leftover scanner; ruff-format wrap
  then **exit 0**.
- `invoke install -m collection` stops `seedian-odoo-1`. Phase 5 ran `invoke start`
  after install before the full suite.

## Remaining Tasks

- None. All tasks `[x]`.

## Workload / PR Boundary

- Mode: stacked PR slice
- Current work unit: 5 — Docs+verify
- Boundary: starts at Phase 4 report/MCP/header done with stale AGENTS.md /
  DESCRIPTION.md and leftover remaining tests; ends at four-state docs, leftover tests
  rewritten, full suite 682 green, scoped pre-commit green
- Estimated review budget impact: High overall change; this slice is the docs/verify PR
  (PR5→main)

## Status

18/18 tasks complete (5 Phase 1 + 4 Phase 2 + 4 Phase 3 + 3 Phase 4 + 2 Phase 5). Ready
for verify.
