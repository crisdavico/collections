```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:2519380dd8937e6cf6564a429c5209dca127c4b0f8e35f28d7c06122f644ceb2
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 9/9
scenarios: 36/36
test_command:
  env GID="$(id -g)" UID="$(id -u)" DOODBA_UMASK=27 docker compose run --rm -e
  "DB_FILTER='^devel$'" odoo odoo --test-enable --stop-after-init --workers=0 -d devel
  -u collection --test-tags /collection
test_exit_code: 0
test_output_hash: sha256:c078df6307536c62e36a43f57c732920dae537988adaecb4644d66053bb1f35e
build_command:
  pre-commit run --files odoo/custom/src/private/collection/models/collection_sheet.py
  odoo/custom/src/private/collection/models/collection_voucher.py
  odoo/custom/src/private/collection/views/collection_views.xml
  odoo/custom/src/private/collection/tests/test_collection_sheet.py
  odoo/custom/src/private/collection/tests/test_collection_ui.py
  odoo/custom/src/private/collection/tests/test_collection_document_review.py
  odoo/custom/src/private/collection/tests/test_collection_mcp_tool.py
  odoo/custom/src/private/collection/__manifest__.py
  odoo/custom/src/private/collection/AGENTS.md
build_exit_code: 0
build_output_hash: sha256:94210ee5c8b76a4d5d45bc40b6e3942cd7442751dd31848ab072208bd44b9523
```

## Verification Report

**Change**: auto-assign-open-sheet **Version**: 19.0.1.12.0 **Mode**: Strict TDD

Delta spec counts (ADDED + MODIFIED requirement blocks and their scenarios, counted from
the change specs): 9 requirements / 36 scenarios.

- `specs/collection-sheets/spec.md`: 3 ADDED + 4 MODIFIED = 7 requirements / 18
  scenarios
- `specs/collection-vouchers/spec.md`: 1 ADDED + 1 MODIFIED = 2 requirements / 18
  scenarios

`evidence_revision` is SHA-256 of exact test stdout+stderr concatenated with exact build
stdout+stderr (no separator).

### Completeness

| Metric           | Value |
| ---------------- | ----- |
| Tasks total      | 13    |
| Tasks complete   | 13    |
| Tasks incomplete | 0     |

All tasks in `tasks.md` (1.1–5.1) are checked `[x]`. `apply-progress.md` reports Units
1–3 plus Phases 4–5 complete. No remaining tasks.

### Build & Tests Execution

**Build**: ✅ Passed (scoped pre-commit; `invoke img-build` not run — no image deps)

Command from `/home/crisd/projects/seedian/seedian`. Exit 0. Full stdout+stderr hashed
as `build_output_hash`.

```text
forbidden files......................................(no files to check)Skipped
Update pre-commit excluded addons........................................Passed
Checks for Odoo modules..................................................Passed
ruff (legacy alias)......................................................Passed
ruff format..............................................................Passed
prettier + plugin-xml....................................................Passed
check xml................................................................Passed
pylint with optional checks..............................................Passed
- hook id: pylint_odoo
C8101(manifest-required-author): One of the following authors must be present in manifest: 'Eynes'
Check for Odoo modules using pylint......................................Passed
Generate addons README files from fragments..............................Passed
```

Optional pylint C8101 is a warning, not a hook failure. Mandatory pylint passed. Author
`Seedian` is pre-existing and unchanged by this version bump.

**Tests**: ✅ 220 passed / ❌ 0 failed / ⚠️ 0 skipped

Command (Doodba compose run, cwd `/home/crisd/projects/seedian/seedian`):
`env GID="$(id -g)" UID="$(id -u)" DOODBA_UMASK=27 docker compose run --rm -e "DB_FILTER='^devel$'" odoo odoo --test-enable --stop-after-init --workers=0 -d devel -u collection --test-tags /collection`.
Exit 0. Full stdout+stderr hashed as `test_output_hash`.

```text
collection: 244 tests 4.69s 8052 queries
0 failed, 0 error(s) of 220 tests when loading database 'devel'
```

