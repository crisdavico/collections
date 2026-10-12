# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Shared constants and plain helpers for the collection models.

Kept free of Odoo model definitions so any model module can import it without
creating a registry load-order dependency.
"""

from odoo.exceptions import AccessError, UserError
from odoo.fields import Command

# Users + Managers role model. Back-office operators and the MCP API user are
# Collections Users; Close, Cancel, Reinstate and configuration need a Manager.
# Seller identity users are plain internal users and get no collection group.
COLLECTION_USER_GROUP = "collection.group_collection_user"
COLLECTION_MANAGER_GROUP = "collection.group_collection_manager"

# Catalog codes, mirrored by ``data/collection_document_type_data.xml`` and by
# ``collection.voucher`` / ``collection.voucher.review.snapshot`` selections.
DOCUMENT_TYPE_SELECTION = (
    ("bank_transfer", "Bank Transfer"),
    ("check", "Check"),
    ("cash_deposit", "Cash Deposit"),
    ("unsupported", "Unsupported"),
    ("echeck", "Echeck"),
    ("cash", "Cash"),
    ("retention_certificate", "Retention Certificate"),
    ("seller_deposit", "Seller Deposit"),
    ("seller_commission", "Seller Commission"),
)
DOCUMENT_TYPE_CODES = tuple(code for code, _label in DOCUMENT_TYPE_SELECTION)
CHECK_TYPE_SELECTION = (
    ("common", "Common"),
    ("deferred", "Deferred"),
)
RETENTION_KIND_SELECTION = (
    ("iva", "IVA"),
    ("ganancias", "Ganancias"),
    ("iibb", "IIBB"),
    ("suss", "SUSS"),
    ("other", "Other"),
)
DOCUMENT_KIND_SELECTION = (
    ("invoice", "Invoice"),
    ("quotation", "Quotation"),
)

# Types that carry no designated proof to review, so Document Review never
# reaches them and Confirm MUST NOT demand ``validated_collections`` of them.
# ``seller_deposit`` is deliberately absent: its remittance slip is reviewed.
CONFIRM_REVIEW_EXEMPT_TYPES = frozenset({"cash", "seller_commission"})

# Types that replace cash receipt values when they enter validated_collections.
CASH_REPLACEMENT_TYPES = frozenset({"seller_deposit", "seller_commission"})

# Sheet states that gate seller write, admin edit, and allocation pairing.
SELLER_SHEET_STATES = frozenset({"open"})
ADMIN_EDITABLE_SHEET_STATES = frozenset({"open", "submitted"})
SELLER_DECLARATION_STATES = frozenset({"submitted"})
DRAFT_SHEET_STATES = frozenset({"open", "submitted", "proposal", "cancelled"})
CONFIRMED_SHEET_STATE = "closed"
FROZEN_SHEET_STATES = frozenset({"closed", "cancelled"})
# Callers MAY skip ``raise_if_sheet_frozen`` only under these keys. Chatter
# ``message_post`` is not a bypass.
FROZEN_SHEET_BYPASS_CONTEXTS = frozenset(
    {
        "collection_sheet_audited_state",
        "collection_allocation_audited_state",
        "collection_receipt_audited_state",
        "collection_allocation_parent_unlink",
        "collection_sheet_unlinking",
    }
)


def check_collection_role(env, group_xmlid, message):
    """Raise ``AccessError(message)`` unless the user has the collection role.

    Action methods are callable over RPC, so a ``groups`` attribute on the
    button is not enough: the server checks the role itself. Superuser
    environments (crons, internal elevation) pass.
    """
    if env.su or env.user.has_group(group_xmlid):
        return
    raise AccessError(message)


def record_id(value):
    """Return a database id from a recordset, an int, or a falsy value."""
    if not value:
        return False
    if hasattr(value, "_name"):
        return value[:1].id or False
    return int(value)


def sanitize_voucher_commands(commands):
    """Turn ``Command.delete`` into ``Command.unlink`` on voucher one2manys.

    Vouchers outlive the sheet or allocation that groups them: dropping one
    from the relation must detach it, never delete the record.
    """
    return [
        Command.unlink(command[1])
        if command and command[0] == Command.DELETE
        else command
        for command in commands or []
    ]


def raise_if_sheet_frozen(sheets, message):
    """Raise ``UserError(message)`` when any of ``sheets`` is closed/cancelled.

    This helper does not inspect ``env.context``. Callers skip it only under
    ``FROZEN_SHEET_BYPASS_CONTEXTS`` (audited sheet/allocation/receipt state,
    ``collection_allocation_parent_unlink``, ``collection_sheet_unlinking``).
    ``message_post`` is not a bypass.
    """
    if any(sheet.state in FROZEN_SHEET_STATES for sheet in sheets):
        raise UserError(message)


def raise_if_create_vals_frozen(
    env, vals_list, message, *, field="sheet_id", comodel="collection.sheet"
):
    """Refuse create when the sheet reached from ``vals_list`` is frozen."""
    ids = []
    for vals in vals_list:
        identifier = record_id(vals.get(field))
        if identifier:
            ids.append(identifier)
    records = env[comodel].browse(ids)
    sheets = records if comodel == "collection.sheet" else records.mapped("sheet_id")
    raise_if_sheet_frozen(sheets, message)
