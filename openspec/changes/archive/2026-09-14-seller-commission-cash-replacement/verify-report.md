```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:1eba49d61402734838bfc0fc5f9c22ef0b4e73dadfd4d2bdeae186653041fea1
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 11/11
scenarios: 31/31
test_command: invoke test -m collection --mode=update
test_exit_code: 0
test_output_hash: sha256:206a17fff75141317c530748ad4e4d0c42e52c55bfeace21b2d878e1dc6976d8
build_command: invoke install -m collection
build_exit_code: 0
build_output_hash: sha256:5a3f0059af2d4bfda85ce5e4f9abf93b954d9d13ea3a42e679b0002f6c519ce1
```

## Verification Report

**Change**: seller-commission-cash-replacement
**Version**: collection 19.0.1.48.0
**Mode**: Strict TDD

Delta specs counted 11 `### Requirement:` headings and 31 `#### Scenario:` headings across `specs/collection-vouchers`, `collection-sheets`, `collection-receipts`, and `collection-sheet-report`. `evidence_revision` is SHA-256 of those four delta spec files in stable path order.

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 29 |
| Tasks complete | 29 |
| Tasks incomplete | 0 |

### Build & Tests Execution

**Build**: ✅ Passed

```text
invoke install -m collection
exit 0
Modules loaded. Registry loaded in 4.666s. Initiating shutdown.
```

`invoke img-build` was not run: no Dockerfile/dependency change; module-load install is the declared build for this verify.

**Tests**: ✅ 1003 passed / ❌ 0 failed / ⚠️ 0 skipped (authoritative `collection` suite; stats 1085 tests)

```text
invoke test -m collection --mode=update
collection: 1085 tests 65.09s 97977 queries
0 failed, 0 error(s) of 1003 tests when loading database 'devel'
```

Logged `ERROR: duplicate key value violates unique constraint "collection_voucher_document_id_uniq"` lines are expected UniqueViolation fixtures, not suite failures.

**Coverage**: ➖ Not available — `openspec/config.yaml` `testing.coverage.available: false`

**Lint** (report body only; not envelope test_command): scoped `pre-commit run --files` on collection files excluding `openspec/changes/archive/` — exit 0. pylint optional C8101 `manifest-required-author` (Eynes vs Seedian) is a pre-existing warning; hook Passed.

