# Apply Progress: chatter-voucher-attachments

**Change**: chatter-voucher-attachments
**Mode**: Strict TDD
**Batch**: Work Unit 1 / PR 1 (Phase 1, tasks 1.1–1.11)
**Branch**: `feat/chatter-voucher-attachments-01-migrate-model` (local only; not pushed)

## Completed Tasks

- [x] 1.1 RED voucher/mail chatter proof + MIME picker
- [x] 1.2 GREEN mixin inherit, picker override, drop Binary
- [x] 1.3 RED replace/clear/omit/invalid/reset
- [x] 1.4 GREEN write-reset on `message_main_attachment_id`; keep `attachment_rotation`
- [x] 1.5 RED SQL migrate scenarios
- [x] 1.6 GREEN `migrations/19.0.1.13.0` + manifest `19.0.1.13.0`
- [x] 1.7 RED UI: no Binary widgets; chatter remains
- [x] 1.8 GREEN views: drop Binary widgets; `<chatter open_attachments="True"/>`
- [x] 1.9 RED MCP nest → chatter designated proof
- [x] 1.10 GREEN savepoint `message_post` after create; nest schema unchanged
- [x] 1.11 GREEN helpers create proof via `message_post`

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_collection_voucher.py`, `tests/test_collection_mail.py` | Unit (TransactionCase) | ✅ 26/26 `TestCollectionVoucher`+`TestCollectionMail` | ✅ Written then executed: 1 failed, 5 error(s) of 6 (no `message_main_attachment_id`) | ✅ Passed after mixin + picker | ✅ PNG proof, PDF proof, extra does not steal, non-image extra, force=True text | ➖ None needed |
| 1.2 | same | Unit | (same baseline) | (1.1 RED) | ✅ Inherit `mail.thread.main.attachment`; override picker; drop Binary | ➖ Structural with 1.1 cases | ➖ None needed |
| 1.3 | `tests/test_collection_voucher.py` | Unit | covered by 1.1 net | ✅ Written: replace/clear/omit/invalid/extra-no-reset | ✅ Passed with 1.4 | ✅ approved replace, rejected extra, clear keeps decided, omit, invalid UserError | ➖ None needed |
| 1.4 | `models/collection_voucher.py` | Unit | — | (1.3 RED) | ✅ write-reset on main id change; clear rotation 0; kanban reopen requires main replace | ✅ replace vs extra vs clear | ➖ None needed |
| 1.5 | `tests/test_collection_voucher.py` (`TestCollectionVoucherAttachmentMigrate`) | Unit | N/A (new class) | ✅ Written (import migrate scripts + SQL leftover rows) | ✅ Passed after 1.6 | ✅ named filename vs empty → `proof.bin` | ➖ None needed |
| 1.6 | `migrations/19.0.1.13.0/{pre,post}-migrate.py`, `__manifest__.py` | Unit | — | (1.5 RED) | ✅ pre nulls `res_field`, renames, links `mail.message`; post sets main | ➖ Structural with 1.5 cases | ➖ None needed |
| 1.7 | `tests/test_collection_ui.py` | Unit (arch) | UI Binary-widget test existed | ✅ Written invert: no Binary; chatter `open_attachments` | Execute blocked until 1.8 (`-u` ParseError on leftover widgets) then ✅ | ✅ form + list + kanban omit widgets | ➖ None needed |
| 1.8 | `views/collection_views.xml` | Unit | — | (1.7 RED) | ✅ widgets stripped; `<chatter open_attachments="True"/>` | ➖ Structural | ➖ None needed |
| 1.9 | `tests/test_collection_mcp_tool.py` | Unit | — | ✅ `test_create_with_valid_png_nest_becomes_chatter_proof` | ✅ Passed with 1.10 | ✅ PDF nest adapted helper still persists | ➖ None needed |
| 1.10 | `tools/collection_voucher.py` | Unit | — | (1.9 RED) | ✅ validate nest → sidecar → `message_post` in savepoint; no Binary vals | ➖ Nest schema unchanged (Phase 2 exact-retry triangulation) | ➖ None needed |
| 1.11 | `tests/test_collection_{acl,document_review,document_review_flag,mcp_tool,payment}.py` | Unit | — | N/A helpers | ✅ `post_voucher_proof` / `message_post` only | ➖ Helper rewrite | ➖ None needed |

### Test Summary

- **Safety net**: `TestCollectionVoucher`+`TestCollectionMail` → **0 failed, 0 error(s) of 26 tests**
- **1.1 RED execute**: **1 failed, 5 error(s) of 6 tests** (AttributeError / missing field)
- **Phase 1 focused GREEN**: `0 failed, 0 error(s) of 51 tests` (exit 0)
- **Helper/MCP/review follow-up**: `0 failed, 2 error(s) of 73 tests` — both errors are pre-existing `res.config.settings` `default_picking_policy` NOT NULL on `TestCollectionDocumentReviewFlag.test_settings_toggle_persists_*`; not introduced by this batch. ACL, document review, MCP attachment chatter tests passed.
- **Layers used**: Unit/TransactionCase (51 focused + helper follow-up)
- **Approval tests**: existing Binary attachment tests rewritten to chatter (not a silent behavior preserve)
- **Pure functions created**: 0 (ORM mixin/write path)

## Work Unit Evidence

| Evidence | Required value |
|---|---|
| Focused test command and exact result | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init --test-enable --workers=0 --http-port=18069 --test-tags /collection:TestCollectionVoucher,/collection:TestCollectionVoucherAttachmentMigrate,/collection:TestCollectionMail,/collection:TestCollectionPaymentAttachment,/collection:TestCollectionUi.test_payment_vouchers_views_omit_binary_widgets,/collection:TestCollectionMcpAttachment.test_create_with_valid_png_nest_becomes_chatter_proof` → **exit 0**, `0 failed, 0 error(s) of 51 tests` |
| Runtime harness command/scenario and exact result | N/A — Odoo `TransactionCase` rolls back; no extra runtime boundary beyond the focused module tests |
| Rollback boundary | Revert this branch/commit: `models/collection_voucher.py`, `tools/collection_voucher.py`, `views/collection_views.xml`, `__manifest__.py`, `migrations/19.0.1.13.0/`, Phase 1 test files, and this change folder. Do **not** delete migrated chatter `ir.attachment` / `mail.message` rows if the upgrade already ran |

