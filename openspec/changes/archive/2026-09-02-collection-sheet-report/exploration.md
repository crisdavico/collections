# Exploration: collection-sheet-report

Source plan: `/home/crisd/.claude/plans/i-want-to-print-sorted-lemon.md`.
Normative layout: `collection_sheet_template.xlsx` (untracked in the collection repo).
Generator (readable, non-normative): `/home/crisd/projects/seedian/seedian/build_collection_sheet_template.py`.

## Exploration: Print Planilla de Cobranza (PDF + XLSX)

### Current State

`collection.sheet` groups a seller’s vouchers and per-customer allocations. There is
**no print or export path today**: no `report/` package, no `ir.actions.report`, no
QWeb template, no XLSX builder, no header export button. Manifest `data` stops at
views (`__manifest__.py:11-21`). A repo-wide search for `ir.actions.report` /
`qweb-pdf` / `xlsx` under this addon hits only an unrelated “report” wording in a
sheet test docstring.

Live disk (uncommitted sibling diffs, treated as current code):

- Sheet: `open`/`closed`; `_ensure_saved_sheet()` at
  `models/collection_sheet.py:298-302` refuses non-positive / NewId ids. Close
  confirms every allocation then closes; Reopen opens then drafts
  (`collection_sheet.py:203-237`).
- Allocation: `state` is `draft`/`confirmed` (`collection_allocation.py:57-67`),
  default `draft`. `_compute_totals` (`:128-138`) sums **all** `voucher_ids.amount`
  and `line_ids.amount_applied` with no voucher-state filter. Freeze when
  `state == 'confirmed'` (`:166-169`). Iff constraint: draft ↔ open sheet,
  confirmed ↔ closed sheet (`:252-267`).
- Allocation line (`collection_allocation_line.py`): invoice snapshot fields only.
  **No `document_kind`.** Order `_order = "due_date, invoice_number"`.
- Voucher `document_type` Selection is **company-dependent** via
  `_selection_document_type` (`collection_voucher.py:229-234`): allowed codes ∪
  current value. Catalog labels live on `collection.document.type` (four XMLID
  rows: `bank_transfer`, `check`, `cash_deposit`, `unsupported`).
- Sheet form (`views/collection_views.xml:471-560`): header Close / Reopen /
  Document Review / Reassign Customers / statusbar. Notebook is **one**
  Allocations page. Inner header group is a single `<group>` (seller, dates).
- Allocation form line list starts at `invoice_number`
  (`views/collection_allocation_views.xml:102-111`); search filters are
  `draft`/`confirmed` (`:33-41`); freeze attrs are `state == 'confirmed'`.
- Company `ir.rule` `[('company_id', 'in', company_ids)]` on sheet, allocation,
  line, voucher, customer binding (`security/collection_security.xml`). Models
  under `models/` contain **no** `sudo()`. ACL test
  `test_allocation_models_have_no_sudo` only scans five named files
  (`test_collection_allocation_acl.py:445-479`) — a new inherit file is **not**
  covered unless a new test is added.
- Customer code: `collection.connector.customer.binding.customer_code`.
  `res.company._collection_active_connector()` (`res_company.py:95-102`) raises
  `UserError` when unset — printing must **not** call it.
- Seller commission already exists on
  `collection.connector.seller.binding.commission_percent` (0–100 CHECK), **not**
  on `res.users`. Template comment `res.users.collection_commission_rate` is
  stale.
- Manifest version on disk: **`19.0.1.29.0`**. Migration test asserts that
  string and forbids `migrations/19.0.1.29.0/`
  (`test_collection_company_migration.py:204-211`). `migrations/19.0.1.28.0/`
  exists (allocation state remap).
- UI tests (line numbers **shifted** vs the plan): notebook exactly one page at
  `tests/test_collection_ui.py:1293-1307`; Reassign at
  `index(Document Review) + 1` at `:1445-1457`. Append any XLSX button **last**
  in `<header>` before `state`. Reconciliation fields must **not** add a second
  notebook page.

**Workbook (openpyxl in `seedian-odoo-1`)** matches the generator. Title
`Planilla de Cobranza`; freeze `A6`; landscape; paperSize `9` (A4); fitToWidth
`1`; print titles `$1:$4`; print area `A1:H68`; widths A–H
`13/32/19/17/14/14/15/15`; formats `#,##0.00` / `#,##0` / `0.0%` /
`"$" #,##0.00`. Conditional formatting on `A68:H68`.

