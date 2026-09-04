```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:36112ae4be742d1df0cb5c29aed50270549f34e4d7b55016aa370fb5164de18d
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 24/24
scenarios: 99/99
test_command: invoke test -m collection --mode=update
test_exit_code: 0
test_output_hash: sha256:02b2ff8c10256ee47321a2c953e4c98108ba993f560c1cff84a07062d21236e6
build_command: invoke install -m collection
build_exit_code: 0
build_output_hash: sha256:8fa1201d294b8221d442cf4369adfea4451c90b3413b107e63f78ca4b7f07030
```

## Verification Report

**Change**: `collection-sheet-workflow`
**Version**: collection `19.0.1.33.0`. Delta specs: `collection-sheets` + `collection-vouchers` + `collection-allocations` + `collection-sheet-report` + `document-review`
**Mode**: Strict TDD

Delta spec counts (actual `### Requirement:` / `#### Scenario:` headings): collection-sheets 13/51 + collection-vouchers 4/20 + collection-allocations 3/13 + collection-sheet-report 3/10 + document-review 1/5 = **24 requirements**; **99 scenarios**. Two REMOVED requirements have zero scenarios. `evidence_revision` is SHA-256 of concatenated exact build then test stdout/stderr. Fresh independent run after maintainer-authorized docs-scanner remediation (`test_agents_md_four_state_workflow` now asserts `" ".join(agents.split())`). Prior fail report 1/682 is superseded by this admitted result.

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 18 |
| Tasks complete | 18 |
| Tasks incomplete | 0 |

All `tasks.md` items 1.1–5.2 are `[x]`. Full spec verification proceeded.

### Build & Tests Execution
**Build**: ✅ Passed (`invoke install -m collection` exit 0). `invoke img-build` was not run. Install stopped `seedian-odoo-1`; `invoke start` then restarted it (exit 0).

```text
invoke install -m collection
...
INFO devel odoo.modules.loading: Modules loaded.
INFO devel odoo.registry: Registry loaded in 3.362s
INFO devel odoo.service.server: Initiating shutdown
exit 0
```

**Tests**: ✅ 682 passed / 0 failed / 0 skipped (`0 failed, 0 error(s) of 682 tests`)

```text
invoke test -m collection --mode=update
INFO devel odoo.tests.stats: collection: 746 tests 33.71s 56484 queries
INFO devel odoo.tests.result: 0 failed, 0 error(s) of 682 tests when loading database 'devel'
exit 0
```

`TestCollectionCompanyMigration.test_agents_md_four_state_workflow` started and did not fail. The one-open phrase in `AGENTS.md` is still documented; the scanner joins whitespace so prettier wrap is not a miss.

**Coverage**: ➖ Not available (config `coverage_threshold: 0`; no coverage tool)

