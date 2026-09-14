# Design: Seller commission replaces retained cash

## Technical Approach

Confirm mints one `seller_commission` from locked `commission_withheld`, promotes it,
and the shared engine swaps that much `cash` on non-issued receipts. Specs: vouchers,
sheets, receipts, sheet-report. MCP declare/close unchanged. No Nebula-agent. No
backfill.

## Architecture Decisions

| Decision        | Options                                  | Tradeoff                                                                    | Choice                                                         |
| --------------- | ---------------------------------------- | --------------------------------------------------------------------------- | -------------------------------------------------------------- |
| Mint point      | Declare Cash / button / `action_confirm` | Declare stays editable; a button is a second write                          | Confirm, after both gates, before `proposal`                   |
| Idempotency     | Ledger rows / member voucher             | Cancel does not reverse; re-Confirm is reachable                            | Guard on existing `seller_commission` member                   |
| Remainder       | Silent drop vs raise                     | Deposit over-tender is allowed; over-declared commission is not             | Raise only for `seller_commission`                             |
| Sentinel        | Reuse deposit partner vs second XMLID    | One partner hides type identity                                             | `collection.partner_seller_commission`                         |
| New-work bypass | Re-enable seller / `sudo()` / context    | Historical Confirm must work; never `sudo()`                                | `collection_seller_commission_mint` in `_assert_new_work` only |
| MCP enum        | Add to `_DOCUMENT_TYPES` vs reject first | Enum would advertise a Confirm-only type (`seller_deposit` already omitted) | Reject before membership; leave enum                           |
| Issued receipts | Walk and abort vs skip                   | `_shrink_or_unlink` raises on `issued`                                      | Phase 0: skip `issued`                                         |
| Recon           | Deduct via voucher vs keep withheld      | Leak into `cash_banked`/`tendered` double-counts                            | Leave `_compute_cash_on_hand` / recon algebra                  |

## Data Flow

```
action_confirm (submitted)
  ├─ _vouchers_blocking_confirm   (exempt: cash, seller_commission)
  ├─ cash_declared_at gate
  ├─ _ensure_seller_commission_voucher
  │     no-op if withheld == 0 or member exists
  │     create validated_seller, sc-<uuid4 hex>, amount=withheld
  │       context collection_seller_commission_mint → skip _assert_new_work
  │     write validated_collections (collection_audited_state)
  │       → _cash_replacers_entering_validated_collections
  │       → _run_cash_replacement  (raise if commission remainder ≠ 0)
  │     sheet.message_post
  └─ write proposal (collection_sheet_audited_state)
```

Mint while still `submitted` (`ADMIN_EDITABLE_SHEET_STATES`). A raise rolls the voucher
back. Create cannot stamp `validated_collections`; that write triggers replacement.
Issued cash cannot fund a commission. Residual sums every `cash` receipt value
(including issued) and never blocks a transition.

## File Changes

| File                                                 | Action | Description                                                                           |
| ---------------------------------------------------- | ------ | ------------------------------------------------------------------------------------- |
| `models/collection_common.py`                        | Modify | Ninth Selection; exempt `seller_commission`; add `CASH_REPLACEMENT_TYPES`             |
| `models/collection_voucher.py`                       | Modify | Type→sentinel map; rename enter/run onto the type set; skip `issued`; remainder raise |
| `models/collection_sheet.py`                         | Modify | `_ensure_seller_commission_voucher` in `action_confirm`                               |
| `models/collection_sheet_report.py`                  | Modify | Skip commission in blocks/tendered; `residual_cash_value_total`                       |
| `models/collection_cash_replacement.py`              | Modify | Docstring: `deposit_voucher_id` is the replacing voucher                              |
| `models/res_company.py`                              | Modify | Commission sentinel helpers; mint bypass in `_assert_new_work`                        |
| `models/collection_receipt_value.py`                 | Keep   | `_cash_replace` already takes any replacing voucher                                   |
| `tools/collection_voucher.py`                        | Modify | Reject `seller_commission` before `_DOCUMENT_TYPES`                                   |
| `data/collection_document_type_data.xml`             | Modify | Ninth catalog row                                                                     |
| `data/collection_seller_commission_partner_data.xml` | Create | Function seed, same as deposit                                                        |
| `__manifest__.py`                                    | Modify | `19.0.1.48.0`; data entry                                                             |
| `migrations/19.0.1.48.0/post-migrate.py`             | Create | Copy `19.0.1.43.0` union; no backfill                                                 |
| `views/collection_views.xml`                         | Modify | Residual warning; Odoo 19 `invisible=`                                                |
| `AGENTS.md`, `readme/DESCRIPTION.md`                 | Modify | Nine codes, mint, bypass, leftover pin `19.0.1.49.0`                                  |

No change: MCP declare/close/deposit, `deposit_voucher_id` column, ACL `1,0,1,0`, recon
formula.

## Interfaces / Contracts

```python
CASH_REPLACEMENT_TYPES = frozenset({"seller_deposit", "seller_commission"})
CONFIRM_REVIEW_EXEMPT_TYPES = frozenset({"cash", "seller_commission"})
{"collection_seller_commission_mint": True}  # create-only; ORM/UI/MCP omit it
```

Minted voucher: type `seller_commission`, `sc-<uuid4 hex>`,
`amount=commission_withheld`, sheet seller/sheet, sentinel, ends
`validated_collections`. Ledger type is `deposit_voucher_id.document_type`. No
`_cash_reverse` for commission.

## Testing Strategy

Strict TDD. `invoke test -m collection --mode=update`. No E2E.

| Layer             | What                                                          | Approach                                |
| ----------------- | ------------------------------------------------------------- | --------------------------------------- |
| RED→GREEN Phase 0 | Issued skipped; draft replaced; no raise                      | `test_collection_cash_replacement.py`   |
| Phase 1           | Nine codes; union keeps extras; sentinel; MCP reject          | settings, migration, voucher, MCP tests |
| Phase 2           | FIFO; shared pool; over-declare raises; excess deposit silent | cash-replacement tests                  |
| Phase 3           | Mint/no-op/gates/re-Confirm/disabled seller; recon pin        | `test_collection_sheet.py`              |
| Phase 4           | Blocks/tendered/recon; residual banner; Close unblocked       | report-data + UI                        |
| Integration       | `-u` then suite; leftover pin `19.0.1.49.0`                   | `test_collection_company_migration.py`  |

Bypass must fail create without the context key.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification,
or process-integration boundary.

## Migration / Rollout

`19.0.1.48.0` unions the ninth code (extras kept). No backfill. Delivery `ask-on-risk` /
`stacked-to-main`: Phase 0 own PR; Phases 1–2 and 3–4 stacked. Rollback: revert
code/data/specs and drop the migrate folder; minted rows need manual `_cash_reverse` if
withdrawn mid-period.

## Open Questions

None. AGENTS.md still lists `cash_on_hand` on `declare_collection_cash`; live
`tools/collection_cash_declare.py` does not. This change does not touch that tool.
