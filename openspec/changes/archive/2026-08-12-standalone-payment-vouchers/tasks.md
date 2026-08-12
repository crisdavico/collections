# Tasks: Standalone Payment Vouchers

## Review Workload Forecast

| Field                   | Value                            |
| ----------------------- | -------------------------------- |
| Estimated changed lines | 1800–2800                        |
| 400-line budget risk    | High                             |
| Chained PRs recommended | Yes                              |
| Suggested split         | PR 1 → PR 2 → PR 3 → PR 4 → PR 5 |
| Delivery strategy       | auto-chain                       |
| Chain strategy          | stacked-to-main                  |

Decision needed before apply: No Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

PRs 1–5 stack to main in order. PR 1 drops `collection.voucher.line` (UI/MCP/review stay
red until PRs 2–4). No conversion script; `invoke resetdb -m collection` before upgrade.
Ignore leftover `openspec/changes/document-review-feature-flag/`. Threat matrix N/A.

### Suggested Work Units

| Unit | Goal                        | Likely PR | Focused test command                                                                    | Runtime harness                                                                                                   | Rollback boundary                                                                                                                                                                                                                                                                            |
| ---- | --------------------------- | --------- | --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | Flatten model + lifecycle   | PR 1      | `invoke test -m collection`                                                             | `invoke resetdb -m collection` then `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init` | `models/collection_voucher.py`, delete `models/collection_voucher_line.py`, `models/__init__.py`, `security/ir.model.access.csv`, `__manifest__.py`, `tests/test_collection_{voucher,payment,acl,mail}.py`                                                                                   |
| 2    | Payment Vouchers UI         | PR 2      | `invoke test -m collection`                                                             | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init`                                     | `views/collection_views.xml`, `tests/test_collection_ui.py`                                                                                                                                                                                                                                  |
| 3    | Document Review on voucher  | PR 3      | `invoke test -m collection`                                                             | same upgrade as PR 2                                                                                              | review RPCs in `models/collection_voucher.py`, `static/src/document_review/*`, `tests/test_collection_{document_review,document_review_flag}.py`                                                                                                                                             |
| 4    | MCP N-voucher create/replay | PR 4      | `invoke test -m collection`                                                             | same upgrade as PR 2                                                                                              | `tools/collection_voucher.py`, `tests/test_collection_mcp_tool.py`                                                                                                                                                                                                                           |
| 5    | Nebula + apply-root grant   | PR 5      | `uv run make test TEST_FILE=tests/unit_tests/test_collection_voucher.py` (nebula-agent) | N/A — unit/graph; live MCP cache restart is deploy                                                                | nebula-agent `src/agent/tools/collection_voucher.py`, `tests/unit_tests/test_collection_voucher.py`, `tests/integration_tests/test_graph.py`, `openspec/specs/collection-voucher-registration/spec.md`, `AGENTS.md`; collection `openspec/config.yaml`, `AGENTS.md`, `readme/DESCRIPTION.md` |

## Phase 1: Flatten model + lifecycle (PR 1)

- [x] 1.1 RED: `tests/test_collection_voucher.py` — create defaults `state=pending`, no
      `received_date`, required `customer_identification`, `create_date` not
      overridable; drop `new`/`validated`/`payment_ids`.
- [x] 1.2 GREEN: `models/collection_voucher.py` absorb line payment/attachment/review
      fields; default `pending`; strip forged dates; drop `payment_ids`.
- [x] 1.3 TRIANGULATE: persist `bank_transfer`/`check`
      (`common`/`deferred`)/`cash_deposit`/`unsupported` on voucher
      (`test_collection_voucher.py`); UI omit `document_id` OK
      (`test_collection_payment.py`).
- [x] 1.4 RED: voucher tests — `action_approve`/`action_reject` from `pending` record
      reviewer/time; terminal immutable; `@api.ondelete` only `pending`.
- [x] 1.5 GREEN: those actions; `@api.ondelete(at_uninstall=False)`; drop
      `action_validate` and aggregate line gates.
- [x] 1.6 TRIANGULATE: `test_kanban_drag_writes_state` — `write({state})` without
      `collection_audited_state` runs approve/reject; `state=pending` only if
      `attachment` in vals else refuse reopen.
- [x] 1.7 GREEN: `write()` audit gate; attachment-replace resets `pending` + clears
      audit (`test_collection_payment.py`).
- [x] 1.8 RED: `test_collection_payment.py` — `models.Constraint` UNIQUE(`document_id`)
      on voucher; valid PNG/PDF persist `res_model=collection.voucher`; bad base64/MIME
      `UserError`.
- [x] 1.9 GREEN: Constraint + attachment validation on voucher; delete
      `models/collection_voucher_line.py`; drop import in `models/__init__.py`.
- [x] 1.10 TRIANGULATE: `tests/test_collection_acl.py` — internal voucher CRUD; no
      `collection.voucher.line` ACL; portal denied. GREEN: drop line row in
      `security/ir.model.access.csv`.
- [x] 1.11 RED/GREEN: `tests/test_collection_mail.py` tracks
      `pending`→`approved`/`rejected`. Sequence code `collection.voucher` per payment
      (`data/ir_sequence_data.xml` keep `seq_collection_voucher`).
- [x] 1.12 Structural: `__manifest__.py` `19.0.1.8.0` → `19.0.1.9.0`. No conversion
      script; keep `migrations/19.0.1.7.0`. In-place `-u` unsupported. Triangulation
      skipped: version/data-only.
- [x] 1.13 REFACTOR: `invoke test -m collection`; resetdb + upgrade;
      `pre-commit run --files odoo/custom/src/private/collection/**`.

## Phase 2: UI (PR 2)

- [x] 2.1 RED: `tests/test_collection_ui.py` — xmlids
      `view_collection_voucher_line_{list,search}`, `action_collection_voucher_line`,
      `menu_collection_voucher_line` gone; `load_menus` omits Payment Lines.
- [x] 2.2 GREEN: delete those records in `views/collection_views.xml`.
- [x] 2.3 RED: reuse `view_collection_voucher_{list,search,kanban,form}` — `<list>` not
      `<tree>`; kanban `t-name="card"`, `default_group_by="state"`, `records_draggable`;
      form statusbar Approve/Reject when `pending`; readonly `create_date`; no
      `received_date`; no typed `payment_ids` tables.
- [x] 2.4 GREEN: flatten those views; typed `invisible=` payment fields; Binary+filename
      widgets accept `image/*` and PDF on form/list/kanban.
- [x] 2.5 TRIANGULATE: `unsupported` listed via Payment Vouchers
      `document_type=unsupported` filter; create/edit enabled; search filters
      pending/approved/rejected.
- [x] 2.6 REFACTOR: `invoke test -m collection`; upgrade; scoped pre-commit.

## Phase 3: Document Review (PR 3)

- [x] 3.1 RED: `tests/test_collection_document_review.py` — queue `state==pending` AND
      attachment on `collection.voucher` (drop parent `state==new`); payload
      `voucher_name=self.name`, `voucher_id=self.id`;
      `/web/content?model=collection.voucher`; drop aggregate validate/reject tests.
- [x] 3.2 GREEN: move `get_review_queue`, `action_review_{approve,reject,set_rotation}`
      to `models/collection_voucher.py`; `FOR UPDATE` on `collection_voucher`.
- [x] 3.3 TRIANGULATE: approve persists field corrections; stale/concurrent refuse;
      rotation persist/reset. OWL `LINE_MODEL="collection.voucher"` in
      `static/src/document_review/document_review_helpers.esm.js`; keep `/web/content`
      via payload; `document_review_action.esm.js` / `.xml`.
- [x] 3.4 RED: `tests/test_collection_document_review_flag.py` — OFF `get_review_queue`
      / `action_review_*` raise `UserError` (approve/reject do not run); Payment
      Vouchers Approve/Reject still work; views keep `state`/audit (not line views).
- [x] 3.5 GREEN: RPCs still `_ensure_document_review_enabled`; form/kanban actions do
      not. Keep `views/collection_document_review_views.xml` xmlids; flag/menu hide
      unchanged (`models/ir_ui_menu.py`).
- [x] 3.6 REFACTOR: `invoke test -m collection`; upgrade; scoped pre-commit.

## Phase 4: MCP (PR 4)

- [x] 4.1 RED: `tests/test_collection_mcp_tool.py` — registry
      `create_collection_vouchers` (`category=write`, `registry=mcp`); all-new
      `{vouchers:[{id,name,state,document_id},...]}` payment order; no `sudo()`; no DB
      `muk_mcp.tool` row.
- [x] 4.2 GREEN: `tools/collection_voucher.py` rename `@mcp_tool`;
      `with env.cr.savepoint():` `collection.voucher.create([{...}, ...])`.
- [x] 4.3 TRIANGULATE: exact-retry returns ALL vouchers, ignore customer/attachments;
      in-call dup + partial overlap `UserError` no writes; docs on different vouchers
      succeed (former cross-voucher error).
- [x] 4.4 RED/GREEN: UniqueViolation → `invalidate_all()` then replay or reject; nested
      attachment MIME/base64; portal ACL denied.
- [x] 4.5 REFACTOR: `invoke test -m collection`; upgrade; scoped pre-commit.

## Phase 5: Nebula + apply-root grant (PR 5)

- [x] 5.1 RED: nebula-agent `tests/unit_tests/test_collection_voucher.py` —
      `MCP_TOOL_NAME=="create_collection_vouchers"`; fail-closed; `_format_success`
      lists all voucher identities.
- [x] 5.2 GREEN: nebula-agent `src/agent/tools/collection_voucher.py` rename constant +
      list formatter; keep first-party `register_latest_collection_voucher`.
- [x] 5.3 TRIANGULATE: `tests/integration_tests/test_graph.py` MCP name patches; replay
      list identity.
- [x] 5.4 GREEN: nebula-agent `openspec/specs/collection-voucher-registration/spec.md` —
      one voucher per payment, exact MCP name, list identity.
- [x] 5.5 Structural: collection `openspec/config.yaml` widen context + apply `roots`
      include `/home/crisd/projects/nebula/nebula-agent`; both `AGENTS.md`;
      `readme/DESCRIPTION.md`. Triangulation skipped: config/docs.
- [x] 5.6 REFACTOR: from nebula-agent `uv run make test` +
      `uv run make integration_tests` + `uv run make lint`; collection scoped
      pre-commit.
