# Archive: two-step-seller-close-and-seller-deposit

The change is archived. Specs are the source of truth. The cycle is complete.

## Quick path

1. Task Completion Gate: `tasks.md` 61/61 checked, zero `- [ ]`.
2. Delta specs merged into collection mains plus granted sibling `receipt-proposal-splits`.
3. Change folder moved to `openspec/changes/archive/2026-09-08-two-step-seller-close-and-seller-deposit/` (`git mv` unavailable for the untracked tree; `mv` used). `diff -r` snapshot vs archive: empty (pass).
4. This report written after the move (additive; excluded from that comparison).

## Final state at close

| Topic | Decision |
| ----- | -------- |
| Verdict | PASS WITH WARNINGS (`pass_with_warnings`) |
| Requirements / scenarios | 28/28, 115/115 |
| Collection tests | `invoke test -m collection --mode=update` — 0 failed of 925 |
| CRITICAL | none |
| reviewGate | absent — ordinary repository policy |
| Engram | unavailable — no `mem_save`; OpenSpec filesystem only |
| Artifact store | openspec |
| Archive date | 2026-09-08 |

A first verify FAIL (U6 partial-replace board test) was fixed after that verify (`_replaced_cash_setup` sizes the deposit to `replace_amount`) and re-verify passed. That FAIL is not current state.

## Specs synced

| Domain | Action | Details |
| ------ | ------ | ------- |
| collection-sheets | Updated | 3 added, 5 modified, 0 removed. 14 unrelated requirements preserved. |
| collection-sheet-report | Updated | 1 added, 4 modified, 0 removed. 9 unrelated requirements preserved. |
| collection-receipts | Updated | 2 added, 2 modified, 0 removed. 10 unrelated requirements preserved. |
| collection-vouchers | Updated | 5 added, 3 modified, 0 removed. 34 unrelated requirements preserved. |
| receipt-proposal-splits (sibling) | Updated | 1 added, 0 modified, 2 removed (Reason + Migration present). 2 unrelated requirements preserved (`Largest-share owner`, `Unify and undo split`). |

### Collection added / modified (by name)

| Domain | Added | Modified |
| ------ | ----- | -------- |
| collection-sheets | Declare Cash on submitted; Confirm cash declaration gate; MCP write declare_collection_cash | Seller Close from open; MCP write close_collection_sheet; Mail thread and activities; Historical sheets remain operable; Four-state sheet editability |
| collection-sheet-report | Remittance cash_banked | Sheet reconciliation inputs; Voucher blocks and tendered; Reconciliation status and mismatch; Read-only MCP tool get_collection_sheet_pdf |
| collection-receipts | Cash replacement ledger; Value-preserving cash replacement | Receipt values; Receipt totals |
| collection-vouchers | Sentinel partner for seller_deposit; Receipt values reverse relation and replaced_amount; Replacement trigger on validated_collections write; MCP write create_seller_deposit; Seller deposit form fields | Payment field contract; Collection Settings persistence; Catalog XMLIDs and 19.0.1.40.0 allow-list union |

### Sibling removed (with Reason / Migration)

| Requirement | Reason (summary) | Migration |
| ----------- | ---------------- | --------- |
| Same-sheet split | Sheet-boundary receipt values now belong in core `collection-receipts`. | Replaced by Collection Receipts **Receipt values**. Satellite constraint overrides deleted; `_proposal_card_payload` may remain. |
| Sheet-wide split cap | Sheet-wide voucher split cap now belongs in core `collection-receipts`. | Replaced by Collection Receipts **Receipt values**. Core keeps one batched search. |

Sibling **added**: Replaced cash and remittance board lock.

## Warnings at close (not blockers)

1. MCP `create_seller_deposit` success is `validated_collections` vs one spec Then `validated_seller`.
2. Pre-existing sibling `TestReceiptProposalOrder`.
3. Pre-existing sibling `test_sheet_company_rule_still_guards_the_board`.

## Archive contents

- proposal.md
- exploration.md
- specs/ (five domain deltas)
- design.md
- tasks.md (61/61 complete)
- apply-progress.md
- verify-report.md
- state.yaml
- archive-report.md (this file; additive)

## Mechanical copy

- Snapshot: recursive `cp -R` of the active change folder before the move.
- Move: `git mv` failed (`fatal: source directory is empty` — untracked / ignored tree); `mv` succeeded.
- Source `openspec/changes/two-step-seller-close-and-seller-deposit/` is gone.
- `diff -r` of snapshot vs archived tree: empty (pass).

## Checklist

- [x] Main specs updated; unrelated requirements preserved
- [x] Sibling main spec merged (granted edit root)
- [x] Change folder moved to dated archive
- [x] Archive contains proposal, specs, design, tasks
- [x] Archived `tasks.md` has no unchecked implementation tasks
- [x] Active changes directory no longer has this change
- [x] Verbatim `diff -r` readback is empty
- [x] Engram skip recorded (unavailable)

## Next step

None. The SDD cycle is complete.
