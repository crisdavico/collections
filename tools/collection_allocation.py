# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import annotations

import hashlib
import json
from typing import Any

from psycopg2.errors import UniqueViolation

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import SQL

from odoo.addons.collection.models.collection_common import (
    SELLER_SHEET_STATES,
    privileged,
)
from odoo.addons.collection.tools.collection_voucher import (
    _COLLECTION_AMOUNT_SCHEMA,
    _PAYMENT_SCHEMA,
    _collection_normalize_amount,
    _collection_reject_unknown_keys,
)
from odoo.addons.muk_mcp.core.tool import mcp_tool

_DOCUMENT_KINDS = ("invoice", "quotation")
_RECEIPT_KEYS = frozenset({"document_kind", "values", "applications"})
_RECEIPT_VALUE_KEYS = frozenset({"document_id", "amount"})
_RECEIPT_APPLICATION_KEYS = frozenset(
    {"external_document_id", "number", "balance_seen", "amount_applied"}
)

_RECEIPT_VALUE_SCHEMA = {
    "type": "object",
    "properties": {
        "document_id": {
            "type": "string",
            "minLength": 1,
            "description": "Payment document_id from payments[] in this call.",
        },
        "amount": dict(_COLLECTION_AMOUNT_SCHEMA),
    },
    "required": ["document_id", "amount"],
}

_RECEIPT_APPLICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "external_document_id": {
            "type": "string",
            "minLength": 1,
            "description": "External ERP invoice or quotation id.",
        },
        "number": {
            "type": "string",
            "nullable": True,
            "description": "Document number snapshot.",
        },
        "balance_seen": dict(_COLLECTION_AMOUNT_SCHEMA),
        "amount_applied": dict(_COLLECTION_AMOUNT_SCHEMA),
    },
    "required": ["external_document_id", "balance_seen", "amount_applied"],
}

_RECEIPT_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "document_kind": {
            "type": "string",
            "enum": list(_DOCUMENT_KINDS),
            "description": "Invoice or quotation receipt.",
        },
        "values": {
            "type": "array",
            "minItems": 1,
            "items": _RECEIPT_VALUE_SCHEMA,
            "description": "Payment amounts that fund this receipt.",
        },
        "applications": {
            "type": "array",
            "items": _RECEIPT_APPLICATION_SCHEMA,
            "description": "ERP documents this receipt pays; empty means on account.",
        },
    },
    "required": ["document_kind", "values"],
}

_CREATE_COLLECTION_ALLOCATION_SCHEMA = {
    "type": "object",
    "properties": {
        "seller_id": {
            "type": "integer",
            "description": "Internal seller user id (Enabled Seller).",
        },
        "customer_identification": {
            "type": "string",
            "minLength": 1,
            "description": "Customer identification from the connector binding.",
        },
        "request_id": {
            "type": "string",
            "minLength": 1,
            "description": "Idempotency key for this allocation write.",
        },
        "payments": {
            "type": "array",
            "minItems": 1,
            "items": _PAYMENT_SCHEMA,
            "description": "Inline payments to persist then allocate.",
        },
        "receipts": {
            "type": "array",
            "minItems": 1,
            "items": _RECEIPT_ITEM_SCHEMA,
            "description": "Receipts with values and optional applications.",
        },
    },
    "required": [
        "seller_id",
        "customer_identification",
        "request_id",
        "payments",
        "receipts",
    ],
}


