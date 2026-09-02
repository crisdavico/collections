# Apply Progress: inline-collection-allocation

Work units 1–3 / Phases 1–3 (tasks 1.1–3.5). Strict TDD.

## Completed Tasks

- [x] 1.1 Extract `_PAYMENT_SCHEMA`+parse; keep `@mcp_tool` `create_collection_vouchers`
- [x] 1.2 Rewrite allocation MCP tests; payments schema +
      `{sheet_id,vouchers,allocation}` payload
- [x] 1.3 `request_id` replay returns full payload, zero writes
- [x] 1.4 Exact `document_id` reuse continues to allocation
- [x] 1.5 Partial overlap → generic conflict, zero writes
- [x] 1.6 Other-company `document_id` → generic conflict, zero writes
- [x] 1.7 `auto_create_sheet` off → named English error, zero writes
- [x] 1.8 `invoices: []` on-account
- [x] 1.9 Residual without reason fails
- [x] 1.10 Residual negative fails
- [x] 1.11 `content_hash` includes `residual_reason`
- [x] 1.12 Revalidation rolls back vouchers (existing persist savepoint expanded; no
      extra layer)
- [x] 1.13 Unbound write lazy-creates partner+binding via `_collection_create_vouchers`
- [x] 1.14 Leak/sudo scans; errors raised not `{"error":...}`
- [x] 1.15 Module test + lint
- [x] 2.1 Discovery `category=read` / `registry=mcp` / `kind=method`; no `muk_mcp.tool`
      row
- [x] 2.2 Auth: portal/public `AccessError`; share asserted; not-enabled / unbound
      seller `UserError`
- [x] 2.3 No open sheet (and closed-only) → `{allocation: null}` via
      `_open_sheets_for_seller`
- [x] 2.4 Unbound/unknown identification → null; no partner or binding created
- [x] 2.5 Open sheet without allocation → null
- [x] 2.6 Confirmed payload: `residual_reason` plus `vouchers`/`invoices` lists
- [x] 2.7 Validated allocation returned with stored `state`
- [x] 2.8 Multi-open leftover sheets → existing msgid `UserError`
- [x] 2.9 GET never creates a sheet when `auto_create_sheet` is True
- [x] 2.10 Found payload omits `attachment` / `datas` / `base64` keys
- [x] 2.11 No `sudo()`; no `resolve_customer_partner`; no
      `_resolve_open_sheet_id_for_create`
- [x] 2.12 Module test + lint
- [x] 3.1 Registry absence of `create_collection_vouchers`; drop decorated method+schema;
      keep `_collection_*`
- [x] 3.2 Delete create/replay/ACL voucher-tool tests; retarget Attachment/Provenance +
      partner-resolve onto `create_collection_allocation`
- [x] 3.3 `AGENTS.md` MCP bullets rewritten; helpers remain; version `19.0.1.27.0`
- [x] 3.4 Manifest `19.0.1.27.0`; no `migrations/19.0.1.27.0/`;
      `test_manifest_version_is_1_27_0`
- [x] 3.5 Module test + lint

## TDD Cycle Evidence

