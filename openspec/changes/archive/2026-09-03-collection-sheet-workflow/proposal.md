# Proposal: Collection Sheet Workflow

## Intent

Need a collections-review gate before freeze and an allocation-edit window after,
without blocking MCP from a new Open sheet.

## Assumptions

- Open `--Confirm-->` Proposal `--Close-->` Closed; Proposal or Closed `--Cancel-->`
  Cancelled `--Open-->` Open. Drop Reopen. Reject illegal raw writes and non-open
  create.
- Confirm `UserError` unless every member is `validated_collections`; empty members
  pass.
- One-open/MCP still `open` only. Nebula out. Unlink refuse Proposal/Closed/Cancelled.
  `19.0.1.33.0`. Strict TDD. `auto-chain`.

## Scope

### In Scope

- Four-state sheet; audited Confirm/Close/Cancel/Open; Confirm gate; freeze voucher
  membership/business fields in Proposal/Closed/Cancelled.
- Allocations: draft Open/Proposal/Cancelled; confirmed Closed only; writable
  Open/Proposal; Close confirms; Cancel drafts. Tabs Allocations / Vouchers / Debt per
  plan. Drop Reassign UI/`group_expand`/auto-follow; keep partner-allocation constraint.
- Recon freeze Closed/Cancelled; PDF/XLSX all states. Review header Open-only. Odoo only
  in `collection/`.

### Out of Scope

- Nebula/MCP payload changes; empty-sheet Confirm refuse; report redesign;
  `voucher-states-ui/**`; Copier/git-aggregate.

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `collection-sheets`: four-state lifecycle, tabs, buttons, Confirm gate,
  freeze/editability, drop Reassign, Open-only Review header, one-open still `open`
  only.
- `collection-vouchers`: remove Reassign/`group_expand`/allocation-follow; keep
  constraint; membership Open-only; business-field guards Proposal/Closed/Cancelled.
- `collection-allocations`: draft on Open/Proposal/Cancelled, writable only
  Open/Proposal; confirmed only Closed; Close confirms; Cancel drafts.
- `collection-sheet-report`: freeze recon Closed/Cancelled; PDF/XLSX all four states;
  notebook one page → three.
- `document-review`: Review header only in Open.

## Approach

RED tests then: four-state sheet; allocation iff + sheet-state guards; related debt
lines; drop reassign/`<delete>` kanban. MCP: Proposal does not occupy open.

## Affected Areas

| Area                                                                           | Impact   | Description                                      |
| ------------------------------------------------------------------------------ | -------- | ------------------------------------------------ |
| `models/collection_{sheet,allocation,allocation_line,sheet_report,voucher}.py` | Modified | Lifecycle, iff, freeze, drop follow              |
| `views/collection_views.xml`, `collection_allocation_views.xml`                | Modified | Buttons, tabs, modifiers, delete reassign kanban |
| `tests/test_collection_*.py`                                                   | Modified | Lifecycle, UI, freeze, PDF/XLSX                  |
| `__manifest__.py`, `AGENTS.md`, `readme/`                                      | Modified | `19.0.1.33.0` + docs                             |

## Risks

| Risk                                  | Likelihood | Mitigation                           |
| ------------------------------------- | ---------- | ------------------------------------ |
| File overlap with `voucher-states-ui` | High       | Land it first; never edit its folder |
| Confirm needs `validated_collections` | High       | Use HEAD baseline                    |
| Cancelled draft allocations writable  | Med        | Sheet-state server + view guards     |
| 400-line review budget                | High       | Chained PRs                          |

## Rollback Plan

Revert `collection` to pre-change commit. Open/Closed rows stay valid (no remap).
Reassign XML and additive fields restore/drop cleanly.

## Dependencies

- voucher-states-ui on HEAD. No new deps.

## Success Criteria

- [ ] Agreed transitions only; Confirm `UserError` until every member is
      `validated_collections`.
- [ ] Allocation iff/write rules match Capabilities; Reassign gone; constraint remains.
- [ ] Review + Confirm Open-only; PDF/XLSX all states; MCP still `open`-only.
- [ ] `invoke test -m collection --mode=update` + scoped pre-commit; manifest
      `19.0.1.33.0`.
