## Exploration: collection-receipts

Relate collection vouchers to customer debt so the **external ERP can issue two
receipts** (invoices vs quotations) from one allocation. Product decisions in the
session prompt are treated as settled. This document verifies the design note against
live code and specs.

### Current State

**Allocation is an aggregate, not a receipt.** `collection.allocation` is
`UNIQUE(sheet_id, partner_id)` with two independent pools: `voucher_ids` (money) and
`line_ids` (every outstanding ERP document + `amount_applied`). Totals already split
debt by kind (`total_invoices` / `total_quotations`) but **applied money and vouchers
are one undifferentiated pool**. Residual is `total_debt − total_applied` (negative
allowed; mixes invoice and quotation balances). There is no `collection.receipt`, no
amount-bearing voucher↔kind link, and no ERP write-back.

**`document_kind` is live on lines only.** `collection.allocation.line.document_kind` is
required Selection `invoice`/`quotation`, default `invoice`
(`models/collection_allocation_line.py:45-52`). Form/ORM operators can write `quotation`
on a draft line. MCP create **must omit kind**; persist defaults `invoice`
(`openspec/specs/collection-allocations/spec.md` Requirement _Allocation line
document_kind_, line 374: _"MCP `create_collection_allocation` payload and write
response MUST NOT gain `document_kind`"_). Get returns `document_kind`
(`tools/allocation_lookup.py:127`). Form snapshot `_customer_debt_line_vals` hardcodes
`"document_kind": "invoice"` (`models/collection_allocation.py:217`). MCP revalidate
(`_collection_allocation_revalidate`) never sets kind, so `Command.clear()` + recreate
on amend **wipes operator-set quotations**.

**Which documents were paid is already live.** Persist expands to every outstanding ERP
invoice with payload applied or `amount_applied = 0`
(`collection-allocations/spec.md:141`; `tools/collection_allocation.py:463-505`). Do not
add a model for this.

**Content hash ignores splits and kind.** `_collection_allocation_content_hash` SHA-256s
sorted voucher ids plus sorted `(external_invoice_id, amount_applied)` pairs only
(`tools/collection_allocation.py:358-373`). Matching hash + new `request_id` is a
zero-write replay (`test_content_hash_replay_new_request_id_no_extra_revision`). An
amend that only changes invoice/quotation money split would be silently discarded unless
splits (and kind, if it becomes payload) enter the hash.

**Freeze / unlink.** Allocation membership freeze:
`_FROZEN_FIELDS = {line_ids, voucher_ids, partner_id, sheet_id}` when confirmed or sheet
in `_FROZEN_SHEET_STATES = {closed, cancelled}`
(`models/collection_allocation.py:9-12, 252-281`). Lines: `_raise_if_sheet_frozen` on
write/unlink (`models/collection_allocation_line.py:74-95`). Draft parent unlink uses
`collection_allocation_parent_unlink`: unassigns vouchers, cascades lines/revisions
(`models/collection_allocation.py:283-292`; spec Requirement _Draft unlink with
revisions_). Confirmed unlink refused.

**Debt path has no quotations.** MCP `customer_debt` →
`collection.connector.get_customer_debt` → `_format_customer_debt`. Formatter keeps only
`balance > 0` and `state in {open, overdue}` and copies
`external_invoice_id, number, issue_date, due_date, amount, balance, state` — **no
`document_kind`** (`models/collection_connector.py:21-26, 271-321`). Spec _Normalized
customer debt output_ (`collection-connectors/spec.md:329-338`) freezes that key list.
SQLite `invoices` table has those same columns plus `customer_id`; no quotations table;
no `document_kind` (`collection_connector_sqlite/data/database.sql:29-38`; spec _SQLite
read-only customer debt source_ `collection-connectors/spec.md:433-438`).
`_SQLITE_INVOICE_COLUMNS` would reject a kind column until both spec and adapter change.

**`_DISPATCH_OPS` is a four-op allowlist.**
`{"test_connection", "list_sellers", "list_customers", "get_customer_debt"}`
(`models/collection_connector.py:10-12`). Unknown ops fail closed
(`tests/test_collection_connector.py:89-118`). AGENTS.md MCP create bullet: _"MUST NOT
change `_DISPATCH_OPS`"_. Import spec: _"MUST NOT add a new dispatcher op"_
(`collection-connectors/spec.md:110`). SQLite is **read-only**; _"The file MUST NOT be
written"_ (`collection-connectors/spec.md:437-438`). There is no `create_receipt` (or
any write op) in collection or sqlite.

