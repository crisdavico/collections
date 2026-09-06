# Apply Progress: align-allocation-contracts

**Change**: align-allocation-contracts **Mode**: Strict TDD (Phases 1–3) + Standard
(Phase 4 docs-only; no new production behavior) **Slice**: Phase 1 tasks 1.1–1.6 (RED) +
Phase 2 tasks 2.1–2.6 (GREEN catalog/migrate) + Phase 3 tasks 3.1–3.5 (GREEN strict
parser/MCP schema) + Phase 4 tasks 4.1–4.4 (docs) + remediating queue-payload
`retention_kind` **Delivery**: auto-chain / stacked-to-main **Harness**: reused
`seedian-odoo-1` (no stack rebuild)

Phases 1–3 did not edit nebula-agent. Phase 4 edits only the catalog note in
nebula-agent `AGENTS.md` (no `src/agent/**`, no PRD). Sibling change
`2026-09-04-document-review-editable-ocr` was not touched. Parser/catalog production
code was not re-implemented in Phase 4. Remediating slice did not edit nebula-agent,
`collection_receipt_proposal`, or `static/src/document_review/**`.

## Completed Tasks

- [x] 1.1 Catalog seven XMLIDs + new-company seven + `UNIQUE(code)`
- [x] 1.2 Manifest `19.0.1.40.0` + leftover `19.0.1.39.0` + union migrate
- [x] 1.3 ORM persist echeck/cash/retention_certificate + cash without proof
- [x] 1.4 Six dump types persist draft; `unsupported` zero writes
- [x] 1.5 `image/jpg` alias; cash omit/null proof; JSON null omit; type-foreign
      UserError
- [x] 1.6 Extra keys UserError; decimal-string receipts; `retention_kind` stamps
- [x] 2.1 XMLIDs `document_type_echeck`, `document_type_cash`,
      `document_type_retention_certificate`
- [x] 2.2 `COLLECTION_TYPE_CODES` expanded to seven; helper docstring “seven”
- [x] 2.3 Voucher seven-type Selection; `_RETENTION_KIND_SELECTION`; `retention_kind` +
      ocr/seller copies; `_REVIEW_EDITABLE_FIELD_ORDER`
- [x] 2.4 Snapshot seven-type Selection + `retention_kind`
- [x] 2.5 Manifest `19.0.1.40.0`; `migrations/19.0.1.40.0/post-migrate.py` calls
      `_collection_enable_all_document_types()` only
- [x] 2.6 Upgrade `-u collection`; 1.1–1.3 GREEN; 1.4–1.6 still RED
- [x] 3.1 `tools/collection_voucher.py`: type-owned maps; seven-type schema; amount
      number|string normalizer; MIME `image/jpg` alias
- [x] 3.2 Strict parse: extra=forbid; type-foreign reject; null/`""` omit; cash no
      proof; `YYYY-MM-DD`; check date order; keep `unsupported` reject
- [x] 3.3 `tools/collection_allocation.py`: receipt amounts reuse voucher normalizer;
      advertised schema stays MuK-safe `number`
- [x] 3.4 Upgrade `-u collection`; 1.4–1.6 GREEN; existing allocation tests still pass
- [x] 3.5 `pre-commit run --files` collection
      models/tools/data/migrations/tests/`__manifest__.py`
- [x] 4.1 Collection `AGENTS.md`: catalog 7; `19.0.1.40.0`; union-all migrate;
      `retention_kind`; MCP still rejects `unsupported`; keep `migrations/19.0.1.39.0/`
      MUST NOT exist
- [x] 4.2 `readme/DESCRIPTION.md`: seven types including echeck, cash,
      retention_certificate
- [x] 4.3 Nebula `AGENTS.md`: replace catalog-blocker with Seedian `19.0.1.40.0` factual
      note
- [x] 4.4 `pre-commit run --files` the three docs paths (seedian root + nebula path)

## Files Changed

### Phase 1 (RED goldens; preserved)

