```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:e2a13adb5ea350bb371809a92b6b4b3290c2dffa088a92d037426786ab47e955
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 11/11
scenarios: 21/21
test_command: invoke test -m collection --mode=update
test_exit_code: 0
test_output_hash: sha256:f04ed81f247e7c2c1687c788bc2b0e722c7d40f5244e8aba229efa4c0f0c09bd
build_command: pre-commit run --files odoo/custom/src/private/collection/models/collection_voucher.py odoo/custom/src/private/collection/models/collection_voucher_line.py odoo/custom/src/private/collection/static/src/document_review/document_review_action.esm.js odoo/custom/src/private/collection/static/src/document_review/document_review_helpers.esm.js odoo/custom/src/private/collection/static/src/document_review/document_review_action.xml odoo/custom/src/private/collection/static/src/document_review/document_review_action.scss odoo/custom/src/private/collection/views/collection_document_review_views.xml odoo/custom/src/private/collection/__manifest__.py odoo/custom/src/private/collection/tests/test_collection_document_review.py odoo/custom/src/private/collection/tests/test_collection_voucher.py odoo/custom/src/private/collection/tests/test_collection_payment.py odoo/custom/src/private/collection/tests/test_collection_ui.py odoo/custom/src/private/collection/tests/test_collection_acl.py odoo/custom/src/private/collection/tests/__init__.py
build_exit_code: 0
build_output_hash: sha256:dcdf27d71cca25335208c3bb7544a0d8acc0d7df394051546b0ee7aefcd2f474
```

## Verification Report

**Change**: document-review-ocr-validation
**Version**: 19.0.1.4.0
**Mode**: Strict TDD

Independent spec count from change deltas: `document-review/spec.md` 5 requirements / 11 scenarios; `collection-vouchers/spec.md` ADDED+MODIFIED 6 requirements / 10 scenarios; combined **11 / 21** (matches orchestrator pre-count). Envelope totals use this count. Envelope completed counts include every scenario with a passing covering test at this runtime (✅ COMPLIANT and ⚠️ PARTIAL). None are UNTESTED or FAILING.

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 18 |
| Tasks complete | 18 |
| Tasks incomplete | 0 |

### Build & Tests Execution
**Build**: ✅ Passed (scoped pre-commit as lint/quality stand-in; `invoke img-build` not run)
```text
pre-commit run --files odoo/custom/src/private/collection/models/collection_voucher.py odoo/custom/src/private/collection/models/collection_voucher_line.py odoo/custom/src/private/collection/static/src/document_review/document_review_action.esm.js odoo/custom/src/private/collection/static/src/document_review/document_review_helpers.esm.js odoo/custom/src/private/collection/static/src/document_review/document_review_action.xml odoo/custom/src/private/collection/static/src/document_review/document_review_action.scss odoo/custom/src/private/collection/views/collection_document_review_views.xml odoo/custom/src/private/collection/__manifest__.py odoo/custom/src/private/collection/tests/test_collection_document_review.py odoo/custom/src/private/collection/tests/test_collection_voucher.py odoo/custom/src/private/collection/tests/test_collection_payment.py odoo/custom/src/private/collection/tests/test_collection_ui.py odoo/custom/src/private/collection/tests/test_collection_acl.py odoo/custom/src/private/collection/tests/__init__.py
exit 0 — all applicable hooks Passed (optional pylint_odoo C8101 manifest-required-author warning; hook Passed)
```

**Tests**: ✅ 103 passed / ❌ 0 failed / ⚠️ 0 skipped
```text
invoke test -m collection --mode=update
odoo.tests.result: 0 failed, 0 error(s) of 103 tests when loading database 'devel'
(odoo.tests.stats: collection: 121 tests — framework bookkeeping; authoritative result 103/103)
compose run used a one-off odoo container (seedian-odoo-run-4c1660576f33); no port conflict with seedian-odoo-1
```

**Coverage**: ➖ Not available / threshold: 0 → Coverage analysis skipped — no coverage tool detected