**Security / version.** Company `ir.rule` `[('company_id', 'in', company_ids)]` on
voucher, sheet, snapshot, connector, bindings, allocation, line, revision
(`security/collection_security.xml`). ACL: allocation/line `group_user` `1,1,1,1`;
revision `1,0,1,1`; no extra groups; never `sudo()`. Manifest **`19.0.1.33.0`**.
Existing migrate folders: `1.7`, `1.13`, `1.17`, `1.25`, `1.28`, `1.31`, `1.32`, `1.33`.
AGENTS.md and `test_manifest_version_is_1_33_0` forbid `1.26`/`1.27`/`1.29`/`1.30` and a
second `1.31`. Legal next folder: **`migrations/19.0.1.34.0/`**. Additive only; spec
already says upgrade MUST NOT backfill existing allocations
(`collection-allocations/spec.md:414`).

**Voucher field pressure (Approach B check).** `collection.voucher` currently declares
**46 fields**, including 22 `ocr_*` / `seller_*` provenance copies plus `allocation_id`.
No amount-to-kind fields.

**Nebula cannot declare pairing today.** `InvoiceApplication` is `extra="forbid"` with
`external_invoice_id` + `amount_applied` (+ display `number`/`due_date`) — no
`document_kind` (`nebula-agent/src/agent/state.py:109-121`). Confirm `_invoices_payload`
sends only those two keys (`src/agent/tools/collection_allocation.py:339-346`).
`allocation_request_id` hashes identification, document ids, invoice pairs,
residual_reason — no splits (`src/agent/tools/_allocation.py:240-260`). `customer_debt`
tool forwards MCP `invoices` as-is (`src/agent/tools/customer_debt.py:61-71`). Settled
decision: **the agent supplies the pairing** via `create_collection_allocation`. Without
a Nebula change, Odoo can persist a default one-invoice receipt, but the seller cannot
split a voucher across two receipts.

**Edit authority.** Native `gentle-ai sdd-status` `allowedEditRoots` is the **collection
git root only**. `collection_connector_sqlite` is a **sibling git repo** (`8795859`,
clean) under `odoo/custom/src/private/collection_connector_sqlite`.
`openspec/config.yaml` `apply.roots` lists collection, private, sqlite, and
nebula-agent, but this session must not treat sqlite/Nebula as in-tree edits.

### Affected Areas

- `models/collection_allocation.py` — `receipt_ids` O2M; freeze `_FROZEN_FIELDS`; unlink
  cascade; per-kind applied totals; persist/amend hook
- `models/collection_allocation_line.py` — freeze pattern to copy; kind must survive MCP
  persist
- `models/collection_allocation_revision.py` — hash stored on revision; no schema change
  required unless snapshotting receipt totals
- `models/collection_receipt.py` / `models/collection_receipt_value.py` — **new**
- `models/__init__.py` — import new models
- `models/collection_connector.py` — `_DISPATCH_OPS` extension; `_format_customer_debt`
  must pass `document_kind`
- `tools/collection_allocation.py` — optional splits (+ optional `document_kind` on
  `invoices[]`); **content hash**; persist/amend; backward-compat default receipt
- `tools/allocation_lookup.py` — get payload MAY expose receipts (proposal lock);
  invoices already include kind
- `tools/customer_debt.py` — description/payload if debt rows gain kind (keys still
  `{customer, summary, invoices}`)
- `views/collection_allocation_views.xml` / new receipt views — read-mostly receipts
- `security/collection_security.xml` / `security/ir.model.access.csv` — `company_id`
  rules + ACL; no new groups
- `__manifest__.py` — bump `19.0.1.34.0`; data files
- `migrations/19.0.1.34.0/post-migrate.py` — additive tables only; **no backfill**
- `AGENTS.md` — `_DISPATCH_OPS` freeze and `document_kind` MCP prohibition both change
  (orchestrator/apply; this explore must not edit it)
- `openspec/specs/collection-allocations/spec.md` — lift create-payload kind ban;
  receipts; hash; freeze; unlink; compat
- `openspec/specs/collection-connectors/spec.md` — debt row `document_kind`; dispatcher
  write op; sqlite schema/read-only vs stub write-back
- **Sibling** `collection_connector_sqlite` (`models/collection_connector.py`,
  `data/database.sql`, tests) — quotations/`document_kind` on debt; `create_receipt`
  adapter. **Out of collection git.**
- **Nebula** `src/agent/state.py`, `src/agent/tools/customer_debt.py`,
  `src/agent/tools/collection_draft.py`, `src/agent/tools/collection_allocation.py`,
  `src/agent/tools/_allocation.py`, tests, eval/PRD — required for the agent to declare
  kind/splits. **Out of collection git.**
