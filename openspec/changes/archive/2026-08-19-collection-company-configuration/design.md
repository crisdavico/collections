# Design: Collection Company Configuration

## Technical Approach

Extend the existing **one config per company** pattern (`res.company` + related
`res.config.settings`, Collections app) already used by `document_review_enabled`. Add
enabled sellers, `auto_create_sheet`, and allowed types (catalog M2M). Stamp required
`company_id` on vouchers/sheets, related stored `company_id` on review snapshots, and
standard allowed-company `ir.rule`. One create-only helper gates NEW work for
UI/ORM/import/MCP. MCP replay stays exact-set but **same-company only**; global
`UNIQUE(document_id)` remains; other-company / hidden UniqueViolation is generic reject.
Per-company `ir.sequence` rows keep codes `collection.voucher` / `collection.sheet`.
Maps proposal + deltas `collection-vouchers`, `collection-sheets`, `document-review`,
`seller-lookup`. Nebula-agent out of scope. No extra groups, no `sudo()`, no POS-style
config model.

## Architecture Decisions

| Decision | Options | Tradeoff | Choice |
|----------|---------|----------|--------|
| Settings storage | `res.company`+related settings vs POS-style `collection.config` | Isolating fields vs matching current review flag | **Company + related settings** (settled) |
| Allowed types | Catalog M2M (3a) vs 4 booleans vs voucher Many2one | M2M matches field name; Many2one breaks MCP/snapshots | **`collection.document.type` + M2M**; voucher `document_type` stays Selection |
| New-work gates | Per-path checks vs one helper | Drift across UI/ORM/import/MCP | **One helper** on company/voucher, called from ORM create/write; MCP/list Action inherit |
| Skip gates | Context flag vs path never writes | Flags leak | **Skip by path**: helper only on NEW create and `seller_id`/`document_type` writes; MCP exact same-company replay returns before create; Approve/Reject/Close/Reopen do not call it |
| Empty `enabled_seller_ids` | Treat as all vs none | “All” would surprise after seed-miss | **None for NEW work** |
| Isolation | `ir.rule` `[('company_id','in',company_ids)]` vs no rules | Specs/tests today assert zero rules | **Required `company_id` + that rule**; no extra groups |
| Snapshot company | Rely on voucher rule vs own field | Voucher rules do not hide snapshots | **Related stored `company_id`** + same `ir.rule` |
| `document_id` | Per-company UNIQUE vs keep global | Per-company UNIQUE allows cross-company reuse | **Keep global UNIQUE**; reject-not-replay other company |
| Cross-company hit | `sudo()` search vs visible search + UniqueViolation | `sudo()` forbidden and leaks | **No sudo**. Classify visible hits; UniqueViolation with no same-company exact set → generic `UserError` |
| Sequences | Shared `company_id=False` vs per-company rows | False rows steal `next_by_code` (`company_id in [env.company, False]`) | **Convert False → main (keep `number_next`), copy others, `with_company(record.company_id).next_by_code`** |
| One-open | Per seller vs `(company_id, seller_id)` | Same seller may be open in two companies | **Scope search + advisory lock to company+seller** |
| `auto_create_sheet` OFF | Skip create only vs skip create **and** assign | Spec: stay unassigned | **Skip both**; list Action + explicit sheet create remain |
| `get_seller_id` | Filter enabled vs unchanged | Filtering is a later change | **Unchanged** (no enabled/company filter) |
| Settings XMLID | Rename XMLID vs labels only | Numeric `action-540` / XMLID stay | **Rename labels to Collection Settings**; keep `collection.action_collection_config_settings` |
| Odoo 19 | `_sql_constraints` / `<tree>` | Unsupported | **`models.Constraint`**, **`<list>`** |

## Data Flow

