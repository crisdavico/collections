# Archive Report: document-review-feature-flag

**Date**: 2026-08-12
**Change**: document-review-feature-flag
**Archived to**: `openspec/changes/archive/2026-08-12-document-review-feature-flag/`
**Artifact store**: openspec
**Status**: success
**Intentional warnings**: yes (verify pass_with_warnings — four accepted non-blocking
deviations)

## Gates

| Gate                      | Result        | Evidence                                                                                                  |
| ------------------------- | ------------- | --------------------------------------------------------------------------------------------------------- |
| Task Completion           | PASS          | Archived `tasks.md` — no `- [ ]`; tasks 1.1–4.1 all `[x]` (17/17)                                         |
| Native Review Receipt     | PASS (absent) | `reviewGate` structurally absent; archive proceeded under ordinary repository policy; no receipt demanded |
| CRITICAL in verify-report | PASS          | `critical_findings: 0`, blockers: 0; verdict `pass_with_warnings`                                         |
| Destructive delta         | PASS          | Merge non-destructive (ADDED + MODIFIED only; no REMOVED)                                                 |

## Final-state authority

Per orchestrator launch facts (outrank stale snapshot “pending” claims):

- All 17 tasks complete in `tasks.md` (no `- [ ]`)
- Verify verdict at close: `pass_with_warnings`; blockers 0; critical_findings 0;
  CRITICAL: none
- Tests at close: 130/130 via `invoke test -m collection`
- Spec envelope: 15/15 scenarios (13 COMPLIANT, 2 PARTIAL)
- Build / scoped pre-commit: exit 0
- First verify failed on two ruff E501s; those lines were wrapped; second verify
  admitted `pass_with_warnings`
- Four WARNINGs remain accepted at close (not pending work, not CRITICAL):
  1. PARTIAL: `/odoo/document-review` covered by RPC `UserError` only (no browser E2E)
  2. PARTIAL: payment-line audit columns (`reviewed_by` / `reviewed_at`) not on
     list/search views; `state` remains
  3. Design: `_load_menus_blacklist` has no `@api.model` (matches Odoo 19 core/hr)
  4. Optional pre-existing pylint C8101 manifest-required-author
- No stacked PRs created yet
- Intentional override: user explicitly asked to archive after `pass_with_warnings` (no
  CRITICAL)
- Engram unavailable — `mem_save` skipped (noted below)

## Spec sync

Performed **before** the folder move. Merge via editing main spec files (not a byte-copy
of the change folder).

**Domain**: `document-review`
**Main spec**: `openspec/specs/document-review/spec.md` (existing; all prior
requirements preserved)

| Action   | Requirement                                                  |
| -------- | ------------------------------------------------------------ |
| ADDED    | Per-company Document Review flag (3 scenarios)               |
| ADDED    | Document Review menu and RPCs when flag is off (3 scenarios) |
| MODIFIED | none                                                         |
| REMOVED  | none                                                         |
| RENAMED  | none                                                         |

**Domain**: `collection-vouchers`
**Main spec**: `openspec/specs/collection-vouchers/spec.md`

| Action   | Requirement                                                                                                                                                               |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| MODIFIED | Voucher state transitions — replaced entire requirement block (flag-gated pending-attached validate; new “Validate succeeds with pending attachments when review is off”) |
| MODIFIED | Approve may validate voucher when all attached lines approved — replaced entire block (ON-only approve; new “Review approve does not run when off”)                       |
| MODIFIED | Line reject immediately rejects voucher — replaced entire block (ON-only reject; new “Review reject does not run when off”)                                               |
| ADDED    | none                                                                                                                                                                      |
| REMOVED  | none                                                                                                                                                                      |
| RENAMED  | none                                                                                                                                                                      |

Merge was non-destructive (ADDED + MODIFIED; no REMOVED). Every other main-spec
requirement preserved. RFC 2119 / Given-When-Then retained.

## Mechanical archive

- Method: `git mv` failed (`fatal: source directory is empty` — change folder untracked
  in the nested collection git repo); fallback `mv` succeeded
- Archive path: `openspec/changes/archive/2026-08-12-document-review-feature-flag/`
- Active path removed: `openspec/changes/document-review-feature-flag/` no longer exists
- Pre-move snapshot vs archive `diff -r`: empty (byte-identical); `DIFF_STATUS=0`
- Archive-report is additive after the move and excluded from the snapshot comparison
- Post-comparison `printf` of a `--`-prefixed banner failed in the same shell; it did
  not alter files or the already-empty `diff -r`

### Verbatim `diff -r` readback (Step 2 — spec merge)

Spec sync was in-place heading-matched merge into existing main specs (not a mechanical
full-spec copy). No Step 2 `cp`/`diff -r` for a new domain file.

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
- specs/document-review/spec.md ✅
- specs/collection-vouchers/spec.md ✅
- tasks.md ✅ (17/17 implementation tasks complete)
- verify-report.md ✅
- apply-progress.md ✅
- state.yaml ✅ (as at move; phase `ready-for-archive`)
- archive-report.md ✅ (this file; additive after move)

## Verification at close

| Check                    | Result                                                             |
| ------------------------ | ------------------------------------------------------------------ |
| Main specs updated       | yes (`document-review` +2 ADDED; `collection-vouchers` 3 MODIFIED) |
| Change folder in archive | yes                                                                |
| Active change path gone  | yes                                                                |
| tasks.md unchecked items | none                                                               |
| `diff -r` empty          | yes (Step 3 snapshot vs archive; `DIFF_STATUS=0`)                  |

## Engram

Engram unavailable for this session — `mem_save` for
`sdd/document-review-feature-flag/archive-report` was skipped per orchestrator
instruction. OpenSpec filesystem artifacts are the audit trail.

## SDD cycle

Fully planned, implemented, verified (`pass_with_warnings`), and archived. Ready for the
next change.
