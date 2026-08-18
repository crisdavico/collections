# Tasks: Read-only MCP `get_seller_id`

## Review Workload Forecast

| Field                   | Value           |
| ----------------------- | --------------- |
| Estimated changed lines | 180–260         |
| 400-line budget risk    | Low             |
| Chained PRs recommended | No              |
| Suggested split         | Single PR       |
| Delivery strategy       | ask-on-risk     |
| Chain strategy          | stacked-to-main |

Decision needed before apply: No Chained PRs recommended: No Chain strategy:
stacked-to-main 400-line budget risk: Low

### Suggested Work Units

| Unit | Goal                           | Likely PR | Focused test command                                                             | Runtime harness                                                                                                              | Rollback boundary                                                                                                                                                              |
| ---- | ------------------------------ | --------- | -------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1    | `get_seller_id` + tests + docs | PR 1      | Seedian root `/home/crisd/projects/seedian/seedian`: `invoke test -m collection` | Same root: `invoke install -m collection` (or `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init`) | Drop `tools/seller_lookup.py`; revert `tools/__init__.py`, `tests/test_collection_mcp_seller_lookup.py`, `tests/__init__.py`, `AGENTS.md`, `readme/DESCRIPTION.md`. No schema. |

Edits stay in the collection git dir. Invoke/pre-commit run from Seedian root. Nebula
out of scope. Do not edit `tools/collection_voucher.py`.

## Phase 1: Test harness (RED)

- [x] 1.1 Import `test_collection_mcp_seller_lookup` in `tests/__init__.py`.
- [x] 1.2 Create `tests/test_collection_mcp_seller_lookup.py` (`TransactionCase`; copy
      `_create_user` from `tests/test_collection_mcp_tool.py`; set `partner_id.phone`).
- [x] 1.3 RED discovery: `get_tool_index`/`get_tools` — `get_seller_id` is
      `category=read`, `registry=mcp`, `kind=method`; no DB `muk_mcp.tool` row.
- [x] 1.4 RED spec Unique internal match: `_call` → JSON `{"seller_id": <positive int>}`
      only; vouchers unchanged.

## Phase 2: Mixin (GREEN min)

- [x] 2.1 Create `tools/seller_lookup.py` (AGPL): `_inherit = "muk_mcp.mixin"`;
      `@mcp_tool(name="get_seller_id", category="read", registry="mcp")`;
      `get_seller_id(self, mobile: str) -> dict`.
- [x] 2.2 Add `from . import seller_lookup` in `tools/__init__.py`.
- [x] 2.3 GREEN: `AccessError` unless `base.group_user`; `@api.model`/`@api.private`
      `_collection_normalize_ar_mobile` (digits, strip `54` then one `9`); search
      `res.users` (`share=False`, phone set, active); exact normalize; one hit →
      `_collection_require_internal_seller`; return `{seller_id}`; never `sudo()`.

## Phase 3: Fail-closed specs (RED then GREEN)

- [x] 3.1 RED→GREEN spec Portal or public caller denied: portal **and** public `_call` →
      `AccessError`.
- [x] 3.2 RED→GREEN spec Empty whitespace or invalid mobile: empty/whitespace/no digits
      → `UserError`.
- [x] 3.3 RED→GREEN spec AR variants: stored `+54 9 11 1234-5678`; `5491112345678` and
      `1112345678` → same `seller_id`.
- [x] 3.4 RED→GREEN spec Zero matches fail closed: no internal phone → `UserError`.
- [x] 3.5 RED→GREEN spec Many internal matches: two internals same normalize →
      `UserError` (no pick-first).
- [x] 3.6 RED→GREEN spec Portal share digits excluded: portal/share same digits + one
      internal → internal `seller_id`.
- [x] 3.7 RED→GREEN spec Portal-only digits: only portal/share phone → `UserError`.
- [x] 3.8 RED→GREEN spec Unique hit fails seller bar: unique match lacking
      `base.group_user` → `UserError`.
- [x] 3.9 RED→GREEN spec Employee `mobile_phone` is not a match field: source has no
      `mobile_phone` / `.sudo(` (Path/`inspect`; no `hr`).

## Phase 4: Docs + verify

- [x] 4.1 Update `AGENTS.md`: read MCP `get_seller_id`; WhatsApp = no connector; MCP
      `mobile` allowed.
- [x] 4.2 Update `readme/DESCRIPTION.md` with `get_seller_id`.
- [x] 4.3 Seedian root: `invoke install -m collection` (or
      `odoo -d devel -u collection --stop-after-init`).
- [x] 4.4 Seedian root: `invoke test -m collection` then
      `pre-commit run --files odoo/custom/src/private/collection/**`.
