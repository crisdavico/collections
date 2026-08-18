# Proposal: Seedian Nebula Module

## Intent

Give internal Seedian users an Odoo app to manually register and review payment vouchers
(bank transfer, check, cash deposit) with CRM-style tracking—sequence naming,
New→Validated/Rejected lifecycle, chatter/activities, and payment lines aligned to
Nebula’s OCR schema—without WhatsApp/agent integration yet.

**User impact**: operators create, edit, validate, or reject vouchers in Odoo today;
later Nebula ingestion can map into the same models.

**Affected module**: new owned addon `seedian_nebula` only (`base`, `mail`).

## Scope

### In Scope

- Installable app at `odoo/custom/src/private/seedian_nebula/`
- Models `seedian.nebula.voucher` and `seedian.nebula.payment` (full Nebula extraction
  fields, including `unsupported`)
- Sequence `NEB/<year>/<number>`; CRM-like list/form/search; top-level Nebula → Payment
  Vouchers
- Internal-user full CRUD ACLs; model tests; `readme/DESCRIPTION.rst`

### Out of Scope

- HTTP API, WhatsApp metadata, attachments, partner/CRM linkage, Nebula agent calls

## Capabilities

### New Capabilities

- `seedian-nebula-vouchers`: Voucher header lifecycle (sequence name, customer
  identification, received date, state transitions, mail thread/activities, currency,
  payment one2many); payment lines for `bank_transfer` | `check` | `cash_deposit` |
  `unsupported` with fields `amount`, `from_account`, `to_account`, `voucher_number`,
  `voucher_date`, `check_number`, `check_bank`, `check_issue_date`,
  `check_payment_date`, `check_type`; backend UI, ACLs, and tests.

### Modified Capabilities

- None

## Approach

Scaffold a private Odoo 19 app with ORM models (`mail.thread`, `mail.activity.mixin`),
`ir.sequence` data, XML views/menus, and `ir.model.access.csv` for `base.group_user`.
Persist Nebula OCR fields as nullable columns on one payment model keyed by
`document_type`. Strict TDD: RED tests for sequence, defaults, terminal actions, and
type-specific fields before GREEN; verify with `invoke test -m seedian_nebula` and
scoped pre-commit.

## Affected Areas

| Area                                      | Impact   | Description                                                   |
| ----------------------------------------- | -------- | ------------------------------------------------------------- |
| `odoo/custom/src/private/seedian_nebula/` | New      | Module scaffold, models, data, views, security, tests, readme |
| `openspec/specs/`                         | None yet | First main specs land at archive from this change             |

## Risks

| Risk                                    | Likelihood | Mitigation                                                        |
| --------------------------------------- | ---------- | ----------------------------------------------------------------- |
| OCR schema drift vs Nebula `schemas.py` | Med        | Mirror current contract; defer sync until API phase               |
| Wide ACL (all internal users)           | Low        | Matches approved plan; tighten later with groups if needed        |
| Review size >400 lines                  | Med        | delivery_strategy `ask-on-risk`; chain PRs if tasks forecast high |

## Rollback Plan

Uninstall `seedian_nebula` (drops its models/data). Remove the addon from the private
tree and redeploy. No other modules or Copier/git-aggregate files are touched.

## Dependencies

- Odoo 19 + `mail`; Nebula `schemas.py` as field contract reference only (no runtime
  link)

## Success Criteria

- [ ] Module installs; Nebula menu opens Payment Vouchers
- [ ] New vouchers get `NEB/<year>/<number>`, today as `received_date`, state `new`
- [ ] Validate/Reject only from `new`; chatter/activities work
- [ ] Payment lines persist all type-specific Nebula fields including `unsupported`
- [ ] `invoke test -m seedian_nebula` and scoped pre-commit pass
