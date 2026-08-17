# Design: Collection Sheets

## Technical Approach

Add no-workflow `collection.sheet` via Many2one `sheet_id` (`ondelete="set null"`) and
inverse `voucher_ids`. New UI/MCP all-new require internal `seller_id`; voucher ORM
stays nullable (no backfill). Python + view domains reject mixed sellers, seller-less
rows, and assigned vouchers outside the UI. Exact MCP replay is read-only. Upgrade only.

## Architecture Decisions

| Decision      | Options                   | Tradeoff                   | Choice                                                                        |
| ------------- | ------------------------- | -------------------------- | ----------------------------------------------------------------------------- |
| Membership    | M2O vs M2M                | FK vs join table           | M2O `sheet_id` + O2M `voucher_ids`                                            |
| Same-seller   | Python vs trigger vs both | Cross-table vs messages    | `@api.constrains` + CHECK assigned⇒seller; no `UNIQUE(sheet_id)`; no triggers |
| Create UX     | Server action vs wizard   | Extra model vs Action menu | List-bound `ir.actions.server`; no wizard                                     |
| Legacy seller | ORM required vs nullable  | Upgrade vs RPC hole        | `required=False`; form `required="1"`; MCP request required                   |
| MCP seller    | Top-level vs per-payment  | One seller vs mixed        | Top-level int; validate before lookup; stamp all-new only                     |
| Dates         | UTC vs user TZ            | Midnight skew              | Stored `fields.Date` from UTC min/max `create_date`                           |
| O2M remove    | DELETE vs UNLINK          | Destroy vs unassign        | Sanitize `(2,id)`→`(3,id)`; `widget="many2many"`                              |
| Index         | `models.Index` vs default | Extra DDL                  | None; Many2one already indexed                                                |
| Chatter       | `mail.thread` vs plain    | Extra UX                   | No chatter, no `state`                                                        |
| Nebula        | Edit vs follow-up         | Breaking creates           | Do not edit nebula-agent                                                      |

Rejected: sheet workflow, extra groups, backfill, `create_uid` as seller.

## Data Flow

List Action: validate (non-empty; every `seller_id`; one seller; unassigned; any
`state`) → create → assign → open form. Fail → `UserError`, no sheet. XML domains are UX
only. Sheet unlink: FK set-null. Empty sheets OK (dates False). Freeze sheet `seller_id`
(`readonly` + write block); `ondelete="restrict"`.

```
MCP create_collection_vouchers
  │  require seller_id (schema + exists, share=False, group_user)
  ├─ in-call duplicate document_id → UserError
  ├─ lookup document_id
  ├─ none → savepoint create N; stamp seller_id; attachments as today
  ├─ exact set → return list; NO writes (seller/customer/attachments ignored)
  ├─ partial → UserError, no writes
  └─ UniqueViolation → invalidate_all → replay/reject (ignore seller)
```

## File Changes

| File                                | Action    | Description                                                          |
| ----------------------------------- | --------- | -------------------------------------------------------------------- |
| `models/collection_sheet.py`        | Create    | Sequence; required readonly `seller_id`; O2M; dates; UNLINK sanitize |
| `models/collection_voucher.py`      | Modify    | Nullable `seller_id`; `sheet_id` set-null; constrains+CHECK; Action  |
| `models/__init__.py`                | Modify    | Import sheet                                                         |
| `data/ir_sequence_data.xml`         | Modify    | `collection.sheet` `CS/%(year)s/` pad 4                              |
| `security/ir.model.access.csv`      | Modify    | One `base.group_user` CRUD row                                       |
| `views/collection_views.xml`        | Modify    | Seller/sheet; sheet `<list>`/form/menu; list Action; no wizard       |
| `tools/collection_voucher.py`       | Modify    | Required `seller_id`; stamp all-new only; no `sudo()`                |
| `__manifest__.py`                   | Modify    | `19.0.1.9.0` → `19.0.1.10.0`                                         |
| `tests/test_collection_sheet.py`    | Create    | Sequence, Action fail, membership, UTC dates, unlink                 |
| `tests/test_collection_mcp_tool.py` | Modify    | Schema; stamp; replay no mutate; portal reject                       |
| `tests/test_collection_ui.py`       | Modify    | Form required seller; sheet menu; Action xmlid                       |
| `tests/test_collection_acl.py`      | Modify    | Sheet CRUD internal vs portal                                        |
| `tests/test_collection_voucher.py`  | Modify    | ORM without seller OK; assigned without seller fails                 |
| `tests/__init__.py`                 | Modify    | Import sheet tests                                                   |
| `migrations/`                       | Unchanged | Keep `19.0.1.7.0`; no new script                                     |

## Interfaces / Contracts

Sheet: `CS/<year>/<number>`; required `seller_id`; `voucher_ids`; stored
`date_from`/`date_to`; no `state`. Voucher: `seller_id` `required=False`; `sheet_id`
`ondelete="set null"`; optional `models.Constraint`
`CHECK(sheet_id IS NULL OR seller_id IS NOT NULL)`.

Action gate (domains are UX only): empty / missing seller / mixed sellers / `sheet_id`
set → `UserError`; else create sheet, write `sheet_id`, return form action. O2M:
Command.DELETE→UNLINK in sheet `create`/`write`. Sheet delete uses FK set-null; no sheet
`@api.ondelete` (keep voucher pending-only). MCP
`required: [customer_identification, payments, seller_id]`. Response unchanged. Replay
must not write matching rows (incl. NULL `seller_id`). Dates:
`fields.Date.to_date(create_date)` UTC; empty ⇒ both False.

## Testing Strategy

| Layer       | What                                                          | Approach                                          |
| ----------- | ------------------------------------------------------------- | ------------------------------------------------- |
| Unit        | Constraints, Action fail, dates, unlink, nullable seller, MCP | `test_collection_sheet.py` + voucher/MCP          |
| Integration | Upgrade nullable columns; existing NULL                       | `-u collection`                                   |
| E2E         | N/A                                                           | Config disabled                                   |
| UI/ACL      | `<list>`, Action, form required; sheet CRUD                   | `test_collection_ui.py`, `test_collection_acl.py` |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS, or process-integration. No threat-matrix
tasks.

## Migration / Rollout

`-u collection` to `19.0.1.10.0`. ORM adds nullable columns + sheet table; `sheet_id` FK
`ON DELETE SET NULL`. No backfill, no voucher `NOT NULL`, no reset, no
`migrations/19.0.1.10.0/`. Leave `19.0.1.7.0`. Rollback = revert git. Nebula all-new MCP
fails until follow-up; exact replay works with valid `seller_id`.

## Open Questions

None. Internal seller = `share=False` + `base.group_user`. Spec conflicts → `sdd-tasks`.
