# Design: Seedian Nebula Module

## Technical Approach

Greenfield private Odoo 19 app `seedian_nebula` at
`odoo/custom/src/private/seedian_nebula/`. Voucher header + denormalized payment lines
mirror Nebula OCR (`schemas.py`); CRM-like backend UI, year sequence, mail
chatter/activities. No HTTP, website QWeb, or assets. Specs may land in parallel; source
of truth is `proposal.md`.

## Architecture Decisions

| Decision  | Options                   | Choice                                                       | Rationale                                          |
| --------- | ------------------------- | ------------------------------------------------------------ | -------------------------------------------------- |
| Module    | Extend webpage / new      | New `seedian_nebula` (`application=True`)                    | Isolates cobranzas; owned private only             |
| Depends   | `mail` / +`crm`           | `base`, `mail`                                               | Chatter without partner/CRM (deferred)             |
| Payments  | Child models / wide table | One `seedian.nebula.payment`                                 | Discriminator `document_type` matches Nebula union |
| Amount    | Float / Monetary          | Monetary + technical `currency_id` on voucher                | Required for Monetary UX                           |
| Sequence  | Manual / `ir.sequence`    | Code `seedian.nebula.voucher`, prefix `NEB/%(year)s/`, pad 4 | Same year pattern as core `LC/%(year)s/`           |
| Lifecycle | Stages / Selection        | `new`→`validated`\|`rejected`                                | Terminal buttons only; no reopen                   |
| ACLs      | Custom groups / internal  | Full CRUD `base.group_user`                                  | Approved plan; tighten later                       |
| License   | LGPL / AGPL               | `AGPL-3`                                                     | AGENTS.md for new private addons                   |

## Data Model

**`seedian.nebula.voucher`** (`mail.thread`, `mail.activity.mixin`): `name` (Char,
sequence on create, copy=False); `customer_identification` (Char, required, tracking);
`received_date` (Date, required, default today, tracking); `state` (Selection
new/validated/rejected, default new, tracking); `currency_id` (Many2one `res.currency`,
company default); `payment_ids` (One2many).

**`seedian.nebula.payment`**: `voucher_id` (M2O cascade); `document_type`
(`bank_transfer`\|`check`\|`cash_deposit`\|`unsupported`); `amount` (Monetary nullable);
`currency_id` related; `from_account`, `to_account`, `voucher_number` (Char);
`voucher_date` (Date); `check_number`, `check_bank` (Char); `check_issue_date`,
`check_payment_date` (Date); `check_type` (`common`\|`deferred`). `unsupported` = type
only. No OCR “≥1 field” constraints in v1.

## State Machine

```
new --action_validate--> validated
new --action_reject---> rejected
```

Buttons when `state == 'new'` (Odoo 19 `invisible=…`). Non-`new` → `UserError`.
Recommend `@api.ondelete` block unlink unless `new`.

## Data Flow

```
User → create voucher (sequence + defaults) → edit header/lines → Validate|Reject → tracked chatter
```

## Impacts (rules.design)

| Area                                    | Impact                                      |
| --------------------------------------- | ------------------------------------------- |
| Models                                  | New voucher + payment; sequence XML         |
| Views/menus                             | List/form/search; Nebula → Payment Vouchers |
| Security                                | `ir.model.access.csv` only; no record rules |
| Controllers / QWeb / assets / migration | None                                        |

## File Changes

Under `odoo/custom/src/private/seedian_nebula/`:

| File                                                                           | Action | Description                                                       |
| ------------------------------------------------------------------------------ | ------ | ----------------------------------------------------------------- |
| `__init__.py`, `__manifest__.py`                                               | Create | `19.0.1.0.0`; load security → sequence → views                    |
| `models/__init__.py`, `seedian_nebula_voucher.py`, `seedian_nebula_payment.py` | Create | ORM + validate/reject                                             |
| `data/ir_sequence_data.xml`                                                    | Create | `noupdate=1` sequence                                             |
| `security/ir.model.access.csv`                                                 | Create | CRUD both models for `base.group_user`                            |
| `views/seedian_nebula_views.xml`                                               | Create | Views, act_window, menus; statusbar; `<list>` lines; `<chatter/>` |
| `tests/__init__.py`, `test_seedian_nebula_voucher.py`                          | Create | Model tests                                                       |
| `readme/DESCRIPTION.rst`                                                       | Create | Fragment for `oca-gen-addon-readme`                               |

## Interfaces / Contracts

Names like `NEB/2026/0001` via `next_by_code('seedian.nebula.voucher')` when `name` in
`(False, '/', 'New')`.

## Testing Strategy

Strict TDD: RED `TransactionCase`/`SavepointCase` then GREEN. Cover sequence, defaults,
both terminal actions + UserError, persistence of every type-specific field incl.
`unsupported`. Run `invoke test -m seedian_nebula` + scoped pre-commit. No tours.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR, executable-classification, or
process-integration boundary.

## Migration / Rollout

No migration. Install `invoke install -m seedian_nebula`. Rollback: uninstall + remove
tree.

## Non-Goals

No HTTP API/webhooks, WhatsApp metadata, attachments, partner/CRM linkage, Nebula
agent/OCR calls.

## Open Questions

- [ ] Sequence padding 4 vs 5
- [ ] Confirm unlink blocked when `state != 'new'`
