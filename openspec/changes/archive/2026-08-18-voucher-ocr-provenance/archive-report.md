# Archive Report: voucher-ocr-provenance

**Date**: 2026-08-18 **Change**: voucher-ocr-provenance **Archived to**:
`openspec/changes/archive/2026-08-18-voucher-ocr-provenance/` **Artifact store**:
openspec **Status**: success **Intentional warnings**: yes (verify `pass_with_warnings`
at verification time — zero CRITICAL; Nebula nested provenance client remains out of
scope; duplicate `ir.model` same-label warnings for `ocr_*`/`seller_*` vs current fields
are intentional UX)

## Quick path

1. Main specs now require typed OCR/seller provenance, MCP nests, immutable Document
   Review snapshots, and three-way form/OWL comparison (ADDED only).
2. Change folder is archived; active `openspec/changes/voucher-ocr-provenance/` is gone.
3. Snapshot vs archive `diff -r` is empty (`DIFF_STATUS=0`).

## Gates

| Gate                      | Result               | Evidence                                                                                                                                                                         |
| ------------------------- | -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Task Completion           | PASS                 | Archived `tasks.md` — no `- [ ]`; tasks 1.1–3.2 all `[x]` (14/14). Orchestrator instructed not to reconcile checkboxes.                                                          |
| Native Review Receipt     | PASS (absent)        | `reviewGate` structurally absent; user declined post-verify `reviewOffer` by requesting archive; proceeded under ordinary repository policy; no receipt demanded                 |
| CRITICAL in verify-report | PASS                 | `critical_findings: 0`, `blockers: 0`; verdict `pass_with_warnings` at verification time                                                                                         |
| Destructive delta         | PASS (additive only) | `rules.archive`: warn before merging destructive or backward-incompatible deltas. Deltas are ADDED only (no MODIFIED / REMOVED / RENAMED). No large-section removal. Not a stop. |
| Action context            | PASS                 | `actionContext.mode: repo-local`; edits stayed inside `allowedEditRoots` (`odoo/custom/src/private/collection`). Nebula-agent was not edited.                                    |

## Intentional shipped notes (`rules.archive`)

Merge is additive: four ADDED requirements on `collection-vouchers` and five ADDED
requirements on `document-review`. Existing requirements were preserved. Upgrade is
nullable provenance with no backfill (`19.0.1.14.0`). Sibling
`chatter-voucher-attachments` is already archived independently; this change did not
touch `migrations/19.0.1.13.0/`. Empty MCP provenance when nests are omitted remains
expected until a separate Nebula nested-provenance client ships.

## Final-state authority

Per orchestrator launch facts (outrank stale `verify-report` / `apply-progress` pending
claims) and persisted `tasks.md`:

- All tasks 1.1–3.2 complete in `tasks.md` (14/14; no `- [ ]`)
- Verify at verification time: `pass_with_warnings`; `critical_findings: 0`;
  `blockers: 0`; requirements `9/9`; scenarios `18/18`; collection tests **0 failed of
  278** (stats 308)
- **Post-verify UI fix shipped** (same change, before archive): Raw OCR / Seller
  Confirmed form pages use union visibility with Current `document_type` so empty
  `ocr_*`/`seller_*` types still show Current’s bank-transfer/check widgets. Provenance
  field `string=` labels match Current. OWL `_layerHasDocumentType` treats a type as
  visible if any of current / ocr / seller matches. **Document ID remains Current-only
  by design.**
- Focused tests after that UI fix:
  `docker exec -i seedian-odoo-1 odoo -d devel --test-enable --stop-after-init --workers=0 --http-port=18069 -u collection --test-tags /collection:TestCollectionUi,/collection:TestCollectionDocumentReview.test_owl_keeps_type_visibility_hides_document_id_and_shows_provenance`
  → `0 failed, 0 error(s) of 36 tests when loading database 'devel'`;
  `collection: 40 tests`. Duplicate `ir.model` same-label warnings for
  `ocr_*`/`seller_*` vs current fields are intentional UX, not a defect.
- Manifest `19.0.1.14.0`; Nebula nested provenance client was out of scope and is still
  not shipped; empty provenance values on MCP create remain expected until a separate
  change
- No git commits or PRs were created for this change
- `reviewGate` absent; user declined the post-verify `reviewOffer` by requesting archive

Attributed snapshot history (not current state):

- Per `verify-report` at verification time: OWL type-specific field visibility followed
  current `document_type` only (`isBankTransfer`/`isCheck` from current) for all three
  OWL columns together, weaker than the form notebook’s per-layer types. That warning is
  **not** a current open gap. The later form+OWL union-visibility fix (final-state
  fact 3) is the close state.
- Per `verify-report` at verification time: config `build_command` `invoke img-build`
  was substituted with scoped pre-commit; optional pylint C8101 author warning
  (`Seedian` vs `Eynes`) is pre-existing; task 1.9 Nebula nested provenance remained
  collection-only. Those warnings are not current blockers.
- Per `apply-progress` remaining-task sections from earlier PR slices are superseded by
  tasks 1.1–3.2 `[x]`
- Archived `state.yaml` is orchestrator-owned and was left as-is (`phase: verify`); it
  still mentions the OWL warning in notes. That note is snapshot history, not final
  state.

## Spec sync

Performed **before** the folder move. Both main specs already existed. Merge was
heading-matched (not a mechanical copy of the delta over the main spec). Requirements
not named in the delta were preserved. No REMOVED/RENAMED. No MODIFIED.