class CollectionAllocationMixin(models.AbstractModel):
    """MuK MCP write tool for seller-validated collection allocations."""

    _inherit = "muk_mcp.mixin"

    @api.model
    @mcp_tool(
        name="create_collection_allocation",
        description=(
            "Create or amend a draft collection allocation for an Enabled "
            "Seller. Persists draft until sheet close. Amend is allowed only "
            "while draft. Returns {sheet_id, vouchers, allocation}. Collections "
            "Users only."
        ),
        input_schema=_CREATE_COLLECTION_ALLOCATION_SCHEMA,
        category="write",
        registry="mcp",
    )
    def create_collection_allocation(
        self,
        seller_id: int | None = None,
        customer_identification: str | None = None,
        request_id: str | None = None,
        payments: list[dict[str, Any]] | None = None,
        receipts: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Validate, persist inline payments, revalidate ERP, then allocate.

        :raise AccessError: when the caller is not a Collections User, or the
            trusted seller header does not verify the seller.
        :raise UserError: when input, seller, records, or revalidation fail.
        """
        if kwargs:
            _collection_reject_unknown_keys(
                kwargs,
                frozenset(),
                _("create_collection_allocation"),
            )
        self._collection_require_collection_user()
        document_ids, request_key, identification = (
            self._collection_parse_allocation_identity(
                payments,
                request_id,
                customer_identification,
            )
        )
        seller = self._collection_mcp_seller(seller_id)
        receipt_rows, payment_vals_list = self._collection_parse_allocation_form(
            payments, receipts, identification
        )
        replayed = self._collection_allocation_classify_request(
            request_key, document_ids, seller, receipt_rows, identification
        )
        if replayed is not None:
            return replayed
        self.env.company._assert_new_work(seller.id)
        if not self.env.company.auto_create_sheet:
            raise UserError(
                _("This company requires a collection sheet chosen in Odoo.")
            )
        try:
            return self._collection_allocation_write(
                seller,
                identification,
                request_key,
                document_ids,
                receipt_rows,
                payments,
                payment_vals_list,
            )
        except UniqueViolation:
            self.env.invalidate_all()
            replayed = self._collection_allocation_classify_request(
                request_key, document_ids, seller, receipt_rows, identification
            )
            if replayed is not None:
                return replayed
            raise self._collection_allocation_conflict_error() from None

    @api.model
    @api.private
    def _collection_parse_allocation_identity(
        self,
        payments: Any,
        request_id: Any,
        customer_identification: Any,
    ) -> tuple[list[str], str, str]:
        """Parse the identity fields: request_id, customer and document_ids."""
        if not isinstance(request_id, str) or not request_id.strip():
            raise UserError(_("request_id is required."))
        if (
            not isinstance(customer_identification, str)
            or not customer_identification.strip()
        ):
            raise UserError(_("customer_identification is required."))
        if not isinstance(payments, list) or not payments:
            raise UserError(_("payments must be a non-empty list."))
        document_ids: list[str] = []
        for index, raw in enumerate(payments):
            if not isinstance(raw, dict):
                raise UserError(
                    _("Payment at index %(index)s must be an object.", index=index)
                )
            document_id = raw.get("document_id")
            if not isinstance(document_id, str) or not document_id.strip():
                raise UserError(
                    _(
                        "Each payment requires a non-empty document_id "
                        "(index %(index)s).",
                        index=index,
                    )
                )
            document_ids.append(document_id.strip())
        if len(document_ids) != len(set(document_ids)):
            raise UserError(_("Duplicate document_id in the same call is not allowed."))
        return document_ids, request_id.strip(), customer_identification.strip()

    @api.model
    @api.private
    def _collection_parse_allocation_form(
        self,
        payments: Any,
        receipts: Any,
        identification: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Validate payment and receipt bodies (do not trust schema minItems).

        Identity fields are already validated by
        ``_collection_parse_allocation_identity``. The bodies are parsed before
        any request_id replay, because a replay must carry the same content.
        """
        payment_vals_list = self._collection_parse_payment_vals(
            payments, identification
        )
        receipt_rows = self._collection_parse_allocation_receipts(
            receipts, payment_vals_list
        )
        return receipt_rows, payment_vals_list

    @api.model
    @api.private
    def _collection_parse_allocation_receipts(
        self, receipts: Any, payment_vals_list: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Validate receipts-only MCP input; reject before any writes."""
        if not isinstance(receipts, list) or not receipts:
            raise UserError(_("receipts must be a non-empty list."))
        currency = self.env.company.currency_id
        amounts_by_doc = {
            vals["document_id"]: float(vals["amount"]) for vals in payment_vals_list
        }
        receipt_rows: list[dict[str, Any]] = []
        seen_kinds: set[str] = set()
        value_sums: dict[str, float] = {}
        seen_ext_global: set[str] = set()
        seen_payment_kind: set[tuple[str, str]] = set()
        for index, raw in enumerate(receipts):
            if not isinstance(raw, dict):
                raise UserError(
                    _("Receipt at index %(index)s must be an object.", index=index)
                )
            _collection_reject_unknown_keys(
                raw,
                _RECEIPT_KEYS,
                _("Receipt at index %(index)s", index=index),
            )
            kind = raw.get("document_kind")
            if kind not in _DOCUMENT_KINDS:
                raise UserError(
                    _(
                        "Receipt document_kind must be invoice or quotation "
                        "(index %(index)s).",
                        index=index,
                    )
                )
            if kind in seen_kinds:
                raise UserError(
                    _(
                        "Duplicate receipt document_kind in the same call "
                        "is not allowed."
                    )
                )
            seen_kinds.add(kind)
            values_raw = raw.get("values")
            if not isinstance(values_raw, list) or not values_raw:
                raise UserError(
                    _(
                        "Each receipt requires a non-empty values list "
                        "(index %(index)s).",
                        index=index,
                    )
                )
            values, funded_total = self._collection_parse_receipt_values(
                values_raw,
                amounts_by_doc,
                seen_payment_kind,
                kind,
                currency,
            )
            for value in values:
                document_id = value["document_id"]
                value_sums[document_id] = (
                    value_sums.get(document_id, 0.0) + value["amount"]
                )
            applications_raw = raw.get("applications")
            if applications_raw in (None, False):
                applications_raw = []
            if not isinstance(applications_raw, list):
                raise UserError(
                    _(
                        "Receipt applications must be a list (index %(index)s).",
                        index=index,
                    )
                )
            applications, applied_total = self._collection_parse_receipt_applications(
                applications_raw, seen_ext_global, currency
            )
            if currency.compare_amounts(applied_total, funded_total) > 0:
                raise UserError(
                    _(
                        "Receipt applications cannot exceed funded values "
                        "(index %(index)s).",
                        index=index,
                    )
                )
            receipt_rows.append(
                {
                    "document_kind": kind,
                    "values": values,
                    "applications": applications,
                }
            )
        for document_id, expected in amounts_by_doc.items():
            actual = value_sums.get(document_id, 0.0)
            if currency.compare_amounts(actual, expected) != 0:
                raise UserError(
                    _(
                        "Receipt values must equal each payment's seller_confirmed "
                        "amount."
                    )
                )
        return receipt_rows

    @api.model
    @api.private
    def _collection_parse_receipt_values(
        self,
        values_raw: list[Any],
        amounts_by_doc: dict[str, float],
        seen_payment_kind: set[tuple[str, str]],
        kind: str,
        currency,
    ) -> tuple[list[dict[str, Any]], float]:
        """Validate one receipt's values; amounts must be > 0."""
        values: list[dict[str, Any]] = []
        seen_docs: set[str] = set()
        funded_total = 0.0
        for value_index, raw in enumerate(values_raw):
            if not isinstance(raw, dict):
                raise UserError(
                    _(
                        "Receipt value at index %(index)s must be an object.",
                        index=value_index,
                    )
                )
            _collection_reject_unknown_keys(
                raw,
                _RECEIPT_VALUE_KEYS,
                _("Receipt value at index %(index)s", index=value_index),
            )
            document_id = raw.get("document_id")
            if not isinstance(document_id, str) or not document_id.strip():
                raise UserError(
                    _(
                        "Each receipt value requires a non-empty document_id "
                        "(index %(index)s).",
                        index=value_index,
                    )
                )
            document_id = document_id.strip()
            if document_id not in amounts_by_doc:
                raise UserError(
                    _(
                        "Receipt value document_id must match a payment in the "
                        "same call (index %(index)s).",
                        index=value_index,
                    )
                )
            if document_id in seen_docs:
                raise UserError(
                    _(
                        "Duplicate document_id in the same receipt values is not "
                        "allowed."
                    )
                )
            seen_docs.add(document_id)
            payment_kind = (document_id, kind)
            if payment_kind in seen_payment_kind:
                raise UserError(
                    _("Duplicate split for the same payment and document kind.")
                )
            seen_payment_kind.add(payment_kind)
            try:
                amount = _collection_normalize_amount(raw.get("amount"))
            except ValueError as err:
                raise UserError(
                    _(
                        "Receipt value amount must be greater than zero "
                        "(index %(index)s).",
                        index=value_index,
                    )
                ) from err
            if currency.compare_amounts(amount, 0.0) <= 0:
                raise UserError(
                    _(
                        "Receipt value amount must be greater than zero "
                        "(index %(index)s).",
                        index=value_index,
                    )
                )
            values.append({"document_id": document_id, "amount": amount})
            funded_total += amount
        return values, funded_total

    @api.model
    @api.private
    def _collection_parse_receipt_applications(
        self,
        applications_raw: list[Any],
        seen_ext_global: set[str],
        currency,
    ) -> tuple[list[dict[str, Any]], float]:
        """Validate applications; empty list means on account."""
        applications: list[dict[str, Any]] = []
        seen_ext: set[str] = set()
        applied_total = 0.0
        for app_index, raw in enumerate(applications_raw):
            if not isinstance(raw, dict):
                raise UserError(
                    _(
                        "Receipt application at index %(index)s must be an object.",
                        index=app_index,
                    )
                )
            _collection_reject_unknown_keys(
                raw,
                _RECEIPT_APPLICATION_KEYS,
                _("Receipt application at index %(index)s", index=app_index),
            )
            external_id = raw.get("external_document_id")
            if not isinstance(external_id, str) or not external_id.strip():
                raise UserError(
                    _(
                        "Each application requires a non-empty "
                        "external_document_id (index %(index)s).",
                        index=app_index,
                    )
                )
            external_id = external_id.strip()
            if external_id in seen_ext:
                raise UserError(
                    _(
                        "Duplicate external_document_id in the same receipt "
                        "applications is not allowed."
                    )
                )
            seen_ext.add(external_id)
            if external_id in seen_ext_global:
                raise UserError(
                    _("Duplicate external_document_id across receipts is not allowed.")
                )
            seen_ext_global.add(external_id)
            try:
                balance_seen = _collection_normalize_amount(raw.get("balance_seen"))
                amount_applied = _collection_normalize_amount(raw.get("amount_applied"))
            except ValueError as err:
                raise UserError(
                    _(
                        "Application balance_seen and amount_applied must be "
                        "greater than zero (index %(index)s).",
                        index=app_index,
                    )
                ) from err
            if currency.compare_amounts(balance_seen, 0.0) <= 0:
                raise UserError(
                    _(
                        "Application balance_seen must be greater than zero "
                        "(index %(index)s).",
                        index=app_index,
                    )
                )
            if currency.compare_amounts(amount_applied, 0.0) <= 0:
                raise UserError(
                    _(
                        "Application amount_applied must be greater than zero "
                        "(index %(index)s).",
                        index=app_index,
                    )
                )
            if currency.compare_amounts(amount_applied, balance_seen) > 0:
                raise UserError(
                    _(
                        "Application amount_applied cannot exceed balance_seen "
                        "(index %(index)s).",
                        index=app_index,
                    )
                )
            item: dict[str, Any] = {
                "external_document_id": external_id,
                "balance_seen": balance_seen,
                "amount_applied": amount_applied,
            }
            number = raw.get("number")
            if isinstance(number, str) and number.strip():
                item["number"] = number.strip()
            applications.append(item)
            applied_total += amount_applied
        return applications, applied_total

    @api.model
    @api.private
    def _collection_flatten_receipt_applications(
        self, receipt_rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Flatten receipt applications into allocation line snapshots."""
        invoice_rows: list[dict[str, Any]] = []
        for receipt in receipt_rows:
            kind = receipt["document_kind"]
            for application in receipt["applications"]:
                invoice_rows.append(
                    {
                        "external_invoice_id": application["external_document_id"],
                        "amount_applied": application["amount_applied"],
                        "document_kind": kind,
                        "balance_seen": application["balance_seen"],
                    }
                )
        return invoice_rows

    @api.model
    @api.private
    def _collection_allocation_conflict_error(self) -> UserError:
        """Return a generic request_id conflict UserError (no id or name)."""
        return UserError(_("Allocation request conflict could not be resolved."))

    @api.model
    @api.private
    def _collection_allocation_by_request_id(self, request_id: str):
        """Return the revision matching ``request_id``, if visible."""
        return self.env["collection.allocation.revision"].search(
            [("request_id", "=", request_id)], limit=1
        )

    @api.model
    @api.private
    def _collection_allocation_classify_request(
        self,
        request_id: str,
        document_ids: list[str],
        seller,
        receipt_rows: list[dict[str, Any]],
        identification: str,
    ):
        """Return the replay payload, raise the generic conflict, or None if new.

        A request_id replays only for the seller that wrote it and only with
        the same content: the same voucher set and receipts (the revision's
        content hash) for the same customer. Anything else is the generic
        conflict, so a request_id never reveals another seller's allocation.
        """
        revision = self._collection_allocation_by_request_id(request_id)
        if not revision:
            return None
        allocation = revision.allocation_id
        if (
            revision.company_id != self.env.company
            or allocation.sheet_id.seller_id != seller
        ):
            raise self._collection_allocation_conflict_error()
        vouchers = self._collection_vouchers_by_document_ids(document_ids)
        if (
            len(vouchers) != len(document_ids)
            or revision.content_hash
            != self._collection_allocation_content_hash(vouchers, receipt_rows)
            or not self._collection_identification_names(
                identification, allocation.partner_id
            )
        ):
            raise self._collection_allocation_conflict_error()
        return self._collection_allocation_payload(allocation, revision, document_ids)

    @api.model
    @api.private
    def _collection_identification_names(self, identification: str, partner) -> bool:
        """Return whether a customer binding maps ``identification`` to ``partner``."""
        return bool(
            self.env["collection.connector.customer.binding"].search_count(
                [
                    ("partner_id", "=", partner.id),
                    ("identification", "=", identification),
                ],
                limit=1,
            )
        )

    @api.model
    @api.private
    def _collection_allocation_payload(
        self, allocation, revision, document_ids: list[str]
    ) -> dict[str, Any]:
        """Build the MCP allocation response with sheet_id and ordered vouchers."""
        found = self._collection_vouchers_by_document_ids(document_ids)
        voucher_payload = self._collection_vouchers_payload(found, document_ids)
        return {
            "sheet_id": allocation.sheet_id.id,
            "vouchers": voucher_payload["vouchers"],
            "allocation": {
                "id": allocation.id,
                "name": allocation.name,
                "state": allocation.state,
                "revision": int(revision.revision),
                "total_vouchers": revision.total_vouchers,
                "total_applied": revision.total_applied,
                "residual": revision.residual,
            },
        }

    @api.model
    @api.private
    def _collection_allocation_content_hash(
        self, vouchers, receipt_rows: list[dict[str, Any]]
    ) -> str:
        """SHA-256 of vouchers plus receipt values, applications, and kinds."""
        receipts_payload = []
        for row in sorted(receipt_rows, key=lambda item: str(item["document_kind"])):
            receipts_payload.append(
                {
                    "document_kind": str(row["document_kind"]),
                    "values": sorted(
                        [
                            [
                                str(value["document_id"]),
                                f"{float(value['amount']):.6f}",
                            ]
                            for value in row["values"]
                        ]
                    ),
                    "applications": sorted(
                        [
                            [
                                str(application["external_document_id"]),
                                f"{float(application['amount_applied']):.6f}",
                                f"{float(application['balance_seen']):.6f}",
                            ]
                            for application in row["applications"]
                        ]
                    ),
                }
            )
        payload = {
            "vouchers": sorted(vouchers.ids),
            "receipts": receipts_payload,
        }
        encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        return hashlib.sha256(encoded.encode()).hexdigest()

    @api.model
    @api.private
    def _collection_lock_allocation_pair(self, sheet_id: int, partner_id: int) -> None:
        """Advisory lock the (sheet, partner) pair for concurrent creates."""
        self.env.cr.execute(
            SQL(
                "SELECT pg_advisory_xact_lock(hashtext(%s || %s), %s)",
                "collection.allocation.",
                str(int(sheet_id)),
                int(partner_id),
            )
        )

    @api.model
    @api.private
    def _collection_lock_allocation_row(self, allocation) -> None:
        """FOR UPDATE the allocation header before computing the next revision."""
        self.env.cr.execute(
            """
            SELECT id FROM collection_allocation
            WHERE id = %s
            FOR UPDATE
            """,
            [allocation.id],
        )
        allocation.invalidate_recordset()

    @api.model
    @api.private
    def _collection_allocation_vouchers(self, document_ids: list[str], seller):
        """Load and gate vouchers for the current company, seller, and sheet."""
        Voucher = self.env["collection.voucher"]
        found = Voucher.search([("document_id", "in", document_ids)])
        if len(found) != len(document_ids):
            raise UserError(_("One or more payment documents were not found."))
        by_doc = {voucher.document_id: voucher for voucher in found}
        vouchers = Voucher.browse([by_doc[doc_id].id for doc_id in document_ids])
        currency = self.env.company.currency_id
        if any(voucher.company_id != self.env.company for voucher in vouchers):
            raise UserError(_("Vouchers must belong to the current company."))
        for voucher in vouchers:
            amount = voucher.amount
            if amount in (None, False) or currency.compare_amounts(amount, 0.0) <= 0:
                raise UserError(
                    _("Each voucher must have an amount greater than zero.")
                )
        if len(vouchers.partner_id) != 1:
            raise UserError(_("Vouchers must share a single customer."))
        if len(vouchers.seller_id) != 1 or vouchers.seller_id != seller:
            raise UserError(_("Vouchers must belong to the requesting seller."))
        if not vouchers.sheet_id or len(vouchers.sheet_id) != 1:
            raise UserError(_("Vouchers must belong to a single collection sheet."))
        sheet = vouchers.sheet_id
        if (
            sheet.state not in SELLER_SHEET_STATES
            or sheet.company_id != self.env.company
        ):
            raise UserError(
                _("The collection sheet must be open in the current company.")
            )
        return vouchers, sheet

    @api.model
    @api.private
    def _collection_allocation_bound_partner(self, identification: str, vouchers):
        """Assert identification resolves to the voucher partner; never sudo."""
        connector = self.env.company._collection_active_connector()
        binding = self.env["collection.connector.customer.binding"].search(
            [
                ("connector_id", "=", connector.id),
                ("identification", "=", identification),
            ],
            limit=1,
        )
        if not binding:
            raise UserError(_("The requested customer is not available."))
        if binding.partner_id != vouchers.partner_id:
            raise UserError(_("The customer does not match the selected vouchers."))
        return binding.partner_id, connector

    @api.model
    @api.private
    def _collection_reserved_amounts(
        self,
        external_invoice_ids: list[str],
        exclude_allocation_id: int | bool = False,
        connector=None,
    ) -> dict[str, float]:
        """Applied amounts the ERP balances do not show yet, per external invoice.

        Receipts are typed into the ERP by hand and a manager marks the whole
        sheet "Entered in the ERP". An allocation's applied amount is
        subtracted while its sheet is not cancelled AND (the sheet is not
        marked OR the ``connector`` has not yet taken ERP entries in since the
        mark, i.e. no successful refresh STARTED after it). Cancelled sheets
        never reserve. Without a connector, nothing marked is released.
        Optionally exclude the destination allocation (amendments).
        """
        invoice_ids = [eid for eid in external_invoice_ids if eid]
        if not invoice_ids:
            return {}
        domain = [
            ("external_invoice_id", "in", invoice_ids),
            ("company_id", "=", self.env.company.id),
            ("allocation_id.state", "in", ("draft", "confirmed")),
            ("sheet_id.state", "!=", "cancelled"),
        ]
        reflected_since = (
            connector._collection_erp_reflected_since() if connector else False
        )
        if reflected_since:
            domain += [
                "|",
                ("sheet_id.erp_entered_date", "=", False),
                ("sheet_id.erp_entered_date", ">=", reflected_since),
            ]
        if exclude_allocation_id:
            domain.append(("allocation_id", "!=", exclude_allocation_id))
        grouped = self.env["collection.allocation.line"]._read_group(
            domain,
            groupby=["external_invoice_id"],
            aggregates=["amount_applied:sum"],
        )
        return {
            external_id: float(reserved or 0.0)
            for external_id, reserved in grouped
            if external_id
        }

    @api.model
    @api.private
    def _collection_allocation_revalidate(
        self,
        connector,
        seller,
        identification: str,
        invoice_rows: list[dict[str, Any]],
        destination,
        currency,
    ) -> list[dict[str, Any]]:
        """Revalidate applied rows, then expand to every outstanding ERP invoice."""
        debt = connector.get_customer_debt(seller.id, identification)
        fresh_invoices = {
            row["external_invoice_id"]: row for row in debt.get("invoices") or []
        }
        applied_by_id = {
            row["external_invoice_id"]: row["amount_applied"] for row in invoice_rows
        }
        payload_kinds = {
            row["external_invoice_id"]: row["document_kind"]
            for row in invoice_rows
            if "document_kind" in row
        }
        balance_seen_by_id = {
            row["external_invoice_id"]: row["balance_seen"]
            for row in invoice_rows
            if "balance_seen" in row
        }
        stored_kinds = {}
        if destination:
            stored_kinds = {
                line.external_invoice_id: line.document_kind
                for line in destination.line_ids
            }
        dest_id = destination.id if destination else False
        for external_id, applied in applied_by_id.items():
            if (
                currency.compare_amounts(applied, 0.0) > 0
                and external_id not in fresh_invoices
            ):
                raise UserError(_("An invoice is no longer outstanding."))
            if external_id in balance_seen_by_id and external_id in fresh_invoices:
                fresh_balance = fresh_invoices[external_id].get("balance") or 0.0
                if currency.compare_amounts(
                    balance_seen_by_id[external_id], fresh_balance
                ):
                    raise UserError(_("An invoice balance has changed."))
        reserved = self._collection_reserved_amounts(
            list(fresh_invoices),
            exclude_allocation_id=dest_id,
            connector=connector,
        )
        line_vals: list[dict[str, Any]] = []
        for external_id, fresh in fresh_invoices.items():
            applied = applied_by_id.get(external_id, 0.0)
            elsewhere = reserved.get(external_id, 0.0)
            available = (fresh.get("balance") or 0.0) - elsewhere
            if currency.compare_amounts(applied, available) > 0:
                raise UserError(_("Applied amount exceeds available invoice balance."))
            if external_id in payload_kinds:
                kind = payload_kinds[external_id]
            else:
                kind = stored_kinds.get(external_id, "invoice")
            line_vals.append(
                {
                    "external_invoice_id": external_id,
                    "invoice_number": fresh.get("number") or False,
                    "issue_date": fresh.get("issue_date") or False,
                    "due_date": fresh.get("due_date") or False,
                    "invoice_amount": fresh.get("amount") or 0.0,
                    "invoice_balance": fresh.get("balance") or 0.0,
                    "invoice_state": fresh.get("state") or False,
                    "amount_applied": applied,
                    "document_kind": kind,
                }
            )
        return line_vals

    @api.model
    @api.private
    def _collection_allocation_insert_revision(
        self, allocation, request_id: str, content_hash: str
    ):
        """Append an immutable revision snapshot for the current header."""
        with privileged("collection_allocation_revision"):
            return self.env["collection.allocation.revision"].create(
                {
                    "allocation_id": allocation.id,
                    "revision": allocation.revision,
                    "request_id": request_id,
                    "content_hash": content_hash,
                    "confirmed_by": self.env.user.id,
                    "confirmed_at": fields.Datetime.now(),
                    "total_vouchers": allocation.total_vouchers,
                    "total_applied": allocation.total_applied,
                    "total_debt": allocation.total_debt,
                    "total_invoices": allocation.total_invoices,
                    "total_quotations": allocation.total_quotations,
                    "residual": allocation.residual,
                }
            )

    @api.model
    @api.private
    def _collection_allocation_write(
        self,
        seller,
        identification: str,
        request_id: str,
        document_ids: list[str],
        receipt_rows: list[dict[str, Any]],
        payments: list[dict[str, Any]],
        payment_vals_list: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create or reuse vouchers, revalidate ERP, then persist allocation."""
        existing_docs = self._collection_vouchers_by_document_ids(document_ids)
        classified = self._collection_classify_visible(
            existing_docs, document_ids, seller, payment_vals_list
        )
        sidecars: list[tuple[str, bytes] | None] | None = None
        provenances: list[dict[str, Any] | None] | None = None
        new_vals_list: list[dict[str, Any]] = []
        if classified is None:
            # The seller's own existing vouchers are reused (an amend lists them);
            # only the payments whose document_id is new are created.
            reused = set(existing_docs.mapped("document_id"))
            new_indexes = [
                index
                for index, vals in enumerate(payment_vals_list)
                if vals["document_id"] not in reused
            ]
            new_payments = [payments[index] for index in new_indexes]
            new_vals_list = [payment_vals_list[index] for index in new_indexes]
            sidecars = self._collection_parse_payment_attachments(new_payments)
            provenances = self._collection_parse_payment_provenance(
                new_payments, new_vals_list
            )

        with self.env.cr.savepoint():
            if classified is None:
                try:
                    self._collection_create_vouchers(
                        new_vals_list,
                        seller.id,
                        sidecars or [],
                        provenances or [],
                        identification,
                    )
                except UniqueViolation:
                    self.env.invalidate_all()
                    replayed = self._collection_replay_existing(
                        document_ids, seller, payment_vals_list
                    )
                    if replayed is None:
                        raise self._collection_document_conflict_error() from None
            vouchers, sheet = self._collection_allocation_vouchers(document_ids, seller)
            partner, connector = self._collection_allocation_bound_partner(
                identification, vouchers
            )
            Allocation = self.env["collection.allocation"]
            existing = Allocation.search(
                [("sheet_id", "=", sheet.id), ("partner_id", "=", partner.id)],
                limit=1,
            )
            if not existing:
                self._collection_lock_allocation_pair(sheet.id, partner.id)
                existing = Allocation.search(
                    [("sheet_id", "=", sheet.id), ("partner_id", "=", partner.id)],
                    limit=1,
                )
            if existing:
                if existing.state != "draft":
                    raise UserError(_("Only draft allocations can be amended."))
                self._collection_lock_allocation_row(existing)
                current_ids = set(existing.voucher_ids.ids)
                if not current_ids <= set(vouchers.ids):
                    raise UserError(
                        _(
                            "Amended vouchers must include all previously allocated "
                            "vouchers."
                        )
                    )
            content_hash = self._collection_allocation_content_hash(
                vouchers, receipt_rows
            )
            if existing:
                last = existing.revision_ids.sorted("revision")[-1:]
                if last and last.content_hash == content_hash:
                    return self._collection_allocation_payload(
                        existing, last, document_ids
                    )

            currency = self.env.company.currency_id
            invoice_rows = self._collection_flatten_receipt_applications(receipt_rows)
            line_vals = self._collection_allocation_revalidate(
                connector, seller, identification, invoice_rows, existing, currency
            )
            line_commands = [Command.create(vals) for vals in line_vals]
            if existing:
                allocation = self._collection_allocation_persist_amend(
                    existing,
                    vouchers,
                    line_commands,
                )
            else:
                allocation = Allocation.create(
                    {
                        "sheet_id": sheet.id,
                        "partner_id": partner.id,
                        "revision": 1,
                        "voucher_ids": [Command.set(vouchers.ids)],
                        "line_ids": line_commands,
                    }
                )
            revision = self._collection_allocation_insert_revision(
                allocation, request_id, content_hash
            )
            self._collection_allocation_rebuild_receipts(
                allocation, vouchers, receipt_rows
            )
        return self._collection_allocation_payload(allocation, revision, document_ids)

    @api.model
    @api.private
    def _collection_allocation_persist_amend(
        self,
        allocation,
        vouchers,
        line_commands,
    ):
        """Replace draft membership lines and voucher set, then bump revision."""
        # The receipts are rebuilt from the new values afterwards; dropping them
        # first keeps the old values from capping the new applications.
        allocation.write({"receipt_ids": [Command.clear()]})
        # Command.clear() unlinks lines first and flushes computes before creates.
        allocation.write(
            {
                "revision": allocation.revision + 1,
                "voucher_ids": [Command.set(vouchers.ids)],
                "line_ids": [Command.clear(), *line_commands],
            }
        )
        return allocation

    @api.model
    @api.private
    def _collection_allocation_rebuild_receipts(
        self,
        allocation,
        vouchers,
        receipt_rows: list[dict[str, Any]],
    ) -> None:
        """Rebuild draft receipts and values from explicit receipt values."""
        allocation.write({"receipt_ids": [Command.clear()]})
        by_doc = {voucher.document_id: voucher for voucher in vouchers}
        Receipt = self.env["collection.receipt"]
        Value = self.env["collection.receipt.value"]
        for row in receipt_rows:
            pairs = []
            for value in row["values"]:
                voucher = by_doc.get(value["document_id"])
                if voucher is None:
                    continue
                pairs.append((voucher, float(value["amount"])))
            if not pairs:
                continue
            receipt = Receipt.create(
                {
                    "allocation_id": allocation.id,
                    "document_kind": row["document_kind"],
                }
            )
            Value.create(
                [
                    {
                        "receipt_id": receipt.id,
                        "voucher_id": voucher.id,
                        "amount": amount,
                    }
                    for voucher, amount in pairs
                ]
            )
