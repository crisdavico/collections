```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:11f70166366390f25632df1c43790c8f7a678e38332535fdba38e9636a3fc2b3
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 5/5
scenarios: 10/10
test_command:
  docker exec -i seedian-odoo-1 odoo -d devel --test-enable --stop-after-init
  --workers=0 --http-port=18069 -u collection --test-tags /collection
test_exit_code: 0
test_output_hash: sha256:59372c3f8fe29151a8d8e55209a830a9b101ee2eea6d0d23d1db2bc65ff5fde5
build_command:
  pre-commit run --files odoo/custom/src/private/collection/tools/seller_lookup.py
  odoo/custom/src/private/collection/tools/__init__.py
  odoo/custom/src/private/collection/tests/test_collection_mcp_seller_lookup.py
  odoo/custom/src/private/collection/tests/__init__.py
  odoo/custom/src/private/collection/AGENTS.md
  odoo/custom/src/private/collection/readme/DESCRIPTION.md
  odoo/custom/src/private/collection/README.rst
build_exit_code: 0
build_output_hash: sha256:853d7823d5077eae53aee0e3b58fd0d4f95c4134504bc09aa51532f41f5a5773
```

## Verification Report

**Change**: get-seller-id-by-mobile **Version**: N/A (new capability `seller-lookup`; no
module version bump in this change) **Mode**: Strict TDD

Independent spec count from `specs/seller-lookup/spec.md`: **5 requirements / 10
scenarios**. Envelope completed counts are scenarios with a passing covering test at
this runtime.

`evidence_revision` is SHA-256 of exact test stdout+stderr concatenated with exact build
stdout+stderr (no separator).

`invoke img-build` is the config build command but is disproportionate: this slice is
Python/docs/tests inside collection, with no new Doodba image dependencies. Substitute
build is scoped `pre-commit run --files` on this change’s paths from Seedian root, as
assigned for verify.

`invoke test -m collection` uses `-i` and can run 0 tests on an already-installed
module. Envelope `test_command` is the docker exec
`-u collection --test-tags /collection` run whose full stdout+stderr is hashed. Live
stack holds 8069; this run used `--http-port=18069`. No SerializationFailure; no retry.

### Completeness

| Metric           | Value |
| ---------------- | ----- |
| Tasks total      | 20    |
| Tasks complete   | 20    |
| Tasks incomplete | 0     |

### Build & Tests Execution

**Build**: ✅ Passed (scoped pre-commit; `invoke img-build` skipped)

```text
pre-commit run --files odoo/custom/src/private/collection/tools/seller_lookup.py odoo/custom/src/private/collection/tools/__init__.py odoo/custom/src/private/collection/tests/test_collection_mcp_seller_lookup.py odoo/custom/src/private/collection/tests/__init__.py odoo/custom/src/private/collection/AGENTS.md odoo/custom/src/private/collection/readme/DESCRIPTION.md odoo/custom/src/private/collection/README.rst
exit 0
ruff, ruff format, prettier, trailing-whitespace, EOF, pylint_odoo, oca-gen-addon-readme: Passed
No hook reported "files were modified".
```

**Tests**: ✅ 194 passed / ❌ 0 failed / ⚠️ 0 skipped. Official command exit 0. Stats
line: `collection: 218 tests 4.08s 6726 queries`.

```text
docker exec -i seedian-odoo-1 odoo -d devel --test-enable --stop-after-init --workers=0 --http-port=18069 -u collection --test-tags /collection
exit 0
0 failed, 0 error(s) of 194 tests when loading database 'devel'
All 11 TestCollectionMcpSellerLookup methods started:
  test_ar_whatsapp_variants_match_same_seller
  test_empty_whitespace_or_invalid_mobile_rejected
  test_get_seller_id_discovered_as_method_read_mcp
  test_many_internal_matches_fail_closed_no_pick_first
  test_portal_and_public_callers_denied_access_error
  test_portal_only_digits_fail_closed
  test_portal_share_digits_excluded_returns_internal
  test_seller_lookup_source_omits_mobile_phone_and_sudo
  test_unique_hit_fails_seller_bar_without_group_user
  test_unique_internal_match_returns_seller_id_only
  test_zero_internal_matches_fail_closed
```

**Coverage**: ➖ Not available / threshold: 0% → not blocking (`openspec/config.yaml`
`coverage_threshold: 0`; no coverage tool)

