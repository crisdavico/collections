# Apply Progress: voucher-states-ui (Phase 1 + Phase 2 + Phase 3 + Phase 4)

**Change**: voucher-states-ui **Mode**: Strict TDD **Work unit**: 4 — Leftover AGENTS.md

- readme **Tasks**: 1.1–4.2 complete. All implementation work units finished.

## Completed Tasks

- [x] 1.1 RED `tests/test_collection_voucher.py`: default `draft`; seller action;
      intercept; unlink; attachment reopen.
- [x] 1.2 RED `tests/test_collection_mcp_tool.py` +
      `tests/test_collection_mcp_allocation.py`: MCP stamp `validated_seller`; all
      states may allocate.
- [x] 1.3 RED `tests/test_collection_company_migration.py`: manifest `19.0.1.31.0`;
      migrate folder; no leftover 1.26–1.30.
- [x] 1.4 GREEN `models/collection_voucher.py`: Selection + default draft;
      `action_validate_seller`; drop approve/reject; intercept; draft-only unlink; drop
      `group_expand`; attachment reopen.
- [x] 1.5 GREEN `tools/collection_voucher.py` stamp `"validated_seller"`;
      `tools/collection_allocation.py` drop rejected gate.
- [x] 1.6 GREEN `__manifest__.py` → `19.0.1.31.0`;
      `migrations/19.0.1.31.0/post-migrate.py` SQL CASE; no snapshot rewrite.
- [x] 1.7 Remap leftover old-key literals; `invoke install -m collection`; full
      `invoke test -m collection --mode=update` (602/602); scoped pre-commit.
- [x] 2.1 RED `tests/test_collection_document_review.py`: queue
      `validated_seller`+proof; Approve split write; no reject RPC.
- [x] 2.2 GREEN `models/collection_voucher.py`: queue/`_is_review_eligible` =
      `validated_seller` only; drop `action_review_reject`; split
      `_write_review_decision` (voucher `validated_collections`, snapshot
      `decision="approved"`).
- [x] 2.3 RED/GREEN drop `reject()` + Rechazar in
      `static/src/document_review/document_review_action.esm.js` + `.xml`; keep approve.
- [x] 2.4 Verify: `invoke install -m collection`; review/flag/ACL tests; scoped
      pre-commit.
- [x] 3.1 RED `tests/test_collection_ui.py`: delete stages kanban; `list,form`; keep
      reassign; filters; statusbar; no History; menu 10.
- [x] 3.2 GREEN `views/collection_views.xml` to match 3.1; drop
      History/`review_snapshot_ids`.
- [x] 3.3 RED/GREEN `tests/test_collection_mail.py` + `tracking=True` on
      seller/sheet/type/amount.
- [x] 3.4 RED/GREEN `tests/test_collection_sheet_report_data.py` print-includes new
      voucher keys.
- [x] 3.5 Verify: `invoke install -m collection`; ui/mail/report tests; scoped
      pre-commit.
- [x] 4.1 Replace leftover pending/approved/rejected voucher-state keys in `AGENTS.md`
      and `readme/DESCRIPTION.md`; lock migrate-folder rules to `19.0.1.31.0` (forbid
      adding 1.26–1.30; do not add a second 1.31 later).
- [x] 4.2 Verify: scoped pre-commit on those docs files from Seedian root. Harness N/A
      (docs-only).

## TDD Cycle Evidence

### Phase 1 (preserved)

