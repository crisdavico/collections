## Exploration: get-seller-id-by-mobile

Read-only MuK MCP tool that resolves an internal seller (`res.users` id) from a
WhatsApp/mobile number, in the Seedian **collection** addon only. Product decisions are
locked; this document confirms feasibility against real code.

**Investigation note:** CodeGraph MCP (`user-codegraph`) is not available in this
session. `gentle-ai codegraph init` failed (exit 127; no Node for the `codegraph` CLI).
Analysis used Read/Grep on collection, MuK MCP, and Odoo 19 core.

### Current State

Collection exposes one method-discovered MCP write tool, `create_collection_vouchers`,
on `muk_mcp.mixin` in `tools/collection_voucher.py` (`category="write"`,
`registry="mcp"`). Discovery is MRO scan of `muk_mcp.mixin` for `__mcp_tool__`
(`muk_mcp/core/tool.py:_build_method_index`); `get_tools(registry="mcp")` lists tools
regardless of category. Tests invoke
`self.env["muk_mcp.tool"]._call(name, arguments, env)` and assert `kind=method`, no DB
`muk_mcp.tool` row. `category="read"` is the decorator default and is already used by
Seedian catalog tools (`seedian_product_catalog_mcp/tools/product_catalog.py`) and MuK
built-ins.

Seller bar lives in `_collection_require_internal_seller`: browse `res.users` with no
`sudo()`, reject missing/non-int/`<=0`, then require `exists()`, `not share`, and
`has_group("base.group_user")` → `UserError`. Portal **callers** of the write tool get
`AccessError` from voucher ACL (`security/ir.model.access.csv`: `base.group_user` only),
not from that helper. Portal **seller ids** get `UserError`.

Odoo 19 `res.partner` has `phone` only — **no `mobile` field**. `res.users.phone` is
`related='partner_id.phone'` (`inherited=True`, unstored). Optional
`hr.employee.mobile_phone` exists but collection does not depend on `hr`. Optional
`phone_validation.phone_sanitized` (E164) is not a collection dependency and would
**not** match the locked Argentine rule (strip `+`, spaces, `54`, mobile `9`). Stored
formats therefore vary; exact ORM `=` on `phone` cannot implement uniqueness.

Existing specs: `collection-vouchers` (voucher lifecycle + write MCP),
`collection-sheets`, `document-review`. No `seller-lookup` capability. Fixtures in
`tests/test_collection_mcp_tool.py` and `tests/test_collection_acl.py` already create
internal (`base.group_user`) vs portal (`base.group_portal`) users via `_create_user`
(no phone today). Catalog tests show the read-tool ACL pattern: portal/public →
`AccessError`.

Settled product decisions are feasible in this addon without Nebula or write-path
changes. Collection `AGENTS.md` still lists WhatsApp as out of scope; this tool is an
MCP argument keyed by mobile, not a WhatsApp connector.

### Affected Areas

- `tools/collection_voucher.py` — reuse `_collection_require_internal_seller`; do not
  change `create_collection_vouchers` / `ContextSchema` (Nebula out of scope).
- `tools/__init__.py` — import a sibling tools module if that approach is chosen.
- `tools/seller_lookup.py` (new, if sibling) — `@mcp_tool` read method on
  `muk_mcp.mixin`.
- `tests/test_collection_mcp_seller_lookup.py` (new) and `tests/__init__.py` —
  discovery, normalize match, fail-closed, portal `AccessError`, no `sudo()`.
- `openspec/specs/seller-lookup/spec.md` (new capability; later phases).
- `AGENTS.md` / `openspec/config.yaml` MCP notes — later phases only: document the read
  tool; keep “no WhatsApp inside the addon”.
- **Not affected:** Nebula, `register_latest_collection_voucher`, voucher ACL/CSV,
  `create_collection_vouchers` schema, other OpenSpec change
  `sheet-scoped-document-review`.

### Approaches

**A. Spec placement**

1. **New capability `seller-lookup`** — dedicated spec for the read tool.

   - Pros: does not mix identity lookup into voucher create/idempotency; avoids fighting
     `collection-vouchers` purpose (“No WhatsApp/API/agent”); write MCP requirement
     stays unchanged.
   - Cons: one more spec directory to archive later.
   - Effort: Low

