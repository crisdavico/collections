# collection-sheet-report Specification

## Purpose

Operators MUST print a Planilla de Cobranza from `collection.sheet` as PDF and XLSX with
identical Total Cobrado, Total Aplicado, Remanente, Total Comisión, and Diferencia.

## Requirements

### Requirement: Sheet reconciliation inputs

`collection.sheet` MUST persist `commission_percent` (Float, default 0) and
`commission_withheld` (Monetary). Percent MUST be constrained 0–100 (Odoo 19
`models.Constraint`, MUST NOT `_sql_constraints`). `cash_on_hand` (Monetary, form string
Cash to Administration) MUST be a **stored computed** field equal to
`cash_collected − cash_banked − commission_withheld` — the sum of `cash` voucher amounts
on the sheet minus the sum of `seller_deposit` voucher amounts minus the withheld
commission — recomputed whenever a member voucher's `document_type` or `amount` changes,
a voucher joins or leaves the sheet, or `commission_withheld` changes. It MAY be
negative when remittances plus withheld commission exceed the collected cash.
`cash_on_hand` MUST remain the field name and MUST be `store=True` so it stays
searchable and groupable. Passing `cash_on_hand` to `create` or `write` MUST raise
`UserError` in every state, including `submitted`. Seller-declared `commission_withheld`
MUST be writable only while `state` is `submitted`. `commission_percent` MUST be
writable while `state` is not `closed` or `cancelled`. Closed and cancelled sheets MUST
refuse writes of the two writable fields (`UserError`, no persist). Seller Close MUST
NOT persist the seller declaration. After `open`, writes of `commission_withheld` MUST
be refused while `commission_percent` MAY still persist. Reinstate from Cancelled MUST
NOT reset stored values. The `cash_on_hand` form widget MUST be readonly in every state;
the other two MUST be readonly when the corresponding write would be refused.
(Previously: `cash_on_hand` was a seller-declared Monetary written by Declare Cash and
writable while `submitted`.)

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

#### Scenario: cash_on_hand is derived from the sheet vouchers

- GIVEN a sheet carrying `cash` vouchers, `seller_deposit` vouchers, and a
  `commission_withheld` amount
- WHEN any of those three change
- THEN `cash_on_hand` MUST equal cash total − seller_deposit total − withheld
- AND vouchers of any other `document_type` MUST NOT move it

#### Scenario: cash_on_hand write is always refused

- GIVEN a sheet in any state
- WHEN `cash_on_hand` is passed to `create` or `write`
- THEN MUST raise `UserError` and the derived value MUST be unchanged

#### Scenario: Open edit then cancel keeps values

- GIVEN a submitted sheet with those three fields set
- WHEN Confirm, then Close or Cancel, then Reinstate from Cancelled runs
- THEN the three values MUST remain

#### Scenario: Seller Close does not persist declarations

- GIVEN an open sheet
- WHEN Seller Close writes `state` `submitted` without declaration amounts
- THEN `state` MUST be `submitted`
- AND `commission_withheld` MUST remain unchanged by that write

#### Scenario: Submitted accepts seller declarations

- GIVEN a submitted sheet
- WHEN `commission_withheld` is written lawfully
- THEN that amount MUST persist and `cash_on_hand` MUST follow by compute
- AND a lawful `commission_percent` write MUST persist

#### Scenario: Open freezes seller declarations

- GIVEN an open sheet
- WHEN `commission_withheld` is written
- THEN MUST raise `UserError` and stored values MUST be unchanged
- AND a lawful `commission_percent` write MUST persist

#### Scenario: Proposal recon rate remains editable

- GIVEN a proposal sheet
- WHEN `commission_percent` is written lawfully
- THEN the write MUST persist
- AND writes of `commission_withheld` MUST be refused

### Requirement: Shared report payload