**CAMPO NUEVO comments in the workbook** (not inferred):

| Cell | Comment |
| --- | --- |
| A13 / C13 | `% Comisión Vendedor` — `CAMPO NUEVO — res.users.collection_commission_rate` |
| E13 / G13 | `Total Comisión Devengada` — derived sum of line commissions |
| G23 / G30 | line `Comisión` — `Aplicado × res.users.collection_commission_rate` |
| C30 | Presupuestos — `CAMPO NUEVO` document type on `collection.allocation.line` |
| D58 | `Efectivo en Caja` — physical cash, not a `collection.voucher` |
| A62 | `Comisión Retenida` — withheld at handover |

C13 sample is `0.045` with Excel percent format (displays 4.5%). The planned
Odoo field is 0–100 like the seller binding; the XLSX writer MUST write
`percent / 100.0` into a `0.0%` cell.

C11 formula is `=H55` (voucher-block SUM) while the comment says Σ
`allocation.total_vouchers`. H55 sums voucher blocks. Those diverge when a
sheet voucher has no allocation — the plan’s `mismatch` warning is justified.

Template residual-reason comment lists “A Cuenta / Anticipo / Redondeo”; the
model also has `pending_invoice` (`collection_allocation.py:105-111`). Print
the stored selection label, including that fourth value.

Sample membrete uses `COB/2026/0007`; live sheet sequence is `CS/<year>/<number>`.

**Odoo 19 report JS** (`addons/web/static/src/webclient/actions/action_service.js:1370-1404`):
`_executeReportAction` handles only `qweb-html` | `qweb-pdf` | `qweb-text`,
then `console.error`s. Server `ir.actions.report.report_type` Selection is the
same three values (`odoo/addons/base/models/ir_actions_report.py:170-174`).
`discard_logo_check` / `_action_configure_external_report_layout` live at
`:1181-1187`.

**Libraries (container):** `xlsxwriter 3.1.9`, `openpyxl 3.1.5`. Core
`requirements.txt` pins `XlsxWriter==3.1.9` (Python ≥ 3.12) and `openpyxl==3.1.2`
(image has 3.1.5). `wkhtmltopdf 0.12.6.1 (with patched qt)` is installed.

**`web` dependency:** `collection` depends on `mail`. `mail` depends on
`web_tour`, `html_editor`, and `bus`; each of those depends on `web`. `web` is
`auto_install`. `web.external_layout` is at
`addons/web/views/report_templates.xml:814`. Transitive availability is real;
an explicit `depends += "web"` is still the right XMLID/pylint contract.

**OCA `report_xlsx`:** present under `OCA/reporting-engine`, manifest
`17.0.1.0.2`, `installable: True`, plus JS that registers an `xlsx` report
handler. Series 17.0 on this Odoo 19 stack; do **not** depend on it. The JS
limitation above is exactly why a custom `xlsx` report type is a poor fit.

**Main specs:** `openspec/specs/collection-sheets/spec.md` has no print/export
requirement. `collection-allocations` still describes
validated/rejected/confirmed MCP persist — **stale vs disk** (`draft` default).
This change must specify print against **live** allocation states, not archived
spec prose.

**Collisions on disk (do not edit those files):**

| Claim | Disk |
| --- | --- |
| `draft-until-close` rewriting sheet/allocation/voucher/views | **Holds.** Git `M` on those files. Allocations are `draft`/`confirmed`. Apply-progress marks phases 1–6 complete; `state.yaml` still `blocked: maintainer_decision`. Plan’s claim that allocation views still have `validated`/`rejected` filters is **refuted** — current XML is already draft/confirmed. |
| `seller-commission-percent` claims `test_collection_ui.py`, allocation model, binding commission, manifest 1.29 | **Holds as dirty files.** Binding `commission_percent` is on disk. Manifest `19.0.1.29.0`. Apply-progress: all four phases `[x]`; `state.yaml` is `phase: verify`. |
| Plan version table (1.27 / 1.28) | **Stale.** Live version is `19.0.1.29.0`. Next bump is `19.0.1.30.0` after both siblings archive. |

### Affected Areas

New (uncontested):

- `models/collection_sheet_report.py` — second `_inherit = "collection.sheet"`:
  `currency_id` (related, non-stored), `commission_percent`, `cash_on_hand`,
  `commission_withheld`, range Constraint, closed-sheet `write` guard,
  `_collection_report_data()` + private helpers, `action_print_xlsx()`.
