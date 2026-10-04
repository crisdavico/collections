## Exploration: seller-commission-percent

Store a 0–100 seller commission percentage in the SQLite source and on
`collection.connector.seller.binding`. Surface it through `list_sellers()`, persist it
on Import (overwrite on re-Import), and show it read-only in Collection Settings and the
connector Seller Bindings UI. Do **not** apply the rate to vouchers/allocations or
expose it on MCP / nebula-agent.

Investigation used CodeGraph (`codegraph_explore`) on both git roots after
`gentle-ai codegraph init`. XML, SQL, specs, and manifests are not in the Python symbol
graph; those were read directly (noted below). Collision paths (`draft-until-close`,
`inline-collection-allocation`, allocation test files) were not edited.

### Current State

A seller is four columns today: `id`, `name`, `mobile`, `active`. Nothing in collection,
allocations, or MCP stores or reads a rate.

**SQLite connector** (`collection_connector_sqlite`, version **19.0.1.5.0**):

- `data/database.sql` `CREATE TABLE sellers (id, name, mobile, active)` and INSERTs six
  fixture sellers (Ana…Facundo) with no rate. Facundo (`seller-006`) is `active=0`.
- `_SQLITE_REQUIRED_COLUMNS = {id, name, mobile, active}` (issubset — extra columns are
  already allowed). `_sqlite_fetch_sellers` `SELECT`s those four columns only and maps
  them to a row dict with those keys.
- `hooks.post_init_hook` → `ensure_sample_sqlite_source` rematerializes
  `data/database.sql` into `data_dir` **on install only**. There is **no** `migrations/`
  folder. `readme/DESCRIPTION.md` claims install _and upgrade_ rematerialize; that is
  not true for upgrades today.
- Tests rebuild sellers with the same four-column DDL in `_write_sellers_db`,
  `_write_debt_db`, and several inline `CREATE TABLE sellers` blocks.

**Collection list / Import** (`collection`, version **19.0.1.27.0**):

- `list_sellers()` → `_dispatch("list_sellers")` → `_format_seller_list`. Formatter
  drops inactive rows (`_row_is_active`) and emits
  `{external_seller_id, name, mobile, active, odoo_seller_id}` plus `source`. Extra
  adapter keys are **dropped**.
- Import: `action_import_enabled_sellers` → `_sync_enabled_sellers_from_connector` →
  validate → resolve users → `_collection_upsert_seller_bindings` → `Command.set` on
  `enabled_seller_ids`.
- `_collection_validate_connector_seller_rows` fail-closes **before any write** on
  missing/duplicate external ids and duplicate phones (generic `UserError`).
- `_collection_upsert_seller_bindings` is **create-only**: it builds vals for
  `(connector_id, external_seller_id, user_id)` when the external id is missing, then
  `create()`. Existing bindings are never `write()`n. Re-Import of a rate would not
  update stored values with today’s code.
- Binding model fields: `connector_id`, `external_seller_id`, `user_id`, related stored
  `company_id`. UNIQUE constraints only. No Float, no CHECK 0–100.
- Test adapter `TEST_SELLERS` (and seller-sync `ANA`/`BRUNO`/`INACTIVE`) has the same
  four keys; `_test_list_sellers` copies the dicts as-is.

**UI:**

- Connector form notebook has **Customer Bindings only** (no Seller Bindings page).
  Pattern to copy: `test_collection_customer_binding.py` notebook assertion.
- Collection Settings shows `enabled_seller_ids` (tags) + Import. No One2many of
  bindings, no commission column.
- Binding ACL: `group_user` read, `group_system` write (already).

**MCP (payloads stay unchanged — nebula-agent not inspected beyond this):**

- `get_seller_id` returns `{seller_id}` only (seller-lookup spec: no extra PII).
- `list_collection_customers` / `customer_debt` dispatch the **external** seller id via
  `_enabled_bound_external_seller_id` (returns `binding.external_seller_id` string) and
  format **customer** payloads. They never read seller list rows or binding extras.
- `list_sellers()` is ORM-only; there is no MCP seller-list tool.

**Spec:** `openspec/specs/collection-connectors/spec.md` Requirement _SQLite read-only
sellers source_ hard-codes `sellers` (`id`, `name`, `mobile`, `active`). Requirement
_SQLite read-only customer debt source_ ends with `` `database.sql` MUST NOT change. ``
Import “upsert” language does not currently require writing fields on existing bindings.

### Affected Areas

**`collection_connector_sqlite`** (separate git root):

- `data/database.sql` — add `commission_percent REAL NOT NULL DEFAULT 0` with
  `CHECK (commission_percent >= 0 AND commission_percent <= 100)`; set sample rates (Ana
  5.0, Bruno 7.5, Carla 10.0, Diego 0.0, Elena 3.0, Facundo 5.0).
- `models/collection_connector.py` — required columns, SELECT, row dict.
- `hooks.py` — install rematerialize stays; upgrades need a new script.
- `migrations/19.0.1.6.0/post-migrate.py` — **new** (none exist); call
  `ensure_sample_sqlite_source` so existing sample files gain the column.
- `tests/test_sqlite_connector.py` — `_write_sellers_db`, `_write_debt_db`, inline
  seller DDLs/INSERTs (tuples grow by one value).
- `readme/DESCRIPTION.md` — sellers schema text; keep customer/invoice schemas.
- `__manifest__.py` — `19.0.1.5.0` → `19.0.1.6.0`.

**`collection`:**

- `models/collection_connector.py` — `_format_seller_list` must copy
  `commission_percent`; missing key → `0.0`.
