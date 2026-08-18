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

_PROVENANCE_NEST_SCHEMA = {
    "type": "object",
    "description": (
        "Typed payment review fields. Required together with the sibling nest. "
        "Must include document_type. Must not include document_id, attachment, "
        "or base64."
    ),
    "properties": {
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
    },
    "required": ["document_type"],
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
            "Each payment may include raw_ocr and seller_confirmed nests "
            "with typed payment fields (both required together). "
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
                            "raw_ocr": _PROVENANCE_NEST_SCHEMA,
                            "seller_confirmed": _PROVENANCE_NEST_SCHEMA,
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

        Nested attachments and provenance nests are validated and mapped only
        on the all-new create path. Exact-retry ignores attachment nests,
        provenance nests, customer, and seller_id (no add/replace/compare;
        no writes to matching vouchers).

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

        try:
            # Create-only: validate nests before writes (fail-closed).
            sidecars = self._collection_parse_payment_attachments(payments)
            provenances = self._collection_parse_payment_provenance(
                payments, payment_vals_list
            )
        except UserError:
            replayed = self._collection_replay_existing(document_ids)
            if replayed is not None:
                return replayed
            raise

        try:
            return self._collection_create_vouchers(
                customer, payment_vals_list, seller.id, sidecars, provenances
            )
        except UniqueViolation:
            # Race: concurrent create won the unique(document_id) race.
            # Savepoint already rolled back + cleared; refresh ORM caches.
            # Attachment nests are ignored on the post-race replay path.
            replayed = self._collection_replay_existing(document_ids)
            if replayed is not None:
                return replayed
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
    def _collection_parse_payment_attachments(
        self,
        payments: list[dict[str, Any]],
    ) -> list[tuple[str, bytes] | None]:
        """Validate optional nests; return chatter sidecars (create path only)."""
        sidecars: list[tuple[str, bytes] | None] = []
        for index, raw in enumerate(payments):
            nest = raw.get("attachment") if isinstance(raw, dict) else None
            if nest in (None, False, ""):
                sidecars.append(None)
                continue
            sidecars.append(self._collection_parse_attachment_nest(nest, index))
        return sidecars

    @api.model
    @api.private
    def _collection_parse_payment_provenance(
        self,
        payments: list[dict[str, Any]],
        payment_vals_list: list[dict[str, Any]],
    ) -> list[dict[str, Any] | None]:
        """Validate optional provenance nests on the all-new create path only."""
        stamps: list[dict[str, Any] | None] = []
        for index, (raw, current_vals) in enumerate(
            zip(payments, payment_vals_list, strict=True)
        ):
            stamps.append(
                self._collection_parse_provenance_nests(raw, current_vals, index)
            )
        return stamps

    @api.model
    @api.private
    def _collection_parse_provenance_nests(
        self,
        raw: Any,
        current_vals: dict[str, Any],
        index: int,
    ) -> dict[str, Any] | None:
        """Return ocr_*/seller_* stamps, None when both nests are omitted."""
        payload = raw if isinstance(raw, dict) else {}
        raw_ocr = payload.get("raw_ocr")
        seller = payload.get("seller_confirmed")
        raw_present = raw_ocr not in (None, False, "")
        seller_present = seller not in (None, False, "")
        if not raw_present and not seller_present:
            return None
        if raw_present != seller_present:
            raise UserError(
                _(
                    "Payment at index %(index)s requires both raw_ocr and "
                    "seller_confirmed together.",
                    index=index,
                )
            )
        parsed_raw = self._collection_parse_provenance_nest(raw_ocr, index, "raw_ocr")
        parsed_seller = self._collection_parse_provenance_nest(
            seller, index, "seller_confirmed"
        )
        current_comparable = {
            key: value for key, value in current_vals.items() if key != "document_id"
        }
        if parsed_seller != current_comparable:
            raise UserError(
                _(
                    "seller_confirmed at index %(index)s must match the payment "
                    "fields (except document_id).",
                    index=index,
                )
            )
        stamp: dict[str, Any] = {}
        for name, value in parsed_raw.items():
            stamp[f"ocr_{name}"] = value
        for name, value in parsed_seller.items():
            stamp[f"seller_{name}"] = value
        return stamp

    @api.model
    @api.private
    def _collection_parse_provenance_nest(
        self, nest: Any, index: int, nest_name: str
    ) -> dict[str, Any]:
        """Parse one provenance nest with the same optional-field equality rules."""
        if not isinstance(nest, dict):
            raise UserError(
                _(
                    "Payment %(nest_name)s at index %(index)s must be an object.",
                    nest_name=nest_name,
                    index=index,
                )
            )
        allowed = self.env["collection.voucher"]._REVIEW_EDITABLE_FIELDS
        unknown = set(nest) - allowed
        if unknown:
            raise UserError(
                _(
                    "Payment %(nest_name)s at index %(index)s has unsupported "
                    "keys: %(keys)s.",
                    nest_name=nest_name,
                    index=index,
                    keys=", ".join(sorted(unknown)),
                )
            )
        document_type = nest.get("document_type")
        if document_type not in _DOCUMENT_TYPES:
            raise UserError(
                _(
                    "Payment %(nest_name)s at index %(index)s requires document_type.",
                    nest_name=nest_name,
                    index=index,
                )
            )
        check_type = nest.get("check_type")
        if check_type not in (None, False, "") and check_type not in _CHECK_TYPES:
            raise UserError(
                _(
                    "Invalid check_type in %(nest_name)s for payment index %(index)s.",
                    nest_name=nest_name,
                    index=index,
                )
            )
        vals: dict[str, Any] = {"document_type": document_type}
        for field_name in _PAYMENT_OPTIONAL_FIELDS:
            if field_name in nest and nest[field_name] not in (None, ""):
                vals[field_name] = nest[field_name]
        return vals

    @api.model
    def _collection_parse_attachment_nest(
        self, nest: Any, index: int
    ) -> tuple[str, bytes]:
        """Validate nest shape + MIME/base64; return (name, raw bytes) sidecar."""
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
        return name.strip(), b64decode(raw, validate=True)

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
        # Customer identification, nested attachments, provenance nests, and
        # seller_id are ignored.
        return self._collection_vouchers_payload(existing, document_ids)

    @api.model
    def _collection_replay_existing(self, document_ids: list[str]):
        """Invalidate and replay if document_ids already exist; else None."""
        self.env.invalidate_all()
        raced = self._collection_vouchers_by_document_ids(document_ids)
        if raced:
            return self._collection_replay_or_reject(raced, document_ids)
        return None

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
        sidecars: list[tuple[str, bytes] | None],
        provenances: list[dict[str, Any] | None],
    ) -> dict[str, Any]:
        """Atomically create one voucher per payment inside a savepoint."""
        Voucher = self.env["collection.voucher"]
        document_ids = [vals["document_id"] for vals in payment_vals_list]
        create_vals = []
        for vals, provenance in zip(payment_vals_list, provenances, strict=True):
            row = {
                **vals,
                "customer_identification": customer,
                "state": "pending",
                "seller_id": seller_id,
            }
            if provenance:
                row.update(provenance)
            create_vals.append(row)
        with self.env.cr.savepoint():
            vouchers = Voucher.create(create_vals)
            for voucher, sidecar in zip(vouchers, sidecars, strict=True):
                if not sidecar:
                    continue
                name, raw = sidecar
                voucher.message_post(
                    body=_("Payment proof attached."),
                    message_type="notification",
                    attachments=[(name, raw)],
                )
        return self._collection_vouchers_payload(vouchers, document_ids)
