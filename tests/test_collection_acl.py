# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import inspect

from odoo.exceptions import AccessError, UserError
from odoo.fields import Command
from odoo.tests import TransactionCase

from odoo.addons.collection.models.collection_common import privileged

from .test_collection_payment import (
    PNG_B64,
    dummy_customer_partner,
    ensure_enabled_seller,
    post_voucher_proof,
)


class TestCollectionAcl(TransactionCase):
    """ACL allow for Collections Users; deny for users without the role."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.internal_user = cls._create_user(
            "collection_internal", "collection.group_collection_user"
        )
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

    def _create_company(self, name):
        """Persist a second company; satisfy partner.autopost_bills when present."""
        Partner = self.env["res.partner"].with_context(
            tracking_disable=True,
            mail_create_nolog=True,
            mail_notrack=True,
            mail_create_nosubscribe=True,
        )
        partner_vals = {"name": name, "is_company": True}
        if "autopost_bills" in Partner._fields:
            partner_vals["autopost_bills"] = "ask"
            partner = Partner.create(partner_vals)
        elif self._partner_has_autopost_bills_column():
            self.env.cr.execute(
                """
                INSERT INTO res_partner (
                    name, email, active, complete_name, type, is_company,
                    autopost_bills, create_uid, write_uid, create_date, write_date
                )
                VALUES (
                    %s, %s, true, %s, 'contact', true, 'ask',
                    1, 1,
                    (now() AT TIME ZONE 'UTC'),
                    (now() AT TIME ZONE 'UTC')
                )
                RETURNING id
                """,
                (name, f"{name}@example.com", name),
            )
            partner = Partner.browse(self.env.cr.fetchone()[0])
        else:
            partner = Partner.create(partner_vals)
        return self.env["res.company"].create(
            {
                "name": name,
                "partner_id": partner.id,
            }
        )

    def _restrict_user_to_company(self, user, company):
        user.write(
            {
                "company_id": company.id,
                "company_ids": [(6, 0, [company.id])],
            }
        )

    def _assert_global_company_rule(self, model_name):
        rules = self.env["ir.rule"].search([("model_id.model", "=", model_name)])
        self.assertEqual(
            len(rules), 1, f"{model_name} must have exactly one record rule"
        )
        self.assertFalse(rules.groups, f"{model_name} company rule must be global")
        compact = "".join(rules.domain_force.split())
        self.assertEqual(
            compact,
            "[('company_id','in',company_ids)]",
            f"{model_name} rule must hide companies outside company_ids",
        )

    def _assert_hidden_from_user(self, user, record, read_fields):
        Model = self.env[record._name].with_user(user)
        self.assertFalse(
            Model.search([("id", "=", record.id)]),
            f"{record._name} {record.id} must not be searchable from the other company",
        )
        with self.assertRaises(AccessError):
            Model.browse(record.id).read(read_fields)
        self.assertEqual(
            Model.search_read([("id", "=", record.id)], read_fields),
            [],
        )

    def _voucher_vals(self, customer=None, **extra):
        seller = extra.get("seller_id") or self.internal_user.id
        company = self.env["res.company"].browse(
            extra.get("company_id") or self.env.company.id
        )
        ensure_enabled_seller(
            self.env, self.env["res.users"].browse(seller), company=company
        )
        partner = dummy_customer_partner(
            self.env, customer=customer, extra=extra, default="ACL-CUST"
        )
        vals = {
            "partner_id": partner.id,
            "document_type": "bank_transfer",
            "seller_id": seller,
        }
        document_type = extra.get("document_type", vals["document_type"])
        if document_type != "unsupported" and "amount" not in extra:
            vals["amount"] = 100.0
        vals.update(extra)
        return vals

    def test_internal_user_voucher_crud_allowed(self):
        Voucher = self.env["collection.voucher"].with_user(self.internal_user)
        voucher = Voucher.create(self._voucher_vals())
        self.assertTrue(voucher.id)
        updated = dummy_customer_partner(self.env, customer="ACL-CUST-UPD")
        voucher.write({"partner_id": updated.id})
        self.assertEqual(voucher.partner_id, updated)
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
            Voucher.browse(admin_voucher.id).write(
                {
                    "partner_id": dummy_customer_partner(self.env, customer="NOPE").id,
                }
            )
        with self.assertRaises(AccessError):
            Voucher.browse(admin_voucher.id).unlink()

    def _create_attached_pending_voucher(
        self, env, document_id, customer_identification
    ):
        self.env.company.write({"document_review_enabled": True})
        seller = ensure_enabled_seller(self.env)
        sheet = self.env["collection.sheet"].create({"seller_id": seller.id})
        voucher = env["collection.voucher"].create(
            {
                "partner_id": dummy_customer_partner(
                    self.env, customer=customer_identification
                ).id,
                "document_type": "bank_transfer",
                "amount": 100.0,
                "document_id": document_id,
                "seller_id": seller.id,
                "sheet_id": sheet.id,
            }
        )
        post_voucher_proof(voucher, "acl-proof.png", PNG_B64)
        voucher.action_validate_seller()
        return voucher

    def test_portal_user_review_queue_approve_reject_denied(self):
        """Non-internal users must be denied queue, approve, rotation, and read."""
        admin_voucher = self._create_attached_pending_voucher(
            self.env,
            document_id="ACL-REV-PORTAL-DOC",
            customer_identification="ACL-REV-PORTAL",
        )
        sheet_id = admin_voucher.sheet_id.id
        Voucher = self.env["collection.voucher"].with_user(self.portal_user)
        with self.assertRaises(AccessError):
            Voucher.get_review_queue(sheet_id)
        with self.assertRaises(AccessError):
            Voucher.browse(admin_voucher.id).read(["state"])
        with self.assertRaises(AccessError):
            Voucher.browse(admin_voucher.id).action_review_approve(
                sheet_id, {"amount": 1.0}
            )
        self.assertFalse(hasattr(Voucher, "action_review_reject"))
        with self.assertRaises(AccessError):
            Voucher.browse(admin_voucher.id).action_review_set_rotation(sheet_id, 90)

    def test_internal_user_review_queue_and_approve_allowed(self):
        """Collections Users queue an attached pending voucher and approve it."""
        env = self.env(user=self.internal_user)
        voucher = self._create_attached_pending_voucher(
            env,
            document_id="ACL-REV-INT-APPROVE-DOC",
            customer_identification="ACL-REV-INT-APPROVE",
        )
        self.assertEqual(voucher.state, "validated_seller")
        sheet_id = voucher.sheet_id.id
        queue = env["collection.voucher"].get_review_queue(sheet_id)
        queued_ids = [item["id"] for item in queue]
        self.assertIn(voucher.id, queued_ids)
        voucher.action_review_approve(sheet_id, {"amount": 150.0})
        self.assertEqual(voucher.state, "validated_collections")
        self.assertEqual(voucher.amount, 150.0)
        self.assertEqual(voucher.reviewed_by, self.internal_user)
        self.assertTrue(voucher.reviewed_at)

    def test_internal_user_review_reject_allowed(self):
        """Triangulation: internal users have no review reject RPC."""
        env = self.env(user=self.internal_user)
        voucher = self._create_attached_pending_voucher(
            env,
            document_id="ACL-REV-INT-REJECT-DOC",
            customer_identification="ACL-REV-INT-REJECT",
        )
        self.assertEqual(voucher.state, "validated_seller")
        self.assertFalse(hasattr(voucher, "action_review_reject"))
        self.assertFalse(voucher.reviewed_by)

    def test_internal_user_review_set_rotation_allowed(self):
        """Collections Users persist viewer rotation on an eligible voucher."""
        env = self.env(user=self.internal_user)
        voucher = self._create_attached_pending_voucher(
            env,
            document_id="ACL-REV-INT-ROT-DOC",
            customer_identification="ACL-REV-INT-ROT",
        )
        voucher.action_review_set_rotation(voucher.sheet_id.id, 90)
        self.assertEqual(voucher.attachment_rotation, 90)

    def test_internal_user_form_validate_seller_allowed_when_review_off(self):
        """Payment Vouchers Validate by Seller works when Document Review is OFF."""
        self.env.company.write({"document_review_enabled": False})
        env = self.env(user=self.internal_user)
        voucher = env["collection.voucher"].create(
            self._voucher_vals(customer_identification="ACL-FORM-APPROVE")
        )
        with self.assertRaises(UserError):
            env["collection.voucher"].get_review_queue()
        voucher.action_validate_seller()
        self.assertEqual(voucher.state, "validated_seller")
        self.assertFalse(voucher.reviewed_by)
        self.assertFalse(voucher.reviewed_at)

    def _sheet_vals(self, **extra):
        vals = {"seller_id": self.internal_user.id}
        vals.update(extra)
        seller = self.env["res.users"].browse(vals["seller_id"])
        company = self.env["res.company"].browse(
            vals.get("company_id") or self.env.company.id
        )
        ensure_enabled_seller(self.env, seller, company=company)
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
        """Sheets use one Collections User ACL row plus a global company rule."""
        acls = self.env["ir.model.access"].search(
            [("model_id.model", "=", "collection.sheet")]
        )
        self.assertEqual(len(acls), 1)
        self.assertEqual(
            acls.group_id, self.env.ref("collection.group_collection_user")
        )
        self.assertTrue(acls.perm_read)
        self.assertTrue(acls.perm_write)
        self.assertTrue(acls.perm_create)
        self.assertTrue(acls.perm_unlink)
        self._assert_global_company_rule("collection.sheet")

    def _snapshot_vals(self, voucher, **extra):
        vals = {
            "voucher_id": voucher.id,
            "revision": 1,
            "reviewer_id": self.internal_user.id,
            "reviewed_at": "2026-04-01 12:00:00",
            "decision": "approved",
            "document_type": voucher.document_type,
            "amount": voucher.amount,
        }
        vals.update(extra)
        return vals

    def test_snapshot_acl_read_and_gated_create(self):
        """Collections Users read history; create needs collection_review_snapshot."""
        voucher = (
            self.env["collection.voucher"]
            .with_user(self.internal_user)
            .create(self._voucher_vals(customer_identification="ACL-SNAP"))
        )
        Snapshot = self.env["collection.voucher.review.snapshot"].with_user(
            self.internal_user
        )
        with self.assertRaises(UserError):
            Snapshot.create(self._snapshot_vals(voucher))
        with privileged("collection_review_snapshot"):
            snap = Snapshot.create(self._snapshot_vals(voucher))
        self.assertTrue(snap.id)
        self.assertEqual(snap.voucher_id, voucher)
        self.assertEqual(snap.revision, 1)
        read = Snapshot.browse(snap.id).read(["revision", "decision"])
        self.assertEqual(read[0]["revision"], 1)
        self.assertEqual(read[0]["decision"], "approved")

    def test_snapshot_write_unlink_denied_and_portal_denied(self):
        """Client write/unlink MUST be denied; portal MUST be denied; no sudo/groups."""
        voucher = self.env["collection.voucher"].create(
            self._voucher_vals(customer_identification="ACL-SNAP-DENY")
        )
        Snapshot = self.env["collection.voucher.review.snapshot"]
        with privileged("collection_review_snapshot"):
            snap = Snapshot.create(
                self._snapshot_vals(voucher, reviewer_id=self.env.user.id)
            )
        with self.assertRaises(UserError):
            snap.write({"amount": 1.0})
        with self.assertRaises(UserError):
            snap.unlink()
        self.assertTrue(snap.exists())
        self.assertAlmostEqual(snap.amount, voucher.amount, places=2)

        PortalSnap = Snapshot.with_user(self.portal_user)
        with self.assertRaises(AccessError):
            PortalSnap.browse(snap.id).read(["revision"])
        with self.assertRaises(AccessError):
            with privileged("collection_review_snapshot"):
                PortalSnap.create(
                    self._snapshot_vals(
                        voucher, revision=2, reviewer_id=self.portal_user.id
                    )
                )

        acls = self.env["ir.model.access"].search(
            [("model_id.model", "=", "collection.voucher.review.snapshot")]
        )
        self.assertEqual(len(acls), 1)
        self.assertEqual(
            acls.group_id, self.env.ref("collection.group_collection_user")
        )
        self.assertTrue(acls.perm_read)
        self.assertTrue(acls.perm_create)
        self.assertFalse(acls.perm_write)
        self.assertFalse(acls.perm_unlink)
        self._assert_global_company_rule("collection.voucher.review.snapshot")
        snapshot_cls = type(self.env["collection.voucher.review.snapshot"])
        voucher_cls = type(self.env["collection.voucher"])
        sources = [
            inspect.getsource(snapshot_cls.create),
            inspect.getsource(snapshot_cls.write),
            inspect.getsource(snapshot_cls._unlink_forbidden),
            inspect.getsource(voucher_cls._append_review_snapshot),
        ]
        for source in sources:
            code_lines = [
                line
                for line in source.splitlines()
                if not line.lstrip().startswith("#")
            ]
            code = "\n".join(code_lines)
            self.assertNotIn(".sudo(", code)
            self.assertNotIn("sudo()", code)

    def test_voucher_acl_internal_group_and_company_rule(self):
        """Vouchers use one Collections User ACL row plus a global company rule."""
        acls = self.env["ir.model.access"].search(
            [("model_id.model", "=", "collection.voucher")]
        )
        self.assertEqual(len(acls), 1)
        self.assertEqual(
            acls.group_id, self.env.ref("collection.group_collection_user")
        )
        self.assertTrue(acls.perm_read)
        self.assertTrue(acls.perm_write)
        self.assertTrue(acls.perm_create)
        self.assertTrue(acls.perm_unlink)
        self._assert_global_company_rule("collection.voucher")

    def test_catalog_acl_read_only_with_manager_group(self):
        """The shared catalog stays read-only, including for managers.

        Administrators read it too: creating a company seeds its allowed types.
        """
        acls = self.env["ir.model.access"].search(
            [("model_id.model", "=", "collection.document.type")]
        )
        self.assertEqual(
            acls.group_id,
            self.env.ref("collection.group_collection_user")
            | self.env.ref("base.group_system"),
        )
        for acl in acls:
            with self.subTest(group=acl.group_id.name):
                self.assertTrue(acl.perm_read)
                self.assertFalse(acl.perm_write)
                self.assertFalse(acl.perm_create)
                self.assertFalse(acl.perm_unlink)
        self.assertFalse(
            self.env["ir.rule"].search(
                [("model_id.model", "=", "collection.document.type")]
            )
        )
        groups = self.env["ir.model.data"].search(
            [("module", "=", "collection"), ("model", "=", "res.groups")]
        )
        self.assertEqual(
            sorted(groups.mapped("name")),
            ["group_collection_manager", "group_collection_user"],
        )

    def test_voucher_company_id_required_defaults_to_env_company(self):
        field = self.env["collection.voucher"]._fields["company_id"]
        self.assertTrue(field.required)
        voucher = self.env["collection.voucher"].create(
            self._voucher_vals(customer_identification="CO-REQ-V")
        )
        self.assertEqual(voucher.company_id, self.env.company)

    def test_sheet_company_id_required_defaults_to_env_company(self):
        field = self.env["collection.sheet"]._fields["company_id"]
        self.assertTrue(field.required)
        sheet = self.env["collection.sheet"].create(self._sheet_vals())
        self.assertEqual(sheet.company_id, self.env.company)

    def test_snapshot_company_id_related_stored_from_voucher(self):
        field = self.env["collection.voucher.review.snapshot"]._fields["company_id"]
        self.assertTrue(field.required)
        self.assertEqual(field.related, "voucher_id.company_id")
        self.assertTrue(field.store)
        voucher = self.env["collection.voucher"].create(
            self._voucher_vals(customer_identification="CO-REQ-SNAP")
        )
        with privileged("collection_review_snapshot"):
            snap = self.env["collection.voucher.review.snapshot"].create(
                self._snapshot_vals(voucher, reviewer_id=self.env.user.id)
            )
        self.assertEqual(snap.company_id, voucher.company_id)
        self.assertEqual(snap.company_id, self.env.company)

    def test_allowed_company_voucher_sheet_snapshot_visible(self):
        """Happy path: allowed-company user can read A's voucher, sheet, snapshot."""
        self._restrict_user_to_company(self.internal_user, self.env.company)
        sheet = (
            self.env["collection.sheet"]
            .with_user(self.internal_user)
            .create(self._sheet_vals())
        )
        voucher = (
            self.env["collection.voucher"]
            .with_user(self.internal_user)
            .create(
                self._voucher_vals(
                    customer_identification="SHOW-A-VOUCHER",
                    sheet_id=sheet.id,
                )
            )
        )
        with privileged("collection_review_snapshot"):
            snap = (
                self.env["collection.voucher.review.snapshot"]
                .with_user(self.internal_user)
                .create(self._snapshot_vals(voucher))
            )
        Voucher = self.env["collection.voucher"].with_user(self.internal_user)
        Sheet = self.env["collection.sheet"].with_user(self.internal_user)
        Snapshot = self.env["collection.voucher.review.snapshot"].with_user(
            self.internal_user
        )
        self.assertEqual(Voucher.search([("id", "=", voucher.id)]), voucher)
        self.assertEqual(voucher.company_id, self.env.company)
        self.assertTrue(Voucher.browse(voucher.id).read(["name"])[0]["name"])
        self.assertEqual(Sheet.search([("id", "=", sheet.id)]), sheet)
        self.assertEqual(sheet.company_id, self.env.company)
        self.assertTrue(Sheet.browse(sheet.id).read(["name"])[0]["name"])
        self.assertEqual(Snapshot.search([("id", "=", snap.id)]), snap)
        self.assertEqual(snap.company_id, voucher.company_id)
        self.assertEqual(Snapshot.browse(snap.id).read(["revision"])[0]["revision"], 1)

    def test_other_company_vouchers_hidden(self):
        company_b = self._create_company("Hide Voucher Co B")
        self._restrict_user_to_company(self.internal_user, self.env.company)
        voucher_b = self.env["collection.voucher"].create(
            self._voucher_vals(
                customer_identification="HIDE-B-VOUCHER",
                company_id=company_b.id,
            )
        )
        self.assertEqual(voucher_b.company_id, company_b)
        self._assert_hidden_from_user(self.internal_user, voucher_b, ["name", "id"])

    def test_other_company_sheets_hidden(self):
        company_b = self._create_company("Hide Sheet Co B")
        self._restrict_user_to_company(self.internal_user, self.env.company)
        sheet_b = self.env["collection.sheet"].create(
            self._sheet_vals(company_id=company_b.id)
        )
        self.assertEqual(sheet_b.company_id, company_b)
        self._assert_hidden_from_user(self.internal_user, sheet_b, ["name", "id"])

    def test_other_company_snapshots_hidden(self):
        company_b = self._create_company("Hide Snapshot Co B")
        self._restrict_user_to_company(self.internal_user, self.env.company)
        voucher_b = self.env["collection.voucher"].create(
            self._voucher_vals(
                customer_identification="HIDE-B-SNAP",
                company_id=company_b.id,
            )
        )
        with privileged("collection_review_snapshot"):
            snap_b = self.env["collection.voucher.review.snapshot"].create(
                self._snapshot_vals(voucher_b, reviewer_id=self.env.user.id)
            )
        self.assertEqual(snap_b.company_id, company_b)
        self._assert_hidden_from_user(self.internal_user, snap_b, ["revision", "id"])

    def _enable_seller_deposit_type(self, company=None):
        catalog = self.env.ref("collection.document_type_seller_deposit")
        (company or self.env.company).write(
            {"allowed_document_type_ids": [Command.link(catalog.id)]}
        )
        return catalog

    def _cash_replacement_records(self):
        """Open-sheet cash receipt plus same-sheet seller_deposit (not allocated)."""
        seller = ensure_enabled_seller(self.env, self.internal_user)
        partner = dummy_customer_partner(self.env, customer="ACL-REPL")
        sheet = self.env["collection.sheet"].create(
            {
                "seller_id": seller.id,
                "company_id": self.env.company.id,
            }
        )
        cash = self.env["collection.voucher"].create(
            {
                "partner_id": partner.id,
                "document_type": "cash",
                "seller_id": seller.id,
                "sheet_id": sheet.id,
                "amount": 100.0,
            }
        )
        allocation = self.env["collection.allocation"].create(
            {
                "sheet_id": sheet.id,
                "partner_id": partner.id,
                "voucher_ids": [Command.set(cash.ids)],
            }
        )
        receipt = self.env["collection.receipt"].create(
            {
                "allocation_id": allocation.id,
                "document_kind": "invoice",
            }
        )
        self._enable_seller_deposit_type()
        deposit = self.env["collection.voucher"].create(
            {
                "document_type": "seller_deposit",
                "seller_id": seller.id,
                "sheet_id": sheet.id,
                "amount": 50.0,
                "voucher_number": "SD-ACL",
                "voucher_date": "2026-09-08",
            }
        )
        return allocation, receipt, cash, deposit

    def _replacement_vals(self, receipt, cash, deposit, **extra):
        vals = {
            "receipt_id": receipt.id,
            "cash_voucher_id": cash.id,
            "deposit_voucher_id": deposit.id,
            "amount": extra.pop("amount", 10.0),
            "direction": extra.pop("direction", "replace"),
            "created_by": extra.pop("created_by", self.env.user.id),
            "created_at": extra.pop("created_at", "2026-09-01 12:00:00"),
        }
        vals.update(extra)
        return vals

    def test_cash_replacement_acl_1_0_1_0_and_company_rule(self):
        """Ledger MUST be Collections User 1,0,1,0 with a global company ir.rule."""
        acls = self.env["ir.model.access"].search(
            [("model_id.model", "=", "collection.cash.replacement")]
        )
        self.assertEqual(len(acls), 1)
        self.assertEqual(
            acls.group_id, self.env.ref("collection.group_collection_user")
        )
        self.assertTrue(acls.perm_read)
        self.assertTrue(acls.perm_create)
        self.assertFalse(acls.perm_write)
        self.assertFalse(acls.perm_unlink)
        self._assert_global_company_rule("collection.cash.replacement")
        _allocation, receipt, cash, deposit = self._cash_replacement_records()
        Replacement = self.env["collection.cash.replacement"].with_user(
            self.internal_user
        )
        with self.assertRaises(UserError):
            Replacement.create(self._replacement_vals(receipt, cash, deposit))
        with privileged("collection_cash_replacement"):
            row = Replacement.create(
                self._replacement_vals(
                    receipt, cash, deposit, created_by=self.internal_user.id
                )
            )
        self.assertTrue(row.id)
        self.assertEqual(row.direction, "replace")
        self.assertEqual(row.company_id, self.env.company)
        read = Replacement.browse(row.id).read(["amount", "direction"])
        self.assertEqual(read[0]["direction"], "replace")
        self.assertAlmostEqual(read[0]["amount"], 10.0, places=2)

    def test_cash_replacement_write_refused(self):
        """Existing replacement write MUST refuse and leave stored fields."""
        _allocation, receipt, cash, deposit = self._cash_replacement_records()
        with privileged("collection_cash_replacement"):
            row = self.env["collection.cash.replacement"].create(
                self._replacement_vals(receipt, cash, deposit, amount=25.0)
            )
        with self.assertRaises(UserError):
            row.write({"amount": 1.0})
        self.assertAlmostEqual(row.amount, 25.0, places=2)
        self.assertEqual(row.direction, "replace")
        self.assertEqual(row.cash_voucher_id, cash)
        self.assertEqual(row.deposit_voucher_id, deposit)

    def test_connector_acl_user_read_system_write_rows(self):
        """Connectors: Collections User read; systems and managers have CRUD."""
        acls = self.env["ir.model.access"].search(
            [("model_id.model", "=", "collection.connector")]
        )
        self.assertEqual(len(acls), 3)
        user_group = self.env.ref("collection.group_collection_user")
        system_group = self.env.ref("base.group_system")
        user_acl = acls.filtered(lambda acl: acl.group_id == user_group)
        system_acl = acls.filtered(lambda acl: acl.group_id == system_group)
        self.assertEqual(len(user_acl), 1)
        self.assertTrue(user_acl.perm_read)
        self.assertFalse(user_acl.perm_write)
        self.assertFalse(user_acl.perm_create)
        self.assertFalse(user_acl.perm_unlink)
        self.assertEqual(len(system_acl), 1)
        self.assertTrue(system_acl.perm_read)
        self.assertTrue(system_acl.perm_write)
        self.assertTrue(system_acl.perm_create)
        self.assertTrue(system_acl.perm_unlink)
        manager_group = self.env.ref("collection.group_collection_manager")
        manager_acl = acls.filtered(lambda acl: acl.group_id == manager_group)
        self.assertEqual(len(manager_acl), 1)
        self.assertTrue(manager_acl.perm_read)
        self.assertTrue(manager_acl.perm_write)
        self.assertTrue(manager_acl.perm_create)
        self.assertTrue(manager_acl.perm_unlink)

    def test_internal_user_reads_but_cannot_write_connector(self):
        connector = self.env["collection.connector"].create(
            {"name": "ACL RW Connector"}
        )
        Connector = self.env["collection.connector"].with_user(self.internal_user)
        self.assertEqual(Connector.search([("id", "=", connector.id)]), connector)
        self.assertEqual(
            Connector.browse(connector.id).read(["name"])[0]["name"],
            "ACL RW Connector",
        )
        with self.assertRaises(AccessError):
            Connector.create({"name": "ACL RW Nope"})
        with self.assertRaises(AccessError):
            Connector.browse(connector.id).write({"name": "ACL RW Nope"})
        with self.assertRaises(AccessError):
            Connector.browse(connector.id).unlink()

    def test_system_user_can_create_write_unlink_connector(self):
        system_user = self._create_user("collection_system", "base.group_system")
        Connector = self.env["collection.connector"].with_user(system_user)
        connector = Connector.create({"name": "System Write Connector"})
        self.assertTrue(connector.id)
        connector.write({"name": "System Write Connector Upd"})
        self.assertEqual(connector.name, "System Write Connector Upd")
        connector_id = connector.id
        connector.unlink()
        self.assertFalse(Connector.browse(connector_id).exists())

    def test_portal_user_connector_denied(self):
        acls = self.env["ir.model.access"].search(
            [("model_id.model", "=", "collection.connector")]
        )
        self.assertTrue(acls, "collection.connector MUST have ACL rows")
        connector = self.env["collection.connector"].create(
            {"name": "Portal Deny Connector"}
        )
        Connector = self.env["collection.connector"].with_user(self.portal_user)
        with self.assertRaises(AccessError):
            Connector.create({"name": "Portal Nope"})
        with self.assertRaises(AccessError):
            Connector.browse(connector.id).read(["name"])
        with self.assertRaises(AccessError):
            Connector.browse(connector.id).write({"name": "Nope"})
        with self.assertRaises(AccessError):
            Connector.browse(connector.id).unlink()

    def test_other_company_connectors_hidden(self):
        self._assert_global_company_rule("collection.connector")
        company_b = self._create_company("Hide Connector Co B")
        self._restrict_user_to_company(self.internal_user, self.env.company)
        connector_a = self.env["collection.connector"].create(
            {"name": "Show Connector Co A"}
        )
        connector_b = self.env["collection.connector"].create(
            {
                "name": "Hide Connector Co B",
                "company_id": company_b.id,
            }
        )
        self.assertEqual(connector_b.company_id, company_b)
        Connector = self.env["collection.connector"].with_user(self.internal_user)
        self.assertEqual(Connector.search([("id", "=", connector_a.id)]), connector_a)
        self._assert_hidden_from_user(self.internal_user, connector_b, ["name", "id"])
