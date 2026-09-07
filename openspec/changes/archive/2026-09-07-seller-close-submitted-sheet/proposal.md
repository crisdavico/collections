# Proposal: Seller Close for Collection Sheets

## Intent

Sellers never log into Odoo. Today `open` conflates seller live-sheet write access with
admin edit/Document Review. Administration Confirm freezes at `proposal` at an arbitrary
moment; the seller’s next voucher silently starts a new sheet. Add fifth state
`submitted` as the seller’s own close declaration, lock the agent out, let
administration keep working as they do on `open`.

## Scope

### In Scope

- Fifth key `submitted`; named state sets.
- Seller close, Confirm from `submitted` (PR 3 `open|submitted`), Cancel, Reinstate.
- Membership, Document Review, draft allocations, recon split, Rendida, recon
  `readonly`.
- MCP write `close_collection_sheet` (`seller_id` only) under `collection-sheets`.
- Manifest `19.0.1.42.0`; no migrate folder.

### Out of Scope

Handoff notification; Nebula agent code (document fetch-Planilla-before-close only);
`_closed_membership_user_error`; `_OUTSTANDING_INVOICE_STATES`; ACL / seller-vs-admin
groups; Confirm-unreachable-when-Document-Review-off; undo for mistaken Seller Close;
`state=submitted` list filter; allocation views whitelist/blacklist mismatch; in-flight
`expose-allocatable-customer-debt` and `document-review-editable-ocr`.

## Capabilities

### New Capabilities

None

### Modified Capabilities

- `collection-sheets`: fifth state; close/reinstate; membership/Confirm/unlink/UI;
  **ADDED** MCP write `close_collection_sheet` (`seller_id` only). `seller-lookup`
  stays read-only `get_seller_id`.
- `collection-sheet-report`: recon split; Rendida label; PDF MCP stays
  open-only.
- `collection-vouchers`: `_sheet_is_frozen` / membership unlock widens to submitted.
- `document-review`: review allowed on submitted.
- `collection-allocations`: draft legal on submitted; `DRAFT_SHEET_STATES` copy; MCP
  write stays `SELLER_SHEET_STATES` (`open`).

## Approach

Named editable-iff sets; `open` create-only. Strict TDD. Six stacked PRs to main; PR 3
transitional Confirm `open|submitted`; PR 5 makes submitted mandatory and must include
sibling `collection_receipt_proposal/tests/common.py` `_confirm()` (outside apply.roots
— delivery risk, not a blocker for this proposal).

**User impact:** seller declares the boundary; agent locked out; next voucher a new
`open` sheet; admin works `submitted` like `open`.

**MCP contract:** allocation write/lookup stay `open`; PDF `{sheet:null}` on non-open;
close 0-open → `UserError`; no `sudo()`; no nebula-agent implementation.

## Affected Areas

Sheet/voucher/allocation/report models; MCP lockout; views; tests; docs. New:
`tools/collection_sheet_close.py`. Odoo stays in `collection/` except sibling `_confirm()`.

## Risks

- Sibling `_confirm()` outside apply.roots (High): consent; land with PR 5.
- Confirm sites 83/14 files, not 163/12 (Med): ripgrep at apply.
- In-flight Review OCR (Med): coordinate.
- Confirm unreachable if Review off (Med): out of scope.
- No seller-vs-admin ACL (Low): future writes use `SELLER_SHEET_STATES`.

## Rollback Plan

Revert stacked PRs newest-first. No SQL remap; `open` rows stay.
Drop the close-tool import.

## Dependencies

PR 5 sibling `_confirm()` needs edit-authority consent.

## Success Criteria

- [ ] Seller Close → `submitted`; MCP write refused; next allocation on a new `open` sheet
- [ ] Admin membership, Document Review, draft allocations, `commission_percent` on
      `submitted`; seller declarations frozen; Confirm only from `submitted`
- [ ] MCP close is `seller_id`-only, no sudo; PDF stays open-only;
      `invoke test -m collection --mode=update` green; sibling suite from PR 5
