# Apply Progress: get-seller-id-by-mobile

**Change**: get-seller-id-by-mobile **Mode**: Strict TDD **Batch**: Phase 1 (1.1–1.4
RED) + Phase 2 (2.1–2.3 GREEN min) + Phase 3 (3.1–3.9 fail-closed tests) + Phase 4
(4.1–4.4 docs + install + `/collection` tests + lint) **Work unit**: `get_seller_id`
tests and docs (this slice: Phase 4 docs + verify) **Delivery**: single PR
(`400-line budget risk: Low`; `Chained PRs recommended: No`)

## Completed Tasks

- [x] 1.1 Import `test_collection_mcp_seller_lookup` in `tests/__init__.py`.
- [x] 1.2 Create `tests/test_collection_mcp_seller_lookup.py` (`TransactionCase`; copy
      `_create_user`; set `partner_id.phone`).
- [x] 1.3 RED discovery: `get_tool_index`/`get_tools` — `get_seller_id` is
      `category=read`, `registry=mcp`, `kind=method`; no DB `muk_mcp.tool` row.
- [x] 1.4 RED spec Unique internal match: `_call` → JSON `{"seller_id": <positive int>}`
      only; vouchers unchanged.
- [x] 2.1 Create `tools/seller_lookup.py` (AGPL): mixin + `@mcp_tool` `get_seller_id`.
- [x] 2.2 Import `seller_lookup` in `tools/__init__.py`.
- [x] 2.3 GREEN: AccessError unless `base.group_user`; normalize + unique hit →
      `{seller_id}`; never `sudo()`.
- [x] 3.1 Portal and public `_call` → `AccessError`.
- [x] 3.2 Empty / whitespace / no-usable-digits mobile → `UserError`.
- [x] 3.3 AR variants: stored `+54 9 …`; queries `549…` and local 10-digit → same
      `seller_id`.
- [x] 3.4 Zero matches → `UserError`.
- [x] 3.5 Two internals same normalize → `UserError` (no pick-first).
- [x] 3.6 Portal/share same digits + one internal → internal `seller_id`.
- [x] 3.7 Only portal/share has that phone → `UserError`.
- [x] 3.8 Unique hit fails seller bar: share=False without `base.group_user` →
      `UserError`.
- [x] 3.9 Source has no `mobile_phone` and no `.sudo(` (Path/`inspect`; no `hr`).
- [x] 4.1 Update `AGENTS.md`: read MCP `get_seller_id`; WhatsApp = no connector inside
      the addon; MCP `mobile` argument is allowed. Repo map row, MCP bullets, testing
      table row. Write-tool rules kept. Nebula not claimed changed.
- [x] 4.2 Update `readme/DESCRIPTION.md` with `get_seller_id`. `README.rst` regenerated
      by oca-gen-addon-readme.
- [x] 4.3 Seedian root: `invoke install -m collection` (exit 0).
- [x] 4.4 Full `/collection` tests GREEN + scoped pre-commit on this change’s files
      (exit 0). Assigned `**` glob is not clean (archive YAML + pre-existing E501);
      archive restored.

## Files Changed

