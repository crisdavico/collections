# Apply Progress: document-review-ocr-only

**Change**: `document-review-ocr-only`
**Mode**: Strict TDD
**Batch**: Phase 4 / work unit 4 (manifest `19.0.1.36.0` + AGENTS + verify)
**Delivery**: size:exception (user-authorized apply-through-verify despite High
forecast); chain strategy stacked-to-main later
**applyState at start**: ready
**Engram**: not available — filesystem only

## Completed Tasks

- [x] 1.1 RED `get_review_queue` `seller_changed_fields`: empty-empty omit; emptied
      seller `False`/`0.0`; typed Char/Date/Selection/Monetary diffs; keys follow
      `_REVIEW_EDITABLE_FIELD_ORDER`
- [x] 1.2 RED rewrite approve/correction/stale: empty/omit/nonempty `vals` leave current
      unchanged; snapshot `approved` matches current; keep empty-vals snapshot test
- [x] 1.3 RED rewrite OWL source tests: one readonly `ocr_*`; no seller/current widgets,
      `t-on-*`/`onFieldInput`, or `buildApproveVals`; `_layerHasDocumentType` OCR∪seller
      only; `.seller-warning` `role="status"`; dual bank/check groups; no `document_id`;
      approve RPC `[[id], sheetId]`
- [x] 1.4 `invoke test -m collection --mode=update` RED; no `models/` or `static/`
- [x] 2.1 `_REVIEW_EDITABLE_FIELD_ORDER` tuple (frozenset derived from it) plus empty/eq
      helpers (`float_compare` 2dp; `fields.Date.to_date`; Char/Selection exact)
- [x] 2.2 `_review_queue_payload` adds `seller_changed_fields` (ocr vs seller; both
      empty omit; else seller raw `False`/`0.0`). Keep current/`ocr_*`/`seller_*`
- [x] 2.3 Ignore approve `vals`; `_write_review_decision()` with no extra; delete
      `_editable_review_vals`. Keep `action_review_approve(..., vals=None)`
- [x] 2.4 Payload + approve tests GREEN; OWL source tests still RED (at end of Phase 2)
- [x] 3.1 `document_review_action.xml`: one readonly `ocr_*`; drop seller/current/
      `t-on-*`; `<p class="seller-warning" role="status" aria-live="polite">`; dual
      groups OCR∪seller type
- [x] 3.2 `document_review_action.esm.js`: type getters OCR∪seller; drop `onFieldInput`;
      `orm.call(..., [[id], sheetId])`
- [x] 3.3 `document_review_helpers.esm.js`: drop `buildApproveVals`; map lookup + format
      (Spanish/ISO/2dp/blank; nested JSON `false` treated as empty)
- [x] 3.4 `document_review_action.scss`: `.seller-warning` `--rose` (not `.btn.no`). OWL
      source tests GREEN. ACL leftover-vals assert expects `100.0`
- [x] 4.1 GREEN `__manifest__.py` `"version": "19.0.1.36.0"`; kept receipt views; no
      `migrations/19.0.1.36.0/`
- [x] 4.2 RED-then-GREEN version asserts + `AGENTS.md` OCR-only / seller warnings /
      no-rewrite; keep 1.34/1.35 receipt migrate docs
- [x] 4.3 Scoped pre-commit exit **0**; `invoke test -m collection --mode=update` exit
      **0** (`0 failed, 0 error(s) of 749 tests`)

## Remaining Tasks

None. Ready for verify.

## Files Changed

