# Apply Progress: standalone-payment-vouchers

**Change**: standalone-payment-vouchers **Mode**: Strict TDD **Work unit**: Phase 5 / PR
5 — Nebula + apply-root grant **Updated**: 2026-08-12

## Completed Phase 1 tasks

- [x] 1.1 RED: voucher create defaults `pending`; no `received_date`; required
      `customer_identification`; `create_date` not overridable; drop
      `new`/`validated`/`payment_ids`
- [x] 1.2 GREEN: flatten payment/attachment/review fields onto `collection.voucher`;
      default `pending`; strip forged dates; drop `payment_ids`
- [x] 1.3 TRIANGULATE: persist `bank_transfer` / `check` (`common`/`deferred`) /
      `cash_deposit` / `unsupported`; UI omit `document_id` OK
- [x] 1.4 RED: `action_approve` / `action_reject` from `pending` record reviewer/time;
      terminal immutable; `@api.ondelete` only `pending`
- [x] 1.5 GREEN: those actions; drop `action_validate` and aggregate line gates
- [x] 1.6 TRIANGULATE: `write({state})` without `collection_audited_state` runs
      approve/reject; `state=pending` only if `attachment` in vals
- [x] 1.7 GREEN: `write()` audit gate; attachment-replace resets `pending` + clears
      audit
- [x] 1.8 RED: UNIQUE(`document_id`) on voucher; PNG/PDF persist
      `res_model=collection.voucher`; bad base64/MIME `UserError`
- [x] 1.9 GREEN: Constraint + attachment validation on voucher; delete
      `models/collection_voucher_line.py`; drop import
- [x] 1.10 TRIANGULATE: internal voucher CRUD; no `collection.voucher.line` ACL; portal
      denied; drop line ACL row
- [x] 1.11 RED/GREEN: chatter tracks `pending`→`approved`/`rejected`; sequence code
      `collection.voucher` kept
- [x] 1.12 Structural: `__manifest__.py` `19.0.1.8.0` → `19.0.1.9.0`; no conversion
      script; keep `migrations/19.0.1.7.0`
- [x] 1.13 REFACTOR: focused tests + resetdb + upgrade + scoped pre-commit

## Completed Phase 2 tasks

- [x] 2.1 RED: `tests/test_collection_ui.py` — xmlids
      `view_collection_voucher_line_{list,search}`, `action_collection_voucher_line`,
      `menu_collection_voucher_line` gone; `load_menus` omits Payment Lines
- [x] 2.2 GREEN: those records already deleted in Phase 1 load-bearing trim;
      `<delete search=...>` kept
- [x] 2.3 RED: reuse `view_collection_voucher_{list,search,kanban,form}` — `<list>` not
      `<tree>`; kanban `t-name="card"`, `default_group_by="state"`, `records_draggable`;
      form statusbar Approve/Reject when `pending`; readonly `create_date`; no
      `received_date`; no typed `payment_ids` tables
- [x] 2.4 GREEN: flatten views; typed `invisible=` payment fields; Binary+filename
      widgets accept `image/*` and PDF on form/list/kanban
- [x] 2.5 TRIANGULATE: `unsupported` listed via Payment Vouchers
      `document_type=unsupported` filter; create/edit enabled; search filters
      pending/approved/rejected
- [x] 2.6 REFACTOR: focused UI + Phase 1 tags green; `-u collection` harness; scoped
      pre-commit Passed

## Completed Phase 3 tasks

- [x] 3.1 RED: rewrite `tests/test_collection_document_review.py` onto
      `collection.voucher`; queue `pending`+attachment; payload
      `voucher_name`/`voucher_id`; `/web/content?model=collection.voucher`; drop
      aggregate validate/reject tests
- [x] 3.2 GREEN: RPCs already on `models/collection_voucher.py` from Phase 1;
      `FOR UPDATE` on `collection_voucher` verified
- [x] 3.3 TRIANGULATE: approve field corrections (bank_transfer/check/cash_deposit);
      stale/ineligible refuse; rotation persist/reset; OWL
      `LINE_MODEL="collection.voucher"`; voucher copy in action JS/XML
