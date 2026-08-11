# Apply Progress: voucher-line-attachments

**Mode**: Strict TDD **Last updated**: 2026-08-11 **Active work unit completed**: Phase
4 — Quality gate (tasks 4.1–4.2); all work units done

## Completed Tasks

- [x] 1.1 RED: payment attachment omit/valid/invalid tests
- [x] 1.2 RED: replace/clear/unlink/`copy=False` tests
- [x] 1.3 GREEN: Binary+filename fields + MIME/base64 validation
- [x] 1.4 GREEN: manifest `19.0.1.3.0`
- [x] 1.5 Verify: install + payment/module tests green
- [x] 2.1 RED: UI arch tests for typed + Payment Lines attachment widgets
- [x] 2.2 GREEN: binary widgets on three typed lists + Payment Lines list
- [x] 2.3 Verify: install + UI/module tests green
- [x] 3.1 RED: MCP create with valid nest / omit / MIME+b64 reject tests
- [x] 3.2 RED: MCP exact-retry attachment unchanged (with/without nest) tests
- [x] 3.3 GREEN: optional `{name,mimetype,datas}` create-only map; replay ignores nest
- [x] 3.4 Verify: install + full module tests green
- [x] 4.1 Quality gate: scoped pre-commit on collection paths — Passed
- [x] 4.2 Quality gate: `invoke test -m collection --mode=update` — 0 failed, 0 error(s)
      of 75 tests

## TDD Cycle Evidence

| Task | Test File                           | Layer                       | Safety Net                                           | RED                                                                  | GREEN                                                                                                                  | TRIANGULATE                                                                    | REFACTOR                                                                                                                      |
| ---- | ----------------------------------- | --------------------------- | ---------------------------------------------------- | -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| 1.1  | `tests/test_collection_payment.py`  | Unit (TransactionCase)      | ✅ 54/54 (`invoke test -m collection --mode=update`) | ✅ Written (omit/PNG/PDF/bad b64/bad MIME) → 9 ERROR AttributeError  | ✅ Passed after 1.3                                                                                                    | ✅ PNG + PDF; bad b64 + text MIME                                              | ✅ Shared helpers/constants                                                                                                   |
| 1.2  | `tests/test_collection_payment.py`  | Unit (TransactionCase)      | ✅ same baseline                                     | ✅ Written (replace/clear/unlink/copy)                               | ✅ Passed after 1.3                                                                                                    | ✅ replace PNG→PDF + clear empty path                                          | ✅ Shared `_line_attachments` helper                                                                                          |
| 1.3  | `tests/test_collection_payment.py`  | Unit (TransactionCase)      | ✅ N/A (implementation)                              | covered by 1.1–1.2 RED                                               | ✅ 13/13 payment tests                                                                                                 | covered by multi-case suite                                                    | ✅ `_validate_attachment_payload` + create/write pre-check                                                                    |
| 1.4  | N/A (manifest bump)                 | Structural                  | N/A                                                  | ➖ Triangulation skipped: single version string                      | ✅ version `19.0.1.3.0`                                                                                                | ➖ Single                                                                      | ➖ None needed                                                                                                                |
| 1.5  | payment + module suite              | Integration                 | N/A                                                  | N/A                                                                  | ✅ install OK; 63/63 module tests                                                                                      | N/A                                                                            | N/A                                                                                                                           |
| 2.1  | `tests/test_collection_ui.py`       | Unit (TransactionCase arch) | ✅ 63/63 (`invoke test -m collection --mode=update`) | ✅ Written → 2 failed + 1 error (missing widgets)                    | ✅ Passed after 2.2                                                                                                    | ✅ typed×3 + Payment Lines; accept image/\*+.pdf; reject `.doc` advertisement  | ✅ Shared `_assert_attachment_binary_widget` helper                                                                           |
| 2.2  | `views/collection_views.xml`        | View arch                   | N/A (implementation)                                 | covered by 2.1 RED                                                   | ✅ widgets on 4 lists                                                                                                  | covered by multi-list suite                                                    | ➖ None needed (matches design shape)                                                                                         |
| 2.3  | UI + module suite                   | Integration                 | N/A                                                  | N/A                                                                  | ✅ `invoke install -m collection` OK; `invoke test -m collection --mode=update` → **0 failed, 0 error(s) of 66 tests** | N/A                                                                            | N/A                                                                                                                           |
| 3.1  | `tests/test_collection_mcp_tool.py` | Unit (TransactionCase)      | ✅ 66/66 (`invoke test -m collection --mode=update`) | ✅ Written → 7 failed of 9 (`TestCollectionMcpAttachment`)           | ✅ Passed after 3.3                                                                                                    | ✅ PNG + PDF persist; omit compat; MIME mismatch + bad b64 + text/plain reject | ✅ Shared nest helpers/constants                                                                                              |
| 3.2  | `tests/test_collection_mcp_tool.py` | Unit (TransactionCase)      | ✅ same baseline                                     | ✅ Written (replace nest / add-when-none / omit nest leave existing) | ✅ Passed after 3.3                                                                                                    | ✅ with nest replace blocked; nest-on-empty blocked; omit leaves file          | ➖ covered by create-path ignore on replay                                                                                    |
| 3.3  | `tools/collection_voucher.py`       | MCP tool                    | N/A (implementation)                                 | covered by 3.1–3.2 RED                                               | ✅ 9/9 attachment tests                                                                                                | covered by multi-case suite                                                    | ✅ `_collection_enrich_payment_attachments` + `_collection_parse_attachment_nest`; reuses `Line._validate_attachment_payload` |
| 3.4  | MCP + module suite                  | Integration                 | N/A                                                  | N/A                                                                  | ✅ `invoke install -m collection` OK; `invoke test -m collection --mode=update` → **0 failed, 0 error(s) of 75 tests** | N/A                                                                            | N/A                                                                                                                           |
| 4.1  | N/A (lint gate)                     | Quality                     | N/A                                                  | N/A (verification)                                                   | ✅ scoped pre-commit Passed                                                                                            | N/A                                                                            | ✅ Trivial wrap of `enumerate(zip(...))` for Ruff E501; trailing-whitespace auto-fix on this progress file                    |
| 4.2  | full module suite                   | Integration                 | N/A                                                  | N/A (verification)                                                   | ✅ `invoke test -m collection --mode=update` → **0 failed, 0 error(s) of 75 tests**                                    | N/A                                                                            | N/A                                                                                                                           |

