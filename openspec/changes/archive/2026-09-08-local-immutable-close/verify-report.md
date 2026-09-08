```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:c488019cbdbc2830e4ca2976bfe19a17f45f6700b23199ea7667894e2e63e0a7
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 9/9
scenarios: 41/41
test_command: invoke test -m collection --mode=update
test_exit_code: 0
test_output_hash: sha256:676367ec5d01bd71348a33b43edb677dc6326eb61628625fd62ead223a7704f2
build_command: invoke test -m collection --mode=update
build_exit_code: 0
build_output_hash: sha256:676367ec5d01bd71348a33b43edb677dc6326eb61628625fd62ead223a7704f2
```

## Verification Report

**Change**: local-immutable-close
**Version**: collection 19.0.1.44.0
**Mode**: Strict TDD

Delta specs counted **9** `### Requirement:` headings (including 1 REMOVED with no scenarios) and **41** `#### Scenario:` headings across `collection-sheets` (2 req / 18 scn), `collection-receipts` (5 req / 12 scn), and `collection-allocations` (2 req / 11 scn).

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 17 |
| Tasks complete | 17 |
| Tasks incomplete | 0 |

Plus R.1 wrap-tolerant AGENTS pins (`" ".join(agents.split())` for `MUST NOT consult the connector` and `MUST NOT call create_receipt`). Apply state `all_done`.

### Build & Tests Execution
**Build**: ✅ Passed (`invoke img-build` skipped as not a meaningful/cheap gate for this addon-only change; module `-u collection` ran inside the authoritative test command)
```text
invoke test -m collection --mode=update
(from /home/crisd/projects/seedian/seedian; includes odoo -u collection --test-enable --stop-after-init --workers=0 --test-tags /collection)
exit 0; Module collection loaded in 62.42s (incl. 61.03s test); Registry loaded in 68.181s
```

**Tests**: ✅ 950 passed / ❌ 0 failed / ⚠️ 0 skipped (authoritative `collection` suite)
```text
invoke test -m collection --mode=update
0 failed, 0 error(s) of 950 tests when loading database 'devel'
Odoo collection: 1030 tests 60.91s 92472 queries
Prior FAIL pin TestCollectionCompanyMigration.test_agents_md_five_state_workflow now passes (wrap-tolerant AGENTS Close pins).
```

Sibling `invoke test -m collection_receipt_proposal --mode=update` (not the envelope test_command; recorded in apply, not re-run here): **3 failed, 1 error(s) of 140 tests**. Failures remain pre-existing board drift (`document_numbers` never on `collection.receipt`; FIFO vs `line_ids`; company-rule RPC). Independence: Close production does not call `create_receipt` (`models/collection_sheet.py` has no `create_receipt` symbol); collection suite Close tests passed. Satellite not edited.

**Coverage**: ➖ Not available — no coverage tool in `openspec/config.yaml`

**Pre-commit** (report body only): scoped `pre-commit run --files` on changed collection files — **Passed** (apply Phase 6.3 `PRECOMMIT_EXIT:0`; optional C8101 author warning on `__manifest__.py`). Not re-run this verify (no production edits this refresh).

