```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:2d567b8e9806a908880ffe5a9755e32f92fa6da66c5f552fa216193b85e44f0b
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 27/27
scenarios: 98/98
test_command: invoke test -m collection --mode=update
test_exit_code: 0
test_output_hash: sha256:f53c94a632527e062e0058f37ae976c18cfe71528a4366864b0b8323ef61f652
build_command:
  "pre-commit run --files odoo/custom/src/private/collection/__manifest__.py
  odoo/custom/src/private/collection/AGENTS.md
  odoo/custom/src/private/collection/README.rst
  odoo/custom/src/private/collection/models/__init__.py
  odoo/custom/src/private/collection/models/collection_document_type.py
  odoo/custom/src/private/collection/models/collection_voucher.py
  odoo/custom/src/private/collection/models/collection_sheet.py
  odoo/custom/src/private/collection/models/collection_voucher_review_snapshot.py
  odoo/custom/src/private/collection/models/res_company.py
  odoo/custom/src/private/collection/models/res_config_settings.py
  odoo/custom/src/private/collection/tools/collection_voucher.py
  odoo/custom/src/private/collection/data/collection_document_type_data.xml
  odoo/custom/src/private/collection/data/ir_sequence_data.xml
  odoo/custom/src/private/collection/security/collection_security.xml
  odoo/custom/src/private/collection/security/ir.model.access.csv
  odoo/custom/src/private/collection/views/collection_views.xml
  odoo/custom/src/private/collection/views/res_config_settings_views.xml
  odoo/custom/src/private/collection/migrations/19.0.1.17.0/post-migrate.py
  odoo/custom/src/private/collection/readme/DESCRIPTION.md
  odoo/custom/src/private/collection/static/description/index.html
  odoo/custom/src/private/collection/tests/__init__.py
  odoo/custom/src/private/collection/tests/test_collection_ui.py
  odoo/custom/src/private/collection/tests/test_collection_document_review_flag.py
  odoo/custom/src/private/collection/tests/test_collection_company_settings.py
  odoo/custom/src/private/collection/tests/test_collection_acl.py
  odoo/custom/src/private/collection/tests/test_collection_company_migration.py
  odoo/custom/src/private/collection/tests/test_collection_voucher.py
  odoo/custom/src/private/collection/tests/test_collection_sheet.py
  odoo/custom/src/private/collection/tests/test_collection_payment.py
  odoo/custom/src/private/collection/tests/test_collection_mail.py
  odoo/custom/src/private/collection/tests/test_collection_document_review.py
  odoo/custom/src/private/collection/tests/test_collection_mcp_tool.py
  odoo/custom/src/private/collection/tests/test_collection_mcp_seller_lookup.py"
build_exit_code: 0
build_output_hash: sha256:c79ce1002758912d022a814cda4bf0c879807cd1d8da41e012f1c4fa59268eaa
```

## Verification Report

**Change**: collection-company-configuration **Version**: 19.0.1.17.0 **Mode**: Strict
TDD

Re-verify after Phase 8 covering tests (no production change). Engram was unavailable
(orchestrator). CodeGraph MCP server `user-codegraph` was not listed; verification used
filesystem inspection of `odoo/custom/src/private/collection` plus this session's
runtime suite. `invoke img-build` was skipped (Python/XML change; image rebuild not
required). Quality/build evidence is scoped pre-commit. Spec totals counted from
`### Requirement:` / `#### Scenario:` headings in the four delta specs:
collection-vouchers 15/60, collection-sheets 9/27, document-review 2/8, seller-lookup
1/3.

### Completeness

| Metric           | Value |
| ---------------- | ----- |
| Tasks total      | 15    |
| Tasks complete   | 15    |
| Tasks incomplete | 0     |

### Build & Tests Execution

**Build**: ✅ Passed (scoped pre-commit; `invoke img-build` N/A)

```text
pre-commit run --files <33 collection paths from apply-progress>
forbidden files...Skipped
ruff / ruff format / prettier / pylint_odoo / oca-checks / oca-gen-addon-readme: Passed
pylint optional C8101 manifest-required-author (Seedian vs Eynes) — hook still Passed
exit 0
```

**Tests**: ✅ 392 passed / ❌ 0 failed / ⚠️ 0 skipped

