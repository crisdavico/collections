```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:2024cdc48a8cf770972be29ff8ed70183a897524fac598531ae15daf736db3a7
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 17/17
scenarios: 70/70
test_command: invoke test -m collection --mode=update
test_exit_code: 0
test_output_hash: sha256:88977687f9249d0d712f8da783c1b29e02d3cdf9d4eef1182ab6ca63cc1e4fbe
build_command: docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --workers=0 --http-port=18069 --gevent-port=18072
build_exit_code: 0
build_output_hash: sha256:2aaa76bc103a84b749a74d4ed41f7df2f83ba977629159c1c84a74eebbaa4baf
```

## Verification Report

**Change**: `draft-until-close`
**Version**: collection `19.0.1.29.0` (migrate folder `19.0.1.28.0`; delta specs `collection-allocations` + `collection-vouchers` + `collection-sheets`)
**Mode**: Strict TDD

Delta spec counts (actual `### Requirement:` / `#### Scenario:` headings, including REMOVED): allocations ADDED 2/7 + MODIFIED 8/28 + REMOVED 1/0; vouchers MODIFIED 3/20; sheets MODIFIED 3/15 = **17 requirements**; **70 scenarios**. Matches the authoritative totals passed to the validator. Nebula-agent is out of this change and was not treated as a gap.

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 13 |
| Tasks complete | 13 |
| Tasks incomplete | 0 |

All `tasks.md` items 1.1–6.2 are `[x]`. Full spec verification proceeded.

### Build & Tests Execution
**Build**: ✅ Passed (module upgrade; `invoke img-build` not run per verify instructions)

```text
docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --workers=0 --http-port=18069 --gevent-port=18072
exit 0
output sha256:2aaa76bc103a84b749a74d4ed41f7df2f83ba977629159c1c84a74eebbaa4baf
Module collection loaded; views/security/data reloaded; registry shutdown clean.
```

**Tests**: ✅ 560 passed / ❌ 0 failed / ⚠️ 0 skipped

```text
invoke test -m collection --mode=update
exit 0
output sha256:88977687f9249d0d712f8da783c1b29e02d3cdf9d4eef1182ab6ca63cc1e4fbe
odoo.tests.result: 0 failed, 0 error(s) of 560 tests when loading database 'devel'
odoo.tests.stats: collection: 616 tests 28.29s 45602 queries
```

**Coverage**: ➖ Not available — Coverage analysis skipped — no coverage tool detected

