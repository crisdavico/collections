# Delta for Collection Sheet Report

## MODIFIED Requirements

### Requirement: Voucher blocks and tendered

Voucher blocks that feed `collected_total` MUST group member `voucher_ids` by
`document_type` and MUST exclude both `seller_deposit` and `seller_commission`. Labels
MUST come from `collection.document.type` keyed by `code` (MUST NOT use
company-dependent `_selection_document_type`). Order MUST be `bank_transfer`, `check`,
`cash_deposit`, then remaining codes alphabetically (`unsupported` last as Otros, only
when non-empty). Empty blocks MUST be dropped. `collected_total` MUST equal those
voucher-block subtotals and MUST NOT include `seller_deposit` or `seller_commission`.

`tendered` MUST include `cash_on_hand` plus `cash_deposit`, `check`, `bank_transfer`,
`echeck`, `retention_certificate`, and `seller_deposit` (`cash_banked`). `tendered` MUST
NOT include `seller_commission`, and that exclusion MUST be explicit rather than an
accident of the type dispatch falling through.

Recon algebra MUST remain `net_due = collected − withheld` and
`difference = tendered − net_due`. Every existing `recon` key MUST remain. Because the
commission amount is excluded from both `collected_total` and `tendered` while
`commission_withheld` still carries it, `difference` MUST remain `−unsupported`: minting
a `seller_commission` voucher MUST NOT change any `recon` value. Counting the commission
in either total would deduct it twice and drive `cash_on_hand` negative by exactly the
commission amount. (Previously: `seller_deposit` was the only excluded code, and
`seller_commission` did not exist.)

#### Scenario: Commission excluded from collected and tendered

- GIVEN a sheet with a `cash` voucher 500, `commission_withheld` 300, and a minted
  `seller_commission` 300
- WHEN the report payload is built
- THEN `collected_total` MUST NOT include the 300
- AND `tendered.total` MUST NOT include the 300
- AND no voucher block of code `seller_commission` MUST be present

#### Scenario: Recon unchanged by the mint

- GIVEN a submitted sheet whose report `recon` is R
- WHEN Confirm mints and promotes the `seller_commission` voucher
- THEN every key of `recon` MUST still equal its value in R
- AND `difference` MUST remain `−unsupported`

### Requirement: Remittance cash_banked

`cash_banked` MUST equal the sum of member `seller_deposit` voucher amounts. It MUST NOT
sum `cash_deposit` and MUST NOT sum `seller_commission`. It MUST NOT be derived from the
cash-replacement ledger. `cash_on_hand` MUST stay
`cash_collected − cash_banked − commission_withheld`; the commission MUST be deducted
through `commission_withheld` only, never additionally through a voucher total. Excess
`seller_deposit` beyond replaceable cash MUST be allowed and MUST surface through recon
tendered totals. A submitted sheet with zero allocations MUST still report `cash_banked`
from deposit vouchers. (Previously: `seller_commission` did not exist, so the exclusion
was unstated.)

#### Scenario: cash_banked excludes the commission

- GIVEN a sheet with `seller_deposit` 80, `cash_deposit` 20, and `seller_commission` 30
- WHEN the report payload is built
- THEN `cash_banked` MUST equal 80

## ADDED Requirements

### Requirement: Residual cash is reported, not enforced

The sheet MUST expose a computed non-stored `residual_cash_value_total` equal to the sum
of `collection.receipt.value.amount` on the sheet's receipts whose voucher
`document_type` is `cash`. It represents cash still recorded as a claim on the seller's
pocket after every remittance and commission instrument has been applied.

The sheet form MUST surface a warning when `residual_cash_value_total` is non-zero and
the sheet `state` is not `open` or `submitted`. It MUST stay silent in `open` and
`submitted`, because the commission instrument is minted only at Confirm and the
instrument ledger therefore lags `commission_withheld` legitimately throughout the
seller's declaration phase.

Residual cash MUST NOT block Confirm, Close, or any other transition. It MUST NOT feed
`collected_total`, `tendered`, `cash_on_hand`, or `recon`.

#### Scenario: Residual surfaces after Confirm

- GIVEN a Confirmed sheet whose receipts still carry `cash` values totalling 40
- WHEN the sheet form is read
- THEN `residual_cash_value_total` MUST equal 40
- AND the warning MUST be visible

#### Scenario: Silent while submitted

- GIVEN a submitted sheet with `cash` receipt values and `commission_withheld` set
- WHEN the sheet form is read
- THEN the warning MUST NOT be visible

#### Scenario: Residual never blocks

- GIVEN a Confirmed sheet with non-zero `residual_cash_value_total`
- WHEN Close runs
- THEN `state` MUST become `closed`

#### Scenario: Residual is outside the recon algebra

- GIVEN a sheet with non-zero `residual_cash_value_total`
- WHEN the report payload is built
- THEN `recon` MUST NOT reference it
- AND `tendered.total` MUST NOT change