`_collection_report_data()` MUST return one payload: primitives (`str` / `float` / `int`
/ `bool` / `date` / `list` / `dict`) plus `sheet` and `currency` for QWeb. Nested
customer, document-row, and voucher-row dict values MUST be primitives (XLSX MUST NOT
touch the ORM). MUST include `company`, `printed_on`, `reference`, `state_label`,
`seller_name`, `currency_name`, `date_from`, `date_to`, `customer_count`,
`voucher_count`, `commission_percent`, `customers`, `customer_totals`,
`document_blocks`, `applied_total`, `voucher_blocks`, `collected_total`, `tendered`,
`recon`, `mismatch`, `allocated_collected` (Σ allocation `total_vouchers`, the other
side of the mismatch). Print MUST include every `allocation_ids` and `voucher_ids` row
(draft/confirmed; draft/validated_seller/validated_collections). Open-sheet prints MUST
include drafts. Customer totals MUST equal allocation sums. PDF HTML and XLSX cached
totals MUST match. Report copy MUST be Spanish Argentina: sheet state labels,
voucher-block titles (`Transferencia bancaria` / `Cheque` / `Depósito en efectivo` /
`Otros`), recon banner, and check type (`Común` / `Diferido`). Document rows MUST
include `invoice_balance`. Customer rows MUST include `debt` (`allocation.total_debt`,
printed as Saldo Total before Cobrado). `customer_totals` MUST include `debt`. Voucher
`number` MUST be `voucher_number` for transfers/deposits and `check_number` (or blank)
for checks — MUST NOT be the COL sequence name. Check rows MUST include `check_bank`,
`check_type`, and `check_payment_date`. (Previously: Print-includes voucher keys were
pending/approved/rejected. Clientes omitted Saldo Total so Remanente looked like Cobrado
− Aplicado.)

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
`collection.connector.customer.binding` using raw `company_id.collection_connector_id`.
MUST NOT call `_collection_active_connector()`. Unbound or no-connector companies MUST
print a blank code. Sort key MUST be `(code == "", code, partner_name)` so coded
customers group first and blanks last. Document rows MUST then sort by
`(code_sort, due_date or date.max, invoice_number or "")`. Voucher rows MUST sort by
`(code_sort, date, number)`. Both writers MUST iterate those lists and MUST NOT re-sort.

#### Scenario: Binding code vs blank last

- GIVEN one bound partner with a code and one unbound partner
- WHEN the payload is built
- THEN the bound code MUST appear
- AND the unbound code MUST be blank and that customer MUST sort last

### Requirement: Document blocks and commission

Document blocks MUST split `allocation_ids.line_ids` by `document_kind` (`invoice` then
`quotation`). Empty blocks MUST be dropped. Per-row commission MUST be
`currency.round(applied * percent / 100.0)`. Block `subtotal_commission` MUST be the sum
of those rounded rows (MUST NOT be `subtotal_applied × percent`). Percent 0 MUST yield
zero commission.

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

Voucher blocks that feed `collected_total` MUST group member `voucher_ids` by
`document_type` and MUST exclude both `seller_deposit` and `seller_commission`. Labels
MUST come from `collection.document.type` keyed by `code` (MUST NOT use
company-dependent `_selection_document_type`). Order MUST be `bank_transfer`, `check`,
`cash_deposit`, then remaining codes alphabetically (only when non-empty). Empty
blocks MUST be dropped. `collected_total` MUST equal those
voucher-block subtotals and MUST NOT include `seller_deposit` or `seller_commission`.

`tendered` MUST include `cash_on_hand` plus `cash_deposit`, `check`, `bank_transfer`,
`echeck`, `retention_certificate`, and `seller_deposit` (`cash_banked`). `tendered` MUST
NOT include `seller_commission`, and that exclusion MUST be explicit rather than an
accident of the type dispatch falling through.

Recon algebra MUST remain `net_due = collected − withheld` and
`difference = tendered − net_due`. Every existing `recon` key MUST remain. Because
`cash_on_hand` is now derived as the remainder and every collected type is tendered,
`difference` MUST be 0: the banner balances by construction and both `in_favor` and
`outstanding` are unreachable from real sheet data. Both branches MUST stay in
`_collection_report_recon` and MUST still map a non-zero `difference`. Because the
commission amount is excluded from both `collected_total` and `tendered` while
`commission_withheld` still carries it, `difference` MUST remain unchanged: minting
a `seller_commission` voucher MUST NOT change any `recon` value. Counting the commission
in either total would deduct it twice and drive `cash_on_hand` negative by exactly the
commission amount. (Previously: `seller_deposit` was the only excluded code, and
`seller_commission` did not exist. Before that: Every catalog code including remittance
fed `collected_total`; `tendered` included only `cash_on_hand` plus deposits, checks,
and transfers — no echeck, retention, or `seller_deposit`.)

#### Scenario: Catalog order and empty drop

- GIVEN vouchers of types `check` and `cash` only
- WHEN voucher blocks are built
- THEN order MUST be check then cash
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
- THEN `tendered.seller_deposits`, `tendered.echecks`, and `tendered.retentions` MUST
  carry those amounts and `tendered.total` MUST be their sum plus `tendered.cash`
