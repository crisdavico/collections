```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:c6d15f667e396e823d2c645838e6e1d4ed36d68d3875e1f646a804f333d5966b
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 5/5
scenarios: 15/15
test_command: invoke test -m collection --mode=update
test_exit_code: 0
test_output_hash: sha256:71301fba05064b205f7f1605ac91939dd40078b6b09844f0df7716c07448e799
build_command:
  pre-commit run --files odoo/custom/src/private/collection/models/res_company.py
  odoo/custom/src/private/collection/models/res_config_settings.py
  odoo/custom/src/private/collection/models/ir_ui_menu.py
  odoo/custom/src/private/collection/models/collection_voucher.py
  odoo/custom/src/private/collection/models/collection_voucher_line.py
  odoo/custom/src/private/collection/views/res_config_settings_views.xml
  odoo/custom/src/private/collection/__manifest__.py
  odoo/custom/src/private/collection/tests/test_collection_document_review_flag.py
  odoo/custom/src/private/collection/tests/test_collection_document_review.py
  odoo/custom/src/private/collection/tests/test_collection_voucher.py
  odoo/custom/src/private/collection/tests/test_collection_acl.py
  odoo/custom/src/private/collection/tests/test_collection_ui.py
  odoo/custom/src/private/collection/tests/__init__.py
  odoo/custom/src/private/collection/models/__init__.py
build_exit_code: 0
build_output_hash: sha256:aa838140002d107fc03af537853e02bdeba2bb6f32fcd12a6779151a45c0bec8
```

## Verification Report

**Change**: document-review-feature-flag **Version**: 19.0.1.8.0 **Mode**: Strict TDD

Independent spec count from change deltas: `specs/document-review/spec.md` 2
requirements / 6 scenarios; `specs/collection-vouchers/spec.md` 3 requirements / 9
scenarios; combined **5 / 15** (matches orchestrator pre-count). Envelope totals use
this count. Envelope completed counts include every scenario with a passing covering
test at this runtime (✅ COMPLIANT and ⚠️ PARTIAL). None are UNTESTED or FAILING.

`evidence_revision` is SHA-256 of exact test stdout+stderr concatenated with exact build
stdout+stderr (no separator). Same construction as the prior fail report
(`sha256:e942efd88f2e79455cf8e4ebba6f6ead3c45e006842f600d04afdff145acb398`); this
revision is `sha256:c6d15f667e396e823d2c645838e6e1d4ed36d68d3875e1f646a804f333d5966b`.

### Completeness

| Metric           | Value |
| ---------------- | ----- |
| Tasks total      | 17    |
| Tasks complete   | 17    |
| Tasks incomplete | 0     |

### Build & Tests Execution

**Build**: ✅ Passed (scoped pre-commit as lint/quality stand-in; `invoke img-build` not
run)

```text
pre-commit run --files odoo/custom/src/private/collection/models/res_company.py odoo/custom/src/private/collection/models/res_config_settings.py odoo/custom/src/private/collection/models/ir_ui_menu.py odoo/custom/src/private/collection/models/collection_voucher.py odoo/custom/src/private/collection/models/collection_voucher_line.py odoo/custom/src/private/collection/views/res_config_settings_views.xml odoo/custom/src/private/collection/__manifest__.py odoo/custom/src/private/collection/tests/test_collection_document_review_flag.py odoo/custom/src/private/collection/tests/test_collection_document_review.py odoo/custom/src/private/collection/tests/test_collection_voucher.py odoo/custom/src/private/collection/tests/test_collection_acl.py odoo/custom/src/private/collection/tests/test_collection_ui.py odoo/custom/src/private/collection/tests/__init__.py odoo/custom/src/private/collection/models/__init__.py
exit 0 — ruff E501 resolved (docstring shortened; assert message split). Applicable hooks Passed. Optional pylint_odoo C8101 manifest-required-author warning; that hook Passed.
```

**Tests**: ✅ 130 passed / ❌ 0 failed / ⚠️ 0 skipped

