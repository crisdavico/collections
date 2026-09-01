# Apply Progress: seedian-nebula-module

**Mode**: Strict TDD **Work unit**: Unit 3 / Phase 3 / PR 3 (stacked-to-main) —
cumulative with Units 1–2 **Branch**: `sdd/seedian-nebula-module-pr3` (from
`sdd/seedian-nebula-module-pr2`) **Updated**: 2026-08-10 **Remediation**: Menu and form
behaviors UNTESTED → COMPLIANT via `test_seedian_nebula_ui.py`

## Completed Tasks

### Phase 1 (Unit 1 / PR 1) — preserved

- [x] 1.1 RED: sequence `NEB/<year>/<n>`, unique name on create
- [x] 1.2 RED: defaults + required `customer_identification` / `received_date`
- [x] 1.3 RED: validate/reject from `new`; UserError on terminal; unlink blocked when
      not `new`
- [x] 1.4 RED: persist Nebula payment fields + unsupported/partial lines
- [x] 1.5 GREEN: scaffold `__manifest__.py` / `__init__.py` (`19.0.1.0.0`, depends
      `base`/`mail`, AGPL-3)
- [x] 1.6 GREEN: voucher + payment models; sequence create; validate/reject;
      `@api.ondelete`
- [x] 1.7 GREEN: `data/ir_sequence_data.xml` (`seedian.nebula.voucher`, `NEB/%(year)s/`,
      pad 4, `noupdate=1`)
- [x] 1.8 Prove: `invoke test -m seedian_nebula` → `0 failed, 0 error(s) of 13 tests`

### Phase 2 (Unit 2 / PR 2) — preserved

- [x] 2.1 RED: internal `base.group_user` CRUD ACL allow; non-internal deny (voucher +
      payment)
- [x] 2.2 RED: mail thread/activity create + state-change tracking on validate/reject
- [x] 2.3 GREEN: `security/ir.model.access.csv` full CRUD both models for
      `base.group_user`
- [x] 2.4 GREEN: `views/seedian_nebula_views.xml` — list/search/form, statusbar,
      buttons, `<list>` lines, `<chatter/>`, Nebula → Payment Vouchers
- [x] 2.5 GREEN: `readme/DESCRIPTION.rst` fragment
- [x] 2.6 Prove: `invoke test -m seedian_nebula --mode=update` →
      `0 failed, 0 error(s) of 21 tests`

### Phase 3 (Unit 3 / PR 3) — this batch (verify-only)

- [x] 3.1 `invoke install -m seedian_nebula` → exit 0; module `state=installed`, version
      `19.0.1.0.0`
- [x] 3.2 Scoped pre-commit on `odoo/custom/src/private/seedian_nebula/**` → exit 0
      after E501 fix
- [x] 3.3 Spot-check: menu Nebula → Payment Vouchers; form arch has statusbar / Validate
      / Reject / payment `<list>` / `<chatter/>` (odoo shell + user-odoo MCP)

### Remediation (verify FAIL blocker) — Menu and form behaviors

- [x] R1 RED: `tests/test_seedian_nebula_ui.py` — menu XML-IDs, act_window, list/search
      required fields, form statusbar/Validate/Reject/editable
      `payment_ids`/`<chatter/>` with voucher in `new`
- [x] R1 GREEN: existing `views/seedian_nebula_views.xml` already satisfied assertions —
      **no production view edits**
- [x] R1 Prove: `invoke test -m seedian_nebula --mode=update` →
      `0 failed, 0 error(s) of 24 tests` (21 prior + 3 UI)

## Files Changed

### Phase 1 (preserved)

| File                                                                          | Action  | What Was Done                                    |
| ----------------------------------------------------------------------------- | ------- | ------------------------------------------------ |
| `odoo/custom/src/private/seedian_nebula/__init__.py`                          | Created | Module package init                              |
| `odoo/custom/src/private/seedian_nebula/__manifest__.py`                      | Created | App manifest 19.0.1.0.0, base+mail, AGPL-3       |
| `odoo/custom/src/private/seedian_nebula/models/__init__.py`                   | Created | Model imports                                    |
| `odoo/custom/src/private/seedian_nebula/models/seedian_nebula_voucher.py`     | Created | Voucher + lifecycle + sequence create + ondelete |
| `odoo/custom/src/private/seedian_nebula/models/seedian_nebula_payment.py`     | Created | Denormalized Nebula payment lines                |
| `odoo/custom/src/private/seedian_nebula/data/ir_sequence_data.xml`            | Created | Year sequence pad 4                              |
| `odoo/custom/src/private/seedian_nebula/tests/__init__.py`                    | Created | Test package                                     |
| `odoo/custom/src/private/seedian_nebula/tests/test_seedian_nebula_voucher.py` | Created | TransactionCase coverage for Unit 1              |