| Task | Test File                                                                      | Layer                              | Safety Net                                           | RED                                                                           | GREEN                                                        | TRIANGULATE                                                            | REFACTOR                                    |
| ---- | ------------------------------------------------------------------------------ | ---------------------------------- | ---------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------- | ------------------------------------------- |
| 1.1  | `tests/test_collection_voucher.py`                                             | Integration (Odoo TransactionCase) | ✅ `TestCollectionVoucher` 0 failed / 42             | ✅ Written (focused 8-tag run 5 failed, 3 errors)                             | ✅ Passed                                                    | ✅ defaults + seller action + intercept + unlink + replace             | ✅ Clean                                    |
| 1.2  | `tests/test_collection_mcp_tool.py`, `tests/test_collection_mcp_allocation.py` | Integration                        | ✅ MCP attach + allocation + migration 0 failed / 60 | ✅ Written (`validated_seller` stamp; `test_all_voucher_states_may_allocate`) | ✅ Passed (10.0 apply so three states share overdue balance) | ✅ PNG nest + omit-nest; draft/seller/collections allocate             | ✅ Clean                                    |
| 1.3  | `tests/test_collection_company_migration.py`                                   | Integration                        | included in 60 above                                 | ✅ Written (`test_manifest_version_is_1_31_0`)                                | ✅ Passed                                                    | ✅ folder exists + CASE keys + no snapshot UPDATE                      | ➖ None needed                              |
| 1.4  | `models/collection_voucher.py`                                                 | Integration                        | same as 1.1                                          | ✅ 1.1 tests                                                                  | ✅ Passed                                                    | ✅ intercept collections vs seller vs reopen; first-attach keeps draft | ✅ attachment reset only when old+new proof |
| 1.5  | `tools/collection_voucher.py`, `tools/collection_allocation.py`                | Integration                        | same as 1.2                                          | ✅ 1.2 tests                                                                  | ✅ Passed                                                    | ✅ stamp + three-state allocate                                        | ➖ None needed                              |
| 1.6  | `__manifest__.py`, `migrations/19.0.1.31.0/post-migrate.py`                    | Integration                        | same as 1.3                                          | ✅ 1.3 tests                                                                  | ✅ Passed                                                    | ➖ Single (SQL CASE contract)                                          | ➖ None needed                              |
| 1.7  | leftover `tests/test_collection_*.py`                                          | Integration                        | full suite after remap                               | ✅ literals would crash ORM browse                                            | ✅ `invoke test -m collection --mode=update` 0 failed / 602  | ✅ review/ACL/mail/UI/report remaps                                    | ✅ first-attach vs replace                  |

### Phase 2

| Task | Test File                                                                                | Layer                              | Safety Net                                      | RED                                                                     | GREEN                                                                       | TRIANGULATE                                                                            | REFACTOR       |
| ---- | ---------------------------------------------------------------------------------------- | ---------------------------------- | ----------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | -------------- |
| 2.1  | `tests/test_collection_document_review.py`                                               | Integration (Odoo TransactionCase) | ✅ `TestCollectionDocumentReview` 0 failed / 50 | ✅ Written (`17 failed, 0 error(s) of 50 tests`)                        | ✅ 2.2/2.3 production                                                       | ✅ seller+proof queued vs draft+proof excluded; approve split; reject RPC gone         | ➖ tests only  |
| 2.2  | `models/collection_voucher.py` (+ leftover flag/ACL remaps)                              | Integration                        | same as 2.1                                     | ✅ 2.1 tests                                                            | ✅ Passed (`0 failed, 0 error(s) of 96` review+flag+ACL)                    | ✅ draft/unattached/collections refuse; reopen then second approve snapshot `approved` | ✅ split write |
| 2.3  | `static/src/document_review/document_review_action.esm.js`, `document_review_action.xml` | Integration (source asserts)       | included in 2.1                                 | ✅ OWL tests in 2.1 (`action_review_reject` / `Rechazar` still present) | ✅ Passed (same 96)                                                         | ✅ `Aprobar y seguir` / `approve()` remain; reject method and button gone              | ➖ None needed |
| 2.4  | install + review tests + scoped pre-commit                                               | Integration                        | n/a                                             | n/a                                                                     | ✅ `invoke install -m collection`; review 96/96; pre-commit after E501 wrap | ➖ Verify task                                                                         | ➖ None needed |

### Phase 3

