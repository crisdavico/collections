# Archive Report: seedian-nebula-mcp-voucher-tool

**Archived**: 2026-08-11  
**Archive path**: `openspec/changes/archive/2026-08-11-seedian-nebula-mcp-voucher-tool/`  
**Artifact store**: openspec (filesystem only; git index left at approved candidate tree)  
**Verdict at close**: PASS WITH WARNINGS (final state)

## Gates

| Gate | Result | Evidence |
|------|--------|----------|
| Native Review Receipt | allow | Lineage `review-fa964b4704b4cb50`; store/receipt `sha256:12050400…` / `sha256:5b0eb166…`; candidate tree `9ae58ef627153544da26bcaa00efeba14123668f`; post-apply `review validate` allow; sdd-status `reviewGate.result: allow` |
| Task Completion | pass | `tasks.md` 25/25 checkboxes `[x]` (Phases 1–5) |
| CRITICAL verify issues | none | Worktree/admitted `verify-report.md` `critical_findings: 0`, `blockers: 0`, `verdict: pass_with_warnings` |
| Action context | pass | `repo-local`; `allowedEditRoots` = seedian_nebula module |

## Final-State Authority Summary

At cycle close (highest-ranked sources):

1. **Native review**: post-apply gate allow for lineage `review-fa964b4704b4cb50`; index `git write-tree` remains `9ae58ef627153544da26bcaa00efeba14123668f` after filesystem archive (no `git add` of PASS verify-report or merged main specs into the index).
2. **Tasks**: all 25 implementation tasks complete in persisted `tasks.md`.
3. **Orchestrator final-state facts**: admitted verify is worktree PASS WITH WARNINGS (`evidence_revision: sha256:604b7a1c904abcc4839d242e7008499a203890ada70f1d0fd5fca3791163533b`; 4/4 reqs; 12/12 scenarios; tests 0 failed / 46). Staged/index copy of `verify-report.md` still holds an OLD authority-only FAIL envelope (`evidence_revision: sha256:39805bcd…`) — **not** final state; intentionally not re-staged so review identity stays intact.
4. **Verify-report (admitted intermediate, consistent with final facts)**: `pass_with_warnings`; settle was `interrupted` (prettier openspec markdown drift during settle(passed)); verify remains `all_done` in sdd-status with admitted evidence above.

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `seedian-nebula-vouchers` | Updated | **ADDED** 2 requirements (`MCP tool create_nebula_voucher`, `Payment document_id uniqueness`); **MODIFIED** 2 (`Voucher header fields and defaults`, `Menu and backend UI`); 0 removed/renamed. Preserved 6 untouched baseline requirements. |

### Destructive / BI merge warning (`rules.archive`)

Intentional backward-incompatible delta applied to main specs: drop `received_date` in favor of ORM `create_date` (migration `19.0.1.1.0`). Pre-merge baseline required `received_date`; post-merge main specs **MUST NOT** store/accept `received_date` and require readonly `create_date` instead. Mentions of `received_date` that remain are prohibition / historical notes only — **no contradiction** between published main specs and the delta after merge.

## Change Delivered

`create_nebula_voucher` MCP tool (`@mcp_tool` on `muk_mcp.mixin`, no sudo, ACL-bound), nullable unique payment `document_id` with MCP-required non-empty ids, idempotent create/replay/conflict rejection, and voucher UI/model migration off `received_date` onto `create_date`.

## Archive Contents

- proposal.md ✅
- exploration.md ✅
- design.md ✅
- specs/seedian-nebula-vouchers/spec.md ✅
- tasks.md ✅ (25/25 complete)
- apply-progress.md ✅
- verify-report.md ✅ (admitted PASS WITH WARNINGS; worktree bytes)
- state.yaml ✅
- archive-report.md ✅ (this file)

## Non-blocking warnings retained at close

1. Optional pylint C8101: manifest author is `Seedian`, not `Eynes`; mandatory pylint passed (per verify-report at verification time).
2. Prettier reformatted openspec markdown on first pre-commit pass during verify; re-run stabilized build exit 0.
3. Verify attempt settle was `interrupted` during settle(passed); admitted evidence still governs final state.
4. Git index still stages the OLD FAIL `verify-report.md` blob under the pre-archive path while worktree/archive holds PASS — intentional to preserve candidate tree `9ae58ef…` / review receipt. Delivery/commit hygiene may later rename paths and refresh evidence without claiming that FAIL is final.

## Source of Truth Updated

- `openspec/specs/seedian-nebula-vouchers/spec.md` (filesystem worktree merged; index blob may lag until a future staged delivery)

## SDD Cycle Complete

Planned, implemented, verified, reviewed (native approved), and archived. Ready for the next change.
