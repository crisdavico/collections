```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:f74330c373878b27430c93091af6043ac8be0c4b23101d120efb7190462803de
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 24/24
scenarios: 124/124
test_command: invoke test -m collection --mode=update
test_exit_code: 0
test_output_hash: sha256:df881cba8fac063b72a25835cee7e56e161d65281d9fa95f26bfd1185090c15d
build_command: invoke img-build
build_exit_code: 0
build_output_hash: sha256:eb65abde996be93eb0525f9085bc70fdd581504a8baf3ea5625e6cc6a1af96cd
```

## Verification Report

**Change**: seller-close-submitted-sheet **Version**: collection 19.0.1.42.0 **Mode**:
Strict TDD

Delta-spec recount from `openspec/changes/seller-close-submitted-sheet/specs/` (ADDED +
MODIFIED only): **24 requirements**, **124 scenarios**. Spec phase claim 24/124 matches
this recount.

### Completeness

| Metric           | Value |
| ---------------- | ----- |
| Tasks total      | 17    |
| Tasks complete   | 17    |
| Tasks incomplete | 0     |

All 17 tasks in `tasks.md` are `[x]`. Apply-progress records Phases 1–6 GREEN.
Completeness does not imply scenario coverage.

### Build & Tests Execution

**Build**: ✅ Passed (`invoke img-build`, exit 0, ~69.2s). Image
`registry.eynes.com.ar/seedian/seedian:master-latest` built. Hash is SHA-256 of exact
invoke stdout/stderr (the captured file minus the trailing `EXIT:0\n` appended by the
wrapper).

```text
invoke img-build
[+] Building 78.7s (12/12) FINISHED
 => [1/1] FROM ghcr.io/tecnativa/doodba:19.0-onbuild@sha256:aca3cda0c8a2e…
 => [ 5/43] ONBUILD RUN --mount=target=/var/lib/apt/lists,type=cache…  59.4s
 => exporting to image  15.3s
 ✔ Image registry.eynes.com.ar/seedian/seedian:master-latest Built  69.2s
exit 0
```

**Tests**: ✅ 846 passed / ❌ 0 failed / ⚠️ 0 skipped (Odoo:
`0 failed, 0 error(s) of 846 tests when loading database 'devel'`; stats also logged
`collection: 920 tests 53.00s` including setup). Command from Doodba root:
`invoke test -m collection --mode=update`. Six covering tests added after the prior
FAIL.

```text
invoke test -m collection --mode=update
odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection
INFO devel odoo.tests.result: 0 failed, 0 error(s) of 846 tests when loading database 'devel'
exit 0
```

Sibling `invoke test -m collection_receipt_proposal --mode=update` was **not** re-run
this verify. Phase 5 apply-progress recorded **2 failed, 1 error of 134** in
`TestReceiptProposalOrder` (pre-existing; not the collection gate).

**Coverage**: ➖ Not available (openspec `testing.coverage.available: false`).

**Lint (supporting)**: scoped
`pre-commit run --files odoo/custom/src/private/collection/**` Passed. Optional pylint
C8101 `manifest-required-author` on `__manifest__.py` (pre-existing).

### Spec Compliance Matrix

Statuses: ✅ COMPLIANT, ⚠️ PARTIAL. No UNTESTED or FAILING rows (collection suite
passed).

#### collection-sheets — Seller Close from open

| Requirement            | Scenario                         | Test                                                                                            | Result       |
| ---------------------- | -------------------------------- | ----------------------------------------------------------------------------------------------- | ------------ |
| Seller Close from open | Open sheet closes to submitted   | `tests/test_collection_sheet.py > test_action_seller_close_validated_collections_member_passes` | ✅ COMPLIANT |
| Seller Close from open | Empty members pass Seller Close  | `tests/test_collection_sheet.py > test_action_seller_close_empty_members_pass`                  | ✅ COMPLIANT |
| Seller Close from open | Draft members block Seller Close | `tests/test_collection_sheet.py > test_action_seller_close_draft_members_name_offenders`        | ✅ COMPLIANT |
| Seller Close from open | Non-open Seller Close refused    | `tests/test_collection_sheet.py > test_action_seller_close_refused_from_every_non_open_state`   | ✅ COMPLIANT |

#### collection-sheets — MCP write close_collection_sheet

| Requirement                      | Scenario                              | Test                                                                                                                                             | Result       |
| -------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ------------ |
| MCP write close_collection_sheet | Internal seller closes the open sheet | `tests/test_collection_mcp_sheet_close.py > test_internal_seller_closes_open_sheet`                                                              | ✅ COMPLIANT |
| MCP write close_collection_sheet | Zero open sheets raise not null       | `tests/test_collection_mcp_sheet_close.py > test_zero_open_sheets_raise_user_error_not_null`                                                     | ✅ COMPLIANT |
| MCP write close_collection_sheet | sheet_id rejected                     | `tests/test_collection_mcp_sheet_close.py > test_sheet_id_is_rejected`                                                                           | ✅ COMPLIANT |
| MCP write close_collection_sheet | Next write uses a new open sheet      | `tests/test_collection_mcp_sheet_close.py > test_next_write_uses_a_new_open_sheet` (ORM `_create_sheet`, not MCP `create_collection_allocation`) | ⚠️ PARTIAL   |
| MCP write close_collection_sheet | Non-internal close refused            | `tests/test_collection_mcp_sheet_close.py > test_portal_and_public_callers_denied_access_error`                                                  | ✅ COMPLIANT |

