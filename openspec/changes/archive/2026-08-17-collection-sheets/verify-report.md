```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:4d1ec0bf98360a86f24fc76979fe8dcb2739fff5aafba465f04a5f298376436e
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 8/8
scenarios: 23/23
test_command: invoke test -m collection --mode=update
test_exit_code: 0
test_output_hash: sha256:fee36f41c4f53e4324aafb2b72fa8b656888b63c9ab56921d24c96b356511011
build_command: invoke install -m collection
build_exit_code: 0
build_output_hash: sha256:0053145d281cbeeafafe1dcceb1eeab694ac35c6098a41b03ebcf353a93c7254
```

## Verification Report

**Change**: collection-sheets
**Version**: 19.0.1.10.0
**Mode**: Strict TDD

Independent spec count from change artifacts: `specs/collection-sheets/spec.md` 6 requirements / 12 scenarios; `specs/collection-vouchers/spec.md` 2 requirements (1 ADDED + 1 MODIFIED) / 11 scenarios; combined **8 / 23**. Envelope completed counts are scenarios with a passing covering test at this runtime.

`evidence_revision` is SHA-256 of exact test stdout+stderr concatenated with exact build stdout+stderr (no separator).

`invoke img-build` is the config build command but is disproportionate here: this change is Python/XML/ACL/views/tests inside the collection addon, with no new Doodba apt/pip image dependencies. Substitute build is `invoke install -m collection` (module upgrade on devel), matching apply-progress runtime harness.

CodeGraph: `gentle-ai codegraph init --cwd` on the collection git root failed with exit 127. Structural checks used filesystem read/grep. Engram MCP was unavailable; this report is OpenSpec-only.

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 18 |
| Tasks complete | 18 |
| Tasks incomplete | 0 |

### Build & Tests Execution
**Build**: ✅ Passed (`invoke img-build` skipped; module upgrade substitute)
```text
invoke install -m collection
exit 0
Modules loaded. Registry loaded in 3.472s
```

**Tests**: ✅ 166 passed / ❌ 0 failed / ⚠️ 0 skipped. Official command exit 0.
```text
invoke test -m collection --mode=update
exit 0
0 failed, 0 error(s) of 166 tests when loading database 'devel'
```

Odoo stats also printed `collection: 188 tests`; the authoritative result line is **166**. Suite count is 166 rather than apply-progress 164 because the working tree still has unstaged settings-menu WIP (`tests/test_collection_ui.py`, `views/res_config_settings_views.xml`). Flag-off isolation edits in `tests/test_collection_document_review_flag.py` and `test_load_menus_omits_document_review_when_flag_off` are uncommitted and were left in place. All collection-sheets covering tests started this run; none failed.

**Coverage**: ➖ Not available (config `coverage.available: false`)

