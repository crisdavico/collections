# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Seller identity for the collection MCP tools.

Off by default: a tool acts for the ``seller_id`` the agent passes. Once an
administrator names a header in ``collection.mcp_trusted_seller_header``, the
seller comes from that HTTP header instead. The gateway, never the model,
writes the verified sender phone there, so a ``seller_id`` or ``mobile``
argument that names anyone else is refused.
"""

from __future__ import annotations

from typing import Any

from odoo import _, api, models
from odoo.exceptions import AccessError, UserError
from odoo.http import request

from odoo.addons.collection.models.collection_common import COLLECTION_USER_GROUP

TRUSTED_SELLER_HEADER_PARAM = "collection.mcp_trusted_seller_header"
_OMITTED = (None, False, "")


def request_header(name: str) -> str:
    """Return header ``name`` of the current HTTP request, stripped, or ``""``.

    The only place that reads the request, so tests can patch it. Outside an
    HTTP request (cron, shell, tests) no header exists.
    """
    if not request:
        return ""
    return (request.httprequest.headers.get(name) or "").strip()


def _same_id(value: Any, expected: int) -> bool:
    """Return whether an agent-supplied id names ``expected``."""
    if isinstance(value, bool):
        return False
    try:
        return int(value) == expected
    except (TypeError, ValueError):
        return False


class CollectionSellerIdentityMixin(models.AbstractModel):
    """Resolve the caller role and the seller a collection MCP tool acts for."""

    _inherit = "muk_mcp.mixin"

    @api.model
    @api.private
    def _collection_require_collection_user(self) -> None:
        """Raise AccessError unless the MCP caller is a Collections User."""
        if not self.env.user.has_group(COLLECTION_USER_GROUP):
            raise AccessError(
                _("Only Collections Users can use the collection agent tools.")
            )

    @api.model
    @api.private
    def _collection_trusted_seller_header(self) -> str:
        """Return the trusted header name, or ``""`` while the feature is off."""
        # ir.config_parameter is readable by administrators only; this reads
        # one fixed key and writes nothing.
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(TRUSTED_SELLER_HEADER_PARAM)
        )
        return (value or "").strip()

    @api.model
    @api.private
    def _collection_seller_identity_error(self) -> AccessError:
        """One message for every identity failure, so none tells sellers apart."""
        return AccessError(_("The seller identity could not be verified."))

    @api.model
    @api.private
    def _collection_trusted_seller(self, header_name: str):
        """Return ``(seller, digits)`` for the trusted header, or fail closed."""
        digits = self._collection_normalize_ar_mobile(request_header(header_name))
        seller = self._collection_enabled_seller_by_mobile(digits)
        if not seller:
            raise self._collection_seller_identity_error()
        return seller, digits

    @api.model
    @api.private
    def _collection_mcp_seller(self, seller_id: Any = None):
        """Return the seller a tool acts for.

        Feature off: the internal user ``seller_id`` names. Feature on: the
        enabled seller the trusted header names; a ``seller_id`` naming anyone
        else is refused.
        """
        header_name = self._collection_trusted_seller_header()
        if not header_name:
            return self._collection_require_internal_seller(seller_id)
        seller, _digits = self._collection_trusted_seller(header_name)
        if seller_id not in _OMITTED and not _same_id(seller_id, seller.id):
            raise self._collection_seller_identity_error()
        return seller

    @api.model
    @api.private
    def _collection_mcp_seller_by_mobile(self, mobile: Any = None):
        """Return the seller ``get_seller_id`` answers with.

        Feature off: the unique enabled seller whose phone is ``mobile``.
        Feature on: the trusted header's seller; a ``mobile`` normalizing to
        another number is refused.
        """
        header_name = self._collection_trusted_seller_header()
        if header_name:
            seller, digits = self._collection_trusted_seller(header_name)
            if (
                mobile not in _OMITTED
                and self._collection_normalize_ar_mobile(mobile) != digits
            ):
                raise self._collection_seller_identity_error()
            return seller
        if not self._collection_normalize_ar_mobile(mobile):
            raise UserError(_("mobile is required."))
        seller = self._collection_enabled_seller_by_mobile(mobile)
        if not seller:
            raise UserError(_("No unique seller found for that mobile."))
        return seller
