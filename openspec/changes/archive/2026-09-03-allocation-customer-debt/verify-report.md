```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:9f085efd34dc9310025e2c39a9464b859aaa714c92ad5e27c9a75397ec593c36
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 10/10
scenarios: 47/47
test_command:
  "docker compose run --rm -e DB_FILTER=^devel$ odoo odoo --test-enable
  --stop-after-init --workers=0 -u collection --test-tags /collection"
test_exit_code: 0
test_output_hash: sha256:bf9c34a9c66538ce172be93482dbf77e84a59657dae91a1d03ec6ebe0bd79cec
build_command:
  "docker compose run --rm -e DB_FILTER=^devel$ odoo odoo --stop-after-init --workers=0
  -u collection"
build_exit_code: 0
build_output_hash: sha256:fdc55775a639d850be67bbd2f4cfae232899a743efb3a1744a2f1313a2aab4b2
```

## Verification Report

**Change**: `allocation-customer-debt` **Version**: collection `19.0.1.32.0`. Delta
specs: `collection-allocations` + `collection-vouchers` **Mode**: Strict TDD

Delta spec counts (actual `### Requirement:` / `#### Scenario:` blocks):
collection-allocations 7/26 + collection-vouchers 3/21 = **10 requirements**; **47
scenarios**. Matches the authoritative totals passed to the validator.
`evidence_revision` is SHA-256 of the two delta spec files concatenated.

### Completeness

| Metric           | Value |
| ---------------- | ----- |
| Tasks total      | 18    |
| Tasks complete   | 18    |
| Tasks incomplete | 0     |

All `tasks.md` items 1.1–4.5 are `[x]`. Full spec verification proceeded.

### Build & Tests Execution

**Build**: ✅ Passed (module upgrade `-u collection`). Configured `invoke img-build` was
**not** run: sibling `voucher-states-ui` is also in verify on the same devel DB / shared
Odoo image, so a full image rebuild would collide. Used `docker compose run --rm`
upgrade instead of stopping `seedian-odoo-1`.

```text
docker compose run --rm -e DB_FILTER=^devel$ odoo odoo --stop-after-init --workers=0 -u collection
exit 0
Modules loaded.
Registry loaded in 5.441s
output sha256:fdc55775a639d850be67bbd2f4cfae232899a743efb3a1744a2f1313a2aab4b2
```

**Tests**: ✅ 636 passed / ❌ 0 failed / ⚠️ 0 skipped. Re-executed this session via
`docker compose run --rm` (did not stop `seedian-odoo-1`). No SerializationFailure.
Equivalent intent: `invoke test -m collection --mode=update`.

```text
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection
exit 0
collection: 700 tests 31.49s 53088 queries
0 failed, 0 error(s) of 636 tests when loading database 'devel'
output sha256:bf9c34a9c66538ce172be93482dbf77e84a59657dae91a1d03ec6ebe0bd79cec
```

**Coverage**: ➖ Not available / threshold: 0% → ➖ Not available

### Spec Compliance Matrix

