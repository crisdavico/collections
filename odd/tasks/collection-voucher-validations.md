# Collection Voucher Validations

## Objective

Harden the cobranza workflow so a payment voucher cannot be registered twice, cannot
carry incoherent instrument data, and cannot allocate more money than was actually
collected. Register the company's own bank accounts so transfers and cash deposits can
be matched against them.

## Problem

Today `collection.voucher` has exactly one uniqueness rule: `UNIQUE(document_id)`
(`models/collection_voucher.py:213`), the external idempotency key. Nothing prevents the
same physical check, transfer reference or deposit slip from being loaded twice through
the UI or the MCP path. `amount` has no positive check. Check dates are never validated
against each other. `voucher_date` may be in the future. Allocations may apply more
money than the sheet actually collected, and that mismatch is only flagged cosmetically
in the sheet report. No company bank account exists anywhere in the addon, so
`from_account` / `to_account` are unverifiable free text.

## Why

Duplicate and incoherent vouchers inflate what a customer appears to have paid. That
propagates into allocations, receipts and the ERP hand-off, and today it is only caught
by a human reading a PDF.

## Scope

**Authorized:** `odoo/custom/src/private/collection/` only.

**In scope**

- Positive-amount rule on `collection.voucher`.
- `check_number` mandatory at save for `check` / `echeck`, plus duplicate rejection.
- Per-type duplicate identity for `bank_transfer`, `cash_deposit`,
  `retention_certificate`; `cash` explicitly exempt.
- Check date coherence (`common` vs `deferred`).
- `voucher_date` / `check_issue_date` not in the future.
- Allocation `total_applied` must not exceed `total_vouchers` (money collected).
- Company bank accounts surfaced through core `res.partner.bank` and matched against
  `to_account` for transfers and deposits.

**Explicitly out of scope (user decision)**

- Over-allocation against customer debt stays ALLOWED. `allocation.residual` may remain
  negative. Do not add a `total_applied <= total_debt` rule. Do not cap
  `allocation.line.amount_applied` at `invoice_balance`.
- No new field on `res.company` for bank data; core `res.company.bank_ids` (related to
  `partner_id.bank_ids`) is used instead.
- No behaviour flags added to the `collection.document.type` catalog. Per-type knowledge
  stays in Python dicts, following the existing `_TYPE_OWNED_FIELDS` convention in
  `tools/collection_voucher.py:35`.

## Constraints

- Odoo 19: `models.Constraint` / `models.Index` / `models.UniqueIndex`
  (`odoo/orm/table_objects.py`), never `_sql_constraints`. `<list>` not `<tree>`.
- `models.UniqueIndex("(cols) WHERE cond", "message")` is the only way to express a
  partial unique index. It applies via `pool.post_constraint`, so it degrades to a
  warning on dirty production data instead of failing the upgrade.
- A production dump exists (`prod.sql.gz`). Prefer Python `@api.constrains` for rules
  that could retroactively reject existing rows; reserve DB-level rules for cases where
  a race matters.
- `document_type == "unsupported"` owns no instrument fields
  (`tools/collection_voucher.py:66`) and must stay exempt from amount and instrument
  rules.
- User-facing strings in English wrapped in `_()`; Spanish ships via `i18n/es_AR.po`.
- Migration folders are pinned by a leftover scanner. Only add one for a real
  stored-data change, and never a version AGENTS.md forbids.
- Commit prefix: `[IMP|ADD|FIX] collection: <summary>`.

## Resolved decisions

| Decision                        | Value                                              | Source                                            |
| ------------------------------- | -------------------------------------------------- | ------------------------------------------------- |
| `check_number` enforcement point | At save (create/write)                            | User, this session                                |
| Over-allocation vs debt         | Allowed, unchanged                                 | User, this session                                |
| Company bank storage            | Core `res.partner.bank` via `res.company.bank_ids` | User, this session                                |
| Per-type rule location          | Python dict, `tools/collection_voucher.py`         | Orchestrator, follows existing code               |
| TDD mode                        | Strict — RED before GREEN                          | `openspec/config.yaml: strict_tdd: true` + CLAUDE.md |
| Test runner                     | `invoke test -m collection --mode=update`          | `openspec/config.yaml`                            |
| Delivery strategy               | `ask-on-risk`                                      | `openspec/config.yaml`                            |
| Chain strategy                  | `stacked-to-main`                                  | `openspec/config.yaml`                            |

## Known breaking change

`check_number` becomes mandatory for `check` / `echeck`. It is currently declared
`nullable: true` in the MCP schema (`tools/collection_voucher.py:118`) and listed in
`_PAYMENT_OPTIONAL_FIELDS`. The Nebula Collections Agent (separate repo) will receive
`UserError` for check payments sent without a number. Needs a coordinated deploy.

Because `check_number` is shared by all nine document types, field-level `required=True`
is not expressible. "Mandatory at save" is implemented as an `@api.constrains` that
fires on create/write, plus a conditional `required=` in the form view for UX. Net
effect matches the decision: the save is blocked.

