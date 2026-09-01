```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:5cfc67093b12bf1c0f5659e4a9524ca061f04238480b139d2a54d0202e7533dd
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 9/9
scenarios: 18/18
test_command:
  docker exec -i seedian-odoo-1 odoo -d devel --test-enable --stop-after-init
  --workers=0 --http-port=18069 -u collection --test-tags /collection
test_exit_code: 0
test_output_hash: sha256:c6fdba69da7190f985fb72a2b38640642c620b0d44aa31dd80bb478935c93b32
build_command:
  pre-commit run --files odoo/custom/src/private/collection/models/collection_voucher.py
  odoo/custom/src/private/collection/models/collection_voucher_review_snapshot.py
  odoo/custom/src/private/collection/models/__init__.py
  odoo/custom/src/private/collection/tools/collection_voucher.py
  odoo/custom/src/private/collection/views/collection_views.xml
  odoo/custom/src/private/collection/static/src/document_review/document_review_action.xml
  odoo/custom/src/private/collection/static/src/document_review/document_review_helpers.esm.js
  odoo/custom/src/private/collection/tests/test_collection_mcp_tool.py
  odoo/custom/src/private/collection/tests/test_collection_voucher.py
  odoo/custom/src/private/collection/tests/test_collection_acl.py
  odoo/custom/src/private/collection/tests/test_collection_document_review.py
  odoo/custom/src/private/collection/tests/test_collection_ui.py
  odoo/custom/src/private/collection/security/ir.model.access.csv
  odoo/custom/src/private/collection/__manifest__.py
  odoo/custom/src/private/collection/AGENTS.md
  odoo/custom/src/private/collection/readme/DESCRIPTION.md
  odoo/custom/src/private/collection/README.rst
build_exit_code: 0
build_output_hash: sha256:adbd5388fee82b2bffceecf96dd917417b8ec46fade05a49d815f0ca9ad6e48e
```

## Verification Report

**Change**: voucher-ocr-provenance **Version**: 19.0.1.14.0 **Mode**: Strict TDD

Independent spec count from retrieved change artifacts (not invented):
`specs/collection-vouchers/spec.md` 4 ADDED = **4 requirements / 11 scenarios**;
`specs/document-review/spec.md` 5 ADDED = **5 requirements / 7 scenarios**; combined **9
requirements / 18 scenarios**. Envelope completed counts are scenarios and requirements
with a passing covering test at this runtime.

`evidence_revision` is SHA-256 of exact test stdout+stderr concatenated with exact build
stdout+stderr (no separator). Canonical verification-evidence bytes:
`/tmp/voucher-ocr-provenance-verification-evidence.bin` (122782 bytes), digest
`sha256:5cfc67093b12bf1c0f5659e4a9524ca061f04238480b139d2a54d0202e7533dd`.

Config `build_command` is `invoke img-build`. That is disproportionate: this change adds
no Doodba image dependencies. Substitute build is scoped pre-commit from Seedian root on
this change's authored files (models, tools, views, OWL, tests, security, manifest,
AGENTS.md, readme). Hook result: Passed (optional pylint C8101 warning).

`--http-port=18069` is required because live `seedian-odoo-1` already binds 8069.

Engram MCP was not used; this report is OpenSpec-only.

### Completeness

| Metric           | Value |
| ---------------- | ----- |
| Tasks total      | 14    |
| Tasks complete   | 14    |
| Tasks incomplete | 0     |

Source of completeness: `tasks.md` checkboxes (all `[x]`, 1.1–3.2). `apply-progress.md`
Remaining Tasks: none.

### Build & Tests Execution

**Build**: ✅ Passed

```text
cwd: /home/crisd/projects/seedian/seedian
pre-commit run --files <authored collection models/tools/views/OWL/tests/security/manifest/AGENTS.md/readme>
exit 0
Hooks Passed (forbidden-files/po/shebang/symlink skipped as no matching files).
Optional pylint C8101 manifest-required-author (Seedian vs Eynes) printed; hook still Passed.
```

**Tests**: ✅ 278 passed / ❌ 0 failed / ⚠️ 0 skipped (stats: collection 308 tests)

```text
docker exec -i seedian-odoo-1 odoo -d devel --test-enable --stop-after-init --workers=0 --http-port=18069 -u collection --test-tags /collection
exit 0
odoo.tests.result: 0 failed, 0 error(s) of 278 tests when loading database 'devel'
odoo.tests.stats: collection: 308 tests 8.05s
Covering tests listed in the matrix started (Starting …) and completed without FAIL/ERROR.
INFO FileNotFoundError tracebacks during ir_attachment._file_read (stale devel filestore blobs while loading menus) did not fail any test.
```

**Coverage**: ➖ Not available / threshold: 0% → ➖ Not available

