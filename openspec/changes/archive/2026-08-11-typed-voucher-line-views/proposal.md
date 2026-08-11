# Proposal: Typed voucher line tables and payment-lines menu

## Intent

Operators edit all payment types in one dense lines list. They need type-specific
stacked tables on the voucher form and a filterable payment-lines menu, without
splitting the model.

## Scope

### In Scope

- Replace the single editable `payment_ids` list with three stacked typed tables: bank
  transfer, check, cash deposit.
- Auto-set `document_type` on add; hide type column; show type fields + `document_id`.
- Remove the old all-columns payment-lines table.
- Add Collections → Payment Lines: read-only list/search on `collection.voucher.line`
  with field filters.
- Keep mixed types per voucher; same models; MCP unchanged.

### Out of Scope

- Separate models per type; editable Payment Lines menu; `unsupported` form table;
  WhatsApp / partner / attachments / multi-currency.

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `collection-vouchers`: Typed stacked form tables; read-only Payment Lines menu; show
  `document_id` in those UIs (UI omit still allowed).

## Approach

Keep `collection.voucher.line`. Use three domain-filtered One2many embeds of
`payment_ids` (or typed One2many with same inverse) with `default_document_type` context
and distinct list arches. Add read-only `act_window` + search/list for lines. Update UI
TransactionCase; no MCP/schema migration beyond views.

## Affected Areas

| Area                           | Impact    | Description                     |
| ------------------------------ | --------- | ------------------------------- |
| `models/collection_voucher.py` | Modified  | Optional typed One2many helpers |
| `views/collection_views.xml`   | Modified  | Stacked typed lists; line menu  |
| `tests/test_collection_ui.py`  | Modified  | Arch/menu assertions            |
| MCP / line fields              | Unchanged | Same persistence/tool contract  |

## Risks

| Risk                                      | Likelihood | Mitigation                           |
| ----------------------------------------- | ---------- | ------------------------------------ |
| `unsupported` MCP lines invisible on form | Med        | Filterable on Payment Lines menu     |
| One2many domain/default pitfalls          | Med        | Cover defaults + filters in UI tests |

## Rollback Plan

Revert view/model helper commits and upgrade the module. No data migration.

## Dependencies

- Existing voucher/line field contract; Odoo 19 list/form domain+context patterns

## Success Criteria

- [ ] Form shows three stacked typed editable tables with correct fields
- [ ] New rows get the table’s `document_type`; type column hidden
- [ ] Mono payment-lines table gone; mixed types still allowed
- [ ] Payment Lines menu is read-only and filterable
- [ ] `document_id` visible; UI omit still OK; MCP unchanged
- [ ] `invoke test -m collection` green
