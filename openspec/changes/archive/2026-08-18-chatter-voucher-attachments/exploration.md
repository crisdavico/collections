# Exploration: chatter-voucher-attachments

Move `collection.voucher` payment proof off Binary fields onto chatter (`mail.thread` /
`ir.attachment` linked via `mail.message`). MCP nest payload stays
`{name, mimetype, datas}`. Document review must keep preview/rotate.

## Current State

Voucher already inherits `mail.thread` + `mail.activity.mixin`. Form already has
`<chatter />`. Proof is a **separate** Binary field, not a chatter file.

**Storage**

- `attachment = fields.Binary(attachment=True, copy=False)` — ORM stores `ir.attachment`
  with `res_model=collection.voucher`, `res_field=attachment`. `ir.attachment.name` is
  the **field name** (`attachment`), not the operator filename.
- `attachment_filename` Char (`copy=False`) holds the display/download name used by
  Binary widgets and review URLs.
- `attachment_rotation` Integer `0|90|180|270` (`copy=False`, SQL CHECK) lives on the
  voucher. It is **not** a file field.

**Write / review reset** (`models/collection_voucher.py`)

- `create`/`write` call `_validate_attachment_payload` (valid base64, detected MIME
  `image/*` or `application/pdf`).
- `write` of `attachment` runs `_vals_with_review_reset_on_new_attachment`: non-empty
  content → `state=pending`, clear `reviewed_by`/`reviewed_at`; **any** `attachment` key
  (including empty) → `attachment_rotation=0`.
- Kanban reopen to `pending` is refused unless `attachment` is in the same write vals.
- Review eligibility: `state == pending` **and** `_records_with_attachment()`
  (`res_field=attachment`).
- Queue domain: `("attachment", "!=", False)`.
- Viewer URL:
  `/web/content?model=collection.voucher&id={id}&field=attachment&filename=...`. OWL
  binds `current.attachment_url`; kind is inferred from filename (optional `mimetype`
  already supported in helpers).

**MCP** (`tools/collection_voucher.py`)

- Optional nest `{name, mimetype, datas}` per payment.
- All-new path maps nest → `attachment` + `attachment_filename` inside the same
  `Voucher.create` savepoint.
- Exact-retry / UniqueViolation replay **ignores** nests (no add/replace/compare).

**UI**

- Form, list, and kanban declare Binary widgets + `attachment_filename`
  (`accepted_file_extensions: image/*,.pdf`).
- Chatter is form-only; list/kanban currently upload via Binary widgets.

**Nebula** (`nebula-agent` `register_latest_collection_voucher`)

- Payload-only coupling: nests `{name, mimetype, datas}` from OCR `source`.
- Does not mention Binary fields, `res_field`, or `/web/content?...&field=`.
- **Out of scope** unless Odoo changes the nest schema (it must not).

**Specs today** (`openspec/specs/collection-vouchers/spec.md`)

- Require Binary `attachment=True` + filename via `ir.attachment`.
- Require Binary widgets on form/list/kanban.
- Replacement = write of new Binary content.
- No dedicated `document-review` spec file; queue/viewer rules live in voucher spec +
  tests.

**Sibling change:** `openspec/changes/auto-assign-open-sheet/` is verify-complete and
must not be edited in this change.

## Affected Areas

- `models/collection_voucher.py` — drop Binary/filename fields; keep rotation; proof
  lookup, URL, eligibility, write-reset, MIME validation.
- `tools/collection_voucher.py` — nest still validated; persist via
  `message_post(attachments=[(name, raw_bytes)])` after create, inside the existing
  savepoint. Replay path unchanged.
- `views/collection_views.xml` — remove Binary widgets from form/list/kanban; keep
  `<chatter />` (optionally `open_attachments="True"`).
- `static/src/document_review/*` — likely payload-only (`attachment_url` /
  `attachment_filename`); OWL already ignores Binary keys.
- `tests/test_collection_mcp_tool.py` — assert chatter/`res_field` empty + message link,
  not Binary field rows.
- `tests/test_collection_document_review.py` — create helpers, queue domain, URL
  contract (`field=attachment` must go).
