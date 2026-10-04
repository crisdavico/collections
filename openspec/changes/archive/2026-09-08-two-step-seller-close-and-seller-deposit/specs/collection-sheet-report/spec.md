# Delta for Collection Sheet Report

## ADDED Requirements

### Requirement: Remittance cash_banked

`cash_banked` MUST equal the sum of member `seller_deposit` voucher amounts. It MUST NOT
sum `cash_deposit`. It MUST NOT be derived from the cash-replacement ledger. Excess
`seller_deposit` beyond replaceable cash MUST be allowed and MUST surface through recon
tendered totals. A submitted sheet with zero allocations MUST still report `cash_banked`
from deposit vouchers.

#### Scenario: cash_banked sums seller_deposit only

- GIVEN a sheet with `seller_deposit` 80 and `cash_deposit` 20
- WHEN report payload is built
- THEN `cash_banked` MUST equal 80
- AND MUST NOT include 20

#### Scenario: Excess deposit still banks

- GIVEN replaceable cash 50 and `seller_deposit` 80
- WHEN report payload is built
- THEN `cash_banked` MUST equal 80

#### Scenario: No allocations still banks from vouchers

- GIVEN a submitted sheet with a `seller_deposit` member and zero allocations
- WHEN report payload is built
- THEN `cash_banked` MUST equal that deposit amount
- AND MUST NOT be zero merely because the ledger is empty

## MODIFIED Requirements

### Requirement: Sheet reconciliation inputs

`collection.sheet` MUST persist `commission_percent` (Float, default 0), `cash_on_hand`,
and `commission_withheld` (Monetary). Percent MUST be constrained 0–100 (Odoo 19
`models.Constraint`, MUST NOT `_sql_constraints`). The stored field name `cash_on_hand`
MUST remain `cash_on_hand` (the form string MAY read Cash to Administration).
Seller-declared `cash_on_hand` and `commission_withheld` MUST be writable only while
`state` is `submitted`. `commission_percent` MUST be writable while `state` is not
`closed` or `cancelled`. Closed and cancelled sheets MUST refuse writes of those three
fields (`UserError`, no persist). Seller Close MUST NOT persist the two seller
declarations. After `open`, writes of the two seller declarations MUST be refused while
`commission_percent` MAY still persist. Reinstate from Cancelled MUST NOT reset stored
values. Form widgets for the three fields MUST be readonly when the corresponding write
would be refused. (Previously: Seller declarations writable only while `open`; a
combined Seller Close write persisted them because the guard evaluated the pre-write
`open` state; after `submitted`, further declaration writes were refused.)

#### Scenario: Percent range

- GIVEN an open sheet
- WHEN `commission_percent` is written 0, 100, or outside 0–100
- THEN 0 and 100 MUST persist
- AND outside 0–100 MUST raise and MUST NOT persist

#### Scenario: Closed write guard

- GIVEN a closed or cancelled sheet
- WHEN `cash_on_hand`, `commission_withheld`, or `commission_percent` is written
- THEN MUST raise `UserError`
- AND stored values MUST be unchanged

#### Scenario: Open edit then cancel keeps values

- GIVEN a submitted sheet with those three fields set
- WHEN Confirm, then Close or Cancel, then Reinstate from Cancelled runs
- THEN the three values MUST remain

#### Scenario: Seller Close does not persist declarations

- GIVEN an open sheet
- WHEN Seller Close writes `state` `submitted` without declaration amounts
- THEN `state` MUST be `submitted`
- AND `cash_on_hand` and `commission_withheld` MUST remain unchanged by that write

#### Scenario: Submitted accepts seller declarations

- GIVEN a submitted sheet
- WHEN `cash_on_hand` or `commission_withheld` is written lawfully
- THEN those amounts MUST persist
- AND a lawful `commission_percent` write MUST persist

#### Scenario: Open freezes seller declarations

- GIVEN an open sheet
- WHEN `cash_on_hand` or `commission_withheld` is written
- THEN MUST raise `UserError` and stored values MUST be unchanged
- AND a lawful `commission_percent` write MUST persist