2. **Delta on `collection-vouchers`** — add a requirement beside
   `create_collection_vouchers`.
   - Pros: seller_id already lives in that spec.
   - Cons: lookup does not create/stamp vouchers and must not replace connector
     `seller_id`; purpose and “deferred integrations” text would need careful surgery.
   - Effort: Low–Medium

**B. Mixin file**

1. **Sibling `tools/seller_lookup.py`** — second `_inherit = "muk_mcp.mixin"` class.

   - Pros: write file is already ~437 lines; read vs write SRP; MuK still discovers via
     mixin MRO; can call `_collection_require_internal_seller` on the merged model;
     matches catalog’s dedicated tools module.
   - Cons: extra import in `tools/__init__.py`.
   - Effort: Low

2. **Extend `tools/collection_voucher.py`** — add `@mcp_tool` on `CollectionMcpMixin`.
   - Pros: one file; AGENTS.md already points helpers here.
   - Cons: mixes a read lookup into a write-heavy module; harder review.
   - Effort: Low

**C. Search strategy**

1. **Load candidates then normalize-filter** — search `res.users` in caller env
   (`share=False`, non-empty `phone`, default `active`); normalize argument and each
   `phone`; require **exactly one** hit; then `_collection_require_internal_seller`.

   - Pros: matches locked Argentine/WhatsApp normalize; format-agnostic; portal rows
     excluded before uniqueness; no `phone_validation` / `hr` dependency.
   - Cons: scans internal users with a phone (fine at seller scale).
   - Effort: Low

2. **ORM domain only** (`ilike` / `=` on `phone`).

   - Pros: one query.
   - Cons: stored `+54 9 …` vs `549…` vs local 10 digits will miss or false-match;
     cannot express “strip 54 then 9” in a domain.
   - Effort: Low (wrong)

3. **Depend on `phone_validation.phone_sanitized` (E164).**
   - Pros: indexed sanitized column when that module is installed.
   - Cons: new dependency; E164 keeps country `54` and often mobile `9`, which is the
     opposite of the locked normalize; not always present.
   - Effort: Medium (wrong)

### Recommendation

- **Spec:** new capability `seller-lookup`. Keep `collection-vouchers` write MCP and
  voucher `seller_id` requirements unchanged. This tool returns `{seller_id}` to the MCP
  caller/LLM only; it does not fill invoke context and does not replace connector
  `seller_id` on `create_collection_vouchers`.
- **Code layout:** sibling `tools/seller_lookup.py` inheriting `muk_mcp.mixin`,
  `category="read"`, `registry="mcp"`, no DB tool row, never `sudo()`. Reuse
  `_collection_require_internal_seller` after a unique match. Deny portal/public
  **callers** with `AccessError` (explicit `base.group_user` check; voucher
  `check_access` is optional extra). Empty/invalid mobile, zero matches, or many
  internal matches → `UserError` (fail closed, no pick-first).
- **Lookup field:** `res.users.phone` / `partner_id.phone` only. Do not invent `mobile`
  on partner; do not search `hr.employee.mobile_phone`.
- **Search:** candidate load then exact normalize (strip `+`, whitespace, punctuation,
  leading `54`, then a single leading mobile `9`). Suggested tool name:
  `get_seller_id_by_mobile`.
- **Tests:** new `TransactionCase` file using existing `_create_user` plus `phone` on
  the partner; discovery via `get_tool_index` / `_call`; variant numbers; portal user
  with the same digits must not count; portal/public caller `AccessError`; source has no
  `sudo()`. Strict TDD (`openspec/config.yaml`).

### Risks

- Sellers who only store WhatsApp on `hr.employee.mobile_phone` (or another field) will
  not match until `res.users.phone` is populated.
- Duplicate normalized numbers among internal users fail closed (operational data issue,
  not a pick-first escape).
- `phone_validation` onchange may store INTERNATIONAL form in some DBs; normalize-filter
  handles that, E164 search would not.
- Collection `AGENTS.md` “no WhatsApp” wording can confuse later agents unless apply
  updates it to allow this MCP read tool.
- CodeGraph was unavailable; MuK/Odoo conclusions are from direct source reads.

### Ready for Proposal

Yes. Product decisions are feasible in collection MCP only. Orchestrator should run
`sdd-propose` for `get-seller-id-by-mobile` with: new `seller-lookup` capability,
sibling read-tool module, candidate-then-normalize search, reuse of
`_collection_require_internal_seller`, Nebula out of scope.
