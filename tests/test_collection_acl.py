# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import AccessError, UserError
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
        vals = {
            "customer_identification": "ACL-CUST",
            "document_type": "bank_transfer",
        }
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

    def test_no_voucher_line_model_or_acl(self):
        """collection.voucher.line must be gone, including its ACL row."""
        self.assertNotIn("collection.voucher.line", self.env)
        self.assertFalse(
            self.env["ir.model.access"].search(
                [("model_id.model", "=", "collection.voucher.line")]
            )
        )

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

    def _create_attached_pending_voucher(
        self, env, document_id, customer_identification
    ):
        self.env.company.write({"document_review_enabled": True})
        return env["collection.voucher"].create(
            {
                "customer_identification": customer_identification,
                "document_type": "bank_transfer",
                "amount": 100.0,
                "document_id": document_id,
                "attachment": PNG_B64,
                "attachment_filename": "acl-proof.png",
            }
        )

    def test_portal_user_review_queue_approve_reject_denied(self):
        """Non-internal users must be denied queue, approve, reject, and read."""
        admin_voucher = self._create_attached_pending_voucher(
            self.env,
            document_id="ACL-REV-PORTAL-DOC",
            customer_identification="ACL-REV-PORTAL",
        )
        Voucher = self.env["collection.voucher"].with_user(self.portal_user)
        with self.assertRaises(AccessError):
            Voucher.get_review_queue()
        with self.assertRaises(AccessError):
            Voucher.browse(admin_voucher.id).read(["state"])
        with self.assertRaises(AccessError):
            Voucher.browse(admin_voucher.id).action_review_approve({"amount": 1.0})
        with self.assertRaises(AccessError):
            Voucher.browse(admin_voucher.id).action_review_reject()
        with self.assertRaises(AccessError):
            Voucher.browse(admin_voucher.id).action_review_set_rotation(90)

    def test_internal_user_review_queue_and_approve_allowed(self):
        """Internal users must queue an attached pending voucher and approve it."""
        env = self.env(user=self.internal_user)
        voucher = self._create_attached_pending_voucher(
            env,
            document_id="ACL-REV-INT-APPROVE-DOC",
            customer_identification="ACL-REV-INT-APPROVE",
        )
        self.assertEqual(voucher.state, "pending")
        queue = env["collection.voucher"].get_review_queue()
        queued_ids = [item["id"] for item in queue]
        self.assertIn(voucher.id, queued_ids)
        voucher.action_review_approve({"amount": 150.0})
        self.assertEqual(voucher.state, "approved")
        self.assertEqual(voucher.amount, 150.0)
        self.assertEqual(voucher.reviewed_by, self.internal_user)
        self.assertTrue(voucher.reviewed_at)

    def test_internal_user_review_reject_allowed(self):
        """Triangulation: internal users must reject an attached pending voucher."""
        env = self.env(user=self.internal_user)
        voucher = self._create_attached_pending_voucher(
            env,
            document_id="ACL-REV-INT-REJECT-DOC",
            customer_identification="ACL-REV-INT-REJECT",
        )
        self.assertEqual(voucher.state, "pending")
        voucher.action_review_reject()
        self.assertEqual(voucher.state, "rejected")
        self.assertEqual(voucher.reviewed_by, self.internal_user)
        self.assertTrue(voucher.reviewed_at)

    def test_internal_user_review_set_rotation_allowed(self):
        """Internal users must persist viewer rotation on an eligible voucher."""
        env = self.env(user=self.internal_user)
        voucher = self._create_attached_pending_voucher(
            env,
            document_id="ACL-REV-INT-ROT-DOC",
            customer_identification="ACL-REV-INT-ROT",
        )
        voucher.action_review_set_rotation(90)
        self.assertEqual(voucher.attachment_rotation, 90)

    def test_internal_user_form_approve_allowed_when_review_off(self):
        """Payment Vouchers Approve must work even when Document Review is OFF."""
        self.env.company.write({"document_review_enabled": False})
        env = self.env(user=self.internal_user)
        voucher = env["collection.voucher"].create(
            self._voucher_vals(customer_identification="ACL-FORM-APPROVE")
        )
        with self.assertRaises(UserError):
            env["collection.voucher"].get_review_queue()
        voucher.action_approve()
        self.assertEqual(voucher.state, "approved")

    def _sheet_vals(self, **extra):
        vals = {"seller_id": self.internal_user.id}
        vals.update(extra)
        return vals

    def test_internal_user_sheet_crud_allowed(self):
        Sheet = self.env["collection.sheet"].with_user(self.internal_user)
        sheet = Sheet.create(self._sheet_vals())
        self.assertTrue(sheet.id)
        self.assertTrue(sheet.name)
        sheet.write({"voucher_ids": [(5, 0, 0)]})
        self.assertFalse(sheet.voucher_ids)
        sheet_id = sheet.id
        sheet.unlink()
        self.assertFalse(Sheet.browse(sheet_id).exists())

    def test_portal_user_sheet_crud_denied(self):
        Sheet = self.env["collection.sheet"].with_user(self.portal_user)
        with self.assertRaises(AccessError):
            Sheet.create(self._sheet_vals())
        admin_sheet = self.env["collection.sheet"].create(self._sheet_vals())
        with self.assertRaises(AccessError):
            Sheet.browse(admin_sheet.id).read(["name"])
        with self.assertRaises(AccessError):
            Sheet.browse(admin_sheet.id).write({"voucher_ids": [(5, 0, 0)]})
        with self.assertRaises(AccessError):
            Sheet.browse(admin_sheet.id).unlink()

    def test_sheet_acl_internal_group_only(self):
        """Triangulation: sheets use one base.group_user ACL row and no record rules."""
        acls = self.env["ir.model.access"].search(
            [("model_id.model", "=", "collection.sheet")]
        )
        self.assertEqual(len(acls), 1)
        self.assertEqual(acls.group_id, self.env.ref("base.group_user"))
        self.assertTrue(acls.perm_read)
        self.assertTrue(acls.perm_write)
        self.assertTrue(acls.perm_create)
        self.assertTrue(acls.perm_unlink)
        self.assertFalse(
            self.env["ir.rule"].search([("model_id.model", "=", "collection.sheet")])
        )
