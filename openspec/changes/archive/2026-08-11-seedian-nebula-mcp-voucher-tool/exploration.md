# Exploration: Atomic idempotent `create_nebula_voucher` MCP write tool

## Current State

`seedian_nebula` (`odoo/custom/src/private/seedian_nebula/`, depends on `base`, `mail`
only) implements manual payment vouchers backed by:

- `seedian.nebula.voucher` (`mail.thread`, `mail.activity.mixin`): `name` (sequence
  `seedian.nebula.voucher` → `NEB/<year>/<0000>`), `customer_identification` (required),
  `received_date` (required, defaults to `fields.Date.context_today`), `state`
  (`new`/`validated`/`rejected`, default `new`), `currency_id` (default
  `env.company.currency_id`), `payment_ids` (One2many).
- `seedian.nebula.payment`: `voucher_id` (M2O cascade), `document_type`
  (`bank_transfer`/`check`/`cash_deposit`/`unsupported`, **required**), plus nullable
  `amount`, `currency_id` (related), `from_account`, `to_account`, `voucher_number`,
  `voucher_date`, `check_number`, `check_bank`, `check_issue_date`,
  `check_payment_date`, `check_type` (`common`/`deferred`). No `document_id` field
  exists today.
- ACL: full CRUD for `base.group_user` on both models, no record rules, no dedicated
  groups (`security/ir.model.access.csv`).
- Views (`views/seedian_nebula_views.xml`): list/search/kanban/form all display
  `received_date`; form shows statusbar, Validate/Reject buttons (only when
  `state == 'new'`), editable payment lines, `<chatter/>`.
- Tests: `test_seedian_nebula_voucher.py` (sequence, defaults incl. `received_date`,
  required-field IntegrityErrors, state transitions, unlink guard, payment field
  persistence), `test_seedian_nebula_acl.py`, `test_seedian_nebula_mail.py`,
  `test_seedian_nebula_ui.py`. Spec `openspec/specs/seedian-nebula-vouchers/spec.md`
  requires `received_date` explicitly
  (`Requirement: Voucher header fields and defaults`).
- No HTTP controllers, no `muk_mcp` dependency, no `tools/` package exist yet in this
  module.

**`muk_mcp`** (`muk-it/odoo-modules`, aggregated on disk at
`odoo/custom/src/muk-it/odoo-modules/muk_mcp/`, declared in `repos.yaml`/`addons.yaml`,
**not currently a `seedian_nebula` dependency**) provides the extension pattern this
change must follow:

- `muk_mcp.mixin` (`AbstractModel`) is the base MCP tool mixin. Other modules add tools
  by declaring `_inherit = 'muk_mcp.mixin'` in their own class (see
  `muk_mcp/mcp/write.py` for `create_records`/`update_records`/`delete_records`).
- `odoo.addons.muk_mcp.core.tool.mcp_tool(name=..., description=..., input_schema=..., category=..., registry=..., meta=...)`
  decorates an `@api.model` method and stamps `func.__mcp_tool__`.
  `core/tool.py::_build_method_index` scans the `muk_mcp.mixin` MRO for these stamped
  methods at call time — **no XML/DB record is created**; this is exactly the "method,
  not `muk_mcp.tool` row" registration path the task requires. `to_strict_schema`
  (`tools/schema.py`) restricts `input_schema` to a fixed key allowlist (`type`,
  `properties`, `required`, `items`, `enum`, `nullable`, …) — no
  `additionalProperties`/`$ref`/`oneOf`, so the nested `payments` array schema must stay
  within that vocabulary.
- Dispatch: `models/tool.py::_execute` resolves `kind == 'method'` entries via
  `func(env[entry['model']], **arguments)` — i.e. `env['muk_mcp.mixin']` (or whichever
  concrete inheriting model, since Odoo merges `_inherit` into one class) called
  **without any `sudo()`**, using the `env` built from the authenticated request. Every
  existing write tool (`create_records`, `update_records`, `delete_records` in
  `mcp/write.py`) follows the same no-sudo pattern and relies on normal ORM
  create/write/unlink to enforce ACL — confirming "no sudo, ACL preserved" is the
  established convention, not a special case to invent.