- [x] 3.4 RED: `tests/test_collection_document_review_flag.py` — OFF RPCs raise
      `UserError`; form Approve/Reject still work; Payment Vouchers views keep
      `state`/audit
- [x] 3.5 GREEN: RPCs still `_ensure_document_review_enabled`; form/kanban
      `action_approve`/`action_reject` do not; xmlids kept; `ir_ui_menu.py` unchanged;
      list/form audit columns added
- [x] 3.6 REFACTOR: focused tags + `-u collection` harness + scoped pre-commit Passed

## Completed Phase 4 tasks

- [x] 4.1 RED: `tests/test_collection_mcp_tool.py` — registry
      `create_collection_vouchers` (`category=write`, `registry=mcp`); all-new
      `{vouchers:[{id,name,state,document_id},...]}` payment order; no `sudo()`; no DB
      `muk_mcp.tool` row
- [x] 4.2 GREEN: `tools/collection_voucher.py` rename `@mcp_tool`;
      `with env.cr.savepoint():` `collection.voucher.create([{...}, ...])`
- [x] 4.3 TRIANGULATE: exact-retry returns ALL vouchers, ignore customer/attachments;
      in-call dup + partial overlap `UserError` no writes; docs on different vouchers
      succeed (former cross-voucher error)
- [x] 4.4 RED/GREEN: UniqueViolation → `invalidate_all()` then replay or reject; nested
      attachment MIME/base64; portal ACL denied
- [x] 4.5 REFACTOR: focused MCP tags + `-u collection` harness + scoped pre-commit
      Passed

## Completed Phase 5 tasks

- [x] 5.1 RED: nebula-agent `tests/unit_tests/test_collection_voucher.py` —
      `MCP_TOOL_NAME=="create_collection_vouchers"`; fail-closed; `_format_success`
      lists all voucher identities
- [x] 5.2 GREEN: nebula-agent `src/agent/tools/collection_voucher.py` rename constant +
      list formatter; keep first-party `register_latest_collection_voucher`
- [x] 5.3 TRIANGULATE: `tests/integration_tests/test_graph.py` MCP name patches; replay
      list identity (`test_agent_tools.py` already used first-party name only)
- [x] 5.4 GREEN: nebula-agent `openspec/specs/collection-voucher-registration/spec.md` —
      one voucher per payment, exact MCP name, list identity
- [x] 5.5 Structural: collection `openspec/config.yaml` widen context + apply `roots`
      include `/home/crisd/projects/nebula/nebula-agent`; both `AGENTS.md`;
      `readme/DESCRIPTION.md` (+ generated `README.rst` /
      `static/description/index.html`). Triangulation skipped: config/docs
- [x] 5.6 REFACTOR: nebula-agent `uv run make test` + `uv run make integration_tests` +
      `uv run make lint`; collection scoped pre-commit Passed

Phase 5 complete. All implementation tasks 1.1–5.6 are `[x]`.

## TDD Cycle Evidence

