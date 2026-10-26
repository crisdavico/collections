# Declare Cash On Close

A seller cannot close a sheet that has collected cash without first saying how much commission they kept from it; the declaration happens inside Seller Close.
Branch `feat/declare-cash-on-close` (addon) and `docs/declare-cash-on-close` (agent repo) · delivery `ask-on-risk` · runner `invoke test -m collection --mode=update` on a scratch DB (or `--test-tags /collection:<Class>`).

## Specs

- **S1** "When the seller wants to close the sheet, we must control that first he tells what is he doing with the cash. We can not close a sheet without the seller doing that first."
- **S2** Approved plan ("go with the recommended approach"): the rule lives in the model, so every path obeys it (MCP, form button, generic `write`). `action_seller_close` refuses when `cash_collected > 0` and no `commission_withheld` is given; it checks `withheld ≤ commission` and `withheld ≤ cash − banked` at close time, then sets `cash_declared_at/by` in the same transaction.
- **S3** `close_collection_sheet` takes `commission_withheld`, required when cash > 0, and returns the declared commission (withheld, owed). This reverses `test_amounts_on_close_refused`.
- **S4** `declare_collection_cash` stays for corrections on `submitted` sheets before Confirm; the Confirm cash check stays (cancelled → reinstate skips close).
- **S5** The back-office "Seller Close" button opens a small wizard asking the withheld amount when there is cash.
- **S6** Docs and tests: addon `AGENTS.md`, `README.md`, `readme/CONFIGURE.md`; agent repo `docs/functional-workflow.md` (steps 9/10, :51, :59, decision log), `AGENTS.md:59`; an eval where the seller asks to close without saying what they kept.
- **S7** The hosted LangSmith prompt (`seedian-collection-agent`) must ask "how much commission did you keep from the cash?" before closing; the diff goes to the user for approval, not pushed by the agent.
- **S8** "we will also expect a clear explanation of what he does with the remaining cash (if he will add a cash deposit or he will send the cash as well)". "If the seller tells that he has a deposit we ask him the payment voucher of that and in odoo we mark it as seller deposit. If he only hand cash, we take that amount." `create_seller_deposit` also accepts the seller's open sheet, so the slip is loaded before closing.
- **S9** Reuse the existing sheet fields, with no new field ("Reuse only, no new field"). The close reply adds `cash.banked` and `cash.to_administration` (Cash to Administration), which is what the seller hands in.
- **S10** The agent asks, before closing, what the seller does with the rest of the cash. It loads any deposit slip first, then closes, and tells the seller what they hand in. Odoo enforces only the commission kept; the deposit-or-hand-in answer is not stored, and no difference is recorded.

Assumption: with no cash collected, close needs no amount; an amount given anyway is validated (only 0 passes) and declared.
Deploy: Odoo and the prompt ship together; the current prompt cannot close a sheet with cash once Odoo requires the amount.

## Tasks

| ID | Specs | Route | Status | Commit |
|----|-------|-------|--------|--------|
| T1 | S2, S3, S4 (model, MCP close, tests) | inline (one behavior; no writer trigger) | done: 7 model + 4 MCP tests RED, then GREEN | (commit) |
| T2 | S5 (wizard, view, tests) | inline | done: 3 wizard tests + UI button test | (commit) |
| T3 | S6 addon docs, openspec, i18n | inline | done: pre-commit converges (manifest author lint pre-existing) | (commit) |
| T5 | S8, S9 (deposit on open sheet, close reply amounts, tests, docs) | inline | done: 6 tests RED then GREEN; full suite 0 failed of 1633 | (commit) |
| T6 | S10 (agent docs, prompt diff) | inline | done: docs on `docs/declare-cash-on-close`; prompt diff awaiting the user's approval | agent repo |
| T4 | S6 agent repo docs + eval, S7 prompt diff | inline | done: docs + eval on `docs/declare-cash-on-close`; prompt diff handed to the user (LangSmith not touched) | agent repo |

Route evidence: one behavior across one addon plus docs; no parallel independent units, so no Writer trigger.

## Log