```text
invoke test -m collection --mode=update
collection: 392 tests 14.87s 23243 queries
0 failed, 0 error(s) of 356 tests when loading database 'devel'
This session started and passed:
TestCollectionMcpTool.test_all_new_empty_enabled_sellers_rejects_no_writes
TestCollectionMcpTool.test_all_new_disabled_seller_rejects_no_writes
TestCollectionMcpTool.test_all_new_disallowed_type_rejects_no_writes
TestCollectionMcpTool.test_all_new_auto_create_off_stays_unassigned
TestCollectionSheet.test_action_rejected_for_disabled_seller
exit 0
```

**Coverage**: ➖ Not available / threshold: 0% → ➖ No coverage tool detected

### Spec Compliance Matrix

| Requirement                                            | Scenario                                                    | Test                                                                                                                                                                                                                                     | Result       |
| ------------------------------------------------------ | ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| Collection Settings persistence                        | Collection Settings labels                                  | `tests/test_collection_ui.py > test_configuration_settings_menu_and_action`                                                                                                                                                              | ✅ COMPLIANT |
| Collection Settings persistence                        | Empty enabled sellers means none for new work               | `tests/test_collection_voucher.py > test_empty_enabled_sellers_rejects_voucher_create`                                                                                                                                                   | ✅ COMPLIANT |
| Collection Settings persistence                        | Defaults enable auto-create and all four types              | `tests/test_collection_company_settings.py > test_auto_create_sheet_defaults_true_on_field` / `test_env_company_allows_all_four_document_types`                                                                                          | ✅ COMPLIANT |
| Collection Settings persistence                        | Unsupported is configurable                                 | `tests/test_collection_company_settings.py > test_unsupported_can_be_disabled_independently`; `tests/test_collection_voucher.py > test_disallowed_type_rejects_voucher_create` / `test_document_type_selection_is_allowed_union_current` | ✅ COMPLIANT |
| Company ownership of vouchers                          | Company required on create                                  | `tests/test_collection_acl.py > test_voucher_company_id_required_defaults_to_env_company`                                                                                                                                                | ✅ COMPLIANT |
| Company ownership of vouchers                          | Other-company vouchers hidden                               | `tests/test_collection_acl.py > test_other_company_vouchers_hidden`                                                                                                                                                                      | ✅ COMPLIANT |
| Enabled seller and allowed type on new voucher work    | ORM and import create require an enabled seller             | `tests/test_collection_voucher.py > test_disabled_seller_rejects_voucher_create`                                                                                                                                                         | ✅ COMPLIANT |
| Enabled seller and allowed type on new voucher work    | UI create offers only enabled sellers and allowed types     | `tests/test_collection_ui.py > test_voucher_form_seller_domain_is_company_enabled_list`; `tests/test_collection_voucher.py > test_document_type_selection_is_allowed_union_current`                                                      | ✅ COMPLIANT |
| Enabled seller and allowed type on new voucher work    | Disallowed type rejected on new work                        | `tests/test_collection_voucher.py > test_disallowed_type_rejects_voucher_create` / `test_document_type_write_to_disallowed_type_rejected`                                                                                                | ✅ COMPLIANT |
| Enabled seller and allowed type on new voucher work    | Seller write to a disabled seller rejected                  | `tests/test_collection_voucher.py > test_seller_write_to_disabled_seller_rejected`                                                                                                                                                       | ✅ COMPLIANT |
| Historical vouchers remain operable                    | Disabled-seller voucher stays visible                       | `tests/test_collection_voucher.py > test_disabled_seller_voucher_stays_visible_and_approvable`                                                                                                                                           | ✅ COMPLIANT |
| Historical vouchers remain operable                    | Disabled-seller voucher remains operable                    | `tests/test_collection_voucher.py > test_disabled_seller_voucher_stays_visible_and_approvable` / `test_disabled_seller_voucher_reject_skips_helper`                                                                                      | ✅ COMPLIANT |
| Cross-company document_id reject not replay            | Global uniqueness still holds                               | `tests/test_collection_payment.py > test_duplicate_non_null_document_id_raises_integrity_error`; `tests/test_collection_mcp_tool.py > test_unique_violation_hidden_other_company_generic_error`                                          | ✅ COMPLIANT |
| Cross-company document_id reject not replay            | Other-company collision undisclosed                         | `tests/test_collection_mcp_tool.py > test_other_company_visible_hit_rejects_generic_no_ids`                                                                                                                                              | ✅ COMPLIANT |
| Cross-company document_id reject not replay            | Multi-company reader must not replay the other company      | `tests/test_collection_mcp_tool.py > test_multi_company_reader_does_not_replay_other_company`                                                                                                                                            | ✅ COMPLIANT |
| Upgrade stamps voucher company and seeds settings      | Voucher company from sheet then seller or default           | `tests/test_collection_company_migration.py > test_voucher_company_from_sheet_then_seller_or_main`                                                                                                                                       | ✅ COMPLIANT |
| Upgrade stamps voucher company and seeds settings      | Repair voucher and sheet company consistency                | `tests/test_collection_company_migration.py > test_repair_member_voucher_matches_sheet_company`                                                                                                                                          | ✅ COMPLIANT |
| Upgrade stamps voucher company and seeds settings      | Seed sellers and enable four types                          | `tests/test_collection_company_migration.py > test_seed_sellers_from_vouchers_and_sheets_keeps_disabled` / `test_migrate_enables_all_four_types_including_partial_lists`                                                                 | ✅ COMPLIANT |
| Upgrade stamps voucher company and seeds settings      | Per-company voucher sequences without a company-less thief  | `tests/test_collection_company_migration.py > test_voucher_and_sheet_numbers_isolated_per_company` / `test_leftover_false_sequence_does_not_steal_company_numbers`                                                                       | ✅ COMPLIANT |
| Voucher sequence naming                                | Sequence assigned on create                                 | `tests/test_collection_voucher.py > test_sequence_assigned_on_create`                                                                                                                                                                    | ✅ COMPLIANT |
| Voucher sequence naming                                | Numbers isolated per company                                | `tests/test_collection_company_migration.py > test_voucher_and_sheet_numbers_isolated_per_company`                                                                                                                                       | ✅ COMPLIANT |
| Authorization for internal users (vouchers)            | Internal user CRUD                                          | `tests/test_collection_acl.py > test_internal_user_voucher_crud_allowed`                                                                                                                                                                 | ✅ COMPLIANT |
| Authorization for internal users (vouchers)            | Non-internal user denied                                    | `tests/test_collection_acl.py > test_portal_user_voucher_crud_denied`                                                                                                                                                                    | ✅ COMPLIANT |
| Payment document_id uniqueness                         | Manual payment without document_id still OK                 | `tests/test_collection_payment.py > test_payment_without_document_id_ok`; `tests/test_collection_ui.py > test_ui_create_may_omit_document_id`                                                                                            | ✅ COMPLIANT |
| MCP optional payment attachment on create              | MCP create with nested attachment                           | `tests/test_collection_mcp_tool.py > test_create_with_valid_png_nest_becomes_chatter_proof`                                                                                                                                              | ✅ COMPLIANT |
| MCP optional payment attachment on create              | MCP attachment MIME mismatch rejected                       | `tests/test_collection_mcp_tool.py > test_create_mime_mismatch_rejects_no_writes`                                                                                                                                                        | ✅ COMPLIANT |
| MCP optional payment attachment on create              | Exact-retry skips attachment writes                         | `tests/test_collection_mcp_tool.py > test_exact_retry_with_nest_does_not_replace_attachment` / `test_exact_retry_with_nest_does_not_add_when_voucher_has_none`                                                                           | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                    | All-new create                                              | `tests/test_collection_mcp_tool.py > test_all_new_create_returns_vouchers_in_payment_order`                                                                                                                                              | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                    | Exact-retry returns all vouchers                            | `tests/test_collection_mcp_tool.py > test_exact_retry_returns_all_vouchers_ignores_customer` / `test_same_company_replay_skips_disabled_seller_and_disallowed_type`                                                                      | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                    | Duplicate document_id in call                               | `tests/test_collection_mcp_tool.py > test_in_call_duplicate_document_id_rejects_no_writes`                                                                                                                                               | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                    | Partial-conflict                                            | `tests/test_collection_mcp_tool.py > test_partial_conflict_rejects_no_writes`                                                                                                                                                            | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                    | Existing document_ids on different vouchers succeed         | `tests/test_collection_mcp_tool.py > test_existing_document_ids_on_different_vouchers_succeed`                                                                                                                                           | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                    | ACL denial for non-permitted user                           | `tests/test_collection_mcp_tool.py > test_portal_user_denied_no_writes`                                                                                                                                                                  | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                    | Missing or invalid seller_id rejected                       | `tests/test_collection_mcp_tool.py > test_missing_seller_id_rejects_no_writes` / `test_portal_seller_id_rejects_no_writes` / `test_unknown_seller_id_rejects_no_writes`                                                                  | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                    | All-new with unique open assigns the batch                  | `tests/test_collection_mcp_tool.py > test_all_new_unique_open_assigns_all_payments`                                                                                                                                                      | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                    | All-new with no open creates one open sheet and assigns all | `tests/test_collection_mcp_tool.py > test_all_new_no_open_creates_one_sheet_and_assigns_all`                                                                                                                                             | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                    | All-new with more than one open rejected                    | `tests/test_collection_mcp_tool.py > test_all_new_multiple_opens_rejects_no_writes`                                                                                                                                                      | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                    | Exact replay does not change sheet_id                       | `tests/test_collection_mcp_tool.py > test_exact_replay_leaves_sheet_id_and_write_date`                                                                                                                                                   | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                    | All-new empty or disabled seller rejected                   | `tests/test_collection_mcp_tool.py > test_all_new_empty_enabled_sellers_rejects_no_writes` / `test_all_new_disabled_seller_rejects_no_writes`                                                                                            | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                    | All-new disallowed type rejected                            | `tests/test_collection_mcp_tool.py > test_all_new_disallowed_type_rejects_no_writes`                                                                                                                                                     | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                    | All-new with auto_create_sheet off stays unassigned         | `tests/test_collection_mcp_tool.py > test_all_new_auto_create_off_stays_unassigned`                                                                                                                                                      | ✅ COMPLIANT |
| Voucher seller field                                   | Legacy null remains valid                                   | `tests/test_collection_voucher.py > test_orm_write_does_not_backfill_null_seller`                                                                                                                                                        | ✅ COMPLIANT |
| Voucher seller field                                   | ORM create without seller                                   | `tests/test_collection_voucher.py > test_orm_create_without_seller_is_rejected`                                                                                                                                                          | ✅ COMPLIANT |
| Voucher seller field                                   | Form create requires seller                                 | `tests/test_collection_ui.py > test_form_seller_id_is_required`                                                                                                                                                                          | ✅ COMPLIANT |
| Voucher seller field                                   | Seller visible on list form search                          | `tests/test_collection_ui.py > test_list_form_search_expose_seller_id`                                                                                                                                                                   | ✅ COMPLIANT |
| Create auto-assign to open sheet                       | UI or ORM create with seller assigns                        | `tests/test_collection_sheet.py > test_create_with_seller_assigns_unique_open_sheet`                                                                                                                                                     | ✅ COMPLIANT |
| Create auto-assign to open sheet                       | Create without seller stays unassigned                      | `tests/test_collection_sheet.py > test_create_without_seller_stays_unassigned`                                                                                                                                                           | ✅ COMPLIANT |
| Create auto-assign to open sheet                       | Explicit sheet_id honored when open                         | `tests/test_collection_sheet.py > test_create_honors_explicit_open_sheet_id`                                                                                                                                                             | ✅ COMPLIANT |
| Create auto-assign to open sheet                       | Assign to closed sheet fails                                | `tests/test_collection_sheet.py > test_create_with_closed_sheet_id_fails`                                                                                                                                                                | ✅ COMPLIANT |
| Create auto-assign to open sheet                       | Later seller write does not auto-assign                     | `tests/test_collection_sheet.py > test_later_seller_write_does_not_auto_assign`                                                                                                                                                          | ✅ COMPLIANT |
| Create auto-assign to open sheet                       | No open sheet creates then assigns                          | `tests/test_collection_sheet.py > test_create_with_seller_creates_open_sheet_when_none`                                                                                                                                                  | ✅ COMPLIANT |
| Create auto-assign to open sheet                       | More than one open rejects create                           | `tests/test_collection_sheet.py > test_create_with_seller_rejected_when_multiple_opens`                                                                                                                                                  | ✅ COMPLIANT |
| Create auto-assign to open sheet                       | Auto-create off skips create and assign                     | `tests/test_collection_sheet.py > test_auto_create_off_skips_create_and_assign`                                                                                                                                                          | ✅ COMPLIANT |
| Immutable review snapshots and ACL                     | Internal users read history without client mutation         | `tests/test_collection_acl.py > test_snapshot_acl_read_and_gated_create` / `test_snapshot_write_unlink_denied_and_portal_denied`                                                                                                         | ✅ COMPLIANT |
| Immutable review snapshots and ACL                     | Form Approve and Reject do not snapshot                     | `tests/test_collection_document_review.py > test_form_approve_and_reject_do_not_append_snapshots`                                                                                                                                        | ✅ COMPLIANT |
| MCP nested provenance on all-new create                | Unchanged seller confirmation                               | `tests/test_collection_mcp_tool.py > test_unchanged_seller_stamps_all_three_layers_equal`                                                                                                                                                | ✅ COMPLIANT |
| MCP nested provenance on all-new create                | Seller correction                                           | `tests/test_collection_mcp_tool.py > test_seller_correction_keeps_raw_and_aligns_current`                                                                                                                                                | ✅ COMPLIANT |
| MCP nested provenance on all-new create                | Both nests omitted leave empty provenance                   | `tests/test_collection_mcp_tool.py > test_omitted_nests_leave_null_provenance` / `test_orm_create_without_nests_leaves_null_provenance`                                                                                                  | ✅ COMPLIANT |
| MCP nested provenance on all-new create                | Bad provenance fails the batch                              | `tests/test_collection_mcp_tool.py > test_one_sided_nests_reject_with_no_writes` / `test_malformed_and_mismatch_nests_reject_with_no_writes`                                                                                             | ✅ COMPLIANT |
| MCP nested provenance on all-new create                | Exact replay ignores provenance nests                       | `tests/test_collection_mcp_tool.py > test_exact_replay_ignores_different_and_omitted_nests`                                                                                                                                              | ✅ COMPLIANT |
| Company ownership of sheets                            | Company required on create                                  | `tests/test_collection_acl.py > test_sheet_company_id_required_defaults_to_env_company`                                                                                                                                                  | ✅ COMPLIANT |
| Company ownership of sheets                            | Other-company sheets hidden                                 | `tests/test_collection_acl.py > test_other_company_sheets_hidden`                                                                                                                                                                        | ✅ COMPLIANT |
| Historical sheets remain operable                      | Disabled-seller sheet stays visible and closeable           | `tests/test_collection_sheet.py > test_disabled_seller_sheet_stays_visible_and_closeable`                                                                                                                                                | ✅ COMPLIANT |
| Upgrade stamps sheet company and sequences             | Sheet company from seller or default                        | `tests/test_collection_company_migration.py > test_sheet_company_stamped_from_seller_else_main`                                                                                                                                          | ✅ COMPLIANT |
| Upgrade stamps sheet company and sequences             | Per-company sheet sequences without a company-less thief    | `tests/test_collection_company_migration.py > test_voucher_and_sheet_numbers_isolated_per_company` / `test_leftover_false_sequence_does_not_steal_company_numbers`                                                                       | ✅ COMPLIANT |
| Sheet sequence identity                                | Sequence assigned on create                                 | `tests/test_collection_sheet.py > test_sequence_assigned_on_create`                                                                                                                                                                      | ✅ COMPLIANT |
| Sheet sequence identity                                | Numbers isolated per company                                | `tests/test_collection_company_migration.py > test_voucher_and_sheet_numbers_isolated_per_company`                                                                                                                                       | ✅ COMPLIANT |
| Sheet seller and same-seller invariant                 | Seller required and frozen                                  | `tests/test_collection_sheet.py > test_create_without_seller_is_rejected` / `test_post_create_seller_write_is_rejected`                                                                                                                  | ✅ COMPLIANT |
| Sheet seller and same-seller invariant                 | Mixed or null seller rejected                               | `tests/test_collection_sheet.py > test_mixed_or_null_seller_assign_rejected`                                                                                                                                                             | ✅ COMPLIANT |
| Sheet seller and same-seller invariant                 | New sheet requires an enabled seller                        | `tests/test_collection_sheet.py > test_sheet_create_empty_enabled_sellers_rejected` / `test_sheet_create_disabled_seller_rejected`                                                                                                       | ✅ COMPLIANT |
| Create sheet Action                                    | Unassigned same-seller any state                            | `tests/test_collection_sheet.py > test_action_creates_sheet_for_unassigned_same_seller_any_state`                                                                                                                                        | ✅ COMPLIANT |
| Create sheet Action                                    | Ineligible selection rejected                               | `tests/test_collection_sheet.py > test_action_rejects_ineligible_selection`                                                                                                                                                              | ✅ COMPLIANT |
| Create sheet Action                                    | Action rejected when an open sheet exists                   | `tests/test_collection_sheet.py > test_action_rejected_when_open_sheet_exists`                                                                                                                                                           | ✅ COMPLIANT |
| Create sheet Action                                    | Action remains when auto-create is off                      | `tests/test_collection_sheet.py > test_action_creates_sheet_when_auto_create_off`                                                                                                                                                        | ✅ COMPLIANT |
| Create sheet Action                                    | Action rejected for a disabled seller                       | `tests/test_collection_sheet.py > test_action_rejected_for_disabled_seller`                                                                                                                                                              | ✅ COMPLIANT |
| Authorization for internal users (sheets)              | Internal user CRUD                                          | `tests/test_collection_acl.py > test_internal_user_sheet_crud_allowed`                                                                                                                                                                   | ✅ COMPLIANT |
| Authorization for internal users (sheets)              | Non-internal user denied                                    | `tests/test_collection_acl.py > test_portal_user_sheet_crud_denied`                                                                                                                                                                      | ✅ COMPLIANT |
| Open/closed lifecycle                                  | Default open on create                                      | `tests/test_collection_sheet.py > test_sequence_assigned_on_create`                                                                                                                                                                      | ✅ COMPLIANT |
| Open/closed lifecycle                                  | Close when open                                             | `tests/test_collection_sheet.py > test_action_close_from_open`                                                                                                                                                                           | ✅ COMPLIANT |
| Open/closed lifecycle                                  | Reopen when no other open                                   | `tests/test_collection_sheet.py > test_action_reopen_from_closed`                                                                                                                                                                        | ✅ COMPLIANT |
| Open/closed lifecycle                                  | Raw state write rejected                                    | `tests/test_collection_sheet.py > test_raw_state_write_invalid_transition_rejected`                                                                                                                                                      | ✅ COMPLIANT |
| At most one open sheet per seller (new operations)     | Create second open rejected                                 | `tests/test_collection_sheet.py > test_create_second_open_rejected`                                                                                                                                                                      | ✅ COMPLIANT |
| At most one open sheet per seller (new operations)     | Reopen rejected if another open exists                      | `tests/test_collection_sheet.py > test_reopen_rejected_if_another_open_exists`                                                                                                                                                           | ✅ COMPLIANT |
| At most one open sheet per seller (new operations)     | More than one open fail-closed on new operations            | `tests/test_collection_sheet.py > test_leftover_multiple_opens_reject_new_ops`                                                                                                                                                           | ✅ COMPLIANT |
| At most one open sheet per seller (new operations)     | Closing extras still succeeds                               | `tests/test_collection_sheet.py > test_leftover_multiple_opens_still_closeable`                                                                                                                                                          | ✅ COMPLIANT |
| At most one open sheet per seller (new operations)     | Same seller may be open in two companies                    | `tests/test_collection_sheet.py > test_same_seller_may_be_open_in_two_companies`                                                                                                                                                         | ✅ COMPLIANT |
| At most one open sheet per seller (new operations)     | Explicit create remains when auto-create is off             | `tests/test_collection_company_migration.py > test_voucher_and_sheet_numbers_isolated_per_company`                                                                                                                                       | ✅ COMPLIANT |
| Lookup ignores enabled sellers and company allow-lists | Unique match not on the enabled list still returns          | `tests/test_collection_mcp_seller_lookup.py > test_unique_match_not_on_enabled_list_still_returns`                                                                                                                                       | ✅ COMPLIANT |
| Lookup ignores enabled sellers and company allow-lists | Empty enabled list does not block lookup                    | `tests/test_collection_mcp_seller_lookup.py > test_empty_enabled_list_does_not_block_lookup`                                                                                                                                             | ✅ COMPLIANT |
| Lookup ignores enabled sellers and company allow-lists | Other-company enabled lists do not filter lookup            | `tests/test_collection_mcp_seller_lookup.py > test_other_company_enabled_lists_do_not_filter_lookup`                                                                                                                                     | ✅ COMPLIANT |
| Review snapshots isolated by company                   | Snapshot follows voucher company                            | `tests/test_collection_acl.py > test_snapshot_company_id_related_stored_from_voucher`                                                                                                                                                    | ✅ COMPLIANT |
| Review snapshots isolated by company                   | Other-company snapshots hidden                              | `tests/test_collection_acl.py > test_other_company_snapshots_hidden`                                                                                                                                                                     | ✅ COMPLIANT |
| Review snapshots isolated by company                   | Allowed-company history still readable                      | `tests/test_collection_acl.py > test_allowed_company_voucher_sheet_snapshot_visible`; `tests/test_collection_ui.py > test_form_review_history_list_readonly_by_revision`                                                                 | ✅ COMPLIANT |
| Per-company Document Review flag                       | Default off                                                 | `tests/test_collection_document_review_flag.py > test_document_review_enabled_defaults_false_on_env_company`                                                                                                                             | ✅ COMPLIANT |
| Per-company Document Review flag                       | Settings admin toggle                                       | `tests/test_collection_document_review_flag.py > test_settings_toggle_persists_true_on_company` / `test_settings_toggle_persists_false_on_company`                                                                                       | ✅ COMPLIANT |
| Per-company Document Review flag                       | Voucher state and audit remain                              | `tests/test_collection_document_review_flag.py > test_payment_voucher_views_keep_state_when_review_off`                                                                                                                                  | ✅ COMPLIANT |
| Per-company Document Review flag                       | Flag preserved when Collection Settings are saved           | `tests/test_collection_document_review_flag.py > test_saving_other_collection_settings_preserves_document_review_on` / `_off`                                                                                                            | ✅ COMPLIANT |
| Per-company Document Review flag                       | Flag still gates review when ON or OFF                      | `tests/test_collection_document_review_flag.py > test_get_review_queue_raises_when_review_off`; `tests/test_collection_acl.py > test_internal_user_review_queue_and_approve_allowed`                                                     | ✅ COMPLIANT |