| Task | Test File                                                                    | Layer                  | Safety Net                                                                        | RED                                                                                                                                                                     | GREEN                                                                                                           | TRIANGULATE                                                                                                                                                                      | REFACTOR                                                        |
| ---- | ---------------------------------------------------------------------------- | ---------------------- | --------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| 1.1  | `tests/test_collection_voucher.py`                                           | Unit (TransactionCase) | ✅ 18/18 voucher tests before edits                                               | ✅ Written; executed fail (`payment_ids` still present, state still `new`)                                                                                              | ✅ Passed after flatten                                                                                         | ✅ required field + `received_date` reject + `create_date` not overridable                                                                                                       | ➖ None needed                                                  |
| 1.2  | `tests/test_collection_voucher.py`                                           | Unit                   | ✅ from 1.1                                                                       | ✅ 1.1 tests described missing fields                                                                                                                                   | ✅ Fields absorbed; `payment_ids` gone; default `pending`                                                       | Covered by 1.3                                                                                                                                                                   | ➖ Batched into flatten                                         |
| 1.3  | `tests/test_collection_voucher.py`, `tests/test_collection_payment.py`       | Unit                   | N/A (new cases)                                                                   | ✅ Written                                                                                                                                                              | ✅ Passed                                                                                                       | ✅ 3 types + unsupported/partial + `check_type=common` + omit `document_id` + multiple NULLs                                                                                     | ➖ None needed                                                  |
| 1.4  | `tests/test_collection_voucher.py`                                           | Unit                   | N/A (new cases)                                                                   | ✅ Written (`action_approve`/`action_reject`/unlink pending)                                                                                                            | ✅ Passed                                                                                                       | ✅ approve + reject + both terminals + unlink approved and rejected                                                                                                              | ➖ None needed                                                  |
| 1.5  | `tests/test_collection_voucher.py`                                           | Unit                   | N/A                                                                               | ✅ `test_action_validate_removed`                                                                                                                                       | ✅ Actions + `@api.ondelete(at_uninstall=False)`                                                                | Covered by 1.4/1.6                                                                                                                                                               | ➖ None needed                                                  |
| 1.6  | `tests/test_collection_voucher.py`                                           | Unit                   | N/A                                                                               | ✅ `test_kanban_drag_writes_state` + reopen refused                                                                                                                     | ✅ Passed                                                                                                       | ✅ drag to approved and rejected; reopen without attachment refused                                                                                                              | ➖ None needed                                                  |
| 1.7  | `tests/test_collection_voucher.py`, `tests/test_collection_payment.py`       | Unit                   | N/A                                                                               | ✅ attachment-replace reset cases                                                                                                                                       | ✅ `write()` audit gate                                                                                         | ✅ approved and rejected replace paths                                                                                                                                           | ➖ Long UserError wrapped                                       |
| 1.8  | `tests/test_collection_payment.py`                                           | Unit                   | N/A                                                                               | ✅ UNIQUE + PNG/PDF + bad base64/MIME                                                                                                                                   | ✅ Passed                                                                                                       | ✅ PNG + PDF; invalid b64 + text MIME; distinct ids                                                                                                                              | ➖ None needed                                                  |
| 1.9  | `tests/test_collection_payment.py`, `tests/test_collection_acl.py`           | Unit                   | N/A                                                                               | ✅ line model gone                                                                                                                                                      | ✅ File deleted; review RPCs relocated to voucher                                                               | ✅ ACL asserts no line model                                                                                                                                                     | Load-bearing RPC move                                           |
| 1.10 | `tests/test_collection_acl.py`                                               | Unit                   | N/A                                                                               | ✅ internal CRUD / no line ACL / portal denied                                                                                                                          | ✅ CSV line row dropped                                                                                         | ✅ portal CRUD + review RPCs denied; form approve works when review OFF                                                                                                          | ➖ None needed                                                  |
| 1.11 | `tests/test_collection_mail.py`                                              | Unit                   | N/A                                                                               | ✅ pending→approved/rejected tracking                                                                                                                                   | ✅ Passed                                                                                                       | ✅ approve and reject chatter values                                                                                                                                             | ➖ None needed                                                  |
| 1.12 | `__manifest__.py`                                                            | Structural             | N/A                                                                               | ➖ Structural                                                                                                                                                           | ✅ `19.0.1.9.0`                                                                                                 | ➖ Triangulation skipped: version/data-only                                                                                                                                      | ➖ None needed                                                  |
| 1.13 | focused + harness                                                            | Integration            | ✅ Phase 1 46/46                                                                  | N/A                                                                                                                                                                     | ✅ Focused green; resetdb+upgrade OK                                                                            | N/A                                                                                                                                                                              | ✅ scoped pre-commit Passed                                     |
| 2.1  | `tests/test_collection_ui.py`                                                | Unit (TransactionCase) | ✅ 6 failed, 9 error(s) of 24 old UI tests (expected-red Payment Lines contract)  | ✅ Written `test_payment_line_xmlids_removed` + `test_load_menus_omits_payment_lines`                                                                                   | ✅ Passed (xmlids already gone from Phase 1 trim)                                                               | ✅ xmlid refs False + load_menus name walk + leftover `ir.ui.menu` search empty                                                                                                  | ➖ None needed                                                  |
| 2.2  | `views/collection_views.xml`                                                 | Unit                   | ✅ from 2.1                                                                       | ✅ 2.1 tests described missing xmlids                                                                                                                                   | ✅ Already deleted; `<delete search=...>` retained                                                              | Covered by 2.1                                                                                                                                                                   | ➖ None needed                                                  |
| 2.3  | `tests/test_collection_ui.py`                                                | Unit                   | ✅ from 2.1                                                                       | ✅ Written list/`<list>`, kanban `card`+drag, Approve/Reject `pending`, no `received_date`, no `payment_ids` tables                                                     | ✅ Passed against Phase 1 load-bearing arch                                                                     | ✅ group_expand `pending/approved/rejected`; no `action_validate`; no `kanban-box`                                                                                               | ➖ None needed                                                  |
| 2.4  | `tests/test_collection_ui.py`, `views/collection_views.xml`                  | Unit                   | N/A                                                                               | ✅ Executed fail: typed `invisible=` missing; list/search missing `document_type`/`amount`; no Binary widgets (4 failed / 21)                                           | ✅ Passed after flatten + widgets                                                                               | Covered by 2.5                                                                                                                                                                   | ✅ Kanban preload field without duplicated widget options       |
| 2.5  | `tests/test_collection_ui.py`                                                | Unit                   | N/A                                                                               | ✅ `test_unsupported_filter_lists_unsupported_vouchers` failed (no filter)                                                                                              | ✅ Search filter + create/edit enabled                                                                          | ✅ unsupported ORM search hit; pending/approved/rejected filters; create/edit on list/kanban/form/action; UI omit `document_id`                                                  | ➖ None needed                                                  |
| 2.6  | focused + harness                                                            | Integration            | ✅ Phase 1 46/46 still green                                                      | N/A                                                                                                                                                                     | ✅ UI 21/21; combined 67/67                                                                                     | N/A                                                                                                                                                                              | ✅ scoped pre-commit Passed                                     |
| 3.1  | `tests/test_collection_document_review.py`                                   | Unit (TransactionCase) | ✅ 67/67 Phase 1–2                                                                | ✅ Written; 4 failed / 43 (OWL `LINE_MODEL` still line; XML “líneas”; audit columns missing). RPC/queue/payload cases already matched Phase 1 RPCs                      | ✅ After OWL+copy+audit views: 0 failed / 43                                                                    | Covered by 3.3                                                                                                                                                                   | ✅ `_voucher_vals` simplified                                   |
| 3.2  | `models/collection_voucher.py`                                               | Unit                   | ✅ from 3.1                                                                       | ✅ 3.1 RPC tests described voucher queue/payload/`FOR UPDATE`                                                                                                           | ✅ Already implemented in Phase 1; verified green                                                               | Covered by 3.3                                                                                                                                                                   | ➖ No RPC rewrite                                               |
| 3.3  | `tests/test_collection_document_review.py`, `static/src/document_review/*`   | Unit                   | N/A                                                                               | ✅ LINE_MODEL + copy tests failed                                                                                                                                       | ✅ `LINE_MODEL="collection.voucher"`; “Payment voucher …” / “comprobantes elegibles”                            | ✅ bank_transfer + check + cash_deposit approve; stale/ineligible; rotation persist/reset; PNG+PDF URLs                                                                          | ➖ Copy-only OWL                                                |
| 3.4  | `tests/test_collection_document_review_flag.py`                              | Unit                   | N/A                                                                               | ✅ Written; 2 failed / 43 remaining were audit-column views (RPC OFF + form Approve/Reject already green)                                                               | ✅ After 3.5 view fields                                                                                        | ✅ OFF + ON view cases; form approve and reject                                                                                                                                  | ➖ E501 wraps                                                   |
| 3.5  | `views/collection_views.xml`                                                 | Unit                   | N/A                                                                               | ✅ 3.4 missing `reviewed_by`/`reviewed_at`                                                                                                                              | ✅ List optional-hide + form readonly audit; RPCs still gated; xmlids/`ir_ui_menu.py` unchanged                 | Covered by 3.4                                                                                                                                                                   | ➖ None needed                                                  |
| 3.6  | focused + harness                                                            | Integration            | ✅ 67/67 Phase 1–2                                                                | N/A                                                                                                                                                                     | ✅ Phase 3 43/43; combined 110/110                                                                              | N/A                                                                                                                                                                              | ✅ scoped pre-commit Passed                                     |
| 4.1  | `tests/test_collection_mcp_tool.py`                                          | Unit (TransactionCase) | ✅ 110/110 Phase 1–3; MCP expected-red (old singular + `collection.voucher.line`) | ✅ Written; executed fail: 6 failed, 7 error(s) of 13 (`Tool not found: create_collection_vouchers`; old name still registered)                                         | Covered by 4.2                                                                                                  | Covered by 4.3                                                                                                                                                                   | ➖ After GREEN                                                  |
| 4.2  | `tools/collection_voucher.py`                                                | Unit                   | ✅ from 4.1                                                                       | ✅ 4.1 tests described missing plural tool + list payload                                                                                                               | ✅ Passed after rename + `Voucher.create([{...}, ...])` in savepoint                                            | Covered by 4.3                                                                                                                                                                   | ✅ `_collection_vouchers_payload` order helper                  |
| 4.3  | `tests/test_collection_mcp_tool.py`                                          | Unit                   | N/A                                                                               | ✅ exact-retry / in-call dup / partial / former cross-voucher                                                                                                           | ✅ Passed                                                                                                       | ✅ 2-payment replay + ignore customer/amount; in-call dup; partial no writes; docs on different vouchers succeed in payment order                                                | ➖ None needed                                                  |
| 4.4  | `tests/test_collection_mcp_tool.py`                                          | Unit                   | N/A                                                                               | ✅ UniqueViolation + nested MIME/base64 + portal ACL (same RED run as 4.1; attachment class also expected-red until GREEN)                                              | ✅ 0 failed / 22 after sudo-comment assertion fix                                                               | ✅ UniqueViolation full replay + partial reject; PNG+PDF persist; MIME mismatch + bad b64 + text MIME; omit nest; exact-retry nest ignore (replace/add/omit); portal AccessError | ✅ sudo assert ignores comments; E501 docstring wrap            |
| 4.5  | focused + harness                                                            | Integration            | ✅ 110/110 Phase 1–3                                                              | N/A                                                                                                                                                                     | ✅ MCP 22/22; Phase 1–3 110/110                                                                                 | N/A                                                                                                                                                                              | ✅ scoped pre-commit Passed                                     |
| 5.1  | `tests/unit_tests/test_collection_voucher.py`                                | Unit                   | ✅ 17/17 before edits                                                             | ✅ Written; executed fail: **14 failed, 8 passed of 22** (`MCP_TOOL_NAME` still singular; `_format_success` ignored `vouchers` list; `get_mcp_tool` requested old name) | Covered by 5.2                                                                                                  | Covered by 5.3                                                                                                                                                                   | ➖ After GREEN                                                  |
| 5.2  | `src/agent/tools/collection_voucher.py`                                      | Unit                   | ✅ from 5.1                                                                       | ✅ 5.1 tests described missing plural name + list formatter                                                                                                             | ✅ 22/22 after `MCP_TOOL_NAME="create_collection_vouchers"` + `_format_success` over `{"vouchers":[...]}`       | Covered by 5.3                                                                                                                                                                   | ✅ ruff wrap on error string                                    |
| 5.3  | `tests/integration_tests/test_graph.py`                                      | Integration            | ✅ 16/16 after GREEN (name patch would fail until 5.2)                            | ✅ MCP name patches + 2-voucher list identity in graph messages                                                                                                         | ✅ 16/16                                                                                                        | ✅ multi-doc create + attachment-batch replay list identity; `test_agent_tools.py` unchanged (first-party name only)                                                             | ✅ ruff wrap on long asserts                                    |
| 5.4  | `openspec/specs/collection-voucher-registration/spec.md`                     | Spec                   | N/A                                                                               | ➖ Spec                                                                                                                                                                 | ✅ one voucher per payment; exact `create_collection_vouchers`; list identity                                   | ➖ Spec                                                                                                                                                                          | ➖ None needed                                                  |
| 5.5  | collection `openspec/config.yaml`, both `AGENTS.md`, `readme/DESCRIPTION.md` | Structural             | N/A                                                                               | ➖ Structural                                                                                                                                                           | ✅ apply `roots` include nebula-agent; docs/MCP name                                                            | ➖ Triangulation skipped: config/docs                                                                                                                                            | ➖ oca-gen-addon-readme regenerated `README.rst` / `index.html` |
| 5.6  | focused + full suite                                                         | Integration            | ✅ 22/22 unit file; 16/16 graph                                                   | N/A                                                                                                                                                                     | ✅ `uv run make test` 126/126; `uv run make integration_tests` 16/16; `uv run make lint` (ruff + mypy --strict) | N/A                                                                                                                                                                              | ✅ collection scoped pre-commit Passed                          |