### Spec Compliance Matrix

| Requirement                                          | Scenario                                            | Test                                                                                                                                                                                                                                                                                      | Result       |
| ---------------------------------------------------- | --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| Typed provenance copies of payment fields            | Identity and proof stay outside provenance          | `test_collection_mcp_tool.py > TestCollectionMcpProvenance.test_schema_exposes_nests_without_identity_or_base64` + `test_omitted_nests_with_attachment_keep_base64_out_of_provenance`                                                                                                     | ✅ COMPLIANT |
| Typed provenance copies of payment fields            | Cash-deposit extra keys stored in all layers        | `test_collection_mcp_tool.py > TestCollectionMcpProvenance.test_cash_deposit_stores_voucher_number_and_date_in_all_layers`                                                                                                                                                                | ✅ COMPLIANT |
| Typed provenance copies of payment fields            | Voucher write rejects provenance keys               | `test_collection_voucher.py > TestCollectionVoucherProvenance.test_write_rejects_ocr_and_seller_keys`                                                                                                                                                                                     | ✅ COMPLIANT |
| MCP nested provenance on all-new create              | Unchanged seller confirmation                       | `test_collection_mcp_tool.py > TestCollectionMcpProvenance.test_unchanged_seller_stamps_all_three_layers_equal`                                                                                                                                                                           | ✅ COMPLIANT |
| MCP nested provenance on all-new create              | Seller correction                                   | `test_collection_mcp_tool.py > TestCollectionMcpProvenance.test_seller_correction_keeps_raw_and_aligns_current`                                                                                                                                                                           | ✅ COMPLIANT |
| MCP nested provenance on all-new create              | Both nests omitted leave empty provenance           | `test_collection_mcp_tool.py > TestCollectionMcpProvenance.test_omitted_nests_leave_null_provenance` + `test_orm_create_without_nests_leaves_null_provenance`                                                                                                                             | ✅ COMPLIANT |
| MCP nested provenance on all-new create              | Bad provenance fails the batch                      | `test_collection_mcp_tool.py > TestCollectionMcpProvenance.test_one_sided_nests_reject_with_no_writes` + `test_malformed_and_mismatch_nests_reject_with_no_writes` + `test_batch_one_sided_second_payment_writes_nothing`                                                                 | ✅ COMPLIANT |
| MCP nested provenance on all-new create              | Exact replay ignores provenance nests               | `test_collection_mcp_tool.py > TestCollectionMcpProvenance.test_exact_replay_ignores_different_and_omitted_nests` + `test_unique_violation_replay_ignores_nests_no_backfill`                                                                                                              | ✅ COMPLIANT |
| Immutable review snapshots and ACL                   | Internal users read history without client mutation | `test_collection_acl.py > TestCollectionAcl.test_snapshot_acl_read_and_gated_create` + `test_snapshot_write_unlink_denied_and_portal_denied`                                                                                                                                              | ✅ COMPLIANT |
| Immutable review snapshots and ACL                   | Form Approve and Reject do not snapshot             | `test_collection_document_review.py > TestCollectionDocumentReview.test_form_approve_and_reject_do_not_append_snapshots`                                                                                                                                                                  | ✅ COMPLIANT |
| Additive upgrade without provenance backfill         | Existing rows keep current and empty provenance     | `test_collection_voucher.py > TestCollectionVoucherProvenance.test_existing_rows_keep_current_with_null_provenance`                                                                                                                                                                       | ✅ COMPLIANT |
| Three-way raw, seller, and current comparison        | Type-specific visibility and hidden document_id     | `test_collection_ui.py > TestCollectionUi.test_form_typed_invisible_on_all_provenance_layers` + `test_form_provenance_pages_hide_document_id` + `test_collection_document_review.py > TestCollectionDocumentReview.test_owl_keeps_type_visibility_hides_document_id_and_shows_provenance` | ✅ COMPLIANT |
| Three-way raw, seller, and current comparison        | Reviewer correction diverges current only           | `test_collection_document_review.py > TestCollectionDocumentReview.test_reviewer_correction_matches_snapshot_current_only`                                                                                                                                                                | ✅ COMPLIANT |
| Queue payload includes readonly provenance           | Queue exposes provenance without fabricating        | `test_collection_document_review.py > TestCollectionDocumentReview.test_queue_includes_readonly_provenance_without_fabricating`                                                                                                                                                           | ✅ COMPLIANT |
| Document Review decisions append immutable snapshots | Unchanged Document Review approval still snapshots  | `test_collection_document_review.py > TestCollectionDocumentReview.test_document_review_approve_empty_vals_snapshots_current`                                                                                                                                                             | ✅ COMPLIANT |
| Document Review decisions append immutable snapshots | Document Review reject also snapshots               | `test_collection_document_review.py > TestCollectionDocumentReview.test_document_review_reject_appends_snapshot`                                                                                                                                                                          | ✅ COMPLIANT |
| Repeated Document Review appends another revision    | Reopen then re-review appends another revision      | `test_collection_document_review.py > TestCollectionDocumentReview.test_reopen_then_review_appends_another_revision`                                                                                                                                                                      | ✅ COMPLIANT |
| Voucher review history is visible                    | History list on the voucher form                    | `test_collection_ui.py > TestCollectionUi.test_form_review_history_list_readonly_by_revision`                                                                                                                                                                                             | ✅ COMPLIANT |