- AND a remittance MUST net out of `tendered.total`, because it raises
  `tendered.seller_deposits` and lowers the derived `cash_on_hand` by the same amount
- AND PDF and XLSX MUST show the same tendered buckets

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
- AND `difference` MUST remain unchanged

### Requirement: Reconciliation status and mismatch

`recon` MUST set `collected`, `withheld`, `net_due`, `tendered`, `difference`, `status`,
and `status_message`. Status MUST be `currency.compare_amounts(difference, 0.0)` →
`balanced` / `in_favor` / `outstanding`. `mismatch` MUST be set when Σ allocation
`total_vouchers` ≠ Σ printed collected voucher amounts (unallocated non-remittance sheet
vouchers). `seller_deposit` MUST NOT set `mismatch` and MUST NOT inflate
`collected_total`. When `mismatch` is set, PDF and XLSX MUST print one warning naming
`allocated_collected`, `collected_total`, and their absolute gap. (Previously: Any
unallocated sheet voucher, including a future remittance, set `mismatch` and was
included in `collected_total`; the warning named no amounts and the XLSX showed none.)

#### Scenario: Tri-state via compare_amounts

- GIVEN difference compared to 0 as equal, greater, or less
- WHEN recon is built
- THEN `status` MUST be `balanced`, `in_favor`, or `outstanding` respectively

#### Scenario: Derived cash balances the banner

- GIVEN a sheet of collected vouchers
- WHEN recon is built from the derived `cash_on_hand`
- THEN `difference` MUST be 0 and `status` MUST be `balanced`

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

### Requirement: Unsaved sheet and mixed currency

Both PDF and XLSX builders MUST call the existing saved-sheet guard. Unsaved (NewId /
non-positive id) MUST raise `UserError` and MUST NOT emit output. Mixed allocation
currencies MUST raise `UserError` (template is single-currency).

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
(`binding_type` report) so Print → Planilla de Cobranza appears on form and list.
Paperformat MUST be A4 portrait with compact header room (`margin_top` 20mm,
`header_spacing` 5mm, `margin_bottom` 14mm for the footer, `margin_left`/`margin_right`
6mm) so the tables span the usable width. Templates MUST use `t-out` (MUST NOT `t-esc`)
and MUST call `web.html_container` and MUST NOT call `web.external_layout` (no company
header); the document renders its own `.article` wrapper and a sibling
`<div class="footer o_cs_footer">` holding the reference, "Impreso el" with `printed_on`
(dd/mm/yyyy), and "Página <page> de <topage>". The Planilla title MUST render once as an
`<h2 class="o_cs_title">` at the top of the page. PDF and XLSX MUST NOT render the
company name; the XLSX MUST NOT render `printed_on`. HTML render (MUST NOT spawn
wkhtmltopdf in tests) MUST contain the sheet reference, seller name, every partner name,
applied document numbers, and the recon banner. (Previously: no footer, no page numbers
and no "Impreso el" on the PDF; `margin_bottom` 8mm.)

#### Scenario: Print menu binding

- GIVEN the report action XMLID
- WHEN inspected
- THEN `report_type` MUST be `qweb-pdf`, model `collection.sheet`, binding report on
  that model, with the collection-sheet paperformat
- AND paperformat orientation MUST be `Portrait`, `margin_top` 20, `header_spacing` 5,
  `margin_bottom` 14, `margin_left`/`margin_right` 6
- AND the document arch MUST contain the `o_cs_title` `<h2>` and MUST NOT set
  `layout_document_title`

#### Scenario: HTML contains names numbers banner

- GIVEN a saved sheet with customers, documents, and a recon status
- WHEN `_render_qweb_html` runs
- THEN HTML MUST contain the reference, seller, partner names, document numbers, and
  banner text
- AND the arch MUST NOT reference `web.external_layout`
- AND the HTML MUST NOT contain the company name
- AND the footer MUST contain "Impreso el <printed_on>" and the `page` / `topage` spans

### Requirement: XLSX workbook and percent scale