## Delivery

Forecast ~1200 authored changed lines across 5 work units — over the ~400-line budget,
so it slices into a stacked chain off `main`. Branch: `feat/voucher-validations`.

| Slice | Work units | PR      |
| ----- | ---------- | ------- |
| 1     | T1         | pending |
| 2     | T2, T3     | pending |
| 3     | T4         | pending |
| 4     | T5         | pending |

## Tasks

- [x] **T1 — Positive amounts and coherent voucher dates** — DONE.
  Verified `1 failed, 0 error(s) of 1012 tests` (the 1 is the known pre-existing
  failure). Baseline was `1 failed of 1003`; 9 tests added.
  - `@api.constrains("amount", "document_type")`: `amount > 0` for every type except
    `unsupported`.
  - `@api.constrains` on check dates: `check_issue_date <= check_payment_date`;
    `check_type == "deferred"` requires `check_payment_date` strictly after
    `check_issue_date`; `check_type == "common"` must not carry a later payment date.
  - `@api.constrains`: `voucher_date` and `check_issue_date` must not be in the future
    relative to the company's today.
  - Tests in `tests/test_collection_voucher.py`.
  - Route: delegated writer (2+ non-trivial files). Trigger: writer rule.

- [x] **T2 — Mandatory check number and check duplicate rejection** — DONE.
  Verified `1 failed, 0 error(s) of 1034 tests`. Two findings worth keeping:
  Odoo runs `@api.constrains` AFTER the INSERT, so the paired `UniqueIndex` won the
  race and users saw a raw `psycopg2.UniqueViolation` instead of a readable error.
  Duplicate detection is now a value-based precheck called from `create()`/`write()`,
  with the index demoted to a pure concurrency backstop. Normalization is
  `str.strip(" ")` in Python and `btrim()` in SQL — spaces only, deliberately matched
  so the two definitions of "same number" cannot drift apart.
  Blast radius: 11 fixtures across 6 further files, swept.
  - `@api.constrains("document_type", "check_number")`: non-empty for `check`/`echeck`.
  - Duplicate rule on normalised `check_number`, scoped per company, for
    `check`/`echeck`: `@api.constrains` for the message plus `models.UniqueIndex` for
    race safety.
  - Form view: `required="document_type in ('check', 'echeck')"` on `check_number`.
  - MCP: reject `check`/`echeck` payments without `check_number` in
    `tools/collection_voucher.py`; update the schema description.
  - Tests in `tests/test_collection_voucher.py` plus an MCP test.
  - Route: delegated writer. Trigger: writer rule.
  - NOTE: identity is `(company_id, check_number)` per the user's instruction to use
    `check_number` for validation. `check_bank` is free text and unreliable, so it is
    deliberately NOT part of the key. Consequence: two banks issuing the same check
    number inside one company collide and the second is rejected.

- [x] **T3 — Duplicate identity for the other instruments** — DONE (same commit as T2).
  - `bank_transfer` / `cash_deposit`: unique on
    `(company_id, document_type, voucher_number)` where `voucher_number` is set.
  - `retention_certificate`: unique on `(company_id, partner_id, voucher_number)`.
  - `cash`: no duplicate rule — repeated identical cash payments are legitimate.
  - `unsupported`: exempt.
  - Tests covering both the rejection and the `cash` exemption.
  - Route: same writer as T2 (same mechanism).

- [x] **T4 — Applied must not exceed collected** — DONE.
  Verified `1 failed, 0 error(s) of 1040 tests`.
  Six existing tests were confirming sheets that applied money to customer debt with
  ZERO vouchers attached (`applied X > collected 0.0`). Their subjects were fine; the
  fixtures simply never modelled the money side. That shape is exactly the production
  bug this rule catches, so the fixtures were given covering vouchers rather than the
  rule being relaxed. No assertion values changed.
  Debt-side over-allocation remains allowed and untouched, as decided.
  - Block when an allocation's `total_applied` exceeds `total_vouchers`.
  - Enforced at `collection.sheet.action_confirm()` and `action_close()`.
  - Must NOT touch the debt-side residual, which stays negative-capable.
  - Tests in `tests/test_collection_allocation.py` or `tests/test_collection_sheet.py`.
  - Route: delegated writer.