| File                                                          | Action   | What Was Done                                                                                                                                                                             |
| ------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/test_collection_document_review.py`                    | Modified | Phase 1: RED helpers + queue diff tests; rewrite approve/OWL/RPC asserts                                                                                                                  |
| `models/collection_voucher.py`                                | Modified | Phase 2: order tuple; empty/eq helpers; `seller_changed_fields`; ignore approve vals; delete `_editable_review_vals`                                                                      |
| `static/src/document_review/document_review_action.xml`       | Modified | Phase 3: one readonly `ocr_*` per field; drop seller/current widgets and `t-on-*`; inline `.seller-warning` with `role="status"` `aria-live="polite"`; `seller_changed_fields` map lookup |
| `static/src/document_review/document_review_action.esm.js`    | Modified | Phase 3: `_layerHasDocumentType` OCR∪seller only; drop `onFieldInput`; approve `[[id], sheetId]`; wrap map lookup/format for QWeb                                                         |
| `static/src/document_review/document_review_helpers.esm.js`   | Modified | Phase 3: drop `buildApproveVals` / rewrite helpers; add `hasSellerChangedField` + `formatSellerChangedValue` (Spanish/ISO/2dp/blank)                                                      |
| `static/src/document_review/document_review_action.scss`      | Modified | Phase 3: `.seller-warning { color: var(--rose) }` (not `.btn.no`)                                                                                                                         |
| `tests/test_collection_acl.py`                                | Modified | Phase 3 collateral: leftover `{"amount": 150.0}` must not rewrite current (`100.0`)                                                                                                       |
| `openspec/changes/document-review-ocr-only/tasks.md`          | Modified | Phase 1 + Phase 2 + Phase 3 + Phase 4 checkboxes `[x]`                                                                                                                                                |
| `openspec/changes/document-review-ocr-only/apply-progress.md` | Updated  | Merged Phase 1 + Phase 2 + Phase 3 + Phase 4 evidence                                                                                                                                                 |
| `__manifest__.py`                                             | Modified | Phase 4: version `19.0.1.35.0` → `19.0.1.36.0` only; receipt `data` row kept                                                                                                                          |
| `tests/test_collection_company_migration.py`                  | Modified | Phase 4: assert manifest `19.0.1.36.0`; forbid 1.35 and 1.36 migrate folders; AGENTS Module metadata 1.36 not 1.34/1.35                                                                                |
| `AGENTS.md`                                                   | Modified | Phase 4: version `19.0.1.36.0`; keep 1.34/1.35 receipt migrate; OWL OCR-only + seller warnings + approve does not rewrite current                                                                      |
| `tests/test_collection_document_review.py`                    | Modified | Phase 4: E501 docstring wraps; approve compact regex allows prettier trailing comma `sheetId,?`                                                                                                       |

Receipt `data` / migrate-1.34/1.35 content kept. No `migrations/19.0.1.36.0/`. Form views and `tests/test_collection_ui.py` untouched.

## TDD Cycle Evidence

| Task | Test File                                  | Layer                                             | Safety Net                                                                                                                                       | RED                                                                         | GREEN                                                                                                                                      | TRIANGULATE                                                                                                                                                              | REFACTOR                                                                                   |
| ---- | ------------------------------------------ | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| 1.1  | `tests/test_collection_document_review.py` | Integration                                       | N/A this batch (file rewritten for new contract; suite otherwise green except these RED rows)                                                    | ✅ Written + executed                                                       | ➖ Phase 1 RED-only                                                                                                                        | ✅ empty-empty `{}`; emptied Char `False`; emptied amount `0.0`; typed Char/Date/Selection/Monetary + equal-nonempty omit; `_REVIEW_EDITABLE_FIELD_ORDER` AttributeError | ➖ No production                                                                           |
| 1.2  | `tests/test_collection_document_review.py` | Integration                                       | Keep-path still green: omit (`test_document_review_approve_empty_vals_snapshots_current`) and `{}` (`test_approve_persists_cash_deposit_fields`) | ✅ Written + executed                                                       | ➖ Phase 1 RED-only                                                                                                                        | ✅ nonempty bank/check; stale nonempty; same-sheet nonempty; omit + empty dict keep                                                                                      | ➖ No production                                                                           |
| 1.3  | `tests/test_collection_document_review.py` | Integration (source-string OWL)                   | Keep-path: `test_owl_empty_provenance_still_loads` still binds OCR without `t-if`                                                                | ✅ Written + executed                                                       | ➖ Phase 1 RED-only                                                                                                                        | ✅ type getter still includes `current.document_type`; `buildApproveVals` still present; approve RPC still sends vals                                                    | ➖ No production                                                                           |
| 1.4  | same                                       | Integration                                       | See Phase 1 command                                                                                                                              | ✅ Suite RED                                                                | ➖ Phase 1 RED-only                                                                                                                        | ➖ Runner evidence                                                                                                                                                       | ➖ No production                                                                           |
| 2.1  | `tests/test_collection_document_review.py` | Integration                                       | Phase 1 baseline: 737/749 pass; 11 failed + 1 error (all `TestCollectionDocumentReview`)                                                         | ✅ Phase 1 already wrote `test_review_editable_field_order_is_stable_tuple` | ✅ Passed (tuple + helpers used by payload)                                                                                                | ✅ tuple membership + uniqueness from that test                                                                                                                          | ✅ frozenset derived from order tuple                                                      |
| 2.2  | same                                       | Integration                                       | Same baseline                                                                                                                                    | ✅ Phase 1 queue tests                                                      | ✅ Passed empty-empty `{}`; emptied Char `False`; emptied amount `0.0`; typed diffs in field order                                         | ✅ 3 queue cases (empty-empty / emptied / typed order)                                                                                                                   | ➖ Helpers already typed; no further extract                                               |
| 2.3  | same                                       | Integration                                       | Same baseline                                                                                                                                    | ✅ Phase 1 approve rewrite tests                                            | ✅ Passed nonempty bank/check; stale; same-sheet; reviewer-correction; empty `{}` / omit keep                                              | ✅ nonempty vs `{}` vs omit; snapshot still copies current                                                                                                               | ✅ `_write_review_decision()` no extra_vals; `_editable_review_vals` deleted               |
| 2.4  | same                                       | Integration                                       | See Phase 2 command                                                                                                                              | ✅ Phase 1 RED rows                                                         | ✅ All payload/approve Phase 1 RED rows now pass                                                                                           | ➖ OWL remaining RED (Phase 3)                                                                                                                                           | ➖ None needed                                                                             |
| 3.1  | `tests/test_collection_document_review.py` | Integration (source-string OWL)                   | Phase 2 baseline: 745/749 pass; 3 OWL FAIL + ACL leftover-vals FAIL                                                                              | ✅ Phase 1 already wrote OWL XML/xpath asserts                              | ✅ Passed one readonly `ocr_*`; no seller/current/`t-on-*`; `.seller-warning` `role="status"` `aria-live="polite"`; dual bank/check groups | ✅ shared type/amount + bank block + check block; empty provenance still binds without OCR `t-if`                                                                        | ➖ Template already one-control-per-field                                                  |
| 3.2  | same                                       | Integration (source-string OWL)                   | Same baseline                                                                                                                                    | ✅ Phase 1 `_layerHasDocumentType` / approve RPC asserts                    | ✅ Passed OCR∪seller only; `onFieldInput` gone; `action_review_approve",[[this.current.id],sheetId]`                                       | ✅ `test_owl_keeps_type_visibility_*` + `test_owl_review_rpcs_pass_sheet_id_*` + `test_build_approve_vals_*`                                                             | ➖ Trailing comma stripped so compact regex matches; no extra extract                      |
| 3.3  | same                                       | Integration (source-string OWL)                   | Same baseline                                                                                                                                    | ✅ Phase 1 `assertNotIn("buildApproveVals")`                                | ✅ Passed; `hasSellerChangedField` + `formatSellerChangedValue` (Spanish labels, ISO date, amount 2dp, blank for nested `false`)           | ➖ Single: no Hoot; format helpers exercised by template wiring; triangulation is the three OWL source tests                                                             | ➖ Dropped unused rewrite helpers (`editableKeysForType` / `ormValue` / `isProvenanceKey`) |
| 3.4  | same + `tests/test_collection_acl.py`      | Integration (source-string OWL + TransactionCase) | Same baseline                                                                                                                                    | ✅ Phase 1 OWL GREEN gate; ACL leftover was known Phase 2 collateral        | ✅ Suite `0 failed, 0 error(s) of 749 tests`; `.seller-warning` uses `--rose`; ACL leftover vals keep `100.0`                              | ✅ OWL three source tests + ACL leftover-vals keep-path                                                                                                                  | ➖ None needed                                                                             |
| 4.2  | `tests/test_collection_company_migration.py` | Integration (disk/manifest)                    | Phase 3 baseline: 749/749                                                                                                                        | ✅ Written first: `test_manifest_version_is_1_36_0` + AGENTS metadata 1.36 while manifest still `19.0.1.35.0` | ✅ Passed after 4.1 bump                                                                                                                  | ✅ version string present; leftover tuple still forbids 1.35 and now 1.36; AGENTS not 1.34/1.35 Module metadata                                                          | ➖ Version constants only                                                                  |
| 4.1  | `__manifest__.py`                           | Integration (disk)                                | Same baseline                                                                                                                                    | ✅ 4.2 asserts required `"version": "19.0.1.36.0"`                         | ✅ Manifest bumped; receipt views kept; no `migrations/19.0.1.36.0/`                                                                      | ➖ Triangulation skipped: single unused version string, no branching                                                                                                     | ➖ Version string only                                                                     |
| 4.3  | same + scoped pre-commit                    | Integration                                       | See 4.3 commands                                                                                                                                 | ✅ Version/OWL asserts already written                                     | ✅ pre-commit exit **0**; suite `0 failed, 0 error(s) of 749 tests`                                                                       | ✅ focused suite + prettier trailing-comma regex still asserts `[[id], sheetId]` (no client vals)                                                                        | ✅ E501 wraps; approve regex `sheetId,?` to match prettier compact source                   |

