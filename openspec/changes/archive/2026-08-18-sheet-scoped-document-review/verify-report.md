```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:3391fee67c467d6191d4f6f2161c3e905e8423bc63c59ff5640a30c7bf414bfb
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 4/4
scenarios: 13/13
test_command: env GID="$(id -g)" UID="$(id -u)" DOODBA_UMASK=27 docker compose run --rm -e "DB_FILTER='^devel$'" odoo odoo --test-enable --stop-after-init --workers=0 -d devel -u collection --test-tags /collection
test_exit_code: 0
test_output_hash: sha256:f7ddd7f18f98d52e6f5fe688ce990336a5ef67730334672ee25205111d71aa11
build_command: pre-commit run --files odoo/custom/src/private/collection/models/collection_voucher.py odoo/custom/src/private/collection/models/collection_sheet.py odoo/custom/src/private/collection/models/__init__.py odoo/custom/src/private/collection/views/collection_views.xml odoo/custom/src/private/collection/views/collection_document_review_views.xml odoo/custom/src/private/collection/static/src/document_review/document_review_action.esm.js odoo/custom/src/private/collection/tests/test_collection_document_review.py odoo/custom/src/private/collection/tests/test_collection_document_review_flag.py odoo/custom/src/private/collection/tests/test_collection_acl.py odoo/custom/src/private/collection/tests/test_collection_sheet.py odoo/custom/src/private/collection/tests/test_collection_ui.py odoo/custom/src/private/collection/__manifest__.py
build_exit_code: 0
build_output_hash: sha256:80616c04ff2ae8175fb56cb41b0accedbfb2ae9f9dae09967eb80890189615e4
```

## Verification Report

**Change**: sheet-scoped-document-review
**Version**: 19.0.1.11.0
**Mode**: Strict TDD

Independent spec count from retrieved change artifacts (not invented):
`specs/collection-sheets/spec.md` 1 ADDED requirement / 4 scenarios;
`specs/document-review/spec.md` 1 ADDED + 2 MODIFIED requirements / 9 scenarios;
combined **4 requirements / 13 scenarios**. Envelope completed counts are scenarios
with a passing covering test at this runtime.

`evidence_revision` is SHA-256 of exact test stdout+stderr concatenated with exact
build stdout+stderr (no separator).

`invoke img-build` is the config build command but is disproportionate: this change is
Python/XML/JS/tests inside the collection addon, with no new Doodba image
dependencies. Substitute build is scoped `pre-commit run --files` on this change's
production/test sources from Seedian root (not a recursive `collection/**` glob;
archived OpenSpec must not be reformatted). Tests ran via the required Doodba
`docker compose run` command from `/home/crisd/projects/seedian/seedian` with
`-d devel` (not `docker exec --stop-after-init` on live `seedian-odoo-1`).

Seller-lookup tests (`TestCollectionMcpSellerLookup`) ran in the full `/collection`
suite and passed; they are unrelated WIP and are not covering tests for this change's
scenarios. Settings-menu tests in `test_collection_ui.py` were not judged as this
change's covering tests.

Engram MCP was not used; this report is OpenSpec-only.

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 25 |
| Tasks complete | 25 |
| Tasks incomplete | 0 |

Source of completeness: `tasks.md` checkboxes (all `[x]`, 1.1–4.3).
`apply-progress.md` "Remaining Tasks" still lists 4.2 as `[ ]`; that section is stale
relative to `tasks.md` and the Completed Tasks list, which mark 4.2 complete via
scoped pre-commit.

### Build & Tests Execution
**Build**: ✅ Passed
```text
cwd: /home/crisd/projects/seedian/seedian
pre-commit run --files <this-change production/test sources listed in envelope>
exit 0
ruff, ruff-format, prettier+xml, eslint, pylint_odoo mandatory, xml, hygiene: Passed
pylint optional: C8101 manifest-required-author ('Eynes' not present); hook still Passed
```

**Tests**: ✅ 194 passed / ❌ 0 failed / ⚠️ 0 skipped (stats: collection 218 tests)
```text
cwd: /home/crisd/projects/seedian/seedian
env GID="$(id -g)" UID="$(id -u)" DOODBA_UMASK=27 docker compose run --rm -e "DB_FILTER='^devel$'" odoo odoo --test-enable --stop-after-init --workers=0 -d devel -u collection --test-tags /collection
exit 0
odoo.tests.stats: collection: 218 tests 4.54s 6716 queries
odoo.tests.result: 0 failed, 0 error(s) of 194 tests when loading database 'devel'
Covering tests started and completed without FAIL/ERROR, including:
TestCollectionDocumentReview.test_queue_is_isolated_to_requested_sheet
TestCollectionDocumentReview.test_queue_empty_for_sheet_with_no_eligible_members
TestCollectionDocumentReview.test_review_queue_refuses_missing_or_invalid_sheet_id
TestCollectionDocumentReview.test_review_mutations_refuse_missing_or_invalid_sheet_id
TestCollectionDocumentReview.test_cross_sheet_mutations_are_refused
TestCollectionDocumentReview.test_stale_sheet_membership_mutations_are_refused
TestCollectionDocumentReview.test_owl_review_rpcs_pass_sheet_id_from_action_params
TestCollectionDocumentReviewFlag.test_review_rpcs_refuse_when_off_with_or_without_sheet_id
TestCollectionDocumentReviewFlag.test_document_review_xmlids_kept
TestCollectionSheet.test_action_open_document_review_*
TestCollectionUi.test_sheet_form_header_document_review_*
TestCollectionUi.test_load_menus_{omits,includes}_document_review_when_flag_{off,on}
TestCollectionAcl.test_portal_user_review_queue_approve_reject_denied
INFO-level ir_attachment FileNotFoundError traces appeared for pre-existing filestore
paths in the one-off compose run; they did not fail tests.
```