### Test Summary

- **Total new tests written (Unit 1)**: 9 (`TestCollectionPaymentAttachment`)
- **Total new tests written (Unit 2)**: 3
  (`test_typed_lists_include_attachment_binary_widgets`,
  `test_payment_lines_list_includes_attachment_binary_widget`,
  `test_typed_and_payment_lists_attachment_accept_is_image_and_pdf`)
- **Total new tests written (Unit 3)**: 9 (`TestCollectionMcpAttachment`)
- **Total tests passing (module after Phase 4)**: 75
- **Layers used**: Unit/Integration via Odoo TransactionCase (MCP `_call` + ORM)
- **Approval tests** (refactoring): None — no pure refactor of prior behavior
- **Pure functions created**: 0 (validation reuses model `_validate_attachment_payload`;
  nest parse lives on mixin helpers)

## Work Unit Evidence

### Unit 1 — Model fields and constraints

| Evidence                                          | Value                                                                                                                                                                                                                                                                                          |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `docker compose run --rm … odoo -u collection --test-tags /collection:TestCollectionPaymentAttachment,/collection:TestCollectionPaymentDocumentId` → **0 failed, 0 error(s) of 13 tests**. Full unit verify: `invoke test -m collection --mode=update` → **0 failed, 0 error(s) of 63 tests**. |
| Runtime harness command/scenario and exact result | `invoke install -m collection` → success (addons init/load, Modules loaded, shutdown). Also `odoo -d devel -u collection --stop-after-init` succeeded.                                                                                                                                         |
| Rollback boundary                                 | Revert `models/collection_voucher_line.py`, `tests/test_collection_payment.py`, `__manifest__.py` (and this change’s OpenSpec progress files). No views/tools/UI/MCP edits in Unit 1.                                                                                                          |

### Unit 2 — UI binary widgets

| Evidence                                          | Value                                                                                                                                                                               |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `invoke test -m collection --mode=update` → **0 failed, 0 error(s) of 66 tests** (includes 3 new UI attachment arch tests). RED before views: **2 failed, 1 error(s) of 66 tests**. |
| Runtime harness command/scenario and exact result | `invoke install -m collection` → success (Modules loaded, shutdown).                                                                                                                |
| Rollback boundary                                 | Revert `views/collection_views.xml`, `tests/test_collection_ui.py` (and Unit 2 OpenSpec progress marks). Does not remove Unit 1 model/payment-test work.                            |

### Unit 3 — MCP optional nest

| Evidence                                          | Value                                                                                                                                                                                                                                                                                                          |
| ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `docker compose run --rm … odoo -d devel -u collection --test-enable --test-tags=/collection:TestCollectionMcpAttachment` → RED **7 failed, 0 error(s) of 9 tests**; GREEN **0 failed, 0 error(s) of 9 tests**. Full module: `invoke test -m collection --mode=update` → **0 failed, 0 error(s) of 75 tests**. |
| Runtime harness command/scenario and exact result | `invoke install -m collection` → success (Modules loaded, shutdown).                                                                                                                                                                                                                                           |
| Rollback boundary                                 | Revert `tools/collection_voucher.py`, `tests/test_collection_mcp_tool.py` (and Unit 3 OpenSpec progress marks). Does not remove Unit 1 model or Unit 2 UI work.                                                                                                                                                |

### Phase 4 — Quality gate

