# Design: Read-only MCP `get_seller_id`

## Technical Approach

Add a method-discovered MuK read tool on a sibling mixin so MCP callers resolve an
internal `res.users` id from the seller’s own WhatsApp/mobile. Maps to proposal
`seller-lookup` and specs/seller-lookup/spec.md. Reuse
`_collection_require_internal_seller` from `tools/collection_voucher.py`. Never
`sudo()`, never a DB `muk_mcp.tool` row, never generic MuK `search_read`. Nebula and
`create_collection_vouchers` stay unchanged.

## Architecture Decisions

| Decision | Options                                                             | Tradeoff                                                                   | Choice                                                                                               |
| -------- | ------------------------------------------------------------------- | -------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Layout   | Sibling `tools/seller_lookup.py` vs extend write mixin              | Extra import vs mix read/write                                             | Sibling `_inherit = "muk_mcp.mixin"` (write file ~437 lines)                                         |
| Auth     | Explicit `base.group_user` vs voucher ACL vs `res.users` search ACL | This tool never touches vouchers; portal search may be empty → `UserError` | Raise `AccessError` first if caller lacks `base.group_user` (catalog-style tests)                    |
| Search   | Normalize-filter vs ORM `=`/`ilike` vs `phone_sanitized`            | Stored `+54 9 …` vs `549…` vs local 10 digits                              | Load `share=False`, non-empty `phone`, default active; exact normalize; exactly one; then seller bar |
| Field    | `res.users.phone` vs partner `mobile` vs `hr.employee.mobile_phone` | Odoo 19 has no partner `mobile`; no `hr` dep                               | Phone only                                                                                           |
| Helpers  | Mixin `_collection_*` vs module functions                           | Matches write mixin; merged model can call seller bar                      | `_collection_normalize_ar_mobile` + candidate match + existing bar                                   |
| Tests    | `test_collection_mcp_seller_lookup.py` vs `…_get_seller_id.py`      | Proposal name; no collision                                                | Proposal filename                                                                                    |

Rejected: pick-first on duplicates; `sudo()`; filling invoke context; stamping vouchers.

## Data Flow

```
MCP _call(get_seller_id, {mobile})
  → AccessError unless caller has base.group_user
  → needle = normalize(mobile); empty → UserError
  → search res.users (caller env, share=False, phone set, active_test)
  → filter where normalize(phone) == needle
  → 0 or 2+ → UserError
  → _collection_require_internal_seller(id) → {seller_id: int}
```

Portal/share rows never enter the candidate set. Unique hit still runs the write-path
seller bar (exists, not share, `base.group_user`).

## File Changes

| File                                         | Action | Description                                                         |
| -------------------------------------------- | ------ | ------------------------------------------------------------------- |
| `tools/seller_lookup.py`                     | Create | `@mcp_tool` `get_seller_id`; normalize + match helpers; AGPL header |
| `tools/__init__.py`                          | Modify | `from . import seller_lookup`                                       |
| `tests/test_collection_mcp_seller_lookup.py` | Create | TransactionCase; copy `_create_user` from MCP tests                 |
| `tests/__init__.py`                          | Modify | Import the new test module                                          |
| `AGENTS.md`                                  | Modify | Document read tool; WhatsApp = no connector, MCP `mobile` allowed   |
| `readme/DESCRIPTION.md`                      | Modify | Generated README already lists MCP; add `get_seller_id`             |

Unchanged: `tools/collection_voucher.py` (reuse helper only), models, views, sequences,
`security/ir.model.access.csv`, Nebula. No new groups or record rules.

## Interfaces / Contracts

Decorator: `@mcp_tool(name="get_seller_id", category="read", registry="mcp")` on
`get_seller_id(self, mobile: str) -> dict`. Discovery: `get_tools` / `get_tool_index`
`kind=method`; no DB row.

```python
input_schema={
    "type": "object",
    "properties": {
        "mobile": {
            "type": "string",
            "description": "Seller WhatsApp/mobile (AR variants accepted).",
        },
    },
    "required": ["mobile"],
}
```

Success JSON only: `{"seller_id": <positive int>}`. No name/PII. MuK `_call` returns
JSON text (same as write-tool tests).

Normalize (non-obvious): keep digits, strip one leading `54`, then one leading `9`.

```python
digits = re.sub(r"\D", "", value or "")
if digits.startswith("54"):
    digits = digits[2:]
if digits.startswith("9"):
    digits = digits[1:]
return digits
```

`+54 9 11 1234-5678`, `5491112345678`, and `1112345678` → `1112345678`. Empty needle →
`UserError`. New helpers: `@api.model` (add `@api.private` like catalog MCP helpers). Do
not edit the existing seller-bar method.

## Testing Strategy

Strict TDD. `invoke test -m collection`. Mirror `tests/test_collection_mcp_tool.py` +
catalog discovery ACL (portal **and** public).

| Layer       | What to Test                                                                                                                                                              | Approach                                                                                                |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Unit        | Normalize variants; empty/invalid `mobile`                                                                                                                                | Call helper / `_call`; expect `UserError`                                                               |
| Integration | Discovery `read`/`mcp`/`method`; unique match JSON keys; zero/many; portal digits excluded; portal-only digits; seller-bar fail; no `.sudo(`; no `mobile_phone` in source | `TransactionCase`; `tool_model._call`; `get_tool_index`; partner `phone`; `inspect`/`Path` like catalog |
| E2E         | N/A                                                                                                                                                                       | Not available                                                                                           |

Reuse `_create_user`; set `partner_id.phone`. Do not depend on `hr`; assert source never
references `mobile_phone`.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification,
or process-integration boundary.

## Migration / Rollout

No migration required. No model, view, sequence, or ACL CSV changes. Module upgrade
reloads Python so MuK rediscovers the method. Rollback: revert the addon; drop
`tools/seller_lookup.py` and its import.

## Open Questions

None.
