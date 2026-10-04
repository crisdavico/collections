# Tasks: Align Allocation Contracts

## Review Workload Forecast

| Field                   | Value                                  |
| ----------------------- | -------------------------------------- |
| Estimated changed lines | 550–750 authored                       |
| 400-line budget risk    | High                                   |
| Chained PRs recommended | Yes                                    |
| Suggested split         | PR 1 catalog → PR 2 parser → PR 3 docs |
| Delivery strategy       | auto-chain                             |
| Chain strategy          | stacked-to-main                        |

Decision needed before apply: No Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

### Suggested Work Units

| Unit | Goal                                        | Likely PR | Focused test command                      | Runtime harness                        | Rollback boundary                                                                       |
| ---- | ------------------------------------------- | --------- | ----------------------------------------- | -------------------------------------- | --------------------------------------------------------------------------------------- |
| 1    | Catalog 7 + `retention_kind` + 1.40.0 union | PR 1      | `invoke test -m collection --mode=update` | `-u collection --stop-after-init`      | XML, voucher/snapshot/`res_company`, manifest, `migrations/19.0.1.40.0/`, tests 1.1–1.3 |
| 2    | Strict dump parse; six MCP types persist    | PR 2      | `invoke test -m collection --mode=update` | N/A — TransactionCase; e2e unavailable | `tools/collection_voucher.py`, `tools/collection_allocation.py`, tests 1.4–1.6          |
| 3    | Catalog-7 docs                              | PR 3      | `pre-commit run --files` the three docs   | N/A — docs-only                        | collection `AGENTS.md`, `readme/DESCRIPTION.md`, nebula-agent `AGENTS.md`               |

Land PR 1 only after 1.1–1.3 GREEN. Stack PR 2 then PR 3.

## Phase 1: RED golden/contract tests

Inline dumps; no nebula import.

- [x] 1.1 `tests/test_collection_company_settings.py`: seven XMLIDs
      (`echeck`/`cash`/`retention_certificate`); new companies enable all seven;
      `UNIQUE(code)`.
- [x] 1.2 `tests/test_collection_company_migration.py`: manifest `19.0.1.40.0`; migrate
      folder; union three types, keep extras (not empty-only). Keep 1.39.0
      leftover-folder.
- [x] 1.3 `tests/test_collection_voucher.py`: ORM persist
      `echeck`/`cash`/`retention_certificate` + `retention_kind`; cash without proof.
- [x] 1.4 `tests/test_collection_mcp_allocation.py`: six dumps persist draft
      `{sheet_id,vouchers,allocation}` with decimal-string amounts; `unsupported`
      UserError, zero writes.
- [x] 1.5 `tests/test_collection_mcp_tool.py`: `image/jpg`→jpeg; cash omit/null
      attachment+`raw_ocr`; JSON null omit; type-foreign nest UserError.
- [x] 1.6 Extra keys on request/payment/receipt/value/nests UserError; decimal-string
      receipt amounts; `retention_kind` stamps current/`seller_*`/`ocr_*`.

## Phase 2: GREEN catalog/types/migration

- [x] 2.1 Add XMLIDs `document_type_echeck`, `_cash`, `_retention_certificate` in
      `data/collection_document_type_data.xml`.
- [x] 2.2 Expand `COLLECTION_TYPE_CODES` in `models/res_company.py` to seven.
- [x] 2.3 `models/collection_voucher.py`: seven `_DOCUMENT_TYPE_SELECTION`;
      `_RETENTION_KIND_SELECTION`; `retention_kind` + ocr/seller copies in
      `_REVIEW_EDITABLE_FIELD_ORDER`.
- [x] 2.4 Same Selection + `retention_kind` on
      `models/collection_voucher_review_snapshot.py`.
- [x] 2.5 Bump `__manifest__.py` to `19.0.1.40.0`; add
      `migrations/19.0.1.40.0/post-migrate.py` calling
      `_collection_enable_all_document_types()` (`Command.link`; extras kept).
- [x] 2.6 Upgrade `-u collection`. Confirm 1.1–1.3 GREEN; 1.4–1.6 still RED.

## Phase 3: GREEN parser/schema

- [x] 3.1 `tools/collection_voucher.py`: type-owned maps; seven-type schema; amount
      number\|string normalizer; MIME `image/jpg` alias.
- [x] 3.2 Strict parse: extra=forbid; type-foreign reject; null/`""` omit; cash no
      proof; `YYYY-MM-DD`; check date order; keep `_collection_parse_payment_vals`
      `unsupported` reject.
- [x] 3.3 `tools/collection_allocation.py`: receipt amounts `anyOf` number\|string;
      reuse normalizer.
- [x] 3.4 Upgrade `-u collection`. Confirm 1.4–1.6 GREEN; existing allocation tests
      still pass.
- [x] 3.5 `pre-commit run --files` collection
      models/tools/data/migrations/tests/`__manifest__.py`.

## Phase 4: Docs

- [x] 4.1 `AGENTS.md`: catalog 7; `19.0.1.40.0`; union-all migrate. Sync migration-test
      version assertions.
- [x] 4.2 `readme/DESCRIPTION.md`: seven types (echeck, cash, retention_certificate).
- [x] 4.3 Delete catalog-blocker paragraph in
      `/home/crisd/projects/nebula/nebula-agent/AGENTS.md` only.
- [x] 4.4 `pre-commit run --files` those three docs paths.