| Requirement                               | Scenario                                                | Test                                                                                                                                                                                                                                                                                  | Result       |
| ----------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| ALLOC-01 Customer Debt snapshot and form  | Full outstanding including zeros                        | `test_collection_allocation.py > test_prepare_customer_debt_lines_snapshots_outstanding_zeros`; `test_collection_mcp_allocation.py > test_applied_only_payload_expands_outstanding_zeros`                                                                                             | ✅ COMPLIANT |
| ALLOC-01 Customer Debt snapshot and form  | Empty lines without connector                           | `test_collection_allocation.py > test_prepare_customer_debt_lines_empty_without_connector`; `test_prepare_customer_debt_lines_empty_without_binding`; `test_onchange_empty_when_unbound_partner`                                                                                      | ✅ COMPLIANT |
| ALLOC-01 Customer Debt snapshot and form  | Create omitted vs supplied; no backfill                 | `test_collection_allocation.py > test_create_omitted_line_ids_snapshots`; `test_create_supplied_line_ids_skips_snapshot`; `test_collection_company_migration.py > test_manifest_version_is_1_32_0` (migrate DROP only; no line INSERT)                                                | ✅ COMPLIANT |
| ALLOC-01 Customer Debt snapshot and form  | Existing-only vouchers and smart button                 | `test_collection_ui.py > test_allocation_form_vouchers_existing_only_many2many`; `test_allocation_form_stat_button_opens_vouchers`; `test_collection_allocation.py > test_action_open_vouchers_domain_is_allocation_id`; `test_delete_command_unassigns_without_destroying_voucher`   | ✅ COMPLIANT |
| ALLOC-01 Customer Debt snapshot and form  | Customer Debt parent arch                               | `test_collection_ui.py > test_allocation_form_customer_debt_helpers_no_residual_reason`; `test_collection_allocation_document_kind.py > test_parent_arch_document_kind_before_invoice_number`                                                                                         | ✅ COMPLIANT |
| ALLOC-02 Totals and residual formula      | Residual and zeros                                      | `test_collection_allocation.py > test_residual_is_debt_minus_applied`; `test_residual_negative_saves_on_draft_and_confirmed`; `test_zero_applied_line_persists`; `test_negative_amount_applied_rejected`; `test_totals_split_invoices_and_quotations`                                 | ✅ COMPLIANT |
| ALLOC-02 Totals and residual formula      | Reason dropped from persist                             | `test_collection_mcp_allocation.py > test_residual_reason_ignored_after_enum`; `test_collection_mcp_allocation_lookup.py > test_found_payload_omits_reason_includes_document_kind`; `test_collection_sheet_report_data.py > test_payload_residual_reason_is_empty_without_field_read` | ✅ COMPLIANT |
| ALLOC-03 Idempotency and amend            | Replay by request_id, content_hash, or UniqueViolation  | `test_collection_mcp_allocation.py > test_request_id_replay_zero_writes`; `test_content_hash_replay_new_request_id_no_extra_revision`; `test_unique_violation_same_company_replays`                                                                                                   | ✅ COMPLIANT |
| ALLOC-03 Idempotency and amend            | Amend voucher superset or overlap                       | `test_collection_mcp_allocation.py > test_amend_superset_bumps_revision`; `test_subset_and_partial_overlap_rejected`; `test_confirmed_destination_refuses_amend`                                                                                                                      | ✅ COMPLIANT |
| ALLOC-03 Idempotency and amend            | Residual reason excluded from content_hash              | `test_collection_mcp_allocation.py > test_reason_only_retry_is_hash_noop`                                                                                                                                                                                                             | ✅ COMPLIANT |
| ALLOC-04 Revalidation and residual        | Fresh debt, residual, and both-state constraint         | `test_collection_mcp_allocation.py > test_revalidation_subtracts_other_draft_and_confirmed`; `test_ignores_caller_total_debt_stores_fresh_summary`; `test_empty_invoices_on_account`; `test_invoice_missing_from_fresh_debt_rejected`                                                 | ✅ COMPLIANT |
| ALLOC-04 Revalidation and residual        | Residual holds on draft and confirmed                   | `test_collection_allocation.py > test_residual_zero_ok_on_draft_and_confirmed`; `test_residual_negative_saves_on_draft_and_confirmed`; `test_residual_is_debt_minus_applied`                                                                                                          | ✅ COMPLIANT |
| ALLOC-04 Revalidation and residual        | Expand applied-only payload                             | `test_collection_mcp_allocation.py > test_applied_only_payload_expands_outstanding_zeros`; `test_zero_applied_missing_from_erp_is_ignored`                                                                                                                                            | ✅ COMPLIANT |
| ALLOC-05 Source detach residual refuse    | Fully applied source detach allowed                     | `test_collection_allocation.py > test_fully_applied_source_detach_via_partner_write_succeeds`; `test_collection_voucher.py > test_partner_write_fully_applied_source_succeeds`                                                                                                        | ✅ COMPLIANT |
| ALLOC-05 Source detach residual refuse    | Leftover-voucher residual MUST NOT refuse detach        | `test_collection_allocation.py > test_leftover_less_than_amount_detach_succeeds`; `test_collection_voucher.py > test_unlink_draft_on_draft_leftover_less_than_amount_succeeds`; `test_partner_write_leftover_less_than_amount_succeeds`                                               | ✅ COMPLIANT |
| ALLOC-05 Source detach residual refuse    | Draft detach without leftover projection                | `test_collection_voucher.py > test_unlink_draft_on_draft_at_residual_zero_succeeds`; `test_collection_allocation.py > test_pending_unlink_on_draft_at_residual_zero_succeeds`                                                                                                         | ✅ COMPLIANT |
| ALLOC-05 Source detach residual refuse    | Confirmed source detach refused                         | `test_collection_allocation.py > test_confirmed_membership_write_refused`; `test_collection_voucher.py > test_confirmed_membership_write_refused`; `test_unlink_draft_on_confirmed_refused`                                                                                           | ✅ COMPLIANT |
| ALLOC-06 MCP get_collection_allocation    | Registered read tool                                    | `test_collection_mcp_allocation_lookup.py > test_discovered_as_method_read_mcp`                                                                                                                                                                                                       | ✅ COMPLIANT |
| ALLOC-06 MCP get_collection_allocation    | Unbound or missing returns null                         | `test_collection_mcp_allocation_lookup.py > test_unbound_identification_returns_null_without_creating_partner`; `test_no_open_sheet_returns_null`; `test_open_sheet_without_allocation_returns_null`                                                                                  | ✅ COMPLIANT |
| ALLOC-06 MCP get_collection_allocation    | Found payload and draft state                           | `test_collection_mcp_allocation_lookup.py > test_found_payload_omits_reason_includes_document_kind`; `test_found_open_sheet_state_is_draft`; `test_found_payload_omits_attachments_and_base64`                                                                                        | ✅ COMPLIANT |
| ALLOC-06 MCP get_collection_allocation    | Multi-open sheet and auth fail closed                   | `test_collection_mcp_allocation_lookup.py > test_multi_open_raises_existing_user_error`; `test_portal_and_public_callers_denied_access_error`; `test_non_enabled_seller_fails_closed`                                                                                                 | ✅ COMPLIANT |
| ALLOC-07 Allocation line document_kind    | Default invoice                                         | `test_collection_allocation_document_kind.py > test_default_invoice`                                                                                                                                                                                                                  | ✅ COMPLIANT |
| ALLOC-07 Allocation line document_kind    | Required selection                                      | `test_collection_allocation_document_kind.py > test_required_selection`                                                                                                                                                                                                               | ✅ COMPLIANT |
| ALLOC-07 Allocation line document_kind    | Quotation round-trip on draft                           | `test_collection_allocation_document_kind.py > test_quotation_round_trip_on_draft`                                                                                                                                                                                                    | ✅ COMPLIANT |
| ALLOC-07 Allocation line document_kind    | Parent arch before invoice_number                       | `test_collection_allocation_document_kind.py > test_parent_arch_document_kind_before_invoice_number`                                                                                                                                                                                  | ✅ COMPLIANT |
| ALLOC-07 Allocation line document_kind    | MCP create omits kind; get returns kind                 | `test_collection_allocation_document_kind.py > test_mcp_create_omits_kind_defaults_invoice`; `test_get_invoices_include_document_kind`                                                                                                                                                | ✅ COMPLIANT |
| VOUCH-01 Voucher allocation membership    | allocation_id write on draft or unset                   | `test_collection_voucher.py > test_allocation_id_write_on_draft_or_unset`; `test_collection_allocation.py > test_allocation_id_write_on_draft_or_unset`                                                                                                                               | ✅ COMPLIANT |
| VOUCH-01 Voucher allocation membership    | Confirmed membership write refused                      | `test_collection_voucher.py > test_confirmed_membership_write_refused`; `test_collection_allocation.py > test_confirmed_membership_write_refused`                                                                                                                                     | ✅ COMPLIANT |
| VOUCH-01 Voucher allocation membership    | Pending unlink on draft or unset                        | `test_collection_voucher.py > test_unlink_allowed_when_draft`; `test_unlink_draft_on_draft_allowed_when_residual_holds`; `test_collection_allocation.py > test_unallocated_pending_voucher_unlink_still_allowed`                                                                      | ✅ COMPLIANT |
| VOUCH-01 Voucher allocation membership    | Draft unlink MUST NOT use leftover-voucher residual     | `test_collection_voucher.py > test_unlink_draft_on_draft_at_residual_zero_succeeds`; `test_unlink_draft_on_draft_leftover_less_than_amount_succeeds`                                                                                                                                  | ✅ COMPLIANT |
| VOUCH-02 Partner write follows allocation | Same-write partner and allocation                       | `test_collection_voucher.py > test_partner_write_same_vals_attaches_draft_allocation`; `test_collection_allocation.py > test_same_write_matching_partner_and_allocation_holds`                                                                                                        | ✅ COMPLIANT |
| VOUCH-02 Partner write follows allocation | Fully applied source allowed                            | `test_collection_voucher.py > test_partner_write_fully_applied_source_succeeds`                                                                                                                                                                                                       | ✅ COMPLIANT |
| VOUCH-02 Partner write follows allocation | Target attaches without leftover residual check         | `test_collection_voucher.py > test_partner_write_attaches_when_target_residual_holds`                                                                                                                                                                                                 | ✅ COMPLIANT |
| VOUCH-02 Partner write follows allocation | Target left unallocated when no unique draft allocation | `test_collection_voucher.py > test_partner_write_left_unallocated_posts_chatter`                                                                                                                                                                                                      | ✅ COMPLIANT |
| VOUCH-02 Partner write follows allocation | Confirmed source refused                                | `test_collection_voucher.py > test_partner_write_confirmed_source_refused`; `test_collection_allocation.py > test_confirmed_source_partner_write_refused`                                                                                                                             | ✅ COMPLIANT |
| VOUCH-02 Partner write follows allocation | Approved or rejected voucher may move                   | `test_collection_voucher.py > test_all_voucher_states_may_change_partner`                                                                                                                                                                                                             | ✅ COMPLIANT |
| VOUCH-03 Voucher lifecycle                | Approve from pending                                    | `test_collection_voucher.py > test_action_validate_seller_from_draft_does_not_stamp_reviewer`                                                                                                                                                                                         | ✅ COMPLIANT |
| VOUCH-03 Voucher lifecycle                | Reject from pending                                     | `test_collection_voucher.py > test_action_reject_does_not_exist`                                                                                                                                                                                                                      | ✅ COMPLIANT |
| VOUCH-03 Voucher lifecycle                | Terminal states block transitions                       | `test_collection_voucher.py > test_terminal_states_block_validate_seller`                                                                                                                                                                                                             | ✅ COMPLIANT |
| VOUCH-03 Voucher lifecycle                | Collections only via Document Review                    | `test_collection_voucher.py > test_raw_write_validated_collections_refused`; `test_create_refuses_validated_collections`                                                                                                                                                              | ✅ COMPLIANT |
| VOUCH-03 Voucher lifecycle                | Delete from pending                                     | `test_collection_voucher.py > test_unlink_allowed_when_draft`; `test_unlink_draft_on_draft_allowed_when_residual_holds`                                                                                                                                                               | ✅ COMPLIANT |
| VOUCH-03 Voucher lifecycle                | Delete blocked when not pending                         | `test_collection_voucher.py > test_unlink_blocked_when_not_draft`                                                                                                                                                                                                                     | ✅ COMPLIANT |
| VOUCH-03 Voucher lifecycle                | Delete pending on confirmed allocation refused          | `test_collection_voucher.py > test_unlink_draft_on_confirmed_refused`; `test_collection_allocation.py > test_pending_unlink_on_confirmed_refused`                                                                                                                                     | ✅ COMPLIANT |
| VOUCH-03 Voucher lifecycle                | Delete on draft MUST NOT use leftover-voucher residual  | `test_collection_voucher.py > test_unlink_draft_on_draft_leftover_less_than_amount_succeeds`                                                                                                                                                                                          | ✅ COMPLIANT |
| VOUCH-03 Voucher lifecycle                | Kanban drag is audited                                  | `test_collection_ui.py > test_stages_kanban_deleted_action_is_list_form`; `test_form_statusbar_validate_seller_when_draft` (`clickable: False`)                                                                                                                                       | ✅ COMPLIANT |
| VOUCH-03 Voucher lifecycle                | Approve and Reject remain when review is off            | `test_collection_voucher.py > test_validate_seller_when_review_is_off`; `test_action_reject_does_not_exist`                                                                                                                                                                           | ✅ COMPLIANT |
| VOUCH-03 Voucher lifecycle                | Default pending                                         | `test_collection_voucher.py > test_defaults_on_create`                                                                                                                                                                                                                                | ✅ COMPLIANT |