- `tests/test_collection_ui.py` — invert Binary-widget assertions.
- `tests/test_collection_voucher.py` — replace-reset + kanban reopen.
- `tests/test_collection_mail.py` — extend with chatter attach (today only posts
  body/activities).
- `tests/test_collection_acl.py`, `tests/test_collection_document_review_flag.py` —
  create-with-Binary helpers.
- `__manifest__.py` — version bump for migration folder.
- `migrations/<new-version>/pre-*.py` — convert field attachments **before** the Binary
  field is dropped (Odoo runs `pre` before `load_openerp_module`).
- `openspec/specs/collection-vouchers/spec.md` — MODIFY Binary/widget/replace
  requirements (delta in this change).
- `AGENTS.md` / `readme/` — Binary wording (apply phase, not this file).
- **Not affected:** Nebula tool code (payload unchanged). Copier / `odoo/` / `OCA/`.
  Sibling `auto-assign-open-sheet`.

## Approaches

### Proof designation (open product assumption)

Chatter may hold extra files. Document review needs **one** designated proof.

| Approach                                                            | Pros                                                                                                                                                                                                 | Cons                                                                                                                                                                      | Effort         |
| ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- |
| **A. `mail.thread.main.attachment` (`message_main_attachment_id`)** | Odoo-native (expenses, invoices). First post sets main (`force=False`). Extra chatter files do **not** steal proof. File stays chatter-visible (`res_field` empty). Viewer uses `/web/content/<id>`. | Must inherit mixin. Default main-picker allows non-image/PDF if proof is empty — must restrict. Replace UX is delete-then-attach (no Binary replace).                     | Medium         |
| **B. Custom `proof_attachment_id` Many2one**                        | Explicit, no mixin. Same replace/extra rules as A.                                                                                                                                                   | Duplicates `message_main_attachment_id`. Extra field + chatter sync code.                                                                                                 | Medium         |
| **C. Oldest eligible chatter image/PDF**                            | No pointer field. MCP’s first file stays proof while extras are newer.                                                                                                                               | Deleting the original promotes an extra to proof (silent replace). Fragile ordering.                                                                                      | Low (wrong)    |
| **D. Latest eligible chatter image/PDF**                            | Simple.                                                                                                                                                                                              | Extra files become proof and would reset review — violates product decision 8.                                                                                            | Low (wrong)    |
| **E. Dedicated `res_field` marker**                                 | Easy SQL filter, similar to today.                                                                                                                                                                   | Field attachments **do not show in chatter** (`res_field` must be empty). Conflicts with “file lives on chatter”. Odoo GC/access treats unknown `res_field` as forbidden. | Medium (wrong) |
| **F. First MCP / create message**                                   | Ties proof to MCP.                                                                                                                                                                                   | UI-created vouchers have no MCP message.                                                                                                                                  | Low (wrong)    |

### Persist path (MCP / ORM)

1. **`message_post(attachments=[(name, bytes)])` after `create`** — typical chatter
   attach; links `mail.message` ↔ `ir.attachment`; mixin sets main.
2. **Create `ir.attachment` then `message_post(attachment_ids=...)`** — more moving
   parts; composer-style, not needed for MCP.
3. **Keep writing Binary then migrate at read time** — rejected; product drops the
   field.

### `attachment_rotation`

Keep the Integer on the voucher. Rotation is viewer state, not file bytes. Reset to 0
when the **proof identity** changes (new `message_main_attachment_id`), matching today’s
Binary write. Extra chatter files must not touch rotation.

## Recommendation

**Use approach A:** inherit `mail.thread.main.attachment` (replaces bare `mail.thread`;
mixin already includes it) and treat `message_main_attachment_id` as the designated
proof.

**Why**

- MCP posts **exactly one** image/PDF via `message_post` → empty main → that file
  becomes proof (`force=False`).
- Users may add extra chatter files afterward;
  `register_as_main_attachment(force=False)` and
  `_message_set_main_attachment_id(..., force=False)` leave proof unchanged → **must
  not** reset review.
