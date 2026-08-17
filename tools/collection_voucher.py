# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import annotations

from base64 import b64decode
from typing import Any

from psycopg2.errors import UniqueViolation

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools.mimetypes import guess_mimetype

from odoo.addons.muk_mcp.core.tool import mcp_tool

_PAYMENT_OPTIONAL_FIELDS = (
    "amount",
    "from_account",
    "to_account",
    "voucher_number",
    "voucher_date",
    "check_number",
    "check_bank",
    "check_issue_date",
    "check_payment_date",
    "check_type",
)

_DOCUMENT_TYPES = ("bank_transfer", "check", "cash_deposit", "unsupported")
_CHECK_TYPES = ("common", "deferred")

_ATTACHMENT_NEST_SCHEMA = {
    "type": "object",
    "description": (
        "Optional proof file for this payment. "
        "Required keys when present: name, mimetype, datas."
    ),
    "properties": {
        "name": {
            "type": "string",
            "description": "Attachment filename.",
        },
        "mimetype": {
            "type": "string",
            "description": "Declared MIME type (must match detected content).",
        },
        "datas": {
            "type": "string",
            "description": "Base64-encoded file contents.",
        },
    },
    "required": ["name", "mimetype", "datas"],
}


class CollectionMcpMixin(models.AbstractModel):
    """MuK MCP write tools for collection vouchers."""

    _inherit = "muk_mcp.mixin"

    @api.model
    @mcp_tool(
        name="create_collection_vouchers",
        description=(
            "Create one payment voucher per payment. "
            "Requires customer_identification, seller_id, and a non-empty "
            "payments array. "
            "seller_id must be an internal user (not portal/share). "
            "Each payment must include a non-empty document_id and document_type. "
            "Each payment may include an optional attachment "
            "{name, mimetype, datas}. "
            "Does not accept received_date; registration time is automatic."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "customer_identification": {
                    "type": "string",
                    "description": "Customer identification string for the voucher.",
                },
                "seller_id": {
                    "type": "integer",
                    "description": (
                        "Internal user id of the seller. Required on every call; "
                        "stamped only on all-new create. Ignored on exact replay."
                    ),
                },
                "payments": {
                    "type": "array",
                    "minItems": 1,
                    "description": "Payments to persist as standalone vouchers.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "Unique payment document identifier.",
                            },
                            "document_type": {
                                "type": "string",
                                "enum": list(_DOCUMENT_TYPES),
                                "description": "Payment document type.",
                            },
                            "amount": {
                                "type": "number",
                                "nullable": True,
                                "description": "Payment amount.",
                            },
                            "from_account": {
                                "type": "string",
                                "nullable": True,
                                "description": "Source account.",
                            },
                            "to_account": {
                                "type": "string",
                                "nullable": True,
                                "description": "Destination account.",
                            },
                            "voucher_number": {
                                "type": "string",
                                "nullable": True,
                                "description": "Bank voucher number.",
                            },
                            "voucher_date": {
                                "type": "string",
                                "nullable": True,
                                "description": "Bank voucher date (ISO).",
                            },
                            "check_number": {
                                "type": "string",
                                "nullable": True,
                                "description": "Check number.",
                            },
                            "check_bank": {
                                "type": "string",
                                "nullable": True,
                                "description": "Check bank name.",
                            },
                            "check_issue_date": {
                                "type": "string",
                                "nullable": True,
                                "description": "Check issue date (ISO).",
                            },
                            "check_payment_date": {
                                "type": "string",
                                "nullable": True,
                                "description": "Check payment date (ISO).",
                            },
                            "check_type": {
                                "type": "string",
                                "nullable": True,
                                "enum": list(_CHECK_TYPES),
                                "description": "Check type.",
                            },
                            "attachment": _ATTACHMENT_NEST_SCHEMA,
                        },
                        "required": ["document_id", "document_type"],
                    },
                },
            },
            "required": ["customer_identification", "payments", "seller_id"],
        },
        category="write",
        registry="mcp",
    )
    def create_collection_vouchers(
        self,
        customer_identification: str,
        payments: list[dict[str, Any]],
        seller_id: int | None = None,
    ) -> dict[str, Any]:
        """Validate, resolve document_id idempotency, then create or replay.

        Nested attachments are validated and mapped only on the all-new create
        path. Exact-retry ignores attachment nests, customer, and seller_id
        (no add/replace/compare; no writes to matching vouchers).

        :raise UserError: when required fields are missing/invalid or conflicts.
        :raise AccessError: when the caller lacks voucher create rights.
        """
        customer = (customer_identification or "").strip()
        if not customer:
            raise UserError(_("customer_identification is required."))
        if not isinstance(payments, list) or not payments:
            raise UserError(_("payments must be a non-empty list."))
        seller = self._collection_require_internal_seller(seller_id)

        payment_vals_list = self._collection_parse_payment_vals(payments)
        document_ids = [vals["document_id"] for vals in payment_vals_list]
        if len(document_ids) != len(set(document_ids)):
            raise UserError(_("Duplicate document_id in the same call is not allowed."))

        # Caller env only — never sudo(); ORM ACL enforces base.group_user rights.
        existing = self._collection_vouchers_by_document_ids(document_ids)
        if existing:
            # Exact-retry / conflict: ignore attachment nests and seller_id.
            return self._collection_replay_or_reject(existing, document_ids)

        # Create-only: validate nests and map into voucher vals after all-new.
        payment_vals_list = self._collection_enrich_payment_attachments(
            payments, payment_vals_list
        )

        try:
            return self._collection_create_vouchers(
                customer, payment_vals_list, seller.id
            )
        except UniqueViolation:
            # Race: concurrent create won the unique(document_id) race.
            # Savepoint already rolled back + cleared; refresh ORM caches.
            # Attachment nests are ignored on the post-race replay path.
            self.env.invalidate_all()
            raced = self._collection_vouchers_by_document_ids(document_ids)
            if raced:
                return self._collection_replay_or_reject(raced, document_ids)
            raise UserError(
                _(
                    "Payment document_id conflict could not be resolved after "
                    "a concurrent create."
                )
            ) from None

    @api.model
    def _collection_parse_payment_vals(
        self, payments: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Validate payment dicts and return voucher create vals."""
        payment_vals_list: list[dict[str, Any]] = []
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
            document_type = raw.get("document_type")
            if document_type not in _DOCUMENT_TYPES:
                raise UserError(
                    _(
                        "Invalid document_type for payment index %(index)s.",
                        index=index,
                    )
                )
            check_type = raw.get("check_type")
            if check_type not in (None, False, "") and check_type not in _CHECK_TYPES:
                raise UserError(
                    _(
                        "Invalid check_type for payment index %(index)s.",
                        index=index,
                    )
                )
            vals: dict[str, Any] = {
                "document_id": document_id.strip(),
                "document_type": document_type,
            }
            for field_name in _PAYMENT_OPTIONAL_FIELDS:
                if field_name in raw and raw[field_name] not in (None, ""):
                    vals[field_name] = raw[field_name]
            payment_vals_list.append(vals)
        return payment_vals_list

    @api.model
    def _collection_enrich_payment_attachments(
        self,
        payments: list[dict[str, Any]],
        payment_vals_list: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Map optional attachment nests into voucher vals (create path only).

        Declared ``mimetype`` must equal the detected allow-listed MIME from
        ``datas``. Reuses ``collection.voucher._validate_attachment_payload``.
        """
        enriched: list[dict[str, Any]] = []
        for index, (raw, vals) in enumerate(
            zip(payments, payment_vals_list, strict=True)
        ):
            nest = raw.get("attachment") if isinstance(raw, dict) else None
            if nest in (None, False, ""):
                enriched.append(vals)
                continue
            attachment_vals = self._collection_parse_attachment_nest(nest, index)
            enriched.append({**vals, **attachment_vals})
        return enriched

    @api.model
    def _collection_parse_attachment_nest(
        self, nest: Any, index: int
    ) -> dict[str, Any]:
        """Validate nest shape + MIME/base64; return Binary/filename voucher vals."""
        if not isinstance(nest, dict):
            raise UserError(
                _(
                    "Payment attachment at index %(index)s must be an object.",
                    index=index,
                )
            )
        name = nest.get("name")
        mimetype = nest.get("mimetype")
        datas = nest.get("datas")
        if not isinstance(name, str) or not name.strip():
            raise UserError(
                _(
                    "Payment attachment at index %(index)s requires a non-empty name.",
                    index=index,
                )
            )
        if not isinstance(mimetype, str) or not mimetype.strip():
            raise UserError(
                _(
                    "Payment attachment at index %(index)s requires a non-empty "
                    "mimetype.",
                    index=index,
                )
            )
        if not isinstance(datas, str) or not datas.strip():
            raise UserError(
                _(
                    "Payment attachment at index %(index)s requires non-empty "
                    "base64 datas.",
                    index=index,
                )
            )

        Voucher = self.env["collection.voucher"]
        # Reuse model allow-list/base64 gate (image/* or application/pdf).
        Voucher._validate_attachment_payload(datas)

        raw = datas.encode() if isinstance(datas, str) else datas
        detected = guess_mimetype(b64decode(raw, validate=True)) or ""
        declared = mimetype.strip()
        if declared != detected:
            raise UserError(
                _(
                    "Payment attachment mimetype at index %(index)s "
                    "(%(declared)s) does not match detected type (%(detected)s).",
                    index=index,
                    declared=declared,
                    detected=detected or "unknown",
                )
            )
        return {
            "attachment": datas,
            "attachment_filename": name.strip(),
        }

    @api.model
    def _collection_vouchers_by_document_ids(self, document_ids: list[str]):
        """Return vouchers matching the submitted document_id set."""
        return self.env["collection.voucher"].search(
            [("document_id", "in", document_ids)]
        )

    @api.model
    def _collection_vouchers_payload(
        self, vouchers, document_ids: list[str]
    ) -> dict[str, Any]:
        """Build the MCP list response in submitted payment order."""
        by_doc = {voucher.document_id: voucher for voucher in vouchers}
        ordered = [by_doc[doc_id] for doc_id in document_ids]
        return {
            "vouchers": [
                {
                    "id": voucher.id,
                    "name": voucher.name,
                    "state": voucher.state,
                    "document_id": voucher.document_id,
                }
                for voucher in ordered
            ]
        }

    @api.model
    def _collection_replay_or_reject(
        self, existing, document_ids: list[str]
    ) -> dict[str, Any]:
        """Replay when every submitted document_id exists; otherwise reject."""
        if len(existing) != len(document_ids):
            raise UserError(
                _(
                    "Partial document_id conflict: some payments already exist "
                    "on another voucher."
                )
            )
        # Exact set of existing document_ids succeeds even across vouchers.
        # Customer identification, nested attachments, and seller_id are ignored.
        return self._collection_vouchers_payload(existing, document_ids)

    @api.model
    def _collection_require_internal_seller(self, seller_id: Any):
        """Return a browsable internal user or raise UserError (no sudo)."""
        if seller_id in (None, False, ""):
            raise UserError(_("seller_id is required."))
        try:
            seller_pk = int(seller_id)
        except (TypeError, ValueError) as err:
            raise UserError(_("seller_id must be an internal user.")) from err
        if seller_pk <= 0:
            raise UserError(_("seller_id is required."))
        seller = self.env["res.users"].browse(seller_pk)
        if (
            not seller.exists()
            or seller.share
            or not seller.has_group("base.group_user")
        ):
            raise UserError(_("seller_id must be an internal user."))
        return seller

    @api.model
    def _collection_create_vouchers(
        self,
        customer: str,
        payment_vals_list: list[dict[str, Any]],
        seller_id: int,
    ) -> dict[str, Any]:
        """Atomically create one voucher per payment inside a savepoint."""
        Voucher = self.env["collection.voucher"]
        document_ids = [vals["document_id"] for vals in payment_vals_list]
        create_vals = [
            {
                **vals,
                "customer_identification": customer,
                "state": "pending",
                "seller_id": seller_id,
            }
            for vals in payment_vals_list
        ]
        with self.env.cr.savepoint():
            vouchers = Voucher.create(create_vals)
        return self._collection_vouchers_payload(vouchers, document_ids)
