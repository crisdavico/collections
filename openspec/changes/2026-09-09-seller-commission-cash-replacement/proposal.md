# Proposal: Seller commission replaces retained cash

## Intent

Cash a seller retains as commission is cash that no longer exists: it will never become
a `seller_deposit`, so the `cash` receipt values backing customer debt stay "a claim on
the seller's pocket" forever. Today the retained amount is deducted only in the
`cash_on_hand` arithmetic (`cash_collected − cash_banked − commission_withheld`), so the
instrument ledger and the reconciliation disagree by exactly `commission_withheld`, with
no instrument that can ever close the gap.

Introduce a ninth catalog code `seller_commission`: a sheet voucher that plays the same
structural role `seller_deposit` plays in cash replacement, but records commission
retained instead of cash remitted. Confirm mints it from the declared
`commission_withheld` and promotes it, so the replacement engine converts that much
`cash` into `seller_commission` on the receipts and persists the swap in
`collection.cash.replacement`.

## Scope

### In Scope

- `_iter_replaceable_cash_values` MUST skip `issued` receipts (prerequisite defect: a
  cash value on an issued receipt makes the whole promotion `UserError` out today)
- Ninth catalog code + Selection entry + `CONFIRM_REVIEW_EXEMPT_TYPES` membership
- Sentinel partner `collection.partner_seller_commission` and a type→sentinel map
  generalizing `_apply_seller_deposit_partner`
- Replacement engine generalized over `CASH_REPLACEMENT_TYPES` (`seller_deposit`,
  `seller_commission`); commission MUST raise on unspent remainder
- `action_confirm` mints at most one `seller_commission` per sheet, before the state
  write, after the existing guards; narrow `_assert_new_work` bypass for the system mint
- Report: exclude the code from voucher blocks and `tendered`; non-blocking
  `residual_cash_value_total` surfaced after Confirm
- Manifest `19.0.1.48.0` + `migrations/19.0.1.48.0/` allow-list union

### Out of Scope

- Backfilling sheets that already carry `commission_withheld` without a voucher
  (forward-only; closed sheets are frozen and MUST NOT be rewritten)
- Deriving the amount from `commission_percent × amount_applied`; the declaration is the
  cash actually kept and the computed figure is the entitlement — the gap stays visible
- Blocking Confirm on residual `cash` receipt values (warn only)
- Any new MCP tool, and any change to `declare_collection_cash` or
  `close_collection_sheet`; Confirm is an admin form action
- Reversing a commission (`_cash_reverse` stays uncalled): the declaration is locked by
  the same transition that mints the voucher, so the two can never diverge
- Renaming `collection.cash.replacement.deposit_voucher_id`

## Capabilities

### Modified Capabilities

- `collection-vouchers`: ninth `seller_commission` code, its sentinel, and its exemption
  from the Confirm review gate.
- `collection-sheets`: Confirm mints and promotes the commission voucher.
- `collection-receipts`: replacement is driven by a type set, skips issued receipts, and
  refuses an under-applied commission.
- `collection-sheet-report`: the code is excluded from `collected_total` and `tendered`,
  preserving `difference`; residual cash is reported, not enforced.

## Approach

### Why Confirm is the mint point

`commission_withheld` is writable only while the sheet is `submitted`
(`_SELLER_DECLARATION_FIELDS` in `collection_sheet_report.write`), and Confirm moves
`submitted → proposal`. Minting inside `action_confirm` therefore locks the declaration
in the same transaction that creates the instrument: the voucher `amount` and
`commission_withheld` can never diverge, so no adjustment or reverse path is needed.
Declaring at `submitted` and minting at Confirm means the instrument ledger legitimately
lags the declaration throughout `submitted`; residual-cash reporting MUST account for
that and stay silent until the sheet leaves `submitted`.

### What that makes load-bearing

`action_cancel` accepts `proposal`, `action_reinstate` walks back, and Cancel
deliberately does not reverse replacements, so `Confirm → Cancel → Reinstate → Confirm`
is reachable. The mint MUST therefore be idempotent per sheet, guarded on the sheet
already carrying a `seller_commission` voucher — not on the replacement rows.

