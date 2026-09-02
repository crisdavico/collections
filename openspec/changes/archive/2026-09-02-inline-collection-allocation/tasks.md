# Tasks: Inline Collection Allocation

## Review Workload Forecast

| Field                   | Value              |
| ----------------------- | ------------------ |
| Estimated changed lines | 900–1400           |
| 400-line budget risk    | High               |
| Chained PRs recommended | Yes                |
| Suggested split         | PR 1 → PR 2 → PR 3 |
| Delivery strategy       | auto-chain         |
| Chain strategy          | stacked-to-main    |

Decision needed before apply: No Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

### Suggested Work Units

| Unit | Goal                                        | Likely PR | Focused test command                      | Runtime harness                  | Rollback boundary                                                                   |
| ---- | ------------------------------------------- | --------- | ----------------------------------------- | -------------------------------- | ----------------------------------------------------------------------------------- |
| 1    | Inline payments; voucher tool still exposed | PR 1      | `invoke test -m collection --mode=update` | N/A — e2e false; TransactionCase | Revert allocation tool, voucher helpers, allocation MCP tests. `@mcp_tool` unmoved. |
| 2    | `get_collection_allocation`                 | PR 2      | `invoke test -m collection --mode=update` | N/A — e2e false; TransactionCase | Delete lookup module, import, tests.                                                |
| 3    | Retire voucher MCP; `19.0.1.27.0`           | PR 3      | `invoke test -m collection --mode=update` | N/A — e2e false; TransactionCase | Restore `@mcp_tool`. Coordinated Nebula deploy before/with this slice.              |

Test command: `invoke test -m collection --mode=update` from Seedian repo root
`/home/crisd/projects/seedian/seedian`. Runtime harness: N/A — e2e false in config;
module TransactionCase is the proving command. Lint:
`pre-commit run --files odoo/custom/src/private/collection/**` from seedian root.

## Phase 1: Inline payments on create_collection_allocation

- [x] 1.1 Extract `_PAYMENT_SCHEMA`+parse in `tools/collection_voucher.py`. Keep
      `@mcp_tool` `create_collection_vouchers`.
- [x] 1.2 RED: rewrite `tests/test_collection_mcp_allocation.py`; ordered `vouchers[]`;
      freeze `{sheet_id,vouchers,allocation}` 7+4. GREEN: `payments` schema+payload.
- [x] 1.3 RED: `request_id` replay full payload. GREEN: replay `document_ids`.
- [x] 1.4 RED: exact `document_id` reuse continues. GREEN: classify dict→continue.
- [x] 1.5 RED: partial overlap conflict. GREEN: classify raise.
- [x] 1.6 RED: other-company conflict. GREEN: classify reject.
- [x] 1.7 RED: `auto_create_sheet` off named error. GREEN:
      `"This company requires a collection sheet chosen in Odoo."`
- [x] 1.8 RED: `invoices: []` on-account. GREEN: empty invoices valve.
- [x] 1.9 RED: residual without reason fails. GREEN: require reason if residual >0.
- [x] 1.10 RED: residual negative fails. GREEN: residual <0 UserError.
- [x] 1.11 RED: reason-only retry not no-op. GREEN: hash includes `residual_reason`.
- [x] 1.12 RED: revalidation rolls back vouchers. GREEN: no extra savepoint.
- [x] 1.13 RED: lazy partner+binding. GREEN: `_collection_create_vouchers`.
- [x] 1.14 RED: leak/sudo scans. GREEN: no `sudo()`; no error-body.
- [x] 1.15 Test+Lint.

## Phase 2: get_collection_allocation

- [x] 2.1 RED: discovery read/mcp/method, no DB row. GREEN:
      `tools/allocation_lookup.py`+`tools/__init__.py`.
- [x] 2.2 RED: auth AccessError/share/not-enabled. GREEN: enabled bound seller.
- [x] 2.3 RED: no open sheet → null. GREEN: `_open_sheets_for_seller`.
- [x] 2.4 RED: unbound → null, no partner. GREEN: no `resolve_customer_partner`.
- [x] 2.5 RED: sheet without allocation → null. GREEN: missing allocation null.
- [x] 2.6 RED: confirmed payload. GREEN: lists+`residual_reason`.
- [x] 2.7 RED: validated returned. GREEN: stored `state`.
- [x] 2.8 RED: multi-open `UserError`. GREEN: existing msgid.
- [x] 2.9 RED: read does not create sheet. GREEN: get never writes sheets.
- [x] 2.10 RED: no attachment/`datas`. GREEN: omit attachments.
- [x] 2.11 RED: no sudo. GREEN: no `sudo()`.
- [x] 2.12 Test+Lint.

## Phase 3: Retire create_collection_vouchers MCP

- [x] 3.1 RED: registry absence of `create_collection_vouchers`. GREEN: drop decorated
      method+schema; keep `_collection_*`.
- [x] 3.2 Delete/retarget `tests/test_collection_mcp_tool.py` create/replay/ACL;
      retarget Attachment/Provenance + `tests/test_collection_mcp_partner_resolve.py`.
- [x] 3.3 `AGENTS.md` MCP bullets + `19.0.1.27.0`.
- [x] 3.4 `__manifest__.py` `19.0.1.27.0`; no `migrations/19.0.1.27.0/`;
      `test_manifest_version_is_1_27_0`.
- [x] 3.5 Test+Lint.