### Test Summary

- **Total tests written/updated (Phase 1 files)**: 46
- **Total tests written/updated (Phase 2 UI)**: 21 (`TestCollectionUi`; replaced 24 old
  cases)
- **Total tests written/updated (Phase 3 review)**: 43 (`TestCollectionDocumentReview`
  28 + `TestCollectionDocumentReviewFlag` 15)
- **Total tests written/updated (Phase 4 MCP)**: 22 (`TestCollectionMcpTool` 13 +
  `TestCollectionMcpAttachment` 9)
- **Total tests written/updated (Phase 5 Nebula)**: 22 unit
  (`test_collection_voucher.py`; +5 new name/formatter/fail-closed/list-identity
  cases) + 16 graph (MCP name + list identity assertions)
- **Total tests passing (focused Phase 1+2+3)**: 110 (0 failed, 0 errors)
- **Total tests passing (focused Phase 4 MCP)**: 22 (0 failed, 0 errors)
- **Total tests passing (Phase 5 nebula-agent)**: 126 unit + 16 integration (0 failed, 0
  errors)
- **Layers used**: Unit/TransactionCase (132 Odoo), Unit (nebula 126), Integration
  (`-u collection` harness + nebula graph)
- **Approval tests (refactoring)**: None — behavior change, not preservation refactor
- **Pure functions created**: `_format_success` rewritten as a pure list formatter (1)