| File                                                         | Action      | What Was Done                                                                                                                                                                                  |
| ------------------------------------------------------------ | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/__init__.py`                                          | Modified    | Import `test_collection_mcp_seller_lookup` (alphabetical, before mcp_tool). (Phase 1)                                                                                                          |
| `tests/test_collection_mcp_seller_lookup.py`                 | Created     | `TestCollectionMcpSellerLookup`: copied `_create_user`; unique login; `partner_id.phone`; discovery + unique-match `_call`. (Phase 1)                                                          |
| `tools/seller_lookup.py`                                     | Created     | Sibling `muk_mcp.mixin`: `@mcp_tool get_seller_id`; `_collection_normalize_ar_mobile`; candidate match; call existing `_collection_require_internal_seller`; never `sudo()`. (Phase 2)         |
| `tools/__init__.py`                                          | Modified    | `from . import seller_lookup`. (Phase 2)                                                                                                                                                       |
| `tests/test_collection_mcp_seller_lookup.py`                 | Modified    | Extended existing class: catalog-style portal+public users; 9 fail-closed tests; unique `collection_seller_lookup_*` logins. (Phase 3) Four E501 docstrings wrapped in Phase 4 so ruff passes. |
| `AGENTS.md`                                                  | Modified    | Read MCP `get_seller_id`; WhatsApp = no connector, MCP `mobile` allowed; repo map; MCP bullets; testing table. Write-tool rules intact. (Phase 4)                                              |
| `readme/DESCRIPTION.md`                                      | Modified    | Short `get_seller_id` sentence; no Nebula-change claim. (Phase 4)                                                                                                                              |
| `README.rst`                                                 | Regenerated | oca-gen-addon-readme from DESCRIPTION fragment. (Phase 4)                                                                                                                                      |
| `openspec/changes/get-seller-id-by-mobile/tasks.md`          | Modified    | Marked 1.1–1.4 `[x]` (Phase 1), 2.1–2.3 `[x]` (Phase 2), 3.1–3.9 `[x]` (Phase 3), 4.1–4.4 `[x]` (Phase 4).                                                                                     |
| `openspec/changes/get-seller-id-by-mobile/apply-progress.md` | Updated     | Merged Phase 1 + Phase 2 + Phase 3 + Phase 4 evidence.                                                                                                                                         |

Not created/edited: `tools/collection_voucher.py`, Nebula. Archive files prettier/`**`
glob touched were restored with `git checkout -- openspec/changes/archive/`.

## TDD Cycle Evidence

### Phase 1 (RED harness — preserved)

| Task | Test File                                    | Layer       | Safety Net                                                                                                               | RED                                                                         | GREEN                  | TRIANGULATE                                              | REFACTOR                                       |
| ---- | -------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- | ---------------------- | -------------------------------------------------------- | ---------------------------------------------- |
| 1.1  | `tests/__init__.py`                          | Structural  | ✅ 0 failed, 0 error(s) of 1 (`TestCollectionMcpTool.test_tool_discovered_with_write_registry_and_schema`) before import | ✅ Import added                                                             | ⏳ deferred to Phase 2 | ➖ skipped: structural import only (one possible output) | ➖ None needed                                 |
| 1.2  | `tests/test_collection_mcp_seller_lookup.py` | Structural  | N/A (new file)                                                                                                           | ✅ File created with `_create_user` + `partner_id.phone`                    | ⏳ deferred to Phase 2 | ➖ skipped: structural test-file scaffold                | ➖ None needed                                 |
| 1.3  | `tests/test_collection_mcp_seller_lookup.py` | Integration | same as 1.1                                                                                                              | ✅ Written; FAIL `AssertionError: 'get_seller_id' not found` in `get_tools` | ⏳ deferred to Phase 2 | ⏳ deferred to Phase 2 (discovery is one scenario)       | ➖ None needed (no production code this batch) |
| 1.4  | `tests/test_collection_mcp_seller_lookup.py` | Integration | same as 1.1                                                                                                              | ✅ Written; ERROR `UserError: Tool not found: get_seller_id` on `_call`     | ⏳ deferred to Phase 2 | ⏳ deferred to Phase 3 (AR variants / fail-closed specs) | ➖ None needed (no production code this batch) |

### Phase 2 (GREEN min — preserved)

| Task | Test File                                    | Layer       | Safety Net                                                                                     | RED                                                        | GREEN                                                      | TRIANGULATE                                                                                                       | REFACTOR                                               |
| ---- | -------------------------------------------- | ----------- | ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| 2.1  | `tests/test_collection_mcp_seller_lookup.py` | Structural  | N/A (new mixin file; write mixin not edited)                                                   | ✅ Phase 1 discovery test already referenced missing mixin | ✅ Passed (tool discovered `read`/`mcp`/`method`)          | ➖ skipped: structural mixin file (one possible output)                                                           | ➖ None needed                                         |
| 2.2  | `tests/test_collection_mcp_seller_lookup.py` | Structural  | N/A (import-only)                                                                              | ✅ Phase 1 tests fail without import                       | ✅ Passed once `tools/__init__.py` imports `seller_lookup` | ➖ skipped: structural import only                                                                                | ➖ None needed                                         |
| 2.3  | `tests/test_collection_mcp_seller_lookup.py` | Integration | Write mixin untouched; focused seller class GREEN; extra write-suite re-run skipped this batch | ✅ Phase 1 unique-match + discovery already RED            | ✅ Passed: `0 failed, 0 error(s) of 2 tests`               | ✅ Phase 1 already has 2 cases (discovery vs unique `{seller_id}`); fail-closed / AR variants deferred to Phase 3 | ➖ None needed (matches design/catalog helper pattern) |

### Phase 3 (fail-closed specs)

Safety net before edits: focused `TestCollectionMcpSellerLookup` → **0 failed, 0
error(s) of 2 tests** (Phase 1–2 still GREEN). Production `tools/seller_lookup.py` was
not gutted.

RED column: production fail-closed already shipped in 2.3. Tests written first; they
passed immediately. Each would fail if the matching branch were missing.

| Task | Test File                                    | Layer         | Safety Net | RED                                                               | GREEN                                                   | TRIANGULATE                                                                 | REFACTOR                              |
| ---- | -------------------------------------------- | ------------- | ---------- | ----------------------------------------------------------------- | ------------------------------------------------------- | --------------------------------------------------------------------------- | ------------------------------------- |
| 3.1  | `tests/test_collection_mcp_seller_lookup.py` | Integration   | ✅ 2/2     | already GREEN — shipped in 2.3; test would fail if branch missing | ✅ Passed (`AccessError` for portal and public `_call`) | ✅ 2 callers (portal + public)                                              | ➖ None needed (production untouched) |
| 3.2  | `tests/test_collection_mcp_seller_lookup.py` | Integration   | ✅ 2/2     | already GREEN — shipped in 2.3; test would fail if branch missing | ✅ Passed (`UserError`)                                 | ✅ 4 inputs (`""`, whitespace, `"---"`, `"++abc"`)                          | ➖ None needed                        |
| 3.3  | `tests/test_collection_mcp_seller_lookup.py` | Integration   | ✅ 2/2     | already GREEN — shipped in 2.3; test would fail if branch missing | ✅ Passed (same `seller_id`)                            | ✅ 2 queries (`5491155550199`, `1155550199`) vs stored `+54 9 11 5555-0199` | ➖ None needed                        |
| 3.4  | `tests/test_collection_mcp_seller_lookup.py` | Integration   | ✅ 2/2     | already GREEN — shipped in 2.3; test would fail if branch missing | ✅ Passed (`UserError`)                                 | ✅ companion unique match (1.4) is the non-empty path                       | ➖ None needed                        |
| 3.5  | `tests/test_collection_mcp_seller_lookup.py` | Integration   | ✅ 2/2     | already GREEN — shipped in 2.3; test would fail if branch missing | ✅ Passed (`UserError`, no pick-first)                  | ✅ two internals vs unique (1.4) vs zero (3.4)                              | ➖ None needed                        |
| 3.6  | `tests/test_collection_mcp_seller_lookup.py` | Integration   | ✅ 2/2     | already GREEN — shipped in 2.3; test would fail if branch missing | ✅ Passed (internal `seller_id` only)                   | ✅ companion portal-only (3.7)                                              | ➖ None needed                        |
| 3.7  | `tests/test_collection_mcp_seller_lookup.py` | Integration   | ✅ 2/2     | already GREEN — shipped in 2.3; test would fail if branch missing | ✅ Passed (`UserError`, portal id not returned)         | ✅ companion mixed digits (3.6)                                             | ➖ None needed                        |
| 3.8  | `tests/test_collection_mcp_seller_lookup.py` | Integration   | ✅ 2/2     | already GREEN — shipped in 2.3; test would fail if branch missing | ✅ Passed (`UserError`)                                 | ✅ companion share-fail (3.7) vs missing `group_user`                       | ➖ None needed                        |
| 3.9  | `tests/test_collection_mcp_seller_lookup.py` | Unit (source) | ✅ 2/2     | already GREEN — shipped in 2.3; test would fail if branch missing | ✅ Passed (no `mobile_phone` / no `.sudo(`)             | ✅ Path file + `inspect.getsource(get_seller_id)`                           | ➖ None needed                        |

### Phase 4 (docs + verify)

| Task | Test File                    | Layer       | Safety Net                                 | RED                                                                                               | GREEN                                                                                                                                     | TRIANGULATE                                       | REFACTOR                                                 |
| ---- | ---------------------------- | ----------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- | -------------------------------------------------------- |
| 4.1  | `AGENTS.md`                  | Structural  | N/A (docs; production mixin already GREEN) | ✅ Docs written to required shape (read tool, no connector, `mobile` allowed, map/MCP/tests rows) | ✅ Structural — file updated; write-tool bullets preserved                                                                                | ➖ skipped: structural docs (one possible output) | ✅ Prettier wrapped AGENTS tables                        |
| 4.2  | `readme/DESCRIPTION.md`      | Structural  | N/A (docs)                                 | ✅ Short `get_seller_id` sentence added                                                           | ✅ Structural — fragment updated; `README.rst` regenerated                                                                                | ➖ skipped: structural docs (one possible output) | ➖ None needed                                           |
| 4.3  | N/A                          | Runtime     | Live stack present                         | ➖ N/A (install, not a new behavior test)                                                         | ✅ `invoke install -m collection` exit 0; doodba `addons init -w collection`; Modules loaded                                              | ➖ skipped: verification install                  | ➖ None needed                                           |
| 4.4  | `tests/test_collection_*.py` | Integration | Phase 3 11/11 seller-lookup GREEN          | ➖ N/A (verification of existing tests)                                                           | ✅ `/collection` **0 failed, 0 error(s) of 187 tests**; stats `collection: 211 tests`; all 11 `TestCollectionMcpSellerLookup` methods ran | ➖ skipped: verification, not new scenarios       | ✅ Four seller-lookup docstrings shortened for ruff E501 |

### Test Summary

- **Total tests written**: 11 (`2` Phase 1 + `9` Phase 3). None added in Phase 2 or 4.
- **Total tests passing**: 11 of 11 seller-lookup; full `/collection` **0 failed, 0
  error(s) of 187 tests** (Phase 4).
- **Layers used**: Integration (Odoo `TransactionCase`) (10), Unit/source inspect (1),
  Structural docs (2)
- **Approval tests** (refactoring): None — no refactoring tasks
- **Pure functions created**: 1 (`_collection_normalize_ar_mobile` on the mixin; Phase
  2). Phase 4 docs only.

## Work Unit Evidence

### Phase 4 (this batch)

| Evidence                                          | Required value                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `invoke start` then `docker exec -i seedian-odoo-1 odoo -d devel --test-enable --stop-after-init --workers=0 --http-port=18069 -u collection --test-tags /collection` → exit 0; **0 failed, 0 error(s) of 187 tests**; `collection: 211 tests 4.25s 6629 queries`. All 11 `TestCollectionMcpSellerLookup` methods started. First `invoke test -m collection` from Seedian root exited 0 but ran **0 tests** (`-i collection` on an already-installed module). |
| Runtime harness command/scenario and exact result | Seedian root `invoke install -m collection` → exit 0. Stopped live `seedian-odoo-1`, one-shot `odoo --stop-after-init --init collection`, `Modules loaded.`, shutdown.                                                                                                                                                                                                                                                                                        |
| Rollback boundary                                 | Drop `tools/seller_lookup.py`; revert `tools/__init__.py`, `tests/test_collection_mcp_seller_lookup.py`, `tests/__init__.py`, `AGENTS.md`, `readme/DESCRIPTION.md` (and regenerated `README.rst`). Do not revert `tools/collection_voucher.py` (untouched). No schema.                                                                                                                                                                                        |

### Phase 1–3 (preserved)

| Evidence                                          | Required value                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `docker exec -i seedian-odoo-1 odoo -d devel --test-enable --stop-after-init --workers=0 --http-port=18069 -u collection --test-tags /collection:TestCollectionMcpSellerLookup` → exit 0; **0 failed, 0 error(s) of 11 tests**. Phase 1–2 methods still ran. `--http-port=18069` because 8069 is held by the running Odoo process. First attempt this batch hit `SerializationFailure` (concurrent `-u` vs live stack); retry succeeded. |
| Runtime harness command/scenario and exact result | N/A until Phase 4 install — live-stack `invoke install -m collection` / docs verify remain Phase 4. Focused `-u collection` reloaded the test module.                                                                                                                                                                                                                                                                                    |
| Rollback boundary                                 | Revert Phase 3 methods and portal/public `setUpClass` users in `tests/test_collection_mcp_seller_lookup.py`. Keep Phase 1 discovery + unique-match tests, `tools/seller_lookup.py`, and `tools/__init__.py` import. Do not revert `tools/collection_voucher.py` (untouched). No schema.                                                                                                                                                  |

Phase 1 safety-net (preserved):
`docker exec -i seedian-odoo-1 odoo -d devel --test-enable --stop-after-init --workers=0 --http-port=18069 -u collection --test-tags /collection:TestCollectionMcpTool.test_tool_discovered_with_write_registry_and_schema`
→ **0 failed, 0 error(s) of 1 tests**.

Phase 1 RED (preserved): same focused seller-lookup command → exit 1; **1 failed, 1
error(s) of 2 tests**. Discovery FAIL: `'get_seller_id' not found`. Unique-match ERROR:
`UserError: Tool not found: get_seller_id`.

Phase 2 GREEN (preserved): same focused command → **0 failed, 0 error(s) of 2 tests**.

Phase 3 safety-net: same focused command before test edits → **0 failed, 0 error(s) of 2
tests**.

Phase 3 GREEN: same focused command after tests → **0 failed, 0 error(s) of 11 tests**.

Phase 4 lint: Seedian root scoped `pre-commit run --files` on this change’s paths → exit
0 (ruff, prettier, pylint_odoo, oca-gen-addon-readme). Assigned glob
`odoo/custom/src/private/collection/**` → exit 1 (ruff E501 in pre-existing
`test_collection_document_review.py`; prettier SyntaxError on archived `state.yaml`
duplicate `phase` keys; trailing-whitespace auto-fixed archive). Archive restored; glob
not re-run.

## Deviations from Design

None — implementation matches design. Sibling mixin, explicit `base.group_user`
AccessError, AR normalize (digits / strip `54` then one `9`), `share=False` + phone set

- default `active_test`, exact normalize filter, unique hit then existing
  `_collection_require_internal_seller`, success `{seller_id}` only, never `sudo()`, no
  generic MuK `search_read`. Phase 3 tests follow catalog portal **and** public
  `_create_user` and Path/`inspect` no-sudo / no-`mobile_phone`. Phase 4 docs match
  design file-change table.

Phase 4 process deviations (not design):

- Tokened `sdd-attempt acquire` returned `blocked: invalid_continuation`. Did not
  acquire blindly. Did not settle. Parent attempt remained `outcome: running`.
- `invoke test -m collection` used `-i` and reported 0 tests; used docker exec
  `-u collection --test-tags /collection` after `invoke start`.
- Assigned pre-commit `**` glob is not clean on this tree; linted this change’s files
  only after restoring archive.

## Issues Found

- `docker exec … odoo` on a live stack requires `--http-port` other than 8069
  (`Address already in use`). Focused tests used `--http-port=18069`.
- Unique-match RED (Phase 1) surfaced as **ERROR** (uncaught
  `UserError: Tool not found`) rather than assertion FAIL. GREEN now returns the
  expected JSON.
- Extra write-MCP discovery re-run after the mixin import was skipped in Phase 2
  (assigned gate is `TestCollectionMcpSellerLookup` only; `collection_voucher.py` was
  not edited).
- Phase 3 first `-u collection` hit
  `psycopg2.errors.SerializationFailure: could not serialize access due to concurrent update`
  against the live devel stack; retry of the same command succeeded.
- Phase 3 tests passed immediately (fail-closed already in 2.3). Production was not
  deleted to manufacture RED.
- `invoke install -m collection` stops live `seedian-odoo-1` (one-shot run container).
  Phase 4 tests required `invoke start` before `docker exec`.
- `invoke test -m collection` on an already-installed module ran 0 tests (`-i` not
  `-u`).
- `pre-commit --files collection/**` mutates `openspec/changes/archive/` (immutable
  audit trail) and fails on archived duplicate YAML keys plus pre-existing E501.

## Remaining Tasks

None — 20/20 tasks `[x]`. Ready for sdd-verify.

## Workload / PR Boundary

- Mode: single PR
- Current work unit: Phase 4 docs + install + `/collection` tests + lint
  (`get_seller_id` tests and docs)
- Boundary: starts after Phase 3 fail-closed tests GREEN; ends after 4.1–4.4 docs,
  `invoke install`, full `/collection` GREEN, scoped pre-commit clean. Does not start
  sdd-verify. Does not edit Nebula.
- Estimated review budget impact: docs + generated README; well under 400 lines for this
  slice.

## Status

20/20 tasks complete (Phase 4 of 4). Ready for sdd-verify.