| Task | Test File                                        | Layer       | Safety Net                                                        | RED                                                                                                | GREEN                                                                          | TRIANGULATE                                           | REFACTOR                                                                |
| ---- | ------------------------------------------------ | ----------- | ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | ----------------------------------------------------- | ----------------------------------------------------------------------- |
| 1.1  | `tests/test_collection_mcp_allocation.py`        | Unit        | ✅ voucher tool still discovered; overlay keeps per-payment ident | ✅ Written (`test_payment_schema_and_parse_replicate_top_level_identification`, discovery overlay) | ✅ Passed                                                                      | ✅ empty ident UserError + two-payment replicate      | ✅ Overlay in decorated method; helpers otherwise untouched             |
| 1.2  | `tests/test_collection_mcp_allocation.py`        | Integration | N/A (rewrite)                                                     | ✅ Written (discovery required set, first create, shape freeze)                                    | ✅ Passed 32/32 class                                                          | ✅ two-payment send order vs first-create single      | ✅ Payload via `_collection_vouchers_payload`                           |
| 1.3  | same                                             | Integration | ✅                                                                | ✅ `test_request_id_replay_zero_writes`                                                            | ✅ Passed                                                                      | ✅ content_hash replay with new request_id            | ➖ None needed                                                          |
| 1.4  | same                                             | Integration | ✅                                                                | ✅ `test_exact_document_id_reuse_continues_to_allocation`                                          | ✅ Passed                                                                      | ✅ vs all-new first create                            | ✅ classify dict → continue, do not return                              |
| 1.5  | same                                             | Integration | ✅                                                                | ✅ `test_partial_overlap_conflict_no_writes`                                                       | ✅ Passed                                                                      | ✅ subset/partial amend reject                        | ➖ None needed                                                          |
| 1.6  | same                                             | Integration | ✅                                                                | ✅ `test_other_company_document_id_conflict`                                                       | ✅ Passed                                                                      | ✅ mixed other-company gate path                      | ➖ Hidden hit uses UniqueViolation → generic conflict                   |
| 1.7  | same                                             | Integration | ✅                                                                | ✅ `test_auto_create_sheet_off_named_error_zero_writes`                                            | ✅ Passed                                                                      | ✅ vs default ON first create                         | ➖ None needed                                                          |
| 1.8  | same                                             | Integration | ✅                                                                | ✅ `test_empty_invoices_on_account`                                                                | ✅ Passed                                                                      | ✅ vs applied overdue 100                             | ➖ invoices required, empty allowed                                     |
| 1.9  | same                                             | Integration | ✅                                                                | ✅ `test_residual_without_reason_fails`                                                            | ✅ Passed                                                                      | ✅ with-reason leftover in 1.11                       | ➖ None needed                                                          |
| 1.10 | same                                             | Integration | ✅                                                                | ✅ `test_residual_negative_fails`                                                                  | ✅ Passed                                                                      | ✅ vs on-account empty invoices                       | ➖ None needed                                                          |
| 1.11 | same                                             | Integration | ✅                                                                | ✅ `test_reason_only_retry_not_noop_hash_includes_reason`                                          | ✅ Passed                                                                      | ✅ matching hash no extra revision                    | ✅ hash payload adds `residual_reason`                                  |
| 1.12 | same                                             | Integration | ✅                                                                | ✅ `test_revalidation_rolls_back_vouchers`                                                         | ✅ Passed                                                                      | ✅ stale invoice + `_counts` includes vouchers        | ✅ Reused existing persist savepoint (no extra layer)                   |
| 1.13 | same                                             | Integration | ✅                                                                | ✅ `test_unbound_write_lazy_creates_partner_and_binding`                                           | ✅ Passed                                                                      | ✅ unbound reuse / mismatch does not create           | ✅ identity assert after create                                         |
| 1.14 | same                                             | Unit        | ✅                                                                | ✅ `test_tool_source_has_no_sudo` + leak tokens on UserError                                       | ✅ Passed                                                                      | ✅ no `{"error"` in source                            | ➖ None needed                                                          |
| 1.15 | module                                           | Integration | ✅                                                                | ➖ verification                                                                                    | ✅ `invoke test -m collection --mode=update` 0 failed / 541; pre-commit passed | ➖                                                    | ➖                                                                      |
| 2.1  | `tests/test_collection_mcp_allocation_lookup.py` | Unit        | N/A (new)                                                         | ✅ Written (`test_discovered_as_method_read_mcp`); RED 5 failed / 12 errors of 16 (tool not found) | ✅ Passed 16/16 class                                                          | ✅ required set + types + no DB row                   | ✅ Mixin file + `tools/__init__.py` import                              |
| 2.2  | same                                             | Integration | ✅                                                                | ✅ portal/public AccessError; not-enabled; unbound seller                                          | ✅ Passed                                                                      | ✅ share portal/public + two seller fail-closed paths | ➖ None needed                                                          |
| 2.3  | same                                             | Integration | ✅                                                                | ✅ `test_no_open_sheet_returns_null`                                                               | ✅ Passed                                                                      | ✅ closed-only sheet also null                        | ✅ `_open_sheets_for_seller`; never `_resolve_open_sheet_id_for_create` |
| 2.4  | same                                             | Integration | ✅                                                                | ✅ unbound listable → null, counts unchanged                                                       | ✅ Passed                                                                      | ✅ unknown ident also null, no partner/binding        | ➖ Binding-only search                                                  |
| 2.5  | same                                             | Integration | ✅                                                                | ✅ open sheet without allocation → null                                                            | ✅ Passed                                                                      | ✅ vs confirmed found payload                         | ➖ None needed                                                          |
| 2.6  | same                                             | Integration | ✅                                                                | ✅ confirmed lists + `residual_reason`                                                             | ✅ Passed                                                                      | ✅ on-account `invoices: []` still present            | ✅ `_collection_allocation_lookup_payload`                              |
| 2.7  | same                                             | Integration | ✅                                                                | ✅ validated returned with stored state                                                            | ✅ Passed                                                                      | ✅ vs confirmed `state`                               | ➖ None needed                                                          |
| 2.8  | same                                             | Integration | ✅                                                                | ✅ leftover multi-open UserError                                                                   | ✅ Passed                                                                      | ✅ exact existing msgid; zero writes                  | ➖ Same msgid as `_resolve_open_sheet_id_for_create`                    |
| 2.9  | same                                             | Integration | ✅                                                                | ✅ GET does not create sheet when auto ON                                                          | ✅ Passed                                                                      | ✅ all null/found branches `_counts()` equal          | ➖ None needed                                                          |
| 2.10 | same                                             | Integration | ✅                                                                | ✅ recursive key walk omits media keys                                                             | ✅ Passed                                                                      | ✅ found invoices non-empty so walk runs              | ✅ Assertion is key-based (not JSON substring)                          |
| 2.11 | same                                             | Unit        | ✅                                                                | ✅ source + `getsource` no sudo / resolve / create-sheet helper                                    | ✅ Passed                                                                      | ✅ file scan + method scan                            | ➖ None needed                                                          |
| 2.12 | module                                           | Integration | ✅                                                                | ➖ verification                                                                                    | ✅ `invoke test -m collection --mode=update` 0 failed / 557; pre-commit passed | ➖                                                    | ➖                                                                      |
| 3.1  | `tests/test_collection_mcp_allocation.py`        | Unit        | ✅ Phase 2 557 green                                              | ✅ Written (`test_create_collection_vouchers_absent_from_mcp_registry`); RED 1 failed / 0 error of 1 (tool still registered) | ✅ Passed 0 failed / 3 (absence + discovery + version) | ✅ helpers remain callable; not in registry; no `muk_mcp.tool` row; mixin has no method | ✅ Dropped decorated method+schema; `_collection_*` untouched |
| 3.2  | `tests/test_collection_mcp_tool.py`, `tests/test_collection_mcp_partner_resolve.py` | Integration | ✅                                                                | ✅ Retargeted Attachment/Provenance/partner-resolve to `create_collection_allocation`; deleted create/replay/ACL + mixed-customer + UniqueViolation-invalid-nest wrap | ✅ 0 failed / 35 focused (Attachment+Provenance+PartnerResolve) | ✅ PNG+PDF nests; invalid MIME; exact retry ignore; UniqueViolation race with distinct `request_id`; inactive+other-seller invalid ident | ➖ `_call` lifts top-level ident + required invoices/`residual_reason` |
| 3.3  | `AGENTS.md`                                        | Structural  | N/A                                                               | ➖ docs                                                                                            | ✅ MCP bullets rewritten                                                      | ➖ Triangulation skipped: documentation only          | ➖ None needed                                                          |
| 3.4  | `tests/test_collection_company_migration.py`       | Unit        | ✅                                                                | ✅ `test_manifest_version_is_1_27_0` + no `migrations/19.0.1.27.0/`                               | ✅ Passed with absence/discovery                                             | ➖ Triangulation skipped: version constant              | ➖ None needed                                                          |
| 3.5  | module                                           | Integration | ✅                                                                | ➖ verification                                                                                    | ✅ `invoke test -m collection --mode=update` 0 failed / 520; pre-commit passed | ➖                                                    | ➖                                                                      |

