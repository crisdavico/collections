# Proposal: Standalone Payment Vouchers

## Intent

Flatten header+line into one `collection.voucher` per payment.

**User impact:** Payment Vouchers is the only create/edit surface (kanban by state).
Payment Lines gone. Each payment owns sequence, chatter, attachment, review. Legacy data
discarded. Nebula registers N vouchers atomically.

## Scope

### In Scope

- Flatten voucher: absorb line fields, customer, sequence, chatter, activities,
  attachment, review audit; `pending → approved/rejected`; delete only from `pending`.
  Drop line model and Payment Lines.
- One create/edit kanban/list/form; intercept `state` writes so drag is audited
  Approve/Reject. Buttons remain when review is OFF; review RPCs still refuse. Queue:
  `pending` + attachment (drop parent `state == new`); OWL `LINE_MODEL` →
  `collection.voucher`.
- MCP `create_collection_vouchers(customer_identification, payments)`: one voucher per
  payment atomically; `document_id` idempotency; exact replay returns ALL vouchers;
  reject in-call dup + partial overlap; cross-voucher becomes success. Destructive
  reset: no conversion. Coordinated Nebula: MCP rename, list formatter, tests, spec;
  grant nebula-agent apply roots.

### Out of Scope

- SQL conversion; batch grouping; WhatsApp/HTTP/CRM/multi-currency/extra ACL; leftover
  `document-review-feature-flag`

## Capabilities

### New Capabilities

None

### Modified Capabilities

- `collection-vouchers`: remove header/line + aggregate-state; standalone UI,
  attachment, ACL, sequence, MCP, idempotency, reset
- `document-review`: queue/OWL/approve-reject retarget from `collection.voucher.line` to
  standalone `collection.voucher`

## Approach

Map header `new/validated/rejected` → `pending/approved/rejected`. Sequence per payment.
N creates in one savepoint; UniqueViolation replay. Exact replay ignores
customer/attachments.

## Affected Areas

| Area                                                       | Impact           | Description                                                  |
| ---------------------------------------------------------- | ---------------- | ------------------------------------------------------------ |
| Odoo models/tools                                          | Modified/Removed | Flatten voucher; drop line; MCP rename + list replay         |
| Views + Review OWL                                         | Modified         | Drop Payment Lines; queue/`LINE_MODEL` → voucher             |
| ACL, sequence, manifest, migrations, tests, config         | Modified         | Drop line ACL; per-payment sequence; nebula-agent apply root |
| Nebula tool, tests, `collection-voucher-registration` spec | Modified         | MCP name + list formatter (not a collection capability)      |

## Risks

| Risk                                                  | Likelihood | Mitigation                                     |
| ----------------------------------------------------- | ---------- | ---------------------------------------------- |
| MCP name mismatch fail-closed                         | High       | Ship both roots; restart MCP cache             |
| Kanban drag skips audit                               | High       | Gate `state` writes through Approve/Reject     |
| Reset discards chatter/attachments                    | High       | resetdb; no conversion                         |
| Blast radius > 400 lines; collection-only apply roots | High       | Chained PRs; grant nebula-agent edit authority |

## Rollback Plan

Revert both git roots. Restore `create_collection_voucher`. Reset DB from a pre-upgrade
dump. No reverse conversion.

## Dependencies

- Coordinated Nebula (`/home/crisd/projects/nebula/nebula-agent`);
  `openspec/config.yaml` nebula-agent apply-root grant
- Module upgrade + DB reset; `muk_mcp` method-discovered tool

## Success Criteria

- [ ] Standalone voucher UI/lifecycle; Payment Lines gone; audited drag; delete only
      from `pending`
- [ ] Review queue/OWL on voucher; RPCs refuse when flag OFF
- [ ] MCP N-voucher create/replay; Nebula renamed tool + list formatter; reset
      documented; tests pass
