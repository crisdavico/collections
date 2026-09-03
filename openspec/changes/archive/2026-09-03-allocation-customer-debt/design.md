# Design: Allocation Customer Debt

## Technical Approach

Snapshot every outstanding ERP invoice onto `collection.allocation.line` (zeros
kept). Residual is computed debt − applied (negative allowed). Drop
`residual_reason` and `_check_residual`. Form onchange and omitted-line create
share `_prepare_customer_debt_lines()`. MCP already fetches ERP in
`_collection_allocation_revalidate`; it expands there (no second fetch). Nebula
untouched. Apply after sibling `voucher-states-ui` (`19.0.1.31.0`). No ACL or
`CA/` sequence changes. Specs (if present) MODIFY residual, hash, get payload,
parent-arch `document_kind`, and detach-projection.

## Architecture Decisions

| Decision | Options | Tradeoff | Choice |
| -------- | ------- | -------- | ------ |
| Snapshot HOW | Shared helper vs duplicate onchange/MCP | Drift vs extra method | Form/create: `_prepare_customer_debt_lines()`. MCP expand stays in revalidate |
| Onchange errors | `_collection_active_connector()` vs read `collection_connector_id` | UserError vs empty lines | Read `company.collection_connector_id`. Missing/inactive/unbound/ERP `UserError` → empty `line_ids`. Never call `_collection_active_connector()` |
| Create lines | Always snapshot vs omitted-only | Double-fetch MCP vs empty ORM | Snapshot iff `"line_ids" not in vals` |
| Get `document_kind` | Add vs omit | Extra key vs kind invisible | Add; stored default `invoice` |
| Detach residual | Stop `residual ± voucher.amount` vs keep leftover-voucher math | Test rewrite vs mixed meaning | Stop projection; drop `_allocation_residual_holds` reason branch; confirmed freeze unchanged |
| Report reason | Stop field read vs leave crash | Empty cell vs template copy | Emit `residual_reason: ""`; leave XLSX/PDF copy |

## Data Flow

```
Form onchange partner_id/sheet_id (skip confirmed)
  → connector = company.collection_connector_id
  → binding(connector, partner_id) → identification
  → get_customer_debt(sheet.seller_id, identification)
  → replace line_ids (applied=0, document_kind=invoice)

ORM create ("line_ids" omitted)
  → same helper once → Command.create

MCP create/amend
  → parse invoices (applied >= 0; zeros may be omitted)
  → hash(sorted voucher ids, applied pairs)  # no residual_reason
  → revalidate: applied>0 payload ids must be outstanding
  → persist every fresh outstanding (applied from payload else 0)
  → header computes totals; do not write total_debt
```

## File Changes

| File | Action | Description |
| ---- | ------ | ----------- |
| `models/collection_allocation.py` | Modify | Compute `total_debt` / `total_invoices` / `total_quotations`; residual = debt − applied; drop `residual_reason` / `_check_residual`; helper + onchange + create-if-omitted; `voucher_count` + `action_open_vouchers` |
| `models/collection_allocation_line.py` | Modify | `amount_applied` default `0`; CHECK `>= 0` |
| `models/collection_allocation_revision.py` | Modify | Drop `residual_reason`; store `total_invoices` / `total_quotations` at insert |
| `models/collection_voucher.py` | Modify | Detach/attach: no leftover-voucher residual projection |
| `models/collection_sheet_report.py` | Modify | Stop `_fields["residual_reason"]`; payload key `""` |
| `tools/collection_allocation.py` | Modify | Parse `>= 0`; expand persist; ignore reason after enum check; drop hash reason, `_collection_allocation_check_residual`, amend placeholder, `total_debt` write |
| `tools/allocation_lookup.py` | Modify | Drop get `residual_reason`; add invoice `document_kind` |
| `views/collection_allocation_views.xml` | Modify | `oe_button_box` copy of sheet; many2many `no_create`/`no_create_edit` + `document_type`; Customer Debt + `document_kind` before `invoice_number`; `help=` on six totals; drop reason |
| `views/collection_sheet_report_views.xml` | Delete | Inherit moves to parent; drop from `__manifest__.py` data |
| `__manifest__.py` | Modify | `19.0.1.32.0` after 1.31.0 |
| `migrations/19.0.1.32.0/post-migrate.py` | Create | `ALTER TABLE` DROP `residual_reason` on allocation + revision |
| Tests in proposal + `AGENTS.md` | Modify | Residual, MCP expand, lookup keys, detach, arch, migration |

`_sanitize_voucher_commands` already maps `Command.DELETE` → unlink; keep.

## Interfaces / Contracts

Helper is `@api.model` / `@api.private`, CRUD-free (vals/commands only):

```python
def _prepare_customer_debt_lines(self, sheet, partner) -> list[dict]:
    # map ERP invoices → line vals, amount_applied=0, document_kind='invoice'
```

Totals (`_compute_totals` depends `voucher_ids.amount`, `line_ids.amount_applied`,
`line_ids.invoice_balance`, `line_ids.document_kind`):

- `total_debt` = sum(`invoice_balance`) — computed stored, not MCP-writable
- `total_invoices` / `total_quotations` = sum(balance) by `document_kind`
- `residual` = `total_debt - total_applied`

MCP schema keeps optional `residual_reason` (enum still validated, never
persisted) and ignored `total_debt`. Hash payload applied pairs only, not the
expanded snapshot. Get allocation object drops `residual_reason`. Invoice rows
add `document_kind`.

Voucher O2M domain: same `partner_id` + `sheet_id`, `allocation_id` empty or
self. `action_open_vouchers` copies sheet (`list,kanban,form`) with
`[('allocation_id', '=', self.id)]`.

## Testing Strategy

| Layer | What | Approach |
| ----- | ---- | -------- |
| Unit | Snapshot, totals, CHECK `>= 0`, negative residual, empty-connector onchange, detach without voucher projection | TransactionCase (strict TDD) |
| Integration | MCP expand zeros, hash ignores reason, get keys + `document_kind`, smart-button domain, parent-arch kind, DROP COLUMN | Existing MCP/UI/migration tests |
| E2E | N/A | Not available |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file
classification, or process-integration boundary.

## Migration / Rollout

Manifest `19.0.1.32.0` after `19.0.1.31.0`. Post-migrate DROP `residual_reason`
on `collection_allocation` and `collection_allocation_revision`. Line CHECK
updates with `models.Constraint` on `-u`. Stored computes recalculate; no
backfill of missing debt lines; old revisions get `0` for new totals. Rollback:
revert pre-1.32.0; restore columns if already dropped.

## Open Questions

- None. HOW is locked (explore 1 / 3 / 5).