XLSX MUST be built from the same payload. Bytes MUST start `PK` and the zip MUST contain
`xl/workbook.xml`. Worksheet MUST freeze `A6`, landscape, paper size 9, fit-to-width 1.
Aggregation cells MUST use formulas with cached SUM values (`data_only` MUST read
non-None totals equal to the payload). Header rows 1–4 (repeated on every printed page)
MUST show the title "Planilla de Cobranza" (row 1), the sheet reference (row 2), and
"Vendedor: <seller> · Período: <desde> – <hasta>" (row 4), with no company name and no
printed date. Clientes **Saldo Total** and **Aplicado** MUST be
`SUMIF` of Facturas/Presupuestos Saldo/Aplicado on a hidden per-customer key column right
of the print area (one key per partner, from the payload `partner_id`; MUST NOT match on
the customer name), **Cobrado** MUST be `SUMIF` of comprobante Importe on that key, and
**Remanente** MUST be `Saldo Total − Aplicado` (cached payload values). The workbook MUST
be created with `strings_to_formulas` and `strings_to_urls` off (shared
`WORKBOOK_OPTIONS`), so free text starting with `=` or looking like a URL stays text;
intentional formulas MUST go through `write_formula`. Totales Remanente MUST reference the
Clientes remanente total (MUST NOT `=C11-G11`). Odoo `commission_percent` 0–100 MUST be written as
`percent / 100.0` into a `0.0%` cell. Banner text and fill MUST follow `recon.status`.
Header **Export XLSX** MUST be last in `<header>` before `state`. Notebook MUST be the
three pages specified in collection-sheets (recon fields remain on the sheet form).
`action_print_xlsx` MUST return `ir.actions.act_url` download; MUST NOT `sudo()`.
(Previously: Clientes totals were `SUMIF` by customer name, so same-named customers or
names holding `*` or `?` pulled each other's rows; text could become a formula. Before
that: Clientes amounts were literals; Resumen remanente was `=C11-G11` cobrado −
aplicado.)

### Requirement: Verdict-first layout and shared vocabulary

PDF and XLSX MUST open, right under the title, with the verdict: **Neto a Rendir**,
**Total Rendido**, and **Diferencia** (`recon` `net_due`, `tendered`, `difference`)
followed by the status banner and, when set, the mismatch warning. XLSX rows: section
"Resultado" on row 6, labels on row 7, values on row 8 as formulas referencing the
Conciliación cells (cached payload values), banner on row 9, mismatch on row 10; the
banner MUST NOT repeat below the Conciliación. "Resumen" MUST be split into **Datos de la
Planilla** (Referencia, Estado, Vendedor, Desde, Hasta, Moneda, Cantidad de Clientes,
Cantidad de Comprobantes, % Comisión Vendedor) and **Totales** (Total Cobrado, Total
Aplicado, Remanente, Total Comisión Devengada). Both formats MUST use the same labels:
Motivo del Remanente, Documento, Vencimiento, Fecha de Emisión, Fecha de Pago,
Nº Comprobante, Conciliación del Vendedor, Composición de lo Rendido, (−) Comisión
Retenida por el Vendedor, (=) Neto a Rendir, Total Rendido, (=) Diferencia, Depósitos de
clientes, Depósitos del vendedor. Customer deposits MUST be explained as "el cliente
depositó en la cuenta de la empresa" and seller deposits as "el vendedor depositó en el
banco el efectivo cobrado" (PDF hint column; XLSX note row under the composition).

The PDF MUST print grand totals: a Clientes **Total** row, a **Total Aplicado** row after
the Facturas/Presupuestos blocks (applied and commission), and a **Total Cobrado** row
after the Comprobantes blocks. Its Conciliación MUST read as a calculation, top to
bottom: Total Cobrado, (−) Comisión Retenida por el Vendedor, (=) Neto a Rendir, Total
Rendido, (=) Diferencia, each with a short hint, followed by **Composición de lo
Rendido**. It MUST end with signature lines "Firma del vendedor" and "Recibió — firma y
aclaración".

The XLSX MUST add two flat worksheets after the Planilla, **Documentos** and
**Comprobantes**, each one Excel table of the same name with a frozen header row (`A2`)
and no merged cells, one row per payload row in payload order. Documentos columns:
Código, Cliente, Tipo (Factura / Presupuesto), Documento, Vencimiento, Saldo, Aplicado,
Comisión. Comprobantes columns: Código, Cliente, Medio de Pago (voucher block label),
Fecha, Nº Comprobante, Banco, Tipo de Cheque, Fecha de Pago, Importe; they hold the
voucher-block rows only (no `seller_deposit`, no `seller_commission`). An empty sheet
MUST still produce both tables with their headers. The Planilla MUST stay the first and
active worksheet; only it takes the template column widths.

#### Scenario: Verdict leads both reports