- [x] **T5 — Company bank accounts and destination matching** — DONE.
  Verified `1 failed, 0 error(s) of 1054 tests`.
  Company accounts are core `res.partner.bank` rows surfaced through
  `res.company.bank_ids` in the Collections settings; no new field on `res.company`.
  `l10n_ar` already types `acc_number` as a CBU.

  **Design changed mid-task by user decision.** The destination match was first built
  as a hard block at save. With a real company account registered in `devel`, that
  failed 12 tests across 5 files — and the same rule in production would stop a seller
  recording a payment whenever OCR misread one digit of a 22-digit CBU. A mismatch is
  now a computed stored flag `to_account_mismatch`, surfaced as a badge in Document
  Review and read-only on the voucher form. It never blocks a save. All 12 tests then
  passed unmodified.

  Still blocking, correctly: `to_account_bank_id` must belong to the voucher's own
  company. That is a user-picked value, not OCR text.

  The flag stays False when the company has no registered accounts, so the whole
  feature is opt-in by configuration and inert until an account is entered.
  - Surface `res.company.bank_ids` in the Collections settings block
    (`views/res_config_settings_views.xml` + `models/res_config_settings.py`).
  - Add `to_account_bank_id` M2O `res.partner.bank` on `collection.voucher`, domain
    restricted to the company's own partner.
  - Validate `to_account` against the company's registered accounts for `bank_transfer`
    and `cash_deposit`, comparing on `sanitized_acc_number`.
  - `l10n_ar` is installed and types `acc_number` as CBU — no extra field needed.
  - Tests in `tests/test_collection_company_settings.py` plus voucher tests.
  - Route: delegated writer.

## Acceptance criteria

- Every new rule rejects the bad case and accepts the good case, proven by a test.
- `cash` vouchers can still be created repeatedly with identical data.
- `unsupported` vouchers remain creatable.
- Over-allocation against debt still succeeds (regression guard).
- `invoke test -m collection --mode=update` passes.
- `pre-commit run --files odoo/custom/src/private/collection/**` passes.

## Applicable checks

`invoke` is not on this machine's Git Bash PATH, so the documented
`invoke test -m collection --mode=update` is run directly against the container, which
is what the invoke task wraps:

```
MSYS_NO_PATHCONV=1 docker exec seedian-odoo-1 odoo -d devel -u collection \
  --test-enable --test-tags /collection --stop-after-init --workers=0 --http-port=8099
```

- Test suite: the command above.
- Lint: `pre-commit run --files odoo/custom/src/private/collection/**`

Three traps, all already hit while establishing the baseline:

- `MSYS_NO_PATHCONV=1` is mandatory. Git Bash rewrites the `/collection` test tag into
  `C:/Program Files/Git/collection`, Odoo logs `Invalid tag`, and the run reports
  `0 failed, 0 error(s) of 0 tests`. That is a green-looking run that executed nothing —
  never accept it as proof.
- `--http-port=8099` is mandatory. The dev server already holds 8069 and the run dies
  with `Address already in use`.
- Only one Odoo test run may touch the `devel` database at a time. Serialize runs.

## Progress

- Feature document created. Branch `feat/voucher-validations` cut from `main`.
- Engram mirror **PENDING** — `mem_save` fails with
  `repository_binding_unavailable` for this repo. Local document is the source of
  truth until the mirror succeeds. Retry before close.
- Baseline captured on `feat/voucher-validations` before any source change:
  **1 failed, 0 error(s) of 1003 tests.**
- Known environmental failure, pre-existing and NOT caused by this feature:
  `TestCollectionMcpAllocation.test_seller_commission_seller_confirmed_rejected`
  (`tests/test_collection_mcp_allocation.py:1866`, `AssertionError: 1 != 0`).
  Any other failing test during this feature is ours.
- T1 delegated to a writer. No source written by the orchestrator.

## T1 findings and corrections

**Measured blast radius of the positive-amount rule: 64 regressions** across 8 test
files (61 amount, 3 check-date). Escalated rather than silently mass-edited.

**Correction — an incorrect rule was specified and has been removed.** The original T1
spec said a `common` check must not carry a payment date later than its issue date.
That is wrong. Fixtures in three independent files encode the opposite as normal
business data:

- `tests/test_collection_document_review.py:654` — 2026-01-10 to 2026-02-10
- `tests/test_collection_document_review.py:1281` — 2026-01-01 to 2026-01-15
- `tests/test_collection_sheet_xlsx.py:785` — 2026-03-01 to 2026-04-15

A cheque común legitimately records when it is actually cashed. The clause is deleted;
the surviving check-date rules are `issue <= payment` and `deferred requires payment
strictly after issue`. A regression test now pins the accepted case.

**Decision — the positive-amount rule fires at save.** Taken by the user after being
shown the full cost. Recorded for future readers because the codebase pushes the other
way and someone will eventually ask why:

- `tools/collection_voucher.py:97` declares `amount` as
  `_COLLECTION_NULLABLE_AMOUNT_SCHEMA` — explicitly nullable in the MCP contract.
- `tools/collection_voucher.py:329,337` already enforce
  `seller_confirmed amount must be greater than zero`, i.e. a positive amount was
  previously required at seller confirmation, not at save.

Consequences accepted: 61 test fixtures updated across 8 files, and `amount` becomes a
second breaking change to the `create_collection_allocation` MCP contract alongside
`check_number`. Both need a coordinated deploy with the Nebula Collections Agent.

## Next step

Finish the T1 fixture sweep to baseline, then commit and move to T2.