| Evidence                                          | Value                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | From seedian root: `pre-commit run --files` on collection paths (modified + OpenSpec change files + core addon files) → **Passed** (all hooks green; optional pylint_odoo notes pre-existing C8101 `manifest-required-author` warning, hook still Passed). First attempt failed Ruff E501 on `tools/collection_voucher.py` (`enumerate(zip(...))` one-liner) and trailing-whitespace on this progress file; trivial wrap + auto-fix → re-run Passed. |
| Runtime harness command/scenario and exact result | `invoke test -m collection --mode=update` → **0 failed, 0 error(s) of 75 tests** (`odoo.tests.result`; `collection: 91 tests` stats line includes framework bookkeeping; authoritative result is 75/75 green). N/A for separate install harness — full module update-mode suite is the Phase 4 confirmation.                                                                                                                                         |
| Rollback boundary                                 | Phase 4 product-behavior-neutral: only lint wrap in `tools/collection_voucher.py` (if distinct from Unit 3), trailing-whitespace cleanup on OpenSpec progress, and OpenSpec marks (`tasks.md` 4.1–4.2, `state.yaml` apply complete, this file). Reverting Phase 4 OpenSpec marks does not remove Units 1–3 code.                                                                                                                                     |

## Files Changed

| File                                                          | Action   | What Was Done                                                                                                                                                                |
| ------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/test_collection_payment.py`                            | Modified | Added `TestCollectionPaymentAttachment` (9 behavioral tests)                                                                                                                 |
| `models/collection_voucher_line.py`                           | Modified | `attachment` / `attachment_filename`; validate base64+MIME; constrains + create/write gate                                                                                   |
| `__manifest__.py`                                             | Modified | Version `19.0.1.2.0` → `19.0.1.3.0`                                                                                                                                          |
| `tests/test_collection_ui.py`                                 | Modified | Added 3 arch tests + `_assert_attachment_binary_widget` for typed + Payment Lines widgets                                                                                    |
| `views/collection_views.xml`                                  | Modified | Binary `attachment` + hidden `attachment_filename` on 3 typed lists + Payment Lines list                                                                                     |
| `tests/test_collection_mcp_tool.py`                           | Modified | Added `TestCollectionMcpAttachment` (9 behavioral tests: create nest/omit/reject + exact-retry ignore)                                                                       |
| `tools/collection_voucher.py`                                 | Modified | Optional nest schema; create-only enrich/map; declared MIME must match detected; replay ignores nest; never `sudo()`; Phase 4: wrap long `enumerate(zip(...))` for Ruff E501 |
| `openspec/changes/voucher-line-attachments/tasks.md`          | Modified | Marked 1.1–1.5, 2.1–2.3, 3.1–3.4, and 4.1–4.2 `[x]`                                                                                                                          |
| `openspec/changes/voucher-line-attachments/state.yaml`        | Modified | Apply complete; all work units done; next = sdd-verify                                                                                                                       |
| `openspec/changes/voucher-line-attachments/apply-progress.md` | Modified | Merged Units 1–3 + Phase 4 evidence                                                                                                                                          |

## Deviations from Design

- Design preferred validation solely via `@api.constrains('attachment')`. Invalid base64
  is rejected by `ir.attachment.create` with `binascii.Error` **before** constrains run.
  Implementation adds `create`/`write` pre-validation via `_validate_attachment_payload`
  so the public contract remains `UserError`, and keeps `@api.constrains` as a second
  gate for MIME/base64 after store.
- Unit 2 UI matches design (list-only Payment Lines; no new form). Delta spec scenario
  wording mentions Payment Lines form; design/tasks constrain list-only — followed
  design/tasks.
- Unit 3: nest MIME/base64 validation runs **after** all-new determination and
  **before** entering the existing create savepoint (mapped vals then created inside
  that savepoint). Matches design “create-only after all-new”; atomicity still holds
  because invalid nests never call create, and valid nests are written only inside the
  savepoint.
- Phase 4: no product-behavior deviations; lint-only wrap for E501.

## Issues Found

- None blocking. Note: default `invoke test -m collection` uses `--mode=init`; on an
  already-installed module that can report 0 tests. Use `--mode=update` (or `-u`) for
  meaningful runs.
- Optional pylint_odoo C8101 (`manifest-required-author` missing `'Eynes'`) remains a
  pre-existing warning; mandatory pylint and the hook overall Passed — not changed in
  Phase 4.

## Remaining Tasks

- None — apply complete. Next phase: `sdd-verify`.

## Workload / PR Boundary

- Mode: stacked PR slice (`stacked-to-main`)
- Current work unit completed: Phase 4 — Quality gate
- Boundary: quality verification only (+ trivial Ruff E501 wrap); no new product
  features
- Next work unit: N/A (all units done)
- Estimated review budget impact: Phase 4 ~0 product LOC; full change remains High
  budget risk across stacked Units 1–3