### The arithmetic invariant

`commission_withheld` stays the declaration; the voucher is the instrument; they are
equal by construction. `_compute_cash_on_hand`, `_compute_cash_banked_totals`, and
`_collection_report_recon` therefore MUST NOT change. If `seller_commission` ever leaks
into `cash_banked` or `tendered`, the amount is counted twice and `cash_on_hand` goes
negative by exactly the commission, breaking the live `difference == −unsupported`
construction guarantee. Pinned by test in two places.

### Sentinel and review

`partner_id` is required and a commission has no customer, so a second sentinel partner
is seeded exactly like `collection.partner_seller_deposit`. A commission carries no
designated proof, so Document Review can never reach it (queue eligibility is
proof-based and needs no change) and the mint MUST stamp `validated_collections` itself
under `collection_audited_state`. `seller_commission` MUST join
`CONFIRM_REVIEW_EXEMPT_TYPES` so a re-Confirm can never deadlock on a voucher that has
nothing to review.

## Affected Areas

| Area                                                 | Impact   | Description                            |
| ---------------------------------------------------- | -------- | -------------------------------------- |
| `models/collection_common.py`                        | Modified | Ninth code; exempt set; type set       |
| `models/collection_voucher.py`                       | Modified | Sentinel map; engine over the type set |
| `models/collection_sheet.py`                         | Modified | Confirm-time mint, idempotent          |
| `models/collection_sheet_report.py`                  | Modified | Blocks/tendered exclusion; residual    |
| `models/res_company.py`                              | Modified | Commission sentinel helpers            |
| `data/collection_document_type_data.xml`             | Modified | Ninth catalog row                      |
| `data/collection_seller_commission_partner_data.xml` | Added    | Sentinel seed function                 |
| `migrations/19.0.1.48.0/post-migrate.py`             | Added    | Allow-list union; no backfill          |
| `views/collection_views.xml`                         | Modified | Residual-cash banner                   |
| `openspec/specs/*`                                   | Modified | Four deltas in this change             |
| `__manifest__.py`, `AGENTS.md`                       | Modified | `19.0.1.48.0`                          |

## Risks

| Risk                                                 | Likelihood | Mitigation                                      |
| ---------------------------------------------------- | ---------- | ----------------------------------------------- |
| Double-count inflates `tendered`, breaks recon       | Med        | Exclusion pinned in WU3 and WU4 tests           |
| Disabled seller makes Confirm unusable on old sheets | Med        | Narrow `_assert_new_work` bypass for the mint   |
| Issued receipt aborts promotion mid-Confirm          | Med        | Phase 0 fix lands first, independently          |
| Commission exceeds replaceable cash                  | Med        | Explicit `UserError`, not a silent drop         |
| Second voucher on re-Confirm after Cancel            | Low        | Mint-once guard on existing sheet voucher       |
| Historical sheets keep the old inconsistency         | High       | Accepted and documented; forward-only by choice |

## Rollback Plan

Revert the model, view, data, and spec changes and drop `migrations/19.0.1.48.0/`. The
migration only unions an allow-list entry, so leaving `seller_commission` enabled on
companies is harmless; already-minted vouchers and their `replace` ledger rows are
immutable and MUST be reversed manually with `_cash_reverse` if the feature is withdrawn
mid-period.

## Success Criteria

- [ ] Confirm on a sheet with `commission_withheld` mints exactly one
      `seller_commission` voucher and replaces that much `cash` on the receipts
- [ ] `cash_on_hand` and every `recon` value are identical before and after the mint
- [ ] `Confirm → Cancel → Reinstate → Confirm` mints no second voucher
- [ ] A commission exceeding replaceable cash raises and mints nothing
- [ ] An issued receipt no longer aborts a deposit or commission promotion
- [ ] `invoke test -m collection --mode=update` passes; scoped pre-commit clean