| Task | Test File                                    | Layer                              | Safety Net                                     | RED                                                                                     | GREEN                                                                 | TRIANGULATE                                                                                          | REFACTOR                          |
| ---- | -------------------------------------------- | ---------------------------------- | ---------------------------------------------- | --------------------------------------------------------------------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | --------------------------------- |
| 3.1  | `tests/test_collection_ui.py`                | Integration (Odoo TransactionCase) | ✅ ui/mail/report `0 failed, 0 error(s) of 84` | ✅ Written (`15 failed, 1 error(s) of 91` before production)                            | ✅ 3.2 production                                                     | ✅ kanban gone vs reassign kept; list order vs optional-hide; state vs type filters; History vs keep | ✅ E501 docstring wrap            |
| 3.2  | `views/collection_views.xml`                 | Integration                        | same as 3.1                                    | ✅ 3.1 tests                                                                            | ✅ Passed (same 91 after GREEN)                                       | ✅ `<delete>` leftover stages kanban; `view_mode` `list,form`; statusbar `clickable: False`          | ➖ None needed                    |
| 3.3  | `tests/test_collection_mail.py`              | Integration                        | included in 84                                 | ✅ Written (amount/seller/sheet/type tracking failed; metadata ERROR then getattr FAIL) | ✅ Passed (`tracking=True` on four fields)                            | ✅ amount float vs seller Many2one vs sheet+type write                                               | ➖ getattr for missing `tracking` |
| 3.4  | `tests/test_collection_sheet_report_data.py` | Integration                        | included in 84                                 | ✅ Written (payload row `state` keys locked)                                            | ✅ Already passing — report already emits new keys from Phase 1 remap | ✅ include `draft`/`validated_seller`/`validated_collections`; exclude pending/approved/rejected     | ➖ None needed                    |
| 3.5  | install + ui/mail/report + scoped pre-commit | Integration                        | n/a                                            | n/a                                                                                     | ✅ `invoke install -m collection`; 91/91; pre-commit after E501       | ➖ Verify task                                                                                       | ➖ None needed                    |

### Phase 4

| Task | Test File                               | Layer | Safety Net                               | RED                                                                                                                               | GREEN                                                                                                                                                                                           | TRIANGULATE                                                                                  | REFACTOR                         |
| ---- | --------------------------------------- | ----- | ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | -------------------------------- |
| 4.1  | `AGENTS.md`, `readme/DESCRIPTION.md`    | Docs  | N/A (docs-only; no production test file) | ✅ Grep showed leftover voucher keys (`pending`/`approved`/`rejected` lifecycle, unlink pending, Approve/Reject, manifest 1.30.0) | ✅ Domain/UI/MCP/migrate prose remapped to `draft`/`validated_seller`/`validated_collections`; snapshot `decision` left `approved`/`rejected`                                                   | ➖ Skipped: docs-only prose remap; one intended wording; no branching or executable behavior | ✅ Prettier wrap on tables/prose |
| 4.2  | scoped pre-commit on the two docs files | Docs  | n/a                                      | n/a                                                                                                                               | ✅ `pre-commit run --files odoo/custom/src/private/collection/AGENTS.md odoo/custom/src/private/collection/readme/DESCRIPTION.md` → exit 0 (prettier, trailing whitespace, EOF, OCA README gen) | ➖ Verify task                                                                               | ➖ None needed                   |

### Test Summary

- **Total tests written**: Phase 4 added no tests (docs-only). Phase 3 added/retargeted
  Payment Vouchers UI (kanban delete, list columns, filters, statusbar, History drop,
  menu 10), chatter tracking on seller/sheet/type/amount, and report payload state keys.
- **Total tests passing (focused)**: Phase 4 N/A (docs). Phase 3 focused: 91
  (`TestCollectionUi` + `TestCollectionMail` + `TestCollectionSheetReportData`).
- **Layers used**: Unit (0), Integration (Odoo TransactionCase, Phases 1–3), E2E (0),
  Docs (Phase 4).
- **Approval tests** (refactoring): None — no dedicated refactoring tasks.
- **Pure functions created**: 0.

## Work Unit Evidence

### Phase 1 (preserved)