### Spec Compliance Matrix

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Document type catalog and Selection | Ninth code present after upgrade | `test_collection_company_migration.py` > `test_upgrade_148_unions_seller_commission_keeps_extras` | ✅ COMPLIANT |
| Document type catalog and Selection | New company allows all nine | `test_collection_company_settings.py` > `test_new_company_enables_all_nine_document_types`; `test_collection_company_migration.py` > `test_new_company_copies_sequences_seeds_types_empty_sellers` | ✅ COMPLIANT |
| Document type catalog and Selection | MCP callers cannot mint a commission | `test_collection_mcp_allocation.py` > `test_seller_commission_seller_confirmed_rejected` | ✅ COMPLIANT |
| Sentinel partner for customerless vouchers | Commission stamps its own sentinel | `test_collection_voucher.py` > `test_seller_commission_stamps_sentinel_partner` | ✅ COMPLIANT |
| Sentinel partner for customerless vouchers | Customer partner refused on a commission | `test_collection_voucher.py` > `test_seller_commission_refuses_customer_partner` | ✅ COMPLIANT |
| Sentinel partner for customerless vouchers | Sentinel seeding is idempotent | `test_collection_voucher.py` > `test_seller_commission_sentinel_seeding_is_idempotent` | ✅ COMPLIANT |
| Confirm review gate | Commission at validated_seller does not block Confirm | `test_collection_voucher.py` > `test_document_type_selection_includes_nine_codes` (frozenset only); deposit triangulation `test_action_confirm_seller_deposit_validated_seller_blocks`; no Confirm Given a leftover `seller_commission` at `validated_seller` | ⚠️ PARTIAL |
| Confirm review gate | Deposit still blocks Confirm | `test_collection_sheet.py` > `test_action_confirm_seller_deposit_validated_seller_blocks` | ✅ COMPLIANT |
| Cash replacement trigger | Commission promotion replaces cash | `test_collection_cash_replacement.py` > `test_commission_replaces_cash_preserving_totals`; `test_collection_sheet.py` > `test_confirm_mints_one_seller_commission_and_replaces_cash` | ✅ COMPLIANT |
| Cash replacement trigger | Re-write does not re-replace | `test_collection_sheet.py` > `test_reconfirm_after_reinstate_mints_no_second_commission`; `test_collection_cash_replacement.py` > `test_non_transition_write_does_not_re_replace` | ✅ COMPLIANT |
| Confirm mints the seller commission voucher | Confirm mints one commission voucher | `test_collection_sheet.py` > `test_confirm_mints_one_seller_commission_and_replaces_cash` | ✅ COMPLIANT |
| Confirm mints the seller commission voucher | Zero commission mints nothing | `test_collection_sheet.py` > `test_zero_commission_confirm_mints_nothing` | ✅ COMPLIANT |
| Confirm mints the seller commission voucher | Refused Confirm mints nothing | `test_collection_sheet.py` > `test_review_gate_refused_confirm_mints_nothing` | ✅ COMPLIANT |
| Confirm mints the seller commission voucher | Re-Confirm after Reinstate mints no second voucher | `test_collection_sheet.py` > `test_reconfirm_after_reinstate_mints_no_second_commission` | ✅ COMPLIANT |
| Confirm mints the seller commission voucher | Disabled seller still allows Confirm | `test_collection_sheet.py` > `test_disabled_seller_confirm_still_mints_commission` | ✅ COMPLIANT |
| Confirm mints the seller commission voucher | Mint does not alter the cash arithmetic | `test_collection_sheet.py` > `test_commission_mint_does_not_change_cash_on_hand_or_cash_banked` | ✅ COMPLIANT |
| Confirm cash declaration gate | Undeclared cash blocks Confirm and the mint | `test_collection_sheet.py` > `test_undeclared_cash_gate_refused_confirm_mints_nothing` | ✅ COMPLIANT |
| Value-preserving cash replacement | Issued receipt skipped, not aborted | `test_collection_cash_replacement.py` > `test_issued_receipt_skipped_not_aborted` | ✅ COMPLIANT |
| Value-preserving cash replacement | Commission replaces cash preserving totals | `test_collection_cash_replacement.py` > `test_commission_replaces_cash_preserving_totals` | ✅ COMPLIANT |
| Value-preserving cash replacement | Deposit and commission share one cash pool | `test_collection_cash_replacement.py` > `test_deposit_and_commission_share_one_cash_pool` | ✅ COMPLIANT |
| Value-preserving cash replacement | Over-declared commission refused | `test_collection_cash_replacement.py` > `test_over_declared_commission_raises` | ✅ COMPLIANT |
| Value-preserving cash replacement | Excess deposit still silently drops | `test_collection_cash_replacement.py` > `test_excess_deposit_still_silently_drops` | ✅ COMPLIANT |
| Cash replacement ledger | Commission replace row is distinguishable | `test_collection_cash_replacement.py` > `test_commission_replaces_cash_preserving_totals` | ✅ COMPLIANT |
| Cash replacement ledger | Commission voucher survives its ledger rows | `test_collection_cash_replacement.py` > `test_commission_voucher_cannot_unlink_once_referenced` | ✅ COMPLIANT |
| Voucher blocks and tendered | Commission excluded from collected and tendered | `test_collection_sheet_report_data.py` > `test_commission_excluded_from_collected_and_tendered` | ✅ COMPLIANT |
| Voucher blocks and tendered | Recon unchanged by the mint | `test_collection_sheet_report_data.py` > `test_recon_unchanged_by_commission_mint` | ✅ COMPLIANT |
| Remittance cash_banked | cash_banked excludes the commission | `test_collection_sheet_report_data.py` > `test_cash_banked_excludes_seller_commission` | ✅ COMPLIANT |
| Residual cash is reported, not enforced | Residual surfaces after Confirm | `test_collection_sheet_report_data.py` > `test_residual_cash_value_total_from_cash_receipt_values`; `test_collection_ui.py` > `test_sheet_form_residual_banner_outside_open_submitted` | ✅ COMPLIANT |
| Residual cash is reported, not enforced | Silent while submitted | `test_collection_sheet_report_data.py` > `test_residual_computes_while_submitted_but_is_not_enforced`; `test_collection_ui.py` > `test_sheet_form_residual_banner_outside_open_submitted` | ✅ COMPLIANT |
| Residual cash is reported, not enforced | Residual never blocks | `test_collection_sheet_report_data.py` > `test_residual_never_blocks_close`; `test_collection_ui.py` > `test_sheet_form_residual_banner_does_not_block_buttons` | ✅ COMPLIANT |
| Residual cash is reported, not enforced | Residual is outside the recon algebra | `test_collection_sheet_report_data.py` > `test_residual_is_outside_recon_algebra` | ✅ COMPLIANT |

**Compliance summary**: 30/31 COMPLIANT, 1/31 PARTIAL (envelope treats PARTIAL as complete because covering tests passed)

### Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| Document type catalog and Selection | ✅ Implemented | Ninth Selection + catalog XMLID; MCP rejects `seller_commission` before `_DOCUMENT_TYPES`; migrate `19.0.1.48.0` unions extras kept |
| Sentinel partner for customerless vouchers | ✅ Implemented | `collection.partner_seller_commission`; `_SENTINEL_PARTNER_GETTERS` map; type-specific UserError |
| Confirm review gate | ✅ Implemented | `CONFIRM_REVIEW_EXEMPT_TYPES = {cash, seller_commission}`; `_vouchers_blocking_confirm`; deposit remains non-exempt |
| Cash replacement trigger | ✅ Implemented | `CASH_REPLACEMENT_TYPES`; `_cash_replacers_entering_validated_collections` + `_run_cash_replacement` |
| Confirm mints the seller commission voucher | ✅ Implemented | `_ensure_seller_commission_voucher` after both gates, before proposal; `sc-<uuid4 hex>`; bypass `collection_seller_commission_mint`; no sudo |
| Confirm cash declaration gate | ✅ Implemented | Undeclared collected cash raises before mint |
| Value-preserving cash replacement | ✅ Implemented | Skip `issued` before kind buckets; commission remainder UserError; deposit remainder silent |
| Cash replacement ledger | ✅ Implemented | `deposit_voucher_id` help names both types; column not renamed; unlink restrict |
| Voucher blocks and tendered | ✅ Implemented | Skip commission in blocks; explicit `elif seller_commission: continue` in tendered; recon algebra unchanged |
| Remittance cash_banked | ✅ Implemented | Sums `seller_deposit` only |
| Residual cash is reported, not enforced | ✅ Implemented | `residual_cash_value_total` compute; form `role="alert"` silent in open/submitted |

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| Mint at Confirm after both gates, before proposal | ✅ Yes | `action_confirm` order matches the design sequence diagram |
| Idempotency on existing member voucher | ✅ Yes | Guard filters `document_type == seller_commission` |
| Raise only for commission remainder | ✅ Yes | Deposit still silent |
| Second sentinel XMLID | ✅ Yes | `collection.partner_seller_commission` |
| Narrow `_assert_new_work` bypass, never sudo | ✅ Yes | Context key + `document_type == seller_commission`; ORM cash+key still raises |
| MCP enum unchanged; reject first | ✅ Yes | Not in `_DOCUMENT_TYPES` |
| Skip issued receipts | ✅ Yes | Phase 0 filter before kind buckets |
| Leave cash_on_hand / recon algebra | ✅ Yes | Double-count pin passed |
| Keep `_apply_seller_deposit_partner` name | ✅ Yes | Documented apply deviation |
| Field help= for replacing voucher | ✅ Yes | Documented apply deviation vs prose "docstring" |

### TDD Compliance

| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | Found in `apply-progress.md` TDD Cycle Evidence table (all 29 tasks) |
| All tasks have tests | ✅ | Implementation tasks 0.1–4.4 have test files; 0.3/4.5/5.1–5.4 are spec/docs/verify |
| RED confirmed (tests exist) | ✅ | Named test files exist under `tests/` |
| GREEN confirmed (tests pass) | ✅ | Independent `invoke test -m collection --mode=update`: 0 failed / 0 errors of 1003 |
| Triangulation adequate | ✅ | Multi-scenario behaviors have 2+ cases (issued skip, remainder split, mint/no-op/gates, collected 500/100, residual leftover/issued) |
| Safety Net for modified files | ✅ | Apply recorded class baselines before GREEN (cash-replacement 19 then 21; sheet 118; report-data 54) |

**TDD Compliance**: 6/6 checks passed

### Test Layer Distribution

| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 0 | 0 | Odoo TransactionCase available; unused for this change |
| Integration | 40 of-record new/updated methods (plus full-suite 1003) | `test_collection_cash_replacement.py`, `test_collection_voucher.py`, `test_collection_sheet.py`, `test_collection_sheet_report_data.py`, `test_collection_ui.py` (`TestCollectionResidualBanner`), `test_collection_company_settings.py`, `test_collection_company_migration.py`, `test_collection_mcp_allocation.py` | Containerized Odoo + PostgreSQL |
| E2E | 0 | 0 | not installed (`testing.layers.e2e.available: false`) |
| **Total** | **1003 suite / 40 of-record** | **8 modified test modules** | |

### Changed File Coverage

Coverage analysis skipped — no coverage tool detected

### Assertion Quality

**Assertion quality**: ✅ All assertions verify real behavior

No tautologies, ghost loops, or empty-only assertions in the of-record methods. Amounts, states, UserError text, XML `invisible=`, ledger `document_type`, and zero-write MCP counts are asserted. `inspect.getsource` on tendered/blocks and MCP modules is the spec-required explicit-exclusion / no-widen contract, not a smoke test.

### Quality Metrics

**Linter**: ⚠️ 1 warning (pylint optional C8101 `manifest-required-author` on `__manifest__.py`; hook Passed)
**Type Checker**: ➖ Not available

### Issues Found

**CRITICAL**: None

**WARNING**:
- Confirm review gate scenario "Commission at validated_seller does not block Confirm" is PARTIAL: `CONFIRM_REVIEW_EXEMPT_TYPES` membership is asserted and deposit still blocks Confirm, but no test Given a leftover `seller_commission` at `validated_seller` then Confirm. Re-Confirm coverage uses a member already at `validated_collections`.
- pylint optional C8101 Eynes author vs Seedian (pre-existing; hook Passed).

**SUGGESTION**:
- Add a focused Confirm case with a pre-existing `seller_commission` at `validated_seller` to close the PARTIAL gap.
- Critical business logic is covered at TransactionCase/integration layer only; E2E tools are not in capabilities.

### Verdict

PASS WITH WARNINGS
Independent suite is green (1003/1003). 30 scenarios COMPLIANT and 1 PARTIAL (Confirm with leftover seller_commission at validated_seller is not a dedicated Given); covering tests for the exempt set and deposit triangulation passed.
