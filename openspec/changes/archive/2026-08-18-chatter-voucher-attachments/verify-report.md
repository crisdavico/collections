```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:946a2f6292016b15c37be83627325659427878f36d55b97f93819a85bbfc54d0
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 10/10
scenarios: 26/26
test_command: docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection,-/collection:TestCollectionMcpProvenance,-/collection:TestCollectionVoucherProvenance,-/collection:TestCollectionAcl.test_snapshot_acl_read_and_gated_create,-/collection:TestCollectionAcl.test_snapshot_write_unlink_denied_and_portal_denied,-/collection:TestCollectionDocumentReview.test_document_review_approve_empty_vals_snapshots_current,-/collection:TestCollectionDocumentReview.test_document_review_reject_appends_snapshot,-/collection:TestCollectionDocumentReview.test_form_approve_and_reject_do_not_append_snapshots,-/collection:TestCollectionDocumentReview.test_reopen_then_review_appends_another_revision,-/collection:TestCollectionDocumentReview.test_reviewer_correction_matches_snapshot_current_only
test_exit_code: 0
test_output_hash: sha256:6c81a12a1befb3b4b52d773e2e362b013cb80ae663494e5cfc8829b353b6a565
build_command: docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --workers=0 --http-port=18069
build_exit_code: 0
build_output_hash: sha256:b68a0a248cc0b063c325976fb607ec0a26e3558d292df0876185201966abc44f
```

## Verification Report

**Change**: chatter-voucher-attachments
**Version**: 19.0.1.13.0
**Mode**: Strict TDD

Independent spec count from retrieved change artifacts (not invented):
`specs/collection-vouchers/spec.md` 2 ADDED + 5 MODIFIED = **7 requirements / 16 scenarios**;
`specs/document-review/spec.md` 3 MODIFIED = **3 requirements / 10 scenarios**;
combined **10 requirements / 26 scenarios**. Envelope completed counts are scenarios
with a passing covering test at this runtime.

`evidence_revision` is SHA-256 of exact test stdout+stderr concatenated with exact
build stdout+stderr (no separator).

`invoke img-build` is the config build command but is disproportionate: this change is
Python/XML/tests/migrations inside the collection addon, with no new Doodba image
dependencies. Substitute build is module-load
`docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --workers=0 --http-port=18069`
(exit 0; module `collection` loaded; no Traceback). `--http-port=18069` is required
because live `seedian-odoo-1` already binds 8069.

First `invoke test -m collection --mode=update` from Seedian root exited 1
(`9 failed, 10 error(s) of 257 tests`) because the worktree contains uncommitted
`voucher-ocr-provenance` WIP (`TestCollectionMcpProvenance`, snapshot/provenance
methods). Those failures are outside this change. Authoritative runtime for this
change excluded that WIP and reproduced apply-progress: **0 failed, 0 error(s) of 242 tests**.

Engram MCP was not used; this report is OpenSpec-only.

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 21 |
| Tasks complete | 21 |
| Tasks incomplete | 0 |

Source of completeness: `tasks.md` checkboxes (all `[x]`, 1.1–4.3).
`apply-progress.md` Remaining Tasks: none.

### Build & Tests Execution
**Build**: ✅ Passed
```text
cwd: /home/crisd/projects/seedian/seedian
docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --workers=0 --http-port=18069
exit 0
Module collection loaded in 0.81s; Modules loaded; Initiating shutdown; no Traceback
```

**Tests**: ✅ 242 passed / ❌ 0 failed / ⚠️ 0 skipped (stats: collection 268 tests)
```text
docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection plus exclusions for uncommitted provenance/snapshot methods
exit 0
odoo.tests.result: 0 failed, 0 error(s) of 242 tests when loading database 'devel'
Covering tests started and completed without FAIL/ERROR, including the matrix below.
```

**Coverage**: ➖ Not available / threshold: 0% → ➖ Not available

