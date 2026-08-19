# Tasks: Collection Company Configuration

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 1800–2500 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1→2→3→4→5→6→7 stacked to main |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Settings + catalog + labels | PR 1 | `invoke test -m collection` | `invoke install -m collection` | catalog; company/settings; settings views |
| 2 | `company_id` + `ir.rule`; ACL flips | PR 2 | `invoke test -m collection` | `invoke install -m collection` | `company_id`; `collection_security.xml`; ACL tests |
| 3 | Migrate backfill + sequences | PR 3 | `invoke test -m collection` | `invoke install -m collection` | `migrations/19.0.1.16.0/`; `ir_sequence_data.xml` |
| 4 | Helper: seller + types | PR 4 | `invoke test -m collection` | `invoke install -m collection` | `_assert_new_work`; voucher/sheet; view domains |
| 5 | `auto_create_sheet` + one-open | PR 5 | `invoke test -m collection` | `invoke install -m collection` | auto-assign; sheet lock; list Action |
| 6 | MCP same-co replay vs reject | PR 6 | `invoke test -m collection` | `invoke install -m collection` | `tools/collection_voucher.py` |
| 7 | Docs/`AGENTS.md` | PR 7 | scoped pre-commit on `AGENTS.md` | N/A — docs-only | `AGENTS.md` |

PR ≤~400; stacked-to-main. No nebula-agent. Threat-matrix N/A. Verify: upgrade + scoped pre-commit + tests.

## Phase 1: Settings + catalog + labels

- [x] 1.1 RED: Flip `"Settings"` (`test_collection_ui.py`, `test_collection_document_review_flag.py`); catalog/empty-sellers/defaults/flag tests.
- [x] 1.2 GREEN: Catalog model+data; company/settings; Collection Settings labels (keep XMLID); `19.0.1.16.0`.

## Phase 2: company_id + ir.rule

- [x] 2.1 RED: Flip no-`ir.rule` (`test_collection_acl.py`); required `company_id` + hide-other-company (voucher/sheet/snapshot).
- [x] 2.2 GREEN: Required `company_id` on voucher/sheet/snapshot; `collection_security.xml` `ir.rule`; catalog ACL; no extra groups.

## Phase 3: Migration + sequences

- [ ] 3.1 RED: Stamp/repair/seed/four-types; per-company `COL/` `CS/` (no `company_id=False` thief).
- [ ] 3.2 GREEN: `post-migrate.py` steps 1–6; seq → `base.main_company`; `with_company` `next_by_code`; company create copies seq+types.

## Phase 4: New-work helper

- [ ] 4.1 RED: Flip nullable-ORM-seller (`test_collection_voucher.py`); empty/disabled/disallowed-type, seller/type write, historical-operable, UI domains.
- [ ] 4.2 GREEN: `res.company._assert_new_work` on create + seller/type write; skip Approve/Close/Reopen; `collection_views.xml` domains.

## Phase 5: auto_create_sheet + one-open

- [ ] 5.1 RED: Flip always-on auto-assign + per-seller one-open (`test_collection_sheet.py`); OFF skip both; Action still creates; open in A+B.
- [ ] 5.2 GREEN: Gate auto-assign (OFF skips both); lock `(company_id, seller_id)`; list Action uses company + helper.

## Phase 6: MCP replay vs reject

- [ ] 6.1 RED: Flip global replay (`test_collection_mcp_tool.py`); same-co replay; other-co reject; UniqueViolation hidden; no B replay; unfiltered `get_seller_id`.
- [ ] 6.2 GREEN: Classifier in `tools/collection_voucher.py`; no `sudo()`; generic `UserError`; all-new via helper; leave `seller_lookup.py`.

## Phase 7: Docs

- [ ] 7.1 Update `AGENTS.md` (helper, sequences, `ir.rule`, MCP replay) + pre-commit + tests.