- `models/res_company.py` — validate range/numeric **before any write** (same
  fail-closed pattern as duplicate phones); upsert must `write` rate on existing
  bindings, not create-only.
- `models/collection_connector_seller_binding.py` —
  `Float(digits=(16, 2), required=True, default=0.0)` + Odoo 19 `models.Constraint`
  CHECK 0–100. Keep users name/phone only.
- `models/res_config_settings.py` — related readonly One2many of bindings for Settings.
- `views/collection_connector_views.xml` — add Seller Bindings notebook page (readonly
  rate).
- `views/res_config_settings_views.xml` — readonly One2many showing `Commission %`.
- `tests/common_connector.py` (`TEST_SELLERS`), `tests/test_collection_seller_sync.py`,
  `tests/test_collection_connector.py` (list shape), UI/notebook tests
  (`test_collection_customer_binding.py` pattern, `test_collection_ui.py` Settings).
- `openspec/specs/collection-connectors/spec.md` — replace the four-tuple; drop
  `` `database.sql` MUST NOT change ``; describe Import overwrite of the stored rate.
- `__manifest__.py` — `19.0.1.27.0` → `19.0.1.28.0`.

**Out of scope (do not touch):** MCP tool payloads, nebula-agent, allocations/vouchers,
`res.users`, `draft-until-close` / `inline-collection-allocation` files.

### Approaches

1. **Persist on `collection.connector.seller.binding` (connector → Import)** — SQLite
   column + `list_sellers()` field + readonly binding field overwritten on Import. Rate
   is source-system data, 1:1 with the external seller, company-scoped via the
   connector.

   - Pros: Matches settled product intent; company-scoped; users stay name/phone;
     MCP/agent stay unchanged; Settings and connector UI can show a stored value after
     Import.
   - Cons: Two addons + sample rematerialize; every sqlite test seller DDL must grow;
     existing non-sample SQLite files fail schema until operators add the column.
   - Effort: Medium

2. **Persist on `res.users`** — extra field on the internal user.

   - Pros: Visible next to the Enabled Seller tag without a bindings One2many.
   - Cons: Rate is not user identity; users are reused across companies; phone-match
     reuse would copy a rate onto a pre-existing user; fights the 1:1 connector binding.
     Rejected by maintainer.
   - Effort: Medium

3. **Live-read only (no stored binding field)** — Settings/UI call `list_sellers()` each
   time; skip binding persistence.

   - Pros: No binding `write` change; no Odoo Constraint.
   - Cons: Settings empty until a live list; no stored audit of last Import; test
     adapter and sqlite would still need the list field; re-Import overwrite of a stored
     rate is a stated requirement.
   - Effort: Low–Medium (wrong product)

4. **Apply the rate on allocations/vouchers in this cut** —
   - Pros: End-to-end commission math sooner.
   - Cons: Explicitly out of scope; couples this store-only change to allocation
     residual math and MCP.
   - Effort: High

### Recommendation

Take **approach 1**.

- Column/field: `commission_percent`. UI label: `Commission %`. Scale 0–100 (`5.0` =
  5%).
- SQLite: `REAL NOT NULL DEFAULT 0` + CHECK 0–100. Required column + SELECT.
- Collection formatter: include the key; missing → `0.0`. Invalid (`< 0`, `> 100`,
  non-numeric) → generic `UserError` in `_collection_validate_connector_seller_rows`
  before any write.
- Binding: Float + `models.Constraint` CHECK; views readonly; Import create **and**
  `write` on existing rows (today’s create-only upsert must change).
- Sample rematerialize via new `migrations/19.0.1.6.0/post-migrate.py` calling
  `ensure_sample_sqlite_source` (destructive rewrite of the **sample** file is existing
  hook behavior: `os.remove` then `executescript`).
- MCP `{seller_id}` / customer payloads unchanged. Do not change `_DISPATCH_OPS`.
- Strict TDD: RED tests on sqlite schema/list, formatter coerce/validate, upsert
  overwrite, UI arch, then implementation.

### Risks

- **Upgrade vs install:** sample SQLite on already-installed DBs stays four-column until
  a post-migrate rematerialize. Operators with a _custom_ sqlite_path must ALTER their
  file; required-column check will fail-close otherwise.
- **Create-only upsert:** forgetting the `write` path leaves Settings showing `0.0`
  after the first Import even when SQLite changes.
- **Formatter drop:** if `_format_seller_list` is not updated, sqlite can SELECT the
  column and Import still never sees it.
- **Duplicated seller DDL** in sqlite tests: any missed `_write_*` / inline schema
  breaks `list_sellers` / debt tests after the column becomes required.
- **Two-repo apply:** collection + `collection_connector_sqlite`; nebula-agent must stay
  untouched. `openspec/config.yaml` still lists nebula as an apply root — proposal
  should keep it out of this change.
- **Review size:** schema + two manifests + tests + spec + UI likely near the 400-line
  authored budget; tasks should split sqlite vs collection work units.
- **Same-workspace collision:** `draft-until-close` is dirty on allocation files; this
  change must not restage those paths.
- **Spec line** `` `database.sql` MUST NOT change `` must be removed or it will block
  the sqlite fixture update.

### Ready for Proposal

Yes. Product choices are settled (name, scale, binding home, Import overwrite, missing
key coerce, fail-closed invalid, MCP/agent/allocations out of scope). The orchestrator
should tell the user: proceed to **sdd-propose** for a store-only commission percentage
on SQLite + seller bindings, with Import overwrite and readonly UI, and no agent or
allocation math in this cut.