#### collection-sheets — Sheet sequence identity

| Requirement             | Scenario                     | Test                                                                                               | Result       |
| ----------------------- | ---------------------------- | -------------------------------------------------------------------------------------------------- | ------------ |
| Sheet sequence identity | Sequence assigned on create  | `tests/test_collection_sheet.py > test_sequence_assigned_on_create`                                | ✅ COMPLIANT |
| Sheet sequence identity | Numbers isolated per company | `tests/test_collection_company_migration.py > test_voucher_and_sheet_numbers_isolated_per_company` | ✅ COMPLIANT |

#### collection-sheets — Membership, dates, and deletion

| Requirement                     | Scenario                                  | Test                                                                                                                           | Result       |
| ------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------------ |
| Membership, dates, and deletion | Assign and reassign                       | `tests/test_collection_sheet.py > test_reassign_moves_voucher_to_sheet_b_only`                                                 | ✅ COMPLIANT |
| Membership, dates, and deletion | Empty sheet                               | `tests/test_collection_sheet.py > test_empty_sheet_dates_false_and_no_received_date`                                           | ✅ COMPLIANT |
| Membership, dates, and deletion | Dates from member create_date             | `tests/test_collection_sheet.py > test_dates_from_utc_member_create_date`                                                      | ✅ COMPLIANT |
| Membership, dates, and deletion | Unlink open unassigns when no allocations | `tests/test_collection_sheet.py > test_unlink_sheet_unassigns_vouchers`                                                        | ✅ COMPLIANT |
| Membership, dates, and deletion | Unlink open cascades draft allocations    | `tests/test_collection_sheet.py > test_unlink_open_cascades_draft_allocations`                                                 | ✅ COMPLIANT |
| Membership, dates, and deletion | Unlink closed refused even when empty     | `tests/test_collection_sheet.py > test_unlink_closed_empty_refused`                                                            | ✅ COMPLIANT |
| Membership, dates, and deletion | Unlink closed with allocations refused    | `tests/test_collection_sheet.py > test_unlink_closed_with_allocations_refused`                                                 | ✅ COMPLIANT |
| Membership, dates, and deletion | Unlink proposal or cancelled refused      | `tests/test_collection_sheet.py > test_unlink_proposal_refused` + `test_unlink_cancelled_refused`                              | ✅ COMPLIANT |
| Membership, dates, and deletion | Submitted membership add and remove       | `tests/test_collection_sheet.py > test_submitted_membership_add_and_remove` (membership persists; chatter change not asserted) | ⚠️ PARTIAL   |
| Membership, dates, and deletion | Unlink submitted refused                  | `tests/test_collection_sheet.py > test_unlink_submitted_refused`                                                               | ✅ COMPLIANT |

#### collection-sheets — Collection Sheets UI

| Requirement          | Scenario                      | Test                                                                                                                               | Result       |
| -------------------- | ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| Collection Sheets UI | Menu and form behaviors       | `tests/test_collection_ui.py > test_collection_sheets_menu_list_form_search` + `test_collection_sheets_form_statusbar_five_states` | ✅ COMPLIANT |
| Collection Sheets UI | Header actions by state       | `tests/test_collection_ui.py > test_collection_sheets_form_statusbar_five_states`                                                  | ✅ COMPLIANT |
| Collection Sheets UI | Illegal header action refused | `tests/test_collection_sheet.py > test_illegal_close_cancel_open_from_open_refused` + `test_confirm_from_open_refused`             | ✅ COMPLIANT |

#### collection-sheets — Mail thread and activities

| Requirement                | Scenario                             | Test                                                                                                                                   | Result       |
| -------------------------- | ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| Mail thread and activities | Message persists on sheet            | `tests/test_collection_mail.py > test_message_post_persists_on_sheet`                                                                  | ✅ COMPLIANT |
| Mail thread and activities | Confirm tracks state in chatter      | `tests/test_collection_mail.py > test_confirm_tracks_state_in_chatter`                                                                 | ✅ COMPLIANT |
| Mail thread and activities | Close tracks state in chatter        | `tests/test_collection_mail.py > test_close_tracks_state_in_chatter`                                                                   | ✅ COMPLIANT |
| Mail thread and activities | Cancel tracks state in chatter       | `tests/test_collection_mail.py > test_cancel_tracks_state_in_chatter` (proposal→cancelled only; submitted Cancel not chatter-asserted) | ⚠️ PARTIAL   |
| Mail thread and activities | Seller Close tracks state in chatter | `tests/test_collection_mail.py > test_close_tracks_state_in_chatter` (Open→Submitted by Seller; declared amounts not tracked)          | ⚠️ PARTIAL   |
| Mail thread and activities | Reinstate tracks state in chatter    | `tests/test_collection_mail.py > test_open_tracks_state_in_chatter`                                                                    | ✅ COMPLIANT |

