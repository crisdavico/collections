```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:4309e379290016827f812662d0cf7e5983d2757a7a971fc1a4cb9a59c9d479ca
verdict: pass
blockers: 0
critical_findings: 0
requirements: 2/2
scenarios: 11/11
test_command: invoke test -m collection --mode=update
test_exit_code: 0
test_output_hash: sha256:88ccc219c70bf0dcf29889baf5c408f5a9937e80dd1ce9718c2acb18927740b7
build_command: docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init
build_exit_code: 0
build_output_hash: sha256:377c89b6ed025ecdd2bb8a94c16b8dd97eed7a04b8d3fb403ec46446ebbbdae1
```

## Verification Report

**Change**: `sheet-form-allocations-only`
**Version**: collection `19.0.1.25.0` (delta specs `collection-sheets` + `collection-vouchers`)
**Mode**: Strict TDD

Delta spec counts (actual `### Requirement:` / `#### Scenario:` blocks): collection-sheets 1/3 + collection-vouchers 1/8 = **2 requirements**; **11 scenarios**. Matches the authoritative totals passed to the validator.

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 12 |
| Tasks complete | 12 |
| Tasks incomplete | 0 |

All `tasks.md` items 1.1–3.2 are `[x]`. Full spec verification proceeded.

### Build & Tests Execution
**Build**: ✅ Passed (module upgrade; `invoke img-build` skipped as not this change)

```text
docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init
exit 0
output sha256:377c89b6ed025ecdd2bb8a94c16b8dd97eed7a04b8d3fb403ec46446ebbbdae1
odoo: Modules loaded.
```

**Tests**: ✅ 509 passed / ❌ 0 failed / ⚠️ 0 skipped

```text
invoke test -m collection --mode=update
exit 0
output sha256:88ccc219c70bf0dcf29889baf5c408f5a9937e80dd1ce9718c2acb18927740b7
odoo.tests.result: 0 failed, 0 error(s) of 509 tests when loading database 'devel'
odoo.tests.stats: collection: 565 tests 23.21s 40453 queries
```

Every covering test named in the matrix logged `Starting ...` in this run and the suite finished with zero failures/errors.

**Lint** (not envelope): scoped `pre-commit run --files` on `AGENTS.md`, `models/collection_sheet.py`, `views/collection_views.xml`, `tests/test_collection_ui.py`, `tests/test_collection_sheet.py`, and `openspec/changes/sheet-form-allocations-only/**` — exit 0. Literal glob `odoo/custom/src/private/collection/**` also exited 0 in this run (optional pylint `C8101` on `__manifest__.py`, author `Eynes`). Apply-progress documents that the same glob can prettier-fail archived duplicate-key `state.yaml`; that is pre-existing and is not a CRITICAL for this change.

**Coverage**: ➖ Not available — Coverage analysis skipped — no coverage tool detected

### Spec Compliance Matrix
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Sheet form notebook | Allocations-only notebook with Customer | `test_collection_ui.py` > `test_sheet_form_notebook_allocations_only` | ✅ COMPLIANT |
| Sheet form notebook | Saved sheet opens filtered vouchers | `test_collection_sheet.py` > `test_action_open_vouchers_returns_filtered_act_window`, `test_action_open_vouchers_domain_matches_each_saved_sheet`, `test_voucher_count_matches_member_count`; `test_collection_ui.py` > `test_sheet_form_stat_button_opens_vouchers`, `test_menu_and_action_xmlids` | ✅ COMPLIANT |
| Sheet form notebook | Unsaved sheet hides and refuses voucher action | `test_collection_ui.py` > `test_sheet_form_stat_button_opens_vouchers`; `test_collection_sheet.py` > `test_action_open_vouchers_refused_on_new_id` | ✅ COMPLIANT |
| Payment Vouchers UI | Menu and form behaviors | `test_collection_ui.py` > `test_menu_and_action_xmlids`, `test_list_and_search_show_required_fields`, `test_form_statusbar_approve_reject_when_pending`, `test_form_typed_invisible_payment_fields`, `test_form_has_no_typed_payment_ids_tables`, `test_views_have_no_received_date` | ✅ COMPLIANT |
| Payment Vouchers UI | Kanban grouped by state | `test_collection_ui.py` > `test_kanban_groups_by_state_and_shows_card_fields`, `test_create_and_edit_enabled_on_payment_vouchers` | ✅ COMPLIANT |
| Payment Vouchers UI | Payment Lines menu absent | `test_collection_ui.py` > `test_payment_line_xmlids_removed`, `test_load_menus_omits_payment_lines` | ✅ COMPLIANT |
| Payment Vouchers UI | UI create_date visibility | `test_collection_ui.py` > `test_list_and_search_show_required_fields`, `test_kanban_groups_by_state_and_shows_card_fields`, `test_form_statusbar_approve_reject_when_pending` | ✅ COMPLIANT |
| Payment Vouchers UI | Customer field has no domain | `test_collection_ui.py` > `test_customer_field_is_partner_id_without_domain` | ✅ COMPLIANT |
| Payment Vouchers UI | sheet_id on list form search | `test_collection_ui.py` > `test_voucher_list_form_search_expose_sheet_id` | ✅ COMPLIANT |
| Payment Vouchers UI | Clear sheet_id unlinks open membership | `test_collection_sheet.py` > `test_reassign_moves_voucher_to_sheet_b_only` | ✅ COMPLIANT |
| Payment Vouchers UI | Closed-sheet unlink denied | `test_collection_sheet.py` > `test_freeze_rejects_add_remove_and_reassign` | ✅ COMPLIANT |

