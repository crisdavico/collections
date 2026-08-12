# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase


class TestCollectionMail(TransactionCase):
    """RED: mail thread / activities and state tracking on validate/reject."""

    def _flush_tracking(self):
        """Force mail.thread precommit tracking finalize (MailCommon.flush_tracking)."""
        self.env.flush_all()
        self.cr.flush()

    def _create_voucher(self, **extra):
        vals = {
            "customer_identification": "MAIL-CUST",
            "document_type": "bank_transfer",
        }
        vals.update(extra)
        voucher = self.env["collection.voucher"].create(vals)
        # Clear create-time _track_discard residue before state writes
        self._flush_tracking()
        return voucher

    def test_message_post_persists_on_voucher(self):
        voucher = self._create_voucher()
        message = voucher.message_post(
            body="Operator note on voucher",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        self.assertTrue(message.id)
        self.assertIn(message, voucher.message_ids)
        self.assertIn("Operator note on voucher", message.body)

    def test_activity_schedule_persists_on_voucher(self):
        voucher = self._create_voucher(customer_identification="MAIL-ACT")
        activity = voucher.activity_schedule(
            "mail.mail_activity_data_todo",
            summary="Review collection voucher",
        )
        self.assertTrue(activity.id)
        self.assertIn(activity, voucher.activity_ids)
        self.assertEqual(activity.summary, "Review collection voucher")

    def test_approve_tracks_state_in_chatter(self):
        voucher = self._create_voucher(customer_identification="MAIL-VAL")
        voucher.action_approve()
        self._flush_tracking()
        tracking = voucher.message_ids.sudo().mapped("tracking_value_ids")
        tracked_fields = tracking.mapped("field_id.name")
        self.assertIn("state", tracked_fields)
        state_tracking = tracking.filtered(lambda t: t.field_id.name == "state")
        self.assertTrue(state_tracking)
        self.assertEqual(state_tracking[-1].old_value_char, "Pending")
        self.assertEqual(state_tracking[-1].new_value_char, "Approved")

    def test_reject_tracks_state_in_chatter(self):
        voucher = self._create_voucher(customer_identification="MAIL-REJ")
        voucher.action_reject()
        self._flush_tracking()
        tracking = voucher.message_ids.sudo().mapped("tracking_value_ids")
        tracked_fields = tracking.mapped("field_id.name")
        self.assertIn("state", tracked_fields)
        state_tracking = tracking.filtered(lambda t: t.field_id.name == "state")
        self.assertTrue(state_tracking)
        self.assertEqual(state_tracking[-1].old_value_char, "Pending")
        self.assertEqual(state_tracking[-1].new_value_char, "Rejected")
