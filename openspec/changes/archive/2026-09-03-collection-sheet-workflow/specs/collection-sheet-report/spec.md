# Delta for Collection Sheet Report

## ADDED Requirements

### Requirement: PDF and XLSX available in all sheet states

Bound Print → Planilla de Cobranza (`qweb-pdf`) and header Export XLSX MUST remain
available for saved sheets in `open`, `proposal`, `closed`, and `cancelled`. Builders
MUST NOT refuse solely because of sheet `state`. Report content rules MUST stay
unchanged. Unsaved and mixed-currency guards MUST still apply.

#### Scenario: PDF in all four states

- GIVEN a saved sheet in `open`, `proposal`, `closed`, or `cancelled`
- WHEN bound PDF Print runs
- THEN a payload MUST be produced
- AND MUST NOT raise because of sheet `state`

#### Scenario: XLSX in all four states

- GIVEN a saved sheet in `open`, `proposal`, `closed`, or `cancelled`
- WHEN Export XLSX runs
- THEN `action_print_xlsx` MUST return a download
- AND MUST NOT raise because of sheet `state`

#### Scenario: Unsaved still refused

- GIVEN a sheet that is not yet saved
- WHEN PDF or XLSX build runs
- THEN MUST raise `UserError` and MUST NOT emit output

## MODIFIED Requirements

### Requirement: Sheet reconciliation inputs

`collection.sheet` MUST persist `commission_percent` (Float, default 0), `cash_on_hand`,
and `commission_withheld` (Monetary). Percent MUST be constrained 0–100 (Odoo 19
`models.Constraint`, MUST NOT `_sql_constraints`). Closed and cancelled sheets MUST
refuse writes of those three fields (`UserError`, no persist). Open and proposal sheets
MAY edit them. Open from Cancelled MUST NOT reset stored values.
(Previously: Closed sheets refused writes; open sheets MAY edit; Reopen MUST NOT reset.)

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

- GIVEN an open sheet with those three fields set
- WHEN Confirm, then Close or Cancel, then Open from Cancelled runs
- THEN the three values MUST remain

#### Scenario: Proposal recon remains editable

- GIVEN a proposal sheet
- WHEN `commission_percent`, `cash_on_hand`, or `commission_withheld` is written lawfully
- THEN the write MUST persist

### Requirement: XLSX workbook and percent scale

XLSX MUST be built from the same payload. Bytes MUST start `PK` and the zip MUST contain
`xl/workbook.xml`. Worksheet MUST freeze `A6`, landscape, paper size 9, fit-to-width 1.
Aggregation cells MUST use formulas with cached SUM values (`data_only` MUST read
non-None totals equal to the payload). Odoo `commission_percent` 0–100 MUST be written
as `percent / 100.0` into a `0.0%` cell. Banner text and fill MUST follow `recon.status`.
Header **Export XLSX** MUST be last in `<header>` before `state`. Notebook MUST be the
three pages specified in collection-sheets (recon fields remain on the sheet form).
`action_print_xlsx` MUST return `ir.actions.act_url` download; MUST NOT `sudo()`.
(Previously: Notebook MUST remain exactly one page with recon in a second inner group.)

#### Scenario: Zip freeze and cached SUM

- GIVEN a saved sheet payload
- WHEN XLSX is rendered
- THEN bytes MUST start `PK` and contain `xl/workbook.xml`
- AND freeze MUST be `A6` and cached SUM cells MUST equal payload totals
  (MUST NOT be `None`)

#### Scenario: Percent scale 0–100 to 0.0%

- GIVEN `commission_percent` 4.5
- WHEN the XLSX percent cell is read
- THEN the stored value MUST be 0.045 with `0.0%` format

#### Scenario: Header button last and three notebook pages

- GIVEN the sheet form arch
- WHEN inspected
- THEN the XLSX button MUST be the last header object button before `state`
- AND the notebook MUST have Allocations, Vouchers, and Debt pages
