# Proposal: Optional image/PDF attachment per voucher line

## Intent

Payment lines need one optional proof file (image or PDF). Manual/non-agent lines may
omit it. Spec today defers attachments entirely.

## Scope

### In Scope

- Optional single Binary (`attachment=True`) + filename on `collection.voucher.line`;
  `ir.attachment` storage; `copy=False`.
- Image/\* or PDF only; reject bad base64 / wrong MIME server-side.
- Binary widgets in typed embedded lists and Payment Lines view; browser filter
  `image/*` + PDF.
- MCP `create_collection_voucher`: optional nested attachment per payment (`name`,
  `mimetype`, base64 `datas`); atomic voucher + lines + files.
- Exact-retry by `document_id` returns existing voucher with no attachment
  add/replace/compare (even if line has none).
- Keep savepoint; all-new / replay / conflict rules; internal-user ACL.

### Out of Scope

- Multi-file; non-image/non-PDF; WhatsApp; HTTP public API; partner/CRM; multi-currency;
  agent LLM code in this addon.

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `collection-vouchers`: Optional one image/PDF per voucher line (model/UI/MCP);
  deferred-integrations note no longer excludes attachments.

## Approach

Add Binary + filename and MIME/base64 constrains on the line model. Wire binary widgets
into typed One2many and Payment Lines views. Extend MCP payment parsing to create
attachments in the atomic create path; skip attachment writes on exact-retry. Cover
model, UI, MCP in TransactionCase; upgrade module after.

## Affected Areas

| Area                                  | Impact   | Description                        |
| ------------------------------------- | -------- | ---------------------------------- |
| `models/collection_voucher_line.py`   | Modified | Binary + filename; MIME validation |
| `tools/collection_voucher.py`         | Modified | Optional MCP attach; replay skip   |
| `views/collection_views.xml`          | Modified | Binary widgets in typed/line views |
| `tests/test_collection_payment.py`    | Modified | Field/MIME constraints             |
| `tests/test_collection_mcp_tool.py`   | Modified | Attach create + replay             |
| `tests/test_collection_ui.py`         | Modified | Widget/arch presence               |
| `openspec/specs/collection-vouchers/` | Modified | Line attachment requirements       |

## Risks

| Risk                               | Likelihood | Mitigation                         |
| ---------------------------------- | ---------- | ---------------------------------- |
| Bad/large MCP payloads             | Med        | Validate before create; savepoint  |
| Replay mutates stored files        | Med        | Explicit no-write on exact-retry   |
| UI accept vs model reject mismatch | Low        | Browser filter + `@api.constrains` |

## Rollback Plan

Revert model/view/tool/test commits and upgrade the module. Drop Binary/filename columns
and linked `ir.attachment` rows via reverse migration if needed.

## Dependencies

- Odoo 19 Binary `attachment=True` patterns (`odoo-19` skill)
- Existing MCP idempotency in `tools/collection_voucher.py`

## Success Criteria

- [ ] Line stores zero or one image/PDF; omit remains valid
- [ ] Bad base64 / wrong MIME rejected; widgets on typed + Payment Lines views
- [ ] MCP create with attachment persists atomically
- [ ] Exact-retry leaves attachments unchanged
- [ ] Conflict/ACL/savepoint unchanged; `invoke test -m collection` green