| File                                         | Action   | What Was Done                                                                                 |
| -------------------------------------------- | -------- | --------------------------------------------------------------------------------------------- |
| `tests/test_collection_company_settings.py`  | Modified | Seven XMLIDs (`Echeck`/`Cash`/`Retention Certificate`); seven-type company asserts            |
| `tests/test_collection_company_migration.py` | Modified | `19.0.1.40.0` leftover-folder + `test_upgrade_140_unions_three_types_keeps_extras`            |
| `tests/test_collection_voucher.py`           | Modified | Selection seven codes; persist echeck/cash/retention; cash without proof                      |
| `tests/test_collection_mcp_allocation.py`    | Modified | Inline dump goldens; extra keys; decimal-string receipts; unsupported zero writes             |
| `tests/test_collection_mcp_tool.py`          | Modified | JPEG fixture; `image/jpg`; cash omit/null; type-foreign; nest extras; `retention_kind` stamps |

### Phase 2 (GREEN catalog / migrate)

| File                                           | Action   | What Was Done                                                                                                                                            |
| ---------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `data/collection_document_type_data.xml`       | Modified | Added echeck/cash/retention_certificate XMLIDs; kept four existing + seed function                                                                       |
| `models/res_company.py`                        | Modified | Seven `COLLECTION_TYPE_CODES`; docstring four→seven; `Command.link` helper unchanged                                                                     |
| `models/collection_voucher.py`                 | Modified | Seven `_DOCUMENT_TYPE_SELECTION`; `_RETENTION_KIND_SELECTION`; current/ocr/seller `retention_kind`; ocr*/seller* document_type share the seven-type list |
| `models/collection_voucher_review_snapshot.py` | Modified | Same seven-type Selection + `retention_kind`                                                                                                             |
| `__manifest__.py`                              | Modified | Version `19.0.1.40.0`                                                                                                                                    |
| `migrations/19.0.1.40.0/post-migrate.py`       | Created  | `env["res.company"].search([])._collection_enable_all_document_types()`; no seed helper                                                                  |
| `tests/test_collection_company_migration.py`   | Modified | Pre-existing union/create-hook asserts now expect `SEVEN_TYPE_CODES` (helper unions all catalog codes)                                                   |

### Phase 3 (GREEN parser / schema; this slice)

| File                                                            | Action   | What Was Done                                                                                                                                                                                                                                                                 |
| --------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tools/collection_voucher.py`                                   | Modified | `_TYPE_OWNED_FIELDS` + seven `_DOCUMENT_TYPES`; flattened nest schema from that map (incl. `retention_kind`); `_collection_normalize_amount` / ISO date / MIME jpg↔jpeg alias; extra=forbid on payment/nests/attachment; type-foreign reject; keep `unsupported` write reject |
| `tools/collection_allocation.py`                                | Modified | Receipt/value/application extra=forbid; amount/`balance_seen`/`amount_applied` reuse `_collection_normalize_amount`; `**kwargs` rejects request extras; keep `currency.compare_amounts`                                                                                       |
| `tests/test_collection_mcp_tool.py`                             | Modified | Distinct `request_id` on cash omit vs null so triangulation is two persists; E501 docstring wrap                                                                                                                                                                              |
| `tests/test_collection_mcp_allocation.py`                       | Modified | E501 wrap on extra-receipt payload line only                                                                                                                                                                                                                                  |
| `openspec/changes/align-allocation-contracts/tasks.md`          | Modified | Marked 3.1–3.5 `[x]`                                                                                                                                                                                                                                                          |
| `openspec/changes/align-allocation-contracts/apply-progress.md` | Updated  | MERGE Phase 1 + 2 + 3 evidence                                                                                                                                                                                                                                                |

### Phase 4 (docs; this slice)

| File                                                            | Action      | What Was Done                                                                                                                                                                                                                                                         |
| --------------------------------------------------------------- | ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AGENTS.md`                                                     | Modified    | Catalog seven codes; manifest `19.0.1.40.0`; `migrations/19.0.1.40.0/` union-all via `_collection_enable_all_document_types` (extras kept); pin `migrations/19.0.1.39.0/` MUST NOT exist; `retention_kind` on voucher/snapshot; MCP write still rejects `unsupported` |
| `readme/DESCRIPTION.md`                                         | Modified    | Seven types including echeck, cash, retention_certificate                                                                                                                                                                                                             |
| `README.rst`                                                    | Regenerated | OCA `oca-gen-addon-readme` hook from DESCRIPTION.md                                                                                                                                                                                                                   |
| `tests/test_collection_company_migration.py`                    | Modified    | AGENTS.md pin `Module metadata \`19.0.1.40.0\``; `assertNotIn` leftover 1.38.0/1.39.0 metadata                                                                                                                                                                        |
| `/home/crisd/projects/nebula/nebula-agent/AGENTS.md`            | Modified    | Replaced catalog-blocker paragraph with Seedian `19.0.1.40.0` catalog/Selection/allow-list note; no `src/agent/**`; no oneOf claim                                                                                                                                    |
| `openspec/changes/align-allocation-contracts/tasks.md`          | Modified    | Marked 4.1–4.4 `[x]`                                                                                                                                                                                                                                                  |
| `openspec/changes/align-allocation-contracts/apply-progress.md` | Updated     | MERGE Phase 1 + 2 + 3 + 4 evidence                                                                                                                                                                                                                                    |

