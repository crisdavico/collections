```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:269cc13a61b49aab9662b57b19927c4f3a09353669dbe4aa1ed8395a12270068
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 4/4
scenarios: 11/11
test_command: invoke test -m collection --mode=update
test_exit_code: 0
test_output_hash: sha256:773f881bb7b431a542357a87a87ad2b7340e447e7188f2123e26b863996b741a
build_command: pre-commit run --files odoo/custom/src/private/collection/models/collection_voucher.py odoo/custom/src/private/collection/static/src/document_review/document_review_action.xml odoo/custom/src/private/collection/static/src/document_review/document_review_action.esm.js odoo/custom/src/private/collection/static/src/document_review/document_review_helpers.esm.js odoo/custom/src/private/collection/static/src/document_review/document_review_action.scss odoo/custom/src/private/collection/tests/test_collection_document_review.py odoo/custom/src/private/collection/tests/test_collection_acl.py odoo/custom/src/private/collection/tests/test_collection_company_migration.py odoo/custom/src/private/collection/__manifest__.py odoo/custom/src/private/collection/AGENTS.md
build_exit_code: 0
build_output_hash: sha256:6e7514a23feeba7eb05aa7a3d80a304045b1b30c4e1e8c62f4718a51aaff659d
```

## Verification Report

**Change**: `document-review-ocr-only`
**Version**: collection `19.0.1.36.0` (no `migrations/19.0.1.36.0/`)
**Mode**: Strict TDD

Independent count from this change's delta only (`openspec/changes/document-review-ocr-only/specs/document-review/spec.md`): **4** `### Requirement:` blocks (1 ADDED + 3 MODIFIED) and **11** `#### Scenario:` blocks. Envelope totals use that count. Completed counts include every scenario with a passing covering test at this runtime (✅ COMPLIANT; none FAILING/UNTESTED).

`evidence_revision` is SHA-256 of exact test stdout+stderr concatenated with exact build stdout+stderr (no separator). `invoke img-build` was not run: this change is Python/JS/XML/SCSS/tests inside the collection addon with no new Doodba image dependencies. Scoped `pre-commit run --files` on this change's touched collection paths is the build/lint stand-in (same pattern as prior document-review verifies). Tests ran from `/home/crisd/projects/seedian/seedian` via `invoke test -m collection --mode=update` (invoke `-d` is `--debugpy`, not database; default db-filter `^devel$`).

Engram was not available; this report is OpenSpec-only. No sheet URL was supplied for manual browser QA.

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 15 |
| Tasks complete | 15 |
| Tasks incomplete | 0 |

Source: `tasks.md` checkboxes 1.1–4.3 all `[x]`. `apply-progress.md` "Status" says 16/16; that is stale relative to the 15 task checkboxes. Full spec verification proceeded.

### Build & Tests Execution
**Build**: ✅ Passed (scoped pre-commit as lint/quality stand-in; `invoke img-build` not run)

```text
cwd: /home/crisd/projects/seedian/seedian
pre-commit run --files <touched collection paths listed in envelope>
exit 0
ruff, ruff-format, prettier+xml, eslint, pylint_odoo mandatory, xml, hygiene: Passed
pylint optional: Passed with C8101 manifest-required-author (Eynes) on __manifest__.py
output sha256:6e7514a23feeba7eb05aa7a3d80a304045b1b30c4e1e8c62f4718a51aaff659d
```

**Tests**: ✅ 749 passed / ❌ 0 failed / ⚠️ 0 skipped

```text
invoke test -m collection --mode=update
odoo.tests.result: 0 failed, 0 error(s) of 749 tests when loading database 'devel'
odoo.tests.stats: collection: 817 tests (framework bookkeeping; authoritative result 749/749)
Covering classes started and finished with no FAIL/ERROR: TestCollectionDocumentReview, TestCollectionUi (form three-way), TestCollectionAcl leftover-vals, TestCollectionVoucherProvenance.write_rejects_ocr_and_seller_keys
output sha256:773f881bb7b431a542357a87a87ad2b7340e447e7188f2123e26b863996b741a
```

**Coverage**: ➖ Not available / threshold: 0 → Coverage analysis skipped — no coverage tool detected