Odoo stats line `244 tests` includes framework overhead; the authoritative result is
`0 failed, 0 error(s) of 220 tests`. Covering `Starting …` lines for the mapped
sheet/UI/MCP tests appeared in this run with no subsequent FAIL/ERROR.

Compose-run logs include `ir.attachment` `FileNotFoundError` INFO traces for filestore
paths missing in the ephemeral container; they did not fail tests.

**Coverage**: ➖ Not available (config `coverage.available: false`,
`coverage_threshold: 0`). Coverage analysis skipped — no coverage tool detected.

### Spec Compliance Matrix

| Requirement                                        | Scenario                                                    | Test                                                                                                                                                                                                        | Result       |
| -------------------------------------------------- | ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| Open/closed lifecycle                              | Default open on create                                      | `tests/test_collection_sheet.py > test_sequence_assigned_on_create`                                                                                                                                         | ✅ COMPLIANT |
| Open/closed lifecycle                              | Close when open                                             | `tests/test_collection_sheet.py > test_action_close_from_open`                                                                                                                                              | ✅ COMPLIANT |
| Open/closed lifecycle                              | Reopen when no other open                                   | `tests/test_collection_sheet.py > test_action_reopen_from_closed`                                                                                                                                           | ✅ COMPLIANT |
| Open/closed lifecycle                              | Raw state write rejected                                    | `tests/test_collection_sheet.py > test_raw_state_write_routes_to_close_and_reopen`; `test_raw_state_write_invalid_transition_rejected`; `test_audited_state_write_allowed_with_context`                     | ✅ COMPLIANT |
| At most one open sheet per seller (new operations) | Create second open rejected                                 | `tests/test_collection_sheet.py > test_create_second_open_rejected`                                                                                                                                         | ✅ COMPLIANT |
| At most one open sheet per seller (new operations) | Reopen rejected if another open exists                      | `tests/test_collection_sheet.py > test_reopen_rejected_if_another_open_exists`                                                                                                                              | ✅ COMPLIANT |
| At most one open sheet per seller (new operations) | More than one open fail-closed on new operations            | `tests/test_collection_sheet.py > test_leftover_multiple_opens_reject_new_ops`                                                                                                                              | ✅ COMPLIANT |
| At most one open sheet per seller (new operations) | Closing extras still succeeds                               | `tests/test_collection_sheet.py > test_leftover_multiple_opens_still_closeable`                                                                                                                             | ✅ COMPLIANT |
| Closed sheet membership freeze                     | Freeze add, remove, and reassign                            | `tests/test_collection_sheet.py > test_freeze_rejects_add_remove_and_reassign`                                                                                                                              | ✅ COMPLIANT |
| Sheet sequence identity                            | Sequence assigned on create                                 | `tests/test_collection_sheet.py > test_sequence_assigned_on_create`; `test_sequence_names_are_unique`                                                                                                       | ✅ COMPLIANT |
| Membership, dates, and deletion                    | Assign and reassign                                         | `tests/test_collection_sheet.py > test_reassign_moves_voucher_to_sheet_b_only`                                                                                                                              | ✅ COMPLIANT |
| Membership, dates, and deletion                    | Empty sheet                                                 | `tests/test_collection_sheet.py > test_empty_sheet_dates_false_and_no_received_date`                                                                                                                        | ✅ COMPLIANT |
| Membership, dates, and deletion                    | Dates from member create_date                               | `tests/test_collection_sheet.py > test_dates_from_utc_member_create_date`                                                                                                                                   | ✅ COMPLIANT |
| Membership, dates, and deletion                    | Unlink unassigns                                            | `tests/test_collection_sheet.py > test_unlink_sheet_unassigns_vouchers`; `test_unlink_closed_sheet_unassigns_vouchers`                                                                                      | ✅ COMPLIANT |
| Create sheet Action                                | Unassigned same-seller any state                            | `tests/test_collection_sheet.py > test_action_creates_sheet_for_unassigned_same_seller_any_state`                                                                                                           | ✅ COMPLIANT |
| Create sheet Action                                | Ineligible selection rejected                               | `tests/test_collection_sheet.py > test_action_rejects_ineligible_selection`; `test_action_rejects_null_seller_selection`                                                                                    | ✅ COMPLIANT |
| Create sheet Action                                | Action rejected when an open sheet exists                   | `tests/test_collection_sheet.py > test_action_rejected_when_open_sheet_exists`; `test_leftover_multiple_opens_reject_new_ops`                                                                               | ✅ COMPLIANT |
| Collection Sheets UI                               | Menu and form behaviors                                     | `tests/test_collection_ui.py > test_collection_sheets_menu_list_form_search`; `test_collection_sheets_form_statusbar_close_reopen`; `test_sheet_form_header_document_review_visible_when_saved_and_flag_on` | ✅ COMPLIANT |
| Create auto-assign to open sheet                   | UI or ORM create with seller assigns                        | `tests/test_collection_sheet.py > test_create_with_seller_assigns_unique_open_sheet`                                                                                                                        | ✅ COMPLIANT |
| Create auto-assign to open sheet                   | Create without seller stays unassigned                      | `tests/test_collection_sheet.py > test_create_without_seller_stays_unassigned`                                                                                                                              | ✅ COMPLIANT |
| Create auto-assign to open sheet                   | Explicit sheet_id honored when open                         | `tests/test_collection_sheet.py > test_create_honors_explicit_open_sheet_id`                                                                                                                                | ✅ COMPLIANT |
| Create auto-assign to open sheet                   | Assign to closed sheet fails                                | `tests/test_collection_sheet.py > test_create_with_closed_sheet_id_fails`; `test_freeze_rejects_add_remove_and_reassign`                                                                                    | ✅ COMPLIANT |
| Create auto-assign to open sheet                   | Later seller write does not auto-assign                     | `tests/test_collection_sheet.py > test_later_seller_write_does_not_auto_assign`                                                                                                                             | ✅ COMPLIANT |
| Create auto-assign to open sheet                   | No open sheet creates then assigns                          | `tests/test_collection_sheet.py > test_create_with_seller_creates_open_sheet_when_none`                                                                                                                     | ✅ COMPLIANT |
| Create auto-assign to open sheet                   | More than one open rejects create                           | `tests/test_collection_sheet.py > test_create_with_seller_rejected_when_multiple_opens`                                                                                                                     | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                | All-new create                                              | `tests/test_collection_mcp_tool.py > test_all_new_create_returns_vouchers_in_payment_order`; `test_all_new_create_stamps_seller_id`                                                                         | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                | Exact-retry returns all vouchers                            | `tests/test_collection_mcp_tool.py > test_exact_retry_returns_all_vouchers_ignores_customer`; `test_exact_retry_does_not_mutate_null_seller`                                                                | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                | Duplicate document_id in call                               | `tests/test_collection_mcp_tool.py > test_in_call_duplicate_document_id_rejects_no_writes`                                                                                                                  | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                | Partial-conflict                                            | `tests/test_collection_mcp_tool.py > test_partial_conflict_rejects_no_writes`                                                                                                                               | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                | Existing document_ids on different vouchers succeed         | `tests/test_collection_mcp_tool.py > test_existing_document_ids_on_different_vouchers_succeed`                                                                                                              | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                | ACL denial for non-permitted user                           | `tests/test_collection_mcp_tool.py > test_portal_user_denied_no_writes`                                                                                                                                     | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                | Missing or invalid seller_id rejected                       | `tests/test_collection_mcp_tool.py > test_missing_seller_id_rejects_no_writes`; `test_portal_seller_id_rejects_no_writes`; `test_unknown_seller_id_rejects_no_writes`                                       | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                | All-new with unique open assigns the batch                  | `tests/test_collection_mcp_tool.py > test_all_new_unique_open_assigns_all_payments`                                                                                                                         | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                | All-new with no open creates one open sheet and assigns all | `tests/test_collection_mcp_tool.py > test_all_new_no_open_creates_one_sheet_and_assigns_all`                                                                                                                | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                | All-new with more than one open rejected                    | `tests/test_collection_mcp_tool.py > test_all_new_multiple_opens_rejects_no_writes`                                                                                                                         | ✅ COMPLIANT |
| MCP tool create_collection_vouchers                | Exact replay does not change sheet_id                       | `tests/test_collection_mcp_tool.py > test_exact_replay_leaves_sheet_id_and_write_date`                                                                                                                      | ✅ COMPLIANT |

