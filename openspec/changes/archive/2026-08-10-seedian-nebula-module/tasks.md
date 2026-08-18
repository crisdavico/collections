# Tasks: Seedian Nebula Module

Defaults (non-blocking): sequence `padding=4`; `@api.ondelete` blocks unlink unless
`state == 'new'`. Threat matrix: N/A.

## Review Workload Forecast

| Field                   | Value                                                          |
| ----------------------- | -------------------------------------------------------------- |
| Estimated changed lines | ~550–900                                                       |
| 400-line budget risk    | High                                                           |
| Chained PRs recommended | Yes                                                            |
| Suggested split         | PR1 models+tests → PR2 UI/security+ACL tests → PR3 verify/docs |
| Delivery strategy       | ask-on-risk                                                    |
| Chain strategy          | stacked-to-main                                                |

Decision needed before apply: No Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

### Suggested Work Units

| Unit | Goal                                      | Likely PR | Focused test command            | Runtime harness                     | Rollback boundary                                                |
| ---- | ----------------------------------------- | --------- | ------------------------------- | ----------------------------------- | ---------------------------------------------------------------- |
| 1    | Scaffold + models + sequence + core tests | PR 1      | `invoke test -m seedian_nebula` | `invoke install -m seedian_nebula`  | `odoo/custom/src/private/seedian_nebula/{models,data,tests,__*}` |
| 2    | ACL + views/menus + ACL tests + readme    | PR 2      | `invoke test -m seedian_nebula` | Open Nebula → Payment Vouchers form | `security/`, `views/`, `readme/`                                 |
| 3    | Upgrade + scoped pre-commit               | PR 3      | `invoke test -m seedian_nebula` | `invoke install -m seedian_nebula`  | verify-only; uninstall module                                    |

Resolved: stacked-to-main (PR1 → merge to main → PR2 → merge → PR3).

## Phase 1: Scaffold + models (PR 1)

- [x] 1.1 RED: `tests/test_seedian_nebula_voucher.py` — sequence `NEB/<year>/<n>`,
      unique name on create
- [x] 1.2 RED: defaults (`received_date` today, `state=new`, company currency); required
      `customer_identification`/`received_date`
- [x] 1.3 RED: `action_validate`/`action_reject` from `new`; `UserError` on terminal;
      unlink blocked when not `new`
- [x] 1.4 RED: persist `bank_transfer`/`check`/`cash_deposit` Nebula fields +
      `unsupported`/partial lines
- [x] 1.5 GREEN: scaffold `__manifest__.py`/`__init__.py` (`19.0.1.0.0`, depends
      `base`/`mail`, AGPL-3)
- [x] 1.6 GREEN: `models/seedian_nebula_voucher.py` + `seedian_nebula_payment.py` per
      design; sequence create; validate/reject; ondelete
- [x] 1.7 GREEN: `data/ir_sequence_data.xml` code `seedian.nebula.voucher`, prefix
      `NEB/%(year)s/`, pad 4, `noupdate=1`
- [x] 1.8 Prove: `invoke test -m seedian_nebula` (Unit 1 cases green)

## Phase 2: UI + security (PR 2)

- [x] 2.1 RED: internal `base.group_user` CRUD ACL allow; non-internal deny (voucher +
      payment)
- [x] 2.2 RED: mail thread/activity create + state-change tracking on validate/reject
- [x] 2.3 GREEN: `security/ir.model.access.csv` full CRUD both models for
      `base.group_user`
- [x] 2.4 GREEN: `views/seedian_nebula_views.xml` — list/search/form, statusbar,
      Validate/Reject `invisible` when not `new`, `<list>` lines, `<chatter/>`, Nebula →
      Payment Vouchers
- [x] 2.5 GREEN: `readme/DESCRIPTION.rst` fragment
- [x] 2.6 Prove: `invoke test -m seedian_nebula` (ACL + mail cases)

## Phase 3: Verify (PR 3)

- [x] 3.1 `invoke install -m seedian_nebula` (or `-u` if already installed)
- [x] 3.2 Scoped pre-commit on `odoo/custom/src/private/seedian_nebula/**`
- [x] 3.3 Spot-check: menu opens; form shows statusbar/buttons/lines/chatter

## Remediation (verify FAIL — Menu and form behaviors UNTESTED)

- [x] R1 RED/GREEN: `tests/test_seedian_nebula_ui.py` TransactionCase covers menu
      XML-IDs, act_window, list/search fields, form statusbar/Validate/Reject/editable
      lines/`<chatter/>` (no view edits — arch already compliant)