### Spec Compliance Matrix
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Queue payload includes seller_changed_fields | Empty-empty omitted | `tests/test_collection_document_review.py` > `test_queue_seller_changed_fields_omits_empty_empty` | ✅ COMPLIANT |
| Queue payload includes seller_changed_fields | Seller value included including emptied | `test_queue_seller_changed_fields_emptied_seller_is_explicit` + `test_queue_seller_changed_fields_typed_diffs_follow_field_order` | ✅ COMPLIANT |
| OWL client loads real ORM data | Typed editable fields by document type | `test_owl_keeps_type_visibility_hides_document_id_and_shows_provenance` (readonly `ocr_*`, no current/seller widgets, no `t-on-input`) | ✅ COMPLIANT |
| OWL client loads real ORM data | Dual typed groups when seller changed document_type | `test_owl_keeps_type_visibility_hides_document_id_and_shows_provenance` (`_layerHasDocumentType` OCR∪seller; bank + check blocks) | ✅ COMPLIANT |
| OWL client loads real ORM data | Readonly context fields | `test_document_review_hides_document_id` (`voucher_name` / `position` / `total`; no `document_id`) | ✅ COMPLIANT |
| OWL client loads real ORM data | Navigate and next record after decision | `test_owl_review_rpcs_pass_sheet_id_from_action_params` (`loadQueue`, `goPrev` present, approve `[[id], sheetId]`) + `runDecision` `loadQueue({keepIndex: true})` in same source | ✅ COMPLIANT |
| Approve and reject without mocks | Correction persistence on approve | `test_approve_persists_edits_and_records_audit` / `test_approve_persists_check_fields` / `test_approve_persists_cash_deposit_fields` / `test_document_review_approve_empty_vals_snapshots_current` / `test_reviewer_correction_matches_snapshot_current_only` / ACL `test_internal_user_review_queue_and_approve_allowed` | ✅ COMPLIANT |
| Approve and reject without mocks | Reject invokes real action | `test_review_reject_rpc_does_not_exist` + `test_document_review_reject_appends_snapshot` + OWL `assertNotIn("action_review_reject")` | ✅ COMPLIANT |
| Three-way raw, seller, and current comparison | Type-specific visibility and hidden document_id | `tests/test_collection_ui.py` > `test_form_typed_invisible_on_all_provenance_layers` / `test_form_notebook_current_raw_seller_pages` / `test_form_provenance_pages_hide_document_id` / `test_form_cash_deposit_keys_present_on_all_layers` | ✅ COMPLIANT |
| Three-way raw, seller, and current comparison | Reviewer correction diverges current only | `test_form_notebook_current_raw_seller_pages` (current editable) + `test_form_typed_invisible_on_all_provenance_layers` (raw/seller readonly) + `tests/test_collection_voucher.py` > `test_write_rejects_ocr_and_seller_keys` | ✅ COMPLIANT |
| Three-way raw, seller, and current comparison | Document Review OCR-only with seller warnings | `test_owl_keeps_type_visibility_hides_document_id_and_shows_provenance` (`.seller-warning` `role="status"`; no three-way widgets; no `document_id`) + `test_owl_empty_provenance_still_loads` | ✅ COMPLIANT |

**Compliance summary**: 11/11 scenarios compliant

