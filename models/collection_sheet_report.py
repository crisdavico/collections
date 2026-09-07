# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

from .collection_common import FROZEN_SHEET_STATES

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
    "proposal": "Propuesta",
    "closed": "Cerrada",
    "cancelled": "Cancelada",
}
_CHECK_TYPE_LABELS = {
    "common": "Común",
    "deferred": "Diferido",
}
_RECON_INPUT_FIELDS = frozenset(
    {"cash_on_hand", "commission_withheld", "commission_percent"}
)
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
        currency_field="currency_id",
        tracking=True,
        copy=False,
    )
    commission_withheld = fields.Monetary(
        currency_field="currency_id",
        tracking=True,
        copy=False,
    )

    _commission_percent_range = models.Constraint(
        "CHECK(commission_percent >= 0 AND commission_percent <= 100)",
        "Seller commission percent must be between 0 and 100.",
    )

    def write(self, vals):
        frozen = _RECON_INPUT_FIELDS & set(vals)
        if frozen and any(sheet.state in FROZEN_SHEET_STATES for sheet in self):
            raise UserError(
                _("Closed collection sheets cannot change the reconciliation inputs.")
            )
        return super().write(vals)

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
        """Group vouchers by catalog code; preferred types then remaining alpha."""
        self.ensure_one()
        labels = {
            row.code: row.name
            for row in self.env["collection.document.type"].search([])
        }
        grouped = {}
        for voucher in self.voucher_ids:
            code = voucher.document_type or ""
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
        """Cash on hand plus deposit, check, and transfer voucher totals."""
        self.ensure_one()
        deposits = 0.0
        checks = 0.0
        transfers = 0.0
        for voucher in self.voucher_ids:
            amount = voucher.amount or 0.0
            if voucher.document_type == "cash_deposit":
                deposits += amount
            elif voucher.document_type == "check":
                checks += amount
            elif voucher.document_type == "bank_transfer":
                transfers += amount
        cash = self.cash_on_hand or 0.0
        return {
            "cash": cash,
            "deposits": deposits,
            "checks": checks,
            "transfers": transfers,
            "total": cash + deposits + checks + transfers,
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
