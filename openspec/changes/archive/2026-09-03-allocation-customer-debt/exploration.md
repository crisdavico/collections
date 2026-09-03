# Exploration: allocation-customer-debt

Source plan (locked product): `~/.cursor/plans/allocation_form_debt_c70c2828.plan.md`.
Manifest for this change: `19.0.1.32.0` (sibling `voucher-states-ui` reserved `19.0.1.31.0`).
Nebula is out of scope. Language: English.

CodeGraph MCP `codegraph_explore` against
`/home/crisd/projects/seedian/seedian/odoo/custom/src/private/collection` did not
return allocation symbols (it repeatedly surfaced `tools/collection_voucher.py`
and document-review JS). Current-state claims below are from direct reads of
the named files.

## Exploration: Collection allocation Customer Debt snapshot

### Current State

`collection.allocation` is a sheet+partner header (`UNIQUE(sheet_id, partner_id)`),
`draft`/`confirmed`, chatter. Vouchers are an O2M (`voucher_ids` inverse
`allocation_id`). Invoice applications are O2M `line_ids` on
`collection.allocation.line`.

**Totals today** (`models/collection_allocation.py` `_compute_totals`, depends
only `voucher_ids.amount` and `line_ids.amount_applied`):

- `total_vouchers` = sum(voucher amounts)
- `total_applied` = sum(line `amount_applied`)
- `residual` = **`total_vouchers - total_applied`** (not debt − applied)
- `total_debt` is a **writable stored Monetary**, not computed. MCP writes the
  ERP `summary.total_balance`.
- `total_invoices` / `total_quotations` **do not exist**.

**Residual reason / constraints:**

- Header `residual_reason` Selection (`on_account`, `advance`, `pending_invoice`,
  `rounding`). Same field on `collection.allocation.revision`.
- `_check_residual`: residual `< 0` → `ValidationError`; residual `> 0` without
  reason → `ValidationError`. Applies draft and confirmed.
- Line `_amount_applied_positive` is `CHECK(amount_applied > 0)` (zero forbidden).
  `_amount_applied_lte_balance` remains `amount_applied <= invoice_balance`.
- `amount_applied` is required Monetary with **no default 0**.
- Line `document_kind` is required `invoice`/`quotation`, default `invoice`.

**Create / onchange:** `create` only sanitizes voucher `Command.DELETE` → unlink
and assigns `CA/` sequence. **No partner/sheet onchange. No ERP debt snapshot.**
ORM create with omitted `line_ids` stores zero lines.

**MCP write** (`tools/collection_allocation.py`):

- Schema keeps optional `total_debt` (ignored) and optional `residual_reason`
  (parsed, persisted, hashed).
- Invoice parse requires `amount_applied > 0` (`exclusiveMinimum: 0`).
- `_collection_allocation_revalidate` walks **payload rows only**. Missing from
  fresh ERP → `"An invoice is no longer outstanding."` Available = fresh balance
  − other draft/confirmed applications. Returns
  `(summary.total_balance, line_vals)` and create/amend **writes `total_debt`**.
- `_collection_allocation_check_residual` uses **vouchers − applied**, refuses
  negative residual and missing reason.
- Content hash includes `residual_reason`. Reason-only retry is an amend
  (`test_reason_only_retry_not_noop_hash_includes_reason`).
- Empty `invoices[]` persists **zero lines** (on-account).
- Amend mid-write uses placeholder `residual_reason` (`on_account`) so
  `_check_residual` does not fire between `Command.clear()` and new lines.

**MCP get** (`tools/allocation_lookup.py`): found payload includes
`residual_reason`; invoice rows are
`external_invoice_id, number, issue_date, due_date, amount, balance, state,
amount_applied` — **no `document_kind`**. Tests freeze those exact keys.

**Views:**