#### collection-sheets — Saved-sheet header action opens Document Review

| Requirement                                     | Scenario                                         | Test                                                                                                                                                                                               | Result       |
| ----------------------------------------------- | ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| Saved-sheet header action opens Document Review | Header action available when flag is on          | `tests/test_collection_ui.py > test_sheet_form_header_document_review_visible_when_saved_and_flag_on`                                                                                              | ✅ COMPLIANT |
| Saved-sheet header action opens Document Review | Header action hidden or refused when flag is off | `tests/test_collection_ui.py > test_sheet_form_header_document_review_hidden_when_flag_off_or_unsaved` + `tests/test_collection_sheet.py > test_action_open_document_review_refused_when_flag_off` | ✅ COMPLIANT |
| Saved-sheet header action opens Document Review | Unsaved sheet must not open review               | `tests/test_collection_sheet.py > test_action_open_document_review_refused_on_new_id`                                                                                                              | ✅ COMPLIANT |
| Saved-sheet header action opens Document Review | Sheet action parameters                          | `tests/test_collection_sheet.py > test_action_open_document_review_returns_client_action_with_sheet_id`                                                                                            | ✅ COMPLIANT |
| Saved-sheet header action opens Document Review | Submitted sheet opens review                     | `tests/test_collection_sheet.py > test_action_open_document_review_succeeds_when_submitted`                                                                                                        | ✅ COMPLIANT |
| Saved-sheet header action opens Document Review | Non-reviewable sheet hides and refuses review    | `tests/test_collection_sheet.py > test_action_open_document_review_refused_when_not_open`                                                                                                          | ✅ COMPLIANT |

#### collection-sheets — Open/closed lifecycle

| Requirement           | Scenario                                 | Test                                                                                                                                   | Result       |
| --------------------- | ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| Open/closed lifecycle | Default open on create                   | `tests/test_collection_sheet.py > test_sequence_assigned_on_create`                                                                    | ✅ COMPLIANT |
| Open/closed lifecycle | Close when proposal                      | `tests/test_collection_sheet.py > test_action_close_from_proposal_confirms_then_closes`                                                | ✅ COMPLIANT |
| Open/closed lifecycle | Reinstate from cancelled to submitted    | `tests/test_collection_sheet.py > test_reinstate_succeeds_while_seller_has_a_new_open_sheet`                                           | ✅ COMPLIANT |
| Open/closed lifecycle | Raw state write rejected                 | `tests/test_collection_sheet.py > test_raw_state_write_routes_to_audited_actions` + `test_raw_state_write_invalid_transition_rejected` | ✅ COMPLIANT |
| Open/closed lifecycle | Cancel from submitted proposal or closed | `tests/test_collection_sheet.py > test_action_cancel_from_submitted_drafts_allocations` + proposal/closed cancel tests                 | ✅ COMPLIANT |
| Open/closed lifecycle | Confirm from open refused                | `tests/test_collection_sheet.py > test_confirm_from_open_refused`                                                                      | ✅ COMPLIANT |
| Open/closed lifecycle | Submitted cannot return to open          | `tests/test_collection_sheet.py > test_submitted_cannot_return_to_open`                                                                | ✅ COMPLIANT |
| Open/closed lifecycle | Cancelled cannot return to open          | `tests/test_collection_sheet.py > test_cancelled_cannot_return_to_open`                                                                | ✅ COMPLIANT |
| Open/closed lifecycle | Proposal cannot return to submitted      | `tests/test_collection_sheet.py > test_action_seller_close_refused_from_every_non_open_state`                                          | ✅ COMPLIANT |
| Open/closed lifecycle | Illegal transition from open refused     | `tests/test_collection_sheet.py > test_illegal_close_cancel_open_from_open_refused`                                                    | ✅ COMPLIANT |
| Open/closed lifecycle | Non-open create rejected                 | `tests/test_collection_sheet.py > test_non_open_create_rejected`                                                                       | ✅ COMPLIANT |

#### collection-sheets — At most one open sheet per seller

