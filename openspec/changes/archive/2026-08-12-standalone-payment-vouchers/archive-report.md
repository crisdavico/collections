# Archive Report: standalone-payment-vouchers

**Date**: 2026-08-12  
**Change**: standalone-payment-vouchers  
**Archived to**: `openspec/changes/archive/2026-08-12-standalone-payment-vouchers/`  
**Artifact store**: openspec  
**Status**: success  
**Intentional warnings**: yes (verify pass_with_warnings — four accepted non-blocking PARTIAL scenarios; destructive REMOVED merge acknowledged)

## Gates

| Gate | Result | Evidence |
| ---- | ------ | -------- |
| Task Completion | PASS | Archived `tasks.md` — no `- [ ]`; tasks 1.1–5.6 all `[x]` (36/36) |
| Native Review Receipt | PASS (absent) | `reviewGate` structurally absent; archive proceeded under ordinary repository policy; no receipt demanded |
| CRITICAL in verify-report | PASS | `critical_findings: 0`, blockers: 0; verdict `pass_with_warnings` |
| Destructive delta | PASS (warned, proceeded) | `rules.archive`: warn before merging destructive deltas. Eleven REMOVED collection-vouchers requirements delete header+line product. Warning acknowledged; user ordered archive of this change; merge applied |

## Final-state authority

Per orchestrator launch facts (outrank stale dispatcher `nextRecommended: verify` / `dependencies.archive: blocked` and intermediate snapshot “pending” claims):

- All 36 tasks complete in `tasks.md` (no `- [ ]`)
- Verify verdict at close: `pass_with_warnings`; blockers 0; critical_findings 0; CRITICAL: none
- Spec envelope: requirements 23/23, scenarios 57/57 (53 COMPLIANT, 4 PARTIAL)
- Tests at close: collection 132/132 via `docker exec ... -u collection --test-tags /collection`; Nebula 126 unit + 16 integration
- Native dispatcher lag: verify envelope used docker test/build commands, not config `invoke test` / `invoke img-build`; user explicitly instructed archive after `pass_with_warnings`
- Four WARNINGs remain accepted at close (not pending work, not CRITICAL):
  1. PARTIAL: Upgrade without conversion — no dedicated conversion-script test (`test_no_voucher_line_model_or_acl` + module load at `19.0.1.9.0`)
  2. PARTIAL: OWL typed editable fields — server persist + queue payload; OWL template type-specific inputs not asserted
  3. PARTIAL: Navigate and next record after decision — multi-item queue covered; OWL `goNext` / `nextIndexAfterReload` not executed
  4. PARTIAL: Rotate clockwise/counterclockwise — rotate buttons + RPC persist; attachment bytes unchanged on rotate not asserted
- Destructive REMOVED header/line requirements are the locked product; user confirmed by ordering archive
- Leftover `openspec/changes/document-review-feature-flag/` was already absent at archive time; this phase did not create, edit, or delete it. Archived copy `openspec/changes/archive/2026-08-12-document-review-feature-flag/` left untouched
- Nebula `openspec/specs/collection-voucher-registration/spec.md` was already updated in place during apply Phase 5 (not a collection delta); this archive did not rewrite nebula application code
- Intentional override: user explicitly asked to archive after `pass_with_warnings` (no CRITICAL)
- Engram unavailable — `mem_save` skipped (noted below)

## Spec sync

Performed **before** the folder move. Merge via editing main spec files (not a byte-copy of the change folder).

**Destructive merge warning (config `rules.archive`)**: merging REMOVED deltas deletes the header+line product from the source of truth (`collection.voucher.line`, Payment Lines UI, singular `create_collection_voucher`, aggregate validate/reject). Warning acknowledged; proceeded per user archive order.

**Domain**: `collection-vouchers`  
**Main spec**: `openspec/specs/collection-vouchers/spec.md` (existing; requirements not named in the delta preserved)

