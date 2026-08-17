# Proposal: Collection Sheets

## Intent

Add `collection.sheet` so operators group a seller’s vouchers. No sheet workflow. New UI
and all-new MCP creates require `seller_id`; existing vouchers stay nullable, not
backfilled. Sheet delete unassigns members; vouchers remain.

## Scope

### In Scope

- `collection.sheet`: `CS/<year>/<number>` (code `collection.sheet`, prefix
  `CS/%(year)s/`); required `seller_id`; stored `date_from`/`date_to`; no `state`.
- `seller_id → res.users` on voucher (ORM nullable) and sheet (required). Domain
  `[('share', '=', False)]`. Form + MCP all-new required; no backfill.
- One sheet per voucher. List-bound `ir.actions.server` on unassigned same-seller
  vouchers (any state). No wizard. Membership editable; empty sheets allowed.
- MCP: required top-level `seller_id`; validate internal user; stamp all-new only; exact
  `document_id` replay MUST NOT mutate legacy matching vouchers; keep attachment
  atomicity.

### Out of Scope

- Nebula — breaking follow-up consumer only; do not edit nebula-agent. Leftover
  `apply.roots` in `openspec/config.yaml` is not permission to change Nebula.
- Sheet workflow, extra groups/rules, `document-review`, seller backfill,
  WhatsApp/HTTP/CRM/multi-currency.

## Capabilities

### New Capabilities

- `collection-sheets`: grouping model, sequence, membership, dates, create Action, ACL,
  unlink-unassign.

### Modified Capabilities

- `collection-vouchers`: nullable `seller_id` + UI; MCP top-level `seller_id` required
  on request, applied only on all-new create; exact replay MUST NOT mutate legacy
  matching vouchers.

## Approach

Many2one `sheet_id` (`ondelete="set null"`) + inverse `voucher_ids`. `@api.constrains`
for same-seller and assigned⇒seller; optional
`CHECK(sheet_id IS NULL OR seller_id IS NOT NULL)`; no `UNIQUE(sheet_id)`; no triggers.
Dates = UTC calendar min/max member `create_date`; empty ⇒ both empty. Sheet `seller_id`
required, readonly after create. ACL: one `base.group_user` CRUD row. Do not copy
`create_uid` as seller.

## Affected Areas

- New: `models/collection_sheet.py`
- Modified: `models/collection_voucher.py` (`seller_id`, `sheet_id`, constraints,
  Action); `views/collection_views.xml`; `data/ir_sequence_data.xml`;
  `security/ir.model.access.csv`; `tools/collection_voucher.py`; tests;
  `__manifest__.py`

## Risks

- High — Nebula all-new MCP fails without `seller_id`. Follow-up consumer; exact replay
  still works.
- Med — form required vs ORM nullable. Keep ORM `required=False`.
- Med — UTC vs local date near midnight. Pin UTC date; no `received_date`.
- High — authored diff > 400 lines. `sdd-tasks` forecast chained PRs.

## Rollback Plan

Revert the collection git change and restore the prior module version. Vouchers persist.
Sheet rows and `sheet_id`/`seller_id` columns drop. No seller backfill to undo.

## Dependencies

Existing voucher sequence/MCP/ACL. Module upgrade. No new Doodba deps.

## Success Criteria

- [ ] Sheets `CS/<year>/<number>`; no workflow; `base.group_user` ACL only
- [ ] Action creates one sheet from unassigned same-seller vouchers (any state); one
      sheet per voucher; membership editable; same-seller enforced; unlink unassigns
- [ ] Dates from min/max member `create_date` (UTC); empty sheet ⇒ empty dates
- [ ] New UI/MCP all-new require seller; existing remain nullable; exact replay does not
      mutate legacy matching vouchers; attachments/idempotency unchanged
- [ ] Nebula not implemented; module tests pass