**Compliance summary**: 47/47 scenarios compliant

VOUCH-03 preserved-state scenarios (Validate by Seller / no Reject / statusbar / kanban)
are sibling `voucher-states-ui` behavior kept in this MODIFIED delta. They passed in
this `/collection` run; they are not defects of `allocation-customer-debt`.

### Correctness (Static Evidence)

| Requirement                               | Status         | Notes                                                                                                                                                                                                         |
| ----------------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ALLOC-01 Customer Debt snapshot and form  | ✅ Implemented | `_prepare_customer_debt_lines` via `collection_connector_id` + binding; onchange skip confirmed; create iff `line_ids` omitted; many2many `no_create`; Customer Debt tab; smart button domain `allocation_id` |
| ALLOC-02 Totals and residual formula      | ✅ Implemented | `residual = total_debt − total_applied`; `amount_applied` default 0 + CHECK `>= 0`; no `residual_reason` field                                                                                                |
| ALLOC-03 Idempotency and amend            | ✅ Implemented | Hash omits `residual_reason`; replay / superset amend unchanged except reason-only no-op                                                                                                                      |
| ALLOC-04 Revalidation and residual        | ✅ Implemented | Expand outstanding zeros; ignore caller `total_debt`; ignore reason after enum                                                                                                                                |
| ALLOC-05 Source detach residual refuse    | ✅ Implemented | Dropped `_projected_residual` / `_allocation_residual_holds`; residual unchanged on detach                                                                                                                    |
| ALLOC-06 MCP get_collection_allocation    | ✅ Implemented | Get omits `residual_reason`; invoices include `document_kind`                                                                                                                                                 |
| ALLOC-07 Allocation line document_kind    | ✅ Implemented | Parent-arch before `invoice_number` on `<list>`; inherit view deleted                                                                                                                                         |
| VOUCH-01 Voucher allocation membership    | ✅ Implemented | Draft unlink/write allowed without leftover-voucher residual math                                                                                                                                             |
| VOUCH-02 Partner write follows allocation | ✅ Implemented | Same-vals attach; residual 0 / leftover < amount allowed; confirmed refused                                                                                                                                   |
| VOUCH-03 Voucher lifecycle                | ✅ Implemented | Residual-unlink clauses updated; sibling `validated_seller` lifecycle preserved                                                                                                                               |