| Evidence                                          | Value                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `docker compose run --rm -e DB_FILTER='^devel$' odoo odoo --test-enable --stop-after-init --workers=0 -u collection --test-tags /collection:TestCollectionVoucher.test_defaults_on_create,/collection:TestCollectionVoucher.test_action_validate_seller_from_draft_does_not_stamp_reviewer,/collection:TestCollectionVoucher.test_action_reject_does_not_exist,/collection:TestCollectionVoucher.test_raw_write_validated_collections_refused,/collection:TestCollectionVoucher.test_replace_main_resets_to_validated_seller_clears_audit_and_rotation,/collection:TestCollectionMcpAttachment.test_create_omitting_nest_still_creates,/collection:TestCollectionMcpAllocation.test_all_voucher_states_may_allocate,/collection:TestCollectionCompanyMigration.test_manifest_version_is_1_31_0` → exit 0, `0 failed, 0 error(s) of 8 tests`. Full suite: `invoke test -m collection --mode=update` → exit 0, `0 failed, 0 error(s) of 602 tests`. |
| Runtime harness command/scenario and exact result | `invoke install -m collection` from Seedian root → exit 0; collection init/upgrade completed (`Modules loaded.`).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| Rollback boundary                                 | Revert `models/collection_voucher.py`, `tools/collection_voucher.py`, `tools/collection_allocation.py`, `__manifest__.py`, `migrations/19.0.1.31.0/`, `views/collection_views.xml` (button/filter remap only), and the Phase 1 test remaps. Does not include Phase 2 OWL/reject removal, Phase 3 kanban delete/History, or Phase 4 docs. Snapshot `decision` rows were never rewritten.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |

### Phase 2

| Evidence                                          | Value                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | Safety net: `--test-tags /collection:TestCollectionDocumentReview` → `0 failed, 0 error(s) of 50 tests`. RED after 2.1: same tags → `17 failed, 0 error(s) of 50 tests`. GREEN after 2.2+2.3: `--test-tags /collection:TestCollectionDocumentReview,/collection:TestCollectionDocumentReviewFlag,/collection:TestCollectionAcl` → exit 0, `0 failed, 0 error(s) of 96 tests`.                                                                                           |
| Runtime harness command/scenario and exact result | `invoke install -m collection` from Seedian root → exit 0; `Modules loaded.` Scoped pre-commit on Phase 2 files (after wrapping E501). Optional full `invoke test -m collection --mode=update` hit 8 failures / 11 errors of 604 (MCP debt totals, UniqueViolation, other-company sheet) plus a later `SerializationFailure` while loading `collection_connector_sqlite` against the restarted `seedian-odoo-1`; none were `TestCollectionDocumentReview` / Flag / ACL. |
| Rollback boundary                                 | Revert `models/collection_voucher.py` review queue/eligibility/`_write_review_decision`/`action_review_reject`, `static/src/document_review/document_review_action.esm.js`, `document_review_action.xml`, and the Phase 2 test remaps in `tests/test_collection_document_review.py`, `tests/test_collection_document_review_flag.py`, `tests/test_collection_acl.py`. Does not revert Phase 1 Selection/MCP/migrate or Phase 3 views/History.                           |

### Phase 3

| Evidence                                          | Value                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | Safety net: `--test-tags /collection:TestCollectionUi,/collection:TestCollectionMail,/collection:TestCollectionSheetReportData` → `0 failed, 0 error(s) of 84 tests`. RED after 3.1/3.3 tests: same tags → `15 failed, 1 error(s) of 91 tests`. GREEN after 3.2/3.3 production: same tags → exit 0, `0 failed, 0 error(s) of 91 tests`. Verify after install: same tags → exit 0, `0 failed, 0 error(s) of 91 tests`.                                                               |
| Runtime harness command/scenario and exact result | `invoke install -m collection` from Seedian root → exit 0; `Modules loaded.` Waited for the install one-off to finish before tests (`seedian-odoo-1` stopped by install; no overlapping suite). Scoped pre-commit on Phase 3 files passed after wrapping E501.                                                                                                                                                                                                                      |
| Rollback boundary                                 | Revert `views/collection_views.xml` (stages kanban `<delete>`, `view_mode` `list,form`, list columns, search filters, statusbar, History drop), `models/collection_voucher.py` `tracking=True` on `seller_id`/`sheet_id`/`document_type`/`amount`, and the Phase 3 test remaps in `tests/test_collection_ui.py`, `tests/test_collection_mail.py`, `tests/test_collection_sheet_report_data.py`. Does not revert Phase 1 Selection/MCP/migrate, Phase 2 review/OWL, or Phase 4 docs. |