| Action | Requirement |
| ------ | ----------- |
| MODIFIED | Voucher sequence naming — replaced entire block (per-payment sequence) |
| MODIFIED | Mail thread and activities — replaced entire block (`pending` chatter) |
| MODIFIED | Authorization for internal users — replaced entire block (no line ACL) |
| MODIFIED | Deferred integrations not required — replaced entire block (per-voucher attachments) |
| MODIFIED | Payment document_id uniqueness — replaced entire block (on voucher) |
| MODIFIED | MCP optional payment attachment on create — replaced entire block (`create_collection_vouchers` list identity) |
| MODIFIED | Concurrent and stale review attempts — replaced entire block (voucher eligibility) |
| MODIFIED | Attachment replacement resets review to pending — replaced entire block (voucher state/audit) |
| ADDED | Voucher fields and defaults (3 scenarios) |
| ADDED | Voucher lifecycle (8 scenarios) |
| ADDED | Payment field contract (2 scenarios) |
| ADDED | Payment Vouchers UI (4 scenarios) |
| ADDED | Unsupported vouchers remain persistable (1 scenario) |
| ADDED | MCP tool create_collection_vouchers (6 scenarios) |
| ADDED | Optional image or PDF attachment per voucher (3 scenarios) |
| ADDED | Attachment widgets on Payment Vouchers views (1 scenario) |
| ADDED | Destructive reset of legacy header and line data (1 scenario) |
| REMOVED | Voucher header fields and defaults (Reason: header+line split removed; Migration: Voucher fields and defaults) |
| REMOVED | Voucher state transitions (Reason: `new`/`validated` aggregate lifecycle removed; Migration: Voucher lifecycle) |
| REMOVED | Payment lines and payment field contract (Reason: `collection.voucher.line` dropped; Migration: Payment field contract) |
| REMOVED | Menu and backend UI (Reason: dual menus / typed line tables / Validate-from-`new` removed; Migration: Payment Vouchers UI) |
| REMOVED | Unsupported lines remain non-editable on voucher form (Reason: Payment Lines browse removed; Migration: Unsupported vouchers remain persistable) |
| REMOVED | MCP tool create_collection_voucher (Reason: singular header+N-lines tool removed; Migration: `create_collection_vouchers`) |
| REMOVED | Optional image or PDF attachment per payment line (Reason: attachments move to voucher; Migration: Optional image or PDF attachment per voucher) |
| REMOVED | Attachment widgets on typed and Payment Lines views (Reason: typed/Payment Lines views removed; Migration: Attachment widgets on Payment Vouchers views) |
| REMOVED | Payment line state and audit (Reason: line lifecycle absorbed; Migration: Voucher lifecycle) |
| REMOVED | Approve may validate voucher when all attached lines approved (Reason: aggregate header validation removed; Migration: none) |
| REMOVED | Line reject immediately rejects voucher (Reason: aggregate header reject removed; Migration: none) |
| RENAMED | none |

Purpose line updated to pending→approved/rejected, one voucher per payment (not a requirement heading; kept source of truth consistent with merged requirements).

**Domain**: `document-review`  
**Main spec**: `openspec/specs/document-review/spec.md` (existing; all prior requirements not in the delta preserved)

| Action | Requirement |
| ------ | ----------- |
| MODIFIED | Eligible review queue — replaced entire block (pending attached `collection.voucher`) |
| MODIFIED | OWL client loads real ORM data — replaced entire block (voucher ORM, not line) |
| MODIFIED | Authenticated binary attachment viewer — replaced entire block (model `collection.voucher`) |
| MODIFIED | Viewer rotation — replaced entire block (angle on voucher) |
| MODIFIED | Approve and reject without mocks — replaced entire block (voucher `state`) |
| MODIFIED | Per-company Document Review flag — replaced entire block (audit on Payment Vouchers views) |
| ADDED | none |
| REMOVED | none |
| RENAMED | none |

Preserved unchanged: Viewer fit and cursor-anchored zoom; Document Review authorization; Document Review menu and RPCs when flag is off. Purpose line updated to voucher proofs. RFC 2119 / Given-When-Then retained.

## Mechanical archive

- Method: `git mv` failed (`fatal: source directory is empty` — change folder untracked in the nested collection git repo); fallback `mv` succeeded
- Archive path: `openspec/changes/archive/2026-08-12-standalone-payment-vouchers/`
- Active path removed: `openspec/changes/standalone-payment-vouchers/` no longer exists
- Pre-move snapshot vs archive `diff -r`: empty (byte-identical); `DIFF_STATUS=0`
- Archive-report is additive after the move and excluded from the snapshot comparison
- `state.yaml` updated after the empty `diff -r` to `phase: archived`

### Verbatim `diff -r` readback (Step 2 — spec merge)

Spec sync was in-place heading-matched merge into existing main specs (not a mechanical full-spec copy). No Step 2 `cp`/`diff -r` for a new domain file.

```
(n/a — existing main specs edited; no full-spec copy)
```

### Verbatim `diff -r` readback (Step 3 — snapshot vs archive)

```
(empty — no differences)
```

## Archive contents

- proposal.md ✅
- design.md ✅
- exploration.md ✅
- specs/collection-vouchers/spec.md ✅
- specs/document-review/spec.md ✅
- tasks.md ✅ (36/36 implementation tasks complete)
- verify-report.md ✅
- apply-progress.md ✅
- state.yaml ✅ (updated after move; phase `archived`)
- archive-report.md ✅ (this file; additive after move)

## Verification at close

| Check | Result |
| ----- | ------ |
| Main specs updated | yes (`collection-vouchers` 8 MODIFIED + 9 ADDED + 11 REMOVED; `document-review` 6 MODIFIED; 3 preserved) |
| Change folder in archive | yes |
| Active change path gone | yes |
| tasks.md unchecked items | none |
| `diff -r` empty | yes (Step 3 snapshot vs archive; `DIFF_STATUS=0`) |
| Leftover `document-review-feature-flag/` | not touched (already absent at archive time) |

## Engram

Engram unavailable for this session — `mem_save` for `sdd/standalone-payment-vouchers/archive-report` was skipped per orchestrator instruction. OpenSpec filesystem artifacts are the audit trail.

## SDD cycle

Fully planned, implemented, verified (`pass_with_warnings`), and archived. Ready for the next change.