OWL contracts are source-string tested (no Hoot). Per this delta's verify instructions, those passing source tests count as COMPLIANT, not UNTESTED. Browser click-through of viewer/nav was not executed; recorded as WARNING, not CRITICAL.

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| Queue payload includes seller_changed_fields | ✅ Implemented | `_review_seller_changed_fields` iterates `_REVIEW_EDITABLE_FIELD_ORDER`; both-empty omit; else seller raw (`False` / `0.0`) |
| OWL client loads real ORM data | ✅ Implemented | Readonly `ocr_*` inputs; `_layerHasDocumentType` uses `ocr_document_type` ∪ `seller_document_type`; `goPrev`/`goNext`; approve reloads queue |
| Approve and reject without mocks | ✅ Implemented | `action_review_approve` `del vals` then `_write_review_decision()`; `_editable_review_vals` deleted; no `action_review_reject`; OWL `[[id], sheetId]` only |
| Three-way raw, seller, and current comparison | ✅ Implemented | Form notebook unchanged (Current editable, Raw/Seller readonly). OWL is OCR-only plus inline `.seller-warning` |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| `seller_changed_fields` JSON object in field order | ✅ Yes | Tuple order; frozenset derived; empty `{}` |
| Empty/eq helpers (`float_compare` 2dp, Date, exact Char/Selection) | ✅ Yes | `_review_field_is_empty` / `_review_fields_equal` |
| Dual typed groups OCR ∪ seller only | ✅ Yes | Current type omitted from `_layerHasDocumentType` |
| Inline `.seller-warning` `--rose`, `role="status"` | ✅ Yes | SCSS `color: var(--rose)`; emptied formats blank |
| Ignore approve `vals`; drop `_editable_review_vals` / `buildApproveVals` / `onFieldInput` | ✅ Yes | Signature `vals=None` kept unused |
| Manifest bump at apply; no migrate folder | ✅ Yes | `19.0.1.36.0`; receipt views kept |
| Do not edit form / `test_collection_ui.py` / receipts | ✅ Yes | Form three-way covered by existing UI tests that passed this run |

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | Found in `apply-progress.md` TDD Cycle Evidence table |
| All tasks have tests | ✅ | 15/15 tasks name `tests/test_collection_document_review.py` or version/ACL files that exist |
| RED confirmed (tests exist) | ✅ | Queue diff, approve no-rewrite, OWL source, version asserts present |
| GREEN confirmed (tests pass) | ✅ | 749/749 passed this runtime, including all covering names above |
| Triangulation adequate | ✅ | Payload 3 cases; approve nonempty/`{}`/omit; OWL bank+check+cash; version string |
| Safety Net for modified files | ⚠️ | Phase 1 recorded "N/A this batch" on rewritten (modified, not new) `test_collection_document_review.py` |

**TDD Compliance**: 5/6 checks passed (safety-net N/A on a modified file is WARNING)

---

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 0 | 0 | — |
| Integration | 55 | 1 primary (`tests/test_collection_document_review.py`); collateral in `test_collection_acl.py`, `test_collection_company_migration.py` | Odoo TransactionCase + OWL source-string |
| E2E | 0 | 0 | not installed (no Hoot) |
| **Total** | **55** | **1 primary** | |

---

### Changed File Coverage
Coverage analysis skipped — no coverage tool detected

---

### Assertion Quality
**Assertion quality**: ✅ All assertions verify real behavior

Covering tests assert payload maps, unchanged current fields, snapshot `decision`/`amount`, xpath readonly `ocr_*`, missing reject RPC, and form notebook/invisible contracts. OWL xpath loops iterate a fixed 11-name binding tuple after `assertTrue(nodes)`. No tautologies, ghost empty loops, or smoke-only renders.

---

### Quality Metrics
**Linter**: ⚠️ 1 optional warning (pylint_odoo C8101 `manifest-required-author` Eynes); hook Passed, no errors
**Type Checker**: ➖ Not available

### Issues Found
**CRITICAL**: None

**WARNING**:
- Browser/manual sheet URL was not supplied and was not executed. OWL/nav/viewer contracts are source-string tested; this is not CRITICAL.
- Strict TDD safety net for Phase 1 recorded N/A on a modified (not newly created) `tests/test_collection_document_review.py`.
- Optional pylint C8101 on `__manifest__.py` (Eynes author); hook still Passed.
- `apply-progress.md` reports 16/16 tasks; `tasks.md` has 15 `[x]` items (1.1–4.3). Completeness uses `tasks.md`.

**SUGGESTION**:
- Odoo logs duplicate `string=` labels for `ocr_*`/`seller_*` vs current fields (pre-existing provenance copies). Not a delta regression.
- No Hoot/E2E layer; click-through of Document Review remains unexecuted.

### Verdict
PASS WITH WARNINGS
Delta 4/4 requirements and 11/11 scenarios have passing covering tests; scoped pre-commit and `invoke test -m collection --mode=update` both exit 0. Warnings are browser-unexecuted QA, TDD safety-net N/A on a rewritten test file, and optional pylint C8101.
