# Proposal: Atomic idempotent `create_nebula_voucher` MCP tool

## Intent

Nebula agents need a MuK MCP write tool to register vouchers with nested payments
without duplicates on retry. Manual UI stays; agents get one ACL-preserving atomic
create/replay returning voucher and payment identities.

## Assumptions

- Exploration Approach 1 (`@mcp_tool` on `muk_mcp.mixin`, not DB tool).
- Hard `muk_mcp` depend OK (already aggregated).
- Q-round skipped; brief + exploration locked.

## Scope

### In Scope

- `seedian_nebula` only: `depends` += `muk_mcp`; `tools/` mixin method
  `create_nebula_voucher` (`category=write`, `registry=mcp`).
- Contract: require `customer_identification` + non-empty `payments`; no `received_date`
  input; company currency; `state=new`; all existing payment fields; MCP requires
  non-empty `document_id` (Char nullable for UI); return voucher `id`/`name`/`state` +
  payment `id`/`document_id`; no sudo; ACL unchanged.
- Idempotency: all-new → create; full same-voucher match → return; in-call dups /
  partial / cross-voucher → reject; unique `document_id` + IntegrityError race (design).
- Drop `received_date`; views use readonly `create_date`; migration drops column (**BI /
  archive-gate**). Strict TDD.

### Out of Scope

- WhatsApp, HTTP API, agent, OCR, attachments, partner/CRM.
- New groups/rules; MCP validate/reject; multi-currency; DB `muk_mcp.tool` rows; edits
  outside `seedian_nebula` (except manifest `depends`).

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `seedian-nebula-vouchers`: drop `received_date`; UI → `create_date`; nullable unique
  `document_id`; ADDED MCP auth/validation/idempotency/response.

## Approach

`muk_mcp.mixin` + `@api.model` `@mcp_tool`: validate → lookup → savepoint create or
replay/reject → JSON. No sudo. Schema in `to_strict_schema` allowlist.

## Affected Areas

| Area                                  | Impact  | Description                               |
| ------------------------------------- | ------- | ----------------------------------------- |
| `__manifest__.py`, `__init__.py`      | Mod     | `muk_mcp`; import `tools`                 |
| `tools/nebula_voucher.py`             | New     | Mixin + tool                              |
| `models/*voucher*.py`, `*payment*.py` | Mod     | Drop date; add `document_id` unique       |
| `views/seedian_nebula_views.xml`      | Mod     | `create_date`                             |
| `migrations/19.0.x/`                  | New     | Drop column                               |
| MCP + voucher/UI tests                | New/Mod | Tool, idempotency, ACL; drop date asserts |

## Risks

| Risk                                 | Likelihood   | Mitigation                            |
| ------------------------------------ | ------------ | ------------------------------------- |
| Concurrent identical calls duplicate | Med          | Unique + IntegrityError reject/replay |
| Column drop loses history            | High if data | Migration + archive warn; BI          |
| Schema keywords silently stripped    | Med          | Design against allowlist              |
| Hard `muk_mcp` depend                | Low          | Confirm target installs               |

## Rollback Plan

Revert prior module version (tool unregister). Dropped date values unrecovered —
snapshot non-empty DBs first.

## Dependencies

- `muk_mcp` method tools; voucher/payment ACL.

## Success Criteria

- [ ] Atomic create; retry same voucher; conflicts reject cleanly.
- [ ] No sudo; UI lines w/o `document_id` OK; `create_date` in UI.
- [ ] `received_date` gone; module tests pass.

## Proposal question round

Deferred: (1) race → reject vs replay? (2) reject if customer differs on match? (3)
confirm `muk_mcp` always co-installed?
