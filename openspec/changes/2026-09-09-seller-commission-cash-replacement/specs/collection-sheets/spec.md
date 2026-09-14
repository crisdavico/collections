# Delta for Collection Sheets

## ADDED Requirements

### Requirement: Confirm mints the seller commission voucher

`action_confirm` MUST mint the retained-commission instrument for each sheet it
confirms. The mint MUST run after the Confirm review gate and the Confirm cash
declaration gate have both passed, and MUST run before the `submitted → proposal` state
write, so that a refused Confirm leaves no voucher behind and the sheet is still
unfrozen when the voucher is created.

The mint MUST be a no-op when `commission_withheld` is zero or unset, and MUST be a
no-op when the sheet already carries a `seller_commission` member voucher. That
idempotency guard MUST key on the existing member voucher, not on replacement ledger
rows, because Cancel does not reverse replacements and
`Confirm → Cancel → Reinstate → Confirm` is a reachable path.

Otherwise the system MUST create exactly one `collection.voucher` with `document_type`
`seller_commission`, `amount` equal to `commission_withheld`, `seller_id` and `sheet_id`
of the sheet, a minted `document_id` matching `sc-<uuid4 hex>`, and `state`
`validated_seller`; then MUST write `validated_collections` under
`collection_audited_state` to trigger cash replacement. The mint MUST NOT `sudo()`. It
MUST post a chatter note on the sheet naming the voucher and amount.

Because the mint is system bookkeeping on an existing sheet rather than new seller work,
it MUST bypass `_assert_new_work` through a narrow documented context key. Confirm MUST
therefore stay usable on a historical sheet whose seller has since been removed from
`enabled_seller_ids`. The bypass MUST NOT widen to ORM, UI, or MCP voucher create.

`commission_withheld` is writable only while the sheet is `submitted`, and Confirm
leaves `submitted`, so the voucher `amount` and the declaration MUST agree permanently
and no reverse or adjustment path MUST exist.

#### Scenario: Confirm mints one commission voucher

- GIVEN a submitted sheet with `commission_withheld` 300, every member
  `validated_collections`, and `cash_declared_at` set
- WHEN Confirm runs
- THEN exactly one `seller_commission` voucher of amount 300 MUST persist on that sheet
- AND its `state` MUST be `validated_collections`
- AND its `document_id` MUST match `sc-<uuid4 hex>`
- AND `state` MUST become `proposal`

#### Scenario: Zero commission mints nothing

- GIVEN a submitted sheet with `commission_withheld` 0 and `cash_declared_at` set
- WHEN Confirm runs
- THEN no `seller_commission` voucher MUST persist
- AND `state` MUST become `proposal`

#### Scenario: Refused Confirm mints nothing

- GIVEN a submitted sheet with `commission_withheld` 300 and a member voucher that
  blocks the Confirm review gate
- WHEN Confirm runs
- THEN MUST raise `UserError`
- AND no `seller_commission` voucher MUST persist
- AND `state` MUST remain `submitted`

#### Scenario: Re-Confirm after Reinstate mints no second voucher

- GIVEN a sheet Confirmed with a `seller_commission`, then Cancelled, then Reinstated
- WHEN Confirm runs again
- THEN exactly one `seller_commission` voucher MUST exist on that sheet
- AND no additional `replace` ledger row MUST be created

#### Scenario: Disabled seller still allows Confirm

- GIVEN a submitted sheet with `commission_withheld` 300 whose `seller_id` is no longer
  in `enabled_seller_ids`
- WHEN Confirm runs
- THEN the `seller_commission` voucher MUST persist
- AND MUST NOT raise "Seller is not enabled for this company"

#### Scenario: Mint does not alter the cash arithmetic

- GIVEN a submitted sheet with `commission_withheld` 300 and `cash_on_hand` X
- WHEN Confirm mints and promotes the commission voucher
- THEN `cash_on_hand` MUST still equal X
- AND `cash_banked` MUST NOT include the commission amount

## MODIFIED Requirements

### Requirement: Confirm cash declaration gate

Confirm MUST refuse when the sheet's collected cash is greater than zero and
`cash_declared_at` is unset. Confirm MUST NOT change sheet or allocation `state` in that
case, and MUST NOT mint a `seller_commission` voucher. When collected cash is zero,
Confirm MUST NOT require Declare Cash. Member `validated_collections` rules in Confirm
review gate MUST still apply, and MUST be evaluated before the commission mint.
(Previously: Confirm had no mint, so the gate ordering was unobservable.)

#### Scenario: Undeclared cash blocks Confirm and the mint

- GIVEN a submitted sheet with collected cash greater than zero, unset
  `cash_declared_at`, and every member `validated_collections`
- WHEN Confirm runs
- THEN MUST raise `UserError`
- AND `state` MUST remain `submitted`
- AND no `seller_commission` voucher MUST persist