#### Scenario: Proposal recon rate remains editable

- GIVEN a proposal sheet
- WHEN `commission_percent` is written lawfully
- THEN the write MUST persist
- AND writes of `cash_on_hand` or `commission_withheld` MUST be refused

### Requirement: Voucher blocks and tendered

Voucher blocks that feed `collected_total` MUST group member `voucher_ids` by
`document_type` and MUST exclude `seller_deposit`. Labels MUST come from
`collection.document.type` keyed by `code` (MUST NOT use company-dependent
`_selection_document_type`). Order MUST be `bank_transfer`, `check`, `cash_deposit`,
then remaining non-remittance codes alphabetically (`unsupported` last as Otros, only
when non-empty). Empty blocks MUST be dropped. `collected_total` MUST equal those
voucher-block subtotals and MUST NOT include `seller_deposit`. `tendered` MUST include
`cash_on_hand` plus `cash_deposit`, `check`, `bank_transfer`, `echeck`,
`retention_certificate`, and `seller_deposit` (`cash_banked`). Recon algebra MUST remain
`net_due = collected − withheld` and `difference = tendered − net_due`. Every existing
`recon` key MUST remain. (Previously: Every catalog code including remittance fed
`collected_total`; `tendered` included only `cash_on_hand` plus deposits, checks, and
transfers — no echeck, retention, or `seller_deposit`.)

#### Scenario: Catalog order and empty drop

- GIVEN vouchers of types `check` and `unsupported` only
- WHEN voucher blocks are built
- THEN order MUST be check then unsupported
- AND transfer and cash-deposit blocks MUST be absent

#### Scenario: Tendered includes cash on hand

- GIVEN `cash_on_hand` > 0 and typed vouchers
- WHEN `tendered` is built
- THEN `tendered.cash` MUST equal `cash_on_hand`
- AND `tendered.total` MUST include that cash

#### Scenario: Remittance excluded from collected

- GIVEN a sheet with `seller_deposit` 80 and a `cash` voucher 50
- WHEN voucher blocks and `collected_total` are built
- THEN `collected_total` MUST equal 50
- AND MUST NOT include 80

#### Scenario: Tendered includes remittance echeck and retention

- GIVEN `seller_deposit`, `echeck`, and `retention_certificate` members
- WHEN `tendered` is built
- THEN `tendered.total` MUST include those three amounts
- AND PDF and XLSX MUST show the same tendered buckets

### Requirement: Reconciliation status and mismatch

`recon` MUST set `collected`, `withheld`, `net_due`, `tendered`, `difference`, `status`,
and `status_message`. Status MUST be `currency.compare_amounts(difference, 0.0)` →
`balanced` / `in_favor` / `outstanding`. `mismatch` MUST be set when Σ allocation
`total_vouchers` ≠ Σ printed collected voucher amounts (unallocated non-remittance sheet
vouchers). `seller_deposit` MUST NOT set `mismatch` and MUST NOT inflate
`collected_total`. (Previously: Any unallocated sheet voucher, including a future
remittance, set `mismatch` and was included in `collected_total`.)

#### Scenario: Tri-state via compare_amounts

- GIVEN difference compared to 0 as equal, greater, or less
- WHEN recon is built
- THEN `status` MUST be `balanced`, `in_favor`, or `outstanding` respectively

#### Scenario: Unallocated voucher mismatch

- GIVEN a non-remittance sheet voucher with no `allocation_id`
- WHEN the payload is built
- THEN `mismatch` MUST be truthy
- AND `collected_total` MUST still include that voucher amount

#### Scenario: Unallocated remittance does not mismatch

- GIVEN a `seller_deposit` sheet voucher with no `allocation_id` and otherwise matching
  allocation totals
- WHEN the payload is built
- THEN `mismatch` MUST be false
- AND `collected_total` MUST NOT include that deposit amount

### Requirement: Read-only MCP tool get_collection_sheet_pdf