### Spec Compliance Matrix
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Draft default and confirm-on-close invariant | Create defaults to draft | `test_collection_allocation.py` > `test_create_defaults_to_draft`; `test_collection_mcp_allocation.py` > `test_first_create_draft_revision_one_totals` | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Close confirms then closes | `test_collection_sheet.py` > `test_action_close_confirms_then_closes`, `test_action_close_confirms_every_allocation` | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Reopen drafts after open | `test_collection_sheet.py` > `test_action_reopen_opens_then_drafts`, `test_action_reopen_drafts_every_allocation` | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Invariant-breaking state write refused | `test_collection_allocation.py` > `test_iff_constraint_skips_under_audited_context`, `test_validate_and_reject_are_gone` | ✅ COMPLIANT |
| Draft unlink with revisions | Draft with revisions unlinks | `test_collection_allocation.py` > `test_draft_unlink_with_revisions_unassigns_vouchers`; `test_collection_allocation_acl.py` > `test_parent_unlink_deletes_revisions_on_draft` | ✅ COMPLIANT |
| Draft unlink with revisions | Confirmed unlink refused | `test_collection_allocation.py` > `test_confirmed_unlink_refused_without_revisions`, `test_confirmed_unlink_refused_with_revisions`; `test_collection_allocation_acl.py` > `test_parent_unlink_refused_when_confirmed` | ✅ COMPLIANT |
| Draft unlink with revisions | Direct revision unlink still forbidden | `test_collection_allocation.py` > `test_direct_revision_unlink_still_forbidden_on_draft`, `test_revision_immutable_and_request_id_unique` | ✅ COMPLIANT |
| MCP create_collection_allocation | First create | `test_collection_mcp_allocation.py` > `test_first_create_draft_revision_one_totals`; `test_collection_allocation.py` > `test_unique_sheet_partner_rejected` | ✅ COMPLIANT |
| MCP create_collection_allocation | Authorization denied | `test_collection_mcp_allocation.py` > `test_empty_payments_and_authorization_denied` | ✅ COMPLIANT |
| MCP create_collection_allocation | Response shape freeze | `test_collection_mcp_allocation.py` > `test_response_shape_freeze_ordered_vouchers` | ✅ COMPLIANT |
| MCP create_collection_allocation | Exact document_id reuse continues | `test_collection_mcp_allocation.py` > `test_exact_document_id_reuse_continues_to_allocation` | ✅ COMPLIANT |
| MCP create_collection_allocation | Partial overlap or other-company conflict | `test_collection_mcp_allocation.py` > `test_partial_overlap_conflict_no_writes`, `test_other_company_document_id_conflict` | ✅ COMPLIANT |
| MCP create_collection_allocation | Revalidation rolls back vouchers | `test_collection_mcp_allocation.py` > `test_revalidation_rolls_back_vouchers` | ✅ COMPLIANT |
| Idempotency and amend | Replay by request_id, content_hash, or UniqueViolation | `test_collection_mcp_allocation.py` > `test_request_id_replay_zero_writes`, `test_content_hash_replay_new_request_id_no_extra_revision`, `test_unique_violation_same_company_replays`, `test_unique_violation_hidden_other_company_generic_no_ids` | ✅ COMPLIANT |
| Idempotency and amend | Amend voucher superset or overlap | `test_collection_mcp_allocation.py` > `test_amend_superset_bumps_revision`, `test_subset_and_partial_overlap_rejected`, `test_confirmed_destination_refuses_amend` | ✅ COMPLIANT |
| Idempotency and amend | Residual reason participates in content_hash | `test_collection_mcp_allocation.py` > `test_reason_only_retry_not_noop_hash_includes_reason` | ✅ COMPLIANT |
| Input and sheet gates | Ineligible input rejected | `test_collection_mcp_allocation.py` > `test_amount_null_or_non_positive_rejected`, `test_rejected_voucher_other_company_other_sheet_mixed_rejected`, `test_unbound_reuse_and_partner_mismatch_rejected_no_create`, `test_disallowed_document_type_rejected`, `test_closed_sheet_refuses_amend` | ✅ COMPLIANT |
| Input and sheet gates | Unbound write lazy-creates partner | `test_collection_mcp_allocation.py` > `test_unbound_write_lazy_creates_partner_and_binding` | ✅ COMPLIANT |
| Input and sheet gates | auto_create_sheet off fail-closed | `test_collection_mcp_allocation.py` > `test_auto_create_sheet_off_named_error_zero_writes` | ✅ COMPLIANT |
| Revalidation and residual | Fresh debt, residual, and both-state constraint | `test_collection_mcp_allocation.py` > `test_revalidation_subtracts_other_draft_and_confirmed`, `test_residual_negative_fails`, `test_empty_invoices_on_account`, `test_ignores_caller_total_debt_stores_fresh_summary`, `test_invoice_missing_from_fresh_debt_rejected`; `test_collection_allocation.py` > `test_residual_negative_rejected_on_draft_and_confirmed` | ✅ COMPLIANT |
| Revalidation and residual | Residual holds on draft and confirmed | `test_collection_allocation.py` > `test_residual_zero_ok_on_draft_and_confirmed`, `test_residual_positive_requires_reason_on_draft_and_confirmed` | ✅ COMPLIANT |
| Freeze, revisions, ACL, back-office | Freeze when confirmed | `test_collection_allocation.py` > `test_freeze_rejects_writes_when_confirmed`, `test_delete_command_unassigns_without_destroying_voucher` | ✅ COMPLIANT |
| Freeze, revisions, ACL, back-office | Draft membership remains writable | `test_collection_allocation.py` > `test_draft_allocation_allows_membership_writes` | ✅ COMPLIANT |
| Freeze, revisions, ACL, back-office | Direct revision mutation forbidden | `test_collection_allocation.py` > `test_revision_immutable_and_request_id_unique`; `test_collection_allocation_acl.py` > `test_revision_acl_read_create_unlink_no_write` | ✅ COMPLIANT |
| Freeze, revisions, ACL, back-office | Validate and Reject gone | `test_collection_allocation.py` > `test_validate_and_reject_are_gone`; `test_collection_ui.py` > `test_collection_allocations_form_statusbar_draft_confirmed` | ✅ COMPLIANT |
| Source detach residual refuse | Fully applied source detach refused | `test_collection_allocation.py` > `test_fully_applied_source_detach_via_partner_write_refused`; `test_collection_voucher.py` > `test_partner_write_fully_applied_source_refused` | ✅ COMPLIANT |
| Source detach residual refuse | Negative projected residual refused | `test_collection_allocation.py` > `test_projected_residual_less_than_amount_detach_refused` | ✅ COMPLIANT |
| Source detach residual refuse | Draft detach when residual holds | `test_collection_allocation.py` > `test_pending_unlink_on_draft_allowed_when_residual_holds`; `test_collection_voucher.py` > `test_unlink_pending_on_draft_allowed_when_residual_holds` | ✅ COMPLIANT |
| Source detach residual refuse | Confirmed source detach refused | `test_collection_allocation.py` > `test_confirmed_source_partner_write_refused`, `test_pending_unlink_on_confirmed_refused`; `test_collection_voucher.py` > `test_partner_write_confirmed_source_refused` | ✅ COMPLIANT |
| Partner match after voucher write | Voucher partner write mismatch refused | `test_collection_allocation.py` > `test_voucher_partner_write_mismatch_without_matching_allocation_refused`; `test_collection_voucher.py` > `test_constrain_mismatch_allocation_id_without_partner_refused` | ✅ COMPLIANT |
| Partner match after voucher write | Same-write matching partner and allocation | `test_collection_allocation.py` > `test_same_write_matching_partner_and_allocation_holds`; `test_collection_voucher.py` > `test_partner_write_same_vals_attaches_draft_allocation` | ✅ COMPLIANT |
| MCP get_collection_allocation | Registered read tool | `test_collection_mcp_allocation_lookup.py` > `test_discovered_as_method_read_mcp` | ✅ COMPLIANT |
| MCP get_collection_allocation | Unbound or missing returns null | `test_collection_mcp_allocation_lookup.py` > `test_unbound_identification_returns_null_without_creating_partner`, `test_unknown_identification_returns_null_without_creating_partner`, `test_no_open_sheet_returns_null`, `test_closed_sheet_only_returns_null`, `test_open_sheet_without_allocation_returns_null` | ✅ COMPLIANT |
| MCP get_collection_allocation | Found payload and draft state | `test_collection_mcp_allocation_lookup.py` > `test_found_payload_includes_lists_and_residual_reason`, `test_on_account_empty_invoices_still_present_as_list`, `test_found_open_sheet_state_is_draft`, `test_found_payload_omits_attachments_and_base64` | ✅ COMPLIANT |
| MCP get_collection_allocation | Multi-open sheet and auth fail closed | `test_collection_mcp_allocation_lookup.py` > `test_multi_open_raises_existing_user_error`, `test_portal_and_public_callers_denied_access_error`, `test_non_enabled_seller_fails_closed`, `test_unbound_enabled_seller_fails_closed` | ✅ COMPLIANT |
| Voucher lifecycle | Approve from pending | `test_collection_voucher.py` > `test_action_approve_from_pending_records_reviewer` | ✅ COMPLIANT |
| Voucher lifecycle | Reject from pending | `test_collection_voucher.py` > `test_action_reject_from_pending_records_reviewer` | ✅ COMPLIANT |
| Voucher lifecycle | Terminal states block transitions | `test_collection_voucher.py` > `test_terminal_states_block_approve_and_reject` | ✅ COMPLIANT |
| Voucher lifecycle | Delete from pending | `test_collection_voucher.py` > `test_unlink_allowed_when_pending`; `test_collection_allocation.py` > `test_unallocated_pending_voucher_unlink_still_allowed` | ✅ COMPLIANT |
| Voucher lifecycle | Delete blocked when not pending | `test_collection_voucher.py` > `test_unlink_blocked_when_not_pending` | ✅ COMPLIANT |
| Voucher lifecycle | Delete pending on confirmed allocation refused | `test_collection_voucher.py` > `test_unlink_pending_on_confirmed_refused`; `test_collection_allocation.py` > `test_pending_unlink_on_confirmed_refused` | ✅ COMPLIANT |
| Voucher lifecycle | Delete pending on draft with negative residual refused | `test_collection_voucher.py` > `test_unlink_pending_on_draft_negative_residual_refused`; `test_collection_allocation.py` > `test_pending_unlink_on_draft_negative_residual_refused` | ✅ COMPLIANT |
| Voucher lifecycle | Kanban drag is audited | `test_collection_voucher.py` > `test_kanban_drag_writes_state` | ✅ COMPLIANT |
| Voucher lifecycle | Approve and Reject remain when review is off | `test_collection_ui.py` > `test_form_statusbar_approve_reject_when_pending`; `test_collection_voucher.py` > `test_action_approve_from_pending_records_reviewer`, `test_action_reject_from_pending_records_reviewer` | ✅ COMPLIANT |
| Voucher lifecycle | Default pending | `test_collection_voucher.py` > `test_defaults_on_create` | ✅ COMPLIANT |
| Voucher allocation membership | allocation_id write on draft or unset | `test_collection_voucher.py` > `test_allocation_id_write_on_draft_or_unset`; `test_collection_allocation.py` > `test_allocation_id_write_on_draft_or_unset` | ✅ COMPLIANT |
| Voucher allocation membership | Confirmed membership write refused | `test_collection_voucher.py` > `test_confirmed_membership_write_refused`; `test_collection_allocation.py` > `test_confirmed_membership_write_refused` | ✅ COMPLIANT |
| Voucher allocation membership | Pending unlink on draft or unset | `test_collection_voucher.py` > `test_unlink_pending_on_draft_allowed_when_residual_holds`, `test_unlink_allowed_when_pending` | ✅ COMPLIANT |
| Voucher allocation membership | Draft residual underflow refuses unlink | `test_collection_voucher.py` > `test_unlink_pending_on_draft_negative_residual_refused` | ✅ COMPLIANT |
| Partner write follows allocation | Same-write partner and allocation | `test_collection_voucher.py` > `test_partner_write_same_vals_attaches_draft_allocation` | ✅ COMPLIANT |
| Partner write follows allocation | Fully applied source refused | `test_collection_voucher.py` > `test_partner_write_fully_applied_source_refused` | ✅ COMPLIANT |
| Partner write follows allocation | Target attaches when residual holds | `test_collection_voucher.py` > `test_partner_write_attaches_when_target_residual_holds` | ✅ COMPLIANT |
| Partner write follows allocation | Target left unallocated when residual does not hold | `test_collection_voucher.py` > `test_partner_write_left_unallocated_posts_chatter` | ✅ COMPLIANT |
| Partner write follows allocation | Confirmed source refused | `test_collection_voucher.py` > `test_partner_write_confirmed_source_refused` | ✅ COMPLIANT |
| Partner write follows allocation | Approved or rejected voucher may move | `test_collection_voucher.py` > `test_approved_or_rejected_voucher_may_change_partner` | ✅ COMPLIANT |
| Membership, dates, and deletion | Assign and reassign | `test_collection_sheet.py` > `test_reassign_moves_voucher_to_sheet_b_only` | ✅ COMPLIANT |
| Membership, dates, and deletion | Empty sheet | `test_collection_sheet.py` > `test_empty_sheet_dates_false_and_no_received_date` | ✅ COMPLIANT |
| Membership, dates, and deletion | Dates from member create_date | `test_collection_sheet.py` > `test_dates_from_utc_member_create_date` | ✅ COMPLIANT |
| Membership, dates, and deletion | Unlink open unassigns when no allocations | `test_collection_sheet.py` > `test_unlink_sheet_unassigns_vouchers` | ✅ COMPLIANT |
| Membership, dates, and deletion | Unlink open cascades draft allocations | `test_collection_sheet.py` > `test_unlink_open_cascades_draft_allocations`, `test_unlink_open_cascades_every_draft_allocation` | ✅ COMPLIANT |
| Membership, dates, and deletion | Unlink closed refused even when empty | `test_collection_sheet.py` > `test_unlink_closed_empty_refused` | ✅ COMPLIANT |
| Membership, dates, and deletion | Unlink closed with allocations refused | `test_collection_sheet.py` > `test_unlink_closed_with_allocations_refused` | ✅ COMPLIANT |
| Open/closed lifecycle | Default open on create | `test_collection_sheet.py` > `test_sequence_assigned_on_create` | ✅ COMPLIANT |
| Open/closed lifecycle | Close when open | `test_collection_sheet.py` > `test_action_close_from_open`, `test_action_close_confirms_then_closes` | ✅ COMPLIANT |
| Open/closed lifecycle | Reopen when no other open | `test_collection_sheet.py` > `test_action_reopen_from_closed`, `test_action_reopen_opens_then_drafts` | ✅ COMPLIANT |
| Open/closed lifecycle | Raw state write rejected | `test_collection_sheet.py` > `test_raw_state_write_invalid_transition_rejected`, `test_raw_state_write_routes_to_close_and_reopen` | ✅ COMPLIANT |
| Open/closed lifecycle | Reopen rejected if another open exists | `test_collection_sheet.py` > `test_reopen_rejected_if_another_open_exists`, `test_blocked_reopen_keeps_allocations_confirmed` | ✅ COMPLIANT |
| Closed sheet membership freeze | Freeze add, remove, and reassign | `test_collection_sheet.py` > `test_freeze_rejects_add_remove_and_reassign` | ✅ COMPLIANT |
| Closed sheet membership freeze | Closed partner_id reuses membership UserError | `test_collection_sheet.py` > `test_freeze_rejects_closed_partner_id_with_membership_error` | ✅ COMPLIANT |
| Closed sheet membership freeze | Closed empty unlink refused | `test_collection_sheet.py` > `test_unlink_closed_empty_refused` | ✅ COMPLIANT |