**Domain**: `collection-vouchers` **Main spec**:
`openspec/specs/collection-vouchers/spec.md` (existing; merge by edit)

| Action   | Requirement                                               |
| -------- | --------------------------------------------------------- |
| ADDED    | Typed provenance copies of payment fields (3 scenarios)   |
| ADDED    | MCP nested provenance on all-new create (5 scenarios)     |
| ADDED    | Immutable review snapshots and ACL (2 scenarios)          |
| ADDED    | Additive upgrade without provenance backfill (1 scenario) |
| MODIFIED | none                                                      |
| REMOVED  | none                                                      |
| RENAMED  | none                                                      |

Preserved unchanged: Voucher sequence naming; Mail thread and activities; Authorization
for internal users; Deferred integrations not required; Payment document_id uniqueness;
MCP optional payment attachment on create; Concurrent and stale review attempts;
Attachment replacement resets review to pending; Voucher fields and defaults; Voucher
lifecycle; Payment field contract; Payment Vouchers UI; Unsupported vouchers remain
persistable; MCP tool create_collection_vouchers; Optional image or PDF attachment per
voucher; Attachment widgets on Payment Vouchers views; Destructive reset of legacy
header and line data; Voucher seller field; Create auto-assign to open sheet; Designated
proof is message_main_attachment_id; Pre-upgrade migration of Binary proofs. Purpose
line unchanged. RFC 2119 / Given-When-Then retained.

**Domain**: `document-review` **Main spec**: `openspec/specs/document-review/spec.md`
(existing; merge by edit)

| Action   | Requirement                                                        |
| -------- | ------------------------------------------------------------------ |
| ADDED    | Three-way raw, seller, and current comparison (2 scenarios)        |
| ADDED    | Queue payload includes readonly provenance (1 scenario)            |
| ADDED    | Document Review decisions append immutable snapshots (2 scenarios) |
| ADDED    | Repeated Document Review appends another revision (1 scenario)     |
| ADDED    | Voucher review history is visible (1 scenario)                     |
| MODIFIED | none                                                               |
| REMOVED  | none                                                               |
| RENAMED  | none                                                               |

Preserved unchanged: Eligible review queue; OWL client loads real ORM data;
Authenticated binary attachment viewer; Viewer fit and cursor-anchored zoom; Viewer
rotation; Approve and reject without mocks; Document Review authorization; Per-company
Document Review flag; Document Review menu and RPCs when flag is off; Sheet identifier
required on review operations. Purpose line unchanged.

## Mechanical archive

- Method: `git mv` failed (`fatal: source directory is empty` — change artifacts were
  untracked); `mv openspec/changes/voucher-ocr-provenance` →
  `openspec/changes/archive/2026-08-18-voucher-ocr-provenance` succeeded
- Archive path: `openspec/changes/archive/2026-08-18-voucher-ocr-provenance/`
- Active path removed: `openspec/changes/voucher-ocr-provenance/` no longer exists
- Pre-move snapshot vs archive `diff -r`: empty (byte-identical); `DIFF_STATUS=0`
- Archive-report is additive after the move and excluded from the snapshot comparison
- `state.yaml` left as-is (orchestrator-owned; not edited)

### Verbatim `diff -r` readback (Step 2 — collection-vouchers merge)

In-place heading-matched merge into the existing main spec (not a mechanical full-spec
overwrite). 4 ADDED appended; 0 MODIFIED; 0 REMOVED; 0 RENAMED; other requirements
preserved.

```
(n/a — existing main spec edited; ADDED appended; other requirements preserved)
```

### Verbatim `diff -r` readback (Step 2 — document-review merge)

In-place heading-matched merge into the existing main spec (not a mechanical full-spec
overwrite). 5 ADDED appended; 0 MODIFIED; 0 REMOVED; 0 RENAMED; other requirements
preserved.

```
(n/a — existing main spec edited; ADDED appended; other requirements preserved)
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
- tasks.md ✅ (14/14 implementation tasks complete)
- verify-report.md ✅
- apply-progress.md ✅
- state.yaml ✅ (left as-is; orchestrator-owned)
- archive-report.md ✅ (this file; additive after move)

## Verification at close

| Check                    | Result                                                                         |
| ------------------------ | ------------------------------------------------------------------------------ |
| Main specs updated       | yes (`collection-vouchers` 4 ADDED; `document-review` 5 ADDED)                 |
| Change folder in archive | yes                                                                            |
| Active change path gone  | yes                                                                            |
| tasks.md unchecked items | none                                                                           |
| `diff -r` empty          | yes (Step 3 snapshot vs archive empty; `DIFF_STATUS=0`)                        |
| Unrelated WIP            | not touched (`migrations/19.0.1.13.0/`, sibling chatter archive, nebula-agent) |

## Engram

OpenSpec mode — filesystem artifacts are the audit trail. No Engram `mem_save`.

## Out of scope at close

- Nebula nested provenance client is still not shipped (intentional; separate change)
- No git commits or PRs were created for this change
- `migrations/19.0.1.13.0/` was not touched
- Duplicate same-label `ir.model` warnings for provenance vs current fields are
  intentional UX

## SDD cycle

Fully planned, implemented, verified (`pass_with_warnings` at verification time; OWL
type-visibility warning later fixed in the same change), and archived. Ready for the
next change.
