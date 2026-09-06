# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import annotations

import math
import re
from base64 import b64decode
from datetime import date, datetime
from typing import Any

from psycopg2.errors import UniqueViolation

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools.mimetypes import guess_mimetype

# One contract map drives flattened JSON Schema (MuK-safe) and runtime parse.
# MuK ``to_strict_schema`` strips ``anyOf`` / ``additionalProperties``; amounts
# are advertised as ``number`` (nullable on nests) and parsed as number|string.
_DOCUMENT_TYPES = (
    "bank_transfer",
    "check",
    "echeck",
    "cash_deposit",
    "retention_certificate",
    "cash",
    "unsupported",
)
_CHECK_TYPES = ("common", "deferred")
_RETENTION_KINDS = ("iva", "ganancias", "iibb", "suss", "other")
_OMIT_VALUES = (None, False, "")
_ISO_DATE = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")
_DATE_FIELDS = frozenset({"voucher_date", "check_issue_date", "check_payment_date"})
_CHECK_DATE_TYPES = frozenset({"check", "echeck"})

_TYPE_OWNED_FIELDS: dict[str, frozenset[str]] = {
    "bank_transfer": frozenset(
        {"amount", "from_account", "to_account", "voucher_number", "voucher_date"}
    ),
    "check": frozenset(
        {
            "amount",
            "check_number",
            "check_bank",
            "check_issue_date",
            "check_payment_date",
            "check_type",
        }
    ),
    "echeck": frozenset(
        {
            "amount",
            "check_number",
            "check_bank",
            "check_issue_date",
            "check_payment_date",
            "check_type",
        }
    ),
    "cash_deposit": frozenset(
        {"amount", "to_account", "voucher_number", "voucher_date"}
    ),
    "retention_certificate": frozenset(
        {"amount", "voucher_number", "voucher_date", "retention_kind"}
    ),
    "cash": frozenset({"amount", "voucher_date"}),
    "unsupported": frozenset(),
}

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
    "retention_kind",
)
_PAYMENT_KEYS = frozenset({"document_id", "attachment", "raw_ocr", "seller_confirmed"})
_ATTACHMENT_KEYS = frozenset({"name", "mimetype", "datas"})
_PROVENANCE_KEYS = frozenset(("document_type",) + _PAYMENT_OPTIONAL_FIELDS)

_COLLECTION_AMOUNT_SCHEMA = {
    "type": "number",
    "description": "Amount as a JSON number or decimal string.",
}
_COLLECTION_NULLABLE_AMOUNT_SCHEMA = {
    "type": "number",
    "nullable": True,
    "description": "Payment amount as a JSON number or decimal string.",
}

_NEST_FIELD_SCHEMA = {
    "amount": _COLLECTION_NULLABLE_AMOUNT_SCHEMA,
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
    "retention_kind": {
        "type": "string",
        "nullable": True,
        "enum": list(_RETENTION_KINDS),
        "description": "Retention certificate kind.",
    },
}


def _collection_reject_unknown_keys(
    raw: dict[str, Any], allowed: frozenset[str], label: str
) -> None:
    """Raise UserError when ``raw`` has keys outside ``allowed`` (extra=forbid)."""
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise UserError(
            _(
                "%(label)s has unsupported keys: %(keys)s.",
                label=label,
                keys=", ".join(unknown),
            )
        )


def _collection_normalize_amount(value: Any) -> float:
    """Parse a JSON number or decimal string; reject bool, non-finite, and junk."""
    if isinstance(value, bool) or value in _OMIT_VALUES:
        raise ValueError("invalid amount")
    if isinstance(value, str):
        value = value.strip()
        if not value:
            raise ValueError("invalid amount")
    elif not isinstance(value, int | float):
        raise ValueError("invalid amount")
    try:
        amount = float(value)
    except (TypeError, ValueError) as err:
        raise ValueError("invalid amount") from err
    if not math.isfinite(amount):
        raise ValueError("invalid amount")
    return amount


def _collection_normalize_iso_date(value: Any) -> str:
    """Return ``YYYY-MM-DD``; accept ISO strings or ``date``/``datetime``."""
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and _ISO_DATE.fullmatch(value):
        date.fromisoformat(value)
        return value
    raise ValueError("invalid date")


def _collection_normalize_mimetype(value: str) -> str:
    """Casefold, strip parameters, and alias ``image/jpg`` to ``image/jpeg``."""
    base = value.split(";", 1)[0].strip().casefold()
    if base == "image/jpg":
        return "image/jpeg"
    return base