- `models/collection_allocation_line.py` — `document_kind` Selection
  `invoice`/`quotation`, `required=True`, `default="invoice"` (`_init_column`
  backfill; **no** `migrations/` folder).
- `report/` package — paperformat, `ir.actions.report`, QWeb templates,
  `report.collection.report_collection_sheet` AbstractModel,
  `collection.sheet.xlsx` AbstractModel writer.
- `views/collection_sheet_report_views.xml` — inherit allocation form; inject
  `document_kind` before `invoice_number`. **Do not** edit
  `views/collection_allocation_views.xml`.
- Tests: `test_collection_sheet_report_data.py`,
  `test_collection_sheet_report.py`, `test_collection_sheet_xlsx.py`,
  `test_collection_allocation_document_kind.py`; `tests/__init__.py`.
- `models/__init__.py` — import the new inherit **after** `collection_sheet`.
- Addon `__init__.py` — `from . import report`.

Modified, collision-aware:

- `views/collection_views.xml` — **not claimed.** XLSX header button last
  (before `state`); recon fields in a **second inner `<group>`**, never a new
  notebook page.
- `__manifest__.py`, `AGENTS.md`, `tests/test_collection_company_migration.py`,
  `readme/DESCRIPTION.md` — **claimed by both siblings.** Confine `depends`,
  `data` entries, and version `19.0.1.30.0` to a last PR after those changes
  archive (or land data/depends in that same last PR so XMLID tests are not
  red against an unloaded file).

Must not touch: `models/collection_sheet.py`,
`models/collection_allocation.py`, `views/collection_allocation_views.xml`,
`tests/test_collection_ui.py`, `tests/test_collection_allocation*.py`, sibling
change folders.

### Approaches

1. **Shared payload + QWeb PDF + xlsxwriter header button (plan)** —
   `_collection_report_data()` returns primitives (+ `sheet`/`currency` for
   QWeb). Print menu via bound `qweb-pdf`. XLSX via `action_print_xlsx` →
   attachment + `ir.actions.act_url` download. New fields on a second sheet
   inherit file.
   - Pros: identical numbers; no custom report type/JS; assertable in
     `TransactionCase`; stays off `collection_sheet.py` and allocation views;
     uses in-image `xlsxwriter`; `_ensure_saved_sheet` + mixed-currency
     `UserError` shared by both outputs; no sudo so company `ir.rule` applies.
   - Cons: PDF membrete uses `web.external_layout` (drops workbook rows 1–4);
     attachment chatter noise; `__manifest__.py` is contested until a last PR;
     C13 percent scale must be converted 0–100 → Excel fraction.
   - Effort: Medium (four reviewable PRs).

2. **OCA `report_xlsx` custom `xlsx` report type** — depend on
   `report_xlsx` 17.0, let its JS handler register `xlsx`.
   - Pros: Print menu for both formats.
   - Cons: 17.0 module on Odoo 19; JS outside TransactionCase; fights
     `action_service.js` unless that JS loads; extra OCA surface; plan
     explicitly rejected this.
   - Effort: Medium, high operational risk.

3. **HTTP controller download (no `ir.attachment`)** — same builder, button
   returns `act_url` to a `type="http"` route (core precedent:
   `addons/product/controllers/pricelist_report.py`).
   - Pros: no chatter Files noise; still no custom report type.
   - Cons: new controller + routing tests; easier to get auth wrong; plan’s
     attachment path is auditable and stays in ORM ACL.
   - Effort: Medium. Keep as drop-in if chatter noise is rejected later.

4. **Append everything onto `collection_sheet.py` + allocation views** —
   one file each.
   - Pros: fewer files.
   - Cons: rewrite collision with `draft-until-close`; violates
     `collision_guard`.
   - Effort: Low technically, High politically. Reject.

5. **openpyxl writer instead of xlsxwriter** — both are in the image.
   - Pros: same library as the generator script.
   - Cons: `write_formula(..., cached_value)` for `data_only=True` tests is
     an xlsxwriter feature the plan relies on; Odoo export historically uses
     XlsxWriter. Prefer xlsxwriter.

### Recommendation

Adopt **approach 1** (the source plan), with these disk-confirmed adjustments
— do not reopen settled product decisions:

- Keep `document_kind` human-settable; no connector/MCP/Nebula work. MCP
  `create_collection_allocation` still writes lines without a kind
  (`tools/collection_allocation.py:493-504`); Presupuestos stay empty until
  someone sets the field.