- Replace-of-proof = chatter delete of the main file, then attach a new eligible file
  (or an explicit force-set). New main id → same reset as today (`pending`, clear audit,
  rotation 0).
- Clearing proof (main → empty, no replacement) → rotation 0, **do not** reopen a
  decided voucher (same as writing empty Binary). Reopen to `pending` still requires a
  proof replacement in the same operation (adapt the current `"attachment" not in vals`
  guard to proof identity).
- Review viewer: `attachment_url` = `/web/content/{attachment_id}?filename={name}` (or
  `/web/content/{id}/{filename}`). Stop using `field=attachment`. Filename/mimetype come
  from `ir.attachment`.
- MIME allow-list stays on MCP nest + when **promoting/setting proof**. Extra chatter
  files may be any Odoo type (new capability; matches “chatter may add more”). Override
  mixin picker so a non-image/non-PDF cannot become main.
- MCP create still at most one proof. Exact-retry still must not add/replace/compare.

**Migration (required before field drop)**

Odoo `pre` scripts run **before** new Python is loaded, so the Binary field still
exists. `Binary(attachment=True)` has **no table column**; files live only in
`ir.attachment`. Field unlink does **not** delete those rows; leftover
`res_field=attachment` becomes **inaccessible** (`KeyError` on missing field).

Pre-migrate per voucher that has a field attachment:

1. Use `attachment_filename` as chatter `name` (fallback `proof.bin`) — do not keep
   `ir.attachment.name == "attachment"`.
2. Null `res_field`, keep `res_model`/`res_id`, attach to a `mail.message`
   (`message_post` or SQL + `mail_message_attachment_rel`).
3. After mixin is loaded (`post` if needed), set `message_main_attachment_id` to that
   file.
4. Drop Binary + `attachment_filename` with the version bump. Keep `attachment_rotation`
   and its CHECK.

**UI impact (accepted by product decisions)**

- No Binary widget on form/list/kanban. Operators attach from chatter **after** the
  voucher is saved (chatter needs `id`). List/kanban lose inline upload.
- No extra form Binary control.

**Nebula:** no code change. Nest schema unchanged.

## Risks

- **Lost files on upgrade** if pre-migration is skipped or names stay `"attachment"` —
  review URLs and chatter labels break.
- **Wrong proof** if mixin default accepts a non-image/PDF while main is empty — must
  filter to `image/*` + `application/pdf` before setting main.
- **Silent review reset** if extras were treated as latest/oldest-without-pointer —
  avoided by A + `force=False`.
- **In-place `ir.attachment.datas` write** on the main file would not change
  `message_main_attachment_id` and would skip reset (chatter UI normally add/deletes).
  Optional hardening: hook datas write on the proof attachment.
- **Test blast radius** is large (MCP, UI arch, review URL `field=attachment`, create
  helpers). Likely **over the 400-line review budget** — plan chained PRs
  (migration+model, MCP+tests, views+review URL).
- **Spec gap:** no `openspec/specs/document-review/spec.md`; URL/eligibility must be
  updated in `collection-vouchers` (and/or a new domain) so verify can bind scenarios.
- Sibling `auto-assign-open-sheet` must stay untouched.

## Open Questions

Resolved recommendations for propose/spec (do not reopen product decisions 1–10):

1. **Proof rule** — `message_main_attachment_id`, first eligible chatter image/PDF when
   empty; extras never steal; replace = new main id.
2. **Extra file MIME** — unrestricted chatter extras; allow-list only for proof
   set/replace and MCP nest.
3. **List/kanban proof indicator** — omit (no Binary, no required replacement widget).
   Optional later: non-Binary many2one/stat, out of this change unless spec insists on a
   visible cue.
4. **MCP chatter body** — short notification e.g. “Payment proof attached.” (not a
   comment that looks like operator chat).
5. **document-review spec** — MODIFY voucher requirements; add a thin `document-review`
   delta only if propose wants a separate domain.

## Ready for Proposal

Yes. Propose should lock approach A, migration-before-drop, MCP nest unchanged, Nebula
out of scope, rotation kept, and the proof-vs-extra rule above. Next: `sdd-propose`.
