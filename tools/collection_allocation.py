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
            "minimum": 0,
            "description": "Amount applied to this invoice (zero allowed).",
        },
        "document_kind": {
            "type": "string",
            "enum": ["invoice", "quotation"],
            "description": "Invoice or quotation; omitted defaults to invoice.",
        },
    },
    "required": ["external_invoice_id", "amount_applied"],
}

_DOCUMENT_KINDS = ("invoice", "quotation")

_SPLIT_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "document_id": {
            "type": "string",
            "minLength": 1,
            "description": "Payment document_id from payments[] in this call.",
        },
        "document_kind": {
            "type": "string",
            "enum": list(_DOCUMENT_KINDS),
            "description": "Receipt kind this split amount belongs to.",
        },
        "amount": {
            "type": "number",
            "description": "Split amount greater than zero.",
        },
    },
    "required": ["document_id", "document_kind", "amount"],
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
            "description": "Optional; enum is validated then ignored.",
        },
        "splits": {
            "type": "array",
            "items": _SPLIT_ITEM_SCHEMA,
            "description": "Optional voucher splits across receipt kinds.",
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
        splits: list[dict[str, Any]] | None = None,
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
            split_rows,
        ) = self._collection_parse_allocation_form(
            payments,
            invoices,
            request_id,
            customer_identification,
            residual_reason,
            splits,
        )
        del reason  # Enum-validated then ignored; never persisted or hashed.
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
                payments,
                payment_vals_list,
                split_rows,
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
        splits: Any = None,
    ) -> tuple[
        list[str],
        list[dict[str, Any]],
        str,
        str,
        str | bool,
        list[dict[str, Any]],
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
        split_rows = self._collection_parse_allocation_splits(splits, payment_vals_list)
        return (
            document_ids,
            invoice_rows,
            request_id.strip(),
            identification,
            reason,
            payment_vals_list,
            split_rows,
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
                        "Invoice amount_applied must be greater than or equal to zero "
                        "(index %(index)s).",
                        index=index,
                    )
                ) from err
            if applied_amount < 0:
                raise UserError(
                    _(
                        "Invoice amount_applied must be greater than or equal to zero "
                        "(index %(index)s).",
                        index=index,
                    )
                )
            item = {
                "external_invoice_id": external_id,
                "amount_applied": applied_amount,
            }
            raw_kind = raw.get("document_kind")
            if "document_kind" in raw and raw_kind not in (None, False, ""):
                if raw_kind not in _DOCUMENT_KINDS:
                    raise UserError(
                        _(
                            "Invoice document_kind must be invoice or quotation "
                            "(index %(index)s).",
                            index=index,
                        )
                    )
                item["document_kind"] = raw_kind
            invoice_rows.append(item)
        return invoice_rows

    @api.model
    @api.private
    def _collection_parse_allocation_splits(
        self, splits: Any, payment_vals_list: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Validate optional splits; empty/omitted means FIFO compat grouping."""
        if splits in (None, False):
            return []
        if not isinstance(splits, list):
            raise UserError(_("splits must be a list."))
        amounts_by_doc = {
            vals["document_id"]: float(vals["amount"]) for vals in payment_vals_list
        }
        split_rows: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        sums: dict[str, float] = {}
        currency = self.env.company.currency_id
        for index, raw in enumerate(splits):
            if not isinstance(raw, dict):
                raise UserError(
                    _("Split at index %(index)s must be an object.", index=index)
                )
            document_id = raw.get("document_id")
            if not isinstance(document_id, str) or not document_id.strip():
                raise UserError(
                    _(
                        "Each split requires a non-empty document_id "
                        "(index %(index)s).",
                        index=index,
                    )
                )
            document_id = document_id.strip()
            if document_id not in amounts_by_doc:
                raise UserError(
                    _(
                        "Split document_id must match a payment in the same call "
                        "(index %(index)s).",
                        index=index,
                    )
                )
            kind = raw.get("document_kind")
            if kind not in _DOCUMENT_KINDS:
                raise UserError(
                    _(
                        "Split document_kind must be invoice or quotation "
                        "(index %(index)s).",
                        index=index,
                    )
                )
            key = (document_id, kind)
            if key in seen:
                raise UserError(
                    _("Duplicate split for the same payment and document kind.")
                )
            seen.add(key)
            try:
                amount = float(raw.get("amount"))
            except (TypeError, ValueError) as err:
                raise UserError(
                    _(
                        "Split amount must be greater than zero (index %(index)s).",
                        index=index,
                    )
                ) from err
            if currency.compare_amounts(amount, 0.0) <= 0:
                raise UserError(
                    _(
                        "Split amount must be greater than zero (index %(index)s).",
                        index=index,
                    )
                )
            split_rows.append(
                {
                    "document_id": document_id,
                    "document_kind": kind,
                    "amount": amount,
                }
            )
            sums[document_id] = sums.get(document_id, 0.0) + amount
        for document_id, total in sums.items():
            if currency.compare_amounts(total, amounts_by_doc[document_id]) > 0:
                raise UserError(_("Split amounts cannot exceed the payment amount."))
        return split_rows

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
        self, vouchers, invoice_rows, split_rows=None
    ) -> str:
        """SHA-256 of vouchers/invoices; extras only when payload has them."""
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
        }
        invoice_kinds = sorted(
            [
                [str(row["external_invoice_id"]), row["document_kind"]]
                for row in invoice_rows
                if "document_kind" in row
            ]
        )
        if invoice_kinds:
            payload["invoice_kinds"] = invoice_kinds
        split_items = sorted(
            [
                [
                    str(row["document_id"]),
                    str(row["document_kind"]),
                    f"{float(row['amount']):.6f}",
                ]
                for row in (split_rows or [])
            ]
        )
        if split_items:
            payload["splits"] = split_items
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
        stored_kinds = {}
        if destination:
            stored_kinds = {
                line.external_invoice_id: line.document_kind
                for line in destination.line_ids
            }
        Line = self.env["collection.allocation.line"]
        dest_id = destination.id if destination else False
        for external_id, applied in applied_by_id.items():
            if (
                currency.compare_amounts(applied, 0.0) > 0
                and external_id not in fresh_invoices
            ):
                raise UserError(_("An invoice is no longer outstanding."))
        line_vals: list[dict[str, Any]] = []
        for external_id, fresh in fresh_invoices.items():
            applied = applied_by_id.get(external_id, 0.0)
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
                    "total_invoices": allocation.total_invoices,
                    "total_quotations": allocation.total_quotations,
                    "residual": allocation.residual,
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
        payments: list[dict[str, Any]],
        payment_vals_list: list[dict[str, Any]],
        split_rows: list[dict[str, Any]] | None = None,
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
                vouchers, invoice_rows, split_rows
            )
            if existing:
                last = existing.revision_ids.sorted("revision")[-1:]
                if last and last.content_hash == content_hash:
                    return self._collection_allocation_payload(
                        existing, last, document_ids
                    )

            currency = self.env.company.currency_id
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
                allocation, vouchers, invoice_rows, split_rows or []
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
    def _collection_compat_fifo_values(self, vouchers, invoice_rows):
        """Assign applied invoice sum onto vouchers in submit order."""
        currency = self.env.company.currency_id
        remaining = sum(float(row["amount_applied"]) for row in invoice_rows)
        values: list[tuple[Any, float]] = []
        for voucher in vouchers:
            if currency.compare_amounts(remaining, 0.0) <= 0:
                break
            take = min(float(voucher.amount or 0.0), remaining)
            if currency.compare_amounts(take, 0.0) > 0:
                values.append((voucher, take))
                remaining -= take
        return values

    @api.model
    @api.private
    def _collection_allocation_rebuild_receipts(
        self,
        allocation,
        vouchers,
        invoice_rows: list[dict[str, Any]],
        split_rows: list[dict[str, Any]],
    ) -> None:
        """Rebuild draft receipts/values from splits or FIFO compat grouping."""
        allocation.write({"receipt_ids": [Command.clear()]})
        groups: dict[str, list[tuple[Any, float]]] = {}
        if split_rows:
            by_doc = {voucher.document_id: voucher for voucher in vouchers}
            for row in split_rows:
                voucher = by_doc.get(row["document_id"])
                if voucher is None:
                    continue
                groups.setdefault(row["document_kind"], []).append(
                    (voucher, float(row["amount"]))
                )
        elif any(float(row.get("amount_applied") or 0.0) > 0.0 for row in invoice_rows):
            fifo_values = self._collection_compat_fifo_values(vouchers, invoice_rows)
            if fifo_values:
                groups["invoice"] = fifo_values
        Receipt = self.env["collection.receipt"]
        Value = self.env["collection.receipt.value"]
        for kind, pairs in groups.items():
            if not pairs:
                continue
            receipt = Receipt.create(
                {
                    "allocation_id": allocation.id,
                    "document_kind": kind,
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
