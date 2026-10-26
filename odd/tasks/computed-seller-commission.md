# Computed Seller Commission

The sheet computes the seller commission; the seller only reports what they did with the cash, and the agent tells them their commission.
Branch `feat/computed-seller-commission` · delivery `ask-on-risk` · runner `invoke test -m collection --mode=update` (or `--test-tags /collection:<Class>`).

## Specs

- **S1** "I want the sheet to calculate the commission". Rule: "Each seller has his commission % and we have to applyed it to the amount untaxed of each debt ... (We have to make a proporcionallity of that if the payment is less than the total)", "we have the seller commisson % in the collection sheet". A new sheet amount `commission_amount` = sum over allocation lines of `round(amount_applied × invoice_amount_untaxed / invoice_amount × commission_percent / 100)`, the same per-line figure the Planilla PDF/XLSX already show.
- **S2** "For quotations we can take the total of the quotation as base." A quotation line (untaxed = total) pays on its applied amount; no connector change.
- **S3** "the seller only inform what did he do with the cash" — user chose "Seller says what they kept": "The sheet shows the commission; the seller reports how much cash they kept (at most the commission) and what they deposited. The rest is owed to the seller." `declare_collection_cash` keeps its `commission_withheld` argument (the cash kept); Odoo refuses an amount above `commission_amount` or above the cash collected minus seller deposits.
- **S4** The rest is owed to the seller: `commission_owed` = `commission_amount` − `commission_withheld`, shown on the sheet form, the PDF and the XLSX.
- **S5** "We inform the seller what is his commisison": `close_collection_sheet` and `declare_collection_cash` return the computed commission so the agent can tell the seller.
- **S6** Confirm keeps minting the `seller_commission` voucher for `commission_withheld` (the cash kept), unchanged.

Assumption: the cap in S3 is checked by the MCP tool when the seller declares; the back-office Declare Cash button stays uncapped so Collections can correct a declaration (about 50 existing model tests declare without allocations). Later allocation or % edits do not re-check it (owed can then go negative and is shown as is).
Out of scope: `collection_receipt_proposal` assignment report still computes gross `applied × percent` (models/collection_assignment_report.py:202).

## Tasks

| ID | Specs | Route | Status | Commit |
|----|-------|-------|--------|--------|
| T1 | S1, S2, S4 (model, form) | inline | done: 2 tests RED (no `commission_amount`) then GREEN; form test RED then GREEN | (this commit) |
| T2 | S3 (declare cap) | inline | done: 2 tests RED (UserError not raised) then GREEN | (this commit) |
| T3 | S5 (MCP responses) | inline | done: 3 tests RED (missing `commission` key) then GREEN | (this commit) |
| T4 | S4 (PDF, XLSX recon) | inline | done: 2 tests RED then GREEN | (this commit) |
| T5 | docs, openspec, i18n | inline | done: pre-commit (oca-checks-po, prettier, gen-addon-readme) converges | (this commit) |
| T6 | agent repo docs + LangSmith prompt text | inline | docs done on agent branch `docs/computed-seller-commission`; prompt text handed to the user (LangSmith not touched) | agent repo |

Route evidence: one coherent behavior in one addon (~300 lines); no Writer trigger (no parallel independent units).

## Log

- **L1** 2026-10-26 user: "i want to change that workflow. I want the sheet to calculate the commission and the seller only inform what did he do with the cash. We inform the seller what is his commisison"
- **L2** user: "Each seller has his commission % and we have to applyed it to the amount untaxed of each debt. Presupuestos we can use the total. But invoices we have the untaxed amount (We have to make a proporcionallity of that if the payment is less than the total). Ask me if have doubt"
- **L3** user: "We have to do the proporcionallity with presupuestos too. we have the seller commisson % in the collection sheet"
- **L4** user chose "Seller says what they kept".
- **L5** user: "For quotations we can take the total of the quotation as base. With that is enough?" — yes: `_collection_commission_base` already pays on applied when untaxed = total; devel has 455 quotations, all untaxed = total.
- **L6** user approved the plan: "go ahead". Engram mirror pending (no Engram tools in this session).
- **L7** Tests run on a fresh `commission_scratch` DB: `devel` sets the trusted seller header parameter, so 5 MCP happy-path tests already fail there on the baseline ("The seller identity could not be verified."). Result: collection + collection_receipt_proposal 0 failed, 0 errors of 1615 tests.
- **L8** Next: user publishes the prompt change in LangSmith; push/PR are the user's call.