### Test Summary

- **Total tests written this batch**: 0 new cases (4.2 retargeted existing version
  asserts; OWL compact regex optional comma). Suite still 749.
- **Total tests passing (suite)**: 749 of 749 (0 failed, 0 errors)
- **Layers used**: Integration (Odoo TransactionCase + OWL source-string + disk/manifest)
- **Approval tests** (refactoring): ACL leftover keep-path still green; approve RPC
  compact regex still requires `[[id], sheetId]` (optional prettier trailing comma)
- **Pure functions created**: 0 this batch (Phase 3 still has `hasSellerChangedField`,
  `formatSellerChangedValue`)

## Work Unit Evidence

| Evidence                                          | Required value                                                                                                                                                                                                                                                                                                             |
| ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `invoke test -m collection --mode=update` from `/home/crisd/projects/seedian/seedian` (db-filter default `^devel$`; invoke `-d` is `--debugpy`, not database). Exit code **0**. `0 failed, 0 error(s) of 749 tests`. Three OWL source tests GREEN; ACL leftover-vals GREEN.                                                |
| Runtime harness command/scenario and exact result | Same invoke `--mode=update` upgrades `collection` then runs TransactionCase + OWL source-string tests. Document Review OWL is source-asserted (no Hoot); approve path ignores leftover client vals.                                                                                                                        |
| Rollback boundary                                 | `static/src/document_review/document_review_action.xml`, `.esm.js`, `document_review_helpers.esm.js`, `document_review_action.scss`, plus the one ACL leftover-amount assertion and this change’s `tasks.md` / `apply-progress.md`. Do not revert Phase 1 tests, Phase 2 `collection_voucher.py`, or receipts dirty files. |