- Tests that go RED on the first spec/code change (strict TDD):
  `tests/test_collection_allocation_document_kind.py`
  (`test_mcp_create_omits_kind_defaults_invoice` schema freeze),
  `tests/test_collection_mcp_allocation.py` (content-hash replay),
  `tests/test_collection_mcp_customer_debt.py` (invoice row key set),
  `tests/test_collection_connector.py` (dispatcher allowlist),
  `tests/test_collection_company_migration.py` (`test_manifest_version_is_1_33_0` +
  AGENTS.md version pins), sqlite connector invoice-schema tests, plus new receipt
  tests.

### Approaches

1. **A. Receipt header + `collection.receipt.value` (design-note recommendation)** —
   `collection.receipt` (at most one per `document_kind` via
   `UNIQUE(allocation_id, document_kind)`); applications **derived** from `line_ids`
   filtered by kind and `amount_applied > 0`; amount-bearing link is
   `collection.receipt.value (voucher_id, amount)`.

   - Pros: Matches ERP shape (values list + documents list + reconciling totals); one
     voucher can split across two receipts; `external_receipt_id` / issued state have a
     home; new kinds add rows not columns; follows line/snapshot child-model idiom;
     unsplit remainder stays on-account with no receipt.
   - Cons: Two new models + security + freeze + hash + MCP schema; sqlite and Nebula
     coordinated repos; `_DISPATCH_OPS` and spec bans must be deliberately lifted.
   - Effort: High (cross-repo; still the smallest design that satisfies settled
     product).

2. **B. Two Monetary fields on `collection.voucher` (`amount_to_invoices` /
   `amount_to_quotations`)** — design note rejects this; live voucher already has **46
   fields**.

   - Pros: Fewer tables; simple hash (`amount_to_*` on voucher ids).
   - Cons: No home for ERP receipt id/state; a third `document_kind` is a column +
     migrate + report change; overcrowds voucher; cannot represent two receipts as
     first-class objects the ERP consumes; still needs debt-kind + dispatcher work.
   - Effort: Medium for the fields, High for the same blockers — worse long-term.

3. **C. Voucher↔line junction `(voucher_id, line_id, amount)`** — **wrong requirement**,
   not a live option. Product: no value↔document detail inside a receipt. Live ERP need
   is two receipts (kind-level), not partial-reconcile. Code has no such junction;
   persist already records which documents were paid via `amount_applied`.
   - Pros: Would answer a different question (check→invoice pairing).
   - Cons: Agent would collect WhatsApp pairings nobody consumes; over-fits
     `account.partial.reconcile`.
   - Effort: High and incorrect.

### Recommendation

**Approach A**, with the design-note field list, subject to these locks the
proposal/spec/design MUST write down:

1. **Prerequisite gap — agent cannot declare quotations (blocker).** Citations:
   `collection-connectors/spec.md:317-338` (debt = outstanding invoices only; frozen
   keys, no `document_kind`); `collection-allocations/spec.md:374` (create
   payload/response MUST NOT gain `document_kind`); live `_format_customer_debt` /
   `_INVOICE_ITEM_SCHEMA` / `_customer_debt_line_vals` /
   `_collection_allocation_revalidate`. Until debt rows carry `document_kind` (default
   `invoice`) **and** create `invoices[]` MAY include it, a quotation receipt cannot be
   built by the agent. Operators can only hand-edit draft lines, and MCP amend currently
   **resets those to invoice**. Proposal MUST amend both specs, pass kind through
   formatter + persist, and treat omitted kind as `invoice`.

2. **Prerequisite gap — `_DISPATCH_OPS` frozen (blocker).** Citations:
   `models/collection_connector.py:10-12`; AGENTS.md _"MUST NOT change
   `_DISPATCH_OPS`"_; `collection-connectors/spec.md:110`; sqlite _"file MUST NOT be
   written"_ (`collection-connectors/spec.md:437-438`). ERP issuance needs an
   allowlisted write op (`create_receipt` or similar) plus a sqlite adapter. Proposal
   MUST: (a) deliberately extend the allowlist; (b) lock **when** Odoo dispatches
   (recommend: persist grouping on MCP write; push on sheet **Close**, receipts `draft`
   until ERP returns `external_receipt_id` then `issued`); (c) keep sqlite **file**
   read-only — adapter is a **no-write stub** returning a deterministic fake id for
   tests, not a receipts table write, unless that spec is also amended.

3. **Compat (settled).** Non-empty `invoices[]` and no splits → one `invoice` receipt.
   Unsplit voucher money is on-account and belongs to **no** receipt. Empty `invoices[]`
   remains all on-account (zero receipts). Totals: `total_values >= total_applied`;
   surplus = `amount_on_account`. Do not require equality.

