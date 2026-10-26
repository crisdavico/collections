# Cash-Focused Reconciliation

Replace the always-zero "Conciliación del Vendedor" (A entregar − Entregado = Diferencia) with a cash calculation, in PDF and XLSX.
Branch `feat/clearer-sheet-report-labels` · delivery `ask-on-risk` · runner `invoke test -m collection --mode=update`.

## Specs

- **S1** Both: option A, "Focus on cash". Conciliación reads: Efectivo cobrado, (−) Depositado por el Vendedor, (−) Comisión Retenida por el Vendedor, (=) Efectivo a entregar; then "Cobrado por otros medios (cheques, transf., ...)" as informative only.
- **S2** Both: "Diferencia and the tri-state status go away": no Diferencia line, no banner, payload drops `net_due`, `tendered`, `difference`, `status`, `status_message`.
- **S3** Both: "Comisión: devengada · retenida · a pagar (separate box)".
- **S4** Both: "keep Composición de lo Entregado" (the `tendered` breakdown stays as it is).
- **S5** Both: the verdict at the top follows the new calculation. Assumption (not asked): it shows Efectivo a entregar, Cobrado por otros medios, Comisión a Pagar al Vendedor; the mismatch warning stays.

Constraint: `_BANNER_FILL` stays in `report/collection_sheet_xlsx.py`; `collection_receipt_proposal` imports it.

## Tasks

| ID | Specs | Route | Status | Commit |
|----|-------|-------|--------|--------|
| T1 | S1-S5 payload, PDF, XLSX, tests, spec, i18n | inline (one behavior; no writer trigger) | done: report tests RED (9+ failing) then GREEN except one test-lookup bug, fixed; final run pending at commit | this commit |

## Log

- **L1** (2026-10-26) User: "Can you review the Conciliación del Vendedor table. It is a bit confusing. Give me options and i will tell you" → "go with A" → "I like option A but then keep Composición de lo Entregado".
- **L2** Evidence: `difference` ≡ 0 by construction (tendered.total = collected_total − withheld); non-zero only in tests that inject a fake total. No consumer outside the report reads the recon payload; the WhatsApp agent reads only `commission.owed` from `declare_collection_cash`.
- **L3** Engram mirror pending: no memory tools in this session.
- **L4** i18n: `invoke updatepot` also pulled unrelated drift (IIBB, IVA, Ratings, removed Transferencia bancaria…); only this change's msgids were spliced in.
