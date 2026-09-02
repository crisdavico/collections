# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import annotations

import hashlib
import json
from typing import Any

from psycopg2.errors import UniqueViolation

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.fields import Command
from odoo.tools import SQL

from odoo.addons.collection.tools.collection_voucher import _PAYMENT_SCHEMA
from odoo.addons.muk_mcp.core.tool import mcp_tool

_RESIDUAL_REASONS = ("on_account", "advance", "pending_invoice", "rounding")

_INVOICE_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "external_invoice_id": {
            "type": "string",
            "minLength": 1,
            "description": "External ERP invoice id.",
        },
        "number": {
            "type": "string",
            "nullable": True,
            "description": "Invoice number snapshot.",
        },
        "issue_date": {
            "type": "string",
            "nullable": True,
            "description": "Invoice issue date snapshot.",
        },
        "due_date": {
            "type": "string",
            "nullable": True,
            "description": "Invoice due date snapshot.",
        },
        "amount": {
            "type": "number",
            "nullable": True,
            "description": "Invoice amount snapshot.",
        },
        "balance": {
            "type": "number",
            "nullable": True,
            "description": "Invoice balance snapshot.",
        },
        "state": {
            "type": "string",
            "nullable": True,
            "description": "Invoice state snapshot.",
        },
        "amount_applied": {
            "type": "number",
            "exclusiveMinimum": 0,
            "description": "Amount applied to this invoice.",
        },
    },
    "required": ["external_invoice_id", "amount_applied"],
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
        "invoices": {
            "type": "array",
            "items": _INVOICE_ITEM_SCHEMA,
            "description": "Invoice applications; empty means all on account.",
        },
        "total_debt": {
            "type": "number",
            "nullable": True,
            "description": "Informational caller total; ignored in favor of fresh ERP.",
        },
        "residual_reason": {
            "type": "string",
            "nullable": True,
            "enum": list(_RESIDUAL_REASONS),
            "description": "Required when residual is greater than zero.",
        },
    },
    "required": [
        "seller_id",
        "customer_identification",
        "request_id",
        "payments",
        "invoices",
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
            "while draft. Returns {sheet_id, vouchers, allocation}. Internal "
            "users only."
        ),
        input_schema=_CREATE_COLLECTION_ALLOCATION_SCHEMA,
        category="write",
        registry="mcp",
    )
    def create_collection_allocation(
        self,
        seller_id: int,
        customer_identification: str,
        request_id: str,
        payments: list[dict[str, Any]],
        invoices: list[dict[str, Any]],
        total_debt: float | None = None,
        residual_reason: str | None = None,
    ) -> dict[str, Any]:
        """Validate, persist inline payments, revalidate ERP, then allocate.

        :raise AccessError: when the caller is not an internal user.
        :raise UserError: when input, seller, records, or revalidation fail.
        """
        del total_debt  # Caller total is informational; persist fresh ERP snapshot.
        if not self.env.user.has_group("base.group_user"):
            raise AccessError(_("Only internal users can create allocations."))
        (
            document_ids,
            invoice_rows,
            request_key,
            identification,
            reason,
            payment_vals_list,
        ) = self._collection_parse_allocation_form(
            payments, invoices, request_id, customer_identification, residual_reason
        )
        seller = self._collection_require_internal_seller(seller_id)
        replayed = self._collection_allocation_classify_request(
            request_key, document_ids
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
                invoice_rows,
                reason,
                payments,
                payment_vals_list,
            )
        except UniqueViolation:
            self.env.invalidate_all()
            replayed = self._collection_allocation_classify_request(
                request_key, document_ids
            )
            if replayed is not None:
                return replayed
            raise self._collection_allocation_conflict_error() from None

    @api.model
    @api.private
    def _collection_parse_allocation_form(
        self,
        payments: Any,
        invoices: Any,
        request_id: Any,
        customer_identification: Any,
        residual_reason: Any,
    ) -> tuple[
        list[str],
        list[dict[str, Any]],
        str,
        str,
        str | bool,
        list[dict[str, Any]],
    ]:
        """Validate MCP form fields in Python (do not trust schema minItems)."""
        if not isinstance(request_id, str) or not request_id.strip():
            raise UserError(_("request_id is required."))
        if (
            not isinstance(customer_identification, str)
            or not customer_identification.strip()
        ):
            raise UserError(_("customer_identification is required."))
        identification = customer_identification.strip()
        if not isinstance(payments, list) or not payments:
            raise UserError(_("payments must be a non-empty list."))
        payment_vals_list, _identifications = self._collection_parse_payment_vals(
            payments, identification
        )
        document_ids = [vals["document_id"] for vals in payment_vals_list]
        if len(document_ids) != len(set(document_ids)):
            raise UserError(_("Duplicate document_id in the same call is not allowed."))
        if not isinstance(invoices, list):
            raise UserError(_("invoices must be a list."))
        invoice_rows = self._collection_parse_allocation_invoices(invoices)
        if residual_reason in (None, False, ""):
            reason: str | bool = False
        elif residual_reason not in _RESIDUAL_REASONS:
            raise UserError(_("Invalid residual_reason."))
        else:
            reason = residual_reason
        return (
            document_ids,
            invoice_rows,
            request_id.strip(),
            identification,
            reason,
            payment_vals_list,
        )

    @api.model
    @api.private
    def _collection_parse_allocation_invoices(
        self, invoices: Any
    ) -> list[dict[str, Any]]:
        """Validate invoice application rows."""
        if not isinstance(invoices, list):
            raise UserError(_("invoices must be a list."))
        invoice_rows: list[dict[str, Any]] = []
        seen_invoices: set[str] = set()
        for index, raw in enumerate(invoices):
            if not isinstance(raw, dict):
                raise UserError(
                    _("Invoice at index %(index)s must be an object.", index=index)
                )
            external_id = raw.get("external_invoice_id")
            if not isinstance(external_id, str) or not external_id.strip():
                raise UserError(
                    _(
                        "Each invoice requires a non-empty external_invoice_id "
                        "(index %(index)s).",
                        index=index,
                    )
                )
            external_id = external_id.strip()
            if external_id in seen_invoices:
                raise UserError(
                    _("Duplicate external_invoice_id in the same call is not allowed.")
                )
            seen_invoices.add(external_id)
            applied = raw.get("amount_applied")
            try:
                applied_amount = float(applied)
            except (TypeError, ValueError) as err:
                raise UserError(
                    _(
                        "Invoice amount_applied must be greater than zero "
                        "(index %(index)s).",
                        index=index,
                    )
                ) from err
            if applied_amount <= 0:
                raise UserError(
                    _(
                        "Invoice amount_applied must be greater than zero "
                        "(index %(index)s).",
                        index=index,
                    )
                )
            invoice_rows.append(
                {
                    "external_invoice_id": external_id,
                    "amount_applied": applied_amount,
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
        self, request_id: str, document_ids: list[str]
    ):
        """Return replay payload, raise on other-company, or None if new."""
        revision = self._collection_allocation_by_request_id(request_id)
        if not revision:
            return None
        if revision.company_id != self.env.company:
            raise self._collection_allocation_conflict_error()
        return self._collection_allocation_payload(
            revision.allocation_id, revision, document_ids
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
        self, vouchers, invoice_rows, residual_reason
    ) -> str:
        """SHA-256 of sorted voucher ids, invoice pairs, and residual_reason."""
        payload = {
            "vouchers": sorted(vouchers.ids),
            "invoices": sorted(
                [
                    [
                        str(row["external_invoice_id"]),
                        f"{float(row['amount_applied']):.6f}",
                    ]
                    for row in invoice_rows
                ]
            ),
            "residual_reason": residual_reason or None,
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
            if voucher.state == "rejected":
                raise UserError(_("Rejected vouchers cannot be allocated."))
        if len(vouchers.partner_id) != 1:
            raise UserError(_("Vouchers must share a single customer."))
        if len(vouchers.seller_id) != 1 or vouchers.seller_id != seller:
            raise UserError(_("Vouchers must belong to the requesting seller."))
        if not vouchers.sheet_id or len(vouchers.sheet_id) != 1:
            raise UserError(_("Vouchers must belong to a single collection sheet."))
        sheet = vouchers.sheet_id
        if sheet.state != "open" or sheet.company_id != self.env.company:
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
    def _collection_allocation_revalidate(
        self,
        connector,
        seller,
        identification: str,
        invoice_rows: list[dict[str, Any]],
        destination,
        currency,
    ) -> tuple[float, list[dict[str, Any]]]:
        """Revalidate invoices against fresh ERP debt minus other applications."""
        debt = connector.get_customer_debt(seller.id, identification)
        fresh_invoices = {
            row["external_invoice_id"]: row for row in debt.get("invoices") or []
        }
        Line = self.env["collection.allocation.line"]
        dest_id = destination.id if destination else False
        line_vals: list[dict[str, Any]] = []
        for row in invoice_rows:
            external_id = row["external_invoice_id"]
            applied = row["amount_applied"]
            fresh = fresh_invoices.get(external_id)
            if not fresh:
                raise UserError(_("An invoice is no longer outstanding."))
            domain = [
                ("external_invoice_id", "=", external_id),
                ("company_id", "=", self.env.company.id),
                ("allocation_id.state", "in", ("draft", "confirmed")),
            ]
            if dest_id:
                domain.append(("allocation_id", "!=", dest_id))
            elsewhere = sum(Line.search(domain).mapped("amount_applied"))
            available = (fresh.get("balance") or 0.0) - elsewhere
            if currency.compare_amounts(applied, available) > 0:
                raise UserError(_("Applied amount exceeds available invoice balance."))
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
                }
            )
        summary = debt.get("summary") or {}
        return float(summary.get("total_balance") or 0.0), line_vals

    @api.model
    @api.private
    def _collection_allocation_check_residual(
        self, vouchers, invoice_rows, residual_reason, currency
    ) -> None:
        """Reject a negative residual or a missing reason when residual > 0."""
        total_vouchers = sum(voucher.amount or 0.0 for voucher in vouchers)
        total_applied = sum(row["amount_applied"] for row in invoice_rows)
        residual = total_vouchers - total_applied
        if currency.compare_amounts(residual, 0.0) < 0:
            raise UserError(_("Residual cannot be negative."))
        if currency.compare_amounts(residual, 0.0) > 0 and not residual_reason:
            raise UserError(
                _("A residual reason is required when the residual is positive.")
            )

    @api.model
    @api.private
    def _collection_allocation_insert_revision(
        self, allocation, request_id: str, content_hash: str
    ):
        """Append an immutable revision snapshot for the current header."""
        return (
            self.env["collection.allocation.revision"]
            .with_context(collection_allocation_revision=True)
            .create(
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
                    "residual": allocation.residual,
                    "residual_reason": allocation.residual_reason,
                }
            )
        )

    @api.model
    @api.private
    def _collection_allocation_write(
        self,
        seller,
        identification: str,
        request_id: str,
        document_ids: list[str],
        invoice_rows: list[dict[str, Any]],
        residual_reason: str | bool,
        payments: list[dict[str, Any]],
        payment_vals_list: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create or reuse vouchers, revalidate ERP, then persist allocation."""
        existing_docs = self._collection_vouchers_by_document_ids(document_ids)
        classified = self._collection_classify_visible(existing_docs, document_ids)
        sidecars: list[tuple[str, bytes] | None] | None = None
        provenances: list[dict[str, Any] | None] | None = None
        if classified is None:
            sidecars = self._collection_parse_payment_attachments(payments)
            provenances = self._collection_parse_payment_provenance(
                payments, payment_vals_list
            )

        with self.env.cr.savepoint():
            if classified is None:
                try:
                    self._collection_create_vouchers(
                        payment_vals_list,
                        seller.id,
                        sidecars or [],
                        provenances or [],
                        [identification] * len(payment_vals_list),
                    )
                except UniqueViolation:
                    self.env.invalidate_all()
                    replayed = self._collection_replay_existing(document_ids)
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
                    vouchers, invoice_rows, residual_reason
                )
                last = existing.revision_ids.sorted("revision")[-1:]
                if last and last.content_hash == content_hash:
                    return self._collection_allocation_payload(
                        existing, last, document_ids
                    )
            else:
                content_hash = self._collection_allocation_content_hash(
                    vouchers, invoice_rows, residual_reason
                )

            currency = self.env.company.currency_id
            fresh_total, line_vals = self._collection_allocation_revalidate(
                connector, seller, identification, invoice_rows, existing, currency
            )
            self._collection_allocation_check_residual(
                vouchers, invoice_rows, residual_reason, currency
            )
            line_commands = [Command.create(vals) for vals in line_vals]
            if existing:
                allocation = self._collection_allocation_persist_amend(
                    existing,
                    vouchers,
                    line_commands,
                    residual_reason,
                    fresh_total,
                )
            else:
                allocation = Allocation.create(
                    {
                        "sheet_id": sheet.id,
                        "partner_id": partner.id,
                        "residual_reason": residual_reason,
                        "total_debt": fresh_total,
                        "revision": 1,
                        "voucher_ids": [Command.set(vouchers.ids)],
                        "line_ids": line_commands,
                    }
                )
            revision = self._collection_allocation_insert_revision(
                allocation, request_id, content_hash
            )
        return self._collection_allocation_payload(allocation, revision, document_ids)

    @api.model
    @api.private
    def _collection_allocation_persist_amend(
        self,
        allocation,
        vouchers,
        line_commands,
        residual_reason,
        fresh_total,
    ):
        """Replace draft membership while residual stays valid mid-write."""
        # Command.clear() unlinks lines first and flushes computes before creates.
        placeholder = residual_reason or allocation.residual_reason or "on_account"
        allocation.write(
            {
                "revision": allocation.revision + 1,
                "residual_reason": placeholder,
                "total_debt": fresh_total,
                "voucher_ids": [Command.set(vouchers.ids)],
                "line_ids": [Command.clear(), *line_commands],
            }
        )
        if allocation.residual_reason != residual_reason:
            allocation.write({"residual_reason": residual_reason})
        return allocation