```text
invoke test -m collection --mode=update
odoo.tests.result: 0 failed, 0 error(s) of 130 tests when loading database 'devel'
(odoo.tests.stats: collection: 150 tests — framework bookkeeping; authoritative result 130/130)
compose run used a one-off odoo container (seedian-odoo-run-98f0f5de9749); no port conflict with seedian-odoo-1
```

**Coverage**: ➖ Not available / threshold: 0 → Coverage analysis skipped — no coverage
tool detected

### Spec Compliance Matrix

| Requirement                                                   | Scenario                                                      | Test                                                                                                                                                                                                                                                                                                                | Result       |
| ------------------------------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| Per-company Document Review flag                              | Default off                                                   | `tests/test_collection_document_review_flag.py` > `test_document_review_enabled_defaults_false_on_env_company` / `test_document_review_enabled_defaults_false_on_browsed_company` / `test_document_review_helper_defaults_false`                                                                                    | ✅ COMPLIANT |
| Per-company Document Review flag                              | Settings admin toggle                                         | `test_settings_toggle_persists_true_on_company` / `test_settings_toggle_persists_false_on_company` + `tests/test_collection_ui.py` > `test_settings_arch_has_collections_app_and_flag_field` / `test_settings_combined_view_exposes_collections_flag` (ORM `res.config.settings` + `#collections` arch; no browser) | ✅ COMPLIANT |
| Per-company Document Review flag                              | Line state and audit remain                                   | `test_payment_line_views_keep_state_when_review_off` / `test_payment_line_views_keep_state_when_review_on` (`state` on list/search; `reviewed_by`/`reviewed_at` absent from those views and not required by the test)                                                                                               | ⚠️ PARTIAL   |
| Document Review menu and RPCs when flag is off                | Menu hidden when off                                          | `tests/test_collection_ui.py` > `test_load_menus_omits_document_review_when_flag_off` (+ ON triangulation `test_load_menus_includes_document_review_when_flag_on`)                                                                                                                                                  | ✅ COMPLIANT |
| Document Review menu and RPCs when flag is off                | Review operations refuse when off                             | `test_get_review_queue_raises_when_review_off` / `test_action_review_approve_does_not_run_when_review_off` / `test_action_review_reject_does_not_run_when_review_off` / `test_action_review_set_rotation_raises_when_review_off` (RPC `UserError`, not `[]`; no browser `/odoo/document-review`)                    | ⚠️ PARTIAL   |
| Document Review menu and RPCs when flag is off                | Internal ACL when on                                          | `tests/test_collection_acl.py` > `test_portal_user_review_queue_approve_reject_denied` (+ `test_internal_user_review_queue_and_approve_allowed` / `test_internal_user_review_reject_allowed` / `test_internal_user_review_set_rotation_allowed`)                                                                    | ✅ COMPLIANT |
| Voucher state transitions                                     | Validate from new                                             | `tests/test_collection_voucher.py` > `test_action_validate_from_new` / `test_action_validate_allows_unattached_pending_line`                                                                                                                                                                                        | ✅ COMPLIANT |
| Voucher state transitions                                     | Reject from new                                               | `test_action_reject_from_new`                                                                                                                                                                                                                                                                                       | ✅ COMPLIANT |
| Voucher state transitions                                     | Terminal states block transitions                             | `test_terminal_states_block_validate_and_reject`                                                                                                                                                                                                                                                                    | ✅ COMPLIANT |
| Voucher state transitions                                     | Validate blocked while attached lines pending                 | `test_action_validate_blocked_when_attached_line_pending` / `tests/test_collection_document_review.py` > `test_action_validate_blocked_while_attached_pending` (flag ON via write/`setUp`)                                                                                                                          | ✅ COMPLIANT |
| Voucher state transitions                                     | Validate succeeds with pending attachments when review is off | `test_action_validate_succeeds_with_pending_attached_when_review_off`                                                                                                                                                                                                                                               | ✅ COMPLIANT |
| Approve may validate voucher when all attached lines approved | Aggregate voucher validation                                  | `tests/test_collection_document_review.py` > `test_aggregate_validate_when_all_attached_approved` (`setUp` enables flag)                                                                                                                                                                                            | ✅ COMPLIANT |
| Approve may validate voucher when all attached lines approved | Review approve does not run when off                          | `test_action_review_approve_does_not_run_when_review_off`                                                                                                                                                                                                                                                           | ✅ COMPLIANT |
| Line reject immediately rejects voucher                       | Immediate voucher rejection on line reject                    | `test_line_reject_rejects_voucher_immediately` / `test_reject_sets_rejected_and_records_audit`                                                                                                                                                                                                                      | ✅ COMPLIANT |
| Line reject immediately rejects voucher                       | Review reject does not run when off                           | `test_action_review_reject_does_not_run_when_review_off`                                                                                                                                                                                                                                                            | ✅ COMPLIANT |

