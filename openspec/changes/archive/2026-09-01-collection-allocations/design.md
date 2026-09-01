# Design: Collection Allocations

## Technical Approach

Persist seller-validated applications as `collection.allocation` (+ line +
revision). One MCP write `create_collection_allocation`: binding-only partner
lookup, fresh `get_customer_debt`, savepoint create/amend. Copy snapshot
immutability, sheet lock, DELETE sanitizer, UniqueViolation reclassify, and
`action_approve` context gate. Manifest `19.0.1.25.0`.

## Architecture Decisions

| Decision | Options | Tradeoff | Choice |
| --- | --- | --- | --- |
| Constraints | `_sql_constraints` / `models.Constraint` | Odoo 19 | `models.Constraint` |
| Line/revision Monetary | skip currency / related stored | registry assert | related stored `currency_id` |
| Idempotency | header `request_id` / revision | amend clobbers rev-1 retry | `revision.request_id` UNIQUE |
| Create race | UNIQUE only / advisory lock | dual lookup | lock `(sheet_id, partner_id)` |
| Amend race | UNIQUE(revision) / `FOR UPDATE` | unique is backup | `FOR UPDATE` then next rev |
| Amend vouchers | delta / PUT | subset orphans | sent set ⊇ current |
| ERP available | raw / subtract others | no write-back | subtract other confirmed/validated same invoice+co |
| Residual | always / confirmed only | Review edits `amount` | constrain while `confirmed` |
| O2M DELETE | raw / sanitizer | destroys vouchers | copy sheet sanitizer |
| Partner | `resolve_customer_partner` / binding | former creates | existing binding; never sudo |
| Sequence | edit 1.17.0 / new migrate | 1.17.0 orphan cleanup | SPECS + XMLID + `19.0.1.25.0` |
| Views | `<tree>` / `<list>` | Odoo 19 | `<list>`; menu 30 |
| `content_hash` | unspecified / SHA-256 | replay stability | SHA-256 of sorted ids + (invoice, applied) |

## Data Flow

```mermaid
sequenceDiagram
  participant MCP as MCP
  participant Rev as revision
  participant ORM as allocation
  participant ERP as debt
  MCP->>MCP: form, seller, new-work
  MCP->>Rev: request_id
  alt same-company
    Rev-->>MCP: replay
  else other-co
    MCP-->>MCP: generic conflict
  else miss
    MCP->>ORM: vouchers, binding, open sheet
    alt exists
      ORM->>ORM: FOR UPDATE, PUT, hash replay?
    else create
      ORM->>ORM: advisory lock
    end
    MCP->>ERP: fresh; subtract others
    MCP->>ORM: savepoint + revision
    alt UniqueViolation
      MCP->>Rev: invalidate; replay or generic
    end
  end
```

Order: form → seller → `request_id` → records → ERP → residual → savepoint.
`invoices: []` = on-account. Ignore MCP `total_debt`; store fresh summary.

## File Changes

| File | Action | Description |
| --- | --- | --- |
| `models/collection_allocation.py` | Create | Header, UNIQUE(sheet,partner), freeze, sanitizer, validate/reject |
| `models/collection_allocation_line.py` | Create | Snapshot; related currency/company; CHECK/UNIQUE |
| `models/collection_allocation_revision.py` | Create | Immutable; gated create; `request_id`/`content_hash` |
| `models/collection_voucher.py` | Modify | `allocation_id` set-null + `check_company`; write/ondelete |
| `models/collection_sheet.py` | Modify | `allocation_ids`; unlink empty OK; restrict if allocated |
| `models/res_company.py` | Modify | SPECS `CA/%(year)s/` padding 4 |
| `models/__init__.py` | Modify | Import allocation models |
| `tools/collection_allocation.py` | Create | `@mcp_tool` write; reuse mixin seller helper |
| `tools/__init__.py` | Modify | Import allocation tool |
| `security/ir.model.access.csv` | Modify | allocation/line `1,1,1,1`; revision `1,0,1,0` |
| `security/collection_security.xml` | Modify | Three company `ir.rule`s |
| `data/ir_sequence_data.xml` | Modify | `seq_collection_allocation` on `base.main_company` |
| `migrations/19.0.1.25.0/post-migrate.py` | Create | `_collection_copy_sequences()` |
| `__manifest__.py` | Modify | `19.0.1.25.0`; allocation views |
| `views/collection_allocation_views.xml` | Create | list/form/search; `path`; menu 30 |
| `views/collection_views.xml` | Modify | Sheet notebook: vouchers + allocations |
| `tests/test_collection_allocation.py` | Create | Constraints, freeze, sanitizer, residual |
| `tests/test_collection_allocation_acl.py` | Create | ACL, ir.rule, no sudo |
| `tests/test_collection_mcp_allocation.py` | Create | Create/amend/replay/subtract/UniqueViolation |
| `tests/test_collection_company_migration.py` | Modify | Version 1.25.0; sequence enum + `CA` |
| `tests/test_collection_sheet.py` | Modify | Unlink empty vs allocated |
| `tests/test_collection_ui.py` | Modify | Notebook + menu 30 |
| `tests/__init__.py` | Modify | Register new tests |
| `AGENTS.md` | Modify | Models, MCP, sequence, tests, version |

Skip 1.17.0 migrate, `_DISPATCH_OPS`, `resolve_customer_partner`, Nebula, or sqlite connector.

## Interfaces / Contracts

`@mcp_tool` on `muk_mcp.mixin`, write/`mcp`. Required: `seller_id`,
`customer_identification`, `request_id`, `vouchers` (`document_id`[], minItems 1,
recheck in Python). `invoices[]` may be empty; each needs `external_invoice_id`
+ `amount_applied` (`exclusiveMinimum` 0) plus snapshot fields. Optional
`total_debt`; `residual_reason` `on_account|advance|pending_invoice|rounding`.
Out: `{allocation:{id,name,state,revision,total_vouchers,total_applied,residual}}`.
Contexts: `collection_allocation_revision`, `collection_allocation_audited_state`.
UniqueViolation: `invalidate_all()` → `request_id` search → replay or generic.

## Testing Strategy

| Layer | What | Approach |
| --- | --- | --- |
| Unit | Constraints, freeze, sanitizer, ondelete, ACL, ir.rule, no `.sudo(` | `TransactionCase`; `inspect.getsource` |
| Integration | MCP create, replay, hash, amend, superset, gates, subtract, UniqueViolation | `test_collection_mcp_allocation.py` |
| E2E | N/A | Manual |

Strict TDD; four stacked units.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR, or process-integration boundary.

## Migration / Rollout

Bump `19.0.1.25.0`. Post-migrate copies `CA/` via `_collection_copy_sequences()`
(main-company template, `number_next=1`). No backfill. Rollback: revert version;
drop allocation models, `allocation_id`, `CA/`, MCP, views. Empty sheets still
unlink-unassign.

## Open Questions

- [ ] None.