### Phase 4

| Evidence                                          | Value                                                                                                                                                                                                                                                                                                                            |
| ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `pre-commit run --files odoo/custom/src/private/collection/AGENTS.md odoo/custom/src/private/collection/readme/DESCRIPTION.md` from `/home/crisd/projects/seedian/seedian` → exit 0. prettier + plugin-xml Passed; trim trailing whitespace Passed; fix end of files Passed; Generate addons README files from fragments Passed. |
| Runtime harness command/scenario and exact result | N/A — docs-only per tasks.md Unit 4 (`Runtime harness: N/A docs-only`). No module install or Odoo test run for this slice.                                                                                                                                                                                                       |
| Rollback boundary                                 | Revert `AGENTS.md`, `readme/DESCRIPTION.md`, and generated `README.rst` (oca-gen-addon-readme from the DESCRIPTION fragment). Does not revert Phase 1–3 application code, tests, or views.                                                                                                                                       |

## Files Changed

### Phase 1 (preserved)

| File                                                   | Action   | What Was Done                                                                            |
| ------------------------------------------------------ | -------- | ---------------------------------------------------------------------------------------- |
| `tests/test_collection_voucher.py`                     | Modified | RED/GREEN lifecycle: default draft, seller action, intercept, unlink, attachment replace |
| `tests/test_collection_mcp_tool.py`                    | Modified | MCP create asserts `validated_seller`                                                    |
| `tests/test_collection_mcp_allocation.py`              | Modified | All three states may allocate; dropped rejected-voucher gate coverage                    |
| `tests/test_collection_company_migration.py`           | Modified | Manifest 1.31.0 + migrate folder + CASE, no snapshot UPDATE                              |
| `models/collection_voucher.py`                         | Modified | New Selection; seller action; intercept; draft unlink; attachment replace; review bridge |
| `tools/collection_voucher.py`                          | Modified | Stamp `validated_seller`                                                                 |
| `tools/collection_allocation.py`                       | Modified | Drop `state == "rejected"` gate                                                          |
| `__manifest__.py`                                      | Modified | Version `19.0.1.31.0`                                                                    |
| `migrations/19.0.1.31.0/post-migrate.py`               | Created  | SQL CASE remap; leftover collapse; no snapshot rewrite                                   |
| `views/collection_views.xml`                           | Modified | Minimal header/filter/statusbar so `-u collection` loads after dropping approve/reject   |
| `tests/test_collection_ui.py`                          | Modified | Search filters + statusbar + no `group_expand`                                           |
| `tests/test_collection_acl.py`                         | Modified | Review voucher states; form Validate by Seller                                           |
| `tests/test_collection_document_review.py`             | Modified | Old voucher keys remapped; snapshot `decision` kept                                      |
| `tests/test_collection_document_review_flag.py`        | Modified | Draft after attach; seller action when review off                                        |
| `tests/test_collection_mail.py`                        | Modified | Track Draft → Validated by Seller                                                        |
| `tests/test_collection_payment.py`                     | Modified | Replace → `validated_seller`; unlink still draft                                         |
| `tests/test_collection_sheet.py`                       | Modified | `action_validate_seller` instead of form approve                                         |
| `tests/test_collection_sheet_report_data.py`           | Modified | Print includes draft/seller/collections                                                  |
| `tests/test_collection_allocation.py`                  | Modified | Default voucher state `draft`                                                            |
| `openspec/changes/voucher-states-ui/tasks.md`          | Modified | 1.1–1.7 `[x]`                                                                            |
| `openspec/changes/voucher-states-ui/apply-progress.md` | Created  | Phase 1 file                                                                             |

### Phase 2