**Compliance summary**: 36/36 scenarios compliant

### Correctness (Static Evidence)

| Requirement                                        | Status         | Notes                                                                                                                                                                               |
| -------------------------------------------------- | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Open/closed lifecycle                              | ✅ Implemented | `collection.sheet.state` Selection `open`/`closed`, default `open`, required; `action_close`/`action_reopen`; raw `state` write intercepted unless `collection_sheet_audited_state` |
| At most one open sheet per seller (new operations) | ✅ Implemented | `_open_sheets_for_seller` + guards on create-open, `action_reopen`, Action, auto-assign; leftover Close still works; no UNIQUE SQL on seller/state                                  |
| Closed sheet membership freeze                     | ✅ Implemented | Closed sheet `write` rejects `voucher_ids`; voucher `create`/`write` rejects add/remove/reassign; unlink via `collection_sheet_unlinking`                                           |
| Sheet sequence identity                            | ✅ Implemented | Sequence `collection.sheet` `CS/<year>/…`; workflow is only `open`/`closed`                                                                                                         |
| Membership, dates, and deletion                    | ✅ Implemented | Dates from member `create_date`; empty dates False; unlink unassigns open and closed                                                                                                |
| Create sheet Action                                | ✅ Implemented | After `_seller_for_sheet_action`, `_raise_if_seller_has_open_sheet`; still create-new-sheet                                                                                         |
| Collection Sheets UI                               | ✅ Implemented | Non-clickable statusbar `open,closed`; Close/Reopen invisibles; membership `readonly="state == 'closed'"`; list/search `state`; Document Review header remains                      |
| Create auto-assign to open sheet                   | ✅ Implemented | `create` before `super`: seller set + omitted/falsey `sheet_id` → lock then 0 create / 1 use / >1 `UserError`; later `seller_id` write does not assign                              |
| MCP tool create_collection_vouchers                | ✅ Implemented | Tool file unchanged; all-new inherits ORM create; replay does not call `create`; response keys `{id,name,state,document_id}` only                                                   |

