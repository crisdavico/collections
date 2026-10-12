# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_frozen_voucher_proof(self):
        """Deleting a voucher's designated proof is a proof change too.

        The database clears ``message_main_attachment_id`` on its own, past
        every voucher guard, so the voucher's rules are asked here first: a
        voucher on a closed or cancelled sheet keeps its proof. Elsewhere the
        delete goes through, and the next proof posted reopens review
        (``collection.voucher._proof_change_reopens_review``).
        """
        voucher_ids = {
            attachment.res_id
            for attachment in self
            if attachment.res_model == "collection.voucher" and attachment.res_id
        }
        if not voucher_ids:
            return
        vouchers = self.env["collection.voucher"].browse(voucher_ids).exists()
        for voucher in vouchers:
            if voucher.message_main_attachment_id in self:
                voucher._ensure_proof_change_allowed(False)