**Compliance summary**: 70/70 scenarios compliant (REMOVED requirement `Back-office Validate and Reject` has zero scenarios; removal covered by Freeze `Validate and Reject gone`)

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| Draft default and confirm-on-close invariant | ✅ Implemented | Selection `draft`/`confirmed`, default `draft`; Close confirms then closes; Reopen opens then drafts; raw state write needs `collection_allocation_audited_state` |
| Draft unlink with revisions | ✅ Implemented | Parent-unlink wrapper + revision ondelete gate; confirmed `_unlink_if_confirmed` |
| MCP create_collection_allocation | ✅ Implemented | Persist omits `state` so default `draft`; revision 1 |
| Idempotency and amend | ✅ Implemented | Amend iff `draft`; `Only draft allocations can be amended.` |
| Input and sheet gates | ✅ Implemented | Open-sheet persist stays `draft` |
| Revalidation and residual | ✅ Implemented | Domain `("draft", "confirmed")`; residual both states |
| Freeze, revisions, ACL, back-office | ✅ Implemented | Freeze iff confirmed; ACL `1,0,1,1`; no `action_validate`/`action_reject` |
| Source detach residual refuse | ✅ Implemented | Inverted detachable helper; confirmed refuse |
| Partner match after voucher write | ✅ Implemented | Same-write attach searches `state="draft"` |
| MCP get_collection_allocation | ✅ Implemented | Lookup returns stored `allocation.state` (`draft` on open sheet) |
| Back-office Validate and Reject | ✅ Removed | Methods gone; Selection keys gone; SQL collapse in `19.0.1.28.0` |
| Voucher lifecycle | ✅ Implemented | Pending unlink unset/draft with residual guard; confirmed refuse |
| Voucher allocation membership | ✅ Implemented | `_allocation_is_draft_or_unset` |
| Partner write follows allocation | ✅ Implemented | Draft attach/detach; confirmed source refuse |
| Membership, dates, and deletion | ✅ Implemented | Open cascade drafts; closed unlink refused even empty |
| Open/closed lifecycle | ✅ Implemented | Confirm-then-close / open-then-draft + iff recheck |
| Closed sheet membership freeze | ✅ Implemented | Closed empty unlink refused |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| Invert-in-place | ✅ Yes | Same UNIQUE, revisions, MCP keys |
| Reuse `collection_allocation_audited_state` | ✅ Yes | Close/Reopen only; Validate/Reject intercept dropped |
| Confirm then close; reopen then draft | ✅ Yes | Skip iff mid-flight; recheck after both writes |
| Gated revision unlink | ✅ Yes | `collection_allocation_parent_unlink` |
| SQL first in `post-migrate.py` | ✅ Yes | Sheet CASE then leftover `validated`/`rejected` collapse; no `CA/` |
| Manifest bump `19.0.1.28.0` | ⚠️ Partial | Design named `19.0.1.28.0`. Code is `19.0.1.29.0` with migrate folder `19.0.1.28.0` (tested). Spec remap behavior holds. |
| No sudo / Nebula out of scope | ✅ Yes | |

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | Found in apply-progress TDD Cycle Evidence table (tasks 1.1–6.2) |
| All tasks have tests | ✅ | 13/13 tasks have test files or suite/lint gates |
| RED confirmed (tests exist) | ✅ | 11/13 feature tasks: listed test files exist. 6.1 suite gate; 6.2 lint RED |
| GREEN confirmed (tests pass) | ✅ | 13/13 — full suite 0 failed, 0 error(s) of 560 tests |
| Triangulation adequate | ✅ | Happy+edge on lifecycle, unlink, MCP amend/revalidation, migrate open vs closed. 6.2 single lint gate |
| Safety Net for modified files | ✅ | 13/13 rows document pre-edit safety net or N/A (new migrate file / verify-only) |