## Installability coupling

Binary field drop cannot `-u collection` while views still declare `attachment`. Widget strip (1.8) and MCP `message_post` glue (1.10) traveled with 1.2 so the upgrade loads. Review URL remains `/web/content?model=...&field=attachment` (Phase 3). Queue eligibility now uses `message_main_attachment_id` so helpers stay installable.

## Deviations from Design

None on proof pointer, picker, MCP persist, or migration version. Review `/web/content/{id}` is intentionally deferred to Phase 3; payload filename now comes from the main attachment name.

## Issues Found

- `TestCollectionDocumentReviewFlag` settings-toggle tests error on `res_config_settings.default_picking_policy` NOT NULL. Pre-existing stock/settings schema issue; not fixed in this batch.
- Authored diff is above 400 lines because widgets + MCP glue must ship with the Binary drop (forecast High). Next slices are Phase 2 (MCP tests) and Phase 3 (review URL/docs).
- `tests/test_collection_acl.py` and `tests/test_collection_document_review_flag.py` were already dirty on `main` with sheet-scoped review helper updates. Staging them for 1.11 includes those unrelated hunks so helpers stay installable; they are not a Phase 3 review-URL rewrite.

## Remaining Tasks

- [ ] Phase 2 MCP persist/exact-retry triangulation (2.1–2.4)
- [ ] Phase 3 review URL `/web/content/{id}`, OWL, AGENTS/readme (3.1–3.3)
- [ ] Phase 4 upgrade/verify (4.1–4.3)

## Workload / PR Boundary

- Mode: stacked PR slice (`auto-chain` / `stacked-to-main`)
- Current work unit: PR 1 migrate + model
- Boundary: mixin, drop Binary, migrate 19.0.1.13.0, picker, write-reset, widget strip, MCP `message_post` glue, helper rewrite
- Estimated review budget impact: High (widgets+MCP glued to field drop; ~1000 authored lines including tests)