- Allocation form (`views/collection_allocation_views.xml`): right group is
  revision, currency, `total_vouchers`, `total_applied`, `total_debt`,
  `residual`, `residual_reason`. No button box. Vouchers page is a plain O2M
  `<list>` (name, partner, state, amount) — **no `many2many` widget, no
  `document_type`**. Second page string is **"Invoices"**; line list has no
  `document_kind` in the parent arch.
- `document_kind` is injected by inherit
  `views/collection_sheet_report_views.xml`
  (`view_collection_allocation_form_document_kind`) before `invoice_number`.
  `tests/test_collection_allocation_document_kind.py` asserts that inherit file,
  not the parent arch. `AGENTS.md` still says do not edit
  `collection_allocation_views.xml`.
- Sheet form already has the smart-button pattern to copy
  (`views/collection_views.xml` `oe_button_box` + `action_open_vouchers` /
  `voucher_count`). Sheet method domain is `[('sheet_id', '=', self.id)]`,
  `view_mode` `list,kanban,form`. Plan wants the same markup on allocation with
  domain `[('allocation_id', '=', self.id)]`.

**Connector debt (confirmed, no `document_kind`):**

- SQLite `_sqlite_fetch_customer_debt` SELECTs
  `id, number, issue_date, due_date, amount, balance, state` only. Zero
  `document_kind` hits in `collection_connector_sqlite`.
- Collection `_format_customer_debt` emits the same invoice keys (plus
  `external_invoice_id`). Outstanding filter is `balance > 0` and state
  `open`/`overdue`. Test fixture `TEST_INVOICES` has two outstanding rows for
  the bound customer (100 overdue + 50 open) and no kind.
- `_collection_active_connector()` **raises UserError** when no active
  connector. Plan onchange must not call that helper as-is.

**Voucher detach / attach coupling (not listed in the plan file list, but
live):** `collection.voucher._projected_residual` is
`allocation.residual + amount_delta`. `_allocation_residual_holds` still
requires `residual_reason` when projected residual `> 0`. Detach tests assume
today’s formula (`residual = vouchers − applied`): fully applied residual `0`
refuses detach; residual `40` with a `100` voucher refuses detach. After
`residual = total_debt − total_applied`, adding/removing a voucher **does not
change residual**.

**Sheet report coupling:** `_collection_report_customers` reads
`allocation._fields["residual_reason"]` and `allocation.residual_reason`.
Dropping the field without a one-line report guard will crash XLSX/PDF data
build. Plan leaves report *copy* out of scope except recomputed residual
numbers.

**Sibling in-flight (`voucher-states-ui`, phase `tasks`, read-only):** delta
only drops the MCP “not rejected” voucher gate. Shared files it will also
edit: `__manifest__.py` → `19.0.1.31.0`, `migrations/19.0.1.31.0/`,
`tools/collection_allocation.py` (`_collection_allocation_vouchers`),
`tests/test_collection_company_migration.py`, `tests/test_collection_mcp_allocation.py`,
`tests/test_collection_ui.py`, `AGENTS.md`. Do not edit that change folder.

**Main spec still requires** residual ≥ 0, reason iff residual > 0, hash
includes reason, get returns `residual_reason`, inherit-only `document_kind`,
and “do not edit `collection_allocation_views.xml`”. Those blocks must be
MODIFIED/REMOVED in the delta spec; product decisions are locked in the plan.

### Affected Areas

- `models/collection_allocation.py` — recompute `total_debt` /
  `total_invoices` / `total_quotations` / residual; drop `residual_reason` and
  `_check_residual`; add `voucher_count` + `action_open_vouchers`; add
  snapshot helper + onchange + create-if-omitted-lines.
- `models/collection_allocation_line.py` — `CHECK(amount_applied >= 0)`;
  default `amount_applied` to `0`.
- `models/collection_allocation_revision.py` — drop `residual_reason`; store
  new header totals at revision time.
- `models/collection_voucher.py` — `_projected_residual` /
  `_allocation_residual_holds` (and detach tests) must follow the new residual
  meaning and the removed reason field.
