# Design: Draft Until Sheet Close

## Technical Approach

Invert lifecycle in place. Default `draft`; Close/Reopen are the only audited `state`
writers. Freeze, amend, residual, membership, unlink, MCP, views, revision ACL, and
tests flip with that. Specs: `collection-allocations`, `collection-sheets`,
`collection-vouchers`. No sudo. No `CA/` sequence. Nebula out of scope.

## Architecture Decisions

| Option                                                                | Tradeoff                           | Decision                                                                                                                   |
| --------------------------------------------------------------------- | ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| New models vs invert-in-place                                         | Extra tables vs wide rewrite       | **Invert-in-place.** Same UNIQUE, revisions, MCP keys.                                                                     |
| Dedicated sync context vs reuse `collection_allocation_audited_state` | Extra key vs one writer            | **Reuse `collection_allocation_audited_state`.** Close/Reopen only. Drop Validate/Reject intercept.                        |
| Confirm after sheet close (no skip)                                   | Simpler constrain vs freeze timing | **Confirm then close; reopen then draft.** Skip iff mid-flight; re-invoke after both writes. Freeze starts at `confirmed`. |
| Soft-cancel drafts                                                    | Avoids revision unlink             | **Refuse.** UNIQUE `(sheet, partner)` would block replace.                                                                 |
| Keep `validated`/`rejected` aliases                                   | Softer SQL                         | **Refuse.** Product drops the keys.                                                                                        |
| SQL remap vs ORM browse                                               | Stale Selection vs ORM             | **SQL first in `post-migrate.py`.**                                                                                        |

## Data Flow

```
MCP create → default draft + revision 1 (vals omit state)
MCP amend  → only while draft; SUPERSET; revalidate minus other draft+confirmed
GET        → open-sheet hit returns state "draft" (field, not hardcoded)

Close   [audited] allocations.state=confirmed → sheet.state=closed → iff recheck
Reopen  [audited] sheet.state=open → allocations.state=draft → iff recheck

Draft unlink → parent-unlink ctx → unassign vouchers (set null) → cascade lines
             → gated revision unlink
Confirmed unlink → UserError (even 0 revisions)
Open sheet unlink → unlink draft allocations → sheet
Closed sheet unlink → UserError even if empty
```

```python
# Iff skip (allocation @api.constrains("state", "sheet_id"))
if self.env.context.get("collection_allocation_audited_state"):
    return
# Close: confirm (skip) then sheet close, then allocations._check_sheet_state_iff()
# Reopen: sheet open then draft (skip), then same recheck.
# Raw allocation state write without that context → UserError (no Validate/Reject).
```

```python
# Gated revision unlink (mirrors create's collection_allocation_revision)
def unlink(self):  # collection.allocation
    if not self.env.context.get("collection_allocation_parent_unlink"):
        return self.with_context(collection_allocation_parent_unlink=True).unlink()
    return super().unlink()

@api.ondelete(at_uninstall=False)  # collection.allocation.revision
def _unlink_forbidden(self):
    if self.env.context.get("collection_allocation_parent_unlink"):
        return
    raise UserError(_("Allocation revisions cannot be deleted."))
```

## File Changes