**Coverage**: ➖ Not available — no coverage tool in this Odoo TransactionCase / Doodba
setup (`openspec/config.yaml` testing.coverage.available: false). Not a failure.

### Spec Compliance Matrix
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Saved-sheet header action opens Document Review | Header action available when flag is on | `tests/test_collection_ui.py > test_sheet_form_header_document_review_visible_when_saved_and_flag_on`; `tests/test_collection_sheet.py > test_action_open_document_review_returns_client_action_with_sheet_id` | ✅ COMPLIANT |
| Saved-sheet header action opens Document Review | Header action hidden or refused when flag is off | `tests/test_collection_ui.py > test_sheet_form_header_document_review_hidden_when_flag_off_or_unsaved`; `tests/test_collection_sheet.py > test_action_open_document_review_refused_when_flag_off` | ✅ COMPLIANT |
| Saved-sheet header action opens Document Review | Unsaved sheet must not open review | `tests/test_collection_sheet.py > test_action_open_document_review_refused_on_new_id`; header `invisible="not id or not document_review_enabled"` | ✅ COMPLIANT |
| Saved-sheet header action opens Document Review | Sheet action parameters | `tests/test_collection_sheet.py > test_action_open_document_review_returns_client_action_with_sheet_id`; `test_action_open_document_review_params_match_each_saved_sheet` | ✅ COMPLIANT |
| Sheet identifier required on review operations | Required sheet context | `tests/test_collection_document_review.py > test_review_queue_refuses_missing_or_invalid_sheet_id`; `test_review_mutations_refuse_missing_or_invalid_sheet_id`; `tests/test_collection_document_review_flag.py > test_review_rpcs_refuse_invalid_sheet_id_when_review_on` | ✅ COMPLIANT |
| Sheet identifier required on review operations | Stale membership | `tests/test_collection_document_review.py > test_stale_sheet_membership_mutations_are_refused` | ✅ COMPLIANT |
| Sheet identifier required on review operations | OWL and RPC arguments include the sheet identifier | `tests/test_collection_document_review.py > test_owl_review_rpcs_pass_sheet_id_from_action_params` | ✅ COMPLIANT |
| Eligible review queue | Queue eligibility | `tests/test_collection_document_review.py > test_queue_includes_only_pending_attached_vouchers`; `test_queue_is_isolated_to_requested_sheet` | ✅ COMPLIANT |
| Eligible review queue | Empty queue | `tests/test_collection_document_review.py > test_queue_empty_for_sheet_with_no_eligible_members`; `test_queue_empty_when_no_eligible_vouchers`; empty-state copy in `test_document_review_copy_targets_vouchers_not_lines` | ✅ COMPLIANT |
| Eligible review queue | Cross-sheet isolation | `tests/test_collection_document_review.py > test_queue_is_isolated_to_requested_sheet`; `test_cross_sheet_mutations_are_refused` | ✅ COMPLIANT |
| Document Review menu and RPCs when flag is off | Menu absence | `tests/test_collection_ui.py > test_document_review_menu_and_client_action`; `test_load_menus_omits_document_review_when_flag_off`; `test_load_menus_includes_document_review_when_flag_on`; `tests/test_collection_document_review_flag.py > test_document_review_xmlids_kept` | ✅ COMPLIANT |
| Document Review menu and RPCs when flag is off | Review operations refuse when off | `tests/test_collection_document_review_flag.py > test_review_rpcs_refuse_when_off_with_or_without_sheet_id` (plus per-RPC OFF tests) | ✅ COMPLIANT |
| Document Review menu and RPCs when flag is off | Internal ACL when on | `tests/test_collection_acl.py > test_portal_user_review_queue_approve_reject_denied`; `test_internal_user_review_queue_and_approve_allowed` | ✅ COMPLIANT |

**Compliance summary**: 13/13 scenarios compliant