### Test Summary

- **Total tests written / rewritten**: Phase 1: 32 in `TestCollectionMcpAllocation`.
  Phase 2: 16 in `TestCollectionMcpAllocationLookup`. Phase 3: 1 registry-absence test;
  Attachment/Provenance/partner-resolve retargeted; voucher-tool create/replay/ACL
  deleted
- **Total tests passing**: 520 collection module
  (`invoke test -m collection --mode=update`). Net drop vs Phase 2 557 is the retired
  voucher-tool create/replay/ACL class plus mixed-customer and UniqueViolation-invalid-nest
  wrap tests
- **Layers used**: Unit (discovery/source scans), Integration (TransactionCase MCP
  `_call`)
- **Approval tests** (refactoring): None for Phase 3 — tool retirement + test retarget
- **Pure functions created**: 0 (ORM/MCP mixins)

## Work Unit Evidence

### Phase 1 (prior)

| Evidence                                          | Required value                                                                                                                                                                                                                           |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --test-enable --stop-after-init --workers=0 --http-port=19069 --gevent-port=19070 --test-tags /collection:TestCollectionMcpAllocation` → **0 failed, 0 error(s) of 32 tests** |
| Runtime harness command/scenario and exact result | N/A — e2e false in `openspec/config.yaml`; module TransactionCase is the proving command. `invoke test -m collection --mode=update` → **0 failed, 0 error(s) of 541 tests**                                                              |
| Rollback boundary                                 | Revert `tools/collection_allocation.py`, `tools/collection_voucher.py` helper/schema overlay, `tools/__init__.py` import order, and `tests/test_collection_mcp_allocation.py`. `@mcp_tool` `create_collection_vouchers` remains.         |

### Phase 2 (this batch)

| Evidence                                          | Required value                                                                                                                                                                                                                                                                                                     |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Focused test command and exact result             | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --test-enable --stop-after-init --workers=0 --http-port=19069 --gevent-port=19070 --test-tags /collection:TestCollectionMcpAllocationLookup` → **RED: 5 failed, 12 error(s) of 16 tests** (tool not found); **GREEN: 0 failed, 0 error(s) of 16 tests** |
| Runtime harness command/scenario and exact result | N/A — e2e false in `openspec/config.yaml`; module TransactionCase is the proving command. `invoke test -m collection --mode=update` → **0 failed, 0 error(s) of 557 tests**. Scoped pre-commit on lookup files passed.                                                                                             |
| Rollback boundary                                 | Delete `tools/allocation_lookup.py` and `tests/test_collection_mcp_allocation_lookup.py`; remove their imports from `tools/__init__.py` and `tests/__init__.py`. Do not revert Phase 1 write-path files. Manifest stays `19.0.1.26.0`. `create_collection_vouchers` remains exposed.                               |