### Phase 2 (preserved)

| File                                | Action   | What Was Done                                                                                |
| ----------------------------------- | -------- | -------------------------------------------------------------------------------------------- |
| `tests/test_seedian_nebula_acl.py`  | Created  | ACL allow/deny TransactionCase (voucher + payment)                                           |
| `tests/test_seedian_nebula_mail.py` | Created  | message_post, activity_schedule, validate/reject tracking                                    |
| `tests/__init__.py`                 | Modified | Import ACL + mail test modules                                                               |
| `security/ir.model.access.csv`      | Created  | Full CRUD both models for `base.group_user`                                                  |
| `views/seedian_nebula_views.xml`    | Created  | List/search/form, statusbar, Validate/Reject, payment `<list>`, `<chatter/>`, menus          |
| `readme/DESCRIPTION.rst`            | Created  | OCA readme fragment                                                                          |
| `__manifest__.py`                   | Modified | data: security → sequence → views                                                            |
| `models/seedian_nebula_voucher.py`  | Modified | Minimal fix: `action_validate`/`action_reject` use `write({'state': ...})` for mail tracking |

### Phase 3 (this batch — verify-only + tiny pre-commit fixes)

| File                                | Action         | What Was Done                                                         |
| ----------------------------------- | -------------- | --------------------------------------------------------------------- |
| `tests/test_seedian_nebula_mail.py` | Modified       | Shortened `_flush_tracking` docstring (ruff E501)                     |
| `readme/DESCRIPTION.md`             | Created (hook) | `oca-gen-addon-readme` replaced `DESCRIPTION.rst` with `.md` fragment |
| `README.rst`                        | Created (hook) | Generated by `oca-gen-addon-readme` during scoped pre-commit          |
| `openspec/.../tasks.md`             | Modified       | Marked 3.1–3.3 `[x]`                                                  |
| `openspec/.../apply-progress.md`    | Modified       | Cumulative Phase 1–3 evidence                                         |

### Remediation (Menu and form behaviors coverage)

| File                              | Action   | What Was Done                                                                                  |
| --------------------------------- | -------- | ---------------------------------------------------------------------------------------------- |
| `tests/test_seedian_nebula_ui.py` | Created  | TransactionCase: menu/action XML-IDs, list/search fields, form statusbar/buttons/lines/chatter |
| `tests/__init__.py`               | Modified | Import `test_seedian_nebula_ui`                                                                |
| `openspec/.../tasks.md`           | Modified | Added remediation R1 checkbox `[x]` (did not uncheck completed tasks)                          |
| `openspec/.../apply-progress.md`  | Modified | Appended remediation TDD + prove evidence                                                      |

## TDD Cycle Evidence

### Phase 1 (preserved)

| Task    | Test File                              | Layer                  | Safety Net | RED                                      | GREEN                                   | TRIANGULATE | REFACTOR                    |
| ------- | -------------------------------------- | ---------------------- | ---------- | ---------------------------------------- | --------------------------------------- | ----------- | --------------------------- |
| 1.1     | `tests/test_seedian_nebula_voucher.py` | Unit (TransactionCase) | N/A (new)  | ✅ Written (sequence + unique)           | ✅ Passed                               | ✅ 2 cases  | ✅ Clean                    |
| 1.2     | same                                   | Unit                   | N/A (new)  | ✅ Written (defaults + required)         | ✅ Passed (IntegrityError for required) | ✅ 3 cases  | ✅ Clean                    |
| 1.3     | same                                   | Unit                   | N/A (new)  | ✅ Written (validate/reject/unlink)      | ✅ Passed                               | ✅ 5 cases  | ✅ Clean UserError messages |
| 1.4     | same                                   | Unit                   | N/A (new)  | ✅ Written (type-specific + unsupported) | ✅ Passed                               | ✅ 3 cases  | ➖ None needed              |
| 1.5–1.7 | (impl)                                 | —                      | N/A (new)  | Covered by 1.1–1.4 RED                   | ✅ Module loads + tests green           | —           | ✅ Minor message cleanup    |
| 1.8     | prove                                  | Integration harness    | —          | —                                        | ✅ `invoke test -m seedian_nebula`      | —           | —                           |

### Phase 2 (preserved)