| Requirement                                        | Scenario                                         | Test                                                                                         | Result       |
| -------------------------------------------------- | ------------------------------------------------ | -------------------------------------------------------------------------------------------- | ------------ |
| At most one open sheet per seller (new operations) | Create second open rejected                      | `tests/test_collection_sheet.py > test_create_second_open_rejected`                          | ✅ COMPLIANT |
| At most one open sheet per seller (new operations) | Reinstate ignores one-open                       | `tests/test_collection_sheet.py > test_reinstate_succeeds_while_seller_has_a_new_open_sheet` | ✅ COMPLIANT |
| At most one open sheet per seller (new operations) | More than one open fail-closed on new operations | `tests/test_collection_sheet.py > test_leftover_multiple_opens_reject_new_ops`               | ✅ COMPLIANT |
| At most one open sheet per seller (new operations) | Leftover open extras cannot Confirm              | `tests/test_collection_sheet.py > test_leftover_open_extras_cannot_confirm`                  | ✅ COMPLIANT |
| At most one open sheet per seller (new operations) | Same seller may be open in two companies         | `tests/test_collection_sheet.py > test_same_seller_may_be_open_in_two_companies`             | ✅ COMPLIANT |
| At most one open sheet per seller (new operations) | Explicit create remains when auto-create is off  | `tests/test_collection_sheet.py > test_action_creates_sheet_when_auto_create_off`            | ✅ COMPLIANT |
| At most one open sheet per seller (new operations) | Submitted does not occupy one-open               | `tests/test_collection_mcp_sheet_close.py > test_next_write_uses_a_new_open_sheet`           | ✅ COMPLIANT |
| At most one open sheet per seller (new operations) | Proposal does not occupy one-open                | `tests/test_collection_sheet.py > test_proposal_does_not_occupy_one_open`                    | ✅ COMPLIANT |

#### collection-sheets — Closed sheet membership freeze

| Requirement                    | Scenario                                      | Test                                                                                                             | Result       |
| ------------------------------ | --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ------------ |
| Closed sheet membership freeze | Freeze add, remove, and reassign              | `tests/test_collection_sheet.py > test_freeze_rejects_add_remove_and_reassign` + proposal/cancelled freeze tests | ✅ COMPLIANT |
| Closed sheet membership freeze | Closed partner_id reuses membership UserError | `tests/test_collection_sheet.py > test_freeze_rejects_closed_partner_id_with_membership_error`                   | ✅ COMPLIANT |
| Closed sheet membership freeze | Closed empty unlink refused                   | `tests/test_collection_sheet.py > test_unlink_closed_empty_refused`                                              | ✅ COMPLIANT |
| Closed sheet membership freeze | Submitted membership not frozen               | `tests/test_collection_sheet.py > test_submitted_membership_add_and_remove`                                      | ✅ COMPLIANT |

#### collection-sheets — Historical sheets remain operable

| Requirement                       | Scenario                                            | Test                                                                                                                                                                               | Result       |
| --------------------------------- | --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| Historical sheets remain operable | Disabled-seller sheet stays visible and confirmable | `tests/test_collection_sheet.py > test_disabled_seller_sheet_stays_visible_and_confirmable` (disables then `confirm_sheet` from open, not Confirm from an already-submitted sheet) | ⚠️ PARTIAL   |
| Historical sheets remain operable | Disabled-seller open sheet remains closeable        | `tests/test_collection_sheet.py > test_disabled_seller_open_sheet_remains_closeable`                                                                                               | ✅ COMPLIANT |

#### collection-sheets — Sheet form notebook

| Requirement         | Scenario                                                      | Test                                                                                     | Result       |
| ------------------- | ------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------ |
| Sheet form notebook | Three-page notebook with Allocations columns                  | `tests/test_collection_ui.py > test_sheet_form_notebook_three_pages_allocations_columns` | ✅ COMPLIANT |
| Sheet form notebook | Vouchers tab opens existing members only in Open or Submitted | `tests/test_collection_ui.py > test_sheet_form_vouchers_tab_existing_only_in_open`       | ✅ COMPLIANT |
| Sheet form notebook | Debt tab amount_applied only in Open Submitted or Proposal    | `tests/test_collection_ui.py > test_sheet_form_debt_tab_amount_applied_only`             | ✅ COMPLIANT |

#### collection-sheets — Confirm review gate

| Requirement         | Scenario                          | Test                                                                                     | Result       |
| ------------------- | --------------------------------- | ---------------------------------------------------------------------------------------- | ------------ |
| Confirm review gate | All members validated_collections | `tests/test_collection_sheet.py > test_action_confirm_all_members_validated_collections` | ✅ COMPLIANT |
| Confirm review gate | Empty members pass Confirm        | `tests/test_collection_sheet.py > test_action_confirm_empty_members_pass`                | ✅ COMPLIANT |
| Confirm review gate | Unreviewed member blocks Confirm  | `tests/test_collection_sheet.py > test_action_confirm_unreviewed_member_blocks`          | ✅ COMPLIANT |

#### collection-sheets — Four-state sheet editability

