# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import uuid

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL
from odoo.tools.translate import _

from .collection_common import (
    ADMIN_EDITABLE_SHEET_STATES,
    COLLECTION_MANAGER_GROUP,
    COLLECTION_USER_GROUP,
    CONFIRM_REVIEW_EXEMPT_TYPES,
    CONFIRMED_SHEET_STATE,
    SELLER_DECLARATION_STATES,
    SELLER_SHEET_STATES,
    check_collection_role,
    is_privileged,
    privileged,
    record_id,
    sanitize_voucher_commands,
)

_STATE_WRITE_ACTIONS = {
    "proposal": "action_confirm",
    "closed": "action_close",
    "cancelled": "action_cancel",
    "submitted": "_dispatch_submitted_state_write",
    "open": "action_reset_to_open",
}
_RESETTABLE_SHEET_STATES = frozenset({"submitted", "proposal", "closed", "cancelled"})
_VALIDATED_COLLECTIONS = "validated_collections"
# The "Entered in the ERP" mark is set and cleared only by its actions (and by
# Cancel), never by a plain write.
ERP_ENTRY_SCOPE = "collection_sheet_erp_entry"
_ERP_ENTRY_FIELDS = frozenset({"erp_entered_date", "erp_entered_uid"})
# Enough for a Confirm-review-exempt member: the seller decided it and
# Document Review has no proof to look at.
_SELLER_DECIDED_STATES = frozenset({"validated_seller", _VALIDATED_COLLECTIONS})