### Spec Compliance Matrix
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Eligible review queue | Queue eligibility | `tests/test_collection_document_review.py` > `test_queue_includes_only_eligible_pending_attached_new` / `test_queue_orders_pdf_and_png_without_base64` | ✅ COMPLIANT |
| Eligible review queue | Empty queue | `tests/test_collection_document_review.py` > `test_queue_empty_when_no_eligible_lines` (+ empty-state copy in `test_document_review_viewer_has_loading_error_empty_attachment_states`) | ✅ COMPLIANT |
| OWL client loads real ORM data | Typed editable fields by document type | `test_approve_persists_edits_and_records_audit` / `test_approve_persists_check_fields` (server persist); OWL template has typed editors; no Hoot/browser | ⚠️ PARTIAL |
| OWL client loads real ORM data | Readonly context fields | Queue payload asserts `document_id` / `voucher_name` / `position`; XML `readonly` on document_id; no OWL readonly test | ⚠️ PARTIAL |
| OWL client loads real ORM data | Navigate and next record after decision | Queue `position`/`total` in `test_queue_orders_pdf_and_png_without_base64`; OWL `goPrev`/`goNext`/`loadQueue({keepIndex})` untested in browser | ⚠️ PARTIAL |
| Authenticated binary attachment viewer | Image via authenticated binary route | `test_queue_image_payload_is_web_content_url_only` + `test_document_review_viewer_binds_web_content_for_image_and_pdf` (XML `<img>` contract; no browser load) | ⚠️ PARTIAL |
| Authenticated binary attachment viewer | PDF via authenticated binary route | `test_queue_pdf_payload_is_web_content_url_only` + XML `<iframe>` bind in `test_document_review_viewer_binds_web_content_for_image_and_pdf` | ⚠️ PARTIAL |
| Authenticated binary attachment viewer | Viewer loading, error, and empty states | `test_document_review_viewer_has_loading_error_empty_attachment_states` (template copy/classes; no load/error events) | ⚠️ PARTIAL |
| Approve and reject without mocks | Correction persistence on approve | `test_approve_persists_edits_and_records_audit` / `test_approve_persists_check_fields` | ✅ COMPLIANT |
| Approve and reject without mocks | Reject invokes real action | `test_reject_sets_rejected_and_records_audit` / `test_line_reject_rejects_voucher_immediately` | ✅ COMPLIANT |
| Document Review authorization | Non-internal user denied Document Review | `tests/test_collection_acl.py` > `test_portal_user_review_queue_approve_reject_denied` (+ internal approve/reject triangulation) | ✅ COMPLIANT |
| Payment line review status and audit | Default pending including upgrade | `test_review_status_defaults_pending_and_copy_false` | ✅ COMPLIANT |
| Payment line review status and audit | Audit on decision | `test_approve_persists_edits_and_records_audit` / `test_reject_sets_rejected_and_records_audit` | ✅ COMPLIANT |
| Approve may validate voucher when all attached lines approved | Aggregate voucher validation | `test_aggregate_validate_when_all_attached_approved` | ✅ COMPLIANT |
| Line reject immediately rejects voucher | Immediate voucher rejection on line reject | `test_line_reject_rejects_voucher_immediately` | ✅ COMPLIANT |
| Concurrent and stale review attempts | Concurrent or stale review attempt | `test_stale_approve_and_reject_refuse_without_corruption` / `test_stale_review_when_voucher_not_new_or_unattached` | ✅ COMPLIANT |
| Attachment replacement resets review to pending | Attachment replacement resets review status | `test_attachment_write_resets_pending_and_clears_audit` / `test_attachment_write_resets_rejected_line` / `test_write_replace_resets_approved_review_to_pending` / `test_write_replace_resets_rejected_review_to_pending` | ✅ COMPLIANT |
| Voucher state transitions | Validate from new | `tests/test_collection_voucher.py` > `test_action_validate_from_new` / `test_action_validate_allows_unattached_pending_line` | ✅ COMPLIANT |
| Voucher state transitions | Reject from new | `test_action_reject_from_new` | ✅ COMPLIANT |
| Voucher state transitions | Terminal states block transitions | `test_terminal_states_block_validate_and_reject` | ✅ COMPLIANT |
| Voucher state transitions | Validate blocked while attached lines pending | `test_action_validate_blocked_while_attached_pending` / `test_action_validate_blocked_when_attached_line_pending` | ✅ COMPLIANT |

