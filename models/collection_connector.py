# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re
from datetime import datetime

import pytz
from psycopg2.errors import UniqueViolation

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_DISPATCH_OPS = frozenset(
    {
        "test_connection",
        "list_sellers",
        "list_customers",
        "get_customer_debt",
        "create_receipt",
    }
)
_OUTSTANDING_INVOICE_STATES = frozenset({"open", "overdue"})


def _row_is_active(row):
    active = row.get("active", True)
    return active not in (0, "0", False, "false", "False")


def _invoice_is_outstanding(row):
    try:
        balance = float(row.get("balance") or 0)
    except (TypeError, ValueError):
        return False
    return balance > 0 and row.get("state") in _OUTSTANDING_INVOICE_STATES


def _format_amount(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def as_of_to_utc(value):
    """Naive UTC datetime of an ``as_of`` ISO string (False when empty)."""
    if not value:
        return False
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo:
        stamp = stamp.astimezone(pytz.utc).replace(tzinfo=None)
    return stamp


def company_timezone(company, user):
    """Company timezone (company partner, else the user, else UTC)."""
    tz_name = company.partner_id.tz or user.tz or "UTC"
    try:
        return pytz.timezone(tz_name)
    except pytz.UnknownTimeZoneError:
        return pytz.utc


class CollectionConnector(models.Model):
    _name = "collection.connector"
    _description = "Collection Connector"
    _order = "name"

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)
    type = fields.Selection(selection=[])
    seller_binding_ids = fields.One2many(
        comodel_name="collection.connector.seller.binding",
        inverse_name="connector_id",
    )
    customer_binding_ids = fields.One2many(
        comodel_name="collection.connector.customer.binding",
        inverse_name="connector_id",
    )

    def test_connection(self):
        """Form button: stays public, so it checks who may manage the connector."""
        self.ensure_one()
        self._check_connection_test_access()
        self._dispatch("test_connection")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": _("Connection Test Successful!"),
                "message": _("The collection connector is configured."),
                "sticky": False,
            },
        }

    @api.private
    def _check_connection_test_access(self):
        self.ensure_one()
        if self.env.su or self.env.user._is_system():
            return
        self._check_collection_management_access()

    # The operations below are called server side only (MCP tools, Import and
    # allocation helpers), never over RPC.

    @api.private
    def list_sellers(self):
        self.ensure_one()
        return self._format_seller_list(self._dispatch("list_sellers"))

    @api.private
    def list_customers(self, seller_id):
        self.ensure_one()
        external_seller_id = self._enabled_bound_external_seller_id(seller_id)
        rows = self._dispatch("list_customers", external_seller_id)
        return self._format_customer_list(rows)

    @api.private
    def get_customer_debt(self, seller_id, customer_identification):
        self.ensure_one()
        identification = self._require_customer_identification(customer_identification)
        external_seller_id = self._enabled_bound_external_seller_id(seller_id)
        payload = self._dispatch(
            "get_customer_debt", external_seller_id, identification
        )
        return self._format_customer_debt(payload)

    @api.private
    def create_receipt(self, receipt):
        self.ensure_one()
        return self._dispatch("create_receipt", receipt)

    @api.private
    def resolve_customer_partner(self, seller_id, identification):
        self.ensure_one()
        identification = self._require_customer_identification(identification)
        self._enabled_bound_external_seller_id(seller_id)
        Binding = self.env["collection.connector.customer.binding"]
        binding = Binding.search(
            [
                ("connector_id", "=", self.id),
                ("identification", "=", identification),
            ],
            limit=1,
        )
        if binding:
            return binding.partner_id
        return self._resolve_unbound_customer_partner(seller_id, identification)

    @api.private
    def _resolve_unbound_customer_partner(self, seller_id, identification):
        self.ensure_one()
        matches = [
            row
            for row in self.list_customers(seller_id).get("customers") or []
            if str(row.get("identification") or "").strip() == identification
        ]
        if len(matches) != 1:
            raise UserError(_("The requested customer is not available."))
        row = matches[0]
        partners = self._collection_commercial_partners_by_cuit(identification)
        if len(partners) > 1:
            raise UserError(_("The requested customer is not available."))
        Binding = self.env["collection.connector.customer.binding"]
        try:
            with self.env.cr.savepoint():
                if partners:
                    partner = partners
                else:
                    partner = self.company_id._collection_create_partners(
                        [
                            {
                                "name": row.get("name") or identification,
                                "vat": identification,
                                "company_id": self.company_id.id,
                                "customer_rank": 1,
                            }
                        ]
                    )
                Binding.create(
                    {
                        "connector_id": self.id,
                        "external_customer_id": row.get("external_customer_id") or "",
                        "identification": identification,
                        "partner_id": partner.id,
                        "customer_code": row.get("customer_code") or False,
                    }
                )
                return partner
        except UniqueViolation:
            Binding.invalidate_model()
            binding = Binding.search(
                [
                    ("connector_id", "=", self.id),
                    ("identification", "=", identification),
                ],
                limit=1,
            )
            if binding:
                return binding.partner_id
            # Another binding constraint (the partner or the external id is
            # already bound under another identification): never leak the
            # database error.
            raise UserError(_("The requested customer is not available.")) from None

    @api.private
    def _collection_commercial_partners_by_cuit(self, identification):
        """Commercial partners whose VAT has the digits of ``identification``.

        The VAT is stored with or without dashes (both exist in this database)
        or with a country prefix, so both sides compare digits only. Contacts
        inherit their parent's VAT; only partners without a parent count.
        """
        digits = re.sub(r"\D", "", identification or "")
        if not digits:
            return self.env["res.partner"]
        variants = {identification, digits, f"AR{digits}"}
        if len(digits) == 11:
            variants.add(f"{digits[:2]}-{digits[2:10]}-{digits[10]}")
        candidates = self.env["res.partner"].search(
            [("vat", "in", sorted(variants)), ("parent_id", "=", False)]
        )
        return candidates.filtered(
            lambda partner: re.sub(r"\D", "", partner.vat or "") == digits
        )

    @api.private
    def _dispatch(self, op, *args):
        self.ensure_one()
        if op not in _DISPATCH_OPS:
            raise UserError(_("The requested connector operation is not available."))
        connector_type = self.type
        type_keys = {
            value
            for value, _label in self._fields["type"]._description_selection(self.env)
        }
        if not connector_type or connector_type not in type_keys:
            raise UserError(_("The collection connector is not configured."))
        method = getattr(self, f"_{connector_type}_{op}", None)
        if not callable(method):
            raise UserError(_("The requested connector operation is not available."))
        return method(*args)

    @api.private
    def _enabled_bound_external_seller_id(self, seller_id):
        self.ensure_one()
        try:
            seller_pk = int(seller_id)
        except (TypeError, ValueError) as err:
            raise UserError(_("The requested seller is not available.")) from err
        enabled = self.env.company.enabled_seller_ids.filtered(
            lambda user: user.id == seller_pk
        )
        if len(enabled) != 1:
            raise UserError(_("The requested seller is not available."))
        binding = self.seller_binding_ids.filtered(
            lambda rec: rec.user_id.id == enabled.id
        )
        if len(binding) != 1:
            raise UserError(_("The requested seller is not available."))
        return binding.external_seller_id

    @api.private
    def _require_customer_identification(self, customer_identification):
        if customer_identification in (None, False):
            raise UserError(_("The requested customer is not available."))
        identification = str(customer_identification).strip()
        if not identification:
            raise UserError(_("The requested customer is not available."))
        return identification

    @api.private
    def _collection_erp_reflected_since(self):
        """Time from which this connector's data includes manual ERP entries.

        A sheet marked "Entered in the ERP" before this time is already in the
        balances the connector serves, so its applied amounts are no longer
        subtracted from them. A connector reading the ERP live answers "now";
        one with a snapshot answers when its last successful refresh STARTED.
        False (this default) means unknown: keep subtracting.
        """
        self.ensure_one()
        return False

    @api.private
    def _source_payload(self):
        """Return the connector provenance block shared by every read payload."""
        self.ensure_one()
        return {
            "connector_id": self.id,
            "connector_type": self.type,
            "connector_name": self.name,
            "company_id": self.company_id.id,
        }

    @api.private
    def _format_seller_list(self, rows):
        self.ensure_one()
        bindings = {
            binding.external_seller_id: binding.user_id.id
            for binding in self.seller_binding_ids
        }
        sellers = []
        for row in rows or []:
            if not _row_is_active(row):
                continue
            external_id = str(row.get("id") or row.get("external_seller_id") or "")
            sellers.append(
                {
                    "external_seller_id": external_id,
                    "name": row.get("name") or "",
                    "mobile": row.get("mobile") or "",
                    "active": True,
                    "odoo_seller_id": bindings.get(external_id),
                    "commission_percent": row.get("commission_percent", 0.0),
                }
            )
        return {
            "sellers": sellers,
            "source": self._source_payload(),
        }

    @api.private
    def _format_customer_list(self, rows):
        self.ensure_one()
        customers = []
        for row in rows or []:
            if not _row_is_active(row):
                continue
            customers.append(
                {
                    "external_customer_id": str(
                        row.get("id") or row.get("external_customer_id") or ""
                    ),
                    "name": row.get("name") or "",
                    "identification": row.get("identification") or "",
                    "customer_code": row.get("customer_code") or "",
                }
            )
        return {
            "customers": customers,
            "source": self._source_payload(),
        }

    @api.private
    def _format_customer_debt(self, payload):
        self.ensure_one()
        if not isinstance(payload, dict):
            raise UserError(_("The requested customer is not available."))
        customer = payload.get("customer")
        if not customer or not _row_is_active(customer):
            raise UserError(_("The requested customer is not available."))
        invoices = []
        for row in payload.get("invoices") or []:
            if not _invoice_is_outstanding(row):
                continue
            kind = row.get("document_kind")
            if kind in (None, False, ""):
                kind = "invoice"
            invoices.append(
                {
                    "external_invoice_id": str(
                        row.get("id") or row.get("external_invoice_id") or ""
                    ),
                    "number": row.get("number") or "",
                    "issue_date": row.get("issue_date") or "",
                    "due_date": row.get("due_date") or "",
                    "amount": _format_amount(row.get("amount")),
                    "balance": _format_amount(row.get("balance")),
                    "state": row.get("state") or "",
                    "document_kind": kind,
                }
            )
        invoices.sort(
            key=lambda row: (
                row["due_date"],
                row["number"],
                row["external_invoice_id"],
            )
        )
        open_balance = sum(row["balance"] for row in invoices if row["state"] == "open")
        overdue_balance = sum(
            row["balance"] for row in invoices if row["state"] == "overdue"
        )
        # Decision D4: open credit notes net the customer's total; the invoice
        # rows (what allocations target) stay gross. Adapters report the open
        # credit as one amount, of either sign.
        currency = self.company_id.currency_id
        gross_total = open_balance + overdue_balance
        credit_total = currency.round(abs(_format_amount(payload.get("credit_total"))))
        net_total = currency.round(gross_total - credit_total)
        return {
            "customer": {
                "external_customer_id": str(
                    customer.get("id") or customer.get("external_customer_id") or ""
                ),
                "name": customer.get("name") or "",
                "identification": customer.get("identification") or "",
                "customer_code": customer.get("customer_code") or "",
            },
            "summary": {
                # What the customer owes: open invoices net of open credits.
                "total_balance": net_total,
                "overdue_balance": overdue_balance,
                "open_balance": open_balance,
                "invoice_count": len(invoices),
                "gross_total": gross_total,
                "credit_total": credit_total,
                "net_total": net_total,
            },
            "invoices": invoices,
            "as_of": self._collection_as_of(payload.get("as_of")),
            "source": self._source_payload(),
        }

    @api.private
    def _collection_as_of(self, value):
        """ISO 8601 time, in the company timezone, the figures were read at.

        ``value`` is the adapter's naive UTC time of its copy of the ERP (a
        snapshot refresh). An adapter that reads the ERP live gives none, so
        the read time stands.
        """
        self.ensure_one()
        stamp = fields.Datetime.to_datetime(value) if value else None
        if not stamp:
            stamp = fields.Datetime.now()
        tz = company_timezone(self.company_id, self.env.user)
        local = pytz.utc.localize(stamp.replace(microsecond=0)).astimezone(tz)
        return local.isoformat()