OWL sheet-id forwarding is covered by source asserts of `orm.call` argument lists
(design Testing Strategy; E2E disabled). Empty client no-remaining-work copy is
source-asserted; server returns `[]` with other-sheet isolation at runtime.

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| Saved-sheet header action opens Document Review | ✅ Implemented | `collection.sheet.action_open_document_review` checks flag then saved id; returns xmlid `collection.action_collection_document_review` with `params.sheet_id`. Header `type="object"` with `invisible="not id or not document_review_enabled"`. Non-stored helper. |
| Sheet identifier required on review operations | ✅ Implemented | Four RPCs call `_require_review_sheet` (flag first, then `int > 0` and `exists()`). Mutations call `_ensure_review_sheet_member`. OWL `reviewSheetId` from `params.sheet_id` only; invalid skips queue. |
| Eligible review queue | ✅ Implemented | `get_review_queue` domain: pending + attached + `sheet_id`. Missing/invalid sheet is `UserError`, not `[]`. Empty eligible sheet returns `[]` with no company-wide fallback. |
| Document Review menu and RPCs when flag is off | ✅ Implemented | Menuitem removed; `<delete model="ir.ui.menu" search="[('name', '=', 'Document Review')]"/>`; `path` cleared; `models/ir_ui_menu.py` deleted. Flag-first refuse on four RPCs. |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| Form object method `action_open_document_review` | ✅ Yes | Sheet form header `type="object"` only |
| Mandatory `params.sheet_id` (not `context.active_id`) | ✅ Yes | Python sets params; OWL getter; tests assert no `active_id` |
| Positional OWL `orm.call` args | ✅ Yes | `get_review_queue([sheetId])`; mutations `[[id], sheetId, ...]` |
| Clear client `path`; leftover URL fail-closed on RPCs | ✅ Yes | `path` empty/False; RPCs refuse without valid sheet / when OFF |
| Remove menuitem and `<delete>` leftover | ✅ Yes | `collection_document_review_views.xml` |
| Delete `_load_menus_blacklist` / `ir_ui_menu.py` | ✅ Yes | File gone; `__init__.py` import dropped |
| Non-stored `document_review_enabled` helper | ✅ Yes | Computed Boolean, `store=False` |
| Manifest `19.0.1.11.0` | ✅ Yes | `__manifest__.py` |
| Apply-progress deviations | ✅ None | Matches design |

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | TDD Cycle Evidence table present in apply-progress |
| All tasks have tests | ✅ | 21/21 behavioral tasks (1.1–3.3) have test files; 3.4/4.1–4.3 are version/upgrade/lint/suite |
| RED confirmed (tests exist) | ✅ | Covering test methods exist in review/flag/acl/sheet/ui files |
| GREEN confirmed (tests pass) | ✅ | Those covering tests started in this runtime and the suite was 0 failed / 0 error(s) |
| Triangulation adequate | ✅ | Two-sheet queues; None/0/False/unknown ids; OFF with/without sheet_id; ON and OFF menu omit; NewId vs saved |
| Safety Net for modified files | ✅ | Phases 1–3 recorded pre-edit green nets; Phase 4 verification-only |

**TDD Compliance**: 6/6 checks passed

---

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 114 | 5 | Odoo TransactionCase (project unit layer) |
| Integration | 0 dedicated files | 0 | Containerized Odoo `-u collection` harness used for this run |
| E2E | 0 | 0 | not installed (testing.e2e.available: false) |
| **Total** | **114** | **5** | |

Files counted (this change's test sources): `test_collection_document_review.py` (36),
`test_collection_document_review_flag.py` (17), `test_collection_acl.py` (11),
`test_collection_sheet.py` (21), `test_collection_ui.py` (29). Includes pre-existing
methods in those files.

---

### Changed File Coverage
Coverage analysis skipped — no coverage tool detected

---

### Assertion Quality
| File | Line | Assertion | Issue | Severity |
|------|------|-----------|-------|----------|
| `tests/test_collection_document_review.py` | 306–310 | `hasattr(Voucher, "get_review_queue")` (and sibling hasattr checks) | Type/existence-only; does not call production review code in this test | WARNING |

**Assertion quality**: 0 CRITICAL, 1 WARNING

Covering tests for spec scenarios assert queue ids, UserError vs `[]`, mutation
refusals without writes, `params.sheet_id` identity, menu absence, and portal
`AccessError`. Empty-queue `[]` asserts have companion non-empty isolation tests.
OWL RPC coverage is source-string matching by design (no browser E2E).

---

### Quality Metrics
**Linter**: ✅ No errors / ⚠️ 1 optional pylint warning (`manifest-required-author` C8101 on `__manifest__.py`; hook Passed)
**Type Checker**: ➖ Not available

### Issues Found
**CRITICAL**: None
**WARNING**:
- `test_review_rpcs_live_on_collection_voucher` uses hasattr-only checks and does not
  itself exercise sheet-scoped RPC behavior (other tests do).
**SUGGESTION**:
- Optional pylint C8101 wants author `Eynes`; addon author is Seedian. Pre-existing /
  repo policy; hook still Passed.
- `apply-progress.md` Remaining Tasks still lists 4.2 unchecked; `tasks.md` is `[x]`.
- One-off compose-run logs INFO filestore FileNotFoundError for pre-existing
  attachments; not a collection test failure.

### Verdict
PASS WITH WARNINGS
All 4 requirements and 13 scenarios have passing covering tests; tasks 25/25 complete;
scoped lint and Doodba `/collection` suite exited 0. Warnings are assertion-quality and
process notes, not spec gaps.