**Compliance summary**: 15/15 scenarios have passing covering tests (13 ✅ COMPLIANT, 2
⚠️ PARTIAL; 0 UNTESTED; 0 FAILING)

### Correctness (Static Evidence)

| Requirement                                                   | Status         | Notes                                                                                                                                                                                                                                                                                     |
| ------------------------------------------------------------- | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Per-company Document Review flag                              | ✅ Implemented | `res.company.document_review_enabled` default False; Settings related `readonly=False`; `#collections` app `groups="base.group_system"`; helper + `registry.clear_cache()` on flag write. Line `state` stays on payment-line views; `reviewed_by`/`reviewed_at` stay on the model/DB only |
| Document Review menu and RPCs when flag is off                | ✅ Implemented | `_load_menus_blacklist` appends review menu id when helper is false; four RPCs raise `UserError("Document Review is not enabled.")` via `_ensure_document_review_enabled` before queue/lock                                                                                               |
| Voucher state transitions                                     | ✅ Implemented | `_ensure_no_pending_attached_review` returns when helper is false; ON path still raises while attached lines are pending                                                                                                                                                                  |
| Approve may validate voucher when all attached lines approved | ✅ Implemented | ON path unchanged (`_validate_voucher_if_all_attached_approved`); OFF approve raises before that path                                                                                                                                                                                     |
| Line reject immediately rejects voucher                       | ✅ Implemented | ON path still rejects a `new` voucher; OFF reject raises and leaves voucher `new`                                                                                                                                                                                                         |

### Coherence (Design)

| Decision                                 | Followed? | Notes                                                                                                           |
| ---------------------------------------- | --------- | --------------------------------------------------------------------------------------------------------------- |
| Company Boolean vs `ir.config_parameter` | ✅ Yes    | `res.company` Boolean, default False                                                                            |
| Related `readonly=False`                 | ✅ Yes    | `related="company_id.document_review_enabled"`                                                                  |
| `_load_menus_blacklist` vs `menu.active` | ✅ Yes    | Blacklist xmlid when OFF; no `menu.active`                                                                      |
| One private helper                       | ✅ Yes    | `res.company._document_review_enabled()` on `env.company` (`@api.model` + `@api.private`)                       |
| Cache clear on flag write                | ✅ Yes    | `self.env.registry.clear_cache()` when flag in vals                                                             |
| Opt-in existing review tests             | ✅ Yes    | Review `setUp`, validate-blocked voucher test, ACL review helper enable the flag                                |
| `_load_menus_blacklist` `@api.model`     | ⚠️ No     | Design guessed `@api.model`; implementation matches Odoo 19 core/hr (no decorator). Menu hide/show tests passed |
| Four RPC checks extracted                | ✅ Yes    | `_ensure_document_review_enabled` (apply 2.6); still raises before queue/lock                                   |
| Manifest `19.0.1.8.0` + settings view    | ✅ Yes    | Settings XML in `data`; version bumped                                                                          |
| No voucher `company_id`                  | ✅ Yes    | Flag follows `env.company`                                                                                      |

### TDD Compliance

