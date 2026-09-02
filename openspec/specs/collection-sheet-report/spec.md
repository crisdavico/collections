# collection-sheet-report Specification

## Purpose

Operators MUST print a Planilla de Cobranza from `collection.sheet` as PDF and
XLSX with identical Total Cobrado, Total Aplicado, Remanente, Total Comisión,
and Diferencia.

## Requirements

### Requirement: Sheet reconciliation inputs

`collection.sheet` MUST persist `commission_percent` (Float, default 0),
`cash_on_hand`, and `commission_withheld` (Monetary). Percent MUST be
constrained 0–100 (Odoo 19 `models.Constraint`, MUST NOT `_sql_constraints`).
Closed sheets MUST refuse writes of those three fields (`UserError`, no
persist). Open sheets MAY edit them. Reopen MUST NOT reset stored values.

#### Scenario: Percent range

- GIVEN an open sheet
- WHEN `commission_percent` is written 0, 100, or outside 0–100
- THEN 0 and 100 MUST persist
- AND outside 0–100 MUST raise and MUST NOT persist

#### Scenario: Closed write guard

- GIVEN a closed sheet
- WHEN `cash_on_hand`, `commission_withheld`, or `commission_percent` is written
- THEN MUST raise `UserError`
- AND stored values MUST be unchanged

#### Scenario: Open edit then reopen keeps values

- GIVEN an open sheet with those three fields set
- WHEN Close then Reopen runs
- THEN the three values MUST remain

### Requirement: Shared report payload

`_collection_report_data()` MUST return one payload: primitives (`str` /
`float` / `int` / `bool` / `date` / `list` / `dict`) plus `sheet` and
`currency` for QWeb. Nested customer, document-row, and voucher-row dict
values MUST be primitives (XLSX MUST NOT touch the ORM). MUST include
`company`, `printed_on`, `reference`, `state_label`, `seller_name`,
`date_from`, `date_to`, `customer_count`, `voucher_count`,
`commission_percent`, `customers`, `customer_totals`, `document_blocks`,
`applied_total`, `voucher_blocks`, `collected_total`, `tendered`, `recon`,
`mismatch`. Print MUST include every `allocation_ids` and `voucher_ids` row
(draft/confirmed; pending/approved/rejected). Open-sheet prints MUST include
drafts. Customer totals MUST equal allocation sums. PDF HTML and XLSX cached
totals MUST match.

#### Scenario: Primitive nested values

- GIVEN a saved sheet with allocations and vouchers
- WHEN `_collection_report_data()` runs
- THEN listed keys MUST be present
- AND nested row dict values MUST be primitives

#### Scenario: Open sheet prints drafts

- GIVEN an open sheet with draft allocations and mixed-state vouchers
- WHEN the payload is built
- THEN every allocation and voucher MUST appear
- AND drafts MUST NOT be omitted

### Requirement: Customer codes and sort

Customer `Código` MUST come from a batched search on
`collection.connector.customer.binding` using raw
`company_id.collection_connector_id`. MUST NOT call
`_collection_active_connector()`. Unbound or no-connector companies MUST
print a blank code. Sort key MUST be `(code == "", code, partner_name)` so
coded customers group first and blanks last. Document rows MUST then sort by
`(code_sort, due_date or date.max, invoice_number or "")`. Voucher rows MUST
sort by `(code_sort, date, number)`. Both writers MUST iterate those lists
and MUST NOT re-sort.

#### Scenario: Binding code vs blank last

- GIVEN one bound partner with a code and one unbound partner
- WHEN the payload is built
- THEN the bound code MUST appear
- AND the unbound code MUST be blank and that customer MUST sort last

### Requirement: Document blocks and commission

Document blocks MUST split `allocation_ids.line_ids` by `document_kind`
(`invoice` then `quotation`). Empty blocks MUST be dropped. Per-row
commission MUST be `currency.round(applied * percent / 100.0)`. Block
`subtotal_commission` MUST be the sum of those rounded rows (MUST NOT be
`subtotal_applied × percent`). Percent 0 MUST yield zero commission.

#### Scenario: Kind split drops empty

- GIVEN invoice lines and no quotation lines
- WHEN document blocks are built
- THEN an invoice block MUST exist
- AND the quotation block MUST be absent

#### Scenario: Round per row then sum

- GIVEN two applied amounts whose per-row rounded commissions differ from
  `subtotal_applied × percent / 100`
- WHEN the invoice block is built
- THEN `subtotal_commission` MUST equal the sum of rounded row commissions
- AND MUST NOT equal `subtotal_applied × percent / 100`

#### Scenario: Zero percent

- GIVEN `commission_percent` 0 and applied lines
- WHEN document blocks are built
- THEN every row commission and every block subtotal MUST be 0

### Requirement: Voucher blocks and tendered

