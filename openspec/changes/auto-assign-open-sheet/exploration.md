## Exploration: auto-assign-open-sheet

### Current State

`collection.sheet` is a grouping container with **no lifecycle**. There is no `state`
field (tests assert `_fields` has none). `seller_id` is required, frozen after create,
and not defaulted from `create_uid`. Membership is `voucher_ids` One2many inverse of
`collection.voucher.sheet_id` (`ondelete="set null"`). `_sanitize_voucher_commands`
rewrites `Command.delete` to `unlink` so removing a member unassigns the voucher.
Stored `date_from`/`date_to` are UTC calendar min/max of member `create_date`. Empty
sheets are allowed. ACL is full CRUD for `base.group_user` only.

`collection.voucher.create` does **not** set `sheet_id`. `seller_id` is ORM-optional;
the Payment Vouchers form requires it. Constraints: Python same-seller match plus SQL
`CHECK(sheet_id IS NULL OR seller_id IS NOT NULL)`. List Action **Create Collection
Sheet** always creates a **new** sheet for unassigned same-seller vouchers (any voucher
state) and assigns the selection. The voucher form/list/search do **not** expose
`sheet_id`; membership is edited from the sheet form (`widget="many2many"`). Sheet form
header has Document Review only — **no statusbar**. Spec today: sheets MUST NOT have
`state` or workflow.

MCP `create_collection_vouchers` stamps `seller_id` on all-new `Voucher.create` inside a
savepoint and **never sets `sheet_id`**. Exact replay / UniqueViolation replay return
`{id,name,state,document_id}` with **no writes**. Replay already ignores customer,
attachments, and `seller_id`. Nebula is out of scope; do not add `sheet_id` to the MCP
response.

Manifest version is **`19.0.1.11.0`**. The only migration script is
`migrations/19.0.1.7.0/pre-migrate.py` (legacy line `review_status` → `state` rename).
Odoo 19: `models.Constraint`, not `_sql_constraints`. Adding a UNIQUE/partial unique
index on `(seller_id) WHERE state = 'open'` would **fail module update** if a seller
already has several sheets, because every existing sheet will start as open.

**Confirmed (fail-closed):** after upgrade a seller MAY have several open sheets.
Auto-assign, Action create-sheet, sheet create, and reopen MUST `UserError` when the
seller already has **more than one** open sheet. Do **not** pick newest. Do **not**
create another. Do **not** add a UNIQUE SQL constraint. Close extras by hand, then
new writes resume.

### Affected Areas

- `models/collection_sheet.py` — add `state` Selection `open`/`closed`; close/reopen
  actions; one-open guards on create/reopen; freeze membership writes when closed
- `models/collection_voucher.py` — auto-assign helper on `create` when `seller_id` set
  and `sheet_id` omitted; freeze `sheet_id` writes against closed sheets; Action rejects
  when an open sheet already exists
- `tools/collection_voucher.py` — no MCP schema/response change; all-new create inherits
  ORM auto-assign; replay must keep skipping sheet writes (add assertions)
- `views/collection_views.xml` — sheet header Close/Reopen; statusbar; list/search
  `state`; membership readonly when closed; keep Create Collection Sheet Action
- `__manifest__.py` — bump to `19.0.1.12.0` so ORM adds the column
- `migrations/19.0.1.12.0/` — optional; ORM default `'open'` is enough if we skip UNIQUE
- `tests/test_collection_sheet.py` — today asserts **no** `state`; creates **two open
  sheets per seller** (`test_reassign_*`, Document Review triangulation). Must rewrite
- `tests/test_collection_ui.py` — asserts sheet form **without** statusbar
- `tests/test_collection_mcp_tool.py` — all-new assign; exact replay must not attach
- `tests/test_collection_document_review.py` — two same-seller sheets; close-first or
  two sellers
- `openspec/specs/collection-sheets/spec.md` — MODIFY “no state”, membership always
  editable, Action always creates; ADD close/reopen, one-open, freeze, auto-assign
