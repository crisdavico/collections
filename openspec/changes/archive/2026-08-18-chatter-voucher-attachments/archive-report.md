# Archive Report: chatter-voucher-attachments

**Date**: 2026-08-18 **Change**: chatter-voucher-attachments **Archived to**:
`openspec/changes/archive/2026-08-18-chatter-voucher-attachments/` **Artifact store**:
openspec **Status**: success **Intentional warnings**: yes (verify `pass_with_warnings`
— zero CRITICAL; Binary→chatter is an intentional shipped incompatibility with migrate
then drop field; optional pylint C8101 author Eynes vs Seedian is pre-existing)

## Quick path

1. Main specs now require designated proof on chatter (`message_main_attachment_id`).
2. Change folder is archived; active `openspec/changes/chatter-voucher-attachments/` is
   gone.
3. Snapshot vs archive `diff -r` is empty (`DIFF_STATUS=0`).

## Gates

| Gate                      | Result                                     | Evidence                                                                                                                                                                                             |
| ------------------------- | ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Task Completion           | PASS                                       | Archived `tasks.md` — no `- [ ]`; tasks 1.1–4.3 all `[x]` (21/21)                                                                                                                                    |
| Native Review Receipt     | PASS (absent)                              | `reviewGate` structurally absent; archive proceeded under ordinary repository policy; no receipt demanded                                                                                            |
| CRITICAL in verify-report | PASS                                       | `critical_findings: 0`, `blockers: 0`; verdict `pass_with_warnings`                                                                                                                                  |
| Destructive delta         | PASS (intentional shipped incompatibility) | `rules.archive`: warn before merging destructive or backward-incompatible deltas. This change ADDS + MODIFIES attachment storage (Binary → chatter). No REMOVED/RENAMED. Recorded below; not a stop. |
| Action context            | PASS                                       | `actionContext.mode: repo-local`; edits stayed inside `allowedEditRoots` (`odoo/custom/src/private/collection`)                                                                                      |

## Intentional shipped incompatibility (`rules.archive`)

Proof storage moved from Binary `attachment` / `attachment_filename` to chatter
designated proof (`message_main_attachment_id`). Upgrade path is migrate then drop field
(`migrations/19.0.1.13.0`). This is an intentional shipped incompatibility, not an
archive blocker. No large-section REMOVED merge was performed.

## Final-state authority

Per orchestrator launch facts (outrank stale `verify-report` / `apply-progress` pending
claims) and persisted `tasks.md`:

- All tasks 1.1–4.3 complete in `tasks.md` (21/21; no `- [ ]`)
- Verify at close: `pass_with_warnings`; `critical_findings: 0`; `blockers: 0`;
  requirements `10/10`; scenarios `26/26`
- Authoritative tests: scoped docker collection suite **0 failed, 0 errors of 242**
  (`--mode=update` / `-u collection`). Bare invoke that included uncommitted
  `voucher-ocr-provenance` WIP is **not** a current failure of this change
- Manifest `19.0.1.13.0`; Nebula out of scope
- Stacked local commits (not pushed): `86bb6a8` (01-migrate-model), `78c3f96`
  (02-mcp-tests), `68d5bfc` (03-document-review), `51b3268` + `870416d` (04-upgrade)
- Maintainer reset the runtime line-budget block to allow archive
- `reviewGate` absent

Attributed snapshot history (not current state):

- Per `verify-report` at verification time: config `build_command` `invoke img-build`
  was skipped in favor of module-load; optional pylint C8101 author warning; uncommitted
  provenance WIP contaminated a bare invoke. Those warnings are not current blockers.
  The provenance WIP remains out of this change
- Per `apply-progress` remaining-task sections from earlier PR slices are superseded by
  tasks 1.1–4.3 `[x]`

## Spec sync

Performed **before** the folder move. Both main specs already existed. Merge was
heading-matched (not a mechanical copy of the delta over the main spec). Requirements
not named in the delta were preserved. No REMOVED/RENAMED.

**Domain**: `collection-vouchers` **Main spec**:
`openspec/specs/collection-vouchers/spec.md` (existing; merge by edit)

| Action   | Requirement                                                                                                   |
| -------- | ------------------------------------------------------------------------------------------------------------- |
| ADDED    | Designated proof is message_main_attachment_id (3 scenarios)                                                  |
| ADDED    | Pre-upgrade migration of Binary proofs (2 scenarios)                                                          |
| MODIFIED | Optional image or PDF attachment per voucher — copy-full replace (chatter `ir.attachment`, empty `res_field`) |
| MODIFIED | Attachment widgets on Payment Vouchers views — copy-full replace (no Binary widgets; chatter remains)         |
| MODIFIED | MCP optional payment attachment on create — copy-full replace (`message_post`; exact-retry ignores nests)     |
| MODIFIED | Concurrent and stale review attempts — copy-full replace (eligibility uses designated proof)                  |
| MODIFIED | Attachment replacement resets review to pending — copy-full replace (main id change; extras/clear)            |
| REMOVED  | none                                                                                                          |
| RENAMED  | none                                                                                                          |