| Requirement                  | Scenario                                           | Test                                                                                                                                                            | Result       |
| ---------------------------- | -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| Four-state sheet editability | Proposal keeps allocation and debt editable        | `tests/test_collection_allocation.py > test_proposal_draft_line_and_voucher_writes_persist`                                                                     | ✅ COMPLIANT |
| Four-state sheet editability | Closed and Cancelled freeze business writes        | `tests/test_collection_allocation.py > test_closed_allocation_writes_refused` + cancelled line/receipt tests + recon guards                                     | ✅ COMPLIANT |
| Four-state sheet editability | Proposal freezes voucher membership                | `tests/test_collection_sheet.py > test_freeze_rejects_membership_on_proposal`                                                                                   | ✅ COMPLIANT |
| Four-state sheet editability | Submitted keeps allocation and membership editable | `tests/test_collection_sheet.py > test_submitted_membership_add_and_remove` + `tests/test_collection_allocation.py > test_create_draft_allocation_on_submitted` | ✅ COMPLIANT |

#### collection-sheet-report

| Requirement                                 | Scenario                                   | Test                                                                                                                                          | Result       |
| ------------------------------------------- | ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| Submitted Spanish report label              | Submitted prints Rendida                   | `tests/test_collection_company_migration.py > test_sheet_report_labels_include_rendida` + five-state payload                                  | ✅ COMPLIANT |
| Sheet reconciliation inputs                 | Percent range                              | `tests/test_collection_sheet_report_data.py > test_percent_range_persists_bounds` + `test_percent_outside_range_raises`                       | ✅ COMPLIANT |
| Sheet reconciliation inputs                 | Closed write guard                         | `tests/test_collection_sheet_report_data.py > test_closed_write_guard` + `test_cancelled_write_guard`                                         | ✅ COMPLIANT |
| Sheet reconciliation inputs                 | Open edit then cancel keeps values         | `tests/test_collection_sheet_report_data.py > test_open_from_cancelled_keeps_recon_values`                                                    | ✅ COMPLIANT |
| Sheet reconciliation inputs                 | Combined close write persists declarations | `tests/test_collection_sheet.py > test_action_seller_close_validated_collections_member_passes` + MCP amount tests                            | ✅ COMPLIANT |
| Sheet reconciliation inputs                 | Submitted freezes seller declarations only | `tests/test_collection_sheet_report_data.py > test_submitted_freezes_seller_declarations_only`                                                | ✅ COMPLIANT |
| Sheet reconciliation inputs                 | Proposal recon rate remains editable       | `tests/test_collection_sheet_report_data.py > test_proposal_recon_remains_editable`                                                           | ✅ COMPLIANT |
| PDF and XLSX available in all sheet states  | PDF in all five states                     | `tests/test_collection_sheet_report.py > test_pdf_in_all_five_states`                                                                         | ✅ COMPLIANT |
| PDF and XLSX available in all sheet states  | XLSX in all five states                    | `tests/test_collection_sheet_xlsx.py > test_xlsx_in_all_five_states`                                                                          | ✅ COMPLIANT |
| PDF and XLSX available in all sheet states  | Unsaved still refused                      | `tests/test_collection_sheet_report_data.py > test_unsaved_sheet_refused` + `tests/test_collection_sheet_xlsx.py > test_unsaved_xlsx_refused` | ✅ COMPLIANT |
| Read-only MCP tool get_collection_sheet_pdf | Open sheet returns base64 PDF              | `tests/test_collection_mcp_sheet_pdf.py > test_open_sheet_returns_base64_pdf_envelope`                                                        | ✅ COMPLIANT |
| Read-only MCP tool get_collection_sheet_pdf | No open sheet returns null                 | `tests/test_collection_mcp_sheet_pdf.py > test_no_sheet_at_all_returns_null` + proposal/closed/cancelled/submitted nulls                      | ✅ COMPLIANT |
| Read-only MCP tool get_collection_sheet_pdf | More than one open sheet fails closed      | `tests/test_collection_mcp_sheet_pdf.py > test_multiple_open_sheets_raise_user_error`                                                         | ✅ COMPLIANT |
| Read-only MCP tool get_collection_sheet_pdf | Caller authorization                       | `tests/test_collection_mcp_sheet_pdf.py > test_portal_and_public_callers_denied_access_error` + `test_invalid_seller_id_fails_closed`         | ✅ COMPLIANT |
| Read-only MCP tool get_collection_sheet_pdf | Company scoping                            | `tests/test_collection_mcp_sheet_pdf.py > test_other_company_open_sheet_is_not_leaked`                                                        | ✅ COMPLIANT |

#### collection-vouchers

