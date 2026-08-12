# Tasks: Document Review Feature Flag

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 420–500 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Company flag + Settings `#collections` + default-off | PR 1 | `invoke test -m collection` | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init` | `models/res_company.py`, `models/res_config_settings.py`, `views/res_config_settings_views.xml`, `__manifest__.py` data, flag-test default/settings cases |
| 2 | Validate-gate skip + RPC refuse + test opt-in | PR 2 | `invoke test -m collection` | N/A — TransactionCase Python gates; no new XML/data | voucher skip, line RPC refuse, opt-in in `tests/test_collection_{document_review,voucher,acl}.py`, flag-test OFF cases |
| 3 | Menu blacklist + load_menus/settings UI | PR 3 | `invoke test -m collection` | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init` | `models/ir_ui_menu.py`, `tests/test_collection_ui.py` load_menus/settings arch |

## Phase 1: Company flag and Settings (PR 1)

- [x] 1.1 RED: `tests/test_collection_document_review_flag.py` — `env.company.document_review_enabled` is False (Default off). Import in `tests/__init__.py`.
- [x] 1.2 GREEN: `models/res_company.py` Boolean default False; import in `models/__init__.py`.
- [x] 1.3 RED: flag test — Settings related write persists on `company_id` (Settings admin toggle).
- [x] 1.4 GREEN: `models/res_config_settings.py` related `readonly=False`; `views/res_config_settings_views.xml` inherit `base.res_config_settings_view_form` (`<app name="collections" groups="base.group_system">`); add to `__manifest__.py` `data`; bump version `19.0.1.7.0` → `19.0.1.8.0`.
- [x] 1.5 GREEN: `@api.private` `_document_review_enabled()`; `write` calls `registry.clear_cache()` when flag in vals.
- [x] 1.6 REFACTOR: AGPL headers; `invoke test -m collection`; upgrade; pre-commit.

## Phase 2: Validate gate and RPC refuse (PR 2)

- [x] 2.1 RED: flag test — OFF `action_validate()` succeeds with pending attached line (Validate succeeds when off).
- [x] 2.2 GREEN: `collection_voucher._ensure_no_pending_attached_review` returns when helper is false.
- [x] 2.3 RED: flag test — OFF `get_review_queue` / `action_review_{approve,reject,set_rotation}` raise `UserError` not `[]` (Review operations refuse; approve/reject do not run).
- [x] 2.4 GREEN: those four methods in `models/collection_voucher_line.py` raise `UserError("Document Review is not enabled.")` before queue/lock.
- [x] 2.5 GREEN opt-in: `TestCollectionDocumentReview.setUp` sets flag True (`_neutralize_preexisting_queue`); `test_action_validate_blocked_when_attached_line_pending` and ACL internal review tests enable flag (portal `AccessError` stays).
- [x] 2.6 REFACTOR: `invoke test -m collection`.

## Phase 3: Menu blacklist and UI (PR 3)

- [x] 3.1 RED: `test_collection_ui.py` — settings arch `name="collections"` + related field; `load_menus` omits review menu when OFF, includes when ON; xmlid tests unchanged.
- [x] 3.2 GREEN: `models/ir_ui_menu.py` `_load_menus_blacklist` appends review menu id when helper false; import in `models/__init__.py`.
- [x] 3.3 RED/GREEN: flag test — payment-line views still show `state` / audit when OFF (Line state and audit remain).
- [x] 3.4 REFACTOR: `invoke test -m collection`; upgrade; `pre-commit run --files odoo/custom/src/private/collection/**`.

## Phase 4: Cleanup

- [x] 4.1 Confirm `views/collection_document_review_views.xml` untouched; no `menu.active`; no voucher `company_id`.