## TDD Cycle Evidence

RED was Phase 1 (executed fail). GREEN executed this slice against those goldens.
Catalog GREEN remains Phase 2.

| Task    | Test File                                     | Layer       | Safety Net                       | RED                        | GREEN                                                    | TRIANGULATE                                | REFACTOR                       |
| ------- | --------------------------------------------- | ----------- | -------------------------------- | -------------------------- | -------------------------------------------------------- | ------------------------------------------ | ------------------------------ |
| 1.1     | `tests/test_collection_company_settings.py`   | Integration | ✅ existing catalog tests        | ✅ Executed fail (Phase 1) | ✅ 5/5 pass Phase 2                                      | ✅ xmlids + count + new company            | ➖ None needed                 |
| 1.2     | `tests/test_collection_company_migration.py`  | Integration | ✅ leftover-folder 1.28–1.38     | ✅ Executed fail (Phase 1) | ✅ manifest + 1.40.0 union pass                          | ✅ version + migrate file + extras         | ➖ None needed                 |
| 1.3     | `tests/test_collection_voucher.py`            | Integration | ✅ existing voucher create       | ✅ Executed fail (Phase 1) | ✅ selection + persist + cash no proof pass              | ✅ three types + cash no proof             | ➖ None needed                 |
| 1.4     | `tests/test_collection_mcp_allocation.py`     | Integration | ✅ existing MCP `_call`          | ✅ Executed fail (Phase 1) | ✅ six dumps + unsupported pass this slice               | ✅ six types + unsupported zero writes     | ➖ Maps + shared normalizer    |
| 1.5     | `tests/test_collection_mcp_tool.py`           | Integration | ✅ attachment/provenance classes | ✅ Executed fail (Phase 1) | ✅ jpg alias + cash omit/null + type-foreign pass        | ✅ jpg vs jpeg; omit vs null               | ➖ MIME helper                 |
| 1.6     | MCP test modules                              | Integration | ✅ receipt/provenance helpers    | ✅ Executed fail (Phase 1) | ✅ extra keys + decimal receipts + retention stamps pass | ✅ request/payment/receipt/value/app/nests | ➖ extra=forbid helper         |
| 2.1–2.6 | catalog/migrate                               | Integration | ✅ Phase 1 RED                   | ✅ Phase 1                 | ✅ Phase 2                                               | ➖ Phase 1 cases                           | ➖ None needed                 |
| 3.1     | `tools/collection_voucher.py`                 | Integration | ✅ 1.4–1.6 RED then GREEN        | ✅ Phase 1                 | ✅ schema/maps used by goldens                           | ✅ seven types + jpg + amounts             | ➖ One map drives schema+parse |
| 3.2     | same goldens                                  | Integration | ✅ existing MCP                  | ✅ Phase 1                 | ✅ extra/type-foreign/dates                              | ✅ extra keys at every nest                | ➖ Shared reject helper        |
| 3.3     | `test_decimal_string_receipt_amounts_persist` | Integration | ✅ existing receipts             | ✅ Phase 1                 | ✅ decimal-string receipts pass                          | ✅ number and string amounts               | ➖ Reuse normalizer            |
| 3.4     | focused docker `-u collection` + test-tags    | Integration | ✅ 100 existing+golden tests     | ✅ Phase 1                 | ✅ 0 failed, 0 error(s) of 10 then 100                   | n/a                                        | n/a                            |
| 3.5     | pre-commit                                    | Lint        | n/a                              | n/a                        | ✅ hooks Passed                                          | ➖ Single                                  | ➖ E501 wraps                  |