### Phase 3 (this batch)

| Evidence                                          | Required value                                                                                                                                                                                                                                                                                                                                                          |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | RED: `docker exec -i seedian-odoo-1 odoo -d devel -u collection --test-enable --stop-after-init --workers=0 --http-port=19081 --gevent-port=19082 --test-tags /collection:TestCollectionMcpAllocation.test_create_collection_vouchers_absent_from_mcp_registry` → **1 failed, 0 error(s) of 1 tests**. GREEN: same tags plus discovery+version on ports 19083/19084 → **0 failed, 0 error(s) of 3 tests**. Retargeted classes: `--test-tags /collection:TestCollectionMcpAttachment,/collection:TestCollectionMcpProvenance,/collection:TestCollectionMcpPartnerResolve` → **0 failed, 0 error(s) of 35 tests** |
| Runtime harness command/scenario and exact result | N/A — e2e false in `openspec/config.yaml`; module TransactionCase is the proving command. `invoke test -m collection --mode=update` → **0 failed, 0 error(s) of 520 tests**. Scoped pre-commit on `odoo/custom/src/private/collection/**` passed (optional C8101 author pre-existing).                                                                              |
| Rollback boundary                                 | Restore `@mcp_tool` `create_collection_vouchers` on `tools/collection_voucher.py`; restore voucher-tool create/replay/ACL tests; revert Attachment/Provenance/partner-resolve `TOOL_NAME`; revert `AGENTS.md` MCP bullets; revert `__manifest__.py` and `test_manifest_version_is_1_27_0` to `19.0.1.26.0`. Do not revert Phase 1 fused write or Phase 2 lookup. Coordinated Nebula deploy. |

## Files Changed