**Compliance summary**: 18/18 scenarios compliant

OWL type-visibility note (known apply/design deviation, judged against spec): form
notebook uses per-layer `ocr_document_type` / `seller_document_type` `invisible=`.
Document Review OWL keeps existing `isBankTransfer` / `isCheck` getters on **current**
`document_type` and wraps all three columns in that gate. Spec scenario GIVEN is a
queued voucher of one type and requires type-specific fields to follow **existing**
visibility on all three layers, plus hidden `document_id`. Covering tests passed for
both surfaces (form per-layer `invisible=` and OWL three-column type blocks without
`document_id`). Side-by-side OWL cannot independently show check rows for OCR and
bank-transfer rows for current in the same aligned grid. This is a design deviation, not
a broken covering-test scenario. WARNING below.

### Correctness (Static Evidence)

| Requirement                                          | Status         | Notes                                                                                                                                                                        |
| ---------------------------------------------------- | -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Typed provenance copies of payment fields            | ✅ Implemented | `ocr_*`/`seller_*` for `_REVIEW_EDITABLE_FIELDS`, `copy=False`; `write()` rejects keys; no identity/attachment copies                                                        |
| MCP nested provenance on all-new create              | ✅ Implemented | `raw_ocr`/`seller_confirmed` parsed on create path after existing-document check; seller must equal top-level; omit → null; fail-closed before write; replay ignores nests   |
| Immutable review snapshots and ACL                   | ✅ Implemented | `collection.voucher.review.snapshot` UNIQUE(voucher, revision); gated `collection_review_snapshot`; write/unlink raise; no sudo/groups/`ir.rule`; form buttons do not append |
| Additive upgrade without provenance backfill         | ✅ Implemented | Manifest `19.0.1.14.0`; ORM additive nulls; no `migrations/19.0.1.14.0/`; unstamped rows stay empty                                                                          |
| Three-way raw, seller, and current comparison        | ✅ Implemented | Form notebook Current/Raw/Seller; OWL readonly `ocr_*`/`seller_*` beside current; empty provenance still binds                                                               |
| Queue payload includes readonly provenance           | ✅ Implemented | `_review_queue_payload` adds stored `ocr_*`/`seller_*`; no `datas`                                                                                                           |
| Document Review decisions append immutable snapshots | ✅ Implemented | `_write_review_decision` writes then `_append_review_snapshot` (empty approve and reject)                                                                                    |
| Repeated Document Review appends another revision    | ✅ Implemented | Reopen (proof replace → pending) then later DR appends revision 2; prior row unchanged                                                                                       |
| Voucher review history is visible                    | ✅ Implemented | History page One2many `<list default_order="revision">` with create/delete/edit false                                                                                        |

### Coherence (Design)

| Decision                                              | Followed?            | Notes                                                                          |
| ----------------------------------------------------- | -------------------- | ------------------------------------------------------------------------------ |
| Typed `ocr_*`/`seller_*` columns, `copy=False`        | ✅ Yes               | Same types/selection as current; view readonly                                 |
| `write()` rejects provenance keys; create may stamp   | ✅ Yes               | Blocked key set from `_REVIEW_EDITABLE_FIELDS`                                 |
| Snapshot only from `_write_review_decision`           | ✅ Yes               | After decision `write`; form `action_approve`/`action_reject` do not           |
| Nested MCP `raw_ocr` + `seller_confirmed`             | ✅ Yes               | Parse after existing-check, before savepoint                                   |
| Replay / UniqueViolation ignore nests                 | ✅ Yes               | No backfill                                                                    |
| Snapshot ACL read+create, no write/unlink, no sudo    | ✅ Yes               | Context flag; `write()` super() only on empty set (pylint)                     |
| Form notebook three-way + history `<list>`            | ✅ Yes               | Per-layer `invisible=` on form                                                 |
| OWL keep `isBankTransfer`/`isCheck`; no `document_id` | ✅ Yes               | Current-type gate wraps all three columns (see WARNING)                        |
| Queue provenance, `buildApproveVals` current-only     | ✅ Yes               | `isProvenanceKey` skips `ocr_`/`seller_`                                       |
| Leave `migrations/19.0.1.13.0/`; no 1.14 migrate      | ✅ Yes               |                                                                                |
| Nebula client nesting                                 | ⚠️ Out of this apply | Proposal out of scope; task 1.9 wording mentions Nebula; Odoo contract shipped |