Phase 4 is Standard docs-only (no RED production tests). Pin tests below are
documentation assertions, not new goldens.

### Test Summary

- **Total tests written this slice**: 0 new goldens (Phase 1 owns RED). One harness fix:
  distinct `request_id` on cash omit vs null.
- **Focused GREEN (1.4–1.6)**: `0 failed, 0 error(s) of 10 tests`.
- **Representative existing suite**: `0 failed, 0 error(s) of 100 tests`
  (`TestCollectionMcpAllocation` + `TestCollectionMcpAttachment` +
  `TestCollectionMcpProvenance` + `TestCollectionMcpPartnerResolve` +
  `TestCollectionAllocationDocumentKind`).
- **Layers used**: Integration (Odoo `TransactionCase`)
- **Approval tests**: None — no refactoring-only tasks
- **Pure functions created**: `_collection_normalize_amount`,
  `_collection_normalize_iso_date`, `_collection_normalize_mimetype`,
  `_collection_reject_unknown_keys`, `_provenance_nest_schema`

### GREEN evidence (Phase 2 catalog; unchanged)

| Test                                                 | Result |
| ---------------------------------------------------- | ------ |
| `test_catalog_xmlids_exist_with_expected_codes`      | PASS   |
| `test_catalog_has_exactly_seven_seeded_types`        | PASS   |
| `test_catalog_duplicate_code_raises_integrity_error` | PASS   |
| `test_env_company_allows_all_seven_document_types`   | PASS   |
| `test_new_company_enables_all_seven_document_types`  | PASS   |
| `test_manifest_version_is_1_40_0`                    | PASS   |
| `test_upgrade_140_unions_three_types_keeps_extras`   | PASS   |
| `test_document_type_selection_includes_seven_codes`  | PASS   |
| `test_persist_echeck_cash_and_retention_certificate` | PASS   |
| `test_cash_persists_without_proof`                   | PASS   |

### GREEN evidence (Phase 3 parser; this slice)

| Test                                                        | Result |
| ----------------------------------------------------------- | ------ |
| `test_six_dump_types_persist_draft_with_decimal_strings`    | PASS   |
| `test_unsupported_dump_raises_with_zero_writes`             | PASS   |
| `test_extra_keys_on_request_payment_receipt_value_rejected` | PASS   |
| `test_decimal_string_receipt_amounts_persist`               | PASS   |
| `test_image_jpg_aliases_to_jpeg`                            | PASS   |
| `test_cash_omit_and_null_attachment_raw_ocr`                | PASS   |
| `test_type_foreign_nest_fields_rejected`                    | PASS   |
| `test_json_null_optional_nest_fields_are_omit`              | PASS   |
| `test_extra_keys_on_nests_rejected`                         | PASS   |
| `test_retention_kind_stamps_current_seller_and_ocr_layers`  | PASS   |

Upgrade this slice:
`-u collection --stop-after-init --http-port=18069 --gevent-port=18072` exit 0.

## Work Unit Evidence