### Spec Compliance Matrix
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Sheet sequence identity | Sequence assigned on create | `tests/test_collection_sheet.py` > `test_sequence_assigned_on_create` / `test_sequence_names_are_unique` | ✅ COMPLIANT |
| Sheet seller and same-seller invariant | Seller required and frozen | `tests/test_collection_sheet.py` > `test_create_without_seller_is_rejected` / `test_seller_is_not_copied_from_create_uid` / `test_post_create_seller_write_is_rejected` / `test_post_create_same_seller_write_is_rejected` | ✅ COMPLIANT |
| Sheet seller and same-seller invariant | Mixed or null seller rejected | `tests/test_collection_sheet.py` > `test_mixed_or_null_seller_assign_rejected`; `tests/test_collection_voucher.py` > `test_assigned_without_seller_fails` | ✅ COMPLIANT |
| Membership, dates, and deletion | Assign and reassign | `tests/test_collection_sheet.py` > `test_reassign_moves_voucher_to_sheet_b_only` | ✅ COMPLIANT |
| Membership, dates, and deletion | Empty sheet | `tests/test_collection_sheet.py` > `test_empty_sheet_dates_false_and_no_received_date` | ✅ COMPLIANT |
| Membership, dates, and deletion | Dates from member create_date | `tests/test_collection_sheet.py` > `test_dates_from_utc_member_create_date` | ✅ COMPLIANT |
| Membership, dates, and deletion | Unlink unassigns | `tests/test_collection_sheet.py` > `test_unlink_sheet_unassigns_vouchers` / `test_delete_command_unassigns_without_destroying_voucher` | ✅ COMPLIANT |
| Create sheet Action | Unassigned same-seller any state | `tests/test_collection_sheet.py` > `test_action_creates_sheet_for_unassigned_same_seller_any_state` | ✅ COMPLIANT |
| Create sheet Action | Ineligible selection rejected | `tests/test_collection_sheet.py` > `test_action_rejects_ineligible_selection` / `test_action_rejects_null_seller_selection` / `test_create_sheet_action_is_list_bound_server_action` | ✅ COMPLIANT |
| Authorization for internal users | Internal user CRUD | `tests/test_collection_acl.py` > `test_internal_user_sheet_crud_allowed` / `test_sheet_acl_internal_group_only` | ✅ COMPLIANT |
| Authorization for internal users | Non-internal user denied | `tests/test_collection_acl.py` > `test_portal_user_sheet_crud_denied` | ✅ COMPLIANT |
| Collection Sheets UI | Menu and form behaviors | `tests/test_collection_ui.py` > `test_collection_sheets_menu_list_form_search` / `test_collection_sheets_form_without_statusbar` | ✅ COMPLIANT |
| Voucher seller field | Legacy null remains valid | `tests/test_collection_voucher.py` > `test_orm_write_does_not_backfill_null_seller` | ✅ COMPLIANT |
| Voucher seller field | ORM create without seller | `tests/test_collection_voucher.py` > `test_orm_create_without_seller_stays_null` | ✅ COMPLIANT |
| Voucher seller field | Form create requires seller | `tests/test_collection_ui.py` > `test_form_seller_id_is_required` | ✅ COMPLIANT |
| Voucher seller field | Seller visible on list form search | `tests/test_collection_ui.py` > `test_list_form_search_expose_seller_id` | ✅ COMPLIANT |
| MCP tool create_collection_vouchers | All-new create | `tests/test_collection_mcp_tool.py` > `test_all_new_create_stamps_seller_id` / `test_all_new_create_returns_vouchers_in_payment_order` / `test_tool_discovered_with_write_registry_and_schema` | ✅ COMPLIANT |
| MCP tool create_collection_vouchers | Exact-retry returns all vouchers | `tests/test_collection_mcp_tool.py` > `test_exact_retry_does_not_mutate_null_seller` / `test_exact_retry_does_not_replace_existing_seller` / `test_exact_retry_returns_all_vouchers_ignores_customer` plus attachment replay tests | ✅ COMPLIANT |
| MCP tool create_collection_vouchers | Duplicate document_id in call | `tests/test_collection_mcp_tool.py` > `test_in_call_duplicate_document_id_rejects_no_writes` | ✅ COMPLIANT |
| MCP tool create_collection_vouchers | Partial-conflict | `tests/test_collection_mcp_tool.py` > `test_partial_conflict_rejects_no_writes` | ✅ COMPLIANT |
| MCP tool create_collection_vouchers | Existing document_ids on different vouchers succeed | `tests/test_collection_mcp_tool.py` > `test_existing_document_ids_on_different_vouchers_succeed` | ✅ COMPLIANT |
| MCP tool create_collection_vouchers | ACL denial for non-permitted user | `tests/test_collection_mcp_tool.py` > `test_portal_user_denied_no_writes` / `test_create_collection_vouchers_does_not_use_sudo` | ✅ COMPLIANT |
| MCP tool create_collection_vouchers | Missing or invalid seller_id rejected | `tests/test_collection_mcp_tool.py` > `test_missing_seller_id_rejects_no_writes` / `test_portal_seller_id_rejects_no_writes` / `test_unknown_seller_id_rejects_no_writes` | ✅ COMPLIANT |

