```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:d8a5540166ed6956b3054606b8faf5909025c96c2e10c55ece1d916a765731a6
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 8/8
scenarios: 14/14
test_command: invoke test -m collection --mode=update
test_exit_code: 0
test_output_hash: sha256:e88c784032a58a526eca048c1b0258cb7f05feb5ea10e09ba53354cc7f8d57b0
build_command: docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init
build_exit_code: 0
build_output_hash: sha256:3f3ed72dbb604402795a33b96913f490ff5f91f98a8fee0f8db7eddd7be98f4e
```

## Verification Report

**Change**: `collection-allocations`
**Version**: collection `19.0.1.25.0` (delta specs `collection-allocations` + `collection-vouchers` + `collection-sheets`)
**Mode**: Strict TDD

Delta spec counts (actual `### Requirement:` / `#### Scenario:` blocks): allocations 5/7 + vouchers 1/1 + sheets 2/6 = **8 requirements**; **14 scenarios**.

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 15 |
| Tasks complete | 15 |
| Tasks incomplete | 0 |

All `tasks.md` items 1.1–3.3 are `[x]`. Full spec verification proceeded.

### Build & Tests Execution
**Build**: ✅ Passed (module upgrade; `invoke img-build` skipped as not this change)

```text
docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init
exit 0
output sha256:3f3ed72dbb604402795a33b96913f490ff5f91f98a8fee0f8db7eddd7be98f4e
odoo: Modules loaded.
```

**Tests**: ✅ 502 passed / ❌ 0 failed / ⚠️ 0 skipped

```text
invoke test -m collection --mode=update
exit 0
output sha256:e88c784032a58a526eca048c1b0258cb7f05feb5ea10e09ba53354cc7f8d57b0
odoo.tests.result: 0 failed, 0 error(s) of 502 tests when loading database 'devel'
odoo.tests.stats: collection: 558 tests 24.34s 40179 queries
```

**Lint** (not envelope): scoped `pre-commit run --files` on changed collection paths, exit 0. Optional pylint `C8101` (`manifest-required-author`, author `Eynes`) on `__manifest__.py`. Mandatory pylint-odoo hook passed. Duplicate OCR/seller field-label warnings appeared during registry load (pre-existing).

**Coverage**: ➖ Not available — Coverage analysis skipped — no coverage tool detected

### Spec Compliance Matrix
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| MCP create_collection_allocation | First create | `test_collection_mcp_allocation.py` > `test_first_create_confirmed_revision_one_totals`; `test_collection_allocation.py` > `test_unique_sheet_partner_rejected` | ✅ COMPLIANT |
| MCP create_collection_allocation | Authorization denied | `test_collection_mcp_allocation.py` > `test_empty_vouchers_and_authorization_denied` | ✅ COMPLIANT |
| Idempotency and amend | Replay by request_id, content_hash, or UniqueViolation | `test_collection_mcp_allocation.py` > `test_request_id_replay_zero_writes`, `test_content_hash_replay_new_request_id_no_extra_revision`, `test_unique_violation_same_company_replays`, `test_unique_violation_hidden_other_company_generic_no_ids` | ✅ COMPLIANT |
| Idempotency and amend | Amend voucher superset or overlap | `test_collection_mcp_allocation.py` > `test_amend_superset_bumps_revision`, `test_subset_and_partial_overlap_rejected`, `test_destination_not_confirmed_refuses_amend` | ✅ COMPLIANT |
| Input and sheet gates | Ineligible input rejected | `test_collection_mcp_allocation.py` > `test_amount_null_or_non_positive_rejected`, `test_rejected_voucher_other_company_other_sheet_mixed_rejected`, `test_binding_only_resolve_does_not_create_or_call_partner_resolve`, `test_unbound_and_partner_mismatch_rejected_no_create` | ✅ COMPLIANT |
| Revalidation and residual | Fresh debt, residual, and confirmed-only constraint | `test_collection_mcp_allocation.py` > `test_revalidation_subtracts_other_confirmed_and_validated`, `test_rejected_allocation_does_not_reduce_available`, `test_invoice_missing_from_fresh_debt_rejected`, `test_ignores_caller_total_debt_stores_fresh_summary`, `test_residual_reason_and_empty_invoices_on_account`; `test_collection_allocation.py` > `test_residual_negative_rejected_only_while_confirmed`, `test_residual_positive_requires_reason_only_when_confirmed` | ✅ COMPLIANT |
| Freeze, revisions, ACL, back-office | Freeze, revisions, and back-office | `test_collection_allocation.py` > `test_freeze_rejects_writes_when_not_confirmed`, `test_delete_command_unassigns_without_destroying_voucher`, `test_revision_immutable_and_request_id_unique`, `test_unlink_with_revisions_refused`, `test_validate_and_reject_use_context_gate`; `test_collection_mcp_allocation.py` > `test_destination_not_confirmed_refuses_amend`; `test_collection_allocation_acl.py` > `test_allocation_and_line_acl_full_crud`, `test_revision_acl_read_create_no_write_unlink`, `test_three_company_ir_rules`, `test_allocation_models_have_no_sudo` | ✅ COMPLIANT |
| Voucher allocation membership | allocation_id write and unlink | `test_collection_allocation.py` > `test_allocation_id_write_only_when_both_confirmed_or_unset`, `test_allocated_voucher_unlink_refused_including_pending` | ✅ COMPLIANT |
| Sheet form notebook | Sheet form notebook | `test_collection_ui.py` > `test_sheet_form_notebook_vouchers_and_allocations` | ✅ COMPLIANT |
| Membership, dates, and deletion | Assign and reassign | `test_collection_sheet.py` > `test_reassign_moves_voucher_to_sheet_b_only` | ✅ COMPLIANT |
| Membership, dates, and deletion | Empty sheet | `test_collection_sheet.py` > `test_empty_sheet_dates_false_and_no_received_date` | ✅ COMPLIANT |
| Membership, dates, and deletion | Dates from member create_date | `test_collection_sheet.py` > `test_dates_from_utc_member_create_date` | ✅ COMPLIANT |
| Membership, dates, and deletion | Unlink unassigns when no allocations | `test_collection_sheet.py` > `test_unlink_sheet_unassigns_vouchers`, `test_unlink_closed_sheet_unassigns_vouchers` | ✅ COMPLIANT |
| Membership, dates, and deletion | Unlink refused when allocations exist | `test_collection_sheet.py` > `test_unlink_refused_when_allocations_exist` | ✅ COMPLIANT |

