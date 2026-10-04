Closed plan used instead of a question round.

# Proposal: Allocation Customer Debt

## Intent

Operators cannot see full outstanding debt on an allocation. Residual is leftover
vouchers, Residual Reason blocks saves, and Invoices stores applied rows only. Snapshot
every outstanding ERP invoice (zeros included), set Residual = Total Debt − Total
Applied (negative allowed), drop Residual Reason.

## Scope

### In Scope

- Shared `_prepare_customer_debt_lines` + onchange + create-if-omitted
- Compute `total_debt` / `total_invoices` / `total_quotations`; residual = debt −
  applied; drop `_check_residual` and `residual_reason`
- `amount_applied` default 0, CHECK `>= 0`
- MCP: ignore `residual_reason`; expand `invoices[]` to full debt; drop reason from
  hash/get; add get `document_kind`; stop writing `total_debt`
- Form: many2many existing vouchers (`no_create`) + `document_type`; Customer Debt tab;
  parent-arch `document_kind`; helpers; Vouchers smart button
- Stop projecting voucher amounts into residual; sheet report stops reading
  `residual_reason`
- Manifest `19.0.1.32.0`, migration, tests, `AGENTS.md` (apply later)

### Out of Scope

- Nebula (overrides config Nebula-in-scope rule); SQLite `document_kind`; backfill old
  lines; sheet copy except residual numbers; sibling `voucher-states-ui/`
  (`19.0.1.31.0`)

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `collection-allocations`: snapshot; residual formula; drop residual_reason
  persist/constraints/hash/get; MCP expand; parent-arch + get `document_kind`; detach
  without leftover-voucher residual
- `collection-vouchers`: unlink, membership, and partner-write MUST NOT project voucher
  amounts onto residual; drop residual_reason attach rules; confirmed freeze unchanged

## Approach

Exploration **1**: `_prepare_customer_debt_lines` via `collection_connector_id` +
binding (not `_collection_active_connector()`). Onchange replaces `line_ids` unless
confirmed; no connector/binding → empty lines. `create` snapshots only if `line_ids`
omitted. **3**: get rows include `document_kind` (default `invoice`). **5**: stop
`residual ± voucher.amount`.

## Affected Areas

- Modified: allocation/line/revision models; voucher detach helpers; sheet-report reason
  read; MCP create/get; allocation form + document_kind inherit; tests; `AGENTS.md`
- New: `migrations/19.0.1.32.0/post-migrate.py` DROP `residual_reason`
- Manifest: `19.0.1.32.0` after sibling `19.0.1.31.0`

## Risks

| Risk                                   | Likelihood | Mitigation                               |
| -------------------------------------- | ---------- | ---------------------------------------- |
| Sibling file overlap                   | High       | Apply after `19.0.1.31.0`                |
| Detach/report leftover residual/reason | High       | Update helpers and report in this change |
| Onchange UserError / no backfill       | Med        | Empty lines; accepted                    |
| Diff > 400 lines                       | High       | `sdd-tasks` chained PRs (`ask-on-risk`)  |

## Rollback Plan

Revert to pre-1.32.0. Restore `residual_reason`, CHECK `> 0`, residual = vouchers −
applied. Reverse ALTER if columns already dropped.

## Dependencies

- Sibling `voucher-states-ui` at `19.0.1.31.0` first; connector `get_customer_debt`;
  `-u collection`

## Success Criteria

- [ ] Snapshot stores every outstanding invoice; zeros stay `amount_applied=0`
- [ ] Residual = total_debt − total_applied; negative saves; no Residual Reason
- [ ] Vouchers many2many existing-only; smart button domain `allocation_id`
- [ ] MCP ignores `residual_reason`, expands applied-only `invoices[]`, get returns
      `document_kind`
- [ ] Detach/attach ignores leftover-voucher residual; no backfill; tests pass after
      apply
