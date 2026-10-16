# Sheet Report Clarity

Make the Planilla de Cobranza PDF and XLSX easier to read: verdict first, one vocabulary,
grand totals, a calculation-style reconciliation, flat XLSX data sheets.
Branch `feat/sheet-report-clarity` (worktree `../collection-sheet-report`) · delivery `ask-on-risk` · runner `invoke test -m collection --mode=update` (or `--test-tags /collection:<Class>`).

## Specs

- **S1** Both: "Put the answer first." Neto a Rendir / Total Rendido / Diferencia and the status banner sit at the top, under the title.
- **S2** Both: "Use the same labels in both." Excel names win: Total Comisión Devengada, Motivo del Remanente, Documento / Vencimiento, Fecha de Emisión / Fecha de Pago, Conciliación del Vendedor, Cantidad de Clientes / Cantidad de Comprobantes, % Comisión Vendedor, Nº Comprobante.
- **S3** Both: "Explain 'Depósitos' vs 'Depósitos vendedor'." One is a deposit voucher from a customer, the other the seller's own bank deposit slip.
- **S4** PDF: "Show the reconciliation as a calculation" (Total Cobrado, (−) Comisión Retenida, (=) Neto a Rendir, Total Rendido, (=) Diferencia), as the Excel does.
- **S5** PDF: "Add grand totals": Clientes total row, Total Aplicado across invoices and quotations, Total Cobrado across all vouchers.
- **S6** PDF: "Split the Resumen grid" into "Datos" and "Totales" with no blank cells.
- **S7** PDF: "Add a footer and signature lines": print date and "Página X de Y" (user chose "Date and page numbers", reversing commit 296f9cc for the PDF only), plus "Firma vendedor / Recibió".
- **S8** Both: "Make the mismatch warning specific": show both amounts and the gap.
- **S9** Excel: "Add flat data sheets": keep the printable Planilla, add "Documentos" and "Comprobantes" as Excel tables with filters, one row per line, no merges.
- **S10** Excel: "Fix the frozen header": real headers frozen on the flat sheets; the repeated print rows add seller and period.
- **S11** "remove Motivo del remanente": Clientes ends at Remanente in PDF and XLSX; the always-empty `residual_reason` placeholder leaves the payload.

Assumption: XLSX keeps no printed date (the footer decision was asked for the PDF).

## Tasks

| ID | Specs | Route | Status | Commit |
|----|-------|-------|--------|--------|
| T1 | S1-S8 (PDF + payload) | inline | done: 15 PDF/payload tests RED then GREEN; sample PDF reviewed | 1026885 |
| T2 | S1-S3, S8-S10 (XLSX) | inline | done: 8 XLSX tests RED then GREEN; sample XLSX dumped | 35d241e |
| T3 | spec.md, AGENTS.md, i18n | inline | done: Odoo export spliced (15 dropped, 37 added); PoFileReader OK; pre-commit clean | dae6073 |
| T4 | S11 | inline | done: 4 tests RED then GREEN; report + MCP PDF 125/125 | 2449ce7 |

Route: inline. PDF and XLSX share the vocabulary, payload keys and spec file, so they are not independent units; no Writer trigger.

## Log

- **L1** (2026-10-16) "what would you change of pdf and excel report of collection sheet to make it better and easier to understand?" → ten proposals; user: "go on with all of that".
- **L2** (2026-10-16) Footer conflicts with spec (no printed date, no footer). User answer: "Date and page numbers".
- **L3** (2026-10-16) Another party began editing the shared `collection` checkout mid-task. User chose "Move me to a worktree": shared checkout back on `feat/reversible-states`, my diff moved to worktree `collection-sheet-report`, tests run on isolated DB `sheetreport` with the worktree mounted.
- **L4** (2026-10-16) Report classes 107/107 green on `sheetreport`. Sample render fixed three PDF layout flaws (grand-total cells, "Código" mid-word break, Datos label width).
- **L5** (2026-10-16) Full `collection` suite 1283/1283 green on `sheetreport`; report + MCP PDF classes 125/125 after formatting. Review assess on 876533c..HEAD: risk medium, `review_due` false (`under_budget`). Branch not pushed; push/PR are the user's call. Engram mirror pending (no memory tool in this session).
- **L6** (2026-10-16) User: "remove Motivo del remanente and push and pr". Delivery: one PR (the user asked for a PR, over the 400-line budget).
