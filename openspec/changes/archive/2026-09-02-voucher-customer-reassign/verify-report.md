```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:2c3bc4fc12a5b21cd28080f51d77f7176842908b82e4c1bac09e008b37087a76
verdict: pass
blockers: 0
critical_findings: 0
requirements: 7/7
scenarios: 22/22
test_command: invoke test -m collection --mode=update
test_exit_code: 0
test_output_hash: sha256:8d6988879c9b43df04c8810fb64bd1e6677b3ac9c48ac954e6344410eb305423
build_command:
  docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init
build_exit_code: 0
build_output_hash: sha256:8d2fc56274b8620c9e76cd178b3fd23005f2586d976559f53e79dec58f5b4dec
```

## Verification Report

**Change**: `voucher-customer-reassign` **Version**: collection `19.0.1.26.0` (delta
specs `collection-allocations` + `collection-vouchers` + `collection-sheets`) **Mode**:
Strict TDD

Delta spec counts (actual `### Requirement:` / `#### Scenario:` blocks):
collection-allocations 2/4 + collection-vouchers 3/10 + collection-sheets 2/8 = **7
requirements**; **22 scenarios**. Matches the authoritative totals passed to the
validator.

### Completeness

| Metric           | Value |
| ---------------- | ----- |
| Tasks total      | 15    |
| Tasks complete   | 15    |
| Tasks incomplete | 0     |

All `tasks.md` items 1.1–3.3 are `[x]`. Full spec verification proceeded.

### Build & Tests Execution

**Build**: ✅ Passed (module upgrade; `invoke img-build` skipped as not this change)

```text
docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init
exit 0
output sha256:8d2fc56274b8620c9e76cd178b3fd23005f2586d976559f53e79dec58f5b4dec
odoo: Modules loaded.
```

**Tests**: ✅ 530 passed / ❌ 0 failed / ⚠️ 0 skipped

```text
invoke test -m collection --mode=update
exit 0
output sha256:8d6988879c9b43df04c8810fb64bd1e6677b3ac9c48ac954e6344410eb305423
odoo.tests.result: 0 failed, 0 error(s) of 530 tests when loading database 'devel'
odoo.tests.stats: collection: 586 tests 25.70s 41687 queries
```

Every covering test named in the matrix logged `Starting ...` in this run and the suite
finished with zero failures/errors.

**Lint** (not envelope): scoped `pre-commit run --files` on
`models/collection_voucher.py`, `models/collection_sheet.py`,
`views/collection_views.xml`, `__manifest__.py`, `AGENTS.md`,
`tests/test_collection_voucher.py`, `tests/test_collection_sheet.py`,
`tests/test_collection_ui.py`, `tests/test_collection_allocation.py`, and
`tests/test_collection_company_migration.py` — exit 0. Optional pylint `C8101`
(`manifest-required-author`, author `Seedian` vs required `Eynes`) on `__manifest__.py`.

**Coverage**: ➖ Not available — Coverage analysis skipped — no coverage tool detected

### Spec Compliance Matrix