- `openspec/specs/collection-vouchers/spec.md` — MODIFY MCP all-new to assign to open
  sheet; replay still no mutation; ORM create with seller auto-assigns; no MCP
  `sheet_id`

Not in this change: Nebula, MCP response shape, extra ACL groups, backfill of
unassigned vouchers, Document Review queue rules (review stays allowed on closed
members).

### Approaches

1. **Where auto-assign runs**

   1. **ORM `collection.voucher.create` helper (covers UI + MCP)** — before
      `super().create`, for each vals with `seller_id` and no `sheet_id`, resolve the
      seller’s unique open sheet or create one, then set `sheet_id`. Batch create (MCP
      N payments, same seller) resolves **once** and assigns all rows. Explicit
      `sheet_id` in vals is honored (still validated). `seller_id` write on existing
      rows does **not** auto-assign (forward-only; leftovers stay until membership or
      Action).
      - Pros: one path for form, RPC, and MCP savepoint create; replay never calls
        create so it cannot attach; matches “both MCP and UI/ORM”
      - Cons: tests that `_create_voucher()` with a seller and expect `sheet_id` empty
        must unassign, omit seller, or create while no open sheet exists
      - Effort: Medium

   2. **MCP-only assign in `_collection_create_vouchers`** — UI/ORM creates stay
      unassigned unless the Action runs.
      - Pros: smaller voucher.create surface
      - Cons: contradicts settled “UI/ORM too”; operators would still need the Action
        for every form create
      - Effort: Low

   3. **Explicit MCP `sheet_id`** — caller picks the sheet.
      - Pros: none vs settled contract
      - Cons: Nebula/schema change; response would be pressured to return `sheet_id`;
        UI still needs a second path
      - Effort: Medium

   **Recommend 1.**

2. **Sheet lifecycle field**

   1. **`state` Selection `open` / `closed`, default `open`, required** — reserved
      Odoo lifecycle name; list/search/statusbar work; existing rows get `'open'` on
      column add.
      - Pros: matches product language; Odoo-idiomatic; dates stay membership-derived
      - Cons: current spec/tests forbid sheet `state`; must MODIFY spec
      - Effort: Low

   2. **Boolean `is_open`** — inverted Close semantics; weaker list UX.
      - Pros: slightly simpler field
      - Cons: not a workflow field; filters/statusbar are awkward
      - Effort: Low

   3. **Computed from `date_to` / emptiness** — not a manual close.
      - Pros: none
      - Cons: cannot reopen; conflicts with computed member dates
      - Effort: n/a (rejected)

   **Recommend 2.1 `state` Selection.**

3. **One open sheet per seller**

   1. **Application-level guards on new operations only** — create open sheet, reopen,
      auto-assign, and Action: count open sheets for that `seller_id`. `0` → create
      (auto-assign/Action) or allow create; `1` → use it (auto-assign) / reject
      create-second (Action, sheet create, reopen); `>1` → `UserError`, no pick, no
      extra sheet. Do **not** `@api.constrains` “at most one open” on every write:
      leftover multi-open sheets must still be **closable** and remain editable until
      closed. Optional `pg_advisory_xact_lock(seller_id)` inside the MCP savepoint /
      auto-assign to shrink the concurrent double-create race without a UNIQUE index.
      - Pros: upgrade-safe; matches fail-closed; close extras still works
      - Cons: two concurrent creates with zero opens can still race two opens without
        a lock; next auto-assign then fails closed until operators close one
      - Effort: Medium

   2. **Partial UNIQUE index `(seller_id) WHERE state='open'`**
      - Pros: DB-hard uniqueness
      - Cons: **breaks `-u collection`** while multiple opens exist after defaulting
        `state='open'`; forbidden by product
      - Effort: High (would need a data-fix migration first)

   **Recommend 3.1.** Do not add UNIQUE now. Advisory lock is worth doing on the
   auto-assign/create-open path (Low extra).