4. **Hash.** Splits MUST enter `_collection_allocation_content_hash`. If `invoices[]`
   gains `document_kind`, kind MUST enter the hash too. Existing revisions keep old
   hashes (additive migration; no backfill) — identical old payloads without splits
   still replay.

5. **Freeze / unlink / security.** Copy `_raise_if_sheet_frozen` onto receipt and value;
   add `receipt_ids` to allocation `_FROZEN_FIELDS`; issued receipts immutable; draft
   parent-unlink cascades receipts/values; vouchers survive. `company_id` related stored
   required precompute index; `ir.rule`; ACL `group_user` (receipt/value: same as lines
   `1,1,1,1`); no new groups; no `sudo()`.

6. **Migration.** Manifest `19.0.1.33.0` → `19.0.1.34.0`; folder
   `migrations/19.0.1.34.0/` only. Do not add `1.26`/`1.27`/`1.29`/`1.30`. Do not
   backfill receipts. `test_manifest_version_is_1_33_0` and AGENTS.md version pins MUST
   be updated in apply (not this explore).

7. **Nebula is required for pairing, not for Odoo persistence.** Default
   one-invoice-receipt compat lets today's agent keep working. Two receipts from one
   voucher **cannot** be declared without Nebula: `src/agent/state.py`
   (`InvoiceApplication`), `src/agent/tools/customer_debt.py`,
   `src/agent/tools/collection_draft.py`, `src/agent/tools/collection_allocation.py`
   (`_invoices_payload`), `src/agent/tools/_allocation.py` (`allocation_request_id` +
   FIFO), plus tests/eval/PRD. Coordinate as a **separate git/PR** (out of
   `allowedEditRoots`). Sqlite schema/adapter is a **third** git/PR.

8. **Get payload.** Proposal MUST say whether `get_collection_allocation` grows a
   `receipts` list or stays vouchers+invoices-only. Recommend adding `receipts` (compat:
   old agents ignore extra keys) so Close/ERP hand-off is inspectable.

### Risks

- **Two spec bans + AGENTS.md freeze are load-bearing.** Shipping receipts without
  lifting `document_kind` on create and `_DISPATCH_OPS` yields grouped rows the agent
  cannot populate and the ERP cannot issue.
- **Sqlite is a sibling repo** (`collection_connector_sqlite` @ `8795859`). Debt
  quotations/`document_kind` and a stub `create_receipt` cannot land inside collection
  git. Session `allowedEditRoots` is collection-only; `openspec/config.yaml`
  `apply.roots` is broader — proposal must name coordinated PRs, not in-tree sqlite
  edits.
- **Nebula is a third repo.** Pairing source is the agent; omitting Nebula leaves only
  the compat default (one invoice receipt).
- **Sqlite read-only vs ERP write-back.** A real sqlite file write would violate
  `collection-connectors/spec.md:437-438`. Stub-only write-back is the compatible
  adapter until a real ERP connector exists.
- **MCP amend today destroys quotation kinds.** Any persist change that still omits kind
  from revalidate vals will keep that bug.
- **Hash migration.** Old revisions will not match a new hash function if callers
  resubmit with implicit default splits; spec MUST define replay for pre-receipt
  payloads (no splits in hash ⇒ same as today).
- **Collision / dirty workspace (not this explore).** `AGENTS.md`,
  `tests/test_collection_company_migration.py`, `tests/test_collection_ui.py` were
  mtime-touched 2026-09-04 12:35:18 UTC with **zero git diff vs HEAD** `f6f9703` on
  `main`. Untracked (not reverted): `.codegraph/`, `tests/__pycache__/`,
  `openspec/changes/archive/2026-08-26-add-pluggable-collection-connectors/.gentle-ai-instance`.
  Another agent may be working here.
- **Review budget.** Models + MCP + security + specs + tests will likely exceed 400
  authored lines; tasks should forecast chained PRs (collection persistence / sqlite
  adapter / Nebula pairing / ERP dispatch).
- **CodeGraph** on collection often returned `collection_voucher.py` instead of
  allocation modules; live reads of allocation/connector/MCP/sqlite/Nebula were used.
  CodeGraph v1.6.0 is available; this session used v1.5.0.

### Ready for Proposal

**Yes.** Product decisions are settled; live code confirms Approach A and both
prerequisite gaps. Tell the user: proposal MUST include spec amendments for (1) optional
`document_kind` on debt + create `invoices[]`, (2) `_DISPATCH_OPS` + sqlite stub
`create_receipt`, (3) splits in the content hash, (4) additive `19.0.1.34.0` with no
receipt backfill, and (5) explicit coordinated sqlite + Nebula PRs because they sit
outside this git root.