| Requirement                          | Scenario                                            | Test                                                                                                                                                                                                                                              | Result       |
| ------------------------------------ | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| Source detach residual refuse        | Fully applied source detach refused                 | `test_collection_allocation.py` > `test_fully_applied_source_detach_via_partner_write_refused`; `test_collection_voucher.py` > `test_partner_write_fully_applied_source_refused`                                                                  | ✅ COMPLIANT |
| Source detach residual refuse        | Negative projected residual refused                 | `test_collection_allocation.py` > `test_projected_residual_less_than_amount_detach_refused`                                                                                                                                                       | ✅ COMPLIANT |
| Partner match after voucher write    | Voucher partner write mismatch refused              | `test_collection_allocation.py` > `test_voucher_partner_write_mismatch_without_matching_allocation_refused`                                                                                                                                       | ✅ COMPLIANT |
| Partner match after voucher write    | Same-write matching partner and allocation          | `test_collection_allocation.py` > `test_same_write_matching_partner_and_allocation_holds`                                                                                                                                                         | ✅ COMPLIANT |
| Partner write follows allocation     | Same-write partner and allocation                   | `test_collection_voucher.py` > `test_partner_write_same_vals_attaches_confirmed_allocation`                                                                                                                                                       | ✅ COMPLIANT |
| Partner write follows allocation     | Fully applied source refused                        | `test_collection_voucher.py` > `test_partner_write_fully_applied_source_refused`                                                                                                                                                                  | ✅ COMPLIANT |
| Partner write follows allocation     | Target attaches when residual holds                 | `test_collection_voucher.py` > `test_partner_write_attaches_when_target_residual_holds`                                                                                                                                                           | ✅ COMPLIANT |
| Partner write follows allocation     | Target left unallocated when residual does not hold | `test_collection_voucher.py` > `test_partner_write_left_unallocated_posts_chatter`                                                                                                                                                                | ✅ COMPLIANT |
| Partner write follows allocation     | Non-confirmed source refused                        | `test_collection_voucher.py` > `test_partner_write_non_confirmed_source_refused`                                                                                                                                                                  | ✅ COMPLIANT |
| Partner write follows allocation     | Approved or rejected voucher may move               | `test_collection_voucher.py` > `test_approved_or_rejected_voucher_may_change_partner`                                                                                                                                                             | ✅ COMPLIANT |
| Voucher partner-allocation constrain | Constrain mismatch refused                          | `test_collection_voucher.py` > `test_constrain_mismatch_allocation_id_without_partner_refused`                                                                                                                                                    | ✅ COMPLIANT |
| Context-gated partner group_expand   | Identity expand without context                     | `test_collection_ui.py` > `test_partner_group_expand_identity_without_readable_sheet`                                                                                                                                                             | ✅ COMPLIANT |
| Context-gated partner group_expand   | Empty allocation columns                            | `test_collection_ui.py` > `test_partner_group_expand_empty_allocation_columns`                                                                                                                                                                    | ✅ COMPLIANT |
| Context-gated partner group_expand   | Stray extra columns                                 | `test_collection_ui.py` > `test_partner_group_expand_stray_voucher_customers`                                                                                                                                                                     | ✅ COMPLIANT |
| Reassign header action and kanban    | Open saved sheet opens customer kanban              | `test_collection_sheet.py` > `test_action_open_voucher_reassign_returns_customer_kanban`, `test_action_open_voucher_reassign_binds_each_saved_sheet`; `test_collection_ui.py` > `test_sheet_form_header_reassign_after_document_review_when_open` | ✅ COMPLIANT |
| Reassign header action and kanban    | Closed sheet refuses reassign action                | `test_collection_sheet.py` > `test_action_open_voucher_reassign_refused_when_closed`; `test_collection_ui.py` > `test_sheet_form_header_reassign_after_document_review_when_open`                                                                 | ✅ COMPLIANT |
| Reassign header action and kanban    | Unsaved sheet refuses reassign action               | `test_collection_sheet.py` > `test_action_open_voucher_reassign_refused_on_new_id`; `test_collection_ui.py` > `test_sheet_form_header_reassign_after_document_review_when_open`                                                                   | ✅ COMPLIANT |
| Reassign header action and kanban    | No Edit Delete or Add column                        | `test_collection_ui.py` > `test_reassign_kanban_groups_by_customer_and_disables_create`                                                                                                                                                           | ✅ COMPLIANT |
| Reassign header action and kanban    | partner_id not readonly on reassign kanban          | `test_collection_ui.py` > `test_reassign_kanban_groups_by_customer_and_disables_create`                                                                                                                                                           | ✅ COMPLIANT |
| Reassign header action and kanban    | Frozen state kanban unchanged                       | `test_collection_ui.py` > `test_reassign_kanban_groups_by_customer_and_disables_create`, `test_kanban_groups_by_state_and_shows_card_fields`, `test_create_and_edit_enabled_on_payment_vouchers`                                                  | ✅ COMPLIANT |
| Closed sheet membership freeze       | Freeze add, remove, and reassign                    | `test_collection_sheet.py` > `test_freeze_rejects_add_remove_and_reassign`                                                                                                                                                                        | ✅ COMPLIANT |
| Closed sheet membership freeze       | Closed partner_id reuses membership UserError       | `test_collection_sheet.py` > `test_freeze_rejects_closed_partner_id_with_membership_error`                                                                                                                                                        | ✅ COMPLIANT |