The system MUST expose `get_collection_sheet_pdf` via `@mcp_tool` on `muk_mcp.mixin`
(`category=read`, `registry=mcp`), method-discovered; MUST NOT add a DB tool record.
Calls MUST use the authenticated user and MUST NOT `sudo()`. Input MUST require exactly
one property, integer `seller_id`, and MUST NOT accept `model`, `domain`, `fields`,
`context`, `order`, a `sheet_id`, or a report reference. At this call site only, the
tool MUST resolve the seller's own `open` sheet on `env.company` through
`collection.sheet._open_sheets_for_seller`; when that helper returns none, it MUST
resolve the seller's single `submitted` sheet. It MUST NOT widen
`_open_sheets_for_seller`. It MUST NOT print `proposal`, `closed`, or `cancelled`
sheets. When both an `open` and a `submitted` sheet exist, it MUST print the `open`
sheet. It MUST render the bound `collection.action_report_collection_sheet` and return
`{sheet:{id,name,state,seller_id,date_from,date_to,voucher_count}, filename, mimetype, content_base64}`
where `content_base64` is the standard-base64 report body and `filename` is a slug
ending `.pdf` carrying the sheet reference with `/` replaced. The tool MUST NOT create
an `ir.attachment`, MUST NOT write any record, MUST NOT require an active
`collection.connector` or seller binding, and MUST NOT expose the XLSX. (Previously:
Resolved only `open` via `_open_sheets_for_seller` and returned `{sheet: null}` when
only `submitted` existed.)

#### Scenario: Open sheet returns base64 PDF

- GIVEN an internal caller and an internal seller with exactly one `open` sheet on the
  caller's company
- WHEN `get_collection_sheet_pdf` runs with that `seller_id`
- THEN the response MUST be exactly `sheet`, `filename`, `mimetype`, `content_base64`
- AND `mimetype` MUST be `application/pdf` and `content_base64` MUST decode to the
  rendered report bytes
- AND the rendered record set MUST be that open sheet only
- AND no record MUST be created or written

#### Scenario: Submitted sheet returns base64 PDF

- GIVEN an internal caller and an internal seller with zero `open` sheets and exactly
  one `submitted` sheet on the caller's company
- WHEN `get_collection_sheet_pdf` runs with that `seller_id`
- THEN the response MUST include that submitted `sheet` and `content_base64`
- AND the rendered record set MUST be that submitted sheet only

#### Scenario: Open preferred over submitted

- GIVEN an internal seller with one `open` sheet and one `submitted` sheet on the
  caller's company
- WHEN `get_collection_sheet_pdf` runs
- THEN the rendered record set MUST be the open sheet only

#### Scenario: No printable sheet returns null

- GIVEN an internal seller with no `open` or `submitted` sheet (none, or only `proposal`
  / `closed` / `cancelled`)
- WHEN `get_collection_sheet_pdf` runs with that `seller_id`
- THEN the response MUST be exactly `{ "sheet": null }`
- AND the report MUST NOT be rendered

#### Scenario: More than one open sheet fails closed

- GIVEN corrupted data where a seller has two `open` sheets on the caller's company
- WHEN `get_collection_sheet_pdf` runs
- THEN MUST raise `UserError` `This seller has more than one open collection sheet.`
- AND MUST NOT return a PDF

#### Scenario: More than one submitted sheet fails closed

- GIVEN zero `open` sheets and two `submitted` sheets on the caller's company
- WHEN `get_collection_sheet_pdf` runs
- THEN MUST raise `UserError`
- AND MUST NOT return a PDF

#### Scenario: Caller authorization

- GIVEN a portal or public caller
- WHEN `get_collection_sheet_pdf` runs with any `seller_id`
- THEN MUST raise `AccessError` and MUST NOT return a PDF
- AND an invalid, portal, or unknown `seller_id` from an internal caller MUST raise
  `UserError`

#### Scenario: Company scoping

- GIVEN an internal caller restricted to company A and a seller whose only `open` or
  `submitted` sheet belongs to company B
- WHEN `get_collection_sheet_pdf` runs with that `seller_id`
- THEN the response MUST be `{ "sheet": null }`
- AND the company-B report MUST NOT be rendered