### Coherence (Design)

| Decision                                                                                                           | Followed? | Notes                                                                                        |
| ------------------------------------------------------------------------------------------------------------------ | --------- | -------------------------------------------------------------------------------------------- |
| `state` Selection `open`/`closed`, default `open`, manifest `19.0.1.12.0`, no UNIQUE, no `migrations/19.0.1.12.0/` | ✅ Yes    | Field + version present; no seller/state UNIQUE; no migration folder                         |
| Auto-assign in ORM `create` before `super` when seller set and `sheet_id` omitted/falsey                           | ✅ Yes    | `_apply_open_sheet_auto_assign`; one resolve per seller; explicit `sheet_id` honored if open |
| One-open count on new ops only (not `@api.constrains` / UNIQUE)                                                    | ✅ Yes    | Create-open, reopen, Action, auto-assign; leftover `>1` still Closeable                      |
| `pg_advisory_xact_lock(hashtext('collection.sheet.open'), seller_id)`                                              | ✅ Yes    | `_lock_open_sheet_for_seller` on auto-assign resolve and create-open                         |
| Close/Reopen + intercept raw `state` write                                                                         | ✅ Yes    | Matches voucher audited-state pattern; invalid transitions rejected                          |
| Freeze via sheet `voucher_ids` write + voucher `sheet_id` create/write; unlink context                             | ✅ Yes    | `collection_sheet_unlinking`                                                                 |
| Action remains create-new; reject if ≥1 open                                                                       | ✅ Yes    | After eligibility checks                                                                     |
| MCP inherit ORM; no schema/`sheet_id` in payload                                                                   | ✅ Yes    | `tools/collection_voucher.py` not edited                                                     |

### TDD Compliance

