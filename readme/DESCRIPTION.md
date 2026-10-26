## Manual payment vouchers for cobranzas

Backend app to register one payment voucher per proof (bank transfer, check, echeck,
cash deposit, retention certificate, cash, seller deposit, or seller commission). Each
voucher owns sequence, chatter, optional image/PDF designated proof
(`message_main_attachment_id` on chatter `ir.attachment`; no Binary `attachment` field),
a required Customer (`partner_id` on `res.partner`; Char identification is gone;
`seller_deposit` and `seller_commission` stamp seeded sentinel partners), and a `draft`
→ `validated_seller` → `validated_collections` lifecycle (ORM/UI default `draft`; MCP
stamps `validated_seller`; Collections only via Document Review Approve; no Reject). A
Collections User can send a voucher Back to Draft while its sheet is open or submitted:
a deposit or commission gives back the cash it replaced, and a draft voucher can be
edited or deleted. In the same sheet states a Collections User can Remove a voucher from
its sheet (voucher form or the sheet's Vouchers tab): it leaves the sheet and allocation
with its receipt values and stays as a voucher, the allocation keeps its applied debt to
lower by hand, and a voucher in a cash swap stays. Collection sheets group a seller's
vouchers through `open` → Seller Close → `submitted` (Submitted by Seller; PDF Rendida)
→ Confirm → `proposal` → Close → `closed`. Submitted, Proposal, or Closed sheets may
Cancel to `cancelled`; Reinstate brings a `cancelled` sheet back to `submitted`. A
Collections Manager can Reset to Open from any later state: receipts and allocations go
back to draft, the ERP mark is cleared, the seller commission is removed and the
declaration cleared, so the sheet can be corrected, amended by the agent or deleted. It
is refused while the seller has another open sheet. Sheets have their own chatter and
activities. The sheet form notebook is Allocations, Vouchers, and Debt. Operators print
a Planilla de Cobranza from a sheet: bound Print PDF (`qweb-pdf`, A4 portrait, no
company letterhead or printed date) and header Collection Sheet XLSX share
`_collection_report_data()`; the workbook never turns typed text into a formula or a
link. Sheet recon inputs are `commission_percent` (0–100) and `commission_withheld`
(frozen while closed or cancelled; never negative); `cash_on_hand` (Cash to
Administration) is derived, not typed: cash vouchers minus `seller_deposit` vouchers
minus `commission_withheld`. Allocation lines carry required `document_kind` (`invoice`
/ `quotation`, default `invoice`). Print includes draft allocations and vouchers;
`mismatch` flags when voucher totals disagree with allocation `total_vouchers`. Each
row's seller commission is `commission_percent` of the untaxed share of what was applied
(`amount_applied × invoice_amount_untaxed / invoice_amount`); the connector gives
`amount_untaxed` per invoice (its total when it has none, and always for a quotation),
lines keep it, and lines with none pay on `amount_applied`. `customer_debt` (MCP) does
not return it. The sheet computes the seller's commission as the sum of those rows
(Seller Commission, `commission_amount`); Commission Owed to Seller (`commission_owed`)
is that commission minus the part kept from cash (`commission_withheld`), printed as
Comisión a Pagar al Vendedor.

Money rules. An allocation's collected money (`total_vouchers`) is the receipt values on
its own receipts plus the full amount of each voucher pointing at it whose money was
never placed on a receipt, so a voucher split across customers counts once, where its
values are. A line cannot apply more than the invoice balance it snapshotted; one ERP
document cannot be applied above its largest snapshotted balance across the company's
non-cancelled sheets; a receipt cannot apply more than its values. An approved
(`validated_collections`) voucher keeps its amount, payment details, customer, company,
currency, and destination account: replacing its designated proof sends it back to
Document Review (giving back any cash it replaced), and on closed or cancelled sheets
the proof cannot change at all. A draft allocation can be deleted only while its sheet
is open or submitted and it has no issued receipt. The agent tells the seller their
commission. A sheet with collected cash cannot close until the seller says how much of
it they kept from the cash: `close_collection_sheet` (and the form's Seller Close
wizard) takes that amount, records it in Commission Withheld in the same step, and
refuses more than the commission or than the cash collected minus seller deposits;
`declare_collection_cash` corrects it on a submitted sheet. On a submitted sheet, the
form's Declare Cash button declares the amount typed in Commission Withheld without that
cap, so Collections can correct it. The commission voucher Confirm mints stays in step
with the declared commission after a Cancel and Reinstate.

Per-company Collection Settings (`res.company` + related `res.config.settings`; XMLID
`collection.action_collection_config_settings`) control enabled sellers (empty = none
for new work), auto-create sheet (default ON), allowed document types, Document Review,
and the active `collection.connector`. Administrators, and Collections Managers from
Company Collection Settings, can Import sellers from that connector: it creates,
matches, and binds users inside the company only, adds them to the enabled list, refuses
an empty answer, and keeps enabled sellers missing from the answer (they are named in a
warning for a manager to disable). Voucher (`COL/`) and sheet (`CS/`) sequences are per
company. Customer bindings (`collection.connector.customer.binding`) map an external
customer to a partner; Collections Users may create them (`1,0,1,0`) and MUST never
`sudo()`.

Access follows two roles. **Collections User** (`collection.group_collection_user`) is
for back-office operators and the MCP API user: Document Review, allocations, the
receipt proposal board, and Confirm. It may create contacts (no edit or delete) so new
customers can be bound without `base.group_partner_manager`. Plain internal users (CRM
users, and the password-less seller identities that Import creates) get no access to
collection data; sellers act only through the agent. Close, Cancel, Reinstate, and Reset
to Open need a Collections Manager, and the server checks the role, not only the button.
The **Collections Manager** group (`collection.group_collection_manager`) implies
Collections User and grants collection configuration without system administration; the
administrator is a manager on install. Under Collections → Configuration, **Company
Collection Settings** edits only the current company's collection options and imports
sellers within that company. **Configure Connection** opens the same connector form used
by **Manage Connectors and Mappings**, with company-scoped CRUD, SQLite/Bejerman
settings, connection testing, and Bejerman snapshot refresh. Use the form's native
**Save** and **Discard** controls; there is no separate connector settings dialog.
Credentials, the web service URL, TLS options, the CA bundle, and the SQLite path are
shown and written only for administrators. Connector operations are server-side only
(`@api.private`); Test Connection checks for an administrator or a Collections Manager.
**Company Bank Accounts** manages only bank accounts belonging to the user's allowed
companies. Company record rules continue to apply to vouchers, sheets, allocations,
receipts, and connector bindings. Privileged configuration writes use fixed field lists
after checking the caller's manager group and company access; collection operations and
MCP tools never elevate. Workflow guards are internal server-side scopes: a context key
sent over RPC or by an MCP tool cannot open them. Creating a company or user is an
explicit database setup step, so installing the module does not create business
companies or login credentials.

Receipts are typed into the ERP by hand. Once that is done for a closed sheet, a
Collections Manager marks it **Entered in the ERP** (undo allowed; Cancel clears it),
and the filter **Pending ERP entry** lists closed sheets still waiting. Until a sheet is
marked and a connector refresh that started after the mark has succeeded, its applied
amounts keep being subtracted from the ERP balances the agent sees; cancelled sheets are
never subtracted.

MCP `create_collection_allocation` takes a top-level `customer_identification`, the
payments, and the receipts that split them, and returns the sheet, the vouchers, and the
draft allocation. On all-new create only, the server lazily resolves the identification
into `partner_id` (by CUIT digits among commercial partners) and MAY create a
`res.partner` plus customer binding. A replay answers only the seller that wrote it and
only with the same content: a reused `request_id` needs the same payments, receipts and
customer, and a reused `document_id` the same seller and payment fields; anything else
is a generic conflict. Each payment may nest `raw_ocr` and `seller_confirmed` (typed
review fields; both omitted leaves empty provenance). MCP `get_seller_id` resolves
`{seller_id}` from a WhatsApp/mobile among the company's enabled sellers. MCP
`list_collection_customers` and `customer_debt` MUST NOT create partners.
`list_collection_customers` returns `{customers}`; with an optional `query` (a name,
CUIT, or customer code, whole or in part) it returns at most 10 matches as
`{customers, total_matches, truncated}`, each tagged `match` `exact`, `partial`, or
`similar`. `customer_debt` returns `{customer, summary, invoices, as_of}`: `as_of` says
when the connector's copy of the ERP was taken, and a copy older than the connector
allows is refused. The summary's `total_balance` is net of open credit notes
(`gross_total`, `credit_total`, `net_total`), with `overdue_balance` and `open_balance`;
invoice rows keep their gross `balance` and add `allocatable_balance`, with summary
`total_allocatable_balance`, `open_allocatable_balance`, and
`overdue_allocatable_balance` (gross minus the reservations described above, clamped at
zero). MCP `get_collection_sheet_pdf` takes only `seller_id` and returns the seller's
open (else submitted) Planilla de Cobranza as
`{sheet, filename, mimetype, content_base64}`, or `{sheet: null}` when there is neither.
Every tool requires a Collections User caller and can be bound to a trusted seller
header (see Configure).