**Compliance summary**: 23/23 scenarios compliant

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| Sheet sequence identity | ✅ Implemented | `collection.sheet` sequence `CS/%(year)s/` pad 4; no `state` |
| Sheet seller and same-seller invariant | ✅ Implemented | Required frozen `seller_id`; write block; constrains + CHECK assigned⇒seller |
| Membership, dates, and deletion | ✅ Implemented | M2O `sheet_id` `ondelete="set null"`; UTC stored dates; DELETE→UNLINK |
| Create sheet Action | ✅ Implemented | List-bound `ir.actions.server`; Python gate; no wizard |
| Authorization for internal users | ✅ Implemented | One `base.group_user` CRUD row; no `ir.rule` |
| Collection Sheets UI | ✅ Implemented | Menu/list/form/search; `widget="many2many"`; no statusbar |
| Voucher seller field | ✅ Implemented | ORM `required=False`; form `required="1"`; domain `share=False`; no backfill |
| MCP tool create_collection_vouchers | ✅ Implemented | Required top-level `seller_id`; stamp all-new only; replay read-only; no `sudo()` |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| M2O `sheet_id` + O2M `voucher_ids` | ✅ Yes | |
| `@api.constrains` + CHECK; no UNIQUE(sheet_id); no triggers | ✅ Yes | |
| List-bound server action; no wizard | ✅ Yes | |
| ORM seller nullable; form required; MCP request required | ✅ Yes | |
| Top-level MCP seller; stamp all-new only | ✅ Yes | |
| UTC `fields.Date` from member `create_date` | ✅ Yes | |
| Sanitize Command.DELETE→UNLINK; many2many widget | ✅ Yes | |
| No extra indexes; no sheet chatter/state | ✅ Yes | |
| Do not edit nebula-agent | ✅ Yes | This change's collection git stack does not include nebula-agent |
| Manifest `19.0.1.10.0`; keep `migrations/19.0.1.7.0` | ✅ Yes | |
| Freeze sheet seller (`readonly` + write block) | ✅ Yes | Model `readonly=True` plus write UserError; form `readonly="id"` keeps create editable |

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | Found in apply-progress for PR1–PR4 |
| All tasks have tests | ✅ | 16/18 tasks own tests; 4.3 version bump and 4.4 verify are structural |
| RED confirmed (tests exist) | ✅ | Sheet, voucher, UI, ACL, MCP test files exist on `feat/collection-sheets-04-ui-acl` |
| GREEN confirmed (tests pass) | ✅ | All collection-sheets covering tests started this run; official suite 0 failed / 166 |
| Triangulation adequate | ✅ | Multi-case for seller freeze, Action ineligible, MCP seller reject, dates/unlink |
| Safety Net for modified files | ✅ | Modified files reported pre-change suite; new `test_collection_sheet.py` is N/A (new) |

**TDD Compliance**: 6/6 checks passed (4.1 ACL RED passed immediately because the ACL row shipped in PR2; tests still exist and passed here)

---

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 26 | 4 | Odoo TransactionCase (`test_collection_sheet.py`, voucher/UI/ACL deltas) |
| Integration | 7 | 1 | Containerized Odoo + MCP `_call` (`test_collection_mcp_tool.py` seller/replay) |
| E2E | 0 | 0 | not installed |
| **Total** | **33** | **5** | |

---

### Changed File Coverage
Coverage analysis skipped — no coverage tool detected

---

### Assertion Quality
**Assertion quality**: ✅ All assertions verify real behavior

No tautologies, ghost loops, or production-code-free assertions in the change tests. Form/menu coverage is XML-arch TransactionCase (project pattern; E2E unavailable).

---

### Quality Metrics
**Linter**: ➖ Not re-run this verify (would auto-fix and mutate the working tree; isolation and settings WIP must stay). Type Checker: ➖ Not available

### Issues Found
**CRITICAL**: None
**WARNING**:
- Working tree has unstaged settings-menu WIP (`tests/test_collection_ui.py`, `views/res_config_settings_views.xml`) that inflates the suite (166 vs apply-progress 164). Extra settings tests started and passed; they are not collection-sheets covering tests.
- Flag-off isolation is uncommitted (`tests/test_collection_document_review_flag.py` `_force_document_review_enabled` / `new()` defaults; `test_load_menus_omits_document_review_when_flag_off` writes False first). Those previously failed 12 tests started and passed this run. Isolation is not in commit `71cbf1a`.
- CodeGraph init failed (exit 127); structural evidence is filesystem-only.
- Devel filestore `FileNotFoundError` noise appeared in test logs; official result remained 0 failed / 0 errors.
**SUGGESTION**:
- Commit or drop the flag-off isolation separately from collection-sheets so the green suite does not depend on uncommitted test edits.
- Sheet UI is TransactionCase arch-only; no HttpCase/E2E (config e2e unavailable).

### Verdict
PASS WITH WARNINGS
Official test command exited 0 (166/166). All 23 in-scope collection-sheets scenarios have passing covering tests. Warnings are working-tree isolation, settings-menu WIP suite inflation, and CodeGraph fallback — not in-scope spec regressions.
