# Proposal: Draft Until Sheet Close

## Intent

Allocations stay **draft** on an open sheet; **confirmed** only on Close. Operators
delete drafts, pending vouchers, and open sheets without losing revision audit.

**User impact:** delete drafts before Close; Close freezes; Validate/Reject gone; empty
closed sheets not deletable (Reopen then delete).

## Scope

### In Scope

- Models, MCP persist `draft`, views, revision ACL unlink, migrate `19.0.1.28.0`, tests,
  `AGENTS.md`
- Lifecycle invert: draft default; confirm-on-close; freeze/amend invert; residual both
  states
- Delete invert: draft unlink with revisions; pending unlink draft/unset; open cascade;
  closed refuse

### Out of Scope

- Nebula copy, PRD, eval, `_EXISTING_ALLOCATION_MESSAGE`; agent amend / `request_id`
  including fetched revision
- Deleting approved/rejected vouchers or closed sheets; destroying vouchers on
  allocation/sheet delete
- `CA/` sequence; leftover `inline-collection-allocation`

## Capabilities

### New Capabilities

None

### Modified Capabilities

- `collection-allocations`: draft default; confirm-on-close; drop Validate/Reject;
  freeze/amend invert; draft unlink with revisions; residual in both states;
  revalidation domain draft+confirmed
- `collection-vouchers`: pending unlink on draft/unset with residual guard; membership
  invert to draft-or-unset
- `collection-sheets`: close/reopen sync; open-sheet delete cascades drafts; closed
  sheet delete refused

## Approach

Invert-in-place. Close confirms then closes; Reopen opens then drafts; skip
iff-constraint via `collection_allocation_audited_state`. Draft unlink unassigns
vouchers, cascades lines, deletes revisions under gated parent-unlink. ACL `1,0,1,1`;
`@api.ondelete` remains the lock. Amend/membership only while draft; residual in both
states. SQL remap first in `post-migrate.py` (`open`→`draft`, `closed`→`confirmed`). No
sudo.

## Affected Areas

| Area                                                                    | Impact       | Description                                                                 |
| ----------------------------------------------------------------------- | ------------ | --------------------------------------------------------------------------- |
| `models/collection_{allocation,allocation_revision,sheet,voucher}.py`   | Modified     | Lifecycle invert; gated revision cascade; sheet sync/delete; voucher unlink |
| `tools/collection_allocation.py`, `tools/allocation_lookup.py`          | Modified     | Persist/amend draft; lookup `state: "draft"`                                |
| `views/collection_allocation_views.xml`, `security/ir.model.access.csv` | Modified     | Drop Validate/Reject; revision `1,0,1,1`                                    |
| `__manifest__.py`, `migrations/19.0.1.28.0/`, `AGENTS.md`, tests        | Modified/New | Bump; SQL remap; TDD rewrite                                                |

## Risks

| Risk                                 | Likelihood | Mitigation                           |
| ------------------------------------ | ---------- | ------------------------------------ |
| Close/Reopen vs iff-constraint       | High       | Skip constrain under audited context |
| Revision ACL unlink + leaky ondelete | Med        | Tight parent-unlink gate             |
| Pending delete residual `< 0`        | Med        | Spec refuse; delete whole draft      |
| Authored diff >400 LOC               | High       | Chained PRs (`auto-chain`)           |

## Rollback Plan

Revert commits. Upgrade cannot restore Selection keys or invert freeze. If `19.0.1.28.0`
ran, SQL-map back is **not** a safe inverse (`validated`/`rejected` collapsed). Restore
from dump. Manifest `19.0.1.27.0`.

## Dependencies

- Collection addon only. Nebula deferred. Strict TDD.

## Success Criteria

- [ ] MCP persist `draft` + revision 1; amend refused when confirmed
- [ ] Close/Reopen sync; draft unlink with revisions; pending unlink with residual guard
- [ ] Open cascade; closed unlink refused even empty; no Validate/Reject
- [ ] `invoke test -m collection --mode=update` and scoped pre-commit