| Check                         | Result | Details                                                                                                                                                                              |
| ----------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| TDD Evidence reported         | ✅     | TDD Cycle Evidence tables present for Phases 1–4 in apply-progress                                                                                                                   |
| All tasks have tests          | ✅     | 16/17 tasks map to test files; 4.1 is confirmation-only (views untouched / no `menu.active` / no voucher `company_id`)                                                               |
| RED confirmed (tests exist)   | ✅     | Listed files exist: `test_collection_document_review_flag.py`, `test_collection_document_review.py`, `test_collection_voucher.py`, `test_collection_acl.py`, `test_collection_ui.py` |
| GREEN confirmed (tests pass)  | ✅     | Full `/collection` suite 130/130 pass on this verify execution                                                                                                                       |
| Triangulation adequate        | ⚠️     | Flag OFF/ON, four RPCs, persist True/False, load_menus OFF/ON triangulated; audit-column appearance and `/odoo/document-review` browser path are single-layer/partial                |
| Safety Net for modified files | ✅     | apply-progress recorded baselines before voucher/line/UI edits; N/A (new) matches new company/settings/menu/flag-test files                                                          |

**TDD Compliance**: 5/6 checks passed (triangulation ⚠️ for audit columns and browser
review path)

---

### Test Layer Distribution

| Layer       | Tests                                                                                  | Files                         | Tools                                           |
| ----------- | -------------------------------------------------------------------------------------- | ----------------------------- | ----------------------------------------------- |
| Unit        | 91 in change-related files (14 flag + 27 document_review + 18 voucher + 8 acl + 24 ui) | 5                             | Odoo TransactionCase                            |
| Integration | 130 module tests (full suite)                                                          | 8 test modules under `tests/` | Containerized Odoo + PostgreSQL (`invoke test`) |
| E2E         | 0                                                                                      | 0                             | not installed (`e2e: false`)                    |
| **Total**   | **130**                                                                                | **8**                         |                                                 |

---

### Changed File Coverage

Coverage analysis skipped — no coverage tool detected

---

### Assertion Quality

| File                                            | Line    | Assertion                                                                | Issue                                                              | Severity |
| ----------------------------------------------- | ------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------ | -------- |
| `tests/test_collection_document_review_flag.py` | 191–197 | `if list_nodes:` / `if search_nodes:` around `reviewed_by`/`reviewed_at` | Audit columns are not required to appear; empty xpath still passes | WARNING  |

**Assertion quality**: 0 CRITICAL, 1 WARNING

Flag OFF RPC tests assert the exact `UserError` message and unchanged
`pending`/`new`/rotation. Default-off and Settings persist tests assert concrete boolean
values. Empty-queue is not used for the refuse path (`assertRaises(UserError)`). No
tautologies or ghost loops found.

---

### Quality Metrics

**Linter**: ✅ No errors; ⚠️ 1 optional pylint_odoo C8101 (`manifest-required-author`
missing `'Eynes'`; hook Passed) **Type Checker**: ➖ Not available

### Issues Found

**CRITICAL**: None

**WARNING**:

1. `_load_menus_blacklist` has no `@api.model`. Design guessed `@api.model`;
   implementation matches Odoo 19 core/hr. Menu blacklist tests passed; this does not
   break a spec.
2. Scenario "Review operations refuse when off" is ⚠️ PARTIAL: four RPCs raise
   `UserError` (not empty-queue success), but direct `/odoo/document-review` has no
   browser/HttpCase coverage (`e2e: false`).
3. Scenario "Line state and audit remain" is ⚠️ PARTIAL: payment-line list/search still
   expose `state`; `reviewed_by`/`reviewed_at` are not on those views and the covering
   test does not fail when they are absent.

**SUGGESTION**:

1. If audit columns must appear on payment-line views, add `reviewed_by`/`reviewed_at`
   to list/search and assert presence (not a conditional no-op).
2. Optional pylint_odoo C8101 (`manifest-required-author`) remains pre-existing; not
   introduced by this change.

### Verdict

PASS WITH WARNINGS All 17 tasks complete; 130/130 collection tests passed; scoped
pre-commit exited 0. 15/15 scenarios have passing covering tests (13 fully COMPLIANT, 2
PARTIAL). Remaining issues are PARTIAL E2E/audit-column coverage and the design
`@api.model` WARNING on `_load_menus_blacklist`.