### Spec Compliance Matrix

| Requirement                            | Scenario                                     | Test                                                                                                   | Result       |
| -------------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ------------ |
| Read-only MCP tool get_seller_id       | Unique internal match returns seller_id only | `tests/test_collection_mcp_seller_lookup.py` > `test_unique_internal_match_returns_seller_id_only`     | ✅ COMPLIANT |
| Caller authorization                   | Portal or public caller denied               | `tests/test_collection_mcp_seller_lookup.py` > `test_portal_and_public_callers_denied_access_error`    | ✅ COMPLIANT |
| Fail closed on empty or invalid mobile | Empty whitespace or invalid mobile rejected  | `tests/test_collection_mcp_seller_lookup.py` > `test_empty_whitespace_or_invalid_mobile_rejected`      | ✅ COMPLIANT |
| Phone-only AR WhatsApp identity        | AR variants match one seller                 | `tests/test_collection_mcp_seller_lookup.py` > `test_ar_whatsapp_variants_match_same_seller`           | ✅ COMPLIANT |
| Phone-only AR WhatsApp identity        | Employee mobile_phone is not a match field   | `tests/test_collection_mcp_seller_lookup.py` > `test_seller_lookup_source_omits_mobile_phone_and_sudo` | ✅ COMPLIANT |
| Unique internal match or fail closed   | Zero matches fail closed                     | `tests/test_collection_mcp_seller_lookup.py` > `test_zero_internal_matches_fail_closed`                | ✅ COMPLIANT |
| Unique internal match or fail closed   | Many internal matches fail closed            | `tests/test_collection_mcp_seller_lookup.py` > `test_many_internal_matches_fail_closed_no_pick_first`  | ✅ COMPLIANT |
| Unique internal match or fail closed   | Portal share digits excluded                 | `tests/test_collection_mcp_seller_lookup.py` > `test_portal_share_digits_excluded_returns_internal`    | ✅ COMPLIANT |
| Unique internal match or fail closed   | Portal-only digits fail closed               | `tests/test_collection_mcp_seller_lookup.py` > `test_portal_only_digits_fail_closed`                   | ✅ COMPLIANT |
| Unique internal match or fail closed   | Unique hit fails seller bar                  | `tests/test_collection_mcp_seller_lookup.py` > `test_unique_hit_fails_seller_bar_without_group_user`   | ✅ COMPLIANT |

Discovery (`category=read`, `registry=mcp`, `kind=method`, no DB `muk_mcp.tool` row) is
requirement body, not a separate scenario; covered by
`test_get_seller_id_discovered_as_method_read_mcp` (passed).

Employee `mobile_phone` coverage is source/`inspect` (design: no `hr` dependency) rather
than an `hr.employee` fixture. That is the covering test named in design and task 3.9;
it passed at runtime.

**Compliance summary**: 10/10 scenarios compliant

### Correctness (Static Evidence)

| Requirement                            | Status         | Notes                                                                                                                                                                                                  |
| -------------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Read-only MCP tool get_seller_id       | ✅ Implemented | `@mcp_tool(name="get_seller_id", category="read", registry="mcp")` on sibling `muk_mcp.mixin`; required `mobile`; success `{"seller_id": int}` only; unique-match test asserts voucher count unchanged |
| Caller authorization                   | ✅ Implemented | `AccessError` if caller lacks `base.group_user` before search                                                                                                                                          |
| Fail closed on empty or invalid mobile | ✅ Implemented | Normalize then empty needle → `UserError(_("mobile is required."))`                                                                                                                                    |
| Phone-only AR WhatsApp identity        | ✅ Implemented | Search `res.users` `phone` (`share=False`, non-empty); digits, strip leading `54` then one `9`; no `mobile_phone` / no `hr`                                                                            |
| Unique internal match or fail closed   | ✅ Implemented | `len(matches) != 1` → `UserError`; unique hit then `_collection_require_internal_seller`; portal/share rows excluded by `share=False`                                                                  |

### Coherence (Design)