### Spec Compliance Matrix
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Designated proof is message_main_attachment_id | MCP nest becomes designated proof | `test_collection_mcp_tool.py > TestCollectionMcpAttachment.test_create_with_valid_png_nest_becomes_chatter_proof` | ✅ COMPLIANT |
| Designated proof is message_main_attachment_id | Extra files do not steal proof | `test_collection_mail.py > TestCollectionMail.test_extra_chatter_file_does_not_steal_proof` | ✅ COMPLIANT |
| Designated proof is message_main_attachment_id | Non-image extra cannot become proof | `test_collection_mail.py > TestCollectionMail.test_non_image_extra_cannot_become_proof` | ✅ COMPLIANT |
| Pre-upgrade migration of Binary proofs | Binary field attachment migrates | `test_collection_voucher.py > TestCollectionVoucherAttachmentMigrate.test_binary_field_attachment_migrates_to_chatter_main` | ✅ COMPLIANT |
| Pre-upgrade migration of Binary proofs | Empty filename fallback | `test_collection_voucher.py > TestCollectionVoucherAttachmentMigrate.test_empty_filename_falls_back_to_proof_bin` | ✅ COMPLIANT |
| Optional image or PDF attachment per voucher | Omit attachment valid | `test_collection_voucher.py > TestCollectionVoucher.test_omit_proof_remains_valid` | ✅ COMPLIANT |
| Optional image or PDF attachment per voucher | Valid file persists | `test_collection_payment.py > TestCollectionPaymentAttachment.test_valid_png_persists_via_ir_attachment` | ✅ COMPLIANT |
| Optional image or PDF attachment per voucher | Invalid content rejected | `test_collection_voucher.py > TestCollectionVoucher.test_invalid_main_attachment_raises_user_error` | ✅ COMPLIANT |
| Attachment widgets on Payment Vouchers views | Payment Vouchers views omit Binary widgets | `test_collection_ui.py > TestCollectionUi.test_payment_vouchers_views_omit_binary_widgets` | ✅ COMPLIANT |
| MCP optional payment attachment on create | MCP create with nested attachment | `test_collection_mcp_tool.py > TestCollectionMcpAttachment.test_create_with_valid_png_nest_becomes_chatter_proof` | ✅ COMPLIANT |
| MCP optional payment attachment on create | MCP attachment MIME mismatch rejected | `test_collection_mcp_tool.py > TestCollectionMcpAttachment.test_create_mime_mismatch_rejects_no_writes` | ✅ COMPLIANT |
| MCP optional payment attachment on create | Exact-retry skips attachment writes | `test_collection_mcp_tool.py > TestCollectionMcpAttachment.test_exact_retry_with_nest_does_not_replace_attachment` | ✅ COMPLIANT |
| Concurrent and stale review attempts | Concurrent or stale review attempt | `test_collection_document_review.py > TestCollectionDocumentReview.test_stale_review_when_designated_proof_missing` | ✅ COMPLIANT |
| Attachment replacement resets review to pending | Attachment replacement resets voucher state | `test_collection_voucher.py > TestCollectionVoucher.test_replace_main_resets_pending_clears_audit_and_rotation` | ✅ COMPLIANT |
| Attachment replacement resets review to pending | Extra chatter files do not reset review | `test_collection_voucher.py > TestCollectionVoucher.test_extra_chatter_does_not_reset_review_or_rotation` | ✅ COMPLIANT |
| Attachment replacement resets review to pending | Clearing proof does not reopen | `test_collection_voucher.py > TestCollectionVoucher.test_clear_main_resets_rotation_keeps_decided` | ✅ COMPLIANT |
| Eligible review queue | Queue eligibility | `test_collection_document_review.py > TestCollectionDocumentReview.test_queue_includes_only_pending_attached_vouchers` | ✅ COMPLIANT |
| Eligible review queue | Empty queue | `test_collection_document_review.py > TestCollectionDocumentReview.test_queue_empty_for_sheet_with_no_eligible_members` | ✅ COMPLIANT |
| Eligible review queue | Cross-sheet isolation | `test_collection_document_review.py > TestCollectionDocumentReview.test_cross_sheet_mutations_are_refused` | ✅ COMPLIANT |
| Authenticated binary attachment viewer | Image via authenticated binary route | `test_collection_document_review.py > TestCollectionDocumentReview.test_queue_image_payload_is_web_content_url_only` | ✅ COMPLIANT |
| Authenticated binary attachment viewer | PDF via authenticated binary route | `test_collection_document_review.py > TestCollectionDocumentReview.test_queue_pdf_payload_is_web_content_url_only` | ✅ COMPLIANT |
| Authenticated binary attachment viewer | Viewer loading, error, and empty states | `test_collection_document_review.py > TestCollectionDocumentReview.test_document_review_viewer_has_loading_error_empty_attachment_states` | ✅ COMPLIANT |
| Viewer rotation | Rotate clockwise and counterclockwise | `test_collection_document_review.py > TestCollectionDocumentReview.test_document_review_viewer_rotate_buttons` | ✅ COMPLIANT |
| Viewer rotation | Restore saved rotation | `test_collection_document_review.py > TestCollectionDocumentReview.test_set_rotation_persists_and_returns_in_queue` | ✅ COMPLIANT |
| Viewer rotation | Attachment replace resets rotation | `test_collection_document_review.py > TestCollectionDocumentReview.test_attachment_write_resets_rotation` | ✅ COMPLIANT |
| Viewer rotation | Extra chatter files do not reset rotation | `test_collection_document_review.py > TestCollectionDocumentReview.test_extra_chatter_files_do_not_reset_rotation` | ✅ COMPLIANT |