### Spec Compliance Matrix
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Frozen associate create freeze | Frozen sheet refuses associate create | `tests/test_collection_allocation.py` > `test_frozen_sheet_refuses_allocation_create`; `tests/test_collection_receipt.py` > `test_frozen_sheet_refuses_receipt_and_value_create` | ✅ COMPLIANT |
| Frozen associate create freeze | Proposal still allows allocation create | `tests/test_collection_allocation.py` > `test_proposal_still_allows_allocation_create` | ✅ COMPLIANT |
| Open/closed lifecycle | Default open on create | `tests/test_collection_sheet.py` > `test_sequence_assigned_on_create` | ✅ COMPLIANT |
| Open/closed lifecycle | Close when proposal | `tests/test_collection_sheet.py` > `test_action_close_from_proposal_confirms_then_closes`; `tests/test_collection_receipt.py` > `test_close_issues_draft_receipts` | ✅ COMPLIANT |
| Open/closed lifecycle | Close without connector succeeds | `tests/test_collection_sheet.py` > `test_action_close_without_connector_succeeds` | ✅ COMPLIANT |
| Open/closed lifecycle | Close without receipts still closes | `tests/test_collection_sheet.py` > `test_action_close_with_zero_receipts_still_closes` | ✅ COMPLIANT |
| Open/closed lifecycle | Close keeps voucher documentary state | `tests/test_collection_sheet.py` > `test_action_close_keeps_voucher_validated_collections` | ✅ COMPLIANT |
| Open/closed lifecycle | Close does not rewrite issued receipts | `tests/test_collection_receipt.py` > `test_close_does_not_rewrite_issued_receipts` | ✅ COMPLIANT |
| Open/closed lifecycle | Cancel from closed reopens local receipts only | `tests/test_collection_receipt.py` > `test_cancel_reopens_closed_receipts_not_issued`; `tests/test_collection_sheet.py` > `test_cancel_closed_then_reinstate_to_submitted` | ✅ COMPLIANT |
| Open/closed lifecycle | Reinstate from cancelled to submitted | `tests/test_collection_sheet.py` > `test_reinstate_succeeds_while_seller_has_a_new_open_sheet` | ✅ COMPLIANT |
| Open/closed lifecycle | Raw state write rejected | `tests/test_collection_sheet.py` > `test_raw_state_write_invalid_transition_rejected` | ✅ COMPLIANT |
| Open/closed lifecycle | Cancel from submitted proposal or closed | `tests/test_collection_sheet.py` > `test_action_cancel_from_submitted_drafts_allocations`; `test_action_cancel_from_proposal_drafts_allocations`; `test_action_cancel_from_closed_drafts_allocations` | ✅ COMPLIANT |
| Open/closed lifecycle | Confirm from open refused | `tests/test_collection_sheet.py` > `test_confirm_from_open_refused` | ✅ COMPLIANT |
| Open/closed lifecycle | Submitted cannot return to open | `tests/test_collection_sheet.py` > `test_submitted_cannot_return_to_open` | ✅ COMPLIANT |
| Open/closed lifecycle | Cancelled cannot return to open | `tests/test_collection_sheet.py` > `test_cancelled_cannot_return_to_open` | ✅ COMPLIANT |
| Open/closed lifecycle | Proposal cannot return to submitted | `tests/test_collection_sheet.py` > `test_action_seller_close_refused_from_every_non_open_state`; `test_illegal_close_cancel_open_from_open_refused` (Reinstate only-cancelled guard) | ✅ COMPLIANT |
| Open/closed lifecycle | Illegal transition from open refused | `tests/test_collection_sheet.py` > `test_illegal_close_cancel_open_from_open_refused` | ✅ COMPLIANT |
| Open/closed lifecycle | Non-open create rejected | `tests/test_collection_sheet.py` > `test_non_open_create_rejected` | ✅ COMPLIANT |
| Frozen sheet refuses cash replacement create | Frozen sheet refuses replacement create | `tests/test_collection_receipt.py` > `test_frozen_sheet_refuses_replacement_create` | ✅ COMPLIANT |
| Frozen sheet refuses cash replacement create | Cancel still does not reverse | `tests/test_collection_receipt.py` > `test_cancel_does_not_create_reverse_replacements` | ✅ COMPLIANT |
| Freeze and issued immutability | Closed sheet refuses receipt write | `tests/test_collection_receipt.py` > `test_closed_sheet_refuses_receipt_and_value_write_unlink`; `test_cancelled_sheet_refuses_receipt_and_value_write_unlink` | ✅ COMPLIANT |
| Freeze and issued immutability | Issued receipt immutable | `tests/test_collection_receipt.py` > `test_issued_receipt_is_immutable` | ✅ COMPLIANT |
| Freeze and issued immutability | Frozen sheet refuses receipt create | `tests/test_collection_receipt.py` > `test_frozen_sheet_refuses_receipt_and_value_create` | ✅ COMPLIANT |
| Freeze and issued immutability | Cancel reopens closed not issued | `tests/test_collection_receipt.py` > `test_cancel_reopens_closed_receipts_not_issued` | ✅ COMPLIANT |
| ERP identity and state | Unique external id | `tests/test_collection_receipt.py` > `test_unique_external_receipt_id_allows_multiple_nulls` | ✅ COMPLIANT |
| ERP identity and state | Close leaves draft receipts closed locally | `tests/test_collection_receipt.py` > `test_close_issues_draft_receipts`; `test_close_skips_zero_value_receipts` | ✅ COMPLIANT |
| ERP identity and state | Historical issued keeps identity | `tests/test_collection_receipt.py` > `test_close_does_not_rewrite_issued_receipts`; `test_cancel_reopens_closed_receipts_not_issued` | ✅ COMPLIANT |
| ERP identity and state | Raw receipt state write rejected | `tests/test_collection_receipt.py` > `test_raw_receipt_state_write_rejected` | ✅ COMPLIANT |
| Read-mostly views | Form does not issue | `tests/test_collection_ui.py` > `test_receipt_views_use_list_and_form_does_not_issue` | ✅ COMPLIANT |
| Read-mostly views | Closed is a legal receipt state | `tests/test_collection_ui.py` > `test_receipt_views_use_list_and_form_does_not_issue` (`filter_closed`); `tests/test_collection_receipt.py` > `test_close_issues_draft_receipts` (Selection) | ✅ COMPLIANT |
| Frozen sheet refuses allocation create | Frozen sheet refuses allocation create | `tests/test_collection_allocation.py` > `test_frozen_sheet_refuses_allocation_create` | ✅ COMPLIANT |
| Frozen sheet refuses allocation create | Frozen sheet refuses line create | `tests/test_collection_allocation.py` > `test_frozen_sheet_refuses_line_create` | ✅ COMPLIANT |
| Frozen sheet refuses allocation create | Frozen sheet refuses revision create | `tests/test_collection_allocation.py` > `test_frozen_sheet_refuses_revision_create` | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Create defaults to draft | `tests/test_collection_allocation.py` > `test_create_defaults_to_draft` | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Draft legal on submitted | `tests/test_collection_allocation.py` > `test_create_draft_allocation_on_submitted`; `test_iff_draft_on_submitted_passes` | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Close confirms then closes | `tests/test_collection_sheet.py` > `test_action_close_from_proposal_confirms_then_closes`; `test_action_close_confirms_every_allocation` | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Cancel drafts allocations | `tests/test_collection_sheet.py` > `test_action_cancel_from_closed_drafts_allocations` | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Reinstate from cancelled leaves draft | `tests/test_collection_allocation.py` > `test_open_from_cancelled_leaves_draft`; `tests/test_collection_sheet.py` > `test_action_open_from_cancelled_leaves_draft` | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Confirm does not confirm allocations | `tests/test_collection_allocation.py` > `test_confirm_does_not_confirm_allocations` | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Invariant-breaking state write refused | `tests/test_collection_allocation.py` > `test_validate_and_reject_are_gone`; `test_draft_state_error_names_submitted` | ✅ COMPLIANT |
| Draft default and confirm-on-close invariant | Draft-state error names submitted | `tests/test_collection_allocation.py` > `test_draft_state_error_names_submitted` | ✅ COMPLIANT |