### Phase 3 GREEN (former Phase 2 still-RED OWL + ACL collateral)

PASS:

- `test_owl_keeps_type_visibility_hides_document_id_and_shows_provenance`
- `test_owl_review_rpcs_pass_sheet_id_from_action_params`
- `test_build_approve_vals_sends_current_keys_only`
- `test_owl_empty_provenance_still_loads` (keep-path)
- `test_internal_user_review_queue_and_approve_allowed` (leftover `{"amount": 150.0}`
  does not rewrite; current stays `100.0`)

### Phase 4 GREEN (manifest / AGENTS / verify)

| Evidence | Required value |
| --- | --- |
| Focused test command and exact result | `invoke test -m collection --mode=update` from `/home/crisd/projects/seedian/seedian`. Exit **0**. `0 failed, 0 error(s) of 749 tests`. `test_manifest_version_is_1_36_0` and `test_agents_md_four_state_workflow` GREEN. |
| Runtime harness command/scenario and exact result | Same invoke `--mode=update` upgrades `collection` (assets) then runs the suite. Scoped `pre-commit run --files` on this change’s collection + OpenSpec paths: exit **0** (pylint optional C8101 Eynes author warning only; hook Passed). |
| Rollback boundary | `__manifest__.py` version string, `tests/test_collection_company_migration.py` version asserts, `AGENTS.md` version + Document Review OWL notes, E501 wraps + approve `sheetId,?` regex in `tests/test_collection_document_review.py`, and this change’s `tasks.md` / `apply-progress.md`. Do not revert Phase 1–3 production OWL/voucher work or receipts dirty files. |

## Deviations from Design

None — implementation matches design (OCR-only readonly controls, OCR∪seller type
groups, ignore vals / no `buildApproveVals`, nested `false` formatted as blank,
`.seller-warning` `--rose`). Manifest is apply-time `19.0.1.36.0` with no migrate
folder. Approve compact regex now allows prettier’s trailing comma after `sheetId`
(still no client vals).

## Issues Found

- Scoped pre-commit first failed ruff E501 on Phase 1/3 review-test docstrings; wrapped
  those docstrings. Prettier trailing comma in `action_review_approve` compact source
  broke two OWL regexes; regex now matches rotation’s optional-comma pattern.
- Invoke `-d devel` is `--debugpy`, not a database flag. Used
  `invoke test -m collection --mode=update` (default db-filter `^devel$`).
- pylint optional C8101 (`manifest-required-author` Eynes) remains a warning; hook
  Passed.

## Workload / PR Boundary

- Mode: size:exception
- Current work unit: 4 (manifest `19.0.1.36.0` + AGENTS + verify)
- Boundary: starts at version asserts / manifest bump / AGENTS OWL note; ends when
  scoped pre-commit and `invoke test -m collection --mode=update` pass
- Estimated review budget impact: version strings + AGENTS bullets + pre-commit wraps

## Status

16/16 tasks complete (Phase 1 + Phase 2 + Phase 3 + Phase 4). Ready for verify.