| Task | Test File                           | Layer                  | Safety Net                   | RED                                                  | GREEN                                                   | TRIANGULATE                                      | REFACTOR                                   |
| ---- | ----------------------------------- | ---------------------- | ---------------------------- | ---------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------------ | ------------------------------------------ |
| 2.1  | `tests/test_seedian_nebula_acl.py`  | Unit (TransactionCase) | ✅ Phase 1 13/13 still green | ✅ Written; internal create → AccessError before ACL | ✅ Passed after CSV                                     | ✅ 4 cases (voucher+payment × allow+deny)        | ✅ User factory for account.autopost_bills |
| 2.2  | `tests/test_seedian_nebula_mail.py` | Unit (TransactionCase) | ✅ Same                      | ✅ Written; tracking empty until flush+write         | ✅ Passed (`write` + `cr.flush`)                        | ✅ 4 cases (message, activity, validate, reject) | ✅ `_flush_tracking` helper                |
| 2.3  | (impl)                              | —                      | —                            | Covered by 2.1 RED                                   | ✅ ACL CSV loaded                                       | —                                                | ➖ Structural                              |
| 2.4  | (impl)                              | —                      | —                            | Views structural; UI spot-check → Phase 3            | ✅ XML loads; RNG fix (no `expand` on search `<group>`) | ➖ Structural                                    | ✅ Search group attrs                      |
| 2.5  | (impl)                              | —                      | —                            | Triangulation skipped: readme fragment only          | ✅ Fragment present                                     | ➖ Structural                                    | ➖ None needed                             |
| 2.6  | prove                               | Integration harness    | —                            | —                                                    | ✅ `0 failed, 0 error(s) of 21 tests`                   | —                                                | —                                          |

### Phase 3 (this batch — verify-only)

| Task | Test File            | Layer           | Safety Net      | RED        | GREEN                                                               | TRIANGULATE | REFACTOR                  |
| ---- | -------------------- | --------------- | --------------- | ---------- | ------------------------------------------------------------------- | ----------- | ------------------------- |
| 3.1  | N/A (install verify) | Runtime harness | ✅ Prior 21/21  | N/A verify | ✅ `invoke install -m seedian_nebula` exit 0; MCP `state=installed` | N/A         | N/A                       |
| 3.2  | N/A (lint)           | Quality         | ✅ Module tree  | N/A verify | ✅ scoped pre-commit exit 0 after E501                              | N/A         | ✅ Docstring shorten only |
| 3.3  | N/A (UI spot-check)  | Runtime/DB      | ✅ Views loaded | N/A verify | ✅ shell + MCP menu/form arch assertions                            | N/A         | N/A                       |

### Remediation R1 — Menu and form behaviors (STRICT TDD)

| Task | Test File                         | Layer                                | Safety Net              | RED                                                              | GREEN                                                 | TRIANGULATE                                                                                       | REFACTOR       |
| ---- | --------------------------------- | ------------------------------------ | ----------------------- | ---------------------------------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------- | -------------- |
| R1   | `tests/test_seedian_nebula_ui.py` | Unit (TransactionCase registry/arch) | ✅ 0 failed of 21 prior | ✅ Written first (3 methods; views exist, scenario was UNTESTED) | ✅ Passed without view edits — arch already compliant | ✅ 3 cases: menu/action; list+search fields; form statusbar/buttons/lines/chatter + voucher `new` | ➖ None needed |

### Test Summary

- **Total tests written (cumulative)**: 24 methods (13 Phase 1 + 4 ACL + 4 mail + 3 UI
  remediation)
- **Total tests passing**: 24
  (`0 failed, 0 error(s) of 24 tests when loading database 'devel'`) after UI
  remediation
- **Layers used**: Unit/TransactionCase (24), Integration via containerized
  `invoke test --mode=update`, Runtime install + UI XML-ID spot-check
- **Approval tests**: None
- **Pure functions created**: 0
- **Phase 3 TDD**: N/A for pure verify tasks (install / pre-commit / spot-check)
- **Remediation TDD**: Strict TDD RED→GREEN for Menu and form behaviors; triangulation
  via three distinct assertion surfaces

## Work Unit Evidence

### Unit 1 (preserved)

| Evidence                              | Value                                                                                |
| ------------------------------------- | ------------------------------------------------------------------------------------ |
| Focused test command and exact result | `invoke test -m seedian_nebula` → exit 0; `0 failed, 0 error(s) of 13 tests`         |
| Runtime harness                       | Module install path via `invoke test`; dedicated `invoke install` deferred to Unit 3 |
| Rollback boundary                     | Remove models/data/tests/manifest scaffold                                           |

### Unit 2 (preserved)