| Requirement                      | Scenario                                          | Test                                                                                                                                                                   | Result       |
| -------------------------------- | ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| Create auto-assign to open sheet | UI or ORM create with seller assigns              | `tests/test_collection_sheet.py > test_create_with_seller_assigns_unique_open_sheet`                                                                                   | ✅ COMPLIANT |
| Create auto-assign to open sheet | Create without seller stays unassigned            | `tests/test_collection_sheet.py > test_create_without_seller_stays_unassigned`                                                                                         | ✅ COMPLIANT |
| Create auto-assign to open sheet | Explicit sheet_id honored when open               | `tests/test_collection_sheet.py > test_create_honors_explicit_open_sheet_id`                                                                                           | ✅ COMPLIANT |
| Create auto-assign to open sheet | Explicit sheet_id honored when submitted          | `tests/test_collection_sheet.py > test_create_honors_explicit_submitted_sheet_id`                                                                                      | ✅ COMPLIANT |
| Create auto-assign to open sheet | Assign to closed sheet fails                      | `tests/test_collection_sheet.py > test_create_with_closed_sheet_id_fails`                                                                                              | ✅ COMPLIANT |
| Create auto-assign to open sheet | Later seller write does not auto-assign           | `tests/test_collection_sheet.py > test_later_seller_write_does_not_auto_assign`                                                                                        | ✅ COMPLIANT |
| Create auto-assign to open sheet | No open sheet creates then assigns                | `tests/test_collection_sheet.py > test_create_with_seller_creates_open_sheet_when_none`                                                                                | ✅ COMPLIANT |
| Create auto-assign to open sheet | More than one open rejects create                 | `tests/test_collection_sheet.py > test_create_with_seller_rejected_when_multiple_opens`                                                                                | ✅ COMPLIANT |
| Create auto-assign to open sheet | Auto-create off skips create and assign           | `tests/test_collection_sheet.py > test_auto_create_off_skips_create_and_assign`                                                                                        | ✅ COMPLIANT |
| Sheet-state voucher field guards | Open membership and business fields writable      | `tests/test_collection_voucher.py > test_open_membership_and_business_fields_writable`                                                                                 | ✅ COMPLIANT |
| Sheet-state voucher field guards | Submitted membership and business fields writable | `tests/test_collection_sheet.py > test_submitted_membership_add_and_remove` + `test_submitted_partner_reassign_persists` (no amount/`from_account` write on submitted) | ⚠️ PARTIAL   |
| Sheet-state voucher field guards | Proposal closed cancelled membership refused      | `tests/test_collection_voucher.py > test_proposal_membership_sheet_id_refused` + cancelled + freeze tests                                                              | ✅ COMPLIANT |
| Sheet-state voucher field guards | Proposal closed cancelled business fields refused | `tests/test_collection_voucher.py > test_proposal_business_fields_refused` + cancelled/closed business tests                                                           | ✅ COMPLIANT |
| Sheet-state voucher field guards | Chatter remains writable when frozen              | `tests/test_collection_voucher.py > test_chatter_remains_writable_when_sheet_frozen`                                                                                   | ✅ COMPLIANT |

#### document-review

| Requirement                                    | Scenario                                           | Test                                                                                               | Result       |
| ---------------------------------------------- | -------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ------------ |
| Sheet identifier required on review operations | Required sheet context                             | `tests/test_collection_document_review.py > test_review_queue_refuses_missing_or_invalid_sheet_id` | ✅ COMPLIANT |
| Sheet identifier required on review operations | Stale membership                                   | `tests/test_collection_document_review.py > test_stale_sheet_membership_mutations_are_refused`     | ✅ COMPLIANT |
| Sheet identifier required on review operations | OWL and RPC arguments include the sheet identifier | `tests/test_collection_document_review.py > test_owl_review_rpcs_pass_sheet_id_from_action_params` | ✅ COMPLIANT |
| Sheet identifier required on review operations | Open sheet identifier still works                  | `tests/test_collection_document_review.py > test_review_rpcs_still_succeed_on_open_sheet`          | ✅ COMPLIANT |
| Sheet identifier required on review operations | Submitted sheet identifier works                   | `tests/test_collection_document_review.py > test_review_rpcs_succeed_on_submitted_sheet`           | ✅ COMPLIANT |
| Sheet identifier required on review operations | Non-reviewable sheet identifier refused            | `tests/test_collection_document_review.py > test_review_rpcs_refuse_non_open_sheet`                | ✅ COMPLIANT |

#### collection-allocations