**Compliance summary**: 14/14 scenarios compliant

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| MCP create_collection_allocation | ✅ Implemented | `@mcp_tool` write on mixin; UNIQUE(sheet, partner); payload `{allocation:{id,name,state,revision,total_vouchers,total_applied,residual}}`; no sudo |
| Idempotency and amend | ✅ Implemented | request_id replay; content_hash replay; PUT superset amend; UniqueViolation invalidate_all then replay/generic |
| Input and sheet gates | ✅ Implemented | amount>0, not rejected, one partner/seller/sheet, binding-only, open same-company sheet |
| Revalidation and residual | ✅ Implemented | fresh debt minus other confirmed/validated; residual>=0 and reason iff >0 only while confirmed |
| Freeze, revisions, ACL, back-office | ✅ Implemented | freeze when not confirmed; DELETE sanitizer; revision UNIQUE(request_id); ACL 1,1,1,1 / 1,0,1,0; validate/reject context gate |
| Voucher allocation membership | ✅ Implemented | `allocation_id` set-null + check_company; write iff both confirmed/unset; ondelete refuses allocated unlink |
| Sheet form notebook | ✅ Implemented | notebook pages Vouchers (`voucher_ids`) and Allocations (`allocation_ids`) |
| Membership, dates, and deletion | ✅ Implemented | empty unlink unassigns; allocated unlink UserError + FK restrict; dates from create_date |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| models.Constraint / related stored currency | ✅ Yes | line/revision related stored `currency_id` and `company_id` |
| revision.request_id UNIQUE | ✅ Yes | gated create; IntegrityError on dup |
| advisory lock create; FOR UPDATE amend | ✅ Yes | lock `(sheet_id, partner_id)`; FOR UPDATE then next rev |
| PUT voucher superset | ✅ Yes | subset/partial overlap UserError, no writes |
| ERP available = fresh − other confirmed/validated | ✅ Yes | rejected applications ignored |
| Residual constrain while confirmed | ✅ Yes | validated amount edit may go negative |
| O2M DELETE sanitizer | ✅ Yes | vouchers persist unassigned |
| Binding-only partner; never sudo | ✅ Yes | no `resolve_customer_partner`; inspect + file source |
| Sequence CA/ via 19.0.1.25.0 migrate | ✅ Yes | SPECS padding 4; not in 1.17.0 codes |
| `<list>`; menu 30 | ✅ Yes | path `collection-allocations`; after sheets 20 |
| content_hash SHA-256 | ✅ Yes | matching hash new request_id does not add revision |
| sheet_id ondelete=restrict | ⚠️ Documented | FK restrict **and** `@api.ondelete` UserError (no raise in `unlink()`) |
| UniqueViolation reclassify | ⚠️ Documented | live path implemented; same-company UV test patches `_collection_allocation_write` |
| Amend residual placeholder | ⚠️ Documented | placeholder `residual_reason` across `Command.clear()` flush |
| Sheet nested list partner_id | ⚠️ Documented | Allocations nested `<list>` omits `partner_id` |

