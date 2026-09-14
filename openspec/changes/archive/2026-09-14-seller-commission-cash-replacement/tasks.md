# Tasks: Seller commission replaces retained cash

Strict TDD: every phase writes RED tests before the GREEN change. Run
`invoke test -m collection --mode=update` after each phase.

## Phase 0: Issued receipts stop aborting replacement (independently reviewable)

- [x] 0.1 RED `tests/test_collection_cash_replacement.py`: a sheet with an `issued`
      receipt holding a `cash` value and a `draft` receipt holding another; a
      `seller_deposit` promotion MUST replace the draft cash, leave the issued receipt
      untouched, and MUST NOT raise.
- [x] 0.2 GREEN `_iter_replaceable_cash_values`: filter candidate receipts to
      `state != 'issued'` before the kind buckets.
- [x] 0.3 Delta the `Value-preserving cash replacement` requirement (issued exclusion
      only) and land as its own commit — this is a defect fix, not the feature.

## Phase 1: Catalog, sentinel, type plumbing

- [x] 1.1 RED `tests/test_collection_company_settings.py` +
      `test_collection_company_migration.py`: nine catalog rows; a new company allows
      all nine; the `19.0.1.48.0` union adds `seller_commission` and keeps extras;
      manifest pinned to `19.0.1.48.0`; `19.0.1.49.0` leftover pin.
- [x] 1.2 RED `tests/test_collection_voucher.py`: `seller_commission` create stamps
      `collection.partner_seller_commission`; a real customer `partner_id` refuses; a
      `customer_identification` refuses; sentinel seeding is idempotent.
- [x] 1.3 GREEN `collection_common.py`: ninth `DOCUMENT_TYPE_SELECTION` entry; add
      `seller_commission` to `CONFIRM_REVIEW_EXEMPT_TYPES`; add
      `CASH_REPLACEMENT_TYPES = frozenset({"seller_deposit", "seller_commission"})`.
      Confirm `COLLECTION_TYPE_CODES = DOCUMENT_TYPE_CODES` needs no edit.
- [x] 1.4 GREEN ninth row in `data/collection_document_type_data.xml`; new
      `data/collection_seller_commission_partner_data.xml`; manifest `data` entry.
- [x] 1.5 GREEN `res_company._seller_commission_partner()` +
      `_collection_ensure_seller_commission_partner()` mirroring the deposit helpers.
- [x] 1.6 GREEN generalize `_apply_seller_deposit_partner` into a type→sentinel map on
      `collection.voucher`; keep both refusal messages type-specific.
- [x] 1.7 GREEN reject `seller_commission` on the MCP write path alongside
      `unsupported`.
- [x] 1.8 Manifest `19.0.1.48.0`; `migrations/19.0.1.48.0/post-migrate.py` copying the
      `19.0.1.43.0` union body. No backfill of any kind.

## Phase 2: Generalize the replacement engine

- [x] 2.1 RED `tests/test_collection_cash_replacement.py`: a `seller_commission`
      promotion replaces cash FIFO and preserves `total_values` / `amount_applied`;
      ledger rows carry it as `deposit_voucher_id` with `direction` `replace`; a deposit
      and a commission share one cash pool without double-consuming; an over-declared
      commission raises; an excess deposit still drops silently (regression); the
      commission voucher cannot be unlinked once referenced.
- [x] 2.2 GREEN rename `_seller_deposits_entering_validated_collections` →
      `_cash_replacers_entering_validated_collections` and
      `_run_seller_deposit_cash_replacement` → `_run_cash_replacement`, both filtering
      on `CASH_REPLACEMENT_TYPES`.
- [x] 2.3 GREEN raise `UserError` when a `seller_commission` finishes the walk with a
      non-zero remainder; leave the deposit remainder silent.
- [x] 2.4 GREEN docstring `collection.cash.replacement.deposit_voucher_id` as "the
      replacing voucher (`seller_deposit` or `seller_commission`)". No column rename, no
      migration.

## Phase 3: Mint at Confirm

- [x] 3.1 RED `tests/test_collection_sheet.py`: Confirm with `commission_withheld` 300
      mints exactly one voucher at `validated_collections` with `document_id`
      `sc-<uuid4 hex>` and replaces 300 of cash; zero commission mints nothing; a
      Confirm refused by either existing gate mints nothing and leaves `submitted`;
      `Confirm → Cancel → Reinstate → Confirm` mints no second voucher and adds no
      ledger row; a seller removed from `enabled_seller_ids` still Confirms.
- [x] 3.2 RED the double-count pin: `cash_on_hand` and `cash_banked` are identical
      before and after the mint.
- [x] 3.3 GREEN `collection_sheet._ensure_seller_commission_voucher()` with the
      zero-amount and existing-member idempotency guards; chatter note.
- [x] 3.4 GREEN call it in `action_confirm` after both guards, before the state write.
- [x] 3.5 GREEN narrow `_assert_new_work` bypass context key for the system mint,
      documented; assert by test it does not widen to ORM/UI/MCP create.

## Phase 4: Reporting and residual warning

- [x] 4.1 RED `tests/test_collection_sheet_report_data.py`: `collected_total`,
      `tendered.total`, and the voucher blocks all exclude `seller_commission`; every
      `recon` key is unchanged by the mint and `difference` stays `−unsupported`;
      `cash_banked` excludes it.
- [x] 4.2 RED `tests/test_collection_ui.py` + report data: `residual_cash_value_total`
      computes from `cash` receipt values; the banner shows outside `open`/`submitted`
      only; it blocks nothing and touches no recon key.
- [x] 4.3 GREEN skip `seller_commission` in `_collection_report_voucher_blocks`
      alongside `seller_deposit`; make its exclusion from `_collection_report_tendered`
      explicit rather than dispatch fall-through.
- [x] 4.4 GREEN `residual_cash_value_total` compute + the sheet-form banner.
- [x] 4.5 Confirm no MCP surface changed: `declare_collection_cash` and
      `close_collection_sheet` request and response shapes untouched.

## Phase 5: Docs and verify

- [x] 5.1 AGENTS.md: nine catalog codes; the second sentinel and the type→sentinel map;
      `CONFIRM_REVIEW_EXEMPT_TYPES` is now two codes; `CASH_REPLACEMENT_TYPES`;
      Confirm-time mint and its `_assert_new_work` bypass;
      `Module metadata 19.0.1.48.0`; add `migrations/19.0.1.48.0/` and a "Do **not** add
      `migrations/19.0.1.49.0/`" pin.
- [x] 5.2 Fold the four deltas into the live specs under `openspec/specs/`.
- [x] 5.3 `readme/DESCRIPTION.md` if it enumerates document types; regenerate
      `README.rst` via the OCA hook, never by hand.
- [x] 5.4 `invoke install -m collection` upgrade, then
      `invoke test -m collection --mode=update`, then
      `pre-commit run --files odoo/custom/src/private/collection/**`.

## Review budget

Phase 0 is one commit and well under budget. Phases 1–2 and 3–4 are each near the
400-line review budget once tests are counted; keep them as separate stacked PRs rather
than one branch.
