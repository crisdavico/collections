# Design: Voucher States UI

## Technical Approach

In-place Selection remap on `collection.voucher.state` (proposal + exploration 1;
snapshot 2A). SQL CASE in `migrations/19.0.1.31.0/post-migrate.py` (copy
`migrations/19.0.1.28.0/post-migrate.py`) remaps rows **before** ORM browse. ORM/UI
default `draft`; MCP `_collection_create_vouchers` stamps `validated_seller`; Document
Review Approve is the only path to `validated_collections`. Snapshot `decision` stays
`approved`/`rejected`. No Reject, no form Collections button, no Nebula. Specs:
`collection-vouchers`, `document-review`, `collection-allocations`,
`collection-sheet-report`.

Odoo 19: keep `<list>`, `@api.ondelete`, `t-out`, no extra groups, no `sudo()`. No
ir.sequence or ACL change.

## Architecture Decisions

| Option                                | Tradeoff                                  | Decision                             |
| ------------------------------------- | ----------------------------------------- | ------------------------------------ |
| In-place keys vs old keys + labels    | Dual vocab vs wide tests                  | In-place remap                       |
| Snapshot 2A vs extend `decision`      | Historical `rejected` vs snapshot migrate | Keep `approved`/`rejected`           |
| Intercept raw `validated_collections` | Skip Review if allowed                    | Refuse; Review only                  |
| Delete kanban vs hide                 | Leftover `ir.ui.view`                     | `<delete>` + `view_mode` `list,form` |
| `group_expand` on `state`             | Empty stage columns                       | Drop with stages kanban              |

## Data Flow

```
ORM/UI create ──default──► draft
MCP create    ──stamp───► validated_seller
draft ──action_validate_seller──► validated_seller
validated_seller + proof ──Review Approve──► voucher validated_collections
                                          └── snapshot decision="approved"
attachment replace (new proof) ──► validated_seller; clear reviewer/time
raw write validated_collections ──UserError──► (Review only)
clear proof ──no reopen──► state unchanged; rotation 0
```

Seller action and `_write_review_decision` keep `collection_audited_state=True` so
intercept does not recurse. MCP stamp is create-time (`create()` has no intercept).
`create()` MUST refuse `validated_collections`. Attachment reopen keeps
`message_main_attachment_id` in the same vals so intercept allows `validated_seller`.

## File Changes

| File                                                       | Action | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ---------------------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `models/collection_voucher.py`                             | Modify | Selection `draft`/`validated_seller`/`validated_collections`, default `draft`, drop `group_expand`; `action_validate_seller` (draft only, no reviewer stamp); drop `action_approve`/`action_reject`; intercept; `_unlink_if_pending` → draft-only; queue/`_is_review_eligible` `validated_seller`; drop `action_review_reject`; split `_write_review_decision`; attachment reset → `validated_seller`; `tracking=True` on `seller_id`, `sheet_id`, `document_type`, `amount` |
| `models/collection_voucher_review_snapshot.py`             | Keep   | `decision` Selection unchanged; no row migrate                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `tools/collection_voucher.py`                              | Modify | `_collection_create_vouchers` stamp `"validated_seller"`                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `tools/collection_allocation.py`                           | Modify | Drop `state == "rejected"` gate in `_collection_allocation_vouchers`                                                                                                                                                                                                                                                                                                                                                                                                         |
| `views/collection_views.xml`                               | Modify | `<delete>` `view_collection_voucher_kanban`; `view_mode` `list,form`; keep reassign kanban; list/search/form/statusbar; drop History page                                                                                                                                                                                                                                                                                                                                    |
| `static/src/document_review/document_review_action.esm.js` | Modify | Drop `reject()`; keep `approve()`/`runDecision`                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `static/src/document_review/document_review_action.xml`    | Modify | Drop Rechazar button                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `__manifest__.py`                                          | Modify | `19.0.1.30.0` → `19.0.1.31.0`                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `migrations/19.0.1.31.0/post-migrate.py`                   | Create | SQL CASE + leftover collapse                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `tests/test_collection_*.py`                               | Modify | Old keys, actions, UI, mail, MCP reject gate, report mixed states, manifest `1.31.0`                                                                                                                                                                                                                                                                                                                                                                                         |
| `AGENTS.md`, `readme/DESCRIPTION.md`                       | Modify | Leftover pending/approved/rejected prose (apply, not this artifact)                                                                                                                                                                                                                                                                                                                                                                                                          |

## Interfaces / Contracts

Voucher `state`: `draft` | `validated_seller` | `validated_collections`. Snapshot
`decision`: `approved` | `rejected`. MCP list payload still
`{id,name,state,document_id}` (new keys). RPC: remove `action_review_reject`;
`action_review_approve` writes voucher `validated_collections` and snapshot `approved`.
Form button `action_validate_seller`. Flag still gates `get_review_queue`,
`action_review_approve`, `action_review_set_rotation`.

Non-obvious write split (do **not** pass one string to both fields):

```python
self.with_context(collection_audited_state=True).write(
    {"state": "validated_collections", "reviewed_by": ..., "reviewed_at": ..., **extra}
)
self._append_review_snapshot("approved")
```

Intercept (no `collection_audited_state`): refuse `validated_collections`; route bare
`validated_seller` through `action_validate_seller`; allow `validated_seller` when
`message_main_attachment_id` is in vals; refuse reopen to `draft` without new proof.

## Testing Strategy

| Layer                  | What to Test                                                                                                                                                                                       | Approach                                           |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| Unit (TransactionCase) | Lifecycle, intercept, unlink draft-only, queue `validated_seller`, Review Approve split, no Reject RPCs, MCP stamp, allocation all states, attachment reopen, chatter tracking, SQL remap, UI arch | RED then `invoke test -m collection --mode=update` |
| Integration            | Same runner; MCP fused create + allocation; OWL source asserts drop `action_review_reject`                                                                                                         | Existing review/MCP tests                          |
| E2E                    | N/A                                                                                                                                                                                                | Module has no tours                                |

Lock `menu_collection_voucher.sequence == 10` vs `menu_collection_config == 100`. Keep
`test_manifest_version` on `19.0.1.31.0` and assert `migrations/19.0.1.31.0/` exists (do
not add 1.26/1.27/1.29/1.30 folders).

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification,
or process-integration boundary. MCP payload key names are unchanged; only Selection
values change.

## Migration / Rollout

`migrations/19.0.1.31.0/post-migrate.py` (cursor SQL, no ORM):

1. `UPDATE collection_voucher SET state = CASE WHEN 'pending' THEN 'draft' WHEN 'approved' THEN 'validated_collections' WHEN 'rejected' THEN 'draft' ELSE state END`
2. Collapse leftover old keys to `draft`
3. Do **not** rewrite snapshot `decision` rows

Ship via `-u collection`. Rollback: revert addon to `19.0.1.30.0`; reverse SQL
`validated_collections`→`approved`; `validated_seller` and migrated `draft`→ `pending`.
Migrated rejects stay `draft`.

## Open Questions

None — remap, snapshot 2A, intercept, kanban delete, and Nebula-out-of-scope are
settled.
