```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:b4f2de5457d142b5199a8f2fa4d582073cbea0dfcb21fa5e98c5600a6bda9ec6
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 4/4
scenarios: 9/9
test_command: invoke test -m collection --mode=update
test_exit_code: 0
test_output_hash: sha256:c9d3f13c2adb28dfb253f6ef4b67ff9431b54b1d2d18601cd6b2cbf93276f1f0
build_command:
  pre-commit run --files
  odoo/custom/src/private/collection/models/collection_voucher_line.py
  odoo/custom/src/private/collection/tools/collection_voucher.py
  odoo/custom/src/private/collection/views/collection_views.xml
  odoo/custom/src/private/collection/tests/test_collection_payment.py
  odoo/custom/src/private/collection/tests/test_collection_ui.py
  odoo/custom/src/private/collection/tests/test_collection_mcp_tool.py
  odoo/custom/src/private/collection/__manifest__.py
  odoo/custom/src/private/collection/AGENTS.md
build_exit_code: 0
build_output_hash: sha256:6d98425e46215f4f2b8fab3b881780878ec26c619632f3a7e86c4ee851b21809
```

## Verification Report

**Change**: voucher-line-attachments **Version**: 19.0.1.3.0 **Mode**: Strict TDD

### Completeness

| Metric           | Value |
| ---------------- | ----- |
| Tasks total      | 14    |
| Tasks complete   | 14    |
| Tasks incomplete | 0     |

### Build & Tests Execution

**Build**: ✅ Passed (scoped pre-commit as lint/quality stand-in; no separate typecheck)

```text
pre-commit run --files odoo/custom/src/private/collection/models/collection_voucher_line.py odoo/custom/src/private/collection/tools/collection_voucher.py odoo/custom/src/private/collection/views/collection_views.xml odoo/custom/src/private/collection/tests/test_collection_payment.py odoo/custom/src/private/collection/tests/test_collection_ui.py odoo/custom/src/private/collection/tests/test_collection_mcp_tool.py odoo/custom/src/private/collection/__manifest__.py odoo/custom/src/private/collection/AGENTS.md
exit 0 — all hooks Passed (optional pylint_odoo C8101 manifest-required-author warning; hook Passed)
```

**Tests**: ✅ 75 passed / ❌ 0 failed / ⚠️ 0 skipped

```text
invoke test -m collection --mode=update
odoo.tests.result: 0 failed, 0 error(s) of 75 tests when loading database 'devel'
(odoo.tests.stats: collection: 91 tests — framework bookkeeping; authoritative result 75/75)
```

**Coverage**: ➖ Not available / threshold: 0 → Coverage analysis skipped — no coverage
tool detected

### Spec Compliance Matrix

| Requirement                                         | Scenario                                | Test                                                                                                                                                                                                                       | Result       |
| --------------------------------------------------- | --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| Optional image or PDF attachment per payment line   | Omit attachment valid                   | `tests/test_collection_payment.py` > `TestCollectionPaymentAttachment.test_omit_attachment_persists`                                                                                                                       | ✅ COMPLIANT |
| Optional image or PDF attachment per payment line   | Valid file persists                     | `tests/test_collection_payment.py` > `test_valid_png_persists_via_ir_attachment` / `test_valid_pdf_persists_via_ir_attachment`                                                                                             | ✅ COMPLIANT |
| Optional image or PDF attachment per payment line   | Invalid content rejected                | `tests/test_collection_payment.py` > `test_invalid_base64_raises_and_does_not_persist` / `test_non_image_non_pdf_mime_raises_and_does_not_persist`                                                                         | ✅ COMPLIANT |
| Attachment widgets on typed and Payment Lines views | Typed tables show Binary widgets        | `tests/test_collection_ui.py` > `test_typed_lists_include_attachment_binary_widgets` / `test_typed_and_payment_lists_attachment_accept_is_image_and_pdf`                                                                   | ✅ COMPLIANT |
| Attachment widgets on typed and Payment Lines views | Payment Lines views show Binary widgets | `tests/test_collection_ui.py` > `test_payment_lines_list_includes_attachment_binary_widget` / accept triangulation                                                                                                         | ✅ COMPLIANT |
| MCP optional payment attachment on create           | MCP create with nested attachment       | `tests/test_collection_mcp_tool.py` > `test_create_with_valid_png_nest_persists_atomically` / `test_create_with_valid_pdf_nest_persists`                                                                                   | ✅ COMPLIANT |
| MCP optional payment attachment on create           | MCP attachment MIME mismatch rejected   | `tests/test_collection_mcp_tool.py` > `test_create_mime_mismatch_rejects_no_writes` / `test_create_bad_base64_rejects_no_writes` / `test_create_text_mime_rejects_no_writes`                                               | ✅ COMPLIANT |
| MCP optional payment attachment on create           | Exact-retry skips attachment writes     | `tests/test_collection_mcp_tool.py` > `test_exact_retry_with_nest_does_not_replace_attachment` / `test_exact_retry_with_nest_does_not_add_when_line_has_none` / `test_exact_retry_without_nest_leaves_existing_attachment` | ✅ COMPLIANT |
| Deferred integrations not required                  | Completeness without deferred features  | `tests/test_collection_voucher.py` lifecycle (create/validate/reject without attachments) + `test_omit_attachment_persists` + `test_create_omitting_nest_still_creates`                                                    | ✅ COMPLIANT |

**Compliance summary**: 9/9 scenarios compliant

### Correctness (Static Evidence)