Voucher blocks MUST group `voucher_ids` by `document_type`. Labels MUST come
from `collection.document.type` keyed by `code` (MUST NOT use company-dependent
`_selection_document_type`). Order MUST be `bank_transfer`, `check`,
`cash_deposit`, then remaining codes alphabetically (`unsupported` last as
Otros, only when non-empty). Empty blocks MUST be dropped.
`collected_total` MUST equal voucher-block subtotals. `tendered` MUST include
`cash_on_hand` plus deposits, checks, and transfers.

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

### Requirement: Reconciliation status and mismatch

`recon` MUST set `collected`, `withheld`, `net_due`, `tendered`,
`difference`, `status`, and `status_message`. Status MUST be
`currency.compare_amounts(difference, 0.0)` → `balanced` / `in_favor` /
`outstanding`. `mismatch` MUST be set when Σ allocation `total_vouchers` ≠ Σ
printed voucher amounts (unallocated sheet vouchers).

#### Scenario: Tri-state via compare_amounts

- GIVEN difference compared to 0 as equal, greater, or less
- WHEN recon is built
- THEN `status` MUST be `balanced`, `in_favor`, or `outstanding` respectively

#### Scenario: Unallocated voucher mismatch

- GIVEN a sheet voucher with no `allocation_id`
- WHEN the payload is built
- THEN `mismatch` MUST be truthy
- AND `collected_total` MUST still include that voucher amount

### Requirement: Unsaved sheet and mixed currency

Both PDF and XLSX builders MUST call the existing saved-sheet guard. Unsaved
(NewId / non-positive id) MUST raise `UserError` and MUST NOT emit output.
Mixed allocation currencies MUST raise `UserError` (template is
single-currency).

#### Scenario: Unsaved sheet refused

- GIVEN a sheet that is not yet saved
- WHEN PDF or XLSX build runs
- THEN MUST raise `UserError`
- AND MUST NOT return a payload or file

#### Scenario: Mixed currency refused

- GIVEN two allocations on one sheet with different `currency_id`
- WHEN `_collection_report_data()` runs
- THEN MUST raise `UserError`
- AND MUST NOT return a payload

### Requirement: PDF Print menu and QWeb

The system MUST bind `ir.actions.report` `qweb-pdf` on `collection.sheet`
(`binding_type` report) so Print → Planilla de Cobranza appears on form and
list. Paperformat MUST be A4 landscape. Templates MUST use `t-out` (MUST NOT
`t-esc`) and MUST call `web.html_container` plus `web.external_layout` (PDF
membrete is company letterhead, not workbook rows 1–4). HTML render (MUST NOT
spawn wkhtmltopdf in tests) MUST contain the sheet reference, seller name,
every partner name, applied document numbers, and the recon banner.

#### Scenario: Print menu binding

- GIVEN the report action XMLID
- WHEN inspected
- THEN `report_type` MUST be `qweb-pdf`, model `collection.sheet`, binding
  report on that model, with the collection-sheet paperformat

#### Scenario: HTML contains names numbers banner

- GIVEN a saved sheet with customers, documents, and a recon status
- WHEN `_render_qweb_html` runs
- THEN HTML MUST contain the reference, seller, partner names, document
  numbers, and banner text
- AND the arch MUST reference `web.external_layout`

### Requirement: XLSX workbook and percent scale

XLSX MUST be built from the same payload. Bytes MUST start `PK` and the zip
MUST contain `xl/workbook.xml`. Worksheet MUST freeze `A6`, landscape, paper
size 9, fit-to-width 1. Aggregation cells MUST use formulas with cached SUM
values (`data_only` MUST read non-None totals equal to the payload). Odoo
`commission_percent` 0–100 MUST be written as `percent / 100.0` into a `0.0%`
cell. Banner text and fill MUST follow `recon.status`. Header **Export XLSX**
MUST be last in `<header>` before `state`. Notebook MUST remain exactly one
page (recon fields in a second inner `<group>`). `action_print_xlsx` MUST
return `ir.actions.act_url` download; MUST NOT `sudo()`.

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

#### Scenario: Header button last and one notebook page

- GIVEN the sheet form arch
- WHEN inspected
- THEN the XLSX button MUST be the last header object button before `state`
- AND the notebook MUST have exactly one page

### Requirement: Company ACL and no sudo

Payload build, HTML render, and XLSX download MUST obey company `ir.rule`.
Company-B users MUST receive `AccessError` on a company-A sheet. Report code
MUST NOT `sudo()`.

#### Scenario: Company-B AccessError

- GIVEN an internal user whose company is B and a sheet in company A
- WHEN `_collection_report_data()`, HTML render, or `action_print_xlsx` runs
- THEN MUST raise `AccessError`
- AND MUST NOT return payload, HTML, or an attachment
