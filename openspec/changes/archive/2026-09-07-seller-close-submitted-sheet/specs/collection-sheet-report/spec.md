# Delta for collection-sheet-report

## ADDED Requirements

### Requirement: Submitted Spanish report label

When sheet `state` is `submitted`, PDF and XLSX `state_label` MUST be `Rendida`. Other
existing Spanish state labels MUST remain unchanged.

#### Scenario: Submitted prints Rendida

- GIVEN a saved submitted sheet
- WHEN `_collection_report_data()` or bound PDF/XLSX build runs
- THEN `state_label` MUST be `Rendida`

## MODIFIED Requirements

### Requirement: Sheet reconciliation inputs

`collection.sheet` MUST persist `commission_percent` (Float, default 0), `cash_on_hand`,
and `commission_withheld` (Monetary). Percent MUST be constrained 0–100 (Odoo 19
`models.Constraint`, MUST NOT `_sql_constraints`). Seller-declared `cash_on_hand` and
`commission_withheld` MUST be writable only while `state` is `open`.
`commission_percent` MUST be writable while `state` is not `closed` or `cancelled`.
Closed and cancelled sheets MUST refuse writes of those three fields (`UserError`, no
persist). A single audited write that sets `state` to `submitted` together with the two
seller declarations MUST be accepted because the guard MUST evaluate the pre-write
`open` state. After `submitted`, further writes of the two seller declarations MUST be
refused while `commission_percent` MAY still persist. Reinstate from Cancelled MUST NOT
reset stored values. Form widgets for the three fields MUST be readonly when the
corresponding write would be refused. (Previously: All three fields editable on `open`
and `proposal`; Closed and Cancelled refused all three; Open from Cancelled kept
values.)

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
- WHEN Seller Close, then Confirm, then Close or Cancel, then Reinstate from Cancelled
  runs
- THEN the three values MUST remain

#### Scenario: Combined close write persists declarations

- GIVEN an open sheet
- WHEN Seller Close writes `state` `submitted` together with `cash_on_hand` and
  `commission_withheld`
- THEN `state` MUST be `submitted`
- AND both declaration amounts MUST persist

#### Scenario: Submitted freezes seller declarations only

- GIVEN a submitted sheet
- WHEN `cash_on_hand` or `commission_withheld` is written
- THEN MUST raise `UserError` and stored values MUST be unchanged
- AND a lawful `commission_percent` write MUST persist

#### Scenario: Proposal recon rate remains editable

- GIVEN a proposal sheet
- WHEN `commission_percent` is written lawfully
- THEN the write MUST persist
- AND writes of `cash_on_hand` or `commission_withheld` MUST be refused

### Requirement: PDF and XLSX available in all sheet states

Bound Print → Planilla de Cobranza (`qweb-pdf`) and header Export XLSX MUST remain
available for saved sheets in `open`, `submitted`, `proposal`, `closed`, and
`cancelled`. Builders MUST NOT refuse solely because of sheet `state`. Report content
rules MUST stay unchanged. Unsaved and mixed-currency guards MUST still apply.
(Previously: Available in the four states `open`, `proposal`, `closed`, `cancelled`.)

#### Scenario: PDF in all five states

- GIVEN a saved sheet in `open`, `submitted`, `proposal`, `closed`, or `cancelled`
- WHEN bound PDF Print runs
- THEN a payload MUST be produced
- AND MUST NOT raise because of sheet `state`

#### Scenario: XLSX in all five states

- GIVEN a saved sheet in `open`, `submitted`, `proposal`, `closed`, or `cancelled`
- WHEN Export XLSX runs
- THEN `action_print_xlsx` MUST return a download
- AND MUST NOT raise because of sheet `state`

#### Scenario: Unsaved still refused

- GIVEN a sheet that is not yet saved
- WHEN PDF or XLSX build runs
- THEN MUST raise `UserError` and MUST NOT emit output

### Requirement: Read-only MCP tool get_collection_sheet_pdf

The system MUST expose `get_collection_sheet_pdf` via `@mcp_tool` on `muk_mcp.mixin`
(`category=read`, `registry=mcp`), method-discovered; MUST NOT add a DB tool record.
Calls MUST use the authenticated user and MUST NOT `sudo()`. Input MUST require exactly
one property, integer `seller_id`, and MUST NOT accept `model`, `domain`, `fields`,
`context`, `order`, a `sheet_id`, or a report reference. The tool MUST resolve the
seller's own `open` sheet on `env.company` through
`collection.sheet._open_sheets_for_seller` and MUST NOT print `submitted`, `proposal`,
`closed`, or `cancelled` sheets. It MUST render the bound
`collection.action_report_collection_sheet` and return
`{sheet:{id,name,state,seller_id,date_from,date_to,voucher_count}, filename, mimetype, content_base64}`
where `content_base64` is the standard-base64 report body and `filename` is a slug
ending `.pdf` carrying the sheet reference with `/` replaced. The tool MUST NOT create
an `ir.attachment`, MUST NOT write any record, MUST NOT require an active
`collection.connector` or seller binding, and MUST NOT expose the XLSX. (Previously:
Non-open list omitted `submitted`.)

#### Scenario: Open sheet returns base64 PDF

- GIVEN an internal caller and an internal seller with exactly one `open` sheet on the
  caller's company
- WHEN `get_collection_sheet_pdf` runs with that `seller_id`
- THEN the response MUST be exactly `sheet`, `filename`, `mimetype`, `content_base64`
- AND `mimetype` MUST be `application/pdf` and `content_base64` MUST decode to the
  rendered report bytes
- AND the rendered record set MUST be that open sheet only
- AND no record MUST be created or written

#### Scenario: No open sheet returns null

- GIVEN an internal seller with no sheet, or only `submitted` / `proposal` / `closed` /
  `cancelled` sheets
- WHEN `get_collection_sheet_pdf` runs with that `seller_id`
- THEN the response MUST be exactly `{ "sheet": null }`
- AND the report MUST NOT be rendered

#### Scenario: More than one open sheet fails closed

- GIVEN corrupted data where a seller has two `open` sheets on the caller's company
- WHEN `get_collection_sheet_pdf` runs
- THEN MUST raise `UserError` `This seller has more than one open collection sheet.`
- AND MUST NOT return a PDF

#### Scenario: Caller authorization

- GIVEN a portal or public caller
- WHEN `get_collection_sheet_pdf` runs with any `seller_id`
- THEN MUST raise `AccessError` and MUST NOT return a PDF
- AND an invalid, portal, or unknown `seller_id` from an internal caller MUST raise
  `UserError`

#### Scenario: Company scoping

- GIVEN an internal caller restricted to company A and a seller whose only `open` sheet
  belongs to company B
- WHEN `get_collection_sheet_pdf` runs with that `seller_id`
- THEN the response MUST be `{ "sheet": null }`
- AND the company-B report MUST NOT be rendered