| Requirement                                         | Status         | Notes                                                                                                                                                              |
| --------------------------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Optional image or PDF attachment per payment line   | ✅ Implemented | `attachment` Binary(`attachment=True`, `copy=False`) + `attachment_filename`; `_validate_attachment_payload` + `@api.constrains` + create/write gate → `UserError` |
| Attachment widgets on typed and Payment Lines views | ✅ Implemented | Binary widgets + `accepted_file_extensions: image/*,.pdf` on 3 typed lists and Payment Lines list (`view_mode=list` only)                                          |
| MCP optional payment attachment on create           | ✅ Implemented | Optional nest `{name,mimetype,datas}` enrich only on all-new path; declared MIME must match detected; replay ignores nest; no `sudo()`                             |
| Deferred integrations not required                  | ✅ Implemented | Attachments remain optional; voucher CRUD/validate/reject succeed without files                                                                                    |

### Coherence (Design)

| Decision                                    | Followed?  | Notes                                                                                                                                                          |
| ------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Storage Binary + Char filename              | ✅ Yes     | `attachment` / `attachment_filename`                                                                                                                           |
| Names avoid `datas` clash                   | ✅ Yes     | Former naming chosen                                                                                                                                           |
| Validation via guess_mimetype + b64decode   | ✅ Yes     | Shared helper; allow `image/*` or `application/pdf`                                                                                                            |
| Hook `@api.constrains('attachment')`        | ⚠️ Partial | Constrains kept; also create/write pre-check so bad base64 surfaces as `UserError` before `ir.attachment` raises `binascii.Error` (documented apply deviation) |
| MCP nest validate create-only after all-new | ✅ Yes     | Enrich after existing check; replay ignores nest                                                                                                               |
| Nest shape `{name,mimetype,datas}`          | ✅ Yes     | Schema + parse helpers                                                                                                                                         |
| UI accept `image/*,.pdf`                    | ✅ Yes     | All four lists                                                                                                                                                 |
| Payment Lines list-only                     | ✅ Yes     | Action `view_mode=list`; no new form (matches design/tasks)                                                                                                    |
| Manifest `19.0.1.3.0`                       | ✅ Yes     | Confirmed in `__manifest__.py`                                                                                                                                 |

### TDD Compliance

| Check                         | Result | Details                                                                                      |
| ----------------------------- | ------ | -------------------------------------------------------------------------------------------- |
| TDD Evidence reported         | ✅     | Found TDD Cycle Evidence table in apply-progress                                             |
| All tasks have tests          | ✅     | 14/14 tasks mapped; RED tasks point at real test files                                       |
| RED confirmed (tests exist)   | ✅     | `test_collection_payment.py`, `test_collection_ui.py`, `test_collection_mcp_tool.py` present |
| GREEN confirmed (tests pass)  | ✅     | Full suite 75/75 pass on verify execution                                                    |
| Triangulation adequate        | ✅     | PNG+PDF, bad b64+MIME, typed×3+Payment Lines, MCP retry with/without nest                    |
| Safety Net for modified files | ✅     | RED tasks recorded baseline suite runs before modification                                   |

**TDD Compliance**: 6/6 checks passed

---

### Test Layer Distribution

| Layer       | Tests                                        | Files                                                                                    | Tools                                           |
| ----------- | -------------------------------------------- | ---------------------------------------------------------------------------------------- | ----------------------------------------------- |
| Unit        | 21 new attachment-focused (+ existing suite) | 3 (`test_collection_payment.py`, `test_collection_ui.py`, `test_collection_mcp_tool.py`) | Odoo TransactionCase                            |
| Integration | 75 module tests (full suite)                 | 6 test modules under `tests/`                                                            | Containerized Odoo + PostgreSQL (`invoke test`) |
| E2E         | 0                                            | 0                                                                                        | not installed                                   |
| **Total**   | **75**                                       | **6**                                                                                    |                                                 |

---

### Changed File Coverage

Coverage analysis skipped — no coverage tool detected

---

### Assertion Quality

**Assertion quality**: ✅ All assertions verify real behavior

Reviewed new/changed attachment tests: omit/valid/invalid persistence, UI arch
widget+accept checks, MCP atomic create, MIME/base64 reject with no-writes counters, and
exact-retry no-add/replace/compare. No tautologies, ghost loops, or smoke-only asserts
found.

---

### Quality Metrics

**Linter**: ⚠️ 1 pre-existing optional warning (C8101 `manifest-required-author` missing
`'Eynes'`); hook Passed / 0 errors **Type Checker**: ➖ Not available

### Issues Found

**CRITICAL**: None

**WARNING**:

1. Design preferred validation solely via `@api.constrains('attachment')`;
   implementation also pre-validates in `create`/`write` so invalid base64 raises
   `UserError` before `ir.attachment` raises `binascii.Error`. Spec contract
   (`UserError`, no persist) still holds — documented deviation only.
2. Delta scenario wording mentions Payment Lines "list or form"; design/tasks
   intentionally ship list-only (`view_mode=list`). List coverage exists and passed; no
   form view was added.

**SUGGESTION**:

1. Optional pylint_odoo C8101 (`manifest-required-author`) remains pre-existing; not
   introduced by this change.
2. Prefer `invoke test -m collection --mode=update` (or `-u`) on an already-installed
   module; default `--mode=init` can report 0 tests.

### Verdict

PASS WITH WARNINGS All 4 requirements / 9 scenarios are COMPLIANT with passing runtime
tests; two non-blocking design/wording deviations remain documented.