**Compliance summary**: 26/26 scenarios compliant

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| Designated proof is message_main_attachment_id | ✅ Implemented | Mixin `mail.thread.main.attachment`; picker filters image/* + PDF |
| Pre-upgrade migration of Binary proofs | ✅ Implemented | `migrations/19.0.1.13.0` pre nulls `res_field`, post sets main |
| Optional image or PDF attachment per voucher | ✅ Implemented | Binary fields dropped; chatter `ir.attachment` with empty `res_field` |
| Attachment widgets on Payment Vouchers views | ✅ Implemented | No Binary widgets; `<chatter open_attachments="True"/>` |
| MCP optional payment attachment on create | ✅ Implemented | Savepoint `message_post`; exact-retry ignores nests |
| Concurrent and stale review attempts | ✅ Implemented | Eligibility `pending` + `message_main_attachment_id` |
| Attachment replacement resets review to pending | ✅ Implemented | Write-reset on main id change; extras/clear as specified |
| Eligible review queue | ✅ Implemented | Queue filters pending + designated proof, sheet-scoped |
| Authenticated binary attachment viewer | ✅ Implemented | `_attachment_content_url` → `/web/content/{id}`; no `field=` |
| Viewer rotation | ✅ Implemented | Keep `attachment_rotation`; reset 0 on main change or clear |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| Proof pointer = `message_main_attachment_id` | ✅ Yes | Mixin inherit; Binary dropped |
| Picker override image/* + PDF | ✅ Yes | `_message_set_main_attachment_id` filters MIME |
| Extras `force=False` never steal | ✅ Yes | Covered by mail/voucher tests |
| MCP persist via `message_post` after create | ✅ Yes | Savepoint; nest schema unchanged |
| Review URL `/web/content/{id}` | ✅ Yes | No `field=attachment` |
| Rotation reset on main change or clear | ✅ Yes | Clear does not reopen decided |
| OWL unchanged (binds `current.attachment_url`) | ✅ Yes | Apply deviation: no `static/src/document_review/*` edit |
| In-place `datas` write residual | ✅ Yes | Accepted; no hook |

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | Found in apply-progress TDD Cycle Evidence table |
| All tasks have tests | ✅ | 17/21 tasks have test files; 4.1 upgrade, 4.2 lint, 3.3 docs, 1.11 helpers are N/A |
| RED confirmed (tests exist) | ✅ | 19/19 TDD-table rows point at existing test files or N/A docs/helpers |
| GREEN confirmed (tests pass) | ✅ | 242/242 tests pass on scoped execution |
| Triangulation adequate | ✅ | Multi-case for proof/MCP/review/migration; singles match single-scenario specs |
| Safety Net for modified files | ✅ | Apply reported nets for voucher/mail/UI/MCP/review; 1.5 new class N/A |

**TDD Compliance**: 6/6 checks passed (19/21 tasks have complete TDD evidence; 4.1–4.2 are upgrade/lint)

---

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 242 | 10 | Odoo TransactionCase |
| Integration | 0 | 0 | Containerized Odoo with PostgreSQL (TransactionCase runs inside it) |
| E2E | 0 | 0 | not installed |
| **Total** | **242** | **10** | |

HEAD test methods in this change's edited test files: voucher 31, mail 7, ui 29, mcp_tool 39, document_review 39, payment 15, acl 11, document_review_flag 17.

---

### Changed File Coverage
Coverage analysis skipped — no coverage tool detected

---

### Assertion Quality
**Assertion quality**: ✅ All assertions verify real behavior

Covering tests assert designated proof identity, MIME/`UserError`, `/web/content/{id}` (no `field=`), state/audit/rotation, chatter extras, and migrate filename fallback. No tautologies, ghost loops, or production-free assertions in this change's covering tests.

---

### Quality Metrics
**Linter**: ⚠️ 1 warning (optional pylint C8101 `manifest-required-author` expects `Eynes`; hook still Passed)
**Type Checker**: ➖ Not available

### Issues Found
**CRITICAL**: None
**WARNING**:
- Config `build_command` is `invoke img-build`; substituted module-load upgrade because this change has no new image deps. Tests prove the upgraded module.
- Worktree is dirty with uncommitted `voucher-ocr-provenance` tests/code. Bare `invoke test -m collection --mode=update` exited 1 (9 failed / 10 errors). Scoped exclusions restored this change's 242-test green suite. Do not archive while mixing that WIP into a chatter-only commit unless intended.
- Optional pylint C8101 author warning (pre-existing `Seedian`, not `Eynes`).
**SUGGESTION**:
- Viewer rotate/load/empty coverage is TransactionCase + QWeb/JS string checks (no E2E; E2E tools not in capabilities).

### Verdict
PASS WITH WARNINGS
26/26 spec scenarios have passing covering tests; 21/21 tasks complete; module-load and scoped 242-test run are green. Warnings are img-build substitute, dirty-tree invoke contamination, and pre-existing manifest author lint.
