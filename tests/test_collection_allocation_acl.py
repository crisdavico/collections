# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import inspect
from pathlib import Path

from odoo.exceptions import AccessError, UserError
from odoo.fields import Command
from odoo.tests import TransactionCase

from .test_collection_payment import dummy_customer_partner, ensure_enabled_seller


def _source_without_comments(method):
    code_lines = [
        line
        for line in inspect.getsource(method).splitlines()
        if not line.lstrip().startswith("#")
    ]
    return "\n".join(code_lines)


class TestCollectionAllocationAcl(TransactionCase):
    """RED: allocation/line CRUD ACL, revision 1,0,1,1, parent-unlink, company
    ir.rule.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.internal_user = cls._create_user("alloc_acl_internal", "base.group_user")
        cls.portal_user = cls._create_user("alloc_acl_portal", "base.group_portal")

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

    def _assert_acl(self, model_name, perms):
        acls = self.env["ir.model.access"].search([("model_id.model", "=", model_name)])
        self.assertEqual(len(acls), 1, f"{model_name} must have one ACL row")
        self.assertEqual(acls.group_id, self.env.ref("base.group_user"))
        self.assertEqual(bool(acls.perm_read), perms[0])
        self.assertEqual(bool(acls.perm_write), perms[1])
        self.assertEqual(bool(acls.perm_create), perms[2])
        self.assertEqual(bool(acls.perm_unlink), perms[3])

    def _create_sheet(self, user=None, company=None):
        user = user or self.internal_user
        company = company or self.env.company
        ensure_enabled_seller(self.env, user, company=company)
        return self.env["collection.sheet"].create(
            {"seller_id": user.id, "company_id": company.id}
        )

    def _create_allocation(self, user=None, company=None, partner=None):
        user = user or self.internal_user
        company = company or self.env.company
        sheet = self._create_sheet(user=user, company=company)
        partner = partner or dummy_customer_partner(
            self.env, customer=f"ALLOC-ACL-{company.id}"
        )
        return self.env["collection.allocation"].create(
            {
                "sheet_id": sheet.id,
                "partner_id": partner.id,
            }
        )

    def _add_line(self, allocation, external_invoice_id, amount=1.0):
        voucher = self.env["collection.voucher"].create(
            {
                "partner_id": allocation.partner_id.id,
                "document_type": "bank_transfer",
                "seller_id": allocation.sheet_id.seller_id.id,
                "sheet_id": allocation.sheet_id.id,
                "company_id": allocation.company_id.id,
                "amount": amount,
                "document_id": f"DOC-{external_invoice_id}",
            }
        )
        allocation.write(
            {
                "voucher_ids": [Command.link(voucher.id)],
                "line_ids": [
                    Command.create(
                        {
                            "external_invoice_id": external_invoice_id,
                            "invoice_number": external_invoice_id,
                            "invoice_balance": amount,
                            "amount_applied": amount,
                        }
                    )
                ],
            }
        )
        return allocation.line_ids.filtered(
            lambda line: line.external_invoice_id == external_invoice_id
        )

    def _revision_vals(self, allocation, **extra):
        vals = {
            "allocation_id": allocation.id,
            "revision": 1,
            "request_id": extra.pop("request_id", f"req-acl-{allocation.id}"),
            "content_hash": "hash",
            "confirmed_by": extra.pop("confirmed_by", self.env.user.id),
            "confirmed_at": "2026-09-01 12:00:00",
        }
        vals.update(extra)
        return vals

    def test_debt_picker_acl_full_crud(self):
        """Picker transients MUST be 1,1,1,1 for base.group_user."""
        self._assert_acl("collection.allocation.debt.picker", (1, 1, 1, 1))
        self._assert_acl("collection.allocation.debt.candidate", (1, 1, 1, 1))
        allocation = self._create_allocation()
        Picker = self.env["collection.allocation.debt.picker"].with_user(
            self.internal_user
        )
        picker = Picker.create({"allocation_id": allocation.id})
        self.assertTrue(picker.id)
        self.assertEqual(picker.allocation_id, allocation)
        PortalPicker = self.env["collection.allocation.debt.picker"].with_user(
            self.portal_user
        )
        with self.assertRaises(AccessError):
            PortalPicker.create({"allocation_id": allocation.id})

    def test_allocation_and_line_acl_full_crud(self):
        """allocation and line MUST be 1,1,1,1 for base.group_user."""
        self._assert_acl("collection.allocation", (1, 1, 1, 1))
        self._assert_acl("collection.allocation.line", (1, 1, 1, 1))
        Alloc = self.env["collection.allocation"].with_user(self.internal_user)
        sheet = self._create_sheet()
        partner = dummy_customer_partner(self.env, customer="ALLOC-ACL-CRUD")
        voucher = self.env["collection.voucher"].create(
            {
                "partner_id": partner.id,
                "document_type": "bank_transfer",
                "seller_id": sheet.seller_id.id,
                "sheet_id": sheet.id,
                "amount": 10.0,
            }
        )
        allocation = Alloc.create(
            {
                "sheet_id": sheet.id,
                "partner_id": partner.id,
                "voucher_ids": [Command.set(voucher.ids)],
            }
        )
        self.assertTrue(allocation.id)
        line = (
            self.env["collection.allocation.line"]
            .with_user(self.internal_user)
            .create(
                {
                    "allocation_id": allocation.id,
                    "external_invoice_id": "INV-ACL",
                    "invoice_number": "N-1",
                    "invoice_balance": 10.0,
                    "amount_applied": 10.0,
                }
            )
        )
        self.assertTrue(line.id)
        line.write({"invoice_number": "N-1b"})
        self.assertEqual(line.invoice_number, "N-1b")
        line.unlink()
        self.assertFalse(line.exists())
        allocation_id = allocation.id
        allocation.unlink()
        self.assertFalse(Alloc.browse(allocation_id).exists())

    def test_revision_acl_read_create_unlink_no_write(self):
        """revision MUST be 1,0,1,1; create gated; write denied; direct unlink
        UserError.
        """
        self._assert_acl("collection.allocation.revision", (1, 0, 1, 1))
        allocation = self._create_allocation()
        Revision = self.env["collection.allocation.revision"].with_user(
            self.internal_user
        )
        with self.assertRaises(UserError):
            Revision.create(self._revision_vals(allocation))
        rev = Revision.with_context(collection_allocation_revision=True).create(
            self._revision_vals(allocation, confirmed_by=self.internal_user.id)
        )
        self.assertTrue(rev.id)
        read = Revision.browse(rev.id).read(["request_id", "revision"])
        self.assertEqual(read[0]["revision"], 1)
        with self.assertRaises(UserError):
            self.env["collection.allocation.revision"].browse(rev.id).write(
                {"content_hash": "nope"}
            )
        with self.assertRaises(UserError):
            self.env["collection.allocation.revision"].browse(rev.id).unlink()
        with self.assertRaises(UserError):
            Revision.browse(rev.id).write({"content_hash": "acl-nope"})
        with self.assertRaises(UserError):
            Revision.browse(rev.id).unlink()
        self.assertTrue(rev.exists())
        self.assertTrue(allocation.exists())

    def test_parent_unlink_deletes_revisions_on_draft(self):
        """Draft parent unlink MUST delete revisions under the parent-unlink gate."""
        allocation = self._create_allocation()
        self.assertEqual(allocation.state, "draft")
        rev = (
            self.env["collection.allocation.revision"]
            .with_context(collection_allocation_revision=True)
            .create(
                self._revision_vals(
                    allocation,
                    request_id="req-parent-unlink",
                    confirmed_by=self.internal_user.id,
                )
            )
        )
        rev_id = rev.id
        allocation_id = allocation.id
        allocation.with_user(self.internal_user).unlink()
        self.assertFalse(
            self.env["collection.allocation"].browse(allocation_id).exists()
        )
        self.assertFalse(
            self.env["collection.allocation.revision"].browse(rev_id).exists()
        )

    def test_parent_unlink_refused_when_confirmed(self):
        """Confirmed parent unlink MUST be refused; revisions MUST remain."""
        allocation = self._create_allocation()
        rev = (
            self.env["collection.allocation.revision"]
            .with_context(collection_allocation_revision=True)
            .create(
                self._revision_vals(
                    allocation,
                    request_id="req-parent-confirmed",
                    confirmed_by=self.internal_user.id,
                )
            )
        )
        allocation.with_context(collection_allocation_audited_state=True).write(
            {"state": "confirmed"}
        )
        allocation_id = allocation.id
        rev_id = rev.id
        with self.assertRaises(UserError):
            allocation.with_user(self.internal_user).unlink()
        self.assertTrue(
            self.env["collection.allocation"].browse(allocation_id).exists()
        )
        self.assertTrue(
            self.env["collection.allocation.revision"].browse(rev_id).exists()
        )

    def test_portal_denied_on_allocation_models(self):
        allocation = self._create_allocation()
        line = self._add_line(allocation, "INV-PORTAL", amount=5.0)
        rev = (
            self.env["collection.allocation.revision"]
            .with_context(collection_allocation_revision=True)
            .create(self._revision_vals(allocation, request_id="req-portal"))
        )
        for record, fields in (
            (allocation, ["name", "state"]),
            (line, ["amount_applied"]),
            (rev, ["request_id"]),
        ):
            Model = self.env[record._name].with_user(self.portal_user)
            with self.assertRaises(AccessError):
                Model.browse(record.id).read(fields)

    def test_three_company_ir_rules(self):
        for model_name in (
            "collection.allocation",
            "collection.allocation.line",
            "collection.allocation.revision",
        ):
            self._assert_global_company_rule(model_name)

        self._restrict_user_to_company(self.internal_user, self.env.company)
        visible = self._create_allocation(user=self.internal_user)
        visible_line = self._add_line(visible, "INV-VIS")
        visible_rev = (
            self.env["collection.allocation.revision"]
            .with_context(collection_allocation_revision=True)
            .create(
                self._revision_vals(
                    visible,
                    request_id="req-vis",
                    confirmed_by=self.internal_user.id,
                )
            )
        )

        company_b = self._create_company("Alloc Hidden Co")
        seller_b = self._create_user("alloc_acl_seller_b", "base.group_user")
        seller_b.write(
            {
                "company_id": company_b.id,
                "company_ids": [(6, 0, [company_b.id])],
            }
        )
        hidden = self._create_allocation(user=seller_b, company=company_b)
        hidden_line = self._add_line(hidden, "INV-HID")
        hidden_rev = (
            self.env["collection.allocation.revision"]
            .with_context(collection_allocation_revision=True)
            .create(
                self._revision_vals(
                    hidden,
                    request_id="req-hid",
                    confirmed_by=seller_b.id,
                )
            )
        )

        Alloc = self.env["collection.allocation"].with_user(self.internal_user)
        self.assertTrue(Alloc.search([("id", "=", visible.id)]))
        self._assert_hidden_from_user(self.internal_user, hidden, ["name"])
        self._assert_hidden_from_user(
            self.internal_user, hidden_line, ["amount_applied"]
        )
        self._assert_hidden_from_user(self.internal_user, hidden_rev, ["request_id"])
        self.assertEqual(visible_line.company_id, self.env.company)
        self.assertEqual(visible_rev.company_id, self.env.company)

    def test_allocation_models_have_no_sudo(self):
        models_root = Path(__file__).resolve().parents[1] / "models"
        sources = [
            (models_root / name).read_text(encoding="utf-8")
            for name in (
                "collection_allocation.py",
                "collection_allocation_line.py",
                "collection_allocation_revision.py",
                "collection_voucher.py",
                "collection_sheet.py",
            )
        ]
        alloc_cls = type(self.env["collection.allocation"])
        rev_cls = type(self.env["collection.allocation.revision"])
        voucher_cls = type(self.env["collection.voucher"])
        sources.extend(
            [
                inspect.getsource(alloc_cls.create),
                inspect.getsource(alloc_cls.write),
                inspect.getsource(alloc_cls.unlink),
                inspect.getsource(rev_cls.create),
                inspect.getsource(rev_cls.write),
                inspect.getsource(rev_cls._unlink_forbidden),
                inspect.getsource(voucher_cls.write),
            ]
        )
        for source in sources:
            code_lines = [
                line
                for line in source.splitlines()
                if not line.lstrip().startswith("#")
            ]
            code = "\n".join(code_lines)
            self.assertNotIn(".sudo(", code)
            self.assertNotIn("sudo()", code)
        self.assertEqual(_source_without_comments(alloc_cls.write).count("sudo"), 0)

    def test_related_stored_company_id_on_all_three_models(self):
        alloc_field = self.env["collection.allocation"]._fields["company_id"]
        self.assertEqual(alloc_field.related, "sheet_id.company_id")
        self.assertTrue(alloc_field.store)
        self.assertTrue(alloc_field.required)
        self.assertTrue(alloc_field.precompute)
        line_field = self.env["collection.allocation.line"]._fields["company_id"]
        self.assertEqual(line_field.related, "allocation_id.company_id")
        self.assertTrue(line_field.store)
        self.assertTrue(line_field.required)
        self.assertTrue(line_field.precompute)
        rev_field = self.env["collection.allocation.revision"]._fields["company_id"]
        self.assertEqual(rev_field.related, "allocation_id.company_id")
        self.assertTrue(rev_field.store)
        self.assertTrue(rev_field.required)
        self.assertTrue(rev_field.precompute)