**Compliance summary**: 41/41 scenarios compliant (covering tests passed). REMOVED requirement `Close dispatches create_receipt` has no scenarios; removal is proven by `test_action_close_without_connector_succeeds` (`create_receipt` patched `assert_not_called`) and by `models/collection_sheet.py` containing no `create_receipt` symbol.

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| Frozen associate create freeze | ✅ Implemented | `raise_if_create_vals_frozen` on allocation/line/revision/receipt/value/replacement create |
| Open/closed lifecycle | ✅ Implemented | `action_close` strips connector; `_mark_draft_receipts_closed`; Cancel `_reopen_closed_receipts`; Reinstate → `submitted` |
| Frozen sheet refuses cash replacement create | ✅ Implemented | replacement create calls helper after gate |
| Freeze and issued immutability | ✅ Implemented | receipt intercept + freeze create; issued stays `collection_receipt_issuing` |
| ERP identity and state | ✅ Implemented | Selection `draft`/`closed`/`issued`; no `external_receipt_id` on local Close |
| Read-mostly views | ✅ Implemented | Closed search filter; `external_receipt_id` hidden; `<list>` |
| Close dispatches create_receipt (REMOVED) | ✅ Removed | dispatcher loop gone from `action_close`; `create_receipt` remains unused |
| Frozen sheet refuses allocation create | ✅ Implemented | helper on `sheet_id` after gates |
| Draft default and confirm-on-close invariant | ✅ Implemented | Close confirms then closes; Confirm does not confirm |