def _provenance_nest_schema() -> dict[str, Any]:
    """Flattened seven-type nest schema from ``_TYPE_OWNED_FIELDS``."""
    properties: dict[str, Any] = {
        "document_type": {
            "type": "string",
            "enum": list(_DOCUMENT_TYPES),
            "description": "Payment document type.",
        },
    }
    for field_name in _PAYMENT_OPTIONAL_FIELDS:
        properties[field_name] = dict(_NEST_FIELD_SCHEMA[field_name])
    return {
        "type": "object",
        "description": (
            "Typed payment review fields. seller_confirmed is required; raw_ocr is "
            "optional. Must include document_type. Must not include document_id, "
            "attachment, or base64."
        ),
        "properties": properties,
        "required": ["document_type"],
    }


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

_PROVENANCE_NEST_SCHEMA = _provenance_nest_schema()

_PAYMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "document_id": {
            "type": "string",
            "minLength": 1,
            "description": "Unique payment document identifier.",
        },
        "attachment": _ATTACHMENT_NEST_SCHEMA,
        "raw_ocr": _PROVENANCE_NEST_SCHEMA,
        "seller_confirmed": _PROVENANCE_NEST_SCHEMA,
    },
    "required": ["document_id", "seller_confirmed"],
}


class CollectionMcpMixin(models.AbstractModel):
    """Internal collection payment helpers on muk_mcp.mixin."""

    _inherit = "muk_mcp.mixin"

    @api.model
    def _collection_parse_payment_vals(
        self, payments: list[dict[str, Any]], identification: str
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Validate payments; voucher fields come from required seller_confirmed."""
        if not isinstance(identification, str) or not identification.strip():
            raise UserError(_("customer_identification is required."))
        identification = identification.strip()
        payment_vals_list: list[dict[str, Any]] = []
        identifications: list[str] = []
        currency = self.env.company.currency_id
        for index, raw in enumerate(payments):
            if not isinstance(raw, dict):
                raise UserError(
                    _("Payment at index %(index)s must be an object.", index=index)
                )
            _collection_reject_unknown_keys(
                raw,
                _PAYMENT_KEYS,
                _("Payment at index %(index)s", index=index),
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
            seller = raw.get("seller_confirmed")
            if seller in (None, False, ""):
                raise UserError(
                    _(
                        "Each payment requires seller_confirmed (index %(index)s).",
                        index=index,
                    )
                )
            parsed = self._collection_parse_provenance_nest(
                seller, index, "seller_confirmed"
            )
            document_type = parsed["document_type"]
            if document_type == "unsupported":
                raise UserError(
                    _(
                        "Unsupported payments cannot be allocated (index %(index)s).",
                        index=index,
                    )
                )
            amount = parsed.get("amount")
            try:
                amount_value = _collection_normalize_amount(amount)
            except ValueError as err:
                raise UserError(
                    _(
                        "seller_confirmed amount must be greater than zero "
                        "(index %(index)s).",
                        index=index,
                    )
                ) from err
            if currency.compare_amounts(amount_value, 0.0) <= 0:
                raise UserError(
                    _(
                        "seller_confirmed amount must be greater than zero "
                        "(index %(index)s).",
                        index=index,
                    )
                )
            identifications.append(identification)
            vals: dict[str, Any] = {
                "document_id": document_id.strip(),
                **parsed,
                "amount": amount_value,
            }
            payment_vals_list.append(vals)
        return payment_vals_list, identifications

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
        """Stamp seller_* always; stamp ocr_* only when raw_ocr is present."""
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
        """Return ocr_*/seller_* stamps; seller_confirmed required, raw_ocr optional."""
        payload = raw if isinstance(raw, dict) else {}
        raw_ocr = payload.get("raw_ocr")
        seller = payload.get("seller_confirmed")
        raw_present = raw_ocr not in (None, False, "")
        seller_present = seller not in (None, False, "")
        if not seller_present:
            if raw_present:
                raise UserError(
                    _(
                        "Payment at index %(index)s requires seller_confirmed "
                        "when raw_ocr is present.",
                        index=index,
                    )
                )
            return None
        parsed_seller = self._collection_parse_provenance_nest(
            seller, index, "seller_confirmed"
        )
        current_comparable = {
            key: value
            for key, value in current_vals.items()
            if key not in ("document_id",)
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
        for name, value in parsed_seller.items():
            stamp[f"seller_{name}"] = value
        if raw_present:
            parsed_raw = self._collection_parse_provenance_nest(
                raw_ocr, index, "raw_ocr"
            )
            for name, value in parsed_raw.items():
                stamp[f"ocr_{name}"] = value
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
        _collection_reject_unknown_keys(
            nest,
            _PROVENANCE_KEYS,
            _(
                "Payment %(nest_name)s at index %(index)s",
                nest_name=nest_name,
                index=index,
            ),
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
        owned = _TYPE_OWNED_FIELDS[document_type]
        foreign = sorted(
            key
            for key, value in nest.items()
            if key != "document_type" and value not in _OMIT_VALUES and key not in owned
        )
        if foreign:
            raise UserError(
                _(
                    "Payment %(nest_name)s at index %(index)s has type-foreign "
                    "keys: %(keys)s.",
                    nest_name=nest_name,
                    index=index,
                    keys=", ".join(foreign),
                )
            )
        check_type = nest.get("check_type")
        if check_type not in _OMIT_VALUES and check_type not in _CHECK_TYPES:
            raise UserError(
                _(
                    "Invalid check_type in %(nest_name)s for payment index %(index)s.",
                    nest_name=nest_name,
                    index=index,
                )
            )
        retention_kind = nest.get("retention_kind")
        if (
            retention_kind not in _OMIT_VALUES
            and retention_kind not in _RETENTION_KINDS
        ):
            raise UserError(
                _(
                    "Invalid retention_kind in %(nest_name)s for payment "
                    "index %(index)s.",
                    nest_name=nest_name,
                    index=index,
                )
            )
        vals: dict[str, Any] = {"document_type": document_type}
        for field_name in _PAYMENT_OPTIONAL_FIELDS:
            if field_name not in owned or field_name not in nest:
                continue
            value = nest[field_name]
            if value in _OMIT_VALUES:
                continue
            if field_name == "amount":
                try:
                    vals["amount"] = _collection_normalize_amount(value)
                except ValueError as err:
                    raise UserError(
                        _(
                            "Invalid amount in %(nest_name)s for payment "
                            "index %(index)s.",
                            nest_name=nest_name,
                            index=index,
                        )
                    ) from err
                continue
            if field_name in _DATE_FIELDS:
                try:
                    vals[field_name] = _collection_normalize_iso_date(value)
                except ValueError as err:
                    raise UserError(
                        _(
                            "Invalid %(field_name)s in %(nest_name)s for payment "
                            "index %(index)s.",
                            field_name=field_name,
                            nest_name=nest_name,
                            index=index,
                        )
                    ) from err
                continue
            vals[field_name] = value
        if document_type in _CHECK_DATE_TYPES:
            issue = vals.get("check_issue_date")
            payment = vals.get("check_payment_date")
            if issue and payment and payment < issue:
                raise UserError(
                    _(
                        "check_payment_date must be on or after check_issue_date "
                        "in %(nest_name)s for payment index %(index)s.",
                        nest_name=nest_name,
                        index=index,
                    )
                )
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
        _collection_reject_unknown_keys(
            nest,
            _ATTACHMENT_KEYS,
            _("Payment attachment at index %(index)s", index=index),
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
        declared = _collection_normalize_mimetype(mimetype)
        detected_normalized = _collection_normalize_mimetype(detected)
        if declared != detected_normalized:
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
    @api.private
    def _collection_document_conflict_error(self) -> UserError:
        """Return a generic document_id conflict UserError (no id or name)."""
        return UserError(_("Payment document_id conflict could not be resolved."))

    @api.model
    @api.private
    def _collection_classify_visible(self, existing, document_ids: list[str]):
        """Return replay payload, raise on other-company/partial, or None if new."""
        if not existing:
            return None
        current_id = self.env.company.id
        if any(voucher.company_id.id != current_id for voucher in existing):
            raise self._collection_document_conflict_error()
        return self._collection_replay_or_reject(existing, document_ids)

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
        """Invalidate caches and classify visible document_id rows, or return None."""
        self.env.invalidate_all()
        raced = self._collection_vouchers_by_document_ids(document_ids)
        return self._collection_classify_visible(raced, document_ids)

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
        payment_vals_list: list[dict[str, Any]],
        seller_id: int,
        sidecars: list[tuple[str, bytes] | None],
        provenances: list[dict[str, Any] | None],
        identifications: list[str],
    ) -> dict[str, Any]:
        """Atomically resolve customers and create one voucher per payment."""
        Voucher = self.env["collection.voucher"]
        document_ids = [vals["document_id"] for vals in payment_vals_list]
        connector = self.env.company._collection_active_connector()
        with self.env.cr.savepoint():
            create_vals = []
            for vals, provenance, identification in zip(
                payment_vals_list, provenances, identifications, strict=True
            ):
                try:
                    with self.env.cr.savepoint():
                        partner = connector.resolve_customer_partner(
                            seller_id, identification
                        )
                except UniqueViolation:
                    # Binding UNIQUE must not reach the outer document_id handler.
                    raise UserError(
                        _("The requested customer is not available.")
                    ) from None
                row = {
                    **vals,
                    "state": "validated_seller",
                    "seller_id": seller_id,
                    "partner_id": partner.id,
                }
                if provenance:
                    row.update(provenance)
                create_vals.append(row)
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