- Identity: `controllers/mcp.py::_handle_tools_call` → `muk_mcp.tool._call` →
  `_execute`; `env.uid` comes from the resolved MCP key's `user_id`
  (`models/key.py::authenticate`, always a real `res.users`, checked active). So the
  caller genuinely is an internal Odoo user and existing `base.group_user` ACL rows
  already gate the tool — no new security group is required as long as that user has
  `base.group_user` (already granted access to `seedian.nebula.voucher/payment`).
- Category/registry: `muk_mcp.tool.category` Selection is only `read`/`write`;
  `registry` is a free-form comma-separated string matched by
  `get_tool_index(registry=...)` — `category='write', registry='mcp'` on the decorator
  is exactly the shape `mcp/write.py` uses.
- Atomicity precedent: `_mcp_create_records` wraps `create()` +
  `_mcp_assert_records_allowed` in `self.env.cr.savepoint()` and rolls back the insert
  if the post-create check fails — the same technique (an inner savepoint) is the
  natural fit for "all rows or none" voucher+lines creation.
- Tests precedent: `muk_mcp/tests/test_tools.py` and `test_acl_isolation.py` call tools
  in-process via `self.tool_model._call(name, arguments, self.env(user=...))` and assert
  on the decoded JSON result or raised `AccessError`/`UserError` — this is the pattern
  to reuse for `create_nebula_voucher` tests instead of spinning up real HTTP/JSON-RPC.

## Affected Areas

- `odoo/custom/src/private/seedian_nebula/__manifest__.py` — add `muk_mcp` to `depends`;
  bump version; register new `tools/` package files under `data`/python import only (no
  XML needed for a method-kind tool); likely add `migrations/`.
- `odoo/custom/src/private/seedian_nebula/__init__.py` — add `from . import tools`.
- `odoo/custom/src/private/seedian_nebula/tools/__init__.py`, `tools/nebula_voucher.py`
  (new) — `MCPMixin(models.AbstractModel)` with `_inherit = 'muk_mcp.mixin'` and the
  `@api.model @mcp_tool(...)` method implementing `create_nebula_voucher`.
- `odoo/custom/src/private/seedian_nebula/models/seedian_nebula_voucher.py` — remove
  `received_date` field (breaks `create()` default logic only incidentally: the
  sequence-assignment override is untouched).
- `odoo/custom/src/private/seedian_nebula/models/seedian_nebula_payment.py` — add
  `document_id` (Char, nullable, indexed) plus a
  `models.Constraint('unique (document_id)', ...)` (Postgres unique constraints allow
  unlimited NULLs, so manual UI lines with no `document_id` are unaffected) to make
  idempotency race-safe under concurrent identical calls.
- `odoo/custom/src/private/seedian_nebula/views/seedian_nebula_views.xml` — remove
  `received_date` from list/search(+group-by filter)/kanban/form; add readonly
  `create_date` in its place per the task intent.
- `odoo/custom/src/private/seedian_nebula/migrations/19.0.1.1.0/` (new, version bump) —
  drop the now-unused `received_date` column; a real `prod.sql.gz` dump exists for this
  repo, so silently leaving an orphaned NOT NULL column is not safe to skip even though
  this is pre-GA.
- `odoo/custom/src/private/seedian_nebula/tests/test_seedian_nebula_voucher.py` — delete
  `test_received_date_required`, fix `test_defaults_on_create` (drop the `received_date`
  assertion).
- `odoo/custom/src/private/seedian_nebula/tests/test_seedian_nebula_mcp_tool.py` (new) —
  TDD coverage for the tool (see Recommendation).
- `odoo/custom/src/private/seedian_nebula/openspec/specs/seedian-nebula-vouchers/spec.md`
  — will need a `MODIFIED Requirement: Voucher header fields and defaults` (drop
  `received_date`) and an `ADDED Requirement` for the MCP tool contract in the
  `sdd-spec` phase (not written now — exploration only).
- `odoo/custom/src/repos.yaml` / `addons.yaml` — already declare `muk_mcp`
  (`muk-it/odoo-modules`); no change needed there, only the manifest `depends`.

## Approaches