- `models/collection_sheet_report.py` — stop reading header
  `residual_reason` (leave cell empty or drop label lookup). Residual numbers
  already come from the header compute.
- `tools/collection_allocation.py` — parse `amount_applied >= 0`; revalidate
  persists **all** outstanding ERP invoices; ignore `residual_reason`; drop
  reason from hash; stop writing `total_debt`; drop residual UserErrors.
- `tools/allocation_lookup.py` — drop `residual_reason` from get payload;
  optionally add `document_kind` on invoice rows.
- `views/collection_allocation_views.xml` — button box; many2many vouchers +
  `document_type` + domain; Customer Debt tab + `document_kind` before
  `invoice_number`; helpers; field order; no Residual Reason.
- `views/collection_sheet_report_views.xml` — remove document_kind inherit
  once parent arch owns the field.
- `__manifest__.py` — `19.0.1.32.0` (after sibling `19.0.1.31.0`).
- `migrations/19.0.1.32.0/post-migrate.py` — `ALTER TABLE … DROP COLUMN
  residual_reason` on allocation + revision (Constraint SQL updates on `-u`).
- `tests/test_collection_allocation.py`,
  `tests/test_collection_allocation_document_kind.py`,
  `tests/test_collection_mcp_allocation.py`,
  `tests/test_collection_mcp_allocation_lookup.py`,
  `tests/test_collection_ui.py`,
  `tests/test_collection_company_migration.py`,
  plus voucher detach tests in `tests/test_collection_voucher.py` /
  `tests/test_collection_allocation.py`.
- `AGENTS.md` — residual / MCP / “do not edit allocation views” bullets.
- `openspec/specs/collection-allocations/spec.md` — MODIFY residual,
  hash, get payload, document_kind view, detach-projection scenarios.
- Out of scope: Nebula, SQLite `document_kind`, sibling
  `openspec/changes/voucher-states-ui/**`.

### Approaches

1. **Shared snapshot helper + form onchange + create-if-omitted** — Add
   `@api.private _prepare_customer_debt_lines()` that resolves
   `company.collection_connector_id` + customer binding by `partner_id`,
   calls `get_customer_debt(sheet.seller_id, identification)`, returns line
   vals (`amount_applied=0`, `document_kind='invoice'`). Onchange
   `partner_id`/`sheet_id` replaces `line_ids` when not confirmed. `create`
   snapshots only when `line_ids` is omitted. MCP always passes expanded
   lines, so it does not double-fetch.
   - Pros: One fetch path; onchange stays CRUD-free (vals/commands only);
     matches the locked plan; testable without the form.
   - Cons: Onchange of customer/sheet wipes in-progress applied amounts
     (accepted: snapshot is frozen at that moment). Must not call
     `_collection_active_connector()` (it UserErrors).
   - Effort: Medium

2. **Inline onchange / duplicate MCP expand** — Form onchange inlines the
   ERP walk; MCP revalidate keeps its own expand loop; no shared helper.
   - Pros: Slightly fewer new methods.
   - Cons: Two copies of binding+debt+line-vals; easy to drift on empty
     connector vs UserError.
   - Effort: Medium (higher long-term)

Lookup `document_kind` (plan left this open):

3. **Add `document_kind` on get invoice rows** — Additive key; reflects
   operator edits that split Total Invoices vs Quotations. Update
   `_INVOICE_KEYS` tests. Nebula may notice; accepted and out of scope.
   - Pros: Get matches stored lines; UI/tests can assert kind.
   - Cons: Exact-key consumers see a new field.
   - Effort: Low

4. **Omit `document_kind` on get** — Drop only `residual_reason`; keep
   invoice keys frozen.
   - Pros: Smaller get delta.
   - Cons: Kind is now first-class on the form but invisible on the read
     tool; later agents cannot see quotation vs invoice.
   - Effort: Low

Detach / attach after the residual formula change (plan left HOW implicit):