**Compliance summary**: 98/98 scenarios compliant

### Correctness (Static Evidence)

| Requirement                          | Status         | Notes                                                                                                              |
| ------------------------------------ | -------------- | ------------------------------------------------------------------------------------------------------------------ |
| Collection Settings persistence      | ✅ Implemented | `res.company` fields + related settings; labels Collection Settings; XMLID kept                                    |
| Company ownership of vouchers/sheets | ✅ Implemented | Required `company_id`; global `ir.rule`                                                                            |
| New-work helper                      | ✅ Implemented | `@api.private` `_assert_new_work`; voucher create/write; sheet create                                              |
| Cross-company document_id            | ✅ Implemented | Classifier + generic UniqueViolation; no `sudo()`                                                                  |
| Upgrade + sequences                  | ✅ Implemented | `migrations/19.0.1.17.0/post-migrate.py` steps 1–6; `with_company`                                                 |
| MCP all-new gates                    | ✅ Implemented | `_call` covering tests this session: empty sellers, disabled seller, disallowed type, auto OFF unassigned          |
| Create sheet Action disabled seller  | ✅ Implemented | `test_action_rejected_for_disabled_seller` calls `action_create_collection_sheet` after `Command.set` other seller |
| `get_seller_id` unfiltered           | ✅ Implemented | `tools/seller_lookup.py` unchanged; lookup tests passed                                                            |
| Catalog + snapshot isolation         | ✅ Implemented | `UNIQUE(code)`; related stored snapshot `company_id` + `ir.rule`                                                   |