### Spec Compliance Matrix
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Confirm review gate | All members validated_collections | `test_collection_sheet.py` > `test_action_confirm_all_members_validated_collections` | ✅ COMPLIANT |
| Confirm review gate | Empty members pass Confirm | `test_collection_sheet.py` > `test_action_confirm_empty_members_pass` | ✅ COMPLIANT |
| Confirm review gate | Unreviewed member blocks Confirm | `test_collection_sheet.py` > `test_action_confirm_unreviewed_member_blocks` (+ `test_action_confirm_seller_validated_member_blocks`) | ✅ COMPLIANT |
| Four-state sheet editability | Proposal keeps allocation and debt editable | `test_collection_allocation.py` > `test_proposal_draft_line_and_voucher_writes_persist` | ✅ COMPLIANT |
| Four-state sheet editability | Closed and Cancelled freeze business writes | `test_collection_allocation.py` > `test_closed_allocation_writes_refused` / `test_cancelled_draft_line_write_refused`; `test_collection_sheet_report_data.py` > `test_closed_write_guard` / `test_cancelled_write_guard` | ✅ COMPLIANT |
| Four-state sheet editability | Proposal freezes voucher membership | `test_collection_sheet.py` > `test_freeze_rejects_membership_on_proposal`; `test_collection_voucher.py` > `test_proposal_membership_sheet_id_refused` | ✅ COMPLIANT |
| Sheet sequence identity | Sequence assigned on create | `test_collection_sheet.py` > `test_sequence_assigned_on_create` | ✅ COMPLIANT |
| Sheet sequence identity | Numbers isolated per company | `test_collection_company_migration.py` > `test_voucher_and_sheet_numbers_isolated_per_company` | ✅ COMPLIANT |
| Membership, dates, and deletion | Assign and reassign | `test_collection_sheet.py` > `test_reassign_moves_voucher_to_sheet_b_only` | ✅ COMPLIANT |
| Membership, dates, and deletion | Empty sheet | `test_collection_sheet.py` > `test_empty_sheet_dates_false_and_no_received_date` | ✅ COMPLIANT |
| Membership, dates, and deletion | Dates from member create_date | `test_collection_sheet.py` > `test_dates_from_utc_member_create_date` | ✅ COMPLIANT |
| Membership, dates, and deletion | Unlink open unassigns when no allocations | `test_collection_sheet.py` > `test_unlink_sheet_unassigns_vouchers` | ✅ COMPLIANT |
| Membership, dates, and deletion | Unlink open cascades draft allocations | `test_collection_sheet.py` > `test_unlink_open_cascades_draft_allocations` | ✅ COMPLIANT |
| Membership, dates, and deletion | Unlink closed refused even when empty | `test_collection_sheet.py` > `test_unlink_closed_empty_refused` | ✅ COMPLIANT |
| Membership, dates, and deletion | Unlink closed with allocations refused | `test_collection_sheet.py` > `test_unlink_closed_with_allocations_refused` | ✅ COMPLIANT |
| Membership, dates, and deletion | Unlink proposal or cancelled refused | `test_collection_sheet.py` > `test_unlink_proposal_refused` / `test_unlink_cancelled_refused` | ✅ COMPLIANT |
| Collection Sheets UI | Menu and form behaviors | `test_collection_ui.py` > `test_collection_sheets_menu_list_form_search` / `test_collection_sheets_form_statusbar_four_states` | ✅ COMPLIANT |
| Collection Sheets UI | Header actions by state | `test_collection_ui.py` > `test_collection_sheets_form_statusbar_four_states` | ✅ COMPLIANT |
| Collection Sheets UI | Illegal header action refused | `test_collection_sheet.py` > `test_illegal_close_cancel_open_from_open_refused` | ✅ COMPLIANT |
| Mail thread and activities | Message persists on sheet | `test_collection_mail.py` > `test_message_post_persists_on_sheet` | ✅ COMPLIANT |
| Mail thread and activities | Confirm tracks state in chatter | `test_collection_mail.py` > `test_confirm_tracks_state_in_chatter` | ✅ COMPLIANT |
| Mail thread and activities | Close tracks state in chatter | `test_collection_mail.py` > `test_close_tracks_state_in_chatter` | ✅ COMPLIANT |
| Mail thread and activities | Cancel tracks state in chatter | `test_collection_mail.py` > `test_cancel_tracks_state_in_chatter` | ✅ COMPLIANT |
| Mail thread and activities | Open tracks state in chatter | `test_collection_mail.py` > `test_open_tracks_state_in_chatter` | ✅ COMPLIANT |
| Saved-sheet header action opens Document Review | Header action available when flag is on | `test_collection_ui.py` > `test_sheet_form_header_document_review_visible_when_saved_and_flag_on` | ✅ COMPLIANT |
| Saved-sheet header action opens Document Review | Header action hidden or refused when flag is off | `test_collection_ui.py` > `test_sheet_form_header_document_review_hidden_when_flag_off_or_unsaved`; `test_collection_sheet.py` > `test_action_open_document_review_refused_when_flag_off` | ✅ COMPLIANT |
| Saved-sheet header action opens Document Review | Unsaved sheet must not open review | `test_collection_sheet.py` > `test_action_open_document_review_refused_on_new_id` | ✅ COMPLIANT |
| Saved-sheet header action opens Document Review | Sheet action parameters | `test_collection_sheet.py` > `test_action_open_document_review_params_match_each_saved_sheet` | ✅ COMPLIANT |
| Saved-sheet header action opens Document Review | Non-open sheet hides and refuses review | `test_collection_sheet.py` > `test_action_open_document_review_refused_when_not_open`; `test_collection_ui.py` > `test_collection_sheets_form_statusbar_four_states` | ✅ COMPLIANT |
| Open/closed lifecycle | Default open on create | `test_collection_sheet.py` > `test_sequence_assigned_on_create` | ✅ COMPLIANT |
| Open/closed lifecycle | Close when proposal | `test_collection_sheet.py` > `test_action_close_from_proposal_confirms_then_closes` | ✅ COMPLIANT |
| Open/closed lifecycle | Open when no other open | `test_collection_sheet.py` > `test_action_open_from_cancelled_leaves_draft` | ✅ COMPLIANT |
| Open/closed lifecycle | Raw state write rejected | `test_collection_sheet.py` > `test_raw_state_write_routes_to_audited_actions` / `test_raw_state_write_invalid_transition_rejected` | ✅ COMPLIANT |
| Open/closed lifecycle | Open rejected if another open exists | `test_collection_sheet.py` > `test_open_rejected_if_another_open_exists` / `test_blocked_open_keeps_allocations_draft` | ✅ COMPLIANT |
| Open/closed lifecycle | Cancel from proposal or closed | `test_collection_sheet.py` > `test_action_cancel_from_proposal_drafts_allocations` / `test_action_cancel_from_closed_drafts_allocations` | ✅ COMPLIANT |
| Open/closed lifecycle | Illegal transition refused | `test_collection_sheet.py` > `test_illegal_close_cancel_open_from_open_refused` | ✅ COMPLIANT |
| Open/closed lifecycle | Non-open create rejected | `test_collection_sheet.py` > `test_non_open_create_rejected` | ✅ COMPLIANT |
| At most one open sheet per seller (new operations) | Create second open rejected | `test_collection_sheet.py` > `test_create_second_open_rejected` | ✅ COMPLIANT |
| At most one open sheet per seller (new operations) | Open rejected if another open exists | `test_collection_sheet.py` > `test_open_rejected_if_another_open_exists` | ✅ COMPLIANT |
| At most one open sheet per seller (new operations) | More than one open fail-closed on new operations | `test_collection_sheet.py` > `test_leftover_multiple_opens_reject_new_ops` | ✅ COMPLIANT |
| At most one open sheet per seller (new operations) | Confirming extras still succeeds | `test_collection_sheet.py` > `test_leftover_multiple_opens_confirm_still_succeeds` | ✅ COMPLIANT |
| At most one open sheet per seller (new operations) | Same seller may be open in two companies | `test_collection_sheet.py` > `test_same_seller_may_be_open_in_two_companies` | ✅ COMPLIANT |
| At most one open sheet per seller (new operations) | Explicit create remains when auto-create is off | `test_collection_sheet.py` > `test_action_creates_sheet_when_auto_create_off` | ✅ COMPLIANT |
| At most one open sheet per seller (new operations) | Proposal does not occupy one-open | `test_collection_sheet.py` > `test_proposal_does_not_occupy_one_open` | ✅ COMPLIANT |
| Closed sheet membership freeze | Freeze add, remove, and reassign | `test_collection_sheet.py` > `test_freeze_rejects_add_remove_and_reassign` | ✅ COMPLIANT |
| Closed sheet membership freeze | Closed partner_id reuses membership UserError | `test_collection_sheet.py` > `test_freeze_rejects_closed_partner_id_with_membership_error` | ✅ COMPLIANT |
| Closed sheet membership freeze | Closed empty unlink refused | `test_collection_sheet.py` > `test_unlink_closed_empty_refused` | ✅ COMPLIANT |
| Historical sheets remain operable | Disabled-seller sheet stays visible and confirmable | `test_collection_sheet.py` > `test_disabled_seller_sheet_stays_visible_and_confirmable` | ✅ COMPLIANT |
| Sheet form notebook | Three-page notebook with Allocations columns | `test_collection_ui.py` > `test_sheet_form_notebook_three_pages_allocations_columns` | ✅ COMPLIANT |
| Sheet form notebook | Vouchers tab opens existing members only in Open | `test_collection_ui.py` > `test_sheet_form_vouchers_tab_existing_only_in_open` | ✅ COMPLIANT |
| Sheet form notebook | Debt tab amount_applied only in Open or Proposal | `test_collection_ui.py` > `test_sheet_form_debt_tab_amount_applied_only` | ✅ COMPLIANT |
| Sheet-state voucher field guards | Open membership and business fields writable | `test_collection_voucher.py` > `test_open_membership_and_business_fields_writable` | ✅ COMPLIANT |
| Sheet-state voucher field guards | Proposal closed cancelled membership refused | `test_collection_voucher.py` > `test_proposal_membership_sheet_id_refused` / `test_cancelled_membership_sheet_id_refused`; `test_collection_sheet.py` > `test_freeze_rejects_add_remove_and_reassign` | ✅ COMPLIANT |
| Sheet-state voucher field guards | Proposal closed cancelled business fields refused | `test_collection_voucher.py` > `test_proposal_business_fields_refused` / `test_cancelled_business_fields_refused` / `test_closed_business_fields_refused` | ✅ COMPLIANT |
| Sheet-state voucher field guards | Chatter remains writable when frozen | `test_collection_voucher.py` > `test_chatter_remains_writable_when_sheet_frozen` | ✅ COMPLIANT |
| Payment Vouchers UI | Menu and form behaviors | `test_collection_ui.py` > `test_menu_and_action_xmlids` / `test_list_and_search_show_required_fields` / `test_form_statusbar_validate_seller_when_draft` | ✅ COMPLIANT |
| Payment Vouchers UI | Kanban grouped by state | `test_collection_ui.py` > `test_stages_kanban_deleted_action_is_list_form` / `test_reassign_kanban_xmlid_deleted` | ✅ COMPLIANT |
| Payment Vouchers UI | Payment Lines menu absent | `test_collection_ui.py` > `test_payment_line_xmlids_removed` / `test_load_menus_omits_payment_lines` | ✅ COMPLIANT |
| Payment Vouchers UI | Menu sequence locked | `test_collection_ui.py` > `test_menu_and_action_xmlids` | ✅ COMPLIANT |
| Payment Vouchers UI | Search filters | `test_collection_ui.py` > `test_search_filters_draft_validated_seller_collections` / `test_search_filters_each_document_type` / `test_search_created_on_is_date_filter` | ✅ COMPLIANT |
| Payment Vouchers UI | UI create_date visibility | `test_collection_ui.py` > `test_list_and_search_show_required_fields` / `test_form_statusbar_validate_seller_when_draft` | ✅ COMPLIANT |
| Payment Vouchers UI | Customer field has no domain | `test_collection_ui.py` > `test_customer_field_is_partner_id_without_domain` | ✅ COMPLIANT |
| Payment Vouchers UI | sheet_id on list form search | `test_collection_ui.py` > `test_voucher_list_form_search_expose_sheet_id` | ✅ COMPLIANT |
| Payment Vouchers UI | Clear sheet_id unlinks open membership | `test_collection_voucher.py` > `test_open_membership_and_business_fields_writable` | ✅ COMPLIANT |
| Payment Vouchers UI | Closed-sheet unlink denied | `test_collection_voucher.py` > `test_proposal_membership_sheet_id_refused` / `test_cancelled_membership_sheet_id_refused`; `test_collection_sheet.py` > `test_freeze_rejects_add_remove_and_reassign` | ✅ COMPLIANT |
| Partner write follows allocation | Allocated customer change refused | `test_collection_voucher.py` > `test_allocated_partner_write_refused` | ✅ COMPLIANT |
| Partner write follows allocation | Unassign then customer change | `test_collection_voucher.py` > `test_unassign_then_partner_write` | ✅ COMPLIANT |
| Partner write follows allocation | Same-value partner write | `test_collection_voucher.py` > `test_same_value_partner_write_does_not_recompute` | ✅ COMPLIANT |
| Partner write follows allocation | Confirmed source refused | `test_collection_voucher.py` > `test_partner_write_confirmed_source_refused` | ✅ COMPLIANT |
| Partner write follows allocation | Unassigned voucher may change customer | `test_collection_voucher.py` > `test_unassigned_partner_write_does_not_auto_follow` / `test_all_voucher_states_may_change_partner` | ✅ COMPLIANT |
| Partner write follows allocation | Fully applied source no longer auto-moves | `test_collection_voucher.py` > `test_allocated_partner_write_refused_when_residual_zero`; `test_collection_allocation.py` > `test_fully_applied_source_detach_via_partner_write_succeeds` | ✅ COMPLIANT |
| Cancelled and Closed allocation write guards | Cancelled draft line write refused | `test_collection_allocation.py` > `test_cancelled_draft_line_write_refused` | ✅ COMPLIANT |
| Cancelled and Closed allocation write guards | Closed allocation writes refused | `test_collection_allocation.py` > `test_closed_allocation_writes_refused` | ✅ COMPLIANT |
| Cancelled and Closed allocation write guards | Proposal draft remains writable | `test_collection_allocation.py` > `test_proposal_draft_line_and_voucher_writes_persist` | ✅ COMPLIANT |
| Cancelled and Closed allocation write guards | Cancelled line unlink refused | `test_collection_allocation.py` > `test_cancelled_line_unlink_refused` | ✅ COMPLIANT |
| MCP open sheet is state open only | Proposal does not occupy MCP open | `test_collection_mcp_allocation_lookup.py` > `test_proposal_sheet_does_not_occupy_mcp_open` | ✅ COMPLIANT |
| MCP open sheet is state open only | New open while proposal exists | `test_collection_mcp_allocation.py` > `test_create_new_open_while_proposal_exists` | ✅ COMPLIANT |
| MCP open sheet is state open only | Closed or cancelled not used as open | `test_collection_mcp_allocation_lookup.py` > `test_closed_sheet_only_returns_null` / `test_cancelled_sheet_only_returns_null` | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Create defaults to draft | `test_collection_allocation.py` > `test_create_defaults_to_draft`; `test_collection_mcp_allocation.py` > `test_first_create_draft_revision_one_totals` | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Close confirms then closes | `test_collection_allocation.py` > `test_close_from_proposal_confirms_then_closes` | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Cancel drafts allocations | `test_collection_allocation.py` > `test_cancel_from_proposal_drafts_allocations` / `test_cancel_from_closed_drafts_allocations` | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Open from cancelled leaves draft | `test_collection_allocation.py` > `test_open_from_cancelled_leaves_draft` | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Confirm does not confirm allocations | `test_collection_allocation.py` > `test_confirm_does_not_confirm_allocations` | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Invariant-breaking state write refused | `test_collection_allocation.py` > `test_iff_constraint_skips_under_audited_context` / `test_validate_and_reject_are_gone` | ✅ COMPLIANT |
| PDF and XLSX available in all sheet states | PDF in all four states | `test_collection_sheet_report.py` > `test_pdf_in_all_four_states`; `test_collection_sheet_report_data.py` > `test_payload_in_all_four_states` | ✅ COMPLIANT |
| PDF and XLSX available in all sheet states | XLSX in all four states | `test_collection_sheet_xlsx.py` > `test_xlsx_in_all_four_states` | ✅ COMPLIANT |
| PDF and XLSX available in all sheet states | Unsaved still refused | `test_collection_sheet_report_data.py` > `test_unsaved_sheet_refused`; `test_collection_sheet_xlsx.py` > `test_unsaved_xlsx_refused` | ✅ COMPLIANT |
| Sheet reconciliation inputs | Percent range | `test_collection_sheet_report_data.py` > `test_percent_range_persists_bounds` / `test_percent_outside_range_raises` | ✅ COMPLIANT |
| Sheet reconciliation inputs | Closed write guard | `test_collection_sheet_report_data.py` > `test_closed_write_guard` / `test_cancelled_write_guard` | ✅ COMPLIANT |
| Sheet reconciliation inputs | Open edit then cancel keeps values | `test_collection_sheet_report_data.py` > `test_open_from_cancelled_keeps_recon_values` | ✅ COMPLIANT |
| Sheet reconciliation inputs | Proposal recon remains editable | `test_collection_sheet_report_data.py` > `test_proposal_recon_remains_editable` | ✅ COMPLIANT |
| XLSX workbook and percent scale | Zip freeze and cached SUM | `test_collection_sheet_xlsx.py` > `test_xlsx_bytes_are_zip_with_workbook` / `test_xlsx_print_setup_freeze_and_column_width` / `test_xlsx_cached_subtotals_match_payload` | ✅ COMPLIANT |
| XLSX workbook and percent scale | Percent scale 0–100 to 0.0% | `test_collection_sheet_xlsx.py` > `test_xlsx_percent_scale_4_5_is_excel_fraction` | ✅ COMPLIANT |
| XLSX workbook and percent scale | Header button last and three notebook pages | `test_collection_sheet_xlsx.py` > `test_header_xlsx_button_last_before_state` / `test_sheet_form_three_notebook_pages_recon_second_group` | ✅ COMPLIANT |
| Sheet identifier required on review operations | Required sheet context | `test_collection_document_review.py` > `test_review_queue_refuses_missing_or_invalid_sheet_id` / `test_review_mutations_refuse_missing_or_invalid_sheet_id` | ✅ COMPLIANT |
| Sheet identifier required on review operations | Stale membership | `test_collection_document_review.py` > `test_stale_sheet_membership_mutations_are_refused` | ✅ COMPLIANT |
| Sheet identifier required on review operations | OWL and RPC arguments include the sheet identifier | `test_collection_document_review.py` > `test_owl_review_rpcs_pass_sheet_id_from_action_params` | ✅ COMPLIANT |
| Sheet identifier required on review operations | Open sheet identifier still works | `test_collection_document_review.py` > `test_review_rpcs_still_succeed_on_open_sheet` | ✅ COMPLIANT |
| Sheet identifier required on review operations | Non-open sheet identifier refused | `test_collection_document_review.py` > `test_review_rpcs_refuse_non_open_sheet` | ✅ COMPLIANT |