5. **Stop adding voucher amounts into residual** — `_projected_residual`
   no longer does `residual ± voucher.amount`. Draft detach/attach no longer
   uses leftover-voucher math. Drop the `residual_reason` branch in
   `_allocation_residual_holds`. Spec MODIFY “Source detach residual refuse”
   (fully-applied detach is no longer residual-negative). Confirmed freeze
   still refuses membership writes.
   - Pros: Matches locked residual meaning; avoids mixed semantics.
   - Cons: Existing detach tests must be rewritten (not just residual
     numbers).
   - Effort: Medium

6. **Keep legacy `residual ± voucher.amount`** — Displayed residual is
   debt − applied, but detach still pretends residual is leftover vouchers.
   - Pros: Fewer detach test rewrites.
   - Cons: Operators see Residual 40 (debt leftover) and still cannot
     detach a 100 voucher for a reason that is no longer what Residual
     means.
   - Effort: Low (wrong)

### Recommendation

Use **approach 1** (shared helper) as the plan already specified. Onchange
must treat missing/inactive connector or missing binding as **empty lines,
no UserError** (read `collection_connector_id`, do not call
`_collection_active_connector()`). MCP revalidate expands to every
outstanding invoice after validating applied payload ids; zero-applied
payload rows and omitted zeros are both allowed; “no longer outstanding”
stays only for payload rows with `amount_applied > 0`.

Use **approach 3**: add `document_kind` on `get_collection_allocation`
invoice rows. Kind is how totals split; the read tool should return what is
stored.

Use **approach 5** for voucher detach/attach: do not project voucher amounts
onto the new residual. Propose/spec must MODIFY the detach-refuse
requirement rather than keep a leftover-voucher residual in parallel.
Confirmed allocations stay frozen.

Do not reopen locked product: Customer Debt snapshot including zeros;
`residual = total_debt - total_applied` with negative allowed; drop Odoo
`residual_reason` while MCP still accepts and ignores it; no SQLite kind;
no backfill of old lines; Nebula untouched; manifest `19.0.1.32.0`.

### Risks

- **Concurrent sibling `voucher-states-ui`:** same files
  (`__manifest__.py`, `tools/collection_allocation.py`,
  `tests/test_collection_company_migration.py`, MCP/UI allocation tests,
  `AGENTS.md`). Apply this change after 1.31.0 lands, or rebase. Do not
  edit the sibling change folder.
- **Voucher detach/attach + report `residual_reason`:** omitting those
  follow-ons will raise `ValidationError`/`UserError` or crash report data
  after the field is removed.
- **Onchange vs `_collection_active_connector`:** using the existing
  company helper on the form will UserError when Settings has no connector.
- **Upgrade residual:** stored computes recalculate with the new formula
  and current lines; old headers without zero-debt rows will show a smaller
  `total_debt` than live ERP. Plan forbids backfill.
- **Test blast radius:** many helpers still pass `residual_reason` and
  assume `CHECK(amount_applied > 0)`, hash-includes-reason, get key set,
  inherit-only `document_kind`, and residual = vouchers − applied
  (`test_residual_positive_requires_reason_*`,
  `test_residual_negative_rejected_*`, MCP residual tests, lookup
  `_ALLOC_KEYS`).
- **Review budget:** model + MCP + views + migration + AGENTS + many tests
  will likely exceed 400 authored lines; `sdd-tasks` should forecast chained
  PRs.
- **CodeGraph:** index did not resolve allocation symbols this session;
  later phases should keep using explicit file reads.

### Ready for Proposal

Yes. Current code plus the locked plan are enough to write the proposal and
delta specs. Tell the user: proceed to `sdd-propose` (do not start apply).
The proposal must list voucher detach/report follow-ons and the sibling
1.31.0 file overlap. Specs must MODIFY residual, hash, get payload,
document_kind parent-arch, and detach-projection — not reopen the snapshot
or residual formula.