**Compliance summary**: 22/22 scenarios compliant

### Correctness (Static Evidence)

| Requirement                          | Status         | Notes                                                                                                                                                                                       |
| ------------------------------------ | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Source detach residual refuse        | ✅ Implemented | `_ensure_source_allocation_detachable` projects residual minus voucher amount via `compare_amounts`; refuse when `< 0`; no silent unallocate                                                |
| Partner match after voucher write    | ✅ Implemented | `_check_voucher_allocation_partner` `@api.constrains("partner_id", "allocation_id")`; inject `allocation_id` only when omitted so stale Q+A still mismatches                                |
| Partner write follows allocation     | ✅ Implemented | Partner branch before allocation gate; same-`super().write` `partner_id`+`allocation_id`; attach iff unique confirmed same-sheet residual holds; else `False` + `message_post`; no `sudo()` |
| Voucher partner-allocation constrain | ✅ Implemented | UserError on partner mismatch; allocation-only write refused                                                                                                                                |
| Context-gated partner group_expand   | ✅ Implemented | `group_expand="_read_group_partner_ids"` (method, not `True`); identity unless readable positive int sheet; allocation ∪ member partners, `res.partner` `_order`                            |
| Reassign header action and kanban    | ✅ Implemented | `action_open_voucher_reassign` `views` only (reassign kanban, form); header after Document Review `invisible="not id or state != 'open'"`; new XMLID; state kanban untouched                |
| Closed sheet membership freeze       | ✅ Implemented | `_ensure_partner_reassign_unlocked` raises the same membership UserError as closed `sheet_id`                                                                                               |

### Coherence (Design)

| Decision                                             | Followed? | Notes                                                                                               |
| ---------------------------------------------------- | --------- | --------------------------------------------------------------------------------------------------- |
| Method `group_expand`, not boolean `True`            | ✅ Yes    | `_read_group_partner_ids(self, groups, domain)`; `_readable_reassign_sheet` excludes bool/`"12"`/≤0 |
| Same-`super().write` partner+allocation              | ✅ Yes    | `_vals_with_partner_allocation` injects when omitted; per-record split like main attachment         |
| Source residual block via `compare_amounts`          | ✅ Yes    | Fully applied and projected `< 0` raise UserError                                                   |
| Attach iff residual holds else unallocated + chatter | ✅ Yes    | `_allocation_residual_holds`; `message_post` unallocated note                                       |
| Action `views` only; omit `view_mode`/`view_id`      | ✅ Yes    | Name **Reassign Customers**; no `path`                                                              |
| New reassign kanban XMLID; freeze state kanban       | ✅ Yes    | `view_collection_voucher_reassign_kanban`; `default_group_by="state"` unchanged                     |
| Closed freeze reuses membership UserError            | ✅ Yes    | Same string as closed `sheet_id`                                                                    |
| Partner branch before allocation_id gate             | ✅ Yes    | `_prepare_partner_reassign_write` then `_ensure_allocation_membership_writable`                     |
| Manifest `19.0.1.26.0`; no migrate folder            | ✅ Yes    | `test_manifest_version_is_1_26_0`; no `migrations/19.0.1.26.0/`                                     |
| Invert tests before XML/Python                       | ✅ Yes    | apply-progress RED then GREEN for Phases 1–3                                                        |

Apply-progress deviations (inject only when `allocation_id` omitted; C901 extract
`_prepare_partner_reassign_write` / `_intercept_state_write`) do not change spec
outcomes.

### Issues Found

**CRITICAL**: None **WARNING**: None **SUGGESTION**:

- Optional pylint `C8101` (`manifest-required-author`, author `Seedian`) on
  `__manifest__.py`; mandatory pylint hook still Passed.
- Pre-existing duplicate OCR/seller field-label warnings on `collection.voucher` during
  registry load (build and tests).
- `test_customer_field_is_partner_id_without_domain` docstring still mentions a "sheet
  member list"; counts correctly include the reassign kanban xmlid (`2`).
- Odoo stats line reports `586 tests` while `odoo.tests.result` reports `530` loaded
  tests; envelope uses the result line (same convention as archived verify).

### Verdict

PASS All 7 requirements and 22 scenarios have covering tests that started and passed in
this run; design decisions match the implementation.

### TDD Compliance

| Check                         | Result | Details                                                                                                                                                                           |
| ----------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TDD Evidence reported         | ✅     | TDD Cycle Evidence table in `apply-progress.md` for tasks 1.1–3.3                                                                                                                 |
| All tasks have tests          | ✅     | 12/12 implementation tasks (1.1–1.6, 2.1–2.4, 3.1–3.2) have test files; 1.7/2.5/3.3 quality N/A                                                                                   |
| RED confirmed (tests exist)   | ✅     | Named methods exist in `test_collection_voucher.py`, `test_collection_sheet.py`, `test_collection_allocation.py`, `test_collection_ui.py`, `test_collection_company_migration.py` |
| GREEN confirmed (tests pass)  | ✅     | This run: 0 failed, 0 error(s) of 530 tests                                                                                                                                       |
| Triangulation adequate        | ✅     | 1.1/1.3/2.1/2.2/3.1 triangulated; 1.2 constrain + 1.3 companion; 1.4/1.6 version Single                                                                                           |
| Safety Net for modified files | ✅     | 1.1–1.3/2.1–2.4/3.1 recorded existing suites; 1.4 N/A (rename); 1.6 N/A manifest bump                                                                                             |

**TDD Compliance**: 6/6 checks passed

---

### Test Layer Distribution

| Layer       | Tests  | Files | Tools                                                                                                                                                 |
| ----------- | ------ | ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Unit        | 1      | 1     | File-read `test_manifest_version_is_1_26_0`                                                                                                           |
| Integration | 21     | 4     | Odoo TransactionCase + lxml arch (`test_collection_voucher.py`, `test_collection_sheet.py`, `test_collection_allocation.py`, `test_collection_ui.py`) |
| E2E         | 0      | 0     | not installed                                                                                                                                         |
| **Total**   | **22** | **5** | focused tests created/inverted for this change                                                                                                        |

Envelope run also executed the full collection module suite (530). Closed freeze
add/remove/reassign reuses `test_freeze_rejects_add_remove_and_reassign`. State-kanban
freeze reuses `test_kanban_groups_by_state_and_shows_card_fields` and
`test_create_and_edit_enabled_on_payment_vouchers`.

---

### Changed File Coverage

Coverage analysis skipped — no coverage tool detected

---

### Assertion Quality

**Assertion quality**: ✅ All assertions verify real behavior

Scanned new/inverted methods in `tests/test_collection_voucher.py`,
`tests/test_collection_sheet.py`, `tests/test_collection_allocation.py`,
`tests/test_collection_ui.py`, and `tests/test_collection_company_migration.py`. Write
tests call `voucher.write` / allocation create and assert partner, allocation
membership, residual, UserError strings, and chatter body. Action tests assert
`views`/domain/context and closed/unsaved UserError. Arch tests assert reassign kanban
attrs, header order/`invisible`, and distinct state-kanban XMLID. Expand tests call
`formatted_read_group` with `read_group_expand=True` and assert identity vs
union/`_order`. Version test asserts manifest string and absent migrate folder. No
tautologies, ghost loops, or production-code-free assertions.

---

### Quality Metrics

**Linter**: ✅ No errors on owned files (scoped pre-commit exit 0). Optional glob
`C8101` on `__manifest__.py` is pre-existing. **Type Checker**: ➖ Not available