**TDD Compliance**: 6/6 checks passed

---

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 290 | 8 | Odoo TransactionCase |
| Integration | 560 | module suite | Containerized Odoo `--mode=update` |
| E2E | 0 | 0 | not installed |
| **Total** | **560 suite** | **8 changed test files** | |

Changed test files: `test_collection_allocation.py` (31), `test_collection_allocation_acl.py` (8), `test_collection_sheet.py` (74), `test_collection_voucher.py` (57), `test_collection_mcp_allocation.py` (33), `test_collection_mcp_allocation_lookup.py` (16), `test_collection_company_migration.py` (14), `test_collection_ui.py` (57).

---

### Changed File Coverage
Coverage analysis skipped — no coverage tool detected

---

### Assertion Quality
**Assertion quality**: ✅ All assertions verify real behavior

Scanned the eight changed test files for tautologies, orphan empty checks, type-only-only asserts, ghost loops, and smoke-only UI. Invert tests assert state values, UserError, residual, revision counts, payload keys, and unlink persistence. `hasattr(action_validate)` is paired with Selection keys and refused state writes.

---

### Quality Metrics
**Linter**: ⚠️ Optional pylint `C8101` (`manifest-required-author`) on `__manifest__.py` — hook Passed in apply Phase 6; pre-existing; not re-run in this verify (user-specified commands were test + module upgrade)
**Type Checker**: ➖ Not available

### Issues Found
**CRITICAL**: None
**WARNING**: Design specified module version `19.0.1.28.0`; current `__manifest__.py` is `19.0.1.29.0` while `migrations/19.0.1.28.0/post-migrate.py` exists and tests assert that split. Spec SQL remap is implemented. Not a scenario failure.
**SUGGESTION**: Optional pylint `C8101` author warning on `__manifest__.py` (pre-existing; hook Passed). MCP UniqueViolation `ERROR` log lines on other-company `document_id` tests remain expected (caught).

### Verdict
PASS WITH WARNINGS
All 70 scenarios have passing covering tests; 13/13 tasks complete; suite 0 failed of 560. Manifest is `19.0.1.29.0` instead of design `19.0.1.28.0`.
