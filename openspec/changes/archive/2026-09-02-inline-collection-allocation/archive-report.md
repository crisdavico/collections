# Archive Report: inline-collection-allocation

**Archived**: 2026-09-02
**Change**: `inline-collection-allocation`
**Store**: openspec (filesystem only; Engram not used)
**Status**: success
**reviewGate**: absent (kill switch off / no review started; archive proceeded under ordinary policy)

## Final state at close

These facts outrank intermediate `apply-progress` / `verify-report` snapshots.

| Fact | Value | Authority |
| ---- | ----- | --------- |
| Implementation tasks | 32/32 `[x]`; pending 0 | persisted `tasks.md` |
| Verify verdict | PASS (not FAIL) | launch final-state + `verify-report.md` envelope `verdict: pass` |
| Requirements / scenarios | 10/10, 31/31 | `verify-report.md` header |
| Module tests at verify time | `invoke test -m collection --mode=update` → 0 failed of 520, exit 0 | launch final-state + `verify-report.md` |
| Manifest | `19.0.1.27.0`; no `migrations/19.0.1.27.0/` | launch final-state |
| Coordinated Nebula deploy | operational risk, not an incomplete task | launch final-state |

CRITICAL findings: none. Archive was not blocked.

## Task Completion Gate

Inspected `openspec/changes/inline-collection-allocation/tasks.md` before merge/move. Zero `- [ ]` implementation tasks. Phases 1–3 (1.1–3.5) are all `[x]`. Gate passed; no archive-time checkbox reconciliation.

## Native Review Receipt Gate

Structured status `reviewGate` is structurally absent. No review transaction/ledger/receipt was read. Archive proceeded under ordinary repository policy. User confirmation to archive was treated as confirmation for the known backward-incompatible OpenSpec deltas (below), not as a substitute for a missing receipt.

## Destructive / backward-incompatible deltas (user confirmed)

`openspec/config.yaml` `rules.archive` requires a warning before merging destructive or backward-incompatible deltas. The user explicitly asked to archive and confirmed these known breaking deltas. They were merged; they were not re-asked.

1. **`vouchers` → `payments` on `create_collection_allocation`.** Input now requires inline `payments[]` (minItems 1, no per-payment `customer_identification`) and required `invoices[]` (MAY be empty). Success output is `{sheet_id, vouchers, allocation}` rather than `{allocation:{...}}` only.
2. **REMOVED MCP tool `create_collection_vouchers`.** The `@mcp_tool` is gone. Internal `_collection_*` helpers remain and are reused by allocation. See REMOVED Reason/Migration below.
3. **Partner lazy-create now on allocation write.** Unbound identification on `create_collection_allocation` MAY create `res.partner` plus `collection.connector.customer.binding` via `resolve_customer_partner`. Reads (`get_collection_allocation`, `list_collection_customers`, `customer_debt`) still MUST NOT provision.

## REMOVED requirement (recorded before deletion from main specs)

**Requirement:** MCP tool create_collection_vouchers (domain `collection-vouchers`)

- **Reason:** Fused confirm is `create_collection_allocation` with inline `payments[]`; a second write tool would drift from the Nebula contract and split partner/sheet/idempotency paths.
- **Migration:** Retire the `@mcp_tool` in work unit 3 (after/with Nebula deploy). Keep `_collection_*` helpers internal and reuse them from allocation. Re-point attachment, provenance, partner-resolve, and remaining MCP tests to `create_collection_allocation`. Delete create/replay/ACL tests that only covered the retired tool. Do not add a `muk_mcp.tool` row.

## Specs synced to source of truth

Delta specs merged into existing main specs. Requirements not named in a delta were preserved.

| Domain | Action | Details |
| ------ | ------ | ------- |
| collection-allocations | Updated | ADDED 1 (`MCP get_collection_allocation`); MODIFIED 3 (`MCP create_collection_allocation`, `Input and sheet gates`, `Idempotency and amend`). Preserved: Revalidation and residual; Freeze, revisions, ACL, back-office; Source detach residual refuse; Partner match after voucher write. |
| collection-connectors | Updated | MODIFIED 1 (`Write path may create partners and bindings`). All other requirements preserved. |
| collection-vouchers | Updated | ADDED 1 (`Internal collection payment helpers`); MODIFIED 3 (`MCP optional payment attachment on create`, `MCP nested provenance on all-new create`, `Cross-company document_id reject not replay`); REMOVED 1 (`MCP tool create_collection_vouchers`). All other requirements preserved. |

Main spec paths:

- `openspec/specs/collection-allocations/spec.md`
- `openspec/specs/collection-connectors/spec.md`
- `openspec/specs/collection-vouchers/spec.md`

### Leftovers not in the delta (preserved on purpose)

These still mention the retired tool or the old write path because they were not ADDED/MODIFIED/REMOVED in the change deltas:

- `collection-connectors` **Purpose** still says the voucher-create path MAY create partners/bindings.
- `collection-connectors` **Requirement: Rollback unchanged** still names `create_collection_vouchers` among tools that MUST stay unchanged when connectors are cleared.

They are historical spec text, not incomplete archive work.

## Mechanical move

- Change folder was **untracked** (`git ls-files` miss). `git mv` failed with `fatal: source directory is empty`. Fallback `mv` succeeded.
- Archive path: `openspec/changes/archive/2026-09-02-inline-collection-allocation/`
- Active path `openspec/changes/inline-collection-allocation/` is gone after the move.
- Pre-move recursive snapshot compared with `diff -r`. Empty diff (exit 0). This report is additive and was written after that comparison.

## Archive contents

- proposal.md
- exploration.md
- design.md
- tasks.md (32/32 complete; no unchecked implementation tasks)
- specs/collection-allocations/spec.md
- specs/collection-connectors/spec.md
- specs/collection-vouchers/spec.md
- apply-progress.md
- verify-report.md
- state.yaml
- archive-report.md (this file; additive after move)

## Attempt

Authenticated as the parent attempt with `--token sha256:cbe8bfc92f6342fa6d245ae312f77cd5187a2a209be213ab7ec9b1d72e1047c4`. Acquire returned `state: proceed` with the same token (zero mutation). This executor does not settle.

## Risks at close

- Coordinated Nebula agent deploy remains an operational risk: MCP clients that still call `create_collection_vouchers` or the old `vouchers` allocation input will fail until they deploy with the fused `payments[]` contract.
- Leftover `create_collection_vouchers` wording in connectors Purpose and Rollback unchanged may confuse readers of main specs until a later change edits those non-delta sections.