**Compliance summary**: 11/11 scenarios compliant

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| Sheet form notebook | ✅ Implemented | One Allocations notebook page with `partner_id` after `name` before `state`; no `voucher_ids` in arch; `oe_button_box` first inside `<sheet>`; non-stored `voucher_count`; hand-built `action_open_vouchers` (no `path`, domain `sheet_id`, defaults `sheet_id`/`seller_id`); `_ensure_saved_sheet` generalized; button `invisible="not id"` |
| Payment Vouchers UI | ✅ Implemented | Menu action keeps `path="payment-vouchers"`; list `sheet_id optional="hide"`; form `sheet_id` editable after `seller_id`; search field + group-by; kanban has no `sheet_id`; existing freeze/reassign tests cover unlink |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| Hand-built `action_open_vouchers` dict, not `_for_xml_id` | ✅ Yes | `view_mode` `list,kanban,form`; no `path` |
| Form `sheet_id` fully editable; server guards | ✅ Yes | no extra `readonly` on form `sheet_id` |
| Reuse `_ensure_saved_sheet`; generalize message | ✅ Yes | `"This action requires a saved collection sheet."` |
| Exactly one sheet-form `partner_id` (allocations list) | ✅ Yes | `test_customer_field_is_partner_id_without_domain` count stays 1 |
| Non-stored `voucher_count` `@api.depends("voucher_ids")` | ✅ Yes | keep model `voucher_ids` |
| Stat button first child inside `<sheet>` | ✅ Yes | `oe_stat_button` + `statinfo` + `invisible="not id"` |
| Invert UI tests before XML/Python | ✅ Yes | apply-progress RED then GREEN |

### Issues Found
**CRITICAL**: None
**WARNING**: None
**SUGGESTION**:
- Optional pylint `C8101` (`manifest-required-author`, author `Eynes`) appears when the collection glob includes `__manifest__.py`; owned-files lint for this change did not touch the manifest.
- Pre-existing duplicate OCR/seller field-label warnings on `collection.voucher` during registry load (build and tests).
- `test_customer_field_is_partner_id_without_domain` docstring still mentions a "sheet member list"; behavior is correct (one unbound `partner_id` on the allocations nested list).
- Do not use `pre-commit run --files odoo/custom/src/private/collection/**` as the owned quality gate: apply-progress records prettier `SyntaxError` on archived duplicate-key `state.yaml` (this run's glob expansion exited 0).

### Verdict
PASS
All 2 requirements and 11 scenarios have covering tests that started and passed in this run; design decisions match the implementation.

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | TDD Cycle Evidence table in `apply-progress.md` for tasks 1.1–3.2 |
| All tasks have tests | ✅ | 10/10 implementation tasks (1.1–2.4) have test files; 3.1 docs and 3.2 quality are N/A |
| RED confirmed (tests exist) | ✅ | `tests/test_collection_ui.py` and `tests/test_collection_sheet.py` contain the inverted/new methods listed in apply-progress |
| GREEN confirmed (tests pass) | ✅ | This run: 0 failed, 0 error(s) of 509 tests |
| Triangulation adequate | ✅ | 1.1/1.3/1.4/1.5 triangulated; 1.2 invert-by-removal Single; 1.6 unsaved Single with Document Review companion |
| Safety Net for modified files | ✅ | 1.1–1.6/2.1–2.4 recorded existing suites; 3.1 N/A docs |

**TDD Compliance**: 6/6 checks passed

---

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 8 | 2 | Odoo TransactionCase + lxml arch (`test_collection_ui.py` inverted/new methods; `test_collection_sheet.py` count/action/`UserError`) |
| Integration | 0 | 0 | no new HttpCase |
| E2E | 0 | 0 | not installed |
| **Total** | **8** | **2** | focused tests created/inverted for this change |

Envelope run also executed the full collection module suite (509). Unlink scenarios reuse existing freeze/reassign methods in `test_collection_sheet.py`.

---

### Changed File Coverage
Coverage analysis skipped — no coverage tool detected

---

### Assertion Quality

**Assertion quality**: ✅ All assertions verify real behavior

Scanned new/inverted methods in `tests/test_collection_ui.py` and `tests/test_collection_sheet.py`. Arch tests assert notebook page strings, `voucher_ids` absence, Customer field order, stat-button slot/widget/`invisible`, list `optional="hide"`, form following-sibling `sheet_id`, search group-by, and kanban without `sheet_id`. Model tests assert non-stored compute, `len(voucher_ids)` vs count, act_window `view_mode`/`domain`/`context`/no `path`, and `UserError` on `.new()`. Freeze/reassign tests call `write({"sheet_id": ...})` and assert membership. No tautologies, ghost loops, or production-code-free assertions.

---

### Quality Metrics
**Linter**: ✅ No errors on owned files (scoped pre-commit exit 0). Optional glob `C8101` on `__manifest__.py` is pre-existing.
**Type Checker**: ➖ Not available