```
MCP create_collection_vouchers (no sudo)
  parse payments → search visible vouchers by document_id
       │
       ├─ all docs on env.company → exact replay (skip seller/type/sheet/nests)
       ├─ partial overlap on env.company only → existing partial UserError, no write
       ├─ any visible other-company hit → generic UserError (no id/name)
       └─ none visible → helper (seller+types) → savepoint create (ORM auto-sheet)
              └─ UniqueViolation → invalidate
                   ├─ same-company exact set now visible → replay (nests ignored)
                   └─ else → generic UserError (hidden row or other company)
```

UI/ORM/import voucher `create` → default `company_id=env.company` → helper →
`with_company(company).next_by_code('collection.voucher')` → auto-assign iff
`auto_create_sheet` and `seller_id` set and `sheet_id` omitted (open sheets **in that
company**).

### Enforcement matrix

| Path | Seller required | Enabled seller | Allowed type | Auto-sheet | Company isolation |
|------|-----------------|----------------|--------------|------------|-------------------|
| UI / ORM / import voucher create | Yes | Yes (empty = block) | Yes | ON: 0 create+assign / 1 assign / >1 UserError in that company. OFF: skip create **and** assign | `company_id` + `ir.rule` |
| Voucher write `seller_id` / `document_type` | Existing row | Yes if seller written | Yes if type written | No auto-assign | Same voucher company |
| Approve / Reject / Close / Reopen | Skip helper | Skip | Skip | n/a | `ir.rule` only |
| MCP all-new | Yes | Yes | Yes | Same as ORM create | Stamp `env.company` |
| MCP exact same-company replay | Skip | Skip | Skip | No sheet create/assign/mutate | Replay only that company |
| MCP other-company or UniqueViolation with no same-company set | Reject, no write | n/a | n/a | No write | Generic `UserError`, no id/name |
| List Action (even if auto OFF) | Yes (selection) | Yes | n/a | Always creates one open sheet when one-open count in that company is 0 | Selection same company; sheet gets that company |
| Explicit sheet create (even if auto OFF) | Yes | Yes | n/a | n/a (always creates) | `company_id`; one-open `(company, seller)` |
| `get_seller_id` | n/a | **No filter** | n/a | n/a | No company allow-list filter |

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `models/collection_document_type.py` | Create | Catalog: `code`/`name`; `models.Constraint UNIQUE(code)` |
| `data/collection_document_type_data.xml` | Create | Four XMLID rows: `bank_transfer`, `check`, `cash_deposit`, `unsupported` |
| `security/collection_security.xml` | Create | Global `ir.rule` on voucher, sheet, snapshot: `[('company_id', 'in', company_ids)]` |
| `migrations/19.0.1.16.0/post-migrate.py` | Create | Ordered backfill (see Migration) |
| `models/res_company.py` | Modify | `enabled_seller_ids` (M2M internal users), `auto_create_sheet` default True, `allowed_document_type_ids`; keep `document_review_enabled`; `_assert_new_work`; create hook copies sequences + seeds all four types |
| `models/res_config_settings.py` | Modify | Related writable fields for the three new company fields |
| `views/res_config_settings_views.xml` | Modify | Settings UI; action+`menu_collection_settings` **name** → Collection Settings; keep XMLID |
| `models/collection_voucher.py` | Modify | Required `company_id` default `env.company`; helper on create + seller/type write; `with_company` sequence; auto-assign gated; list Action uses voucher company + helper; sheet same-company constrain |
| `models/collection_sheet.py` | Modify | Required `company_id`; helper on create; one-open search/lock `(company_id, seller_id)`; `with_company` sequence |
| `models/collection_voucher_review_snapshot.py` | Modify | `company_id` related stored from `voucher_id.company_id` (same pattern as `currency_id`) |
| `tools/collection_voucher.py` | Modify | Company-scoped replay classifier; generic UniqueViolation/other-company reject; all-new still goes through ORM helper |
| `tools/seller_lookup.py` | None | Production unchanged |
| `data/ir_sequence_data.xml` | Modify | Bind module XMLIDs to `base.main_company` (not `False`) |
| `security/ir.model.access.csv` | Modify | Catalog read for `base.group_user` (no extra groups) |
| `views/collection_views.xml` | Modify | Seller domain = company enabled list; type choices = allowed ∪ current value; optional `company_id` column; `<list>` |
| `models/__init__.py`, `__manifest__.py` | Modify | Import catalog; load `collection_security.xml` then ACL CSV; catalog data; version `19.0.1.16.0` |
| `tests/test_collection_*.py` | Modify | Flip no-rule / nullable-seller / global-replay / “Settings” label asserts; add company, helper, UniqueViolation, sequence, one-open, auto-sheet-off cases |
| `AGENTS.md` | Modify | Company rules, sequences, helper (apply phase) |

