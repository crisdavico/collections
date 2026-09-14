# Delta for Collection Vouchers

## MODIFIED Requirements

### Requirement: Document type catalog and Selection

The catalog `collection.document.type` MUST hold nine XMLID rows: `bank_transfer`,
`check`, `echeck`, `cash_deposit`, `retention_certificate`, `cash`, `unsupported`,
`seller_deposit`, and `seller_commission`. `collection.voucher.document_type` and
`collection.voucher.review.snapshot.document_type` MUST stay Selection fields sourced
from the shared `DOCUMENT_TYPE_SELECTION` tuple, and `COLLECTION_TYPE_CODES` MUST keep
following `DOCUMENT_TYPE_CODES` so catalog unions cover every Selection code. New
companies MUST start with all nine codes allowed. Upgrade MUST union the ninth code onto
every existing company and MUST keep extras. MCP write MUST still reject `unsupported`,
and MUST NOT accept `seller_commission` from any caller: only Confirm mints it.
(Previously: Eight rows, without `seller_commission`.)

#### Scenario: Ninth code present after upgrade

- GIVEN a company whose allow-list predates this change
- WHEN the module is upgraded
- THEN `seller_commission` MUST be allowed for that company
- AND every previously allowed code MUST remain allowed

#### Scenario: New company allows all nine

- GIVEN a newly created company
- WHEN its allow-list is read
- THEN all nine catalog codes MUST be present

#### Scenario: MCP callers cannot mint a commission

- GIVEN an internal MCP caller
- WHEN any write tool is called with `document_type` `seller_commission`
- THEN MUST raise `UserError`
- AND no voucher MUST persist

### Requirement: Sentinel partner for customerless vouchers

The system MUST seed two noupdate sentinel partners: XMLID
`collection.partner_seller_deposit` (name `Seller Deposit`) and
`collection.partner_seller_commission` (name `Seller Commission`), both with
`company_id` unset, reachable through `_seller_deposit_partner()` and
`_seller_commission_partner()`. Seeding MUST be idempotent. Voucher create MUST stamp
the sentinel matching `document_type` for every code in that type→sentinel map, MUST
refuse a `customer_identification`, and MUST refuse a `partner_id` that is any partner
other than that type's sentinel. Codes outside the map MUST keep requiring a real
customer `partner_id`. (Previously: One sentinel for `seller_deposit`, stamped by a
`seller_deposit`-only `_apply_seller_deposit_partner`.)

#### Scenario: Commission stamps its own sentinel

- GIVEN a `seller_commission` voucher created with no `partner_id`
- WHEN create completes
- THEN `partner_id` MUST be `collection.partner_seller_commission`
- AND MUST NOT be the `seller_deposit` sentinel

#### Scenario: Customer partner refused on a commission

- GIVEN a `seller_commission` voucher created with a real customer `partner_id`
- WHEN create runs
- THEN MUST raise `UserError`
- AND no voucher MUST persist

#### Scenario: Sentinel seeding is idempotent

- GIVEN both sentinels already exist
- WHEN the seed functions run again
- THEN no duplicate partner MUST be created

### Requirement: Confirm review gate

Confirm MUST require every member voucher to be `validated_collections`, except that
members whose `document_type` is in `CONFIRM_REVIEW_EXEMPT_TYPES` MUST be accepted at
`validated_seller` or `validated_collections`. That set MUST be exactly `cash` and
`seller_commission`: neither carries a designated proof, so Document Review can never
reach them and a gate on `validated_collections` would deadlock. `seller_deposit` MUST
stay non-exempt because its remittance slip is reviewable. (Previously: The exempt set
was `cash` alone.)

#### Scenario: Commission at validated_seller does not block Confirm

- GIVEN a submitted sheet whose only non-`validated_collections` member is a
  `seller_commission` at `validated_seller`
- WHEN Confirm runs
- THEN `state` MUST become `proposal`

#### Scenario: Deposit still blocks Confirm

- GIVEN a submitted sheet with a `seller_deposit` at `validated_seller`
- WHEN Confirm runs
- THEN MUST raise `UserError`
- AND `state` MUST remain `submitted`

### Requirement: Cash replacement trigger

A write that moves a voucher into `validated_collections` MUST run cash replacement when
that voucher's `document_type` is in `CASH_REPLACEMENT_TYPES`, which MUST be exactly
`seller_deposit` and `seller_commission`. Vouchers already at `validated_collections`
MUST NOT re-trigger. Replacement MUST be skipped when the sheet is missing or frozen.
Replacement MUST NOT run for any other code. (Previously: The trigger matched
`seller_deposit` only.)

#### Scenario: Commission promotion replaces cash

- GIVEN a submitted sheet with replaceable `cash` receipt values and a
  `seller_commission` at `validated_seller`
- WHEN it is written to `validated_collections`
- THEN cash MUST be replaced by that commission per Collection Receipts
- AND `replace` ledger rows MUST name the commission as `deposit_voucher_id`

#### Scenario: Re-write does not re-replace

- GIVEN a `seller_commission` already at `validated_collections`
- WHEN `validated_collections` is written again
- THEN no additional replacement row MUST be created