- **L1** 2026-10-26 user: "i want to review something. When the seller wants to close the sheet, we must control that first he tells what is he doing with the cash. We can not close a sheet without the seller doing that first. Propose me a plan"
- **L2** user: "yes, go with the recommended approach" (declare inside close, not declare on open sheets).
- **L3** Evidence: `action_seller_close` (`models/collection_sheet.py:303`) accepts and ignores `commission_withheld`; declare is submitted-only (`:339`, `collection_common.py:122`, `collection_sheet_report.py:207`); Confirm requires `cash_declared_at` when cash > 0 (`:396-407`).
- **L4** Engram mirror pending: no memory tools in this session.
- **L5** Added beyond the plan, to make S7 work: the refusal names the cash collected and the commission, because the agent cannot read the commission before closing (`get_collection_sheet_pdf` returns only a file).
- **L6** Fallout: about 95 existing tests closed cash sheets without an amount. Their fixtures now pass `commission_withheld=0.0`. The cash-replacement `_submit` and the two "undeclared cash blocks Confirm" tests now use `force_sheet_state`, because they plant states that close can no longer reach. `collection_receipt_proposal/tests/common.py` `_confirm` got the same change, on branch `feat/declare-cash-on-close` in that repo.
- **L7** Tests on the scratch DB `cashclose_scratch` (devel has the trusted seller header). The `.pot` was exported from the scratch DB, and only this change's msgids and references were spliced in.
- **L8** Independent verifier: S1-S5 and S7 PASS. One blocker: `readme/DESCRIPTION.md` still described close-then-declare. Fixed in `56bb6f3`, and README.rst/index.html were regenerated. Its advisories: the wizard pre-fills 0; a recordset close applies one amount to every sheet (no caller does this); the draft prompt had dropped the deposit question (restored in the draft).
- **L9** Native review (risk + reliability lenses, base `main`, commits `8339efc` + `56bb6f3`): approved and acknowledged, lineage `review-0128bdbd0a36298c`. Advisories, not blocking: the wizard declares an implicit 0 when nothing is typed (WARNING); the close-time cap "cash minus seller deposits" has no test with a deposit on the sheet (SUGGESTION).
- **L10** Next: the user approves and publishes the LangSmith prompt diff, and decides on the wizard default. Ship Odoo and the prompt together. Push and PRs are the user's call.
- **L11** 2026-10-26 user: "yes, push the prompt". Pushed to LangSmith `seedian-collection-agent` as commit `26e25f4` (parent `f61f5d1`), read back identical to the approved text. The agent builds its graph once (`_graph` in `src/agent/agent.py`), so a running agent keeps the old prompt until it restarts. Rollback: push `f61f5d1`'s manifest again.
- **L12** 2026-10-26 user: "push the branches and open the PRs"; user chose "Single PR, size exception" (845 changed lines). PRs: crisdavico/collections#50, crisdavico/collection_receipt_proposal#17, crisdavico/collection-agent#16. The agent repo's merge to `main` dispatches a deploy (`build-push-arm64.yml`), which restarts the agent onto the new prompt, so merge #16 only once #50 is deployed.
- **L13** 2026-10-26 user: "as we tells the seller to explain how much money of the comission he keeps, we will also expect a clear explanation of what he does with the remaining cash (if he will add a cash deposit or he will send the cash as well)". The user chose "Odoo records + enforces". Then: "If the seller tells that he has a deposit we ask him the payment voucher of that and in odoo we mark it as seller deposit. If he only hand cash, we take that amount. Ask me anything you need". Then "Record any difference". Then "we already have fields on collection sheet. Can we use those?". Then "Reuse only, no new field". Then "Yes, build it", after being told that this drops enforcement in Odoo and the recorded difference.
- **L14** When the seller has both an open and a submitted sheet, a deposit now goes to the open one (before: to the submitted one). This follows from S8 and matches `get_collection_sheet_pdf`. The reviewer's advisory is covered: a deposit loaded before close lowers the cash cap (`test_deposit_loaded_before_close_is_in_the_reply_and_the_cap`).
- **L15** 2026-10-26 user: "we do not need a confirmation first. Leave the confirmation like a final step before calling close_collection_sheet". Prompt redraft: ask about the cash and any deposit first, confirm last, then close. No tool exposes the commission before close, so the agent learns it from the refusal when the seller's answer does not match the sheet.
- **L16** Verifier on `4e71037`: S1-S5 and S7-S10 PASS. A deposit on an open sheet works with review approval, cash replacement, the Planilla, Reset to Open and delete. One blocker: `AGENTS.md:513-514` still said submitted-only; fixed. Advisories: `to_administration` goes negative when deposits exceed the cash collected (the compute is unchanged, but the reply now shows it); the refusal for two submitted sheets still says "more than one open collection sheet".
- **L17** Native review of `56bb6f3..984e339` (risk + reliability lenses): approved and acknowledged, lineage `review-0bf51131bd892584`. Advisories, not blocking: `cash.to_administration` can be negative (WARNING); a no-open, two-submitted refusal says "more than one open collection sheet" (WARNING); no test covers the "no open or submitted sheet" refusal (SUGGESTION).
- **L18** user: "the prompt is ok" (the version with confirmation last). The LangSmith push was blocked by the session's permission check; it waits on the user, and so do the branch pushes for `4e71037`/`984e339` and `2ad6f71`.