**Compliance summary**: 99/99 scenarios compliant (covering tests exist and passed on this run).

REMOVED requirements with zero scenarios (not in matrix): Reassign header action and kanban — proven by `test_reassign_kanban_xmlid_deleted`, `test_sheet_form_header_has_no_reassign`, `test_action_open_voucher_reassign_removed`; Context-gated partner group_expand — proven by `test_partner_group_expand_dropped`.

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| Confirm review gate | ✅ Implemented | `action_confirm` from open; empty pass; unreviewed/seller-validated block |
| Four-state sheet editability | ✅ Implemented | Proposal allocations/debt writable; membership Open-only |
| Sheet sequence identity | ✅ Implemented | `CS/<year>/` on create; per-company isolation |
| Membership, dates, and deletion | ✅ Implemented | Unlink open cascades; non-open unlink refused |
| Collection Sheets UI | ✅ Implemented | Four-state statusbar; Confirm/Close/Cancel/Open; no Reopen |
| Mail thread and activities | ✅ Implemented | Confirm/Close/Cancel/Open tracked |
| Saved-sheet header action opens Document Review | ✅ Implemented | Header + `_require_review_sheet` Open-only |
| Open/closed lifecycle | ✅ Implemented | Four keys; audited actions; no remap migrate |
| At most one open sheet per seller (new operations) | ✅ Implemented | Counts `open` only; proposal does not occupy |
| Closed sheet membership freeze | ✅ Implemented | Same UserError string kept after dropping Reopen |
| Historical sheets remain operable | ✅ Implemented | Disabled seller Confirm/Open skip helper |
| Sheet form notebook | ✅ Implemented | Allocations / Vouchers / Debt |
| Reassign header action and kanban | ✅ Removed | XMLID `<delete>` + migrate 1.33.0 unlink |
| Sheet-state voucher field guards | ✅ Implemented | Membership + `_REVIEW_EDITABLE_FIELDS`; chatter allowed |
| Payment Vouchers UI | ✅ Implemented | list,form; no stages/reassign kanban; sequence 10 |
| Partner write follows allocation | ✅ Implemented | No auto-follow; constraint UserError while allocated |
| Context-gated partner group_expand | ✅ Removed | `_read_group_partner_ids` dropped |
| Cancelled and Closed allocation write guards | ✅ Implemented | Sheet-state freeze even when draft |
| MCP open sheet is state open only | ✅ Implemented | `_open_sheets_for_seller` unchanged (`tools/` not edited) |
| Draft default and confirm-on-close invariant | ✅ Implemented | Close confirms; Cancel drafts; Confirm does not |
| PDF and XLSX available in all sheet states | ✅ Implemented | Four-state payload/download |
| Sheet reconciliation inputs | ✅ Implemented | Freeze Closed+Cancelled; Proposal editable |
| XLSX workbook and percent scale | ✅ Implemented | A6 freeze; percent/100; XLSX last; three pages |
| Sheet identifier required on review operations | ✅ Implemented | Non-open refuses; open still succeeds |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| Four Selection keys, no SQL remap | ✅ Yes | `open`/`proposal`/`closed`/`cancelled`; migrate 1.33.0 unlinks reassign XMLID only |
| Audited Confirm/Close/Cancel/Open; drop Reopen | ✅ Yes | Header retargeted in Phase 1 to avoid ParseError |
| Confirm gate every member `validated_collections` | ✅ Yes | Empty members pass |
| Allocation iff + freeze Closed/Cancelled | ✅ Yes | `_DRAFT_SHEET_STATES` / `_FROZEN_SHEET_STATES` |
| Debt tab via related stored line `sheet_id` | ✅ Yes | `debt_line_ids`; create/delete off |
| Drop Reassign / `group_expand` / auto-follow | ✅ Yes | Constraint kept |
| Review server gate Open-only | ✅ Yes | Header `invisible` includes `state != 'open'` |
| MCP keep `open` only; no `tools/` change | ✅ Yes | Regression tests only |
| Header buttons in Phase 1 (design listed views later) | ⚠️ Deviation | Documented in apply-progress; required for `-u` |
| Freeze UserError still says "Reopen first." | ✅ Yes | Spec reuse of existing string |
| `_confirm()` helper can leave confirmed allocation on open sheet | ⚠️ Deviation | Used by leftover freeze/partner-write tests; Close path still confirms-then-closes |

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | Found in apply-progress TDD Cycle Evidence table (18 task rows) |
| All tasks have tests | ✅ | 18/18 tasks name test files that exist |
| RED confirmed (tests exist) | ✅ | 18/18 listed test files present under `tests/` |
| GREEN confirmed (tests pass) | ✅ | 18/18 hold; full suite `0 failed, 0 error(s) of 682 tests` including remediated `test_agents_md_four_state_workflow` |
| Triangulation adequate | ⚠️ | Iff has draft on open/proposal/cancelled; chatter frozen path covers proposal+closed, not cancelled; invariant-breaking named case is confirmed-on-open |
| Safety Net for modified files | ✅ | Apply reported pre-edit nets for Phases 1–5; not re-run historically |