| Decision                                                      | Followed? | Notes                                                     |
| ------------------------------------------------------------- | --------- | --------------------------------------------------------- |
| Sibling `tools/seller_lookup.py` `_inherit = "muk_mcp.mixin"` | ✅ Yes    | Imported from `tools/__init__.py`; write mixin not edited |
| AccessError first unless `base.group_user`                    | ✅ Yes    | Before normalize/search                                   |
| Phone-only search + exact normalize filter                    | ✅ Yes    | `search` + `filtered`; not ORM `=` / not `search_read`    |
| Reuse `_collection_require_internal_seller`                   | ✅ Yes    | Called with `matches.id` after unique hit                 |
| Never `sudo()` / no DB `muk_mcp.tool` row                     | ✅ Yes    | Source has no `.sudo(`; discovery test asserts no DB row  |
| Success JSON `{seller_id}` only                               | ✅ Yes    | Unique-match equality on exact dict                       |

### TDD Compliance

| Check                         | Result | Details                                                                                                                                                                                |
| ----------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TDD Evidence reported         | ✅     | Found in apply-progress (Phases 1–4 tables)                                                                                                                                            |
| All tasks have tests          | ✅     | 12/12 behavior tasks (1.3, 1.4, 2.3, 3.1–3.9) map to `tests/test_collection_mcp_seller_lookup.py`; 8 structural/docs/install tasks N/A                                                 |
| RED confirmed (tests exist)   | ⚠️     | Phase 1 RED observed (discovery not found / tool not found). Phase 3 tests exist but were added after production GREEN in 2.3; apply-progress records no observed RED fail for 3.1–3.9 |
| GREEN confirmed (tests pass)  | ✅     | 11/11 seller-lookup methods started; 0 failed, 0 error(s) of 194 tests                                                                                                                 |
| Triangulation adequate        | ✅     | Fail-closed inputs triangulated (portal+public; 4 invalid mobiles; AR two queries; unique vs zero vs many; mixed vs portal-only)                                                       |
| Safety Net for modified files | ✅     | Phase 1 safety-net write-tool 1/1; Phase 3 2/2 seller-lookup GREEN before fail-closed tests; new mixin/test files N/A (new)                                                            |

**TDD Compliance**: 5/6 checks passed (1 warning: Phase 3 RED not observed)

---

### Test Layer Distribution

| Layer       | Tests  | Files | Tools                                                                                           |
| ----------- | ------ | ----- | ----------------------------------------------------------------------------------------------- |
| Unit        | 1      | 1     | Odoo TransactionCase source/`inspect` (`test_seller_lookup_source_omits_mobile_phone_and_sudo`) |
| Integration | 10     | 1     | Odoo TransactionCase (`tool_model._call`, `get_tools` / `get_tool_index`)                       |
| E2E         | 0      | 0     | not installed                                                                                   |
| **Total**   | **11** | **1** |                                                                                                 |

Same file hosts both layers. Integration tools match `openspec/config.yaml`
capabilities.

---

### Changed File Coverage

Coverage analysis skipped — no coverage tool detected
(`testing.coverage.available: false`; `coverage_threshold: 0`).

---

### Assertion Quality

| File | Line | Assertion | Issue | Severity |
| ---- | ---- | --------- | ----- | -------- |
| —    | —    | —         | —     | —        |

**Assertion quality**: ✅ All assertions verify real behavior

No tautologies, ghost loops, or production-code-free asserts. `subTest` loops iterate
fixed tuples (2 callers, 4 invalid mobiles). `UserError` fail-closed tests have
companion unique-match success. Source `mobile_phone`/`sudo` asserts read
`tools/seller_lookup.py` and `inspect.getsource(get_seller_id)`. Unique-match asserts
exact `{"seller_id": id}`, positive int, and unchanged voucher count.

---

### Quality Metrics

**Linter**: ✅ No errors (scoped pre-commit: ruff, prettier, pylint_odoo, OCA README)
**Type Checker**: ➖ Not available

### Issues Found

**CRITICAL**: None **WARNING**: Phase 3 fail-closed tests (3.1–3.9) were written after
production GREEN in task 2.3; apply-progress did not record an observed RED failure for
those scenarios (Strict TDD process gap, not a runtime failure). **SUGGESTION**:
Scenario “Employee mobile_phone is not a match field” is proven by source omission
(design: no `hr`) rather than an `hr.employee` fixture that would exercise UserError on
a matching `mobile_phone`.

### Verdict

PASS WITH WARNINGS All 20 tasks complete; 10/10 spec scenarios have passing covering
tests; design decisions match `tools/seller_lookup.py`; collection tests and scoped
pre-commit exited 0. One Strict TDD process warning (Phase 3 RED not observed).