## Work Unit Evidence

### Phase 1 (PR 1) — Flatten model + lifecycle

| Evidence                                          | Required value                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `docker exec -i seedian-odoo-1 odoo -d devel --test-enable --stop-after-init --workers=0 --http-port=18069 --test-tags /collection:TestCollectionVoucher,/collection:TestCollectionPaymentDocumentId,/collection:TestCollectionPaymentAttachment,/collection:TestCollectionAcl,/collection:TestCollectionMail` → **0 failed, 0 error(s) of 46 tests** (after resetdb). Safety-net baseline before edits: 18/18 `TestCollectionVoucher`. |
| Runtime harness command/scenario and exact result | `invoke resetdb -m collection` → exit 0, `Modules loaded`. Then `invoke start` + `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --workers=0 --http-port=18069` → exit 0, `Module collection loaded`. No `document_type` null-constraint on the reset DB.                                                                                                                                                  |
| Rollback boundary                                 | `models/collection_voucher.py`, delete `models/collection_voucher_line.py`, `models/__init__.py`, `security/ir.model.access.csv`, `__manifest__.py`, `tests/test_collection_{voucher,payment,acl,mail}.py`. Load-bearing extras (revert with the unit): `views/collection_views.xml` (drop `payment_ids` / line xmlids so `-u` can load).                                                                                               |