**TDD Compliance**: 5/6 checks passed (triangulation warning only)

---

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 0 | 0 | Odoo TransactionCase (not used in isolation) |
| Integration | 459 | 12 | Odoo TransactionCase / containerized PostgreSQL (`invoke test -m collection --mode=update`) |
| E2E | 0 | 0 | not installed |
| **Total** | **459** | **12** | changed test files only; full suite 682 |

Changed files: `test_collection_sheet.py` (82), `test_collection_allocation.py` (60), `test_collection_mail.py` (17), `test_collection_document_review.py` (51), `test_collection_company_migration.py` (15), `test_collection_ui.py` (62), `test_collection_voucher.py` (72), `test_collection_sheet_report_data.py` (22), `test_collection_sheet_report.py` (7), `test_collection_sheet_xlsx.py` (14), `test_collection_mcp_allocation_lookup.py` (19), `test_collection_mcp_allocation.py` (38).

---

### Changed File Coverage
Coverage analysis skipped — no coverage tool detected

---

### Assertion Quality
| File | Line | Assertion | Issue | Severity |
|------|------|-----------|-------|----------|
| `tests/test_collection_ui.py` | 1356 | `self.assertEqual(first_child.get("class"), "oe_button_box")` | CSS class / implementation detail | WARNING |
| `tests/test_collection_ui.py` | 1367 | `self.assertIn("oe_stat_button", (button.get("class") or "").split())` | CSS class / implementation detail | WARNING |
| `tests/test_collection_ui.py` | 1552 | `self.assertEqual(first_child.get("class"), "oe_button_box")` | CSS class / implementation detail | WARNING |
| `tests/test_collection_ui.py` | 1563 | `self.assertIn("oe_stat_button", (button.get("class") or "").split())` | CSS class / implementation detail | WARNING |