| Evidence                                          | Value                                                                                                                                                                                            |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Focused test command and exact result             | `invoke test -m seedian_nebula --mode=update` → exit 0; `0 failed, 0 error(s) of 21 tests when loading database 'devel'`                                                                         |
| Runtime harness command/scenario and exact result | ACL + mail TransactionCase prove via same invoke harness; menu/form UI spot-check deferred to Phase 3 task 3.3                                                                                   |
| Rollback boundary                                 | Remove/revert `security/`, `views/`, `readme/`, ACL/mail tests, manifest data list entries, and the minimal `action_validate`/`action_reject` → `write()` change without removing Phase 1 models |

### Unit 3 (this batch)

| Evidence                                          | Value                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `invoke test -m seedian_nebula --mode=update` → exit 0; `0 failed, 0 error(s) of 21 tests when loading database 'devel'` (post E501 docstring fix)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| Runtime harness command/scenario and exact result | **3.1** `invoke install -m seedian_nebula` → exit 0; shell/MCP: `ir.module.module` name=`seedian_nebula` state=`installed` latest=`19.0.1.0.0`. **3.2** `pre-commit run --files $(find odoo/custom/src/private/seedian_nebula -type f)` → first run failed ruff E501 on mail test docstring; after shorten → exit 0 (optional pylint C8101 Eynes author warning only; mandatory pylint passed). Hook also generated `README.rst` and converted fragment to `readme/DESCRIPTION.md`. **3.3** docker `odoo shell` + user-odoo MCP: menus `Nebula` (id 371) → child `Payment Vouchers` (id 372, action `ir.actions.act_window,534`); form view id 2311 arch contains `widget="statusbar"`, `action_validate`, `action_reject`, `payment_ids` + `<list editable="bottom">`, `<chatter/>`. Browser URL (not opened): `http://localhost:19069` (devel `PORT_PREFIX` default 19 → 19069). |
| Rollback boundary                                 | Verify-only: uninstall `seedian_nebula`; revert Phase 3 docstring / generated README + DESCRIPTION.md if undesired; no model/view feature rewrites                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |

### Remediation R1 (Menu and form behaviors)

| Evidence                                          | Value                                                                                                                                                   |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command and exact result             | `invoke test -m seedian_nebula --mode=update` → exit 0; `0 failed, 0 error(s) of 24 tests when loading database 'devel'` (3 new: `TestSeedianNebulaUi`) |
| Runtime harness command/scenario and exact result | N/A — registry/arch TransactionCase is the specified coverage layer (no browser E2E); views already installed from Unit 2/3                             |
| Rollback boundary                                 | Remove `tests/test_seedian_nebula_ui.py` and its import in `tests/__init__.py`; no production view/model changes in this remediation                    |

## Deviations from Design

- Required-field rejection on bare `create()` surfaces as `psycopg2.IntegrityError` (DB
  NOT NULL) in Odoo 19 (Phase 1).
- `action_validate`/`action_reject` use `self.write({"state": ...})` instead of
  attribute assignment so `mail.thread` precommit tracking records state changes (Phase
  2 test-forced minimal model fix).
- Search view omits deprecated `expand`/`string` on `<group>` (Odoo 19 RNG); CRM-style
  plain `<group>` with group_by filters.
- ACL tests create partners with an `autopost_bills` fallback for devel DBs where
  account left a NOT NULL column.
- Phase 3: `oca-gen-addon-readme` emitted `README.rst` and `readme/DESCRIPTION.md`
  (replacing the Phase 2 `.rst` fragment) during scoped pre-commit — accepted as hook
  side-effect, not a design deviation.

## Issues Found

- Default `invoke test` (`mode=init`) may skip re-running tests if the module is already
  installed; use `--mode=update` (as in 2.6 / 3.x) or uninstall+init.
- Odoo 19 search RNG rejects `expand` on `<group>` (ParseError until removed).
- Scoped pre-commit initially failed on ruff E501 in `test_seedian_nebula_mail.py`
  docstring (fixed).
- Optional pylint warns `manifest-required-author` expects `Eynes`; mandatory pylint
  passed — left as-is (no design/author change for verify slice).

## Remaining Tasks

- None — all Phase 1–3 tasks and remediation R1 marked `[x]`. Next: re-run `sdd-verify`.

## Workload / PR Boundary

- Mode: stacked PR slice (Unit 3 / PR 3)
- Current work unit: Unit 3 — install prove + scoped pre-commit + UI spot-check
- Boundary: starts after Phase 2 UI/security; ends with verify evidence + tiny
  lint/readme hook artifacts only; no model/view feature rewrites
- Chain strategy: stacked-to-main (`sdd/seedian-nebula-module-pr3` after PR2)
- Estimated review budget impact: verify-only; tiny diff (docstring + generated README
  fragments)
