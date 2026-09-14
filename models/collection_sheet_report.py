# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

from .collection_common import FROZEN_SHEET_STATES, SELLER_DECLARATION_STATES

_VOUCHER_BLOCK_ORDER = ("bank_transfer", "check", "cash_deposit")
_DOCUMENT_KIND_ORDER = ("invoice", "quotation")
_VOUCHER_BLOCK_LABELS = {
    "bank_transfer": "Transferencia bancaria",
    "check": "Cheque",
    "cash_deposit": "Depósito en efectivo",
    "unsupported": "Otros",
}
_SHEET_STATE_LABELS = {
    "open": "Abierta",
    "submitted": "Rendida",
    "proposal": "Propuesta",
    "closed": "Cerrada",
    "cancelled": "Cancelada",
}
_CHECK_TYPE_LABELS = {
    "common": "Común",
    "deferred": "Diferido",
}
_SELLER_DECLARATION_FIELDS = frozenset({"commission_withheld"})
_ADMIN_RATE_FIELDS = frozenset({"commission_percent"})
_RECON_STATUS = {
    -1: "outstanding",
    0: "balanced",
    1: "in_favor",
}


class CollectionSheetReport(models.Model):
    _inherit = "collection.sheet"

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        readonly=True,
    )
    commission_percent = fields.Float(
        string="Seller Commission %",
        digits=(16, 2),
        default=0.0,
    )
    cash_on_hand = fields.Monetary(
        string="Cash to Administration",
        currency_field="currency_id",
        compute="_compute_cash_on_hand",
        store=True,
        readonly=True,
        tracking=True,
        copy=False,
    )
    commission_withheld = fields.Monetary(
        currency_field="currency_id",
        tracking=True,
        copy=False,
    )
    cash_declared_at = fields.Datetime(copy=False, readonly=True)
    cash_declared_by = fields.Many2one(
        comodel_name="res.users",
        copy=False,
        readonly=True,
        ondelete="restrict",
    )
    cash_collected = fields.Monetary(
        compute="_compute_cash_banked_totals",
        currency_field="currency_id",
    )
    cash_banked = fields.Monetary(
        compute="_compute_cash_banked_totals",
        currency_field="currency_id",
    )

    _commission_percent_range = models.Constraint(
        "CHECK(commission_percent >= 0 AND commission_percent <= 100)",
        "Seller commission percent must be between 0 and 100.",
    )

    @api.model
    @api.private
    def _seller_commission_rates(self, pairs):
        """Map ``(company_id, seller_id)`` to the connector binding percent.

        Fail-soft like ``_prepare_customer_debt_lines``: pairs without an active
        company connector or without a seller binding are simply absent from the
        result, so callers fall back to ``0.0``. One search for the whole batch.
        """
        rates = {}
        wanted = {
            (company_id, seller_id)
            for company_id, seller_id in pairs
            if isinstance(company_id, int)
            and isinstance(seller_id, int)
            and company_id
            and seller_id
        }
        if not wanted:
            return rates
        companies = self.env["res.company"].browse(
            sorted({company_id for company_id, _seller_id in wanted})
        )
        connector_companies = {}
        for company in companies:
            connector = company.collection_connector_id
            if connector and connector.active:
                connector_companies[connector.id] = company.id
        if not connector_companies:
            return rates
        bindings = self.env["collection.connector.seller.binding"].search(
            [
                ("connector_id", "in", list(connector_companies)),
                ("user_id", "in", sorted({seller for _company, seller in wanted})),
            ]
        )
        for binding in bindings:
            key = (connector_companies[binding.connector_id.id], binding.user_id.id)
            if key in wanted:
                rates[key] = binding.commission_percent or 0.0
        return rates

    @api.model
    @api.private
    def _prepare_seller_commission_percent(self, seller, company):
        """Seller rate from the company connector binding; ``0.0`` when unresolved."""
        if not seller or not company:
            return 0.0
        key = (company.id, seller.id)
        return self._seller_commission_rates([key]).get(key, 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        """Seed the reconciliation rate from the seller connector binding.

        Create-time snapshot only: a later Import never rewrites an existing
        sheet, and the value stays editable while the sheet is not frozen. The
        web client posts ``commission_percent`` 0 on every form create, so a
        falsy incoming value counts as "not set".
        """
        if any("cash_on_hand" in vals for vals in vals_list):
            raise UserError(
                _(
                    "Cash to Administration is computed from the sheet vouchers "
                    "and the commission withheld; it cannot be written."
                )
            )
        pending = [
            vals
            for vals in vals_list
            if vals.get("seller_id") and not vals.get("commission_percent")
        ]
        if pending:
            keys = [
                (vals.get("company_id") or self.env.company.id, vals["seller_id"])
                for vals in pending
            ]
            rates = self._seller_commission_rates(keys)
            for vals, key in zip(pending, keys, strict=True):
                rate = rates.get(key)
                if rate:
                    vals["commission_percent"] = rate
        return super().create(vals_list)

    @api.onchange("seller_id")
    def _onchange_seller_commission_percent(self):
        """Show the seller rate as soon as the seller is picked on a new sheet."""
        if self._origin.id:
            return
        self.commission_percent = self._prepare_seller_commission_percent(
            self.seller_id, self.company_id or self.env.company
        )

    def write(self, vals):
        declarations = _SELLER_DECLARATION_FIELDS & set(vals)
        rates = _ADMIN_RATE_FIELDS & set(vals)
        if "cash_on_hand" in vals:
            raise UserError(
                _(
                    "Cash to Administration is computed from the sheet vouchers "
                    "and the commission withheld; it cannot be written."
                )
            )
        if declarations and any(
            sheet.state not in SELLER_DECLARATION_STATES for sheet in self
        ):
            raise UserError(
                _(
                    "Seller-declared commission withheld can only be changed on "
                    "a submitted collection sheet."
                )
            )
        if rates and any(sheet.state in FROZEN_SHEET_STATES for sheet in self):
            raise UserError(
                _("Closed collection sheets cannot change the reconciliation inputs.")
            )
        return super().write(vals)

    @api.depends("voucher_ids.document_type", "voucher_ids.amount")
    def _compute_cash_banked_totals(self):
        """Sum cash and seller_deposit voucher amounts. Never the replacement ledger."""
        for sheet in self:
            collected = 0.0
            banked = 0.0
            for voucher in sheet.voucher_ids:
                amount = voucher.amount or 0.0
                if voucher.document_type == "cash":
                    collected += amount
                elif voucher.document_type == "seller_deposit":
                    banked += amount
            sheet.cash_collected = collected
            sheet.cash_banked = banked

    @api.depends(
        "voucher_ids.document_type",
        "voucher_ids.amount",
        "commission_withheld",
        "currency_id",
    )
    def _compute_cash_on_hand(self):
        """Cash the seller still owes administration.

        Derived, never declared: collected cash minus what the seller already
        remitted (``seller_deposit``) minus the commission they kept.
        """
        for sheet in self:
            amount = (
                (sheet.cash_collected or 0.0)
                - (sheet.cash_banked or 0.0)
                - (sheet.commission_withheld or 0.0)
            )
            currency = sheet.currency_id
            sheet.cash_on_hand = currency.round(amount) if currency else amount

    def _collection_report_data(self):
        """Build the shared Planilla de Cobranza payload (primitives + records)."""
        self.ensure_one()
        self._ensure_saved_sheet()
        currencies = self.allocation_ids.currency_id
        if len(currencies) > 1:
            raise UserError(
                _("Collection sheet report does not support mixed currencies.")
            )
        currency = self._collection_report_currency()
        partners = self.allocation_ids.partner_id | self.voucher_ids.partner_id
        codes = self._collection_report_customer_codes(partners)
        customers = self._collection_report_customers(codes)
        document_blocks = self._collection_report_document_blocks(codes)
        voucher_blocks = self._collection_report_voucher_blocks(codes)
        collected_total = sum(block["subtotal"] for block in voucher_blocks)
        applied_total = sum(block["subtotal_applied"] for block in document_blocks)
        tendered = self._collection_report_tendered()
        recon = self._collection_report_recon(collected_total, tendered)
        alloc_collected = sum(
            allocation.total_vouchers or 0.0 for allocation in self.allocation_ids
        )
        mismatch = currency.compare_amounts(alloc_collected, collected_total) != 0
        return {
            "company": self.company_id.name or "",
            "printed_on": fields.Date.context_today(self),
            "reference": self.name or "",
            "state_label": _SHEET_STATE_LABELS.get(self.state) or self.state or "",
            "seller_name": self.seller_id.name or "",
            "currency_name": currency.name or "",
            "date_from": self.date_from or False,
            "date_to": self.date_to or False,
            "customer_count": len(customers),
            "voucher_count": len(self.voucher_ids),
            "commission_percent": self.commission_percent or 0.0,
            "customers": customers,
            "customer_totals": {
                "debt": sum(row["debt"] for row in customers),
                "collected": sum(row["collected"] for row in customers),
                "applied": sum(row["applied"] for row in customers),
                "residual": sum(row["residual"] for row in customers),
            },
            "document_blocks": document_blocks,
            "applied_total": applied_total,
            "voucher_blocks": voucher_blocks,
            "collected_total": collected_total,
            "cash_banked": self.cash_banked or 0.0,
            "tendered": tendered,
            "recon": recon,
            "mismatch": mismatch,
            "sheet": self,
            "currency": currency,
        }

    def action_print_xlsx(self):
        """Build Planilla XLSX, store it on the sheet, and return a download URL."""
        self.ensure_one()
        content = self.env["collection.sheet.xlsx"]._render_xlsx(
            self._collection_report_data()
        )
        filename = f"{(self.name or '').replace('/', '-')}.xlsx"
        Attachment = self.env["ir.attachment"]
        Attachment.search(
            [
                ("res_model", "=", self._name),
                ("res_id", "=", self.id),
                ("name", "=", filename),
            ]
        ).unlink()
        attachment = Attachment.create(
            {
                "name": filename,
                "type": "binary",
                "raw": content,
                "mimetype": (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
                "res_model": self._name,
                "res_id": self.id,
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "download",
        }

    @api.private
    def _collection_report_currency(self):
        """Allocation currency when the sheet has one, else the company currency."""
        self.ensure_one()
        return self.allocation_ids.currency_id[:1] or self.currency_id

    @api.private
    def _collection_report_customer_codes(self, partners):
        """Return `{partner_id: code}` from raw connector bindings (blank if none)."""
        self.ensure_one()
        codes = {partner.id: "" for partner in partners}
        connector = self.company_id.collection_connector_id
        if not connector or not partners:
            return codes
        bindings = self.env["collection.connector.customer.binding"].search(
            [
                ("connector_id", "=", connector.id),
                ("partner_id", "in", partners.ids),
            ]
        )
        for binding in bindings:
            codes[binding.partner_id.id] = binding.customer_code or ""
        return codes

    @api.private
    def _collection_report_customers(self, codes):
        """Customer rows sorted coded-first, then code, then name."""
        self.ensure_one()
        rows = []
        for allocation in self.allocation_ids:
            partner = allocation.partner_id
            code = codes.get(partner.id, "") or ""
            rows.append(
                (
                    self._collection_report_code_sort(code, partner.name),
                    {
                        "code": code,
                        "name": partner.name or "",
                        "debt": allocation.total_debt or 0.0,
                        "collected": allocation.total_vouchers or 0.0,
                        "applied": allocation.total_applied or 0.0,
                        "residual": allocation.residual or 0.0,
                        "residual_reason": "",
                    },
                )
            )
        rows.sort(key=lambda item: item[0])
        return [item[1] for item in rows]

    @api.private
    def _collection_report_document_blocks(self, codes):
        """Split invoice then quotation blocks; drop empties; round then sum."""
        self.ensure_one()
        currency = self._collection_report_currency()
        percent = self.commission_percent or 0.0
        grouped = {kind: [] for kind in _DOCUMENT_KIND_ORDER}
        for line in self.allocation_ids.line_ids:
            kind = line.document_kind or "invoice"
            if kind not in grouped:
                continue
            partner = line.allocation_id.partner_id
            code = codes.get(partner.id, "") or ""
            applied = line.amount_applied or 0.0
            commission = currency.round(applied * percent / 100.0)
            grouped[kind].append(
                (
                    self._collection_report_code_sort(code, partner.name)
                    + ((line.due_date or date.max), line.invoice_number or ""),
                    {
                        "code": code,
                        "name": partner.name or "",
                        "invoice_number": line.invoice_number or "",
                        "due_date": line.due_date or False,
                        "issue_date": line.issue_date or False,
                        "invoice_balance": line.invoice_balance or 0.0,
                        "amount_applied": applied,
                        "commission": commission,
                    },
                )
            )
        blocks = []
        for kind in _DOCUMENT_KIND_ORDER:
            entries = grouped[kind]
            if not entries:
                continue
            entries.sort(key=lambda item: item[0])
            rows = [item[1] for item in entries]
            blocks.append(
                {
                    "kind": kind,
                    "rows": rows,
                    "subtotal_applied": sum(row["amount_applied"] for row in rows),
                    "subtotal_commission": sum(row["commission"] for row in rows),
                }
            )
        return blocks

    @api.private
    def _collection_report_voucher_blocks(self, codes):
        """Group vouchers by catalog code; skip remittance; remaining alpha."""
        self.ensure_one()
        labels = {
            row.code: row.name
            for row in self.env["collection.document.type"].search([])
        }
        grouped = {}
        for voucher in self.voucher_ids:
            code = voucher.document_type or ""
            if code == "seller_deposit":
                continue
            partner = voucher.partner_id
            partner_code = codes.get(partner.id, "") or ""
            voucher_date = (
                fields.Date.to_date(voucher.create_date)
                if voucher.create_date
                else date.max
            )
            grouped.setdefault(code, []).append(
                (
                    self._collection_report_code_sort(partner_code, partner.name)
                    + (voucher_date, voucher.name or ""),
                    self._collection_report_voucher_row(voucher, partner_code),
                )
            )
        remaining = sorted(code for code in grouped if code not in _VOUCHER_BLOCK_ORDER)
        blocks = []
        for code in (*_VOUCHER_BLOCK_ORDER, *remaining):
            entries = grouped.get(code)
            if not entries:
                continue
            entries.sort(key=lambda item: item[0])
            rows = [item[1] for item in entries]
            blocks.append(
                {
                    "code": code,
                    "label": (
                        _VOUCHER_BLOCK_LABELS.get(code) or labels.get(code) or code
                    ),
                    "rows": rows,
                    "subtotal": sum(row["amount"] for row in rows),
                }
            )
        return blocks

    @api.private
    def _collection_report_voucher_row(self, voucher, partner_code):
        """Type-specific comprobante number and check details (never sequence name)."""
        is_check = voucher.document_type == "check"
        if is_check:
            number = voucher.check_number or ""
            display_date = voucher.check_issue_date or False
        else:
            number = voucher.voucher_number or ""
            display_date = voucher.voucher_date or (
                fields.Date.to_date(voucher.create_date)
                if voucher.create_date
                else False
            )
        return {
            "code": partner_code,
            "name": voucher.partner_id.name or "",
            "number": number,
            "date": display_date,
            "amount": voucher.amount or 0.0,
            "state": voucher.state or "",
            "check_bank": (voucher.check_bank or "") if is_check else "",
            "check_type": (
                _CHECK_TYPE_LABELS.get(voucher.check_type) or "" if is_check else ""
            ),
            "check_payment_date": (
                voucher.check_payment_date or False if is_check else False
            ),
        }

    @api.private
    def _collection_report_tendered(self):
        """Cash on hand plus typed voucher totals, including remittance."""
        self.ensure_one()
        deposits = 0.0
        checks = 0.0
        transfers = 0.0
        echecks = 0.0
        retentions = 0.0
        seller_deposits = 0.0
        for voucher in self.voucher_ids:
            amount = voucher.amount or 0.0
            if voucher.document_type == "cash_deposit":
                deposits += amount
            elif voucher.document_type == "check":
                checks += amount
            elif voucher.document_type == "bank_transfer":
                transfers += amount
            elif voucher.document_type == "echeck":
                echecks += amount
            elif voucher.document_type == "retention_certificate":
                retentions += amount
            elif voucher.document_type == "seller_deposit":
                seller_deposits += amount
        cash = self.cash_on_hand or 0.0
        return {
            "cash": cash,
            "deposits": deposits,
            "checks": checks,
            "transfers": transfers,
            "echecks": echecks,
            "retentions": retentions,
            "seller_deposits": seller_deposits,
            "total": (
                cash
                + deposits
                + checks
                + transfers
                + echecks
                + retentions
                + seller_deposits
            ),
        }

    @api.private
    def _collection_report_recon(self, collected, tendered):
        """Tri-state banner from tendered minus net due."""
        self.ensure_one()
        currency = self._collection_report_currency()
        withheld = self.commission_withheld or 0.0
        net_due = collected - withheld
        tendered_total = tendered["total"]
        difference = tendered_total - net_due
        compared = currency.compare_amounts(difference, 0.0)
        status = _RECON_STATUS[compared]
        messages = {
            "balanced": _("Cuadrada"),
            "in_favor": _("A favor del vendedor"),
            "outstanding": _("Pendiente de rendir"),
        }
        return {
            "collected": collected,
            "withheld": withheld,
            "net_due": net_due,
            "tendered": tendered_total,
            "difference": difference,
            "status": status,
            "status_message": messages[status],
        }

    @api.private
    def _collection_report_code_sort(self, code, partner_name):
        """Sort key: coded customers first, then code, then name."""
        value = code or ""
        return (value == "", value, partner_name or "")