### Coherence (Design)

| Decision                                                               | Followed? | Notes                                                                  |
| ---------------------------------------------------------------------- | --------- | ---------------------------------------------------------------------- |
| Shared `_prepare_customer_debt_lines`; MCP expand in revalidate        | ✅ Yes    | Form/create helper; MCP stays in `_collection_allocation_revalidate`   |
| Read `collection_connector_id`; never `_collection_active_connector()` | ✅ Yes    | Empty lines on missing connector/binding/ERP UserError                 |
| Snapshot iff `"line_ids" not in vals`                                  | ✅ Yes    |                                                                        |
| Get adds `document_kind`; drop get `residual_reason`                   | ✅ Yes    |                                                                        |
| Stop residual ± voucher.amount                                         | ✅ Yes    | Helpers deleted                                                        |
| Report payload `residual_reason: ""`                                   | ✅ Yes    | XLSX/PDF copy left unchanged as designed                               |
| Manifest `19.0.1.32.0` + DROP `residual_reason`                        | ✅ Yes    | Keep sibling `19.0.1.31.0`                                             |
| CHECK `amount_applied >= 0`; drop `<= invoice_balance`                 | ✅ Yes    | Name kept `_amount_applied_positive` (apply deviation; spec still met) |

### TDD Compliance

| Check                         | Result | Details                                                                                                                                                                  |
| ----------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| TDD Evidence reported         | ✅     | TDD Cycle Evidence table present in apply-progress for tasks 1.1–4.5                                                                                                     |
| All tasks have tests          | ✅     | 18/18 tasks name test files or reuse focused classes (refactor gates 1.5/2.4/3.4/4.5 have no new RED)                                                                    |
| RED confirmed (tests exist)   | ✅     | Named RED files exist under `tests/`; covering methods listed in the matrix ran this session                                                                             |
| GREEN confirmed (tests pass)  | ✅     | Full `/collection` this session: exit 0, `0 failed, 0 error(s) of 636 tests`                                                                                             |
| Triangulation adequate        | ✅     | Multi-case RED on residual, MCP expand, helper/onchange, detach; ➖ Single for migrate version (1.2) is appropriate                                                      |
| Safety Net for modified files | ⚠️     | Tasks 4.3 and 4.4 recorded Safety Net as N/A while modifying existing test files (`test_collection_sheet_report_data.py`, `test_collection_allocation_document_kind.py`) |