## Interfaces / Contracts

```python
# res.company — single choke point for NEW work
@api.private
def _assert_new_work(self, seller, document_type=None):
    # seller required; seller in self.enabled_seller_ids (empty => reject);
    # if document_type is not None: code in allowed_document_type_ids.
    # Raise UserError; never sudo.

# voucher.create / sheet.create / voucher.write(seller_id|document_type)
company = company_id or env.company
company._assert_new_work(seller, document_type)

# sequences
self.env["ir.sequence"].with_company(record.company_id).next_by_code(code)

# lock (sheet)
pg_advisory_xact_lock(hashtext('collection.sheet.open.' || company_id), seller_id)
```

Generic other-company / hidden UniqueViolation `UserError`: one message, **no** voucher
id/name/company. Same-company MCP replay payload unchanged
`{vouchers:[{id,name,state,document_id}]}`. MCP still must not accept/return `sheet_id`.
`UNIQUE(document_id)` Constraint text stays generic (no record ids). Multi-company users
who can **read** B still must **not** replay B when creating in A.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (TransactionCase) | Helper: empty/disabled seller, disallowed type, skip on Approve/Close; `auto_create_sheet` off skips create+assign; list Action still creates; one-open per company; sequences isolated; snapshot `company_id`; `get_seller_id` unfiltered | RED then GREEN; `invoke test -m collection` |
| Unit | MCP: same-company exact replay (disabled seller/type, no sheet mutate); other-company visible reject; UniqueViolation with rule-hidden row → generic error, no ids; multi-company reader no B replay | Extend `test_collection_mcp_tool.py` |
| Unit | Settings labels XMLID unchanged; `document_review_enabled` preserved; ACL still `base.group_user` **plus** company `ir.rule` | Flip `test_collection_ui.py`, `test_collection_acl.py`, `test_collection_document_review_flag.py` |
| Integration | Module upgrade post-migrate order (see below) | Container upgrade path in collection tests where practical |
| E2E | N/A | Not available |

Strict TDD. Lint: scoped pre-commit on collection paths.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification,
or process-integration boundary.

## Migration / Rollout

Additive post-migrate after ORM columns exist. **Order:**

1. Stamp **sheet** `company_id` from seller `company_id` else database main company.
2. Stamp **voucher** `company_id` from sheet company when set, else seller company else main.
3. **Repair** member vouchers so `voucher.company_id = sheet.company_id`.
4. **Seed** each company’s `enabled_seller_ids` from distinct sellers used on that company’s vouchers **and** sheets (do not hide historical null/disabled sellers).
5. **Enable all four** catalog types on every company (`allowed_document_type_ids`).
6. **Sequences:** `UPDATE` `company_id IS NULL` rows for codes `collection.voucher` / `collection.sheet` to main company (keep `number_next`); `INSERT` copies for other companies; delete/avoid leftover `company_id=False` rows so they cannot steal `next_by_code`.

Runtime: `res.company.create` copies both sequences and seeds all four types;
`auto_create_sheet` defaults True; new companies start with empty enabled sellers (none
for NEW work). Rollback: revert commits + `-u collection`; if sequences advanced, restore
DB backup. Chained PRs likely (ACL/tests + settings + MCP/uniqueness).

## Open Questions

None