### Issues Found
**CRITICAL**: None
**WARNING**:
- Allocated-sheet delete uses `@api.ondelete` UserError in addition to `sheet_id ondelete="restrict"` (pylint E8140); spec still met.
- Amend persist keeps a placeholder `residual_reason` across `Command.clear()` flush so confirmed residual constraint does not fire mid-write.
- Same-company UniqueViolation replay is exercised by missing the first `request_id` search then raising `UniqueViolation` from `_collection_allocation_write` (live UNIQUE(sheet, partner) hash-replays before insert).
- Sheet notebook Allocations nested `<list>` omits `partner_id` so existing unbound-partner_id count on the sheet form stays one (voucher membership list).
**SUGGESTION**:
- Pre-existing optional pylint `C8101` manifest author `Eynes` (mandatory pylint passed).
- Pre-existing duplicate OCR/seller field-label warnings on `collection.voucher`.
- MuK MCP `get_tools` drops JSON Schema `exclusiveMinimum`; Python still rejects `amount_applied` ≤ 0.
- Missing filestore blobs on `devel` produce `ir.attachment` FileNotFoundError INFO during `load_menus`; tests still pass.

### Verdict
PASS WITH WARNINGS
All 8 requirements and 14 scenarios have passing covering tests; documented design deviations do not break specs.

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | TDD Cycle Evidence table in `apply-progress.md` for tasks 1.1–3.3 |
| All tasks have tests | ✅ | 15/15 have test files or documented suite/docs coverage (1.9/2.3/3.3 verification) |
| RED confirmed (tests exist) | ✅ | New: `tests/test_collection_allocation.py`, `tests/test_collection_allocation_acl.py`, `tests/test_collection_mcp_allocation.py`; UI/sheet/migration methods exist |
| GREEN confirmed (tests pass) | ✅ | This run: 0 failed, 0 error(s) of 502 tests |
| Triangulation adequate | ✅ | UNIQUE other partner/sheet; freeze vs confirmed writable; residual 0 / +reason / negative-after-validate; request_id vs content_hash; subset vs overlap; confirmed vs validated subtract vs rejected ignore |
| Safety Net for modified files | ✅ | 1.3/1.4/3.1 recorded existing suites before edit; 1.1/1.2/2.1 N/A new files |

**TDD Compliance**: 6/6 checks passed

---

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 27 | 3 | Odoo TransactionCase (`test_collection_allocation.py` 18, `test_collection_allocation_acl.py` 6, 3 new methods in `test_collection_ui.py`) |
| Integration | 21 | 1 | Containerized Odoo MCP `_call` (`test_collection_mcp_allocation.py`) |
| E2E | 0 | 0 | not installed |
| **Total** | **48** | **4** | focused tests created for this change |

Envelope run also executed the full collection module suite (502). Additional covering tests live in modified `test_collection_sheet.py` and `test_collection_company_migration.py`.

---

### Changed File Coverage
Coverage analysis skipped — no coverage tool detected

---

### Assertion Quality

**Assertion quality**: ✅ All assertions verify real behavior

Scanned new/changed focused files. UNIQUE tests raise `IntegrityError`. MCP tests assert payload totals, `write_date` unchanged on replay, UserError with no writes, generic conflict without ids, and binding/partner counts. Freeze/unlink tests assert voucher persistence and `allocation_id`. ACL tests assert CSV bits, `AccessError`/`UserError`, and hidden other-company records. UI tests assert `<list>` not `<tree>`, menu sequence 30, and notebook page fields. `assertTrue(allocation.id)` is paired with partner/sheet/state value checks. UniqueViolation same-company test patches write but asserts replay id, revision, and unchanged `write_date`.

---

### Quality Metrics
**Linter**: ⚠️ 0 errors, 1 optional warning (`C8101` manifest author `Eynes` on `collection/__manifest__.py`). Mandatory pylint-odoo hook passed. Scoped pre-commit exit 0.
**Type Checker**: ➖ Not available