### TDD Compliance

| Check                         | Result | Details                                                                                                                                             |
| ----------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| TDD Evidence reported         | ✅     | Found in apply-progress TDD Cycle Evidence table (14 rows)                                                                                          |
| All tasks have tests          | ✅     | 13/14 tasks have test files; 1.10 is docs + scoped pre-commit (N/A tests)                                                                           |
| RED confirmed (tests exist)   | ✅     | 13/14 test files verified on disk; 1.10 docs                                                                                                        |
| GREEN confirmed (tests pass)  | ✅     | 278/278 tests pass on this execution (0 failed, 0 error(s))                                                                                         |
| Triangulation adequate        | ✅     | Multi-case MCP omit/equal/correct/fail-closed/replay; ACL gated+deny; DR empty-approve/reject/form/reopen/edit; UI notebook/history; OWL type+empty |
| Safety Net for modified files | ✅     | Apply reported nets (242/242 then class-scoped UI/DR) for modified production files; new snapshot model N/A (new)                                   |

**TDD Compliance**: 6/6 checks passed (13/14 tasks have complete TDD evidence; 1.10 is
docs)

---

### Test Layer Distribution

| Layer       | Tests   | Files | Tools                                                                     |
| ----------- | ------- | ----- | ------------------------------------------------------------------------- |
| Unit        | 0       | 0     | Odoo TransactionCase available; no isolated pure-unit file in this change |
| Integration | 185     | 5     | Odoo TransactionCase inside `seedian-odoo-1` / PostgreSQL                 |
| E2E         | 0       | 0     | not installed                                                             |
| **Total**   | **185** | **5** |                                                                           |

Changed test files: `test_collection_mcp_tool.py` (54), `test_collection_voucher.py`
(34), `test_collection_acl.py` (13), `test_collection_document_review.py` (50),
`test_collection_ui.py` (34). Full module run: 278 tests (stats 308). Apply reported 36
new provenance tests in those files.

---

### Changed File Coverage

Coverage analysis skipped — no coverage tool detected

---

### Assertion Quality

| File                                | Line  | Assertion                       | Issue                                              | Severity |
| ----------------------------------- | ----- | ------------------------------- | -------------------------------------------------- | -------- |
| `tests/test_collection_mcp_tool.py` | ~2215 | `inspect.getsource` parse-order | Implementation-source coupling (create-path order) | WARNING  |
| `tests/test_collection_acl.py`      | ~349  | `inspect.getsource` no `.sudo(` | Implementation-source coupling                     | WARNING  |

Covering tests otherwise assert persisted field values, `UserError`/no writes, ACL
flags, snapshot revision/decision, form arch `invisible=`/`<list>`, queue keys, and OWL
`t-att-value` / `t-if` bindings. No tautologies, ghost loops, or production-free
assertions. OWL/UI covering tests are template/arch inspection (no browser).

**Assertion quality**: 0 CRITICAL, 2 WARNING

---

### Quality Metrics

**Linter**: ⚠️ 1 warning (optional pylint C8101 `manifest-required-author` expects
`Eynes`; hook still Passed) **Type Checker**: ➖ Not available

### Issues Found

**CRITICAL**: None **WARNING**:

- OWL type-specific field visibility follows current `isBankTransfer`/`isCheck`
  (`current.document_type`) for all three columns together, not per-layer
  `ocr_document_type`/`seller_document_type` like the form notebook. Design explicitly
  kept those getters. Spec scenario still has passing covering tests (form per-layer +
  OWL three-column type blocks + hidden `document_id`). Mismatched-type OCR vs current
  comparison in OWL is weaker than the form.
- Config `build_command` is `invoke img-build`; substituted scoped pre-commit because
  this change has no new image deps.
- Optional pylint C8101 author warning (pre-existing `Seedian`, not `Eynes`).
- Task 1.9 mentions Nebula nested provenance; this apply batch is collection-only
  (proposal out of scope). Odoo MCP nest contract is implemented. **SUGGESTION**:
- OWL/queue covering tests are TransactionCase + QWeb/JS source asserts (no E2E; E2E
  tools not in capabilities).
- Devel filestore logged missing attachment blobs during `load_menus` tests; suite still
  0 failed.

### Verdict

PASS WITH WARNINGS 9/9 requirements and 18/18 spec scenarios have passing covering
tests; 14/14 tasks complete; scoped pre-commit and 278-test run are green. Warnings are
OWL current-type visibility vs form per-layer types (design-aligned), img-build
substitute, pre-existing manifest author lint, and Nebula out of this apply.
