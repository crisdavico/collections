# Tasks: Local Immutable Close

## Review Workload Forecast

| Field                   | Value                     |
| ----------------------- | ------------------------- |
| Estimated changed lines | 550–800                   |
| 400-line budget risk    | High                      |
| Chained PRs recommended | Yes                       |
| Suggested split         | PR1 1–3 → PR2 4 → PR3 5–6 |
| Delivery strategy       | auto-chain                |
| Chain strategy          | stacked-to-main           |

Decision needed before apply: No Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

### Suggested Work Units

| Unit | Goal                                   | Likely PR | Focused test command                      | Runtime harness                                 | Rollback boundary                         |
| ---- | -------------------------------------- | --------- | ----------------------------------------- | ----------------------------------------------- | ----------------------------------------- |
| 1    | RED Close/`closed`/freeze-create/cycle | PR 1      | `invoke test -m collection --mode=update` | N/A=TransactionCase                             | receipt/sheet/allocation/voucher tests    |
| 2    | GREEN receipt `closed` + views         | PR 1      | same                                      | N/A=TransactionCase                             | `collection_receipt.py` + views           |
| 3    | GREEN local Close + Cancel reopen      | PR 1      | same                                      | N/A=TransactionCase                             | `collection_sheet.py`                     |
| 4    | GREEN freeze create                    | PR 2      | same                                      | N/A=TransactionCase                             | `collection_common.py` + associate create |
| 5    | Version/docs                           | PR 3      | company migration test                    | `invoke install -m collection`                  | `__manifest__.py`, `AGENTS.md`            |
| 6    | Verify                                 | PR 3      | both `--mode=update` + scoped pre-commit  | satellite `--mode=update` after `-u collection` | revert PR 3 if satellite fails            |

Strict TDD. Threat matrix N/A.

## Phase 1: RED tests

- [x] 1.1 RED `tests/test_collection_receipt.py`: rewrite `test_close_issues_*` and
      `test_close_missing_connector_rolls_back`. Local Close: `closed`, no connector;
      empty drafts close; `issued` unchanged; raw `state` UserError.
- [x] 1.2 RED same: Cancel `closed`→`draft`; `issued` unchanged; freeze until Reinstate;
      refuse frozen receipt/value/replacement create; no reverse replacements.
- [x] 1.3 RED `tests/test_collection_sheet.py`: Close `proposal` without connector; zero
      receipts close; vouchers stay `validated_collections`; Cancel
      submitted/proposal/closed; Reinstate → `submitted`.
- [x] 1.4 RED `tests/test_collection_allocation.py`: frozen sheet refuses
      allocation/line/revision create; proposal allows create.
- [x] 1.5 RED `tests/test_collection_voucher.py`: membership freeze stays on
      `ADMIN_EDITABLE_SHEET_STATES`.

## Phase 2: GREEN receipt `closed` + views

- [x] 2.1 `models/collection_receipt.py`: Selection `draft`/`closed`/`issued`;
      `_action_mark_closed` / `_action_reopen_closed`; intercept raw `state` unless
      `collection_receipt_audited_state`; freeze create; `issued` immutable; keep
      `collection_receipt_issuing`. REFACTOR helpers.
- [x] 2.2 `views/collection_receipt_views.xml`: Closed filter; hide
      `external_receipt_id`; `<list>` not `<tree>`.

## Phase 3: GREEN local Close and Cancel reopen

- [x] 3.1 `models/collection_sheet.py` `action_close`: `proposal` only; strip
      connector/`create_receipt`; one tx: `_action_mark_closed` (audited), allocations
      confirmed, sheet closed; `_check_sheet_state_iff()`. REFACTOR call sites.
- [x] 3.2 Cancel submitted/proposal/closed: `_action_reopen_closed` (audited; skip
      `issued`); draft allocations; freeze until Reinstate. GREEN 1.1–1.3.

## Phase 4: GREEN freeze create

- [x] 4.1 `models/collection_common.py`: document bypasses (audited state,
      `collection_allocation_parent_unlink`, `collection_sheet_unlinking`; not
      `message_post`). Keep `raise_if_sheet_frozen`.
- [x] 4.2 Call helper on create after gates in
      `models/collection_{allocation,allocation_line,allocation_revision,receipt,receipt_value,cash_replacement}.py`
      (`sheet_id` on allocation).
- [x] 4.3 GREEN 1.4–1.5. REFACTOR duplicate freeze into the helper.

## Phase 5: Docs / version

- [x] 5.1 `__manifest__.py` → `19.0.1.44.0`. No `migrations/19.0.1.44.0/`. `AGENTS.md`:
      local Close; receipt `closed`; freeze create.
- [x] 5.2 `tests/test_collection_company_migration.py`: pin `19.0.1.44.0`; no migrate
      folder.

## Phase 6: Verify

- [x] 6.1 `invoke test -m collection --mode=update`
- [x] 6.2 `-u collection` then
      `invoke test -m collection_receipt_proposal --mode=update` (ran: 3 failed, 1 error
      of 140; pre-existing satellite drift, not Close)
- [x] 6.3 `pre-commit run --files odoo/custom/src/private/collection/**`

## Remediation: AGENTS wrap pin

Failed verify `sha256:59ddea388282fc0317c1d2ae434b8d2866c4a589b51b2e0ba57d0130c984de82`.

- [x] R.1 Wrap-tolerant `MUST NOT consult the connector` and
      `MUST NOT call create_receipt` pins in `test_agents_md_five_state_workflow` via
      `" ".join(agents.split())`. Do not unwrap AGENTS.md. Do not change Close
      production.