| File                                                       | Action   | What Was Done                                                                                               |
| ---------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------- |
| `tests/test_collection_document_review.py`                 | Modified | RED/GREEN: queue `validated_seller`+proof only; approve split; no reject RPC; OWL source asserts            |
| `models/collection_voucher.py`                             | Modified | Queue/`_is_review_eligible` seller-only; drop `action_review_reject`; approve-only `_write_review_decision` |
| `static/src/document_review/document_review_action.esm.js` | Modified | Drop `reject()`; keep `approve()`/`runDecision`                                                             |
| `static/src/document_review/document_review_action.xml`    | Modified | Drop Rechazar; keep Aprobar y seguir                                                                        |
| `tests/test_collection_document_review_flag.py`            | Modified | Leftover: gated ops no longer include reject RPC                                                            |
| `tests/test_collection_acl.py`                             | Modified | Leftover: seller-validate for queue; reject RPC gone                                                        |
| `openspec/changes/voucher-states-ui/tasks.md`              | Modified | 2.1–2.4 `[x]`; Phase 3–4 still open                                                                         |
| `openspec/changes/voucher-states-ui/apply-progress.md`     | Modified | MERGE Phase 1 + Phase 2 evidence                                                                            |

### Phase 3

| File                                                   | Action   | What Was Done                                                                                       |
| ------------------------------------------------------ | -------- | --------------------------------------------------------------------------------------------------- |
| `tests/test_collection_ui.py`                          | Modified | RED/GREEN: stages kanban gone; `list,form`; list columns; filters; statusbar; History drop; menu 10 |
| `views/collection_views.xml`                           | Modified | `<delete>` leftover stages kanban; list/search/form/statusbar; drop History/`review_snapshot_ids`   |
| `tests/test_collection_mail.py`                        | Modified | RED/GREEN: chatter tracking on `seller_id`, `sheet_id`, `document_type`, `amount`                   |
| `models/collection_voucher.py`                         | Modified | `tracking=True` on seller/sheet/type/amount (`state` already tracked)                               |
| `tests/test_collection_sheet_report_data.py`           | Modified | Print-includes `draft`/`validated_seller`/`validated_collections`; exclude old keys                 |
| `openspec/changes/voucher-states-ui/tasks.md`          | Modified | 3.1–3.5 `[x]`; Phase 4 still open                                                                   |
| `openspec/changes/voucher-states-ui/apply-progress.md` | Modified | MERGE Phase 1 + Phase 2 + Phase 3 evidence                                                          |

### Phase 4

| File                                                   | Action   | What Was Done                                                                                         |
| ------------------------------------------------------ | -------- | ----------------------------------------------------------------------------------------------------- |
| `AGENTS.md`                                            | Modified | Leftover voucher-state keys → `draft`/`validated_seller`/`validated_collections`; migrate lock 1.31.0 |
| `readme/DESCRIPTION.md`                                | Modified | Lifecycle sentence remapped; no Reject; MCP stamp `validated_seller`                                  |
| `README.rst`                                           | Modified | Regenerated by oca-gen-addon-readme from DESCRIPTION (generated; not application code)                |
| `openspec/changes/voucher-states-ui/tasks.md`          | Modified | 4.1–4.2 `[x]`; all 18 tasks complete                                                                  |
| `openspec/changes/voucher-states-ui/apply-progress.md` | Modified | MERGE Phase 1 + Phase 2 + Phase 3 + Phase 4 evidence                                                  |

## Deviations from Design

### Phase 1 (preserved)

1. **Review queue / `_is_review_eligible` temporarily
   `state in ("draft", "validated_seller")`.** Design Phase 2 sets queue to
   `validated_seller` only. Dual keys keep Document Review tests green after Selection
   remap: new attached drafts stay reviewable, and attachment replace (→
   `validated_seller`) can still take a later review. Phase 2 must narrow to
   `validated_seller` and drop `action_review_reject`. **Superseded by Phase 2.**
2. **`_write_review_decision` already splits voucher vs snapshot.** Voucher
   `approved`→`validated_collections`, `rejected`→`draft`; snapshot `decision` stays
   `approved`/`rejected`. Phase 2 still owns dropping reject RPC/OWL. **Phase 2 dropped
   the rejected branch; approve-only split remains.**
3. **Minimal `views/collection_views.xml` remap** (filters, Validate by Seller button,
   no Reject, statusbar keys) so module upgrade can parse after dropping
   `action_approve`/`action_reject`. Kanban delete, History tab, list columns, and
   clickable statusbar remain Phase 3. **Superseded by Phase 3.**
