# Archive Report: customer-partner-binding

**Change**: `customer-partner-binding`
**Archived**: 2026-09-01
**Artifact store**: openspec
**Skill resolution**: paths-injected
**Engram**: unavailable — `mem_save` skipped; this file is the closure record
**Work unit**: `archive-close`
**Attempt token**: `sha256:979818251239797a52047c995b2a8d9b72d83b85dc61605dcfa389ec1026895b`
(parent-held acquire re-authenticated with `--token`; not settled)

## Final-state authority

Ranked sources at close (most authoritative first):

1. **Native review authority**: `reviewGate` is structurally **absent** (kill switch
   off / no review discovered). Archive proceeds under ordinary policy. There is no
   receipt to read or block on.
2. **Persisted tasks artifact**: `tasks.md` 16/16 `[x]`; zero `- [ ]` implementation
   tasks. Task Completion Gate passed before spec merge.
3. **Orchestrator launch prompt (2026-09-01)**: `applyState: all_done`;
   `taskProgress: 16/16 complete, allComplete true`; user explicitly instructed
   archive despite native dispatcher still showing `nextRecommended: verify` /
   `dependencies.archive: blocked` (verify routing / command-hash attestation quirk).
   Treated as an **intentional archive override**. CRITICAL findings are 0, so the
   CRITICAL gate does not block.
4. **`verify-report.md` (verification-time snapshot)**: verdict `pass_with_warnings`;
   blockers 0; critical_findings 0; requirements 13/13; scenarios 50/50; collection
   suite 452 passed. Used as historical evidence, not as a claim that D4/Q4 remain
   live blockers.

Stale `state.yaml` `phase: verify` / `Next: sdd-archive (not launched)` is
orchestrator-managed snapshot text from before this close. It is not current. This
archive **is** the close.

## Gates

| Gate | Result |
|------|--------|
| Native Review Receipt | Absent — proceed under ordinary policy |
| Task Completion | Pass — 16/16 `[x]` |
| CRITICAL in verify-report | Pass — 0 CRITICAL |
| Intentional archive override | Recorded — user instructed archive despite dispatcher `nextRecommended: verify` |
| `rules.archive` destructive-delta warning | Recorded below — do not stop |

## Spec merge (before folder move)

Deltas merged into existing main specs. Requirements not named in the delta were
preserved. MODIFIED blocks replaced the matching requirement entirely. No REMOVED
or RENAMED sections.

### collection-connectors

| Action | Requirement |
|--------|-------------|
| Purpose rewrite (required) | Purpose no longer says customers remain connector data with a global create ban. Read tools MUST NOT create `res.partner` or customer bindings. The voucher-create path and `resolve_customer_partner` MAY. |
| ADDED | Write path may create partners and bindings |
| ADDED | Customer binding uniqueness |
| ADDED | Customer partner resolution |
| ADDED | Customer binding ACL |
| MODIFIED | Read-only MCP tool list_collection_customers |
| MODIFIED | Normalized customer list output |
| MODIFIED | Read-only MCP tool customer_debt |
| MODIFIED | Normalized customer debt output |

### collection-vouchers

| Action | Requirement |
|--------|-------------|
| MODIFIED | Deferred integrations not required (partner/CRM now in-scope via required `partner_id`) |
| MODIFIED | Voucher fields and defaults (Char `customer_identification` gone; required `partner_id`) |
| MODIFIED | Payment Vouchers UI (`partner_id`, no Customer domain) |
| MODIFIED | MCP tool create_collection_vouchers (lazy resolve on all-new; replay keeps first-call partner) |
| MODIFIED | Typed provenance copies of payment fields (exclude `partner_id` / identification) |

### `rules.archive` destructive / backward-incompatible warning

This change is **intentional**. It is backward-incompatible:

- Voucher customer identity moves from Char `customer_identification` to required
  `res.partner` `partner_id` (no SQL backfill / D4).
- The connectors Purpose and read-path global prohibition on creating partners or
  bindings is reversed for the write path: `create_collection_vouchers` /
  `resolve_customer_partner` MAY create partners and
  `collection.connector.customer.binding` rows; MCP read tools still MUST NOT.

Archive proceeded without asking the orchestrator to stop.

## Mechanical move

- Source: `openspec/changes/customer-partner-binding/`
- Destination: `openspec/changes/archive/2026-09-01-customer-partner-binding/`
- Method: `git mv` failed (`fatal: source directory is empty` — untracked change
  folder); fallback `mv` succeeded.
- Pre-move recursive snapshot vs archived folder `diff -r`: **empty** (status 0).
- Active change path is gone.
- `archive-report.md` is additive after the move and was excluded from that diff.

Verbatim `diff -r` evidence:

```text
DIFF_R_BEGIN
DIFF_R_END status=0
```

## Archive contents

- proposal.md
- specs/collection-connectors/spec.md
- specs/collection-vouchers/spec.md
- design.md
- tasks.md (16/16 complete)
- verify-report.md
- apply-progress.md
- exploration.md
- state.yaml
- archive-report.md (this file; written after move)

## Verification-time warnings (not current blockers)

Per `verify-report.md` at verification time (`pass_with_warnings`, 0 blockers, 0
CRITICAL):

- **D4**: devel upgrade could not apply SQL NOT NULL on
  `collection.voucher.partner_id` because leftover rows contain nulls. Runtime logged
  `column "partner_id" of relation "collection_voucher" contains null values` then
  `Missing not-null constraint on collection.voucher.partner_id`. Accepted design
  risk; ORM `required=True` still holds; no backfill. Not a current archive blocker.
- **Q4**: at verification time the git working tree still had dirty/untracked
  unrelated connector, archive, and sqlite files outside this change's apply root.
  Not restaged; not a spec fail. Not a current archive blocker.

Optional verification-time notes (lint `C8101` manifest author; concurrent
first-sighting via injected UniqueViolation; cheap `invoke install` instead of
`invoke img-build`) remain snapshot comments, not open work.

## Source of truth after close

- `openspec/specs/collection-connectors/spec.md`
- `openspec/specs/collection-vouchers/spec.md`

The SDD cycle for `customer-partner-binding` is complete: planned, implemented,
verified, and archived.