**TDD Compliance**: 5/6 checks passed (Safety Net warning on two modified files)

---

### Test Layer Distribution

| Layer       | Tests   | Files                | Tools                                                                                      |
| ----------- | ------- | -------------------- | ------------------------------------------------------------------------------------------ |
| Unit        | 0       | 0                    | Odoo TransactionCase available in config; this change did not add isolated pure-unit files |
| Integration | 636     | 16 `tests/test_*.py` | Containerized Odoo + PostgreSQL (`docker compose run --rm`, `-u collection`)               |
| E2E         | 0       | 0                    | not installed (config `e2e.available: false`)                                              |
| **Total**   | **636** | **16**               |                                                                                            |

Changed-file related methods (apply-progress test files): 270 across 9 files, all
Integration (TransactionCase). Spec scenarios are covered at the integration layer. E2E
not available — no SUGGESTION to add browser tests.

---

### Changed File Coverage

Coverage analysis skipped — no coverage tool detected

---

### Assertion Quality

| File                          | Line | Assertion                                                              | Issue                                                                                                                               | Severity |
| ----------------------------- | ---- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | -------- |
| `tests/test_collection_ui.py` | 1423 | `self.assertIn("oe_stat_button", (button.get("class") or "").split())` | CSS class / implementation-detail assertion on the Vouchers smart button (behavior also asserted via `action_open_vouchers` domain) | WARNING  |