### Coherence (Design)

| Decision                         | Followed?                  | Notes                                                                           |
| -------------------------------- | -------------------------- | ------------------------------------------------------------------------------- |
| Company + related settings       | ✅ Yes                     | Not POS-style config                                                            |
| Catalog M2M; voucher Selection   | ✅ Yes                     | Four XMLID rows                                                                 |
| One helper; skip by path         | ✅ Yes                     | Replay/Approve/Close/Reopen skip; seller-only write passes `document_type=None` |
| Empty enabled = none             | ✅ Yes                     |                                                                                 |
| `ir.rule` + required company     | ✅ Yes                     | No extra groups                                                                 |
| Snapshot related stored company  | ⚠️ Yes with extra          | `required=True` + `precompute=True` (needed for INSERT NOT NULL)                |
| Global UNIQUE; reject-not-replay | ✅ Yes                     | Generic message, no ids                                                         |
| Per-company sequences            | ✅ Yes                     | Convert False→main; copies `number_next=1`                                      |
| One-open `(company, seller)`     | ✅ Yes                     | Advisory lock includes company                                                  |
| auto OFF skips create and assign | ✅ Yes                     | ORM and MCP `_call` covering tests passed this session                          |
| `get_seller_id` unchanged        | ✅ Yes                     |                                                                                 |
| Labels only; keep XMLID          | ✅ Yes                     |                                                                                 |
| Migrate folder `19.0.1.16.0`     | ⚠️ Deviates                | Shipped `19.0.1.17.0` so devel already at 1.16.0 still runs it                  |
| Helper on sheet.create           | ⚠️ Extra vs file table     | Required by sheet enabled-seller tests; matches enforcement matrix              |
| Catalog ACL in WU1               | ⚠️ Earlier than design WU2 | Read-only `base.group_user`; no extra groups                                    |