**Compliance summary**: 21/21 scenarios have passing covering tests (15 ✅ COMPLIANT, 6 ⚠️ PARTIAL OWL/viewer; 0 UNTESTED; 0 FAILING)

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| Eligible review queue | ✅ Implemented | `get_review_queue` domain: voucher `new` ∧ `pending` ∧ attachment; payload has no `datas`/`attachment` |
| OWL client loads real ORM data | ✅ Implemented | `orm.call` queue/approve/reject; typed editors by `document_type`; readonly `document_id`; nav + `loadQueue({keepIndex: true})` after decision; mocks dropped |
| Authenticated binary attachment viewer | ✅ Implemented | `/web/content?model=collection.voucher.line&id=…&field=attachment`; `<img>` vs `<iframe>`; loading/error/empty; `sanitizeQueueItem` strips `datas`/`attachment` |
| Approve and reject without mocks | ✅ Implemented | `action_review_approve` / `action_review_reject`; editable field allowlist excludes `document_id` |
| Document Review authorization | ✅ Implemented | Existing `base.group_user` ACL; portal `AccessError` on queue/approve/reject/read |
| Payment line review status and audit | ✅ Implemented | `review_status` default `pending`, `copy=False`; `reviewed_by` / `reviewed_at` on decision |
| Approve may validate voucher when all attached lines approved | ✅ Implemented | `_validate_voucher_if_all_attached_approved`; unattached lines ignored |
| Line reject immediately rejects voucher | ✅ Implemented | Reject writes line then `voucher.action_reject()` when voucher `new` |
| Concurrent and stale review attempts | ✅ Implemented | `FOR UPDATE` + `_ensure_review_eligible` → `UserError` |
| Attachment replacement resets review to pending | ✅ Implemented | Binary write resets `pending` and clears audit |
| Voucher state transitions | ✅ Implemented | `action_validate` calls `_ensure_no_pending_attached_review`; terminal immutability unchanged |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| Review state on line | ✅ Yes | `review_status` + audit on `collection.voucher.line` |
| Queue = new ∧ pending ∧ attachment | ✅ Yes | Search domain in `get_review_queue` |
| Public queue/approve/reject API | ✅ Yes | Thin OWL over model methods |
| Auto validate when all attached approved | ✅ Yes | Last attached approve → `action_validate()` |
| Binary via `/web/content` | ✅ Yes | URL helper; no base64 in queue or OWL state |
| Attachment replace resets pending | ✅ Yes | `_vals_with_review_reset_on_new_attachment` |
| ACL `base.group_user` only | ✅ Yes | No new groups or record rules |
| Additive default `pending` | ✅ Yes | No `migrations/`; manifest `19.0.1.4.0` |
| Menu/tag `collection.document_review` | ✅ Yes | Views kept; xmlid tests passed |

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | TDD Cycle Evidence tables present for Phases 1–4 in apply-progress |
| All tasks have tests | ✅ | 18/18 tasks mapped; RED/GREEN tasks point at real files (`test_collection_document_review.py`, voucher/payment/ui/acl, OWL sources) |
| RED confirmed (tests exist) | ✅ | All listed test files exist under `tests/` |
| GREEN confirmed (tests pass) | ✅ | Full `/collection` suite 103/103 pass on this verify execution |
| Triangulation adequate | ⚠️ | Model/ACL/URL cases triangulated; OWL editor/nav/viewer-load remain single-layer (XML/server) because e2e is unavailable |
| Safety Net for modified files | ✅ | apply-progress recorded baselines before model/OWL/ACL edits; 1.4/2.4/3.3/4.2/4.4 N/A is consistent (GREEN-of-prior, refactor, version, lint) |

**TDD Compliance**: 5/6 checks passed (triangulation ⚠️ for OWL client)

---

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 78 in change-related files (19 document_review + 7 acl + 19 ui + 18 voucher + 15 payment) | 5 | Odoo TransactionCase |
| Integration | 103 module tests (full suite) | 7 test modules under `tests/` | Containerized Odoo + PostgreSQL (`invoke test`) |
| E2E | 0 | 0 | not installed (`e2e: false`) |
| **Total** | **103** | **7** | |

---

### Changed File Coverage
Coverage analysis skipped — no coverage tool detected

---

### Assertion Quality
| File | Line | Assertion | Issue | Severity |
|------|------|-----------|-------|----------|
| `tests/test_collection_document_review.py` | 304–306 | `assertIn("viewer-loading"/"viewer-error"/"viewer-empty", xml)` | CSS class / implementation-detail coupling (copy assertions in the same test are behavioral) | WARNING |

**Assertion quality**: 0 CRITICAL, 1 WARNING

Empty-queue `assertEqual(queue, [])` has companion non-empty eligibility tests. Approve/reject/ACL/guard tests assert concrete field values and `UserError`. No tautologies or ghost loops found.

---

### Quality Metrics
**Linter**: ⚠️ 1 pre-existing optional warning (C8101 `manifest-required-author` missing `'Eynes'`); hook Passed / 0 errors
**Type Checker**: ➖ Not available

### Issues Found
**CRITICAL**: None

**WARNING**:
1. Six OWL/browser scenarios are ⚠️ PARTIAL: typed editors, readonly context, navigation/next-after-decision, image render, PDF render, and viewer loading/error/empty. Covering tests passed (server payload, XML contract, filename/URL helpers) but `openspec/config.yaml` has `e2e: false` — no Hoot/tour/browser execution of img/iframe load or editor/nav interaction.
2. Strict TDD triangulation for Phase 2 OWL (tasks 2.2/2.3) is weaker than apply-progress implies: bank/check persist and menu/tag tests passed; cash-only editor set and client nav/next-after-decision have no dedicated test cases.
3. Viewer state test asserts CSS class names (`viewer-loading`, `viewer-error`, `viewer-empty`) in addition to user-visible copy.

**SUGGESTION**:
1. Optional pylint_odoo C8101 (`manifest-required-author`) remains pre-existing; not introduced by this change.
2. ruff-format would wrap a few long lines in `models/collection_voucher_line.py` and `tests/test_collection_document_review.py`; auto-fixes from this verify run were reverted (report-only).
3. If OWL client behavior must be fully COMPLIANT later, add Hoot unit tests or an HttpCase tour; that is out of this change’s stated test strategy.

### Verdict
PASS WITH WARNINGS
All 18 tasks complete; 103/103 collection tests passed; 21/21 scenarios have passing covering tests (15 fully COMPLIANT, 6 OWL/viewer PARTIAL because e2e is unavailable). No blockers or critical findings.