4. **First designated-proof attach does not stamp `validated_seller`.** Only replacement
   (`old_id` and `new_id` both set) reopens to seller and clears audit. Matches design
   “attachment replace”; first attach keeps `draft` so form Validate by Seller still
   runs.

### Phase 2

None — implementation matches design. Queue and `_is_review_eligible` are
`validated_seller` only (Phase 1 dual-key bridge removed). `_write_review_decision`
writes voucher `validated_collections` then `_append_review_snapshot("approved")`.
`action_review_reject` and OWL `reject()` / Rechazar are gone. Leftover flag/ACL tests
were remapped so dropping the RPC does not leave AttributeError outside the assigned
review file.

### Phase 3

None — implementation matches design. Stages kanban is search-`<delete>`d (fresh install
safe); `view_mode` is `list,form`; Reassign kanban remains; list visible order matches
the spec; statusbar is not clickable; History/`review_snapshot_ids` are gone; chatter
kept. `tracking=True` on `seller_id`, `sheet_id`, `document_type`, `amount`. Report
payload already included the new voucher keys; 3.4 locked that with include/exclude
assertions (no report production change).

### Phase 4

None — documentation matches design. Snapshot `decision` vocabulary left
`approved`/`rejected`. SQL remap source keys remain only in the 1.31.0 migrate-folder
description. Main OpenSpec specs and application code were not edited.

## Issues Found

Phase 4 scoped pre-commit is green (exit 0). First sandboxed pre-commit failed writing
`~/.cache/pre-commit`; re-ran unsandboxed. `oca-gen-addon-readme` regenerated
`README.rst` from `readme/DESCRIPTION.md`. Did not settle the attempt token.

Phase 3 focused ui/mail/report tests are green (91/91). `invoke install -m collection`
stopped `seedian-odoo-1` then ran a one-off; tests waited until that finished. Did not
run a second overlapping full suite.

Phase 2 optional full-suite note preserved: 8 failures / 11 errors of 604 plus a later
`SerializationFailure` loading `collection_connector_sqlite` against a restarted
`seedian-odoo-1`; none were Document Review / Flag / ACL.

## Remaining Tasks

None. All 18 tasks in `tasks.md` are `[x]`. All implementation work units finished.

## Workload / PR Boundary

- Mode: stacked PR slice (auto-chain / stacked-to-main)
- Current work unit: Unit 4 / PR 4
- Boundary: leftover `AGENTS.md` + `readme/DESCRIPTION.md` (plus generated
  `README.rst`); stop before verify/archive. Did not change application code, tests,
  views, or Phase 1–3 behavior.
- Estimated review budget impact: High original forecast; this slice is the autonomous
  Phase 4 docs unit only

## Post-verify coexistence (sibling `allocation-customer-debt`)

Verify FAIL named six tests. Sibling Phase 4 still owns `collection_voucher.py` detach
(`_projected_residual` / leftover-voucher residual). This slice did **not** edit
allocation models, MCP tools, `19.0.1.32.0`, or that detach GREEN.

- List: `reviewed_by` / `reviewed_at` as `optional="hide"` so Document Review Flag views
  still expose audit columns without changing visible column order.
- Voucher residual fixtures: seed `line_ids` so residual is debt−applied (50 / 100 / 80)
  while leftover detach still subtracts voucher amount.

Focused one-off (`docker compose run --rm … --test-tags` those six methods +
`TestCollectionUi.test_list_hides_optional_and_currency_columns`):
`0 failed, 0 error(s) of 7 tests`. Did not re-run full verify while sibling Phase 4 is
open.

## Post-verify remediations (leftover residual + sqlite)

Sibling `allocation-customer-debt` is archived. Production leftover residual is
`debt − applied` with no `_projected_residual`. Refresh verify FAIL was sqlite leftover
`customer_identification` / `pending` plus three stale refuse scenarios in this change's
delta.

- Delta `collection-vouchers`: leftover residual aligned with main spec (unlink and
  partner-write MUST NOT refuse leftover residual 0 / underflow).
- `collection_connector_sqlite` rollback test: ORM create uses `partner_id` + `draft`;
  retired `create_collection_vouchers` MCP is asserted absent.
