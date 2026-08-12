# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase

from .test_collection_payment import PNG_B64


class TestCollectionAcl(TransactionCase):
    """RED: ACL allow for base.group_user; deny for non-internal users."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.internal_user = cls._create_user("collection_internal", "base.group_user")
        cls.portal_user = cls._create_user("collection_portal", "base.group_portal")

    @classmethod
    def _partner_has_autopost_bills_column(cls):
        cls.env.cr.execute(
            """
            SELECT 1
              FROM information_schema.columns
             WHERE table_name = 'res_partner'
               AND column_name = 'autopost_bills'
            """
        )
        return bool(cls.env.cr.fetchone())

    @classmethod
    def _create_user(cls, login, group_xmlid):
        """Create a user; satisfy account.autopost_bills when the DB column exists."""
        partner_vals = {
            "name": login,
            "email": f"{login}@example.com",
        }
        Partner = cls.env["res.partner"].with_context(
            tracking_disable=True,
            mail_create_nolog=True,
            mail_notrack=True,
            mail_create_nosubscribe=True,
        )
        if "autopost_bills" in Partner._fields:
            partner_vals["autopost_bills"] = "ask"
            partner = Partner.create(partner_vals)
        elif cls._partner_has_autopost_bills_column():
            # Column left by account install but field not in this registry view
            cls.env.cr.execute(
                """
                INSERT INTO res_partner (
                    name, email, active, complete_name, type, autopost_bills,
                    create_uid, write_uid, create_date, write_date
                )
                VALUES (
                    %s, %s, true, %s, 'contact', 'ask',
                    1, 1,
                    (now() AT TIME ZONE 'UTC'),
                    (now() AT TIME ZONE 'UTC')
                )
                RETURNING id
                """,
                (login, partner_vals["email"], login),
            )
            partner = Partner.browse(cls.env.cr.fetchone()[0])
        else:
            partner = Partner.create(partner_vals)

        return (
            cls.env["res.users"]
            .with_context(no_reset_password=True, tracking_disable=True)
            .create(
                {
                    "name": login,
                    "login": login,
                    "email": partner_vals["email"],
                    "partner_id": partner.id,
                    "group_ids": [(6, 0, [cls.env.ref(group_xmlid).id])],
                }
            )
        )

    def _voucher_vals(self, **extra):
        vals = {"customer_identification": "ACL-CUST"}
        vals.update(extra)
        return vals

    def test_internal_user_voucher_crud_allowed(self):
        Voucher = self.env["collection.voucher"].with_user(self.internal_user)
        voucher = Voucher.create(self._voucher_vals())
        self.assertTrue(voucher.id)
        voucher.write({"customer_identification": "ACL-CUST-UPD"})
        self.assertEqual(voucher.customer_identification, "ACL-CUST-UPD")
        voucher_id = voucher.id
        voucher.unlink()
        self.assertFalse(Voucher.browse(voucher_id).exists())

    def test_internal_user_payment_crud_allowed(self):
        voucher = (
            self.env["collection.voucher"]
            .with_user(self.internal_user)
            .create(self._voucher_vals(customer_identification="ACL-PAY"))
        )
        Payment = self.env["collection.voucher.line"].with_user(self.internal_user)
        payment = Payment.create(
            {
                "voucher_id": voucher.id,
                "document_type": "bank_transfer",
                "from_account": "ACL-FROM",
            }
        )
        self.assertTrue(payment.id)
        payment.write({"to_account": "ACL-TO"})
        self.assertEqual(payment.to_account, "ACL-TO")
        payment_id = payment.id
        payment.unlink()
        self.assertFalse(Payment.browse(payment_id).exists())

    def test_portal_user_voucher_crud_denied(self):
        Voucher = self.env["collection.voucher"].with_user(self.portal_user)
        with self.assertRaises(AccessError):
            Voucher.create(self._voucher_vals(customer_identification="PORTAL-V"))
        admin_voucher = self.env["collection.voucher"].create(
            self._voucher_vals(customer_identification="PORTAL-DENY")
        )
        with self.assertRaises(AccessError):
            Voucher.browse(admin_voucher.id).read(["name"])
        with self.assertRaises(AccessError):
            Voucher.browse(admin_voucher.id).write({"customer_identification": "NOPE"})
        with self.assertRaises(AccessError):
            Voucher.browse(admin_voucher.id).unlink()

    def test_portal_user_payment_crud_denied(self):
        voucher = self.env["collection.voucher"].create(
            self._voucher_vals(customer_identification="PORTAL-PAY")
        )
        Payment = self.env["collection.voucher.line"].with_user(self.portal_user)
        with self.assertRaises(AccessError):
            Payment.create(
                {
                    "voucher_id": voucher.id,
                    "document_type": "unsupported",
                }
            )
        admin_payment = self.env["collection.voucher.line"].create(
            {
                "voucher_id": voucher.id,
                "document_type": "cash_deposit",
            }
        )
        with self.assertRaises(AccessError):
            Payment.browse(admin_payment.id).read(["document_type"])
        with self.assertRaises(AccessError):
            Payment.browse(admin_payment.id).write({"amount": 1.0})
        with self.assertRaises(AccessError):
            Payment.browse(admin_payment.id).unlink()

    def _create_attached_pending_line(self, env, document_id, customer_identification):
        self.env.company.write({"document_review_enabled": True})
        voucher = env["collection.voucher"].create(
            {"customer_identification": customer_identification}
        )
        line = env["collection.voucher.line"].create(
            {
                "voucher_id": voucher.id,
                "document_type": "bank_transfer",
                "amount": 100.0,
                "document_id": document_id,
                "attachment": PNG_B64,
                "attachment_filename": "acl-proof.png",
            }
        )
        return voucher, line

    def test_portal_user_review_queue_approve_reject_denied(self):
        """Non-internal users must be denied queue, approve, reject, and line read."""
        _voucher, admin_line = self._create_attached_pending_line(
            self.env,
            document_id="ACL-REV-PORTAL-DOC",
            customer_identification="ACL-REV-PORTAL",
        )
        Line = self.env["collection.voucher.line"].with_user(self.portal_user)
        with self.assertRaises(AccessError):
            Line.get_review_queue()
        with self.assertRaises(AccessError):
            Line.browse(admin_line.id).read(["state"])
        with self.assertRaises(AccessError):
            Line.browse(admin_line.id).action_review_approve({"amount": 1.0})
        with self.assertRaises(AccessError):
            Line.browse(admin_line.id).action_review_reject()
        with self.assertRaises(AccessError):
            Line.browse(admin_line.id).action_review_set_rotation(90)

    def test_internal_user_review_queue_and_approve_allowed(self):
        """Internal users must queue an attached pending line and approve it."""
        env = self.env(user=self.internal_user)
        voucher, line = self._create_attached_pending_line(
            env,
            document_id="ACL-REV-INT-APPROVE-DOC",
            customer_identification="ACL-REV-INT-APPROVE",
        )
        self.assertEqual(line.state, "pending")
        queue = env["collection.voucher.line"].get_review_queue()
        queued_ids = [item["id"] for item in queue]
        self.assertIn(line.id, queued_ids)
        line.action_review_approve({"amount": 150.0})
        self.assertEqual(line.state, "approved")
        self.assertEqual(line.amount, 150.0)
        self.assertEqual(line.reviewed_by, self.internal_user)
        self.assertTrue(line.reviewed_at)
        self.assertEqual(voucher.state, "validated")

    def test_internal_user_review_reject_allowed(self):
        """Triangulation: internal users must reject an attached pending line."""
        env = self.env(user=self.internal_user)
        voucher, line = self._create_attached_pending_line(
            env,
            document_id="ACL-REV-INT-REJECT-DOC",
            customer_identification="ACL-REV-INT-REJECT",
        )
        self.assertEqual(line.state, "pending")
        line.action_review_reject()
        self.assertEqual(line.state, "rejected")
        self.assertEqual(line.reviewed_by, self.internal_user)
        self.assertTrue(line.reviewed_at)
        self.assertEqual(voucher.state, "rejected")

    def test_internal_user_review_set_rotation_allowed(self):
        """Internal users must persist viewer rotation on an eligible line."""
        env = self.env(user=self.internal_user)
        _voucher, line = self._create_attached_pending_line(
            env,
            document_id="ACL-REV-INT-ROT-DOC",
            customer_identification="ACL-REV-INT-ROT",
        )
        line.action_review_set_rotation(90)
        self.assertEqual(line.attachment_rotation, 90)