4. **Close / reopen UI**

   1. **Header object buttons Close / Reopen + non-clickable statusbar** — Close when
      `state=='open'`; Reopen when `state=='closed'`. `write` rejects raw `state`
      changes except via those actions (same idea as voucher approve/reject routing).
      Any internal user (existing ACL).
      - Pros: matches voucher header pattern; Document Review button can stay; RPC
        cannot skip the one-open check
      - Cons: UI tests that forbid statusbar must change
      - Effort: Low

   2. **Clickable statusbar only**
      - Pros: fewer buttons
      - Cons: easy to miss reopen; must still intercept `write`
      - Effort: Low

   **Recommend 4.1.**

5. **Freeze membership on closed sheets**

   1. **Override write/create (both models) + assign-to-closed constraint** — on
      `collection.sheet`, reject `voucher_ids` commands while `state=='closed'`. On
      `collection.voucher`, reject `sheet_id` changes that add to a closed sheet or
      **remove/reassign off** a closed sheet (constraint alone cannot see the old
      closed parent after unlink). View: membership readonly when closed (UX only).
      - Pros: covers form widget, RPC, Action, auto-assign; freeze is real
      - Cons: two write hooks to keep in sync
      - Effort: Medium

   2. **Constraint-only**
      - Pros: smaller
      - Cons: cannot freeze **remove** from closed (voucher `sheet_id` becomes empty)
      - Effort: Low (insufficient)

   3. **View readonly only**
      - Pros: tiny
      - Cons: RPC/Action bypass
      - Effort: Low (insufficient)

   **Recommend 5.1.**

### Recommendation

Implement sheet **`state` Selection `open`/`closed`** (default `open`; existing rows
open after upgrade). Guard **new** open sheets (create, reopen, Action) with
application-level counts — fail closed on `>1` open for that seller; never UNIQUE SQL.
Auto-assign in **`collection.voucher.create`** when `seller_id` is set and `sheet_id` is
empty: unique open → assign; none → create open then assign; several → `UserError`. MCP
all-new create rides that helper inside the existing savepoint; **exact replay stays
read-only**. Keep the list Action as **create-new-sheet only**; reject if any open
already exists; leftover unassigned vouchers join an open sheet via membership while it
is open. Freeze closed membership in **sheet and voucher write/create**. UI: header
Close/Reopen + statusbar. Bump manifest to **`19.0.1.12.0`**. Nebula and MCP payload
keys stay unchanged.

Effort: **Medium**. Risk: **Medium** (upgrade multi-open window + test rewrites), not a
product blocker.

### Risks

- **Multi-open after upgrade:** every current sheet becomes `open`. Auto-assign and
  Action fail until extras are closed. Operators must close by hand; do not auto-pick.
- **Test contract break:** `test_collection_sheet.py` asserts no `state` and creates
  two same-seller sheets; `test_collection_ui.py` forbids a sheet statusbar; Document
  Review tests use two same-seller sheets. `_create_voucher()` with a seller will start
  landing on a sheet.
- **Action happy path changes:** after auto-assign, new seller-stamped vouchers are
  rarely unassigned. Action remains for leftovers when **no** open sheet exists (close
  current, then Action or new creates). Unassign from an **open** sheet is still
  allowed; Action then still rejects if that open sheet exists.
- **Concurrent double-open:** without advisory lock, two all-new MCP calls can each
  create an open sheet; the next create then fails closed. Prefer a transaction
  advisory lock on `seller_id`.
- **Naive one-open `@api.constrains`:** would block **closing** extras and incidental
  writes on leftover opens. Guards must apply to new operations only.
- **Review budget:** models + views + MCP assertions + sheet tests likely exceed 400
  authored lines; `sdd-tasks` should forecast chained PRs.

### Ready for Proposal

Yes. Settled product decisions map onto current models without a user blocker.
Orchestrator should proceed to **sdd-propose** for `auto-assign-open-sheet`. Tell the
user: existing sheets all open after upgrade; auto-assign fails closed while a seller
has more than one open sheet; MCP response and Nebula stay unchanged; no UNIQUE index.