### Phase 2 (PR 2) — Payment Vouchers UI

| Evidence                                          | Required value                                                                                                                                                                                                                                                                                                                                                                                |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `docker exec -i seedian-odoo-1 odoo -d devel --test-enable --stop-after-init --workers=0 --http-port=18069 --test-tags /collection:TestCollectionUi` → **0 failed, 0 error(s) of 21 tests**. Combined with Phase 1 tags → **0 failed, 0 error(s) of 67 tests**. Safety-net baseline: 6 failed, 9 error(s) of 24 old UI tests. RED (new tests, no view GREEN yet): 4 failed, 0 error(s) of 21. |
| Runtime harness command/scenario and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --workers=0 --http-port=18069` → exit 0, `loading collection/views/collection_views.xml`, `Module collection loaded`, `Modules loaded.` Did not `invoke resetdb` (Phase 1 already reset; upgrade succeeded).                                                                                                     |
| Rollback boundary                                 | `views/collection_views.xml`, `tests/test_collection_ui.py`. Do not revert Phase 1 model/ACL files with this unit.                                                                                                                                                                                                                                                                            |

### Phase 3 (PR 3) — Document Review on voucher

| Evidence                                          | Required value                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `docker exec -i seedian-odoo-1 odoo -d devel --test-enable --stop-after-init --workers=0 --http-port=18069 --test-tags /collection:TestCollectionDocumentReview,/collection:TestCollectionDocumentReviewFlag` → **0 failed, 0 error(s) of 43 tests** (after `-u collection` for view xml). RED (tests first, OWL/views unchanged): **4 failed, 0 error(s) of 43**. Combined with Phase 1–2 tags → **0 failed, 0 error(s) of 110 tests**. Safety-net baseline: **0 failed, 0 error(s) of 67** Phase 1–2 tests. |
| Runtime harness command/scenario and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --workers=0 --http-port=18069` → exit 0, `loading collection/views/collection_views.xml`, `loading collection/views/collection_document_review_views.xml`, `Module collection loaded`, `Modules loaded.` Did not `invoke resetdb`.                                                                                                                                                                                               |
| Rollback boundary                                 | `tests/test_collection_document_review.py`, `tests/test_collection_document_review_flag.py`, `static/src/document_review/document_review_helpers.esm.js`, `static/src/document_review/document_review_action.esm.js`, `static/src/document_review/document_review_action.xml`, `views/collection_views.xml` (audit columns only). Do not revert Phase 1 RPC relocation or Phase 2 UI flatten with this unit. `models/ir_ui_menu.py` and `views/collection_document_review_views.xml` were not changed.        |

