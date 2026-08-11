# Tasks: Optional image/PDF attachment per voucher line

## Review Workload Forecast

| Field                   | Value                  |
| ----------------------- | ---------------------- |
| Estimated changed lines | 450–600                |
| 400-line budget risk    | High                   |
| Chained PRs recommended | Yes                    |
| Suggested split         | PR 1 → PR 2 → PR 3     |
| Delivery strategy       | ask-on-risk (resolved) |
| Chain strategy          | stacked-to-main        |

Decision needed before apply: No Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

### Suggested Work Units

| Unit | Goal                                    | Likely PR | Focused test command        | Runtime harness                | Rollback boundary                                                      |
| ---- | --------------------------------------- | --------- | --------------------------- | ------------------------------ | ---------------------------------------------------------------------- |
| 1    | Line Binary+filename + model tests      | PR 1      | `invoke test -m collection` | `invoke install -m collection` | `collection_voucher_line.py` + `test_collection_payment.py` + manifest |
| 2    | Binary widgets on typed + Payment Lines | PR 2      | `invoke test -m collection` | `invoke install -m collection` | `collection_views.xml` + `test_collection_ui.py`                       |
| 3    | MCP nest attach + idempotency tests     | PR 3      | `invoke test -m collection` | `invoke install -m collection` | `tools/collection_voucher.py` + `test_collection_mcp_tool.py`          |

Prerequisite (done): `AGENTS.md` attachment rules — do not re-edit.

## Phase 1: Model fields and constraints (Unit 1)

- [x] 1.1 RED: `tests/test_collection_payment.py` — omit attachment persists; valid
      PNG/PDF + filename stores via `ir.attachment`; invalid base64 and
      non-image/non-PDF MIME raise `UserError` and do not persist.
- [x] 1.2 RED: same file — write replace updates file; clear/remove empties
      Binary+filename; unlink line cascades attachment cleanup; `copy=False` on
      duplicate.
- [x] 1.3 GREEN: `models/collection_voucher_line.py` — `attachment`
      Binary(`attachment=True`, `copy=False`), `attachment_filename` Char(`copy=False`);
      `@api.constrains('attachment')` via `b64decode(validate=True)` + `guess_mimetype`;
      allow `image/*` or `application/pdf` else `UserError`.
- [x] 1.4 GREEN: `__manifest__.py` version `19.0.1.2.0` → `19.0.1.3.0`.
- [x] 1.5 Verify: `invoke install -m collection`; payment tests green.

## Phase 2: UI binary widgets (Unit 2)

- [x] 2.1 RED: `tests/test_collection_ui.py` — each typed embed (`bank_transfer`,
      `check`, `cash_deposit`) and Payment Lines list has exactly one `attachment`
      binary widget with `filename="attachment_filename"` and `accepted_file_extensions`
      allowing `image/*` + PDF; filename field present.
- [x] 2.2 GREEN: `views/collection_views.xml` — add those widgets to the three typed
      One2many lists and Payment Lines list (list-only; no new form).
- [x] 2.3 Verify: `invoke install -m collection`; UI tests green.

## Phase 3: MCP optional nest (Unit 3)

- [x] 3.1 RED: `tests/test_collection_mcp_tool.py` — create with valid nested image/PDF
      attachment persists voucher+lines+file atomically; omit nest still creates
      (compat); MIME mismatch / bad base64 → `UserError` and no voucher/line/attachment
      writes.
- [x] 3.2 RED: same file — exact-retry by `document_id` returns existing voucher; with
      or without nest, attachments unchanged (no add/replace/compare).
- [x] 3.3 GREEN: `tools/collection_voucher.py` — optional `{name,mimetype,datas}` after
      all-new; declared MIME must match detected allow-list; map into line vals inside
      existing savepoint; never `sudo()`; replay path ignores nest.
- [x] 3.4 Verify: `invoke install -m collection`; `invoke test -m collection`.

## Phase 4: Quality gate

- [x] 4.1 `pre-commit run --files odoo/custom/src/private/collection/**`
- [x] 4.2 Confirm full `invoke test -m collection` green after Units 1–3.
