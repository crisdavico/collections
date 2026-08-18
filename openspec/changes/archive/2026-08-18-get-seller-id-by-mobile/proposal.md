# Proposal: Read-only MCP `get_seller_id`

## Intent

MCP callers need a company seller’s `res.users` id from the **seller’s own**
WhatsApp/mobile. Collection only has write tool `create_collection_vouchers`. Add a
read-only MCP tool returning `{ "seller_id": <int> }` to the caller/LLM.

Settled: not customer phone; no invoke-context fill; no connector `seller_id` replace on
voucher writes. **Nebula is out of scope** (overrides `config.yaml` Nebula-in-scope
`rules.proposal` bullet). Odoo edits stay in collection.

## Scope

### In Scope

- MuK MCP `get_seller_id` (`category=read`, `registry=mcp`); required `mobile: string`;
  output `{ "seller_id": <int> }` only.
- Normalize AR/WhatsApp (strip `+`, spaces/punctuation, `54`, then one mobile `9`);
  exactly one internal user; zero/many → `UserError`.
- Reuse `_collection_require_internal_seller`. Portal/public callers → `AccessError`. No
  `sudo()`. No DB `muk_mcp.tool` row.
- New `TransactionCase` tests (discovery, variants, portal phone excluded, AccessError,
  no `.sudo(`).
- Clarify `AGENTS.md` “no WhatsApp” to allow this MCP read tool.

### Out of Scope

- Nebula, `register_latest_collection_voucher`, `ContextSchema.seller_id`,
  `create_collection_vouchers` payload.
- Partner `mobile`, `hr.employee.mobile_phone`, `phone_validation` / `hr`.
- Filling invoke context or stamping vouchers.
- Sibling `sheet-scoped-document-review`.

## Capabilities

> Existing specs: `collection-vouchers`, `collection-sheets`, `document-review`.

### New Capabilities

- `seller-lookup`: read-only MCP lookup of internal seller id from `res.users.phone` /
  `partner_id.phone`.

### Modified Capabilities

- None

## Approach

Sibling `tools/seller_lookup.py` on `muk_mcp.mixin` (import in `tools/__init__.py`).
Load candidates (`share=False`, non-empty `phone`, `active`), normalize-filter, one hit,
then `_collection_require_internal_seller`. Phone only (Odoo 19 has no partner
`mobile`). Name `get_seller_id` does not collide with collection or catalog MCP tools.
Strict TDD.

## Affected Areas

| Area                                                              | Impact       | Description                 |
| ----------------------------------------------------------------- | ------------ | --------------------------- |
| `tools/seller_lookup.py`                                          | New          | `@mcp_tool` `get_seller_id` |
| `tools/__init__.py`                                               | Modified     | Import sibling              |
| `tools/collection_voucher.py`                                     | Unchanged    | Reuse seller helper         |
| `tests/test_collection_mcp_seller_lookup.py`, `tests/__init__.py` | New/Modified | TransactionCase             |
| `AGENTS.md`                                                       | Modified     | Document read tool          |
| Models / views / ACL CSV                                          | Unchanged    | No new groups or UI         |

## Risks

| Risk                                        | Likelihood | Mitigation                         |
| ------------------------------------------- | ---------- | ---------------------------------- |
| WhatsApp only on `hr.employee.mobile_phone` | Med        | Require `res.users.phone`; no `hr` |
| Duplicate normalized internals              | Med        | Fail closed; ops fix               |
| INTERNATIONAL vs local stored forms         | Low        | Normalize-filter, not ORM `=`      |
| AGENTS.md “no WhatsApp” misread as ban      | Med        | Apply-phase doc update             |

## Rollback Plan

Revert the collection module; drop `tools/seller_lookup.py` and its import. No schema
migration. Write MCP unchanged.

## Dependencies

- `muk_mcp` method discovery; `_collection_require_internal_seller`; partner `phone`.

## Success Criteria

- [ ] Unique normalized internal phone → `{ "seller_id": <int> }` only.
- [ ] Empty/invalid, zero/many matches, portal seller digits → `UserError`.
- [ ] Portal/public caller → `AccessError`; no `.sudo(` in source.
- [ ] Write MCP / Nebula unchanged; `invoke test -m collection` passes.