- GIVEN a saved sheet with allocations and vouchers
- WHEN the PDF HTML and the XLSX render
- THEN Neto a Rendir, Total Rendido, Diferencia, and the banner MUST come before Datos
  de la Planilla, Totales, and Clientes
- AND the XLSX verdict values MUST cache `recon` `net_due`, `tendered`, `difference`

#### Scenario: Mismatch names both amounts

- GIVEN a sheet with an unallocated non-remittance voucher of 40 next to an allocation
  of 100
- WHEN both reports render
- THEN the warning MUST name 100.00, 140.00, and 40.00
- AND a sheet without mismatch MUST print no warning

#### Scenario: Flat sheets filter cleanly

- GIVEN a sheet with an invoice, a quotation, a transfer, and a check
- WHEN the XLSX renders
- THEN the sheet names MUST be Planilla de Cobranza, Documentos, Comprobantes
- AND each flat sheet MUST hold one table covering the header and every row, freeze
  `A2`, and have no merged cells

#### Scenario: Zip freeze and cached SUM

- GIVEN a saved sheet payload
- WHEN XLSX is rendered
- THEN bytes MUST start `PK` and contain `xl/workbook.xml`
- AND freeze MUST be `A6` and cached SUM cells MUST equal payload totals (MUST NOT be
  `None`)
- AND Clientes Saldo Total / Cobrado / Aplicado MUST be SUMIF formulas on the hidden
  customer-key column
- AND Clientes Remanente MUST be Saldo Total minus Aplicado

#### Scenario: Percent scale 0–100 to 0.0%

- GIVEN `commission_percent` 4.5
- WHEN the XLSX percent cell is read
- THEN the stored value MUST be 0.045 with `0.0%` format

#### Scenario: Header button last and three notebook pages

- GIVEN the sheet form arch
- WHEN inspected
- THEN the XLSX button MUST be the last header object button before `state`
- AND the notebook MUST have Allocations, Vouchers, and Debt pages

### Requirement: Company ACL and no sudo

Payload build, HTML render, and XLSX download MUST obey company `ir.rule`. Company-B
users MUST receive `AccessError` on a company-A sheet. Report code MUST NOT `sudo()`.

#### Scenario: Company-B AccessError

- GIVEN a Collections User whose company is B and a sheet in company A
- WHEN `_collection_report_data()`, HTML render, or `action_print_xlsx` runs
- THEN MUST raise `AccessError`
- AND MUST NOT return payload, HTML, or an attachment

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
Calls MUST use the authenticated user, who MUST be a Collections User (else
`AccessError`), and MUST NOT `sudo()`. Input MUST require exactly
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

- GIVEN a Collections User caller and an internal seller with exactly one `open` sheet on the
  caller's company
- WHEN `get_collection_sheet_pdf` runs with that `seller_id`
- THEN the response MUST be exactly `sheet`, `filename`, `mimetype`, `content_base64`
- AND `mimetype` MUST be `application/pdf` and `content_base64` MUST decode to the
  rendered report bytes
- AND the rendered record set MUST be that open sheet only
- AND no record MUST be created or written

#### Scenario: Submitted sheet returns base64 PDF

- GIVEN a Collections User caller and an internal seller with zero `open` sheets and exactly
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

- GIVEN a portal, public, or plain internal caller (no Collections User)
- WHEN `get_collection_sheet_pdf` runs with any `seller_id`
- THEN MUST raise `AccessError` and MUST NOT return a PDF
- AND an invalid, portal, or unknown `seller_id` from a Collections User caller MUST
  raise `UserError`

#### Scenario: Company scoping

- GIVEN a Collections User caller restricted to company A and a seller whose only `open` or
  `submitted` sheet belongs to company B
- WHEN `get_collection_sheet_pdf` runs with that `seller_id`
- THEN the response MUST be `{ "sheet": null }`
- AND the company-B report MUST NOT be rendered

### Requirement: Submitted Spanish report label

When sheet `state` is `submitted`, PDF and XLSX `state_label` MUST be `Rendida`. Other
existing Spanish state labels MUST remain unchanged.

#### Scenario: Submitted prints Rendida

- GIVEN a saved submitted sheet
- WHEN `_collection_report_data()` or bound PDF/XLSX build runs
- THEN `state_label` MUST be `Rendida`

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

#### Scenario: cash_banked excludes the commission

- GIVEN a sheet with `seller_deposit` 80, `cash_deposit` 20, and `seller_commission` 30
- WHEN the report payload is built
- THEN `cash_banked` MUST equal 80

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