| Evidence                         | Value                                                                                                                                                                                                                                                                                                                                                                                                       |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command             | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --test-enable --stop-after-init --workers=0 --http-port=18069 --gevent-port=18072 --log-level=test --test-tags` the ten 1.4–1.6 methods. Exit 0. `0 failed, 0 error(s) of 10 tests`. Log sha256 `8ed3fddc95063dc4ca52f176a6e9798df63e281d7cee388e292e731860f32c77`                                                                               |
| Runtime harness command/scenario | Reused running `seedian-odoo-1`. `-u collection --stop-after-init --http-port=18069 --gevent-port=18072` then the 100-test representative suite (`TestCollectionMcpAllocation` / Attachment / Provenance / PartnerResolve / DocumentKind). Exit 0. `0 failed, 0 error(s) of 100 tests`. Log sha256 `7544cf4c2c34646af1ea40e2f6bc1f3cdebdd00fbde3abdf53c78d65b268b3ff`. Host `invoke test` cannot bind 8069. |
| Rollback boundary                | Revert `tools/collection_voucher.py`, `tools/collection_allocation.py`, and the cash `request_id` / E501 wraps in the two MCP test files. Do not revert Phase 1 goldens, catalog XML, Selection, or `migrations/19.0.1.40.0/`.                                                                                                                                                                              |

## Work Unit Evidence (Phase 4 docs; this slice)

| Evidence                         | Value                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Focused test command             | From seedian root: `pre-commit run --files odoo/custom/src/private/collection/AGENTS.md odoo/custom/src/private/collection/readme/DESCRIPTION.md /home/crisd/projects/nebula/nebula-agent/AGENTS.md` (also included `tests/test_collection_company_migration.py`). Exit 0. All applicable hooks Passed (`prettier`, `ruff`, `pylint_odoo`, `oca-gen-addon-readme`).                                                                                                                              |
| Runtime harness command/scenario | Docs-only; N/A for a new runtime boundary. Extra pin: reused `seedian-odoo-1` with `-u collection --test-enable --stop-after-init --workers=0 --http-port=18069 --gevent-port=18072 --test-tags /collection:TestCollectionCompanyMigration.test_agents_md_four_state_workflow,/collection:TestCollectionCompanyMigration.test_readme_description_four_state_workflow`. Exit 0. `0 failed, 0 error(s) of 2 tests`. Log sha256 `4aa548c44be0a132d0622f321fe4b6c030351e78053bb473175525b9ac2e7d4b`. |
| Rollback boundary                | Revert collection `AGENTS.md`, `readme/DESCRIPTION.md`, generated `README.rst`, the AGENTS.md version pin lines in `tests/test_collection_company_migration.py`, and the catalog paragraph in nebula-agent `AGENTS.md`. Do not revert Phases 1–3 parser/catalog/migrate.                                                                                                                                                                                                                         |

## Workload / PR Boundary

- Mode: stacked PR slice (PR 3 docs)
- Current work unit: Phase 4 catalog-seven documentation (tasks 4.1–4.4)
- Boundary: collection `AGENTS.md`, `readme/DESCRIPTION.md` (+ generated `README.rst`),
  AGENTS.md version pin in `tests/test_collection_company_migration.py`, nebula-agent
  `AGENTS.md` catalog paragraph only. Land PR 3 after this slice. Stacked-to-main after
  PR 2 parser.
- Estimated review budget: docs slice is well under 400 authored lines (catalog note +
  type list + version pins; prettier re-padded the AGENTS.md map table).

## Deviations from Design

MuK `to_strict_schema` strips `anyOf` and `additionalProperties`. Advertised amount
fields stay `"type": "number"` (nullable on nests) so `inputSchema` still equals the
source constants. Runtime `_collection_normalize_amount` accepts JSON number or decimal
string and rejects bool/NaN/Inf. Extra=forbid is Python-side, not JSON Schema
`additionalProperties`. Behavior matches the dump contract; discovery stays MuK-safe.

## Issues Found

- Host `invoke test` collides with the running Odoo HTTP port; focused docker
  `--http-port=18069` remains the working command.
- `--test-enable` without `-u collection` loads 0 `at_install` tests on an
  already-installed DB.
- `test_cash_omit_and_null_attachment_raw_ocr` used one default `request_id` for two
  persists; after cash became allocatable the second call replayed and KeyError'd.
  Distinct `request_id`s restore omit-vs-null triangulation without loosening asserts.

## Remaining Tasks

None. All implementation tasks 1.1–4.4 are `[x]`. Remediating queue-payload slice
complete. Ready for verify.

## Remediating slice: Document Review queue `retention_kind`

**Work unit**: Emit current `retention_kind` on Document Review queue payload. **Failed
verify evidence**:
`sha256:f3712202f53f977b392bb7e496e811689d914f20d9a90a9eafca0a68a6727656` **Failed
candidate tree**: `5edbcf8e165800c36eea6a4951fbcc5eecac8998` (this correction no longer
matches that tree). **Root cause**: `_review_queue_payload` hardcoded current editable
keys and omitted `retention_kind` after `_REVIEW_EDITABLE_FIELD_ORDER` gained that
field. ocr*/seller* copies already looped `_REVIEW_EDITABLE_FIELDS`.

### Files Changed (this slice)

| File                                                            | Action   | What Was Done                                                                                                                                |
| --------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `models/collection_voucher.py`                                  | Modified | `_review_queue_payload` keeps metadata keys then fills current editable keys from `_REVIEW_EDITABLE_FIELD_ORDER` (includes `retention_kind`) |
| `tests/test_collection_document_review.py`                      | Modified | Optional `assertIn(name, payload, name)` before reading current in `_assert_empty_payload_provenance`                                        |
| `openspec/changes/align-allocation-contracts/apply-progress.md` | Updated  | MERGE remediating TDD + work-unit evidence; 1.1–4.4 stay `[x]`                                                                               |

No new `tasks.md` checkbox. Did not expand `_REVIEW_EDITABLE_FIELD_ORDER`. Did not add
OWL assertions.

### TDD Cycle Evidence (remediating queue payload)

| Task                   | Test File                                  | Layer       | Safety Net                                             | RED                                                                                                       | GREEN                                                                                           | TRIANGULATE                                                                                                                                              | REFACTOR                                           |
| ---------------------- | ------------------------------------------ | ----------- | ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| Queue `retention_kind` | `tests/test_collection_document_review.py` | Integration | ✅ Re-ran existing focused test before production edit | ✅ `0 failed, 1 error(s) of 1 tests` — `KeyError: 'retention_kind'` in `_assert_empty_payload_provenance` | ✅ Focused `0 failed, 0 error(s) of 1 tests`; `/collection` `0 failed, 0 error(s) of 779 tests` | ✅ Existing covering tests: empty provenance vs populated `_assert_payload_layer` (same method) plus `test_queue_check_and_cash_deposit_provenance_keys` | ➖ None needed — order loop is the production form |

### Work Unit Evidence (remediating queue payload)

| Evidence                         | Value                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command             | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --test-enable --stop-after-init --workers=0 --http-port=18069 --gevent-port=18072 --log-level=test --test-tags /collection:TestCollectionDocumentReview.test_queue_includes_readonly_provenance_without_fabricating`. RED exit 0 process with `0 failed, 1 error(s) of 1 tests`. GREEN exit 0. `0 failed, 0 error(s) of 1 tests`. GREEN log sha256 `e5f6a59b999a6fa8730bafddd02434323a5490ff8a85826c4cf778b8bf1b4f49`. |
| Runtime harness command/scenario | Reused running `seedian-odoo-1`. Same docker `-u collection --test-enable --test-tags /collection`. Exit 0. `0 failed, 0 error(s) of 779 tests` (`collection: 849 tests` stats line). Log sha256 `8a8b6d50a56fd6b6005ae55f8f90ebfb277fb23ae602eec5dc8840c274682d8b`. Host `invoke test` cannot bind 8069. Sibling `collection_receipt_proposal` not run.                                                                                                                          |
| Rollback boundary                | Revert the `_review_queue_payload` loop in `models/collection_voucher.py` and the `assertIn` in `tests/test_collection_document_review.py`. Do not revert Phases 1–4 catalog/parser/docs.                                                                                                                                                                                                                                                                                         |

### Test Summary (this slice)

- **Total tests written**: 0 new goldens. Existing RED test is the covering test; one
  `assertIn` hardening.
- **Focused GREEN**: `0 failed, 0 error(s) of 1 tests`.
- **Full `/collection`**: `0 failed, 0 error(s) of 779 tests`.
- **Layers used**: Integration (Odoo `TransactionCase`)
- **Approval tests**: None
- **Pure functions created**: 0
- **Triangulation skipped?** No — noted as existing empty-vs-populated covering tests,
  not a third suite.