### TDD Compliance

| Check                         | Result | Details                                                                                                                                      |
| ----------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| TDD Evidence reported         | ✅     | Found in apply-progress TDD Cycle Evidence table including Unit 8                                                                            |
| All tasks have tests          | ⚠️     | 14/15 tasks have test files; 7.1 is docs-only with suite safety net                                                                          |
| RED confirmed (tests exist)   | ✅     | Listed test files exist on disk, including Phase 8 MCP/Action methods                                                                        |
| GREEN confirmed (tests pass)  | ✅     | This session `392 tests` / `0 failed`                                                                                                        |
| Triangulation adequate        | ⚠️     | Phase 8 triangulates empty vs disabled seller, type, auto OFF, Action; WU6.1 and WU8.1 recorded already-green RED (helper already on create) |
| Safety Net for modified files | ✅     | RED tasks show prior suite counts; GREEN rows N/A (implements prior RED)                                                                     |

**TDD Compliance**: 4/6 checks passed (2 warnings)

---

### Test Layer Distribution

| Layer       | Tests                                                              | Files  | Tools                                                                |
| ----------- | ------------------------------------------------------------------ | ------ | -------------------------------------------------------------------- |
| Unit        | 392 (module suite; 356 methods in 12 `test_collection_*.py` files) | 12     | Odoo TransactionCase                                                 |
| Integration | 0 dedicated HttpCase/tours                                         | 0      | Containerized Odoo+Postgres available; suite remains TransactionCase |
| E2E         | 0                                                                  | 0      | not installed                                                        |
| **Total**   | **392**                                                            | **12** |                                                                      |

