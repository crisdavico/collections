# Proposal: Collection Company Configuration

## Intent

Collections is company-blind. Persist one config per company on existing `res.company` + related `res.config.settings` (not POS-style). No extra groups.

**User impact:** Admins toggle Collection Settings. New work needs an enabled seller and allowed type; existing rows stay operable if seller disabled.

## Scope

### In Scope

- Rename XMLID `collection.action_collection_config_settings` **labels** to **Collection Settings** (keep XMLID, `action-540`).
- `enabled_seller_ids` (empty = none for NEW work; upgrade seeds used sellers per company); `auto_create_sheet` default ON; `allowed_document_type_ids` (transfer, check, cash deposit, Unsupported — all on; Unsupported configurable); keep `document_review_enabled`.
- NEW paths (UI, ORM/import, MCP): seller required + enabled. Same-company MCP replay unchanged. `auto_create_sheet` off skips auto create AND assign; list Action and explicit sheet create remain.
- Required `company_id` on vouchers/sheets; allowed-company `ir.rule`; one-open by company AND seller. Per-company sequences (same codes, `with_company`; convert `company_id=False` to main and copy).
- `document_id` globally unique; other-company hit: reject, not replay, not disclose. Snapshot related stored `company_id` + same `ir.rule`. Catalog + Many2many; voucher `document_type` stays Selection (3a). `get_seller_id` unfiltered.

### Out of Scope

Proof requirement, review threshold, collection kill switch, accounting/journals, HTTP API, Nebula-agent, POS-style config, renaming `action-540`, filtering `get_seller_id`.

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `collection-vouchers`: company ownership; required/enabled seller; allowed types; reject-not-replay `document_id`; sequences; MCP; settings validation
- `collection-sheets`: company ownership; one-open by company+seller; `auto_create_sheet`; required/enabled seller; sequences; record rules
- `seller-lookup`: no-regression — unfiltered by enabled sellers / company allow-list
- `document-review`: `document_review_enabled` preserved; snapshot `company_id` + company `ir.rule`

## Approach

Catalog `collection.document.type` Many2many; keep voucher Selection. Company `ir.rule` on voucher, sheet, snapshot. Gate new writes; skip exact same-company MCP replay. Cross-company `document_id` → generic `UserError` (no `sudo()`). `with_company` sequences; convert then copy. Seed used sellers.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| company/settings | Modified | fields + labels |
| voucher, sheet, snapshot, MCP | Modified | `company_id`, gates, reject-not-replay |
| sequences, security, views, tests | Modified | per-company seq; `ir.rule`; `get_seller_id` unchanged |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Specs contradict this | High | Delta specs + TDD |
| Cross-company UniqueViolation/snapshot leak | Med | Generic reject; snapshot `company_id`+`ir.rule` |
| Sequence leftovers, empty allow-list, 400-line budget | Med | Convert+copy; seed; chained PRs |

## Rollback Plan

Revert collection commits and `-u collection`. If sequences advanced, restore from DB backup.

## Dependencies

Settings XMLID `collection.action_collection_config_settings`; `muk_mcp` names unchanged; no Nebula-agent.

## Success Criteria

- [ ] New create: enabled seller, allowed type, company isolation; same-company MCP replay; other-company `document_id` rejected undisclosed
- [ ] `auto_create_sheet` off skips auto create/assign; `get_seller_id` unfiltered; Settings labels and review flag preserved; `invoke test -m collection`