Manifest `19.0.1.44.0`. No `migrations/19.0.1.44.0/`.

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| Strip Close `create_receipt` | ✅ Yes | `action_close` has no dispatcher call |
| Every draft receipt → `closed` | ✅ Yes | `_action_mark_closed` on all drafts including empty |
| Audited `draft ↔ closed` intercept | ✅ Yes | `collection_receipt_audited_state`; issuing context kept |
| `raise_if_sheet_frozen` / create helper | ✅ Yes | `raise_if_create_vals_frozen`; bypasses documented, not `message_post` |
| No SQL / no `issued` remap | ✅ Yes | leftover pin forbids migrate folder |
| MCP Seller Close unchanged | ✅ Yes | tools not edited |

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | Found in apply-progress TDD Cycle Evidence table |
| All tasks have tests | ✅ | 15/15 implementation tasks name test files; 6.2/6.3 are verify-only; R.1 pin tests exist |
| RED confirmed (tests exist) | ✅ | Phase 1–5 and R.1 test files exist and were executed RED then GREEN |
| GREEN confirmed (tests pass) | ✅ | Authoritative suite **0 failed, 0 error(s) of 950 tests**, invoke exit 0; wrap pin greened |
| Triangulation adequate | ✅ | invoice+quotation; valued vs empty drafts; closed+cancelled create; Cancel submitted/proposal/closed |
| Safety Net for modified files | ⚠️ | Phase 1 in-place rewrites recorded N/A; Phases 2–4 recorded 5/5, 8/8, 6/6 safety nets |

**TDD Compliance**: 5/6 checks passed. Phase 1 GREEN `deferred-to-phase-2-4` then later GREEN is valid Strict TDD. Prior verify FAIL (`sha256:59ddea388282fc0317c1d2ae434b8d2866c4a589b51b2e0ba57d0130c984de82`) was the AGENTS wrap pin; R.1 remediates it.

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 0 dedicated | 0 | helpers exercised via TransactionCase |
| Integration | 950 passed (suite 950) | 7 modified `tests/test_collection_*.py` | Odoo TransactionCase / containerized PostgreSQL |
| E2E | 0 | 0 | not installed |
| **Total** | **950** | **7 modified + rest of module** | |

### Changed File Coverage
Coverage analysis skipped — no coverage tool detected

### Assertion Quality
| File | Line | Assertion | Issue | Severity |
|------|------|-----------|-------|----------|
| `tests/test_collection_receipt.py` | 1008 | `test_close_missing_connector_rolls_back` | Name leftover; body now asserts local Close success (`_close_locally` patches `create_receipt`) | SUGGESTION |

**Assertion quality**: 0 CRITICAL, 0 WARNING. ✅ All assertions verify real behavior (`assert_not_called`, state/`external_receipt_id`, UserError, no persist). R.1 wrap-tolerant `assertIn(..., " ".join(agents.split()))` still asserts the Close contract phrases exist in AGENTS.md.

### Quality Metrics
**Linter**: ✅ No errors (optional C8101 manifest author warning; apply 6.3 passed)
**Type Checker**: ➖ Not available

### Issues Found
**CRITICAL**: None

**WARNING**:
- Satellite `collection_receipt_proposal`: 3 failed, 1 error of 140 (apply 6.2). Pre-existing board drift (`document_numbers` never on `collection.receipt`; FIFO vs `line_ids`; company-rule RPC). Not caused by local Close; satellite not edited.
- Phase 1 TDD safety net recorded N/A for in-place Close-test rewrites.
- `Proposal cannot return to submitted` has no dedicated Reinstate-from-proposal Given; coverage is Seller Close from proposal plus the only-cancelled Reinstate guard.
- Working tree still carries unrelated `models/collection_sheet_report.py` and `tests/test_collection_sheet_report_data.py` edits from other work.

**SUGGESTION**:
- Rename `test_close_missing_connector_rolls_back` to match local-success behavior.

### Verdict
PASS WITH WARNINGS
Authoritative collection tests exited 0 (`0 failed of 950`); 41/41 spec scenarios compliant; AGENTS wrap pin remediates the prior FAIL. Satellite board suite remains red and is out of this Close contract.