class CollectionSheet(models.Model):
    _name = "collection.sheet"
    _description = "Collection Sheet"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default="/",
    )
    seller_id = fields.Many2one(
        comodel_name="res.users",
        string="Seller",
        required=True,
        readonly=True,
        domain=[("share", "=", False)],
        ondelete="restrict",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    voucher_ids = fields.One2many(
        comodel_name="collection.voucher",
        inverse_name="sheet_id",
        string="Vouchers",
    )
    allocation_ids = fields.One2many(
        comodel_name="collection.allocation",
        inverse_name="sheet_id",
        string="Allocations",
    )
    debt_line_ids = fields.One2many(
        comodel_name="collection.allocation.line",
        inverse_name="sheet_id",
        string="Debt",
    )
    date_from = fields.Date(compute="_compute_dates", store=True)
    date_to = fields.Date(compute="_compute_dates", store=True)
    state = fields.Selection(
        selection=[
            ("open", "Open"),
            ("submitted", "Submitted by Seller"),
            ("proposal", "Proposal"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        default="open",
        required=True,
        tracking=True,
        copy=False,
    )
    document_review_enabled = fields.Boolean(
        compute="_compute_document_review_enabled",
    )
    voucher_count = fields.Integer(compute="_compute_voucher_count")
    erp_entered_date = fields.Datetime(
        string="Entered in the ERP",
        readonly=True,
        copy=False,
        index=True,
        help="When a manager marked this closed sheet's receipts as typed into "
        "the ERP. Its applied amounts stop being subtracted from the ERP "
        "balances once a connector refresh that started after this time "
        "succeeded.",
    )
    erp_entered_uid = fields.Many2one(
        comodel_name="res.users",
        string="Entered in the ERP by",
        readonly=True,
        copy=False,
    )

    @api.depends("voucher_ids", "voucher_ids.create_date")
    def _compute_dates(self):
        for sheet in self:
            create_dates = [
                fields.Date.to_date(voucher.create_date)
                for voucher in sheet.voucher_ids
                if voucher.create_date
            ]
            sheet.date_from = min(create_dates) if create_dates else False
            sheet.date_to = max(create_dates) if create_dates else False

    @api.depends_context("company")
    def _compute_document_review_enabled(self):
        enabled = bool(self.env.company._document_review_enabled())
        for sheet in self:
            sheet.document_review_enabled = enabled

    @api.depends("voucher_ids")
    def _compute_voucher_count(self):
        for sheet in self:
            sheet.voucher_count = len(sheet.voucher_ids)

    @api.private
    def _open_sheets_for_seller(self, seller, company):
        return self.search(
            [
                ("seller_id", "=", record_id(seller)),
                ("company_id", "=", record_id(company)),
                ("state", "in", list(SELLER_SHEET_STATES)),
            ]
        )

    @api.private
    def _submitted_sheets_for_seller(self, seller, company):
        return self.search(
            [
                ("seller_id", "=", record_id(seller)),
                ("company_id", "=", record_id(company)),
                ("state", "in", list(SELLER_DECLARATION_STATES)),
            ]
        )

    @api.private
    def _lock_open_sheet_for_seller(self, seller, company):
        self.env.cr.execute(
            SQL(
                "SELECT pg_advisory_xact_lock(hashtext(%s || %s), %s)",
                "collection.sheet.open.",
                str(int(record_id(company))),
                int(record_id(seller)),
            )
        )

    @api.private
    def _raise_if_seller_has_open_sheet(self, seller, company):
        if self._open_sheets_for_seller(seller, company):
            raise UserError(_("This seller already has an open collection sheet."))

    @api.private
    def _resolve_open_sheet_id_for_create(self, seller_id, company_id):
        self._lock_open_sheet_for_seller(seller_id, company_id)
        opens = self._open_sheets_for_seller(seller_id, company_id)
        if len(opens) > 1:
            raise UserError(_("This seller has more than one open collection sheet."))
        if len(opens) == 1:
            return opens.id
        return self.create({"seller_id": seller_id, "company_id": company_id}).id

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        opening_keys = set()
        for vals in vals_list:
            if _ERP_ENTRY_FIELDS & set(vals):
                self._raise_erp_entry_locked()
            company_id = vals.get("company_id") or self.env.company.id
            company = self.env["res.company"].browse(company_id)
            company._assert_new_work(vals.get("seller_id"))
            if vals.get("name", "/") in (False, "/", "New"):
                vals["name"] = (
                    sequence.with_company(company_id).next_by_code("collection.sheet")
                    or "/"
                )
            if "voucher_ids" in vals:
                vals["voucher_ids"] = sanitize_voucher_commands(vals["voucher_ids"])
            if vals.get("state") and vals["state"] not in SELLER_SHEET_STATES:
                raise UserError(_("Collection sheets can only be created in Open."))
            seller_id = vals.get("seller_id")
            if seller_id:
                key = (company_id, seller_id)
                if key in opening_keys:
                    raise UserError(
                        _("This seller already has an open collection sheet.")
                    )
                self._lock_open_sheet_for_seller(seller_id, company_id)
                self._raise_if_seller_has_open_sheet(seller_id, company_id)
                opening_keys.add(key)
        return super().create(vals_list)

    def write(self, vals):
        if _ERP_ENTRY_FIELDS & set(vals) and not is_privileged(ERP_ENTRY_SCOPE):
            self._raise_erp_entry_locked()
        if "seller_id" in vals:
            raise UserError(_("The sheet seller cannot be changed."))
        if "company_id" in vals:
            self._ensure_company_unlocked(vals["company_id"])
        if "state" in vals and not is_privileged("collection_sheet_audited_state"):
            target = vals["state"]
            rest = {key: value for key, value in vals.items() if key != "state"}
            if rest:
                if target == "submitted":
                    raise UserError(
                        _(
                            "Sheet state can only be changed via Seller Close, "
                            "Confirm, Close, Cancel, or Reinstate."
                        )
                    )
                super().write(rest)
            action_name = _STATE_WRITE_ACTIONS.get(target)
            if action_name:
                return getattr(self, action_name)()
            raise UserError(
                _(
                    "Sheet state can only be changed via Seller Close, Confirm, "
                    "Close, Cancel, or Reinstate."
                )
            )
        if "voucher_ids" in vals:
            if not is_privileged("collection_sheet_unlinking") and any(
                sheet.state not in ADMIN_EDITABLE_SHEET_STATES for sheet in self
            ):
                raise UserError(
                    _(
                        "Closed collection sheets cannot change membership. "
                        "Reopen first."
                    )
                )
            vals = dict(vals)
            vals["voucher_ids"] = sanitize_voucher_commands(vals["voucher_ids"])
        if "debt_line_ids" in vals:
            return self.env["collection.allocation.line"]._write_line_batch(
                self.allocation_ids, lambda: super(CollectionSheet, self).write(vals)
            )
        return super().write(vals)

    @api.private
    def _ensure_company_unlocked(self, company):
        """Refuse a company change once the sheet has vouchers or allocations.

        Allocations, lines and receipts take the sheet company through stored
        related fields while vouchers keep their own, so moving the sheet
        would split one sheet across two companies.
        """
        company_id = record_id(company)
        if any(
            sheet.company_id.id != company_id
            and (sheet.voucher_ids or sheet.allocation_ids)
            for sheet in self
        ):
            raise UserError(
                _(
                    "The company of a collection sheet with vouchers or "
                    "allocations cannot be changed."
                )
            )

    def unlink(self):
        # The ondelete cascade below detaches members and removes draft
        # allocations; only this scope lets it touch membership.
        with privileged("collection_sheet_unlinking"):
            return super().unlink()

    @api.ondelete(at_uninstall=False)
    def _unlink_open_sheets_and_cascade_allocations(self):
        if any(sheet.state not in SELLER_SHEET_STATES for sheet in self):
            raise UserError(_("Only open collection sheets can be deleted."))
        # Deleting the sheet detaches its vouchers (ondelete set null).
        self.voucher_ids._raise_if_in_cash_swap()
        self.allocation_ids.unlink()

    def action_seller_close(self, cash_on_hand=None, commission_withheld=None):
        """Seller Close: open → submitted, declaring the cash in the same step.

        A sheet with collected cash cannot close until the seller says how
        much of it they kept as commission (``commission_withheld``, zero
        included). ``cash_on_hand`` is computed and ignored.
        """
        for sheet in self:
            self._lock_open_sheet_for_seller(sheet.seller_id, sheet.company_id)
            # Lock is worthless without a re-read: cached state/membership can
            # predate the lock and hide a concurrent close or voucher insert.
            sheet.invalidate_recordset(["state", "voucher_ids"])
            if sheet.state not in SELLER_SHEET_STATES:
                raise UserError(
                    _("Only open collection sheets can be closed by the seller.")
                )
        self._raise_if_draft_vouchers_block_seller_close()
        for sheet in self:
            if commission_withheld is not None:
                sheet._check_commission_withheld(commission_withheld)
            elif sheet._has_collected_cash():
                raise UserError(
                    _(
                        "This sheet has collected cash of %(cash)s and a seller "
                        "commission of %(commission)s: Seller Close needs "
                        "commission_withheld, the cash the seller kept as "
                        "commission (zero if none).",
                        cash=sheet.cash_collected or 0.0,
                        commission=sheet.commission_amount or 0.0,
                    )
                )
        with privileged("collection_sheet_audited_state"):
            self.write({"state": "submitted"})
        if commission_withheld is not None:
            self.action_declare_cash(commission_withheld=commission_withheld)
        return True

    def action_open_seller_close(self):
        """Form button: close at once, or ask the cash kept when there is cash."""
        self.ensure_one()
        if not self._has_collected_cash():
            return self.action_seller_close()
        wizard = self.env["collection.sheet.close.wizard"].create({"sheet_id": self.id})
        return {
            "type": "ir.actions.act_window",
            "name": _("Seller Close"),
            "res_model": "collection.sheet.close.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    @api.private
    def _has_collected_cash(self):
        self.ensure_one()
        currency = self.company_id.currency_id
        return currency.compare_amounts(self._cash_collected_total(), 0.0) > 0

    @api.private
    def _check_commission_withheld(self, withheld):
        """Refuse a cash kept below zero, above the commission or the cash.

        :raise UserError: when ``withheld`` is negative, above the sheet's
            commission, or above the cash collected minus seller deposits.
        """
        self.ensure_one()
        currency = self.company_id.currency_id
        if currency.compare_amounts(withheld, 0.0) < 0:
            raise UserError(_("commission_withheld must be zero or more."))
        commission = self.commission_amount or 0.0
        if currency.compare_amounts(withheld, commission) > 0:
            raise UserError(
                _(
                    "commission_withheld cannot exceed the seller commission "
                    "of %(amount)s.",
                    amount=commission,
                )
            )
        cash = max((self.cash_collected or 0.0) - (self.cash_banked or 0.0), 0.0)
        if currency.compare_amounts(withheld, cash) > 0:
            raise UserError(
                _(
                    "commission_withheld cannot exceed the cash collected minus "
                    "seller deposits, %(amount)s.",
                    amount=cash,
                )
            )

    @api.private
    def _cash_collected_total(self):
        """Return SUM of cash voucher amounts on this sheet (company currency)."""
        self.ensure_one()
        return self.cash_collected or 0.0

    @api.private
    def _raise_if_draft_vouchers_block_seller_close(self):
        drafts = self.mapped("voucher_ids").filtered(
            lambda voucher: voucher.state == "draft"
        )
        if not drafts:
            return
        names = ", ".join(drafts.mapped("name"))
        raise UserError(_("Seller Close cannot include draft vouchers: %s", names))

    def action_declare_cash(self, commission_withheld=None):
        """Declare the withheld commission; cash on hand follows by compute.

        Without an amount (the form button) the sheet's current commission is
        declared: the form saves the typed value before the button runs.
        """
        if any(sheet.state not in SELLER_DECLARATION_STATES for sheet in self):
            raise UserError(_("Only submitted collection sheets can declare cash."))
        vals = {
            "cash_declared_at": fields.Datetime.now(),
            "cash_declared_by": self.env.user.id,
        }
        if commission_withheld is not None:
            vals["commission_withheld"] = commission_withheld
        return self.write(vals)

    @api.private
    def _dispatch_submitted_state_write(self):
        states = set(self.mapped("state"))
        if len(states) != 1:
            raise UserError(
                _("Seller Close and Reinstate cannot run on mixed sheet states.")
            )
        current = next(iter(states))
        if current in SELLER_SHEET_STATES:
            return self.action_seller_close()
        if current == "cancelled":
            return self.action_reinstate()
        raise UserError(_("Only open collection sheets can be closed by the seller."))

    @api.private
    def _check_collection_user(self):
        check_collection_role(
            self.env,
            COLLECTION_USER_GROUP,
            _(
                "Only Collections Users can review documents or work on "
                "collection sheets."
            ),
        )

    @api.private
    def _check_collection_manager(self):
        check_collection_role(
            self.env,
            COLLECTION_MANAGER_GROUP,
            _("Only Collections Managers can reinstate collection sheets."),
        )

    def action_confirm(self):
        self._check_collection_user()
        if any(sheet.state != "submitted" for sheet in self):
            raise UserError(_("Only submitted sheets can be confirmed."))
        for sheet in self:
            blocking = sheet._vouchers_blocking_confirm()
            if blocking:
                raise UserError(
                    _(
                        "Confirm requires every member voucher to be validated "
                        "by collections: %s",
                        ", ".join(blocking.mapped("name")),
                    )
                )
            collected = sheet._cash_collected_total()
            currency = sheet.company_id.currency_id
            if (
                currency.compare_amounts(collected, 0.0) > 0
                and not sheet.cash_declared_at
            ):
                raise UserError(
                    _(
                        "Confirm requires Declare Cash when the sheet has "
                        "collected cash."
                    )
                )
            sheet._ensure_seller_commission_voucher()
            sheet._raise_if_allocations_over_applied()
        with privileged("collection_sheet_audited_state"):
            return self.write({"state": "proposal"})

    @api.private
    def _seller_commission_voucher(self):
        self.ensure_one()
        return self.voucher_ids.filtered(
            lambda voucher: voucher.document_type == "seller_commission"
        )[:1]

    @api.private
    def _sync_seller_commission_voucher(self):
        """Keep an existing commission voucher equal to the declared commission.

        Only a reinstated sheet holds one before Confirm. Its cash replacement
        is reversed and run again for the new amount, so the voucher, the cash
        it replaced and ``cash_on_hand`` agree. A zero declaration leaves the
        voucher at zero.
        """
        self.ensure_one()
        commission = self._seller_commission_voucher()
        if not commission:
            return commission
        currency = self.company_id.currency_id
        withheld = currency.round(self.commission_withheld or 0.0)
        previous = commission.amount or 0.0
        if commission._resync_seller_commission(withheld):
            self.message_post(
                body=_(
                    "Seller commission %(name)s changed from %(previous)s to "
                    "%(amount)s.",
                    name=commission.name,
                    previous=previous,
                    amount=withheld,
                )
            )
        return commission

    @api.private
    def _ensure_seller_commission_voucher(self):
        """Mint at most one seller_commission from locked commission_withheld.

        An existing member (a reinstated sheet) is brought in step with the
        declaration instead. Otherwise a no-op when withheld is zero. Create
        stays ``validated_seller``; the audited write to ``validated_collections``
        runs replacement while the sheet is still ``submitted``.
        """
        self.ensure_one()
        existing = self._seller_commission_voucher()
        if existing:
            return self._sync_seller_commission_voucher()
        withheld = self.commission_withheld or 0.0
        currency = self.company_id.currency_id
        if currency.compare_amounts(withheld, 0.0) <= 0:
            return self.env["collection.voucher"]
        with privileged("collection_seller_commission_mint"):
            voucher = self.env["collection.voucher"].create(
                {
                    "document_type": "seller_commission",
                    "seller_id": self.seller_id.id,
                    "sheet_id": self.id,
                    "company_id": self.company_id.id,
                    "amount": withheld,
                    "document_id": f"sc-{uuid.uuid4().hex}",
                    "state": "validated_seller",
                }
            )
        with privileged("collection_audited_state"):
            voucher.write({"state": "validated_collections"})
        self.message_post(
            body=_(
                "Seller commission %(name)s minted for %(amount)s.",
                name=voucher.name,
                amount=withheld,
            )
        )
        return voucher

    @api.private
    def _vouchers_blocking_confirm(self):
        """Return the member vouchers whose review state still blocks Confirm.

        Cash never carries a designated proof, so Document Review cannot reach
        it and ``validated_seller`` is enough. Every other type -- including
        ``seller_deposit``, whose remittance slip is reviewable -- MUST be
        ``validated_collections``.
        """
        self.ensure_one()
        return self.voucher_ids.filtered(
            lambda voucher: voucher.state not in _SELLER_DECIDED_STATES
            if voucher.document_type in CONFIRM_REVIEW_EXEMPT_TYPES
            else voucher.state != _VALIDATED_COLLECTIONS
        )

    @api.private
    def _allocations_over_applied(self):
        """Return this sheet's allocations whose ``total_applied`` exceeds
        ``total_vouchers``.

        This is the collected-money gate: an allocation must not apply more
        than its vouchers actually collected. ``total_vouchers`` follows the
        receipt values, so a voucher split across customers counts on each
        customer it pays (the Planilla prints the same figure). It is
        independent of the
        debt-side ``residual``, which stays negative-capable by design -- an
        allocation with zero vouchers and zero applied money passes here even
        though it carries no proof of collection at all, because that is not
        an over-application.
        """
        self.ensure_one()
        currency = self.company_id.currency_id
        return self.allocation_ids.filtered(
            lambda allocation: currency.compare_amounts(
                allocation.total_applied, allocation.total_vouchers
            )
            > 0
        )

    @api.private
    def _raise_if_allocations_over_applied(self):
        self.ensure_one()
        offending = self._allocations_over_applied()
        if not offending:
            return
        details = ", ".join(
            f"{allocation.name} (applied {allocation.total_applied} "
            f"> collected {allocation.total_vouchers})"
            for allocation in offending
        )
        raise UserError(
            _(
                "Applied amount cannot exceed the money the vouchers actually "
                "collected: %s",
                details,
            )
        )

    def action_close(self):
        self._check_collection_user()
        if any(sheet.state != "proposal" for sheet in self):
            raise UserError(_("Only proposal sheets can be closed."))
        for sheet in self:
            sheet._raise_if_allocations_over_applied()
        self._mark_draft_receipts_closed()
        allocations = self.mapped("allocation_ids")
        if allocations:
            with privileged("collection_allocation_audited_state"):
                allocations.write({"state": "confirmed"})
        with privileged("collection_sheet_audited_state"):
            result = self.write({"state": "closed"})
        if allocations:
            allocations._check_sheet_state_iff()
        return result

    def action_cancel(self):
        self._check_collection_user()
        if any(
            sheet.state not in ("submitted", "proposal", "closed") for sheet in self
        ):
            raise UserError(
                _("Only submitted, proposal, or closed sheets can be cancelled.")
            )
        self._reopen_closed_receipts()
        allocations = self.mapped("allocation_ids")
        marked = self.filtered("erp_entered_date")
        with privileged("collection_sheet_audited_state"):
            result = self.write({"state": "cancelled"})
        if marked:
            # A cancelled sheet reserves nothing; Reinstate starts unmarked.
            marked._clear_erp_entry(
                _("Cancel removed the Entered in the ERP mark of this sheet.")
            )
        if allocations:
            with privileged("collection_allocation_audited_state"):
                allocations.write({"state": "draft"})
            allocations._check_sheet_state_iff()
        return result

    @api.private
    def _mark_draft_receipts_closed(self):
        """Close every local draft receipt. Skip issued. No connector."""
        self.mapped("allocation_ids.receipt_ids")._action_mark_closed()

    @api.private
    def _reopen_closed_receipts(self):
        """Reopen local closed receipts to draft. Skip issued."""
        self.mapped("allocation_ids.receipt_ids")._action_reopen_closed()

    def action_reinstate(self):
        self._check_collection_manager()
        if any(sheet.state != "cancelled" for sheet in self):
            raise UserError(_("Only cancelled sheets can be reinstated."))
        allocations = self.mapped("allocation_ids")
        with privileged("collection_sheet_audited_state"):
            result = self.write({"state": "submitted"})
        if allocations:
            allocations._check_sheet_state_iff()
            # Cancelled sheets do not count against a document's balance, so
            # coming back must not over-apply what another sheet took since.
            allocations.line_ids._check_invoice_not_over_applied()
        return result

    def action_reset_to_open(self):
        """Bring the sheet back to Open so it can be corrected or deleted.

        Works from every later state. Closed receipts reopen, allocations go
        back to draft, the ERP mark is cleared, and the seller commission gives
        back its cash and is deleted. The commission declaration is cleared as
        well, so the seller closes and declares cash again in the usual order.
        Refused while the seller has another open sheet: one open sheet per
        seller.
        """
        self._check_collection_user()
        if any(sheet.state not in _RESETTABLE_SHEET_STATES for sheet in self):
            raise UserError(
                _(
                    "Only submitted, proposal, closed, or cancelled sheets can "
                    "be reset to open."
                )
            )
        for sheet in self:
            sheet._reset_one_to_open()
        return True

    @api.private
    def _reset_one_to_open(self):
        self.ensure_one()
        self._lock_open_sheet_for_seller(self.seller_id, self.company_id)
        other = self._open_sheets_for_seller(self.seller_id, self.company_id) - self
        if other:
            raise UserError(
                _(
                    "The seller already has an open sheet: %s. Close or delete "
                    "it first.",
                    other[:1].name,
                )
            )
        was_cancelled = self.state == "cancelled"
        self._reopen_closed_receipts()
        allocations = self.allocation_ids
        with privileged("collection_sheet_audited_state"):
            self.write({"state": "open"})
        if self.erp_entered_date:
            self._clear_erp_entry(
                _("Reset to Open removed the Entered in the ERP mark of this sheet.")
            )
        if allocations:
            with privileged("collection_allocation_audited_state"):
                allocations.write({"state": "draft"})
            allocations._check_sheet_state_iff()
            if was_cancelled:
                # Cancelled sheets do not count against a document's balance.
                allocations.line_ids._check_invoice_not_over_applied()
        commission = self._seller_commission_voucher()
        if commission:
            if commission.state != "draft":
                commission.action_back_to_draft()
            commission.unlink()
        with privileged("collection_sheet_reset"):
            self.write(
                {
                    "commission_withheld": 0.0,
                    "cash_declared_at": False,
                    "cash_declared_by": False,
                }
            )
        self.message_post(body=_("Sheet reset to Open."))

    @api.private
    def _check_erp_entry_manager(self):
        check_collection_role(
            self.env,
            COLLECTION_MANAGER_GROUP,
            _("Only Collections Managers can mark sheets as entered in the ERP."),
        )

    @api.model
    @api.private
    def _raise_erp_entry_locked(self):
        raise UserError(
            _(
                "The Entered in the ERP mark can only be changed with its "
                "Mark and Unmark actions."
            )
        )

    def action_mark_erp_entered(self):
        """Record that this closed sheet's receipts were typed into the ERP.

        From then on its applied amounts stop being subtracted from the ERP
        balances once a connector refresh that started after the mark
        succeeded (the ERP shows them by then).
        """
        self._check_erp_entry_manager()
        if any(sheet.state != CONFIRMED_SHEET_STATE for sheet in self):
            raise UserError(
                _("Only closed sheets can be marked as entered in the ERP.")
            )
        if any(sheet.erp_entered_date for sheet in self):
            raise UserError(_("This sheet is already marked as entered in the ERP."))
        with privileged(ERP_ENTRY_SCOPE):
            self.write(
                {
                    "erp_entered_date": fields.Datetime.now(),
                    "erp_entered_uid": self.env.uid,
                }
            )
        for sheet in self:
            sheet.message_post(
                body=_("Receipts of this sheet marked as entered in the ERP.")
            )
        return True

    def action_unmark_erp_entered(self):
        """Undo a mistaken mark: the applied amounts are subtracted again."""
        self._check_erp_entry_manager()
        if any(not sheet.erp_entered_date for sheet in self):
            raise UserError(_("This sheet is not marked as entered in the ERP."))
        self._clear_erp_entry(_("The Entered in the ERP mark was removed."))
        return True

    @api.private
    def _clear_erp_entry(self, note):
        with privileged(ERP_ENTRY_SCOPE):
            self.write({"erp_entered_date": False, "erp_entered_uid": False})
        for sheet in self:
            sheet.message_post(body=note)

    def action_open_document_review(self):
        self.ensure_one()
        self._check_collection_user()
        self.env["collection.voucher"]._ensure_document_review_enabled()
        self._ensure_saved_sheet()
        if self.state not in ADMIN_EDITABLE_SHEET_STATES:
            raise UserError(
                _(
                    "Document Review is only available on open or submitted "
                    "collection sheets."
                )
            )
        action = self.env["ir.actions.actions"]._for_xml_id(
            "collection.action_collection_document_review"
        )
        action["params"] = dict(action.get("params") or {}, sheet_id=self.id)
        return action

    def action_open_vouchers(self):
        self.ensure_one()
        self._ensure_saved_sheet()
        return {
            "type": "ir.actions.act_window",
            "name": _("Vouchers"),
            "res_model": "collection.voucher",
            "view_mode": "list,kanban,form",
            "domain": [("sheet_id", "=", self.id)],
            "context": {
                "default_sheet_id": self.id,
                "default_seller_id": self.seller_id.id,
            },
        }

    @api.private
    def _ensure_saved_sheet(self):
        self.ensure_one()
        if isinstance(self.id, bool) or not isinstance(self.id, int) or self.id <= 0:
            raise UserError(_("This action requires a saved collection sheet."))