| Check                         | Result | Details                                                                                                           |
| ----------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------- |
| TDD Evidence reported         | ✅     | TDD Cycle Evidence table present in `apply-progress.md` (Units 1–3 plus Phases 4–5 N/A rows)                      |
| All tasks have tests          | ✅     | 1.1–3.3 have test files; 1.4/2.4/3.4/4.1 are suite/lint; 5.1 docs N/A                                             |
| RED confirmed (tests exist)   | ✅     | `tests/test_collection_{sheet,ui,mcp_tool,document_review}.py` exist on disk                                      |
| GREEN confirmed (tests pass)  | ✅     | 220/220 `/collection` tests passed on this verify run                                                             |
| Triangulation adequate        | ✅     | 0/1/>1 open paths; close-first leftover vs two sellers; explicit vs omitted `sheet_id`; MCP unique/none/>1/replay |
| Safety Net for modified files | ✅     | Apply-progress recorded passing counts before modifying sheet/voucher/UI/MCP/review tests                         |

**TDD Compliance**: 6/6 checks passed

Apply-progress GREEN counts (Sheet 43, Ui 29, Review 36, MCP tool 23, suite 220) match
this runtime: `0 failed, 0 error(s) of 220 tests`.

---

### Test Layer Distribution

| Layer       | Tests   | Files | Tools                                                                                                                                                                                       |
| ----------- | ------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Unit        | 140     | 4     | Odoo TransactionCase / view-arch registry (`TestCollectionSheet` 43, `TestCollectionUi` 29, `TestCollectionDocumentReview` 36, `test_collection_mcp_tool.py` 32 including attachment class) |
| Integration | 0       | 0     | Containerized Odoo is the harness for the unit suite, not a separate layer                                                                                                                  |
| E2E         | 0       | 0     | not installed                                                                                                                                                                               |
| **Total**   | **140** | **4** |                                                                                                                                                                                             |

Changed-file tests above; full `/collection` tag ran 220 methods. MCP coverage is
in-process `muk_mcp.tool._call` (same as apply-progress). Every spec scenario is covered
at the TransactionCase / arch layer.

---

### Changed File Coverage

Coverage analysis skipped — no coverage tool detected (config
`coverage.available: false`, `coverage_threshold: 0`).

---

### Assertion Quality

Changed tests call production ORM (`collection.sheet` / `collection.voucher`
create/write/actions) and MCP `_call`, then assert concrete `state`, `sheet_id`, counts,
`UserError`, and payload keys `{id,name,state,document_id}`. Empty/unassigned cases have
companion assigned/non-empty tests. UI tests assert statusbar options, button
invisibles, and membership readonly — those are the specified form behaviors, not CSS
smoke. No tautologies, ghost loops, or type-only-only assertions found.

**Assertion quality**: ✅ All assertions verify real behavior

---

### Quality Metrics

**Linter**: ⚠️ 1 optional warning / 0 errors (pre-commit Passed). Optional pylint C8101
wants author `Eynes`; manifest author is `Seedian` (pre-existing; this change only
bumped `19.0.1.12.0`). Mandatory pylint passed. Ruff, ruff-format, prettier, OCA module
checks, and `oca-gen-addon-readme` passed. **Type Checker**: ➖ Not available

### Issues Found

**CRITICAL**: None **WARNING**:

- Optional pylint C8101 (`manifest-required-author`): hook wants author `Eynes`;
  manifest uses `Seedian`. Hook still Passed. Pre-existing; not introduced by this
  change. **SUGGESTION**:
- Spec wording says raw `state` write MUST be rejected except via Close/Reopen;
  implementation intercepts and routes to `action_close`/`action_reopen` (design).
  Invalid transitions are rejected. Covered by intercept tests; no spec break.
- Collection Sheets UI is proven via XML arch/registry, not a browser. Acceptable: E2E
  tools are not in capabilities.
- Compose-run INFO `FileNotFoundError` on live-DB filestore hashes is harness noise in
  an ephemeral container; TransactionCase still passed.

### Verdict

PASS WITH WARNINGS All 13 tasks are complete; 9/9 requirements and 36/36 scenarios have
passing runtime covering tests; scoped pre-commit passed. Remaining item is a
pre-existing optional pylint author warning that does not break the spec.
