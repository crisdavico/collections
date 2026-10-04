# Proposal: Two-step Seller Close and Seller Deposit

## Intent

Seller Close writes declarations with `submitted` before the seller can see frozen cash.
A banked slip has no remittance type and would inflate Total Cobrado. Split freeze from
declaration; persist `seller_deposit` on a sentinel partner; replace customer cash via
immutable `collection.cash.replacement`.

## Scope

### In Scope

- Amount-free Seller Close; re-runnable `action_declare_cash`; Confirm gated on
  `cash_declared_at` when `cash_collected > 0`.
- Eighth catalog `seller_deposit`; sentinel partner; MCP `create_seller_deposit` and
  `declare_collection_cash`.
- Remittance out of collected/mismatch; into tendered with echeck/retention. Recon
  algebra untouched. Ledger `replace`/`reverse`; trigger on `validated_collections`.
- U1 lift; U6 before U5b; PDF MCP at call site to `submitted`; keep `cash_on_hand`;
  manifest `19.0.1.43.0` (not `19.0.1.42.0/`).

### Out of Scope

Nebula agent; `create_receipt` serialization; `_sqlite_create_receipt`; optional
`partner_id`; reverse on Cancel/Reinstate; new capability folders.

## Capabilities

> sdd-spec: also emit `receipt-proposal-splits`. Apply edits sibling after
> edit-authority grant (`collection` `apply.roots` omit it). Grant is consent, not a
> reason to drop U1/U6.

### New Capabilities

None

### Modified Capabilities

- `collection-sheets`: amount-free close; `action_declare_cash`; Confirm gate; MCP close
  drops amounts, returns `cash.collected`; **ADDED** `declare_collection_cash`.
- `collection-sheet-report`: `submitted` declarations; remittance totals; `cash_banked`;
  PDF `open|submitted` at call site only.
- `collection-receipts`: sheet-boundary + sheet-wide cap; totals `depends=`; replacement
  primitives + ledger ACL `1,0,1,0`.
- `collection-vouchers`: eight catalog XMLIDs + sentinel; `receipt_value_ids` /
  `replaced_amount`; write-hook; deposit MCP + form fields.
- `receipt-proposal-splits`: REMOVE same-sheet/cap (now core); ADD U6 board lock. Keep
  largest-share owner in satellite.

## Approach

Strict TDD. `auto-chain` / `stacked-to-main`; ~400 LOC/unit. No new capability folder:
deposit and ledger fold into voucher/receipt/sheet/report. **U1 → U2 → U3 → U4 → U5a →
U6 → U5b → U5c** (U6 before U5b): lift invariants; catalog

- `19.0.1.43.0`; remittance totals; split close; ledger; board lock; replacement engine;
  deposit MCP on submitted (`sheet_id` explicit).

**User impact:** seller freezes, banks cash, declares two numbers; Planilla Cuadrada;
board cannot reassign replaced cash.

**MCP contract:** close drops amounts, returns `cash.collected` (Nebula follow-up).
Additive declare + deposit tools. PDF `{sheet}` on one `submitted`. Allocation write
stays `open` + customer-required. No `sudo()`.

## Affected Areas

Core sheet/voucher/receipt/report; new ledger; MCP close/PDF + declare/deposit tools;
catalog/sentinel; migrate `19.0.1.43.0`; views; tests; AGENTS.md. Sibling U1 deletes +
U6 board lock.

## Risks

- Nebula still sends close amounts (High): agent follow-up; Seedian ships first.
- U1/U6 outside `collection` `apply.roots` (High): grant sibling root at apply; keep
  U1/U6. Stack U6 before U5b or replaced cash reappears in the pool.
- Cap-test / N+1 / sub-cent / `cash_deposit` slip / leftover scanner / 400-line budget
  (Med): named tests; batched search; exact-cent unlink; sum `seller_deposit`; named
  frozenset; no U4+U5 or U5b+U5c merge.

## Rollback Plan

Revert stacked PRs newest-first. U2 migrate additive. Ledger drops with U5a. No column
rename; no `partner_id` nullability change.

## Dependencies

U1→U5a; U2→U3/U4/U5\*; U5a→U6+U5b; **U6→U5b**; U5b→U5c. Apply needs sibling
edit-authority. Nebula is not a code dependency.

## Success Criteria

- [ ] Close freezes with no amounts; declare re-runnable on `submitted`; Confirm refuses
      undeclared cash when `cash_collected > 0`
- [ ] `seller_deposit` on sentinel; remittance totals correct; ledger on
      `validated_collections`; U6 keeps replaced cash out of the pool
- [ ] MCP close amount-free + `cash.collected`; PDF serves `submitted`; no `sudo()`;
      collection and sibling `--mode=update` green
