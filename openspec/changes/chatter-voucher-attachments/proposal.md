# Proposal: Chatter Voucher Attachments

## Intent

Move voucher proof off Binary widgets onto chatter so operators see
the file on the thread, extras can attach, and Document Review
preview/rotates the designated proof.

## Scope

### In Scope

- Migrate Binary proofs onto chatter; drop `attachment` + `attachment_filename`
- Proof = `message_main_attachment_id`; MCP nest via `message_post` after create
  (savepoint)
- Remove Binary widgets; chatter attach after save (internal users + MCP)
- Review queue/URL/rotation use `/web/content/{id}`; proof MIME `image/*` + PDF
- Tests, version bump, pre-migration; AGENTS.md/readme in apply

### Out of Scope

- Nebula / nest schema; sibling `auto-assign-open-sheet`
- List/kanban proof cue; form Binary control; WhatsApp; public API; extra ACL

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `collection-vouchers`: proof storage, widgets, replace-reset, MCP persist path
- `document-review`: eligibility, authenticated URL, rotation reset on proof

## Approach

Lock exploration A: inherit `mail.thread.main.attachment`. Restrict mixin so
non-image/PDF cannot become main; extras (`force=False`) never steal. MCP: at
most one image/PDF; `message_post(attachments=[(name, bytes)])` after create;
exact-retry ignores nests. Keep `attachment_rotation`; reset to 0 when
main id changes (replace → pending, clear audit, rotation 0). Clearing proof
resets rotation and MUST NOT reopen a decided voucher. Pre-migrate
`res_field=attachment` (rename via `attachment_filename`, null `res_field`,
link `mail.message`) then drop Binary.

Assumptions: MCP body is a short notification (“Payment proof attached.”);
list/kanban omit a proof cue.

## Affected Areas

| Area | Impact |
|------|--------|
| `models/collection_voucher.py` | Modified — mixin; drop Binary; proof reset |
| `tools/collection_voucher.py` | Modified — `message_post`; replay unchanged |
| `views/collection_views.xml` | Modified — remove Binary widgets |
| `static/src/document_review/*` | Modified — chatter proof URL |
| `migrations/<new-version>/pre-*.py` | New — convert before drop |
| `__manifest__.py` | Modified — bump `19.0.1.12.0` |
| `tests/test_collection_*.py` | Modified — MCP, UI, review, mail |
| `openspec/specs/collection-vouchers` | Modified |
| `openspec/specs/document-review` | Modified |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Lost files if pre-migration skipped | Med | Pre-script before field drop |
| Non-image/PDF becomes main | Med | Filter mixin picker |
| In-place `datas` write skips reset | Low | Optional hook |
| Over 400-line review budget | High | Chain migrate+model, MCP, views+review |

## Rollback Plan

Revert `collection` to the prior module version and restore Binary
fields/widgets. Migrated chatter `ir.attachment` / `mail.message` MUST
remain; do not delete proofs.

## Dependencies

- `mail.thread.main.attachment`; module upgrade so `pre` runs before field drop

## Success Criteria

- [ ] No Binary field/widget; MCP nest unchanged; create posts one chatter proof
- [ ] Extra chatter files do not reset review; replacing main does
- [ ] Review uses `/web/content/{id}`; Binary proofs migrate; `invoke test -m collection` passes