**Assertion quality**: 0 CRITICAL, 1 WARNING

No tautologies, ghost loops, or production-code-free tests found in change-related
files. Report `residual_reason` tests combine payload value asserts with source inspect
of `_collection_report_customers` (required by MUST NOT read the dropped field).

---

### Quality Metrics

**Linter**: ⚠️ 1 optional warning (`pylint_odoo` C8101 `manifest-required-author` on
existing Seedian author in `__manifest__.py`). Mandatory hooks passed. Command:
`pre-commit run --files` on changed collection paths; exit 0. **Type Checker**: ➖ Not
available

### Issues Found

**CRITICAL**: None

**WARNING**:

1. Apply-progress Safety Net is N/A for tasks 4.3 and 4.4 even though existing test
   files were modified (Strict TDD protocol gap; tests still passed this session).
2. `test_allocation_form_stat_button_opens_vouchers` asserts CSS class `oe_stat_button`
   (implementation coupling). Domain/`action_open_vouchers` coverage still holds.

**SUGGESTION**:

1. Add an explicit migrate/ORM test that an allocation created with supplied `line_ids`
   keeps those lines after a 1.32.0 upgrade (no-backfill is today covered by
   create-supplied + migrate source inspect).
2. Optional C8101 Seedian-author warning is pre-existing; ignore unless the project
   switches to the Eynes author token.

Sibling `voucher-states-ui` verify failures (if any on that change) are out of scope and
were not treated as defects of this change. This `/collection` run passed including
preserved voucher-state tests.

### Verdict

PASS WITH WARNINGS All 10 requirements and 47 scenarios have covering tests that passed
this session; suite exit 0. Warnings are TDD safety-net protocol and one CSS-class
assertion, not missing or failing spec coverage.