| Requirement                                  | Scenario                               | Test                                                                                                                              | Result       |
| -------------------------------------------- | -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| Draft default and confirm-on-close invariant | Create defaults to draft               | `tests/test_collection_allocation.py > test_create_defaults_to_draft`                                                             | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Draft legal on submitted               | `tests/test_collection_allocation.py > test_iff_draft_on_submitted_passes` + `test_create_draft_allocation_on_submitted`          | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Close confirms then closes             | `tests/test_collection_allocation.py > test_close_from_proposal_confirms_then_closes`                                             | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Cancel drafts allocations              | `tests/test_collection_allocation.py > test_cancel_from_proposal_drafts_allocations` + closed/submitted cancel tests              | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Reinstate from cancelled leaves draft  | `tests/test_collection_allocation.py > test_open_from_cancelled_leaves_draft`                                                     | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Confirm does not confirm allocations   | `tests/test_collection_allocation.py > test_confirm_does_not_confirm_allocations`                                                 | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Invariant-breaking state write refused | `tests/test_collection_allocation.py > test_freeze_rejects_writes_when_confirmed` + iff tests                                     | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Draft-state error names submitted      | `tests/test_collection_allocation.py > test_draft_state_error_names_submitted`                                                    | ✅ COMPLIANT |
| Cancelled and Closed allocation write guards | Cancelled draft line write refused     | `tests/test_collection_allocation.py > test_cancelled_draft_line_write_refused`                                                   | ✅ COMPLIANT |
| Cancelled and Closed allocation write guards | Closed allocation writes refused       | `tests/test_collection_allocation.py > test_closed_allocation_writes_refused`                                                     | ✅ COMPLIANT |
| Cancelled and Closed allocation write guards | Proposal draft remains writable        | `tests/test_collection_allocation.py > test_proposal_draft_line_and_voucher_writes_persist`                                       | ✅ COMPLIANT |
| Cancelled and Closed allocation write guards | Submitted draft remains writable       | `tests/test_collection_allocation.py > test_submitted_draft_line_and_voucher_writes_persist`                                      | ✅ COMPLIANT |
| Cancelled and Closed allocation write guards | Cancelled line unlink refused          | `tests/test_collection_allocation.py > test_cancelled_line_unlink_refused`                                                        | ✅ COMPLIANT |
| MCP open sheet is state open only            | Proposal does not occupy MCP open      | `tests/test_collection_mcp_allocation_lookup.py > test_proposal_sheet_does_not_occupy_mcp_open`                                   | ✅ COMPLIANT |
| MCP open sheet is state open only            | Submitted does not occupy MCP open     | `tests/test_collection_mcp_allocation_lookup.py > test_submitted_sheet_does_not_occupy_mcp_open`                                  | ✅ COMPLIANT |
| MCP open sheet is state open only            | New open while submitted exists        | `tests/test_collection_mcp_allocation.py > test_create_new_open_while_submitted_exists`                                           | ✅ COMPLIANT |
| MCP open sheet is state open only            | New open while proposal exists         | `tests/test_collection_mcp_allocation.py > test_create_new_open_while_proposal_exists`                                            | ✅ COMPLIANT |
| MCP open sheet is state open only            | Closed or cancelled not used as open   | `tests/test_collection_mcp_allocation_lookup.py > test_closed_sheet_only_returns_null` + `test_cancelled_sheet_only_returns_null` | ✅ COMPLIANT |

**Compliance summary**: 118/124 scenarios compliant (6 PARTIAL, 0 UNTESTED, 0 FAILING)

### Correctness (Static Evidence)

| Requirement                      | Status         | Notes                                                                                                                                  |
| -------------------------------- | -------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Seller Close from open           | ✅ Implemented | `action_seller_close` locks, `invalidate_recordset(["state","voucher_ids"])`, draft-offender helper, audited decls+state write         |
| MCP write close_collection_sheet | ✅ Implemented | `tools/collection_sheet_close.py` `@mcp_tool` write/mcp; `seller_id` + amounts; 0-open UserError; `check_access("write")`; no `sudo()` |
| Named sets                       | ✅ Implemented | `SELLER_SHEET_STATES={"open"}`; `ADMIN_EDITABLE_SHEET_STATES={"open","submitted"}`; `DRAFT_SHEET_STATES` includes submitted            |
| Dispatcher                       | ✅ Implemented | `_STATE_WRITE_ACTIONS["submitted"]=_dispatch_submitted_state_write`; no `"open"` key; cancelled→`action_reinstate`                     |
| Confirm submitted-only           | ✅ Implemented | `action_confirm` requires `state == "submitted"`                                                                                       |
| Reinstate                        | ✅ Implemented | `action_reinstate` cancelled→submitted; no one-open lock; `action_open` gone                                                           |
| No migrate folder                | ✅ Implemented | No `migrations/19.0.1.42.0/`; leftover pin present                                                                                     |
| Manifest                         | ✅ Implemented | `19.0.1.42.0`                                                                                                                          |

Source inspection agrees with design for named sets, dispatcher, lock+invalidate, MCP
seller_id-only, no sudo, no migrate folder. The five previously UNTESTED scenarios now
have passing covering tests. Remaining gaps are PARTIAL (chatter amounts, MCP next-write
via ORM, disabled-seller Confirm path, voucher amount write on submitted).

### Coherence (Design)

| Decision                                                                  | Followed?                  | Notes                                                                              |
| ------------------------------------------------------------------------- | -------------------------- | ---------------------------------------------------------------------------------- |
| Fifth key `submitted` vs flag                                             | ✅ Yes                     | Selection + Rendida + five-state statusbar                                         |
| Editable-iff named sets                                                   | ✅ Yes                     | `collection_common.py`                                                             |
| Private dispatcher; drop `"open"`                                         | ✅ Yes                     | `_dispatch_submitted_state_write`                                                  |
| Combined decls+state inside lock                                          | ✅ Yes                     | audited write; unaudited combined write refused                                    |
| `action_reinstate`; drop one-open on that path                            | ✅ Yes                     |                                                                                    |
| MCP `seller_id` only; 0 open → UserError                                  | ✅ Yes                     | not `{sheet: null}`                                                                |
| No `sudo()`; `check_access("write")`                                      | ✅ Yes                     | inspect test + source                                                              |
| No `migrations/19.0.1.42.0/`                                              | ✅ Yes                     |                                                                                    |
| Confirm header still names open+submitted                                 | ✅ Yes (Phase 5 deviation) | ORM refuses Confirm from open; UI still shows Confirm on open per spec header text |
| Leftover AGENTS pin `Confirm/Close/Cancel/Open`                           | ✅ Yes (intentional)       | pin kept; runtime actions are Seller Close/Confirm/Close/Cancel/Reinstate          |
| `_closed_membership_user_error` / `_OUTSTANDING_INVOICE_STATES` untouched | ✅ Yes                     | freeze error text unchanged                                                        |