| File                                             | Action             | What Was Done                                                                                                                                                         |
| ------------------------------------------------ | ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tools/collection_voucher.py`                    | Modified (Phase 1) | Extracted `_PAYMENT_SCHEMA` without `customer_identification`; parse takes top-level ident and replicates; voucher tool overlays per-payment idents; `@mcp_tool` kept |
| `tools/collection_allocation.py`                 | Modified (Phase 1) | `payments` schema; invoices required; fused write; payload `sheet_id`+ordered `vouchers[]`; hash includes reason; fail-closed sheet; identity assert                  |
| `tools/__init__.py`                              | Modified           | Phase 1: import voucher before allocation. Phase 2: import `allocation_lookup`                                                                                        |
| `tests/test_collection_mcp_allocation.py`        | Modified (Phase 1) | Rewritten for inline payments (32 tests)                                                                                                                              |
| `tools/allocation_lookup.py`                     | Created (Phase 2)  | `@mcp_tool` `get_collection_allocation` (`category=read`); binding-only; `_open_sheets_for_seller`; zero writes                                                       |
| `tests/test_collection_mcp_allocation_lookup.py` | Created (Phase 2)  | 16 TransactionCase tests for discovery, auth, null, found, validated, multi-open, no-write, no-media, no-sudo                                                         |
| `tests/__init__.py`                              | Modified (Phase 2)  | Register `test_collection_mcp_allocation_lookup`                                                                                                                      |
| `tools/collection_voucher.py`                    | Modified (Phase 3)  | Dropped `@mcp_tool` `create_collection_vouchers` method+schema; `_collection_*` helpers remain                                                                          |
| `tests/test_collection_mcp_allocation.py`        | Modified (Phase 3)  | Registry absence + discovery `assertNotIn` voucher tool                                                                                                                |
| `tests/test_collection_mcp_tool.py`            | Modified (Phase 3)  | Deleted create/replay/ACL class; Attachment/Provenance `_call` fused allocation payload                                                                                |
| `tests/test_collection_mcp_partner_resolve.py` | Modified (Phase 3)  | `TOOL_NAME` + payload retarget; mixed-customer removed; invalid ident fail-closed                                                                                    |
| `tests/test_collection_company_migration.py`   | Modified (Phase 3)  | `test_manifest_version_is_1_27_0`; no `migrations/19.0.1.27.0/`                                                                                                      |
| `__manifest__.py`                                | Modified (Phase 3)  | `19.0.1.27.0`                                                                                                                                                         |
| `AGENTS.md`                                      | Modified (Phase 3)  | MCP bullets: fused create, get tool, helpers remain, version 1.27.0                                                                                                 |

## Deviations from Design

- Persist savepoint was **expanded** (Phase 1) to cover voucher create + revalidate +
  persist so TransactionCase can observe rollback. This is not a second savepoint layer;
  nested binding savepoints inside `_collection_create_vouchers` remain.
- Hidden other-company `document_id` is not visible to the caller, so classify returns
  None; UniqueViolation on create is mapped to the generic document conflict (same msgid
  as voucher-tool races).
- Phase 2 media assertion walks payload **keys**, not JSON substrings: `document_id` can
  contain the test method name (`…attachments…`) and is not an attachment field.
- Phase 3 deleted `test_unique_violation_replay_ignores_invalid_nest`. That path lived in
  the retired voucher-tool UserError→replay wrap around nest parse. Fused write parses
  nests only when classify is None; invalid nests raise before UniqueViolation. Visible
  exact-retry still ignores invalid nests (`test_exact_retry_ignores_invalid_nest`).
- Phase 3 mixed-customer batch tests were deleted: fused write uses a single top-level
  `customer_identification`.

## Issues Found

None blocking. Optional pylint C8101 on `__manifest__.py` author is pre-existing.

## Remaining Tasks

None — tasks 1.1–3.5 are `[x]` (32/32). Ready for verify.

## Workload / PR Boundary

- Mode: stacked PR slice (`stacked-to-main`)
- Current work unit: Phase 3 retire `create_collection_vouchers` MCP; manifest
  `19.0.1.27.0`
- Boundary: drop voucher `@mcp_tool`; retarget remaining MCP tests; AGENTS.md +
  manifest. Do not reopen Phase 1/2 write/read behavior except discovery `assertNotIn`.
- Estimated review budget impact: this slice is the third chained PR; large deletion of
  voucher-tool-only tests. Coordinated Nebula deploy before/with merge.
