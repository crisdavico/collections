# Real Open Debt

A document already applied on a collection sheet shows its real open amount, whether or not its receipt was typed into the ERP and whenever the debt snapshot was last refreshed.
Branch `feat/real-open-debt` (addon, stacked on `fix/manual-collection-flow`; `collection_connector_bejerman_kras`) and `docs/real-open-debt` (agent repo) · delivery `ask-on-risk` · runner `invoke test -m collection --mode=update` (or `--test-tags /collection:<Class>`).

## Specs

- **S1** "i think is best to forget about when the user sends the info to the ERP. If a debt is already on a sheet, we have to see whats its real open amount". Approved rule, per external document: `open = max(0, min(ERP balance now, base − total applied on non-cancelled sheets))`, where `base` is the ERP balance when the document was first applied on a sheet (the largest among the applied lines). The "Entered in the ERP" mark and the snapshot refresh time no longer change it.
- **S2** Each allocation line stores `erp_balance_base`: the ERP balance when it was created; an MCP amendment keeps it for a document the allocation already applied. Lines stored before this change take their `invoice_balance` (backfilled in the model's `init()` on upgrade).
- **S3** `customer_debt` returns, per invoice, `allocatable_balance` = the open amount (S1) and `in_collection` = `balance − allocatable_balance`; the summary adds `in_collection_total` and `pending_total` (`net_total − in_collection_total`). The tool description says `pending_total` is what the customer still owes. The allocation write checks applications against the same open amount, excluding the allocation it amends.
- **S4** "so this way the seller will see on whatsapp the real remaining amount?" — the Planilla PDF/XLSX "Saldo" column shows what was open on the document before this sheet (S1 over earlier non-cancelled sheets), not the gross ERP balance.
- **S5** "But remember that we have a cron running every 4 hours that recreate debt lines." The rule does not depend on the snapshot rows or their refresh time; document ids (`tipo|punto|letra|numero`) stay the same across refreshes.
- **S6** Docs: addon `AGENTS.md`/`README`; agent repo `docs/functional-workflow.md` (step 15 and the decision log) and `AGENTS.md`. The Bejerman KRAS test that asserted the release by refresh follows S1.
- **S7** "yes, implement it. You change the langsmith prompt": the hosted `seedian-collection-agent` prompt tells the model to give the seller `pending_total` as what the customer owes and mention `in_collection_total` as already collected and pending in the ERP. "only when the seller asks for it": the per-document list (number, due date, `allocatable_balance`, overdue marked; zero open = paid, pending entry in the ERP) only when the seller asks for the detail. Per agent `AGENTS.md` rule 9 the diff is shown before the push.

Known limit (accepted): a payment typed into the ERP outside the sheets while a sheet's receipt is still pending makes the open amount higher than the truth by the smaller of the two (balance 100, 30 on a sheet not typed, 20 typed outside: 70 instead of 50).
Kept as is: the "Entered in the ERP" mark (informational, back-office tracking). Removed: `_collection_erp_reflected_since()` from `collection` and both Bejerman connectors (no caller left).

## Tasks

| ID | Specs | Route | Status | Commit |
|----|-------|-------|--------|--------|
| T1 | S1, S2, S3, S5 (field, init backfill, rule, MCP, tests) | inline (one behavior; no writer trigger) | done: 14 tests RED (10 failed, 8 errors), then GREEN; upgrade backfills a NULL base from invoice_balance | `2efe793` |
| T2 | S4 (sheet report Saldo, tests) | inline | done: `test_planilla_balance_is_what_earlier_sheets_left_open` RED then GREEN | `2efe793` |
| T3 | S6 (addon docs, KRAS test, release hook removed) | inline | done: kras/bejerman tests updated; pre-commit converges (manifest author lint pre-existing) | `0955bcf` (bejerman), `add792f` (kras) |
| T4 | S6, S7 (agent docs, prompt diff) | inline | docs done on `docs/real-open-debt`; prompt pushed after approval: LangSmith commit `bf8bd15e` (total by default, list on request), read back identical | `fe46615` (agent repo) |

## Log

- **L1** (2026-11-02) "The debt that is already on a closed sheet, is being repated on a new open sheet?" / "my doubt is because the seller on whatsapp only sees the debt, but if that debt is on a closed sheet and not transfered to the erp i seems like the customer has open debt. How can we handle that?" / "But remember that we have a cron running every 4 hours that recreate debt lines. Would that be a problem? Make a full review of the project" / "i think is best to forget about when the user sends the info to the ERP. If a debt is already on a sheet, we have to see whats its real open amount" / "so this way the seller will see on whatsapp the real remaining amount?" / "yes, implement it. You change the langsmith prompt"
- **L2** Review: Close marks the sheet "Entered in the ERP" (`16b638a`), so the first snapshot refresh after a close released its applied amounts even when the receipts were not typed in yet; `customer_debt` described the gross `total_balance` as what the customer owes; the Planilla printed gross balances. Engram mirror: pending (no memory tools in this session).
- **L3** Baseline on scratch DB `opendebt_scratch` (collection, collection_receipt_proposal, collection_connector_bejerman, collection_connector_bejerman_kras): 0 failed, 0 errors of 1874. After the change: 0 failed, 0 errors of 1874 (14 tests added, 14 tests of the old release rule removed). A computed field with no dependency was not filled on create, so the base became a plain field defaulted in `create` and backfilled in `init()`. The kras `service/mapping.py` reformat by ruff (pre-existing) was reverted as unrelated.
- **L4** (2026-11-02) "will the response of the agent have a detailed information of each debt?" / "only when the seller asks for it". Review assessment: all four commits medium, `under_budget`, no review due (agent repo assessed with untracked `data/` excluded).
- **L5** (2026-11-02) "yes, push it": pushed `seedian-collection-agent` `e01bb8e5` → `bf8bd15e`; the hosted template read back equals the approved one.