- Keep `cash_on_hand`, `commission_withheld`, `commission_percent` **on the
  sheet**, not copied from seller binding (binding field is live and owned by
  the other change).
- Print **all** `allocation_ids` and **all** `voucher_ids` regardless of
  draft/confirmed or voucher pending/approved/rejected, matching
  `_compute_totals` and the sheet form. Open-sheet prints are working copies
  of drafts; Close then reprint for the confirmed settlement. Surface
  `payload["mismatch"]` when Σ allocation `total_vouchers` ≠ Σ printed voucher
  amounts.
- Filter nothing by allocation state unless product later asks to hide drafts.
- Sequence: PRs A (fields + payload + inherit view XML file) / B (PDF) / C
  (XLSX + form button in `collection_views.xml`) / D (`web` depend, `data`
  entries, version `19.0.1.30.0`, AGENTS, migration test). If `__manifest__.py`
  cannot be touched until D, XMLID/PDF tests belong in D or wait for siblings
  to archive — do not edit the dirty manifest during A–C.
- XLSX: `write_formula` with cached values; banner from Python
  `recon.status`, not conditional_format; `_VOUCHER_BLOCK_COLUMNS`; labels from
  `collection.document.type` by `code`, not `_selection_document_type`.
- Call `_ensure_saved_sheet()` from both builders. No `sudo()`. Customer codes
  via batched search on bindings using raw `company_id.collection_connector_id`.
- QWeb: `t-out` only; `web.html_container` + `web.external_layout`; HTML render
  in tests, not `_render_qweb_pdf`. Pass `context={'discard_logo_check': True}`
  if the layout wizard trips for admins.
- Strict TDD (`openspec/config.yaml`). Fixtures:
  `ensure_enabled_seller`, `install_bound_test_connector`
  (`tests/common_connector.py:201`), `dummy_customer_partner`
  (`tests/test_collection_payment.py:124`).

**Verify later (do not run as this phase):**

```bash
docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init
docker exec -i seedian-odoo-1 odoo -d devel --test-enable --stop-after-init \
  --test-tags /collection:TestCollectionSheetReportData,/collection:TestCollectionSheetXlsx
invoke test -m collection --mode=update -d devel
pre-commit run --files odoo/custom/src/private/collection/**
```

`invoke test -m collection` without `--mode=update` on an installed DB runs 0
tests. Shell smoke (outside `--test-enable`): `_render_qweb_pdf` bytes start
`%PDF`; XLSX zip contains `xl/workbook.xml`.

### Risks

- **Concurrent `draft-until-close`:** printed rows on an **open** sheet are
  `draft` allocations and still-editable lines/vouchers. After Close they are
  `confirmed` and frozen. Including both states matches the form; excluding
  drafts would under-print an open sheet. Sibling `state.yaml` is still
  `blocked` even though apply-progress claims phase 6 done — expect further
  uncommitted churn on claimed files.
- **`__manifest__.py` / version / AGENTS.md** contested at `19.0.1.29.0`.
  Touching them before siblings archive will conflict. Plan’s “stay at 1.27.0
  for A–C” is obsolete.
- **Dual Total Cobrado** (C11 vs H55) and unallocated sheet vouchers —
  `mismatch` must be tested, not silently summed.
- **PDF membrete ≠ workbook rows 1–4** if `web.external_layout` is used.
- **Layout configurator wizard** for admins without
  `external_report_layout_id`.
- **Mixed allocation currencies** — hard-fail `UserError` (template is
  single-currency).
- **Percent scale** — Odoo 0–100 vs Excel `0.0%` fraction.
- **Reopen keeps** `cash_on_hand` / `commission_withheld` /
  `commission_percent` (write guard only while closed).
- **wkhtmltopdf not in the suite** (flake source); PDF bytes are a shell/manual
  check.
- **OCA `report_xlsx` sitting in `addons.yaml: "*"`** — do not enable it for
  this change.
- Main `collection-allocations` spec still says persist `confirmed` on MCP
  create; disk persists `draft`. Print specs must follow disk.

### Ready for Proposal

**Yes.** Product decisions in the plan match the workbook and live models.
Collision file claims still hold (dirty git); allocation-view “stale
validated/rejected” does **not**. Orchestrator should tell the user: proceed to
`sdd-propose` for `collection-sheet-report` using approach 1, delay manifest
version/`depends`/`data` to the last PR (`19.0.1.30.0`), never edit
`collection_sheet.py` or `collection_allocation_views.xml`, and print draft
rows on open sheets (confirmed after Close).
