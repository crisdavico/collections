# Design: Collection Receipts

## Technical Approach

Approach A: `collection.receipt` UNIQUE `(allocation_id, document_kind)` plus
`collection.receipt.value`. Apps derived from `line_ids` (same kind,
`amount_applied > 0`). Persist groups; Close dispatches `create_receipt`; sqlite stub
does not write. Odoo 19: `models.Constraint`, related stored `company_id`
(`required=True`, `precompute=True`, `index=True`), `@api.ondelete`, `<list>`, never
`sudo()`. No new `ir.sequence`.

## Architecture Decisions

| Option                                   | Tradeoff                                | Decision                              |
| ---------------------------------------- | --------------------------------------- | ------------------------------------- |
| A header+value vs B fields vs C junction | A matches ERP; B/C rejected             | **A**                                 |
| Push on persist vs Close                 | Close keeps draft until ERP id          | **Close** → `issued`                  |
| Compat values                            | Full voucher amounts leave no remainder | **FIFO** applied sum by `document_id` |
| Hash extras                              | Empty `splits` key breaks old replay    | Extra keys **only if present**        |
| UNIQUE `external_receipt_id`             | Partial index vs UNIQUE (PG NULLs)      | **UNIQUE**; `False` not `""`          |
| Derived apps                             | Inverse FK on lines                     | Computed M2M `line_ids`               |
| Sqlite / Nebula                          | In-tree vs coordinated                  | **Coordinated PRs**                   |

## Data Flow

```
MCP create/amend
  parse invoices(+optional kind) + optional splits
  hash (omit extras ⇒ today's SHA)
  revalidate (keep kind) → lines/vouchers
  rebuild draft receipts/values
        │
        ▼
Sheet action_close (proposal)
  each draft receipt with ≥1 value:
    company.collection_connector_id.create_receipt(receipt)
    ctx collection_receipt_issuing → external_receipt_id + issued
  then confirm allocations → close sheet
  raise rolls back Close (fail-closed)
```

## File Changes

| File                                     | Action      | Description                                        |
| ---------------------------------------- | ----------- | -------------------------------------------------- |
| `models/collection_receipt.py`           | Create      | Header, constraints, freeze, issued                |
| `models/collection_receipt_value.py`     | Create      | Values, CHECK/UNIQUE, cap/same-allocation          |
| `models/__init__.py`                     | Modify      | Import both                                        |
| `models/collection_allocation.py`        | Modify      | `receipt_ids` frozen; debt vals pass kind          |
| `models/collection_allocation_line.py`   | Pattern     | Copy `_raise_if_sheet_frozen` to receipt/value     |
| `models/collection_sheet.py`             | Modify      | Close: dispatch, stamp issued, confirm             |
| `models/collection_connector.py`         | Modify      | `_DISPATCH_OPS`+`create_receipt`; debt kind        |
| `tools/collection_allocation.py`         | Modify      | Splits/kind/hash; persist rebuild; keep kind       |
| `tools/allocation_lookup.py`             | Modify      | Found payload always `receipts`                    |
| `views/collection_receipt_views.xml`     | Create      | Read-mostly `<list>`/`form`; issuance readonly     |
| `views/collection_allocation_views.xml`  | Modify      | Receipts notebook page                             |
| `security/collection_security.xml`       | Modify      | Company `ir.rule` on receipt and value             |
| `security/ir.model.access.csv`           | Modify      | `group_user` `1,1,1,1`; no new groups              |
| `__manifest__.py`                        | Modify      | `19.0.1.34.0`; data += receipt views               |
| `migrations/19.0.1.34.0/post-migrate.py` | Create      | Additive no-op; **no backfill**                    |
| `tests/test_collection_receipt.py`       | Create      | Models, freeze, issued, unlink, Close, ACL         |
| `tests/test_collection_receipt_split.py` | Create      | Splits, FIFO, amend, hash extras vs omit           |
| `tests/__init__.py`                      | Modify      | Import both                                        |
| `tests/common_connector.py`              | Modify      | `_test_create_receipt`; invoices MAY carry kind    |
| `AGENTS.md`                              | Modify      | Apply: lift `_DISPATCH_OPS`/kind bans; 1.34.0      |
| sqlite sibling                           | Coordinated | Kind seed; `_sqlite_create_receipt`; no file write |
| `nebula-agent`                           | Coordinated | Kind + splits; confirm/`request_id` hash           |

## Interfaces / Contracts

**Receipt:** `allocation_id` cascade; `document_kind` invoice/quotation default invoice;
related stored sheet/partner/currency/`company_id`; `value_ids`; computed `line_ids`;
`total_values`/`total_applied`/`amount_on_account`; `external_receipt_id`; `state`
draft\|issued default draft.

**Value:** `receipt_id` cascade; `voucher_id` restrict; `amount`; related stored
`company_id`.

**Constraints:** `UNIQUE(allocation, kind)`; `UNIQUE(external_receipt_id)`;
`CHECK(amount > 0)`; `UNIQUE(receipt, voucher)`; Σ amount per voucher
`<= voucher.amount`; voucher and receipt share `allocation_id`.

**Persist:** optional `splits[]` `{document_id, document_kind, amount>0}` (duplicate
`(document_id, kind)` refused; per-payment sum `<=` amount). No splits + non-empty
`invoices[]` → one invoice receipt (FIFO). Empty invoices + no splits → zero receipts.
Splits → one receipt per kind. Amend `Command.clear()`+rebuild while draft. Revalidate:
payload kind wins; omitted kind on an existing eid keeps stored kind; else fresh/default
invoice.

**Hash:** always `{vouchers: sorted ids, invoices: sorted [eid, applied:.6f]}`. Iff
payload has invoice `document_kind`, add `invoice_kinds: sorted [eid, kind]`. Iff splits
non-empty, add `splits: sorted [document_id, kind, amount:.6f]`. Never empty extra keys.
`residual_reason` omitted.

**Close stub:** `sheet.company_id.collection_connector_id.create_receipt` only. Return
`{"external_receipt_id": str}`. Test `_test_create_receipt` → `f"stub-{receipt.id}"`.
Sqlite stub: same, no write. Missing connector → `UserError`. Skip zero-value receipts;
zero receipts still Close.

**Get `receipts[]`:**
`{document_kind, state, external_receipt_id, total_values, total_applied, amount_on_account, values:[{document_id, amount}]}`.
No attachments.

**Freeze/unlink:** `_FROZEN_FIELDS` += `receipt_ids`. Copy line freeze; skip
`collection_allocation_parent_unlink`. Issued immutable unless
`collection_receipt_issuing`. Draft parent-unlink unassigns vouchers, cascades
receipts/values.

## Testing Strategy

| Layer       | What                                                        | Approach                                  |
| ----------- | ----------------------------------------------------------- | ----------------------------------------- |
| Unit        | Constraints, FIFO, kind keep, hash omit==today, freeze, ACL | `invoke test -m collection --mode=update` |
| Integration | MCP splits/compat/amend; Close→stub→issued; get `receipts`  | MCP `_call` + `action_close`              |
| E2E         | N/A                                                         | e2e unavailable                           |

**RED:** kind-omit schema; hash replay if extras leak; dispatcher allowlist;
`test_manifest_version_is_1_33_0`; lookup `_TOP_KEYS`; debt keys.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable classification, or
process-integration boundary.

## Migration / Rollout

`19.0.1.33.0` → `19.0.1.34.0`. Folder `migrations/19.0.1.34.0/` only. ORM adds tables;
no receipt INSERT. Rollback: revert 1.33.0 and restore bans.

## Open Questions

None