### Phase 4 (PR 4) — MCP N-voucher create/replay

| Evidence                                          | Required value                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Focused test command and exact result             | `docker exec -i seedian-odoo-1 odoo -d devel --test-enable --stop-after-init --workers=0 --http-port=18069 --test-tags /collection:TestCollectionMcpTool,/collection:TestCollectionMcpAttachment` → **0 failed, 0 error(s) of 22 tests**. RED (tests first, old singular tool): **6 failed, 7 error(s) of 13** `TestCollectionMcpTool` (`Tool not found: create_collection_vouchers`). After GREEN + sudo-comment assertion fix: 22/22. Phase 1–3 tags re-run → **0 failed, 0 error(s) of 110 tests**. |
| Runtime harness command/scenario and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --workers=0 --http-port=18069` → exit 0, `Module collection loaded`, `Modules loaded.` Did not `invoke resetdb`.                                                                                                                                                                                                                                                                                                          |
| Rollback boundary                                 | `tools/collection_voucher.py`, `tests/test_collection_mcp_tool.py`. Do not revert Phase 1–3 model/UI/review files with this unit.                                                                                                                                                                                                                                                                                                                                                                      |

### Phase 5 (PR 5) — Nebula + apply-root grant

| Evidence                                          | Required value                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Focused test command and exact result             | From `/home/crisd/projects/nebula/nebula-agent`: `uv run make test TEST_FILE=tests/unit_tests/test_collection_voucher.py` → **22 passed**. Safety-net baseline before edits: **17/17**. RED (tests first, old singular name + single-voucher formatter): **14 failed, 8 passed of 22**. After GREEN: 22/22. Full `uv run make test` → **126 passed**.                                                                          |
| Runtime harness command/scenario and exact result | N/A — unit/graph; live MCP cache restart is deploy. Graph triangulation: `uv run make integration_tests` → **16 passed**. `uv run make lint` → ruff + `mypy --strict` Success. Collection: `pre-commit run --files odoo/custom/src/private/collection/**` → Passed.                                                                                                                                                            |
| Rollback boundary                                 | nebula-agent `src/agent/tools/collection_voucher.py`, `tests/unit_tests/test_collection_voucher.py`, `tests/integration_tests/test_graph.py`, `openspec/specs/collection-voucher-registration/spec.md`, `AGENTS.md`; collection `openspec/config.yaml`, `AGENTS.md`, `readme/DESCRIPTION.md`, generated `README.rst` / `static/description/index.html`. Do not revert Phase 1–4 Odoo model/UI/review/MCP files with this unit. |

`invoke test -m collection` on the already-installed devel DB ran **0 tests**
(`-i collection` skips at-install tests when the module is present). Focused evidence
used `--test-enable --test-tags` (and `-u collection` when views needed to load).

## Expected-red later-phase tests

None remaining. MCP tests are green after Phase 4. Nebula-agent uses
`create_collection_vouchers` and the list formatter after Phase 5.

Phase 4 `TestCollectionMcpTool` + `TestCollectionMcpAttachment` are green (22/22). Phase
1–3 classes stayed green in the 110-test re-run. Phase 5 nebula unit 126/126 and graph
16/16.

## Deviations from design

1. **Review RPC relocation (required, not Phase 3 OWL work).** Task 1.9 deletes
   `collection_voucher_line.py`. `get_review_queue`,
   `action_review_{approve,reject,set_rotation}` and helpers moved onto
   `collection.voucher` so the module stays importable. Queue eligibility is `pending` +
   attachment; `FOR UPDATE` is on `collection_voucher`; payload uses
   `voucher_name=self.name`, `voucher_id=self.id`,
   `/web/content?model=collection.voucher`. OWL `LINE_MODEL` and
   `tests/test_collection_document_review*.py` were **not** rewritten.

2. **Load-bearing view edits in Phase 1** dropped `payment_ids` / line xmlids /
   `action_validate` so `-u` could load. Phase 2 reused those xmlids and finished the
   standalone UI (typed `invisible=` groups, Binary widgets, unsupported filter,
   list/search payment fields).

3. **MCP left on the old line contract** (`create_collection_voucher`,
   `env["collection.voucher.line"]`). **Resolved in Phase 4.**

4. **TDD batching (Phase 1):** 1.1 RED was executed failing before production flatten.
   1.2 GREEN implemented the full flattened voucher in one model write; 1.3–1.8 tests
   were authored in the same apply batch against that model rather than as 13 isolated
   docker RED runs.

5. **Phase 2 RED vs Phase 1 trim:** 2.1/2.2/2.3 tests for xmlids-gone, `<list>`, kanban
   `card`, Approve/Reject `pending`, and no typed tables passed immediately because
   Phase 1 already trimmed that arch. True RED (4 failed / 21) was 2.4/2.5: typed
   `invisible=`, Binary widgets, list/search `document_type`/`amount`, unsupported
   filter.

6. **Phase 3 RPC GREEN already done in Phase 1.** Task 3.2 did not move RPCs again. 3.1
   RED tests against `collection.voucher` passed for
   queue/payload/`FOR UPDATE`/approve/reject/rotation immediately. True RED (4 failed
   / 43) was OWL `LINE_MODEL` still `collection.voucher.line`, XML “líneas” / JS
   “Payment line”, and Payment Vouchers views missing `reviewed_by`/`reviewed_at`.

7. **Audit columns on Payment Vouchers views.** Spec requires voucher `state` and review
   audit columns regardless of the flag. Phase 2 list/form had `state` but not audit
   fields. Phase 3 added `reviewed_by`/`reviewed_at` (list `optional="hide"`, form
   readonly). `ir_ui_menu.py` and document-review xmlids were not changed.

8. **Phase 4 sudo assertion.** `inspect.getsource` includes the “never sudo()” comment,
   so the first GREEN run failed 1/22. Test now strips comment lines and asserts
   `.sudo(` / `sudo()` are absent from executable source. `create_uid` of created
   vouchers is the internal caller (not superuser).

9. **Phase 4 TDD batching.** 4.1–4.4 tests were authored in one rewrite of
   `test_collection_mcp_tool.py` (old file was expected-red against the deleted line
   model). RED was executed once (13 `TestCollectionMcpTool` cases) before production
   rename. Attachment class cases were in the same file rewrite and went green with 4.2.

10. **Phase 5 `test_agent_tools.py`.** No edit: it only asserts first-party
    `register_latest_collection_voucher`, not the MCP name.

11. **Phase 5 generated README.** `oca-gen-addon-readme` regenerated `README.rst` and
    `static/description/index.html` from `readme/DESCRIPTION.md` during scoped
    pre-commit.

## Remaining tasks

None. All implementation tasks 1.1–5.6 are `[x]`. Next: sdd-verify.