Preserved unchanged: Voucher sequence naming; Mail thread and activities; Authorization
for internal users; Deferred integrations not required; Payment document_id uniqueness;
Voucher fields and defaults; Voucher lifecycle; Payment field contract; Payment Vouchers
UI; Unsupported vouchers remain persistable; MCP tool create_collection_vouchers;
Destructive reset of legacy header and line data; Voucher seller field; Create
auto-assign to open sheet. Purpose line unchanged. RFC 2119 / Given-When-Then retained.

**Domain**: `document-review` **Main spec**: `openspec/specs/document-review/spec.md`
(existing; merge by edit)

| Action   | Requirement                                                                                   |
| -------- | --------------------------------------------------------------------------------------------- |
| MODIFIED | Eligible review queue — copy-full replace (designated proof `message_main_attachment_id`)     |
| MODIFIED | Authenticated binary attachment viewer — copy-full replace (`/web/content/{id}`; no `field=`) |
| MODIFIED | Viewer rotation — copy-full replace (reset on main id change or clear; extras do not reset)   |
| ADDED    | none                                                                                          |
| REMOVED  | none                                                                                          |
| RENAMED  | none                                                                                          |

Preserved unchanged: OWL client loads real ORM data; Viewer fit and cursor-anchored
zoom; Approve and reject without mocks; Document Review authorization; Per-company
Document Review flag; Document Review menu and RPCs when flag is off; Sheet identifier
required on review operations. Purpose line unchanged.

Working-tree note: `document-review/spec.md` already held uncommitted
`sheet-scoped-document-review` sync (menu absence + sheet identifier). Chatter MODIFIED
blocks were applied on that on-disk base so those preserved requirements were not
reverted. The archive commit stages only this change's chatter hunks plus the
collection-vouchers merge; leftover sheet-scoped spec hunks remain unstaged WIP.

## Mechanical archive

- Method: `git add -- openspec/changes/chatter-voucher-attachments` then
  `git mv openspec/changes/chatter-voucher-attachments` →
  `openspec/changes/archive/2026-08-18-chatter-voucher-attachments` succeeded
- Archive path: `openspec/changes/archive/2026-08-18-chatter-voucher-attachments/`
- Active path removed: `openspec/changes/chatter-voucher-attachments/` no longer exists
- Pre-move snapshot vs archive `diff -r`: empty (byte-identical); `DIFF_STATUS=0`
- Archive-report is additive after the move and excluded from the snapshot comparison
- `state.yaml` updated after the empty `diff -r` to `phase: archived`

### Verbatim `diff -r` readback (Step 2 — collection-vouchers merge)

In-place heading-matched merge into the existing main spec (not a mechanical full-spec
overwrite). 2 ADDED appended; 5 MODIFIED blocks replaced in full; other requirements
preserved.

```
(n/a — existing main spec edited; ADDED appended; MODIFIED replaced; other requirements preserved)
```

### Verbatim `diff -r` readback (Step 2 — document-review merge)

In-place heading-matched merge into the existing main spec (not a mechanical full-spec
overwrite). 3 MODIFIED blocks replaced in full; other requirements preserved.

```
(n/a — existing main spec edited; MODIFIED replaced; other requirements preserved)
```

### Verbatim `diff -r` readback (Step 3 — snapshot vs archive)

```
=== DIFF snapshot vs archive (verbatim) ===
=== END DIFF ===
DIFF_STATUS=0
```

Empty output between the markers; no differences.

## Archive contents

- proposal.md ✅
- design.md ✅
- exploration.md ✅
- specs/collection-vouchers/spec.md ✅
- specs/document-review/spec.md ✅
- tasks.md ✅ (21/21 implementation tasks complete)
- verify-report.md ✅
- apply-progress.md ✅
- state.yaml ✅ (updated after move; phase `archived`)
- archive-report.md ✅ (this file; additive after move)

## Verification at close

| Check                    | Result                                                                                                               |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| Main specs updated       | yes (`collection-vouchers` 2 ADDED + 5 MODIFIED; `document-review` 3 MODIFIED)                                       |
| Change folder in archive | yes                                                                                                                  |
| Active change path gone  | yes                                                                                                                  |
| tasks.md unchecked items | none                                                                                                                 |
| `diff -r` empty          | yes (Step 3 snapshot vs archive empty; `DIFF_STATUS=0`)                                                              |
| Unrelated WIP            | not touched (seller-lookup, provenance, older archives, README.rst, product code still dirty and out of this change) |

## Engram

Engram unavailable for this session — skip `mem_save` per orchestrator instruction.
OpenSpec filesystem artifacts are the audit trail.

## Out of scope at close

- Unrelated dirty WIP remains unstaged and is not part of this change
- Stacked feature commits are not pushed
- Nebula-agent is not updated (intentional)

## SDD cycle

Fully planned, implemented, verified (`pass_with_warnings`), and archived. Ready for the
next change.