1. **Method-kind `@mcp_tool` on an inherited `muk_mcp.mixin`** (what the task
   prescribes) — a new `tools/nebula_voucher.py` class with `_inherit = 'muk_mcp.mixin'`
   and one `@api.model @mcp_tool(category='write', registry='mcp')` method implementing
   validation, idempotency lookup, and atomic create in plain Python.

   - Pros: Reviewable/typed/lintable Python; directly unit-testable via
     `TransactionCase` + `tool_model._call(...)`, exactly like `muk_mcp`'s own test
     suite; no sudo needed — ACL enforced by ORM the same way as
     `create_records`/`update_records`; savepoint-based atomicity is a proven pattern
     already in `muk_mcp/mcp/write.py`; ships with the module (versioned in git,
     survives `git-aggregate` re-pulls of `muk_mcp`, no XML data upgrade needed).
   - Cons: Adds a new hard dependency (`muk_mcp`) to `seedian_nebula`; input schema is
     constrained to `to_strict_schema`'s allowed keys, so the nested `payments` array
     item schema must be expressed without `oneOf`/`additionalProperties`; must respect
     the `muk_mcp.mixin` MRO/no-duplicate-tool-name contract (tool names must be
     globally unique across every mixin-extending module in the DB).
   - Effort: Medium.

2. **DB `muk_mcp.tool` record with Python `code` (safe_eval sandbox)** — declare the
   tool as XML `data/tool.xml` with an inline Python snippet, matching how the MuK
   "Playground" custom-tool feature works (`models/tool.py::_run`).

   - Pros: No new Python dependency wiring beyond `depends: ["muk_mcp"]`; editable from
     the backend UI without a module upgrade; officially supported extension surface.
   - Cons: Explicitly excluded by the task ("NOT a DB `muk_mcp.tool` record"); business
     logic lives as an untyped text blob evaluated through `safe_eval`, hard to
     unit-test directly (must go through `_call`/`_run` every time, no direct Python
     function to call or mock); no static analysis/pre-commit coverage of the actual
     logic; idempotency/atomicity logic of this complexity is risky to maintain as a
     string.
   - Effort: Low upfront, High long-term maintenance risk.

3. **No new tool — expose voucher creation through existing generic `create_records`**
   (client sends `model: "seedian.nebula.voucher"`, `values` with a
   `payment_ids: [[0, 0, {...}]]` One2many command).
   - Pros: Zero new code in `seedian_nebula`; nothing to register or test.
   - Cons: `create_records` has no idempotency semantics at all — a network retry from
     the AI client would create a duplicate voucher; the client must know Odoo's
     One2many command-tuple syntax and the full nested field list; no `document_id`
     validation; does not satisfy "atomic idempotent" requirement, which is the entire
     point of this change.
   - Effort: None (but fails the requirement).

## Recommendation

**Approach 1.** It is also the only one that satisfies the task's explicit constraints
(method on `muk_mcp.mixin`, `category="write"`, `registry="mcp"`, no DB tool record).
Key implementation notes for the next phases:

- **Idempotency/atomicity algorithm** (single `@api.model` method, one DB round trip for
  the lookup):
  1. Validate `customer_identification` truthy and `payments` a non-empty list; for each
     payment require non-empty `document_id` — raise `UserError` before touching the DB
     otherwise (mirrors `_mcp_update_records`'s "no record IDs provided" style).
  2. Reject if the submitted `document_id`s contain duplicates within the same call.
  3. `search_read` existing `seedian.nebula.payment` rows whose `document_id` is in the
     submitted set, reading `document_id` and `voucher_id`.
  4. Branch: **zero matches** → create path; **matches cover every submitted id and all
     share one `voucher_id`** → idempotent replay, return that voucher's info unchanged
     (no writes); **anything else** (partial overlap, or matches spanning more than one
     `voucher_id`) → reject the whole call with `UserError`, no writes.
  5. Create path runs inside `self.env.cr.savepoint()`: create the voucher (no
     `received_date` to pass; currency stays the model default; `state` stays `new`
     implicitly), then `create()` all payment lines in one batched call
     (`Payment.create([...])`, not a loop — see repo `odoo-19-performance-guide.md`
     anti-pattern table), each carrying its `document_id`.
  6. Add the `document_id` unique constraint (`models.Constraint`) so a genuine race
     between two concurrent first-time calls with the same ids is caught at the DB
     level; catch the resulting `IntegrityError`/`UniqueViolation` inside the savepoint
     and translate it into the same "reject/replay" decision rather than a raw 500 —
     flag this concurrency edge case explicitly in `design.md` since it is the subtle
     part of "atomic and idempotent".
  7. Return shape: voucher `id`, `name` (sequence reference), `state`, and a
     payment-line mapping (`id` + `document_id`) per created/existing line — matches the
     "return voucher ID, sequence reference, state, payment ID/document-ID mappings"
     requirement and mirrors `_mcp_create_records`'s `{id, display_name}` convention.
- **Schema**: `input_schema` for `payments` items should list every existing nullable
  payment field plus `document_id` (required in the item schema) and `document_type`
  (already required at the model level, so also required here) — reuse
  `tools/descriptions.py` style helpers where sensible, but this module owns its own
  schema dict (it should not import `muk_mcp`'s private helpers beyond `mcp_tool`
  itself, to avoid coupling to internals not part of the documented decorator API).
- **`document_id` field**: nullable Char on `seedian.nebula.payment`, no `required=True`
  at the model level (manual UI-created lines never set it), enforced only inside the
  tool's own validation — matches "Odoo field stays nullable for manual UI lines".
- **received_date removal**: drop the field, its default, its tracking, its 3 view
  occurrences (list/search+groupby/kanban/form) and its 2 tests; add a migration to drop
  the column; replace with a readonly `create_date` field in the same view slots (list
  column, search groupby, kanban footer, form group) — `create_date` already exists on
  every model, no model change required for it, only view XML + spec text.
- **Spec/tests to update in later phases**: `sdd-spec` must MODIFY "Voucher header
  fields and defaults" (drop `received_date` scenarios) and ADD a new requirement
  describing the tool's authorization, validation, idempotency and response contract
  with Given/When/Then scenarios for: all-new create, exact-retry, duplicate-in-call,
  partial-conflict, cross-voucher-conflict, non-`base.group_user` caller denial.

## Risks

- **Concurrency correctness**: without careful savepoint + unique-constraint handling,
  two near-simultaneous identical MCP calls (a classic client-side retry scenario) could
  both pass the "no existing rows" check before either commits, producing two vouchers
  for the same `document_id`s — the DB unique constraint plus IntegrityError handling in
  `design.md`/`tasks.md` must be treated as a first-class requirement, not an
  afterthought.
- **`received_date` column drop on a non-empty DB**: `prod.sql.gz` is checked into the
  repo, implying real historical data may exist; the migration step must be reviewed
  before archiving so no destructive drop ships without the `openspec/config.yaml`
  `rules.archive` "warn before merging destructive deltas" gate being honored.
  `sdd-propose`/`sdd-design` should explicitly flag this as backward-incompatible.
- **Strict input schema vocabulary**: `to_strict_schema` silently drops any JSON-Schema
  keyword outside its allowlist (e.g. `additionalProperties`, `oneOf`, `$ref` would be
  stripped, not rejected) — the nested `payments` schema must be validated against that
  allowlist during `sdd-design`/`sdd-apply`, or the AI client will receive a
  weaker-than-intended schema without any error surfaced.
- **New hard dependency**: adding `muk_mcp` to `seedian_nebula`'s `depends` means this
  addon can no longer install without the MCP server module also being present/enabled;
  confirm this is acceptable for all target environments (dev/prod) before `sdd-propose`
  locks it in.
- **Global tool-name uniqueness**: `_build_method_index` raises `ValueError` if two
  mixin methods anywhere declare the same `name='create_nebula_voucher'` — low risk
  today (single module) but worth a one-line note in `design.md` for future extension
  authors.

## Ready for Proposal

Yes. The requirements given are already specific enough (tool name, category, registry,
mixin/decorator target, idempotency semantics, `document_id` nullability,
`received_date` removal) that `sdd-propose` can proceed directly using Approach 1 above;
the main open items to resolve during `sdd-propose`/`sdd-design` are the exact
IntegrityError-based race handling and the destructive-migration sign-off, both flagged
under Risks.