| File                                                                                                                           | Action | Description                                                                                                                                                                                                                                               |
| ------------------------------------------------------------------------------------------------------------------------------ | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `models/collection_allocation.py`                                                                                              | Modify | Selection `draft`/`confirmed`, default `draft`. Freeze iff `confirmed`. Drop `action_validate`/`action_reject`. Residual both states. Iff constrain. Replace `_unlink_if_no_revisions` with refuse-if-confirmed. Parent-unlink wrapper.                   |
| `models/collection_allocation_revision.py`                                                                                     | Modify | `_unlink_forbidden` no-ops only under `collection_allocation_parent_unlink`. Direct unlink stays UserError.                                                                                                                                               |
| `models/collection_sheet.py`                                                                                                   | Modify | Close confirms then closes; Reopen opens then drafts (audited). Replace `_unlink_if_no_allocations`: closed refuse; open unlinks drafts first.                                                                                                            |
| `models/collection_voucher.py`                                                                                                 | Modify | Drop `_unlink_if_unallocated`. Pending unlink if unset or draft; residual `< 0` refuses (inverted detachable helper; no line edits). Rename `_allocation_is_confirmed_or_unset` → draft-or-unset. Target `state="draft"`. Confirmed source/target refuse. |
| `tools/collection_allocation.py`                                                                                               | Modify | Default persist `draft` (omit `state` in create vals). Amend iff `draft` (replace “already reviewed”). Revalidation `("allocation_id.state", "in", ("draft", "confirmed"))`. Tool description.                                                            |
| `tools/allocation_lookup.py`                                                                                                   | Keep   | Already returns `allocation.state`. Tests only.                                                                                                                                                                                                           |
| `views/collection_allocation_views.xml`                                                                                        | Modify | Drop Validate/Reject, validated/rejected filters, form `reviewed_by`/`reviewed_at`. `statusbar_visible="draft,confirmed"`. Frozen fields `readonly="state == 'confirmed'"`. Keep revision list `delete="false"`.                                          |
| `security/ir.model.access.csv`                                                                                                 | Modify | Revision `1,0,1,1`. `@api.ondelete` remains the lock.                                                                                                                                                                                                     |
| `migrations/19.0.1.28.0/post-migrate.py`                                                                                       | Create | SQL remap from sheet (`open`→`draft`, `closed`→`confirmed`) at start. Collapse `validated`/`rejected`. No `CA/`.                                                                                                                                          |
| `__manifest__.py`                                                                                                              | Modify | `19.0.1.28.0`.                                                                                                                                                                                                                                            |
| `AGENTS.md`                                                                                                                    | Modify | Lifecycle, freeze, unlink, ACL, MCP, UI, version `19.0.1.28.0`.                                                                                                                                                                                           |
| `tests/test_collection_{allocation,allocation_acl,mcp_allocation,mcp_allocation_lookup,sheet,voucher,ui,company_migration}.py` | Modify | Strict TDD rewrite.                                                                                                                                                                                                                                       |

`reviewed_by` / `reviewed_at` stay on the model; leave the form.

## Interfaces / Contracts

MCP create/amend I/O unchanged except `allocation.state` is `"draft"` until Close. Amend
refused when `confirmed`. Lookup open-sheet `state` is `"draft"`. No new tools. Never
`sudo()` or a `muk_mcp.tool` row.

## Testing Strategy

| Layer       | What                                                                                                                                                                                                                                                                           | Approach                                                              |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------- |
| Unit        | Draft default; freeze invert; iff skip+recheck; draft unlink with revisions; confirmed unlink; direct revision UserError; pending residual; membership invert; close/reopen; open cascade; closed empty refuse; MCP persist/amend/revalidation; UI gone; migrate `19.0.1.28.0` | TransactionCase RED→GREEN. `invoke test -m collection --mode=update`. |
| Integration | Same runner in container                                                                                                                                                                                                                                                       | `--mode=update` on installed devel.                                   |
| E2E         | N/A                                                                                                                                                                                                                                                                            | Unavailable.                                                          |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification,
or process-integration boundary.

## Migration / Rollout

Bump `19.0.1.27.0` → `19.0.1.28.0`. SQL at start of
`migrations/19.0.1.28.0/post-migrate.py` (`cr.execute`, not ORM): join allocation to
sheet; `open`→`draft`, `closed`→`confirmed`. Dropped keys never linger. Chatter remains.
Upgrade cannot restore keys; dump restore is the inverse. No `CA/` work. Flip
`test_manifest_version_is_1_27_0` to assert `19.0.1.28.0` and the new folder exists.

## Open Questions

None. Product is settled.