### TDD Compliance

| Check                         | Result | Details                                                                                            |
| ----------------------------- | ------ | -------------------------------------------------------------------------------------------------- |
| TDD Evidence reported         | ✅     | Found in apply-progress TDD Cycle Evidence (17 task rows)                                          |
| All tasks have tests          | ✅     | 17/17 tasks name test files; 6.3 created `tests/test_collection_mcp_sheet_close.py`                |
| RED confirmed (tests exist)   | ✅     | Named test files exist on disk                                                                     |
| GREEN confirmed (tests pass)  | ✅     | This run: 0 failed, 0 error(s) of 846 collection tests                                             |
| Triangulation adequate        | ⚠️     | Most behaviors multi-case; six remaining PARTIAL scenarios still lack a full Then-clause assertion |
| Safety Net for modified files | ✅     | Apply-progress records class nets before RED; 6.3 correctly `N/A (new)`                            |

**TDD Compliance**: 5/6 checks passed (triangulation warning because six PARTIAL
scenarios remain)

### Test Layer Distribution

| Layer       | Tests                                                                                 | Files                                                                        | Tools                                     |
| ----------- | ------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | ----------------------------------------- |
| Unit        | source-scan / inspect (named-set leftover scan, no-sudo source, leftover migrate pin) | `test_collection_company_migration.py`, `test_collection_mcp_sheet_close.py` | Odoo TransactionCase file reads           |
| Integration | 846 module tests (Odoo runner count)                                                  | `tests/test_collection_*.py`                                                 | Odoo TransactionCase in Docker/PostgreSQL |
| E2E         | 0                                                                                     | 0                                                                            | not installed                             |
| **Total**   | **846** (collection `--mode=update`)                                                  | **collection test package**                                                  |                                           |

### Changed File Coverage

Coverage analysis skipped — no coverage tool detected.

### Assertion Quality

| File | Line | Assertion | Issue                                                                                                                                                                      | Severity |
| ---- | ---- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| —    | —    | —         | No tautologies, ghost loops, or production-free asserts found in change tests. Source-scan no-sudo tests read production files and assert absence of `sudo(` / `{"error"`. | —        |

**Assertion quality**: ✅ All assertions verify real behavior

### Quality Metrics

**Linter**: ⚠️ 0 errors / 1 optional warning (C8101 manifest author, pre-existing) /
scoped pre-commit Passed **Type Checker**: ➖ Not available

### Issues Found

**CRITICAL**: None

**WARNING**:

1. PARTIAL — Next write uses a new open sheet: ORM `_create_sheet()` after MCP close,
   not `create_collection_allocation`.
2. PARTIAL — Submitted membership add/remove does not assert chatter.
3. PARTIAL — Cancel chatter is proposal→cancelled only.
4. PARTIAL — Seller Close chatter asserts Open→Submitted by Seller, not declared
   `cash_on_hand`/`commission_withheld`.
5. PARTIAL — Disabled-seller confirmable uses `confirm_sheet` from open after disable,
   not Confirm from a submitted sheet after disable.
6. PARTIAL — Submitted voucher business-field writes (amount/`from_account`) are not
   asserted; membership/partner only.
7. Sibling `collection_receipt_proposal` `TestReceiptProposalOrder`: Phase 5 recorded 2
   failed + 1 error of 134; not re-run; not the collection gate.
8. Phase 6 stacked slice exceeded the 400-line review budget (apply-progress: MCP close
   tests plus ORM triangulation). Delivery strategy was auto-chain/stacked-to-main.
9. AGENTS leftover pin still contains `Confirm/Close/Cancel/Open` by design; runtime
   header is Seller Close/Confirm/Close/Cancel/Reinstate.

**SUGGESTION**:

1. Confirm remains visible on open (`invisible` `not in ('open','submitted')`) while ORM
   refuses Confirm-from-open. Spec header text allows Confirm on open; consider aligning
   the button `invisible` with submitted-only Confirm to avoid a dead control.

### Verdict

PASS WITH WARNINGS Collection tests (846) and img-build passed, all 17 tasks are
checked, the five previously UNTESTED scenarios now have passing covering tests, and
remaining gaps are PARTIAL warnings (chatter, MCP next-write via ORM, disabled-seller
Confirm path, voucher amount write).