---

### Changed File Coverage

Coverage analysis skipped — no coverage tool detected

---

### Assertion Quality

| File                                         | Line    | Assertion                          | Issue                                                                                       | Severity |
| -------------------------------------------- | ------- | ---------------------------------- | ------------------------------------------------------------------------------------------- | -------- |
| `tests/test_collection_mcp_seller_lookup.py` | 307–320 | `self.assertNotIn("sudo()", code)` | Source-scan rather than runtime behavior (companion `_call` tests still assert live lookup) | WARNING  |
| `tests/test_collection_acl.py`               | 436–437 | `self.assertNotIn(".sudo(", code)` | Same source-scan pattern                                                                    | WARNING  |

Phase 8 covering tests call production `_call` / `action_create_collection_sheet`,
assert `UserError` text, and assert no voucher/sheet writes (or unassigned vouchers when
auto is OFF). No tautologies, ghost loops, or empty-only assertions.

**Assertion quality**: 0 CRITICAL, 2 WARNING

---

### Quality Metrics

**Linter**: ✅ No errors (scoped pre-commit Passed); optional pylint C8101 author hint
**Type Checker**: ➖ Not available

### Issues Found

**CRITICAL**: None

**WARNING**:

1. Design migrate path `migrations/19.0.1.16.0/` shipped as `migrations/19.0.1.17.0/`
   with manifest `19.0.1.17.0` (devel already at 1.16.0).
2. Snapshot `company_id` uses `required=True` and `precompute=True` beyond the design
   `currency_id` related-stored pattern.
3. `_assert_new_work` is called on `sheet.create` (seller only); design file-change
   table emphasized voucher, while the enforcement matrix includes explicit sheet
   create.
4. Catalog read ACL shipped in WU1 (design listed ACL flips with WU2). No extra groups.
5. Strict TDD: WU6.1 and WU8.1 include covering tests that already passed on first run
   (no-regression / helper already on create), not newly failing RED.
6. Optional pylint `manifest-required-author` (Seedian vs hook expected Eynes).

**SUGGESTION**:

1. Optional mixed-company list-Action test (design note; not a delta scenario).

### Verdict

PASS WITH WARNINGS All 98 delta scenarios have covering tests that passed this session
(392/0), including the four previously UNTESTED MCP/Action When-paths. Remaining
warnings are documented design/TDD deviations that do not break specs.