**Assertion quality**: 0 CRITICAL, 4 WARNING

No tautologies, ghost loops, or production-code-free assertions found in the changed tests. Remaining assertions exercise ORM/UI/MCP behavior. The AGENTS.md one-open scanner now joins whitespace and is not a trivial assertion.

---

### Quality Metrics
**Linter**: ✅ No errors (`pre-commit run --files odoo/custom/src/private/collection/**` exit 0). Optional pylint C8101 `manifest-required-author` on `__manifest__.py` (not in mandatory hook).
**Type Checker**: ➖ Not available

### Issues Found
**CRITICAL**: None

**WARNING**:
- CSS class assertions on sheet/allocation stat buttons.
- Frozen voucher chatter test covers proposal and closed, not cancelled.
- Iff invariant dedicated non-audited refuse is confirmed-on-open; draft-on-closed raw write is not a named test.
- `_confirm()` test helper can persist confirmed allocations on an open sheet (iff would reject outside audited Close).
- Optional pylint C8101 author on manifest.

**SUGGESTION**:
- Rename leftover `*_detach_*_succeeds` tests to `*_refused` (body already asserts `UserError`).

### Verdict
PASS WITH WARNINGS
Full suite green (682/682). All 24 requirements and 99 scenarios have passing covering tests. Remaining warnings are triangulation, CSS-class asserts, leftover `*_succeeds` names, and documented design deviations; none block archive.
