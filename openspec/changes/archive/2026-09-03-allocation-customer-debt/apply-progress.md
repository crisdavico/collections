# Apply Progress: allocation-customer-debt

**Mode**: Strict TDD
**Work unit**: 1 (Phase 1) + 2 (Phase 2 MCP) + 3 (Phase 3 UI / form) + 4 (Phase 4 detach / report / docs) — stacked-to-main; no PRs
**Batch status**: Phase 1 complete (1.1–1.5). Phase 2 complete (2.1–2.4). Phase 3 complete (3.1–3.4). Phase 4 complete (4.1–4.5).

## Completed Tasks

- [x] 1.1 RED residual = debt−applied; negative saves; zero applied; no `residual_reason`
- [x] 1.2 RED manifest `19.0.1.32.0`; migrate DROP `residual_reason`; keep 1.31.0
- [x] 1.3 GREEN allocation totals/residual compute; line default 0 + CHECK `>= 0`; revision drops reason
- [x] 1.4 GREEN manifest + migrate; strip ORM `residual_reason` writes; drop persist keys
- [x] 1.5 REFACTOR: `invoke install -m collection`; focused allocation + company_migration; scoped pre-commit
- [x] 2.1 RED `tests/test_collection_mcp_allocation.py`: I1+I2 zeros; empty `invoices[]` expands; ignore reason; hash reason-only no-op; parse `>= 0`
- [x] 2.2 RED `tests/test_collection_mcp_allocation_lookup.py`: omit reason; invoices include `document_kind`
- [x] 2.3 GREEN `tools/collection_allocation.py`: parse `>= 0`; expand in revalidate; ignore reason after enum; drop hash reason, `_collection_allocation_check_residual`, amend placeholder. `tools/allocation_lookup.py`: add `document_kind`
- [x] 2.4 REFACTOR: `invoke install -m collection`; MCP classes; update-mode `-u`; scoped pre-commit
- [x] 3.1 RED `tests/test_collection_allocation.py`: helper; onchange replaces lines unless confirmed; missing connector/binding → empty, no UserError; snapshot iff `"line_ids"` omitted
- [x] 3.2 RED `tests/test_collection_ui.py`: many2many `no_create`/`no_create_edit` + `document_type`; Customer Debt; helpers; no Residual Reason; smart button domain `allocation_id`
- [x] 3.3 GREEN `models/collection_allocation.py`: helper via `collection_connector_id`+binding (never `_collection_active_connector()`); onchange; create-if-omitted; `voucher_count` + `action_open_vouchers`. Match `views/collection_allocation_views.xml`
- [x] 3.4 REFACTOR: `invoke install -m collection`; allocation/ui tests; update-mode `-u`; scoped pre-commit
- [x] 4.1 RED `tests/test_collection_voucher.py`: draft detach/unlink/partner-write at residual 0 and leftover < amount succeed; residual unchanged; confirmed refused
- [x] 4.2 GREEN `models/collection_voucher.py`: stop residual ± voucher amount; drop `_projected_residual` / `_allocation_residual_holds`
- [x] 4.3 RED/GREEN `tests/test_collection_sheet_report_data.py`: payload `residual_reason` `""`; source does not read `_fields["residual_reason"]`. Production already emitted `""` from Phase 1. Leave XLSX/PDF copy
- [x] 4.4 RED/GREEN parent-arch `document_kind` before `invoice_number`; get returns kind; delete inherit view; drop from manifest; `AGENTS.md` 1.32.0 on top of sibling `validated_seller`
- [x] 4.5 REFACTOR: `invoke install -m collection`; full `/collection` update-mode; scoped + glob pre-commit

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_collection_allocation.py` | Integration (Odoo TransactionCase) | ✅ 0 failed, 0 error(s) of 43 (`TestCollectionAllocation` + `TestCollectionCompanyMigration`) | ✅ Written then ran: exit 1, `2 failed, 4 error(s) of 6 tests` | ✅ After models: 7 focused tests exit 0 | ✅ residual 110, negative residual, zero applied persist, omitted default 0, negative applied IntegrityError, invoice/quotation split | ✅ Constraint name kept `_amount_applied_positive`; stale PG CHECKs dropped in migrate |
| 1.2 | `tests/test_collection_company_migration.py` | Integration | ✅ same 43-test net | ✅ Written (included in the 6-test RED run; manifest still 1.31.0) | ✅ `test_manifest_version_is_1_32_0` exit 0 | ➖ Single version/migrate scenario | ✅ keep `migrations/19.0.1.31.0/` |
| 1.3 | `tests/test_collection_allocation.py` | Integration | ✅ same | ✅ tests existed first | ✅ Passed with compute + CHECK `>= 0` | ✅ covered by 1.1 cases | ✅ dropped `_amount_applied_lte_balance` so residual can go negative |
| 1.4 | `tests/test_collection_*.py` + migrate | Integration | ✅ same | ✅ 1.2 RED required 1.32.0 migrate file | ✅ manifest `19.0.1.32.0`; persist keys dropped | ➖ migrate DROP only | ✅ surgical view/voucher/report/lookup so field drop does not break `-u` |
| 1.5 | same two classes | Integration | N/A (refactor gate) | ➖ no new RED | ✅ focused classes exit 0, `0 failed, 0 error(s) of 45 tests` | ➖ | ✅ install + pre-commit |
| 2.1 | `tests/test_collection_mcp_allocation.py` | Integration (Odoo TransactionCase) | ✅ 5 failed, 1 error(s) of 50 (Phase 1 leftover residual/expand/reason) | ✅ Written then ran: exit 1, `7 failed, 5 error(s) of 13 tests` | ✅ same 13 tests exit 0 | ✅ I1+I2 zeros, empty expand, ignore reason, hash no-op, parse 0 vs negative, stale zero-applied ignored, applied above voucher SUM | ✅ E501 wrap; hash computed once |
| 2.2 | `tests/test_collection_mcp_allocation_lookup.py` | Integration | ✅ same 50-test net (residual 50/80 leftover) | ✅ Written (included in 13-test RED: missing `document_kind`) | ✅ lookup tests exit 0 | ✅ default `invoice` + stored `quotation` | ➖ None needed |
| 2.3 | `tools/collection_allocation.py`, `tools/allocation_lookup.py` | Integration | ✅ same | ✅ tests existed first | ✅ 13 focused then 54 class tests exit 0 | ✅ covered by 2.1/2.2 | ✅ drop check_residual / amend placeholders; single hash |
| 2.4 | same two MCP classes | Integration | N/A (refactor gate) | ➖ no new RED | ✅ after install: `0 failed, 0 error(s) of 54 tests` | ➖ | ✅ install retry after sibling SerializationFailure; scoped pre-commit exit 0 |
| 3.1 | `tests/test_collection_allocation.py` | Integration (Odoo TransactionCase) | ✅ 0 failed, 0 error(s) of 92 tests (`TestCollectionAllocation` + `TestCollectionUi`) | ✅ Written then ran: exit 1, `4 failed, 11 error(s) of 16 tests` | ✅ same 16 tests exit 0 | ✅ ERP snapshot zeros; empty connector; empty binding; ERP UserError swallowed; never `_collection_active_connector`; draft replace; confirmed skip; unbound clear; omitted create snapshots; supplied skips fetch; voucher_count 0/1/2; smart-button domain; NewId refuse | ➖ mapping extracted in 3.4 |
| 3.2 | `tests/test_collection_ui.py` | Integration | ✅ same 92-test net; sibling stages-kanban / list,form / menu-10 left intact | ✅ Written (included in 16-test RED: no many2many, Invoices page, no button box) | ✅ 3 UI tests exit 0 | ✅ many2many `no_create`/`no_create_edit`+`document_type`; Customer Debt + six `help=`; no Residual Reason; stat button `allocation_id` via 3.1 | ➖ moved `_parse_view_options` with other helpers |
| 3.3 | `models/collection_allocation.py`, `views/collection_allocation_views.xml` | Integration | ✅ same | ✅ tests existed first | ✅ 16 focused then 108 class tests exit 0 | ✅ covered by 3.1/3.2 | ✅ `_customer_debt_line_vals`; shared sheet browse in create |
| 3.4 | same two classes | Integration | N/A (refactor gate) | ➖ no new RED | ✅ after install: `0 failed, 0 error(s) of 108 tests` | ➖ | ✅ `invoke install -m collection` exit 0 (no SerializationFailure); scoped pre-commit exit 0 after E501 wraps |
| 4.1 | `tests/test_collection_voucher.py` (+ allocation detach twins) | Integration (Odoo TransactionCase) | ✅ 1 failed, 0 error(s) of 8 — leftover `test_partner_write_left_unallocated_posts_chatter` (reason branch already gone); refuse tests still passed | ✅ Written then ran: exit 1, `0 failed, 7 error(s) of 10 tests` | ✅ After voucher helpers: 10 focused tests exit 0 | ✅ residual 0 unlink, leftover < amount unlink, residual 0 partner-write, leftover partner-write, allocation_id residual 0, confirmed refuse, unallocated without unique draft | ➖ helpers deleted rather than emptied |
| 4.2 | `models/collection_voucher.py` | Integration | ✅ same | ✅ tests existed first | ✅ 10 focused tests exit 0 | ✅ covered by 4.1 cases | ✅ dropped `_projected_residual` and `_allocation_residual_holds` |
| 4.3 | `tests/test_collection_sheet_report_data.py` | Integration | N/A (payload already `""` from Phase 1) | ✅ Written first this batch | ✅ first run exit 0, `0 failed, 0 error(s) of 3 tests` (GREEN already present) | ✅ one customer `""` + two customers both `""`; source inspect no `_fields["residual_reason"]` | ➖ no production change |
| 4.4 | `tests/test_collection_allocation_document_kind.py` | Integration | N/A (new asserts) | ✅ Written then ran: exit 1, `1 failed, 0 error(s) of 2 tests` (inherit file still present) | ✅ after parent-arch + delete inherit: `0 failed, 0 error(s) of 6 tests` | ✅ parent-arch order + get `quotation` kind | ➖ E501 wraps |
| 4.5 | full `/collection` | Integration | N/A (refactor gate) | ➖ no new RED | ✅ `0 failed, 0 error(s) of 636 tests` | ➖ | ✅ install + glob pre-commit |

### Test Summary

- **Total tests written (Phase 1)**: 7 new allocation/migrate cases (plus fixture debt-line adjustments so leftover-voucher residual still matches until Phase 4)
- **Total tests written (Phase 2)**: 6 new MCP cases (`test_applied_only_payload_expands_outstanding_zeros`, `test_residual_reason_ignored_after_enum`, `test_applied_above_voucher_total_still_persists`, `test_parse_amount_applied_allows_zero_rejects_negative`, `test_zero_applied_missing_from_erp_is_ignored`, `test_get_invoices_include_stored_document_kind`) plus rewritten empty-invoices / reason-hash / lookup payload cases
- **Total tests written (Phase 3)**: 13 allocation cases (helper/onchange/create-if-omitted/`voucher_count`/`action_open_vouchers`) plus 3 UI cases (many2many, Customer Debt helpers, stat button). `test_create_supplied_line_ids_skips_snapshot` already passed in RED (supplied `line_ids` already persisted)
- **Total tests written (Phase 4)**: rewrite unlink/partner-write residual-0 and leftover-less-than-amount to succeed (voucher + allocation twins); unallocated chatter without unique draft; report `residual_reason` `""` (2 cases); parent-arch `document_kind` + get kind
- **Total tests passing (Phase 1 focused)**: 45 (`TestCollectionAllocation` + `TestCollectionCompanyMigration`)
- **Total tests passing (Phase 2 focused)**: 54 (`TestCollectionMcpAllocation` + `TestCollectionMcpAllocationLookup`)
- **Total tests passing (Phase 3 focused)**: 108 (`TestCollectionAllocation` + `TestCollectionUi`)
- **Total tests passing (Phase 4 focused / full)**: 10 detach + 3 report + 6 document_kind; full `/collection` **636**
- **Layers used**: Unit (0), Integration (45 Phase 1 + 54 Phase 2 + 108 Phase 3 + 636 Phase 4 full), E2E (0)
- **Approval tests** (refactoring): Phase 1 43-test net; Phase 2 converted leftover MCP residual/reason asserts to new behavior; Phase 3 92-test net before new RED; Phase 4 8-test detach net (1 leftover unallocated fail)
- **Pure functions created**: 1 (`_customer_debt_line_vals` maps one ERP invoice dict). Phase 4 deleted `_projected_residual` / `_allocation_residual_holds`

### Phase 1 RED command (exit 1)

```bash
cd /home/crisd/projects/seedian/seedian
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionAllocation.test_residual_is_debt_minus_applied,/collection:TestCollectionAllocation.test_residual_negative_saves_on_draft_and_confirmed,/collection:TestCollectionAllocation.test_zero_applied_line_persists,/collection:TestCollectionAllocation.test_negative_amount_applied_rejected,/collection:TestCollectionAllocation.test_totals_split_invoices_and_quotations,/collection:TestCollectionCompanyMigration.test_manifest_version_is_1_32_0
```

Result: **exit 1** — `2 failed, 4 error(s) of 6 tests` (reason constraint, old CHECKs, `total_debt` not computed, manifest still 1.31.0).

### Phase 1 GREEN / work-unit focused command (exit 0)

```bash
cd /home/crisd/projects/seedian/seedian
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionAllocation,/collection:TestCollectionCompanyMigration
```

| Run | Exit | Result |
|-----|------|--------|
| Safety net (before edits) | 0 | `0 failed, 0 error(s) of 43 tests` |
| First GREEN of 7 new tests (stale PG CHECKs after Constraint rename) | 1 | IntegrityError on leftover `amount_applied_lte_balance` / `amount_applied_positive > 0` |
| GREEN after keeping `_amount_applied_positive` + migrate DROP leftovers | 0 | `0 failed, 0 error(s) of 7 tests` |
| Full two classes after fixture debt lines | 0 | `0 failed, 0 error(s) of 45 tests` |
| After `invoke install -m collection` | 1 | `1 failed, 0 error(s) of 45` — `test_migrate_binds_null_sequences_to_main_and_copies_others` `30544 != 30543` (sequence off-by-one; unrelated to residual) |
| Isolated sequence + 1.32.0 | 0 | `0 failed, 0 error(s) of 2 tests` |
| Clean rerun of two classes (1.5 gate) | 0 | `0 failed, 0 error(s) of 45 tests` |

Full `invoke test -m collection --mode=update` was **not** used as the Phase 1 work-unit gate: MCP/voucher/lookup/report still assume old residual or `residual_reason` until Phases 2–4.

### Phase 2 RED command (exit 1)

```bash
cd /home/crisd/projects/seedian/seedian
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionMcpAllocation.test_discovered_as_method_write_mcp,/collection:TestCollectionMcpAllocation.test_first_create_draft_revision_one_totals,/collection:TestCollectionMcpAllocation.test_empty_invoices_on_account,/collection:TestCollectionMcpAllocation.test_applied_only_payload_expands_outstanding_zeros,/collection:TestCollectionMcpAllocation.test_residual_reason_ignored_after_enum,/collection:TestCollectionMcpAllocation.test_applied_above_voucher_total_still_persists,/collection:TestCollectionMcpAllocation.test_reason_only_retry_is_hash_noop,/collection:TestCollectionMcpAllocation.test_parse_amount_applied_allows_zero_rejects_negative,/collection:TestCollectionMcpAllocation.test_zero_applied_missing_from_erp_is_ignored,/collection:TestCollectionMcpAllocation.test_ignores_caller_total_debt_stores_fresh_summary,/collection:TestCollectionMcpAllocationLookup.test_found_payload_omits_reason_includes_document_kind,/collection:TestCollectionMcpAllocationLookup.test_get_invoices_include_stored_document_kind,/collection:TestCollectionMcpAllocationLookup.test_on_account_empty_invoices_still_present_as_list
```

Result: **exit 1** — `7 failed, 5 error(s) of 13 tests` (`exclusiveMinimum`, no expand, residual check still on, hash includes reason, parse rejects 0, lookup missing `document_kind`).

### Phase 2 GREEN / work-unit focused command (exit 0)

```bash
cd /home/crisd/projects/seedian/seedian
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionMcpAllocation,/collection:TestCollectionMcpAllocationLookup
```

| Run | Exit | Result |
|-----|------|--------|
| Safety net (before Phase 2 test edits) | 1 | `5 failed, 1 error(s) of 50 tests` — leftover Phase 1 residual/expand/reason |
| RED 13 focused tests | 1 | `7 failed, 5 error(s) of 13 tests` |
| GREEN 13 focused tests | 0 | `0 failed, 0 error(s) of 13 tests` |
| GREEN both MCP classes | 0 | `0 failed, 0 error(s) of 54 tests` |
| After hash refactor + `invoke install` | 0 | `0 failed, 0 error(s) of 54 tests` |

Full `invoke test -m collection --mode=update` was **not** used as the Phase 2 work-unit gate: UI/detach/report still belong to Phases 3–4.

### Phase 3 RED command (exit 1)

```bash
cd /home/crisd/projects/seedian/seedian
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionAllocation.test_prepare_customer_debt_lines_snapshots_outstanding_zeros,/collection:TestCollectionAllocation.test_prepare_customer_debt_lines_empty_without_connector,/collection:TestCollectionAllocation.test_prepare_customer_debt_lines_empty_without_binding,/collection:TestCollectionAllocation.test_prepare_customer_debt_lines_swallows_erp_usererror,/collection:TestCollectionAllocation.test_prepare_customer_debt_lines_never_calls_active_connector,/collection:TestCollectionAllocation.test_onchange_replaces_lines_on_draft,/collection:TestCollectionAllocation.test_onchange_skips_when_confirmed,/collection:TestCollectionAllocation.test_onchange_empty_when_unbound_partner,/collection:TestCollectionAllocation.test_create_omitted_line_ids_snapshots,/collection:TestCollectionAllocation.test_create_supplied_line_ids_skips_snapshot,/collection:TestCollectionAllocation.test_voucher_count_matches_linked_vouchers,/collection:TestCollectionAllocation.test_action_open_vouchers_domain_is_allocation_id,/collection:TestCollectionAllocation.test_action_open_vouchers_refused_on_new_id,/collection:TestCollectionUi.test_allocation_form_vouchers_existing_only_many2many,/collection:TestCollectionUi.test_allocation_form_customer_debt_helpers_no_residual_reason,/collection:TestCollectionUi.test_allocation_form_stat_button_opens_vouchers
```

Result: **exit 1** — `4 failed, 11 error(s) of 16 tests` (missing helper/onchange/`action_open_vouchers`/`voucher_count`; form still Invoices / no many2many / no button box). `test_create_supplied_line_ids_skips_snapshot` already passed (supplied lines already persist).

### Phase 3 GREEN / work-unit focused command (exit 0)

```bash
cd /home/crisd/projects/seedian/seedian
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionAllocation,/collection:TestCollectionUi
```

| Run | Exit | Result |
|-----|------|--------|
| Safety net (before Phase 3 test edits) | 0 | `0 failed, 0 error(s) of 92 tests` |
| RED 16 focused tests | 1 | `4 failed, 11 error(s) of 16 tests` |
| GREEN 16 focused tests | 0 | `0 failed, 0 error(s) of 16 tests` |
| GREEN both classes | 0 | `0 failed, 0 error(s) of 108 tests` |
| After install + refactor | 0 | `0 failed, 0 error(s) of 108 tests` |

Full `invoke test -m collection --mode=update` was **not** used as the Phase 3 work-unit gate: detach/report/parent-arch still belong to Phase 4. Update-mode equivalent is `-u collection` with those two classes.

### Phase 4 RED command (exit 1)

```bash
cd /home/crisd/projects/seedian/seedian
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionVoucher.test_unlink_draft_on_draft_at_residual_zero_succeeds,/collection:TestCollectionVoucher.test_unlink_draft_on_draft_leftover_less_than_amount_succeeds,/collection:TestCollectionVoucher.test_partner_write_fully_applied_source_succeeds,/collection:TestCollectionVoucher.test_partner_write_leftover_less_than_amount_succeeds,/collection:TestCollectionVoucher.test_partner_write_left_unallocated_posts_chatter,/collection:TestCollectionVoucher.test_allocation_id_write_on_draft_or_unset,/collection:TestCollectionVoucher.test_unlink_draft_on_confirmed_refused,/collection:TestCollectionAllocation.test_pending_unlink_on_draft_at_residual_zero_succeeds,/collection:TestCollectionAllocation.test_fully_applied_source_detach_via_partner_write_succeeds,/collection:TestCollectionAllocation.test_leftover_less_than_amount_detach_succeeds
```

Result: **exit 1** — `0 failed, 7 error(s) of 10 tests` (leftover-voucher residual projection still refused unlink/partner-write). Unallocated chatter and confirmed refuse already passed.

Parent-arch RED:

```bash
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionAllocationDocumentKind.test_parent_arch_document_kind_before_invoice_number,/collection:TestCollectionAllocationDocumentKind.test_get_invoices_include_document_kind
```

Result: **exit 1** — `1 failed, 0 error(s) of 2 tests` (`collection_sheet_report_views.xml` still present). Get kind already passed (Phase 2).

### Phase 4 GREEN / work-unit focused command (exit 0)

```bash
cd /home/crisd/projects/seedian/seedian
docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection
```

| Run | Exit | Result |
|-----|------|--------|
| Safety net (8 detach tests before rewrite) | 1 | `1 failed, 0 error(s) of 8 tests` — unallocated chatter leftover |
| RED 10 detach tests | 1 | `0 failed, 7 error(s) of 10 tests` |
| GREEN 10 detach tests | 0 | `0 failed, 0 error(s) of 10 tests` |
| Report residual_reason tests | 0 | `0 failed, 0 error(s) of 3 tests` (GREEN already from Phase 1) |
| RED parent-arch | 1 | `1 failed, 0 error(s) of 2 tests` |
| GREEN document_kind class | 0 | `0 failed, 0 error(s) of 6 tests` |
| Full `/collection` after install | 0 | `0 failed, 0 error(s) of 636 tests` |

## Work Unit Evidence

### Phase 1

| Evidence | Value |
|----------|--------|
| Focused test command and exact result | `docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionAllocation,/collection:TestCollectionCompanyMigration` → **exit 0**, `0 failed, 0 error(s) of 45 tests` (clean 1.5 rerun). Equivalent intent: `invoke test -m collection --mode=update` scoped to those two classes. |
| Runtime harness command/scenario and exact result | From `/home/crisd/projects/seedian/seedian`: `invoke install -m collection` → **exit 0** (`addons init -w collection`; stopped `seedian-odoo-1`). Then focused tests as above. Scoped `pre-commit run --files` on touched collection files → **exit 0** (optional pylint C8101 `manifest-required-author` on existing Seedian author; mandatory hooks passed). |
| Rollback boundary | `models/collection_allocation.py` compute/constraints; `models/collection_allocation_line.py`; `models/collection_allocation_revision.py`; `__manifest__.py` version `19.0.1.32.0`; `migrations/19.0.1.32.0/`. Do **not** revert sibling `migrations/19.0.1.31.0/`, voucher-state, or `validated_seller` work. |

### Phase 2

| Evidence | Value |
|----------|--------|
| Focused test command and exact result | `docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionMcpAllocation,/collection:TestCollectionMcpAllocationLookup` → **exit 0**, `0 failed, 0 error(s) of 54 tests` (after install/refactor). Update-mode equivalent: `-u collection` with those two classes. |
| Runtime harness command/scenario and exact result | From `/home/crisd/projects/seedian/seedian`: first `invoke install -m collection` → **exit 1** (`SerializationFailure: could not serialize access due to concurrent update` while sibling `voucher-states-ui` upgraded). Retry `invoke install -m collection` → **exit 0**. Then focused MCP tests **exit 0**. Scoped `pre-commit run --files` on the four Phase 2 Python files → **exit 0** (after E501 wrap). |
| Rollback boundary | `tools/collection_allocation.py`; `tools/allocation_lookup.py`; `tests/test_collection_mcp_allocation.py`; `tests/test_collection_mcp_allocation_lookup.py`. Do **not** revert sibling `validated_seller` / 1.31.0 / document-review JS / views. Keep 1.32.0 migrate from Phase 1. |

### Phase 3

| Evidence | Value |
|----------|--------|
| Focused test command and exact result | `docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionAllocation,/collection:TestCollectionUi` → **exit 0**, `0 failed, 0 error(s) of 108 tests` (after install/refactor). Update-mode equivalent: `-u collection` with those two classes. |
| Runtime harness command/scenario and exact result | From `/home/crisd/projects/seedian/seedian`: `invoke install -m collection` → **exit 0** (no SerializationFailure this batch). Then focused allocation+UI tests **exit 0**. Scoped `pre-commit run --files` on the four Phase 3 Python/XML files → **exit 0** (after E501 wraps). |
| Rollback boundary | `models/collection_allocation.py` helper/onchange/create-if-omitted/`voucher_count`/`action_open_vouchers`; `views/collection_allocation_views.xml`; `tests/test_collection_allocation.py`; `tests/test_collection_ui.py` (additive asserts only). Do **not** revert sibling voucher UI / stages-kanban / menu-10 / `views/collection_views.xml` / document-review / 1.31.0. Keep inherit `views/collection_sheet_report_views.xml` until Phase 4. |

### Phase 4

| Evidence | Value |
|----------|--------|
| Focused test command and exact result | `docker compose run --rm -e "DB_FILTER=^devel$" odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection` → **exit 0**, `0 failed, 0 error(s) of 636 tests`. Update-mode equivalent: `invoke test -m collection --mode=update`. |
| Runtime harness command/scenario and exact result | From `/home/crisd/projects/seedian/seedian`: `invoke install -m collection` → **exit 0** (stopped `seedian-odoo-1`; no SerializationFailure). Scoped `pre-commit run --files` → **exit 0** after E501 wraps (optional pylint C8101 `manifest-required-author`). Glob `pre-commit run --files odoo/custom/src/private/collection/**` → **exit 0**. |
| Rollback boundary | `models/collection_voucher.py` residual helpers; `models/collection_sheet_report.py` (already `""`); `views/collection_allocation_views.xml` parent-arch `document_kind`; deleted `views/collection_sheet_report_views.xml`; `__manifest__.py` data drop; `migrations/19.0.1.32.0/post-migrate.py` inherit-view unlink; `AGENTS.md` 1.32.0 / residual / MCP ignore-reason. Do **not** revert sibling `validated_seller` / 1.31.0 / document-review / stages-kanban. |

## Files Changed (Phase 1 work unit)

| File | Action | What Was Done |
|------|--------|---------------|
| `models/collection_allocation.py` | Modified | Compute `total_debt` / `total_invoices` / `total_quotations` / `residual`; residual = debt − applied; drop `residual_reason` + `_check_residual` |
| `models/collection_allocation_line.py` | Modified | `amount_applied` default `0.0`; CHECK `>= 0` on `_amount_applied_positive`; drop `_amount_applied_lte_balance` |
| `models/collection_allocation_revision.py` | Modified | Drop `residual_reason`; add `total_invoices` / `total_quotations` |
| `models/collection_voucher.py` | Modified | `_allocation_residual_holds` no longer reads `residual_reason` (leftover-voucher residual projection remains until Phase 4) |
| `models/collection_sheet_report.py` | Modified | Stop `_fields["residual_reason"]`; payload key `""` |
| `views/collection_allocation_views.xml` | Modified | Remove `<field name="residual_reason"/>` so `-u` succeeds after field drop (fuller UI is Phase 3) |
| `tools/collection_allocation.py` | Modified | Persist create/amend/revision no longer write `residual_reason` or `total_debt`; hash/schema/check stay Phase 2 |
| `tools/allocation_lookup.py` | Modified | Drop `residual_reason` from get payload (field gone) |
| `__manifest__.py` | Modified | Version `19.0.1.32.0`; keep sibling 1.31.0 migrate |
| `migrations/19.0.1.32.0/post-migrate.py` | Created | DROP `residual_reason` on allocation+revision; DROP leftover line CHECKs |
| `tests/test_collection_allocation.py` | Modified | RED cases; pop `residual_reason`; debt lines so leftover-voucher residuals still match |
| `tests/test_collection_company_migration.py` | Modified | `test_manifest_version_is_1_32_0`; keep 1.31.0 assertions |
| `tests/test_collection_voucher.py` | Modified | Helper pops `residual_reason` only |
| `tests/test_collection_allocation_acl.py` | Modified | Remove reason + `write({"total_debt": ...})` |
| `tests/test_collection_mcp_allocation.py` | Modified | Remove ORM `allocation.residual_reason` asserts; MCP args still pass reason (Phase 2) |
| `tests/test_collection_mcp_allocation_lookup.py` | Modified | Pop reason; drop from `_ALLOC_KEYS` / payload field asserts |
| `openspec/changes/allocation-customer-debt/tasks.md` | Modified | Phase 1 `[x]` |
| `openspec/changes/allocation-customer-debt/apply-progress.md` | Created | This file |

## Files Changed (Phase 2 work unit)

| File | Action | What Was Done |
|------|--------|---------------|
| `tests/test_collection_mcp_allocation.py` | Modified | Expand I1+I2 zeros; empty invoices expand; ignore reason; hash no-op; parse `>= 0`; strip leftover ORM `residual_reason` writes |
| `tests/test_collection_mcp_allocation_lookup.py` | Modified | Omit `residual_reason`; invoice rows include `document_kind` (invoice + quotation) |
| `tools/collection_allocation.py` | Modified | Schema `minimum: 0`; parse `>= 0`; expand in revalidate; ignore reason after enum; drop hash reason, `_collection_allocation_check_residual`, amend placeholders |
| `tools/allocation_lookup.py` | Modified | GET invoices include `document_kind` (default `invoice`) |
| `openspec/changes/allocation-customer-debt/tasks.md` | Modified | Phase 2 `[x]` |
| `openspec/changes/allocation-customer-debt/apply-progress.md` | Modified | Merge Phase 2 TDD + work-unit evidence |

## Files Changed (Phase 3 work unit)

| File | Action | What Was Done |
|------|--------|---------------|
| `tests/test_collection_allocation.py` | Modified | Helper/onchange/empty-connector/create-if-omitted/`voucher_count`/`action_open_vouchers` RED cases |
| `tests/test_collection_ui.py` | Modified | Additive allocation-form asserts: many2many `no_create`/`no_create_edit`+`document_type`; Customer Debt; six `help=`; no Residual Reason; Vouchers smart button. Sibling stages-kanban / list,form / menu-10 left intact |
| `models/collection_allocation.py` | Modified | `_prepare_customer_debt_lines` via `collection_connector_id`+binding; onchange skip confirmed; create snapshots iff `line_ids` omitted; `voucher_count` + `action_open_vouchers` domain `allocation_id` |
| `views/collection_allocation_views.xml` | Modified | Button box; many2many vouchers; Customer Debt tab; six totals with help; no Residual Reason. Parent-arch `document_kind` left to Phase 4 inherit |
| `openspec/changes/allocation-customer-debt/tasks.md` | Modified | Phase 3 `[x]` |
| `openspec/changes/allocation-customer-debt/apply-progress.md` | Modified | Merge Phase 3 TDD + work-unit evidence |

## Files Changed (Phase 4 work unit)

| File | Action | What Was Done |
|------|--------|---------------|
| `tests/test_collection_voucher.py` | Modified | Unlink/partner-write at residual 0 and leftover < amount succeed; residual unchanged; unallocated only without unique draft |
| `tests/test_collection_allocation.py` | Modified | Matching detach/unlink twins succeed; residual unchanged |
| `models/collection_voucher.py` | Modified | Stop residual ± voucher amount; drop `_projected_residual` / `_allocation_residual_holds`; attach unique draft without leftover checks |
| `tests/test_collection_sheet_report_data.py` | Modified | Payload `residual_reason` `""`; source does not read `_fields["residual_reason"]` |
| `tests/test_collection_allocation_document_kind.py` | Modified | Parent-arch `document_kind` before `invoice_number`; get returns kind; inherit file gone |
| `views/collection_allocation_views.xml` | Modified | Parent-arch `document_kind` immediately before `invoice_number` |
| `views/collection_sheet_report_views.xml` | Deleted | Inherit moved to parent |
| `__manifest__.py` | Modified | Drop inherit view from `data` |
| `migrations/19.0.1.32.0/post-migrate.py` | Modified | Unlink leftover inherit `document_kind` view + xmlid |
| `AGENTS.md` | Modified | `19.0.1.32.0`, residual = debt−applied, no leftover projection, MCP ignore-reason, parent-arch kind; keep sibling `validated_seller` / 1.31.0 |
| `openspec/changes/allocation-customer-debt/tasks.md` | Modified | Phase 4 `[x]` |
| `openspec/changes/allocation-customer-debt/apply-progress.md` | Modified | Merge Phase 4 TDD + work-unit evidence |

## Deviations from Design

- Kept Constraint **attribute** `_amount_applied_positive` with SQL `CHECK(amount_applied >= 0)` instead of renaming to `_amount_applied_non_negative`. Renaming left stale PostgreSQL CHECKs (`> 0` and `<= invoice_balance`) that failed GREEN until migrate DROP + name restore.
- Dropped SQL CHECK `amount_applied <= invoice_balance` so allocation residual can be negative (spec). MCP still enforces `amount_applied <= available` in revalidate.
- Surgical view / voucher / sheet-report / lookup edits ahead of Phases 3–4 so dropping the ORM field does not break `-u` or `AttributeError`. Leftover-voucher residual projection still exists (Phase 4).
- Phase 2: MCP schema still accepts optional `residual_reason` (enum validated then ignored). Hash no longer includes it. GET `residual_reason` was already dropped in Phase 1; Phase 2 added `document_kind`.
- Hash is still of **payload** applied pairs, not the expanded snapshot (matches design).
- Phase 3: parent-arch `document_kind` is **not** moved yet. Inherit `views/collection_sheet_report_views.xml` still injects it (Phase 4 task 4.4). Adding it to the parent now would duplicate the field. Customer Debt tab, helpers, many2many, and smart button landed in Phase 3 as assigned.
- Phase 4: dropped `_projected_residual` and `_allocation_residual_holds` entirely (reason branch was already gone in Phase 1). Report payload `""` was already in production from Phase 1; 4.3 added tests only. 1.32.0 migrate also unlinks the inherit view xmlid (devel already at 1.32.0 so that SQL did not re-run here; file delete + parent-arch is the live path).

## Issues Found

- After Phase 1 `invoke install -m collection`, one pre-existing sequence test failed once (`number_next_actual` 30544 vs 30543). Isolated re-run and full two-class rerun passed. Treat as install/sequence consumption flake, not residual formula.
- `invoke install` uses `--init collection` on an already-installed module; focused tests used `docker compose run --rm` `-u collection` because `seedian-odoo-1` was stopped.
- Sibling `voucher-states-ui` is APPLYING in the same tree. Shared files were re-read before patches; 1.31.0 migrate and voucher-state tests were kept.
- Phase 2 first `invoke install -m collection` hit `SerializationFailure: could not serialize access due to concurrent update` (sibling upgrade). Retry succeeded (exit 0).
- Phase 3 `invoke install -m collection` succeeded on the first try (**exit 0**); no SerializationFailure this batch.
- Shared `tests/test_collection_ui.py` was re-read before additive allocation-form asserts; sibling stages-kanban / list,form / menu-10 tests were not changed.
- Phase 4 safety net: `test_partner_write_left_unallocated_posts_chatter` already failed because unique draft attach no longer needs `residual_reason`. Rewritten to require no unique draft allocation.
- Phase 4 `invoke install -m collection` stopped `seedian-odoo-1` (invoke wrapper). Full tests used `docker compose run --rm` `-u collection`. No SerializationFailure.
- Auto-review blocked a one-off SQL delete of the leftover inherit view on devel. 1.32.0 migrate includes that DELETE for upgrades from `< 1.32.0`. Full 636 tests still passed.

## Remaining Tasks

- None. All 18 tasks `[x]`.

## Workload / PR Boundary

- Mode: stacked PR slice (`stacked-to-main`)
- Current work unit: 4 — Detach, report `""`, parent-arch kind, docs
- Boundary: starts after Phase 3 form snapshot/many2many/Customer Debt/smart button; ends at voucher detach formula, report payload tests, parent-arch `document_kind`, inherit delete, `AGENTS.md`.
- Estimated review budget impact: Phase 4 only. Do not open PRs in this batch.

## Status

18/18 tasks complete (Phases 1–4 of 4). Ready for verify.

