# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from base64 import b64decode
from datetime import date

from lxml import etree

from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import TransactionCase

from odoo.addons.collection.models.collection_common import privileged

from .test_collection_payment import (
    PNG_B64,
    dummy_customer_partner,
    ensure_enabled_seller,
    post_voucher_proof,
)


class TestCollectionApprovedVoucher(TransactionCase):
    """An approved voucher keeps the money facts Document Review approved."""

    def setUp(self):
        super().setUp()
        self.env.company.write({"document_review_enabled": True})
        self.seller = ensure_enabled_seller(self.env)
        self.sheet = self.env["collection.sheet"].create({"seller_id": self.seller.id})
        self.partner = dummy_customer_partner(self.env, customer="CUST-APPROVED")

    def _voucher(self, amount=1000.0, **extra):
        vals = {
            "partner_id": self.partner.id,
            "document_type": "bank_transfer",
            "amount": amount,
            "seller_id": self.seller.id,
            "sheet_id": self.sheet.id,
            "from_account": "FROM-1",
            "to_account": "TO-1",
            "voucher_number": f"VN-{self._testMethodName}",
            "voucher_date": date(2026, 1, 10),
        }
        vals.update(extra)
        voucher = self.env["collection.voucher"].create(vals)
        post_voucher_proof(voucher, "proof.png", PNG_B64)
        voucher.action_validate_seller()
        return voucher

    def _approved(self, amount=1000.0, **extra):
        voucher = self._voucher(amount=amount, **extra)
        voucher.action_review_approve(self.sheet.id, {})
        self.assertEqual(voucher.state, "validated_collections")
        return voucher

    def _replace_proof(self, voucher):
        replacement = self.env["ir.attachment"].create(
            {
                "name": "proof-2.png",
                "raw": b64decode(PNG_B64),
                "res_model": "collection.voucher",
                "res_id": voucher.id,
            }
        )
        voucher.write({"message_main_attachment_id": replacement.id})
        return replacement

    def _allocate_with_value(self, voucher, value_amount):
        allocation = self.env["collection.allocation"].create(
            {
                "sheet_id": self.sheet.id,
                "partner_id": voucher.partner_id.id,
                "voucher_ids": [Command.set(voucher.ids)],
                "line_ids": [
                    Command.create(
                        {
                            "external_invoice_id": f"INV-{self._testMethodName}",
                            "invoice_number": "A-1",
                            "invoice_balance": value_amount,
                            "amount_applied": 0.0,
                        }
                    )
                ],
            }
        )
        receipt = self.env["collection.receipt"].create(
            {"allocation_id": allocation.id, "document_kind": "invoice"}
        )
        self.env["collection.receipt.value"].create(
            {"receipt_id": receipt.id, "voucher_id": voucher.id, "amount": value_amount}
        )
        return allocation

    def test_raising_the_amount_of_an_approved_voucher_is_refused(self):
        """1000 -> 10000 on an approved voucher MUST NOT pass silently."""
        voucher = self._approved(amount=1000.0)
        reviewer = voucher.reviewed_by
        with self.assertRaises(UserError) as error:
            voucher.write({"amount": 10000.0})
        self.assertIn("Document Review", str(error.exception))
        self.assertEqual(voucher.amount, 1000.0)
        self.assertEqual(voucher.state, "validated_collections")
        self.assertEqual(voucher.reviewed_by, reviewer)

    def test_every_money_field_of_an_approved_voucher_is_locked(self):
        """Each money-relevant business field MUST refuse a new value."""
        other_partner = dummy_customer_partner(self.env, customer="CUST-APPROVED-2")
        voucher = self._approved()
        changes = {
            "amount": 1.0,
            "document_type": "cash_deposit",
            "from_account": "FROM-2",
            "to_account": "TO-2",
            "voucher_number": "VN-OTHER",
            "voucher_date": date(2026, 1, 11),
            "retention_kind": "iva",
            "partner_id": other_partner.id,
        }
        for name, value in changes.items():
            with self.subTest(field=name), self.assertRaises(UserError):
                voucher.write({name: value})
        self.assertEqual(voucher.amount, 1000.0)
        self.assertEqual(voucher.partner_id, self.partner)
        self.assertEqual(voucher.from_account, "FROM-1")

    def test_check_fields_of_an_approved_check_are_locked(self):
        """Check data (number, bank, type, dates) MUST stay as approved."""
        voucher = self._approved(
            document_type="check",
            voucher_number=False,
            check_number="CHK-APPROVED",
            check_bank="Bank A",
            check_type="common",
            check_issue_date=date(2026, 1, 5),
            check_payment_date=date(2026, 1, 20),
        )
        changes = {
            "check_number": "CHK-OTHER",
            "check_bank": "Bank B",
            "check_type": "deferred",
            "check_issue_date": date(2026, 1, 6),
            "check_payment_date": date(2026, 1, 21),
        }
        for name, value in changes.items():
            with self.subTest(field=name), self.assertRaises(UserError):
                voucher.write({name: value})
        self.assertEqual(voucher.check_number, "CHK-APPROVED")

    def test_rewriting_the_same_values_still_passes(self):
        """A form save that resends unchanged values MUST NOT be refused."""
        voucher = self._approved()
        voucher.write(
            {
                "amount": 1000.0,
                "partner_id": self.partner.id,
                "from_account": "FROM-1",
                "voucher_date": "2026-01-10",
            }
        )
        self.assertEqual(voucher.state, "validated_collections")

    def test_clearing_the_proof_of_an_approved_voucher_is_refused(self):
        """An approval MUST NOT outlive the proof it was given against."""
        voucher = self._approved()
        proof = voucher.message_main_attachment_id
        with self.assertRaises(UserError):
            voucher.write({"message_main_attachment_id": False})
        self.assertEqual(voucher.message_main_attachment_id, proof)

    def test_replacing_the_proof_reopens_review_and_unlocks(self):
        """The existing path back to review MUST keep working end to end."""
        voucher = self._approved()
        self._replace_proof(voucher)
        self.assertEqual(voucher.state, "validated_seller")
        self.assertFalse(voucher.reviewed_by)
        voucher.write({"amount": 900.0})
        voucher.action_review_approve(self.sheet.id, {"amount": 950.0})
        self.assertEqual(voucher.amount, 950.0)
        self.assertEqual(voucher.state, "validated_collections")

    def test_document_review_approve_still_corrects_the_amount(self):
        """Approve applies the reviewer's correction on a validated_seller voucher."""
        voucher = self._voucher(amount=1000.0)
        voucher.action_review_approve(self.sheet.id, {"amount": 990.0})
        self.assertEqual(voucher.amount, 990.0)
        self.assertEqual(voucher.state, "validated_collections")

    def test_audited_server_flows_are_not_blocked(self):
        """Only server code inside the audited scope passes the lock."""
        voucher = self._approved()
        with privileged("collection_audited_state"):
            voucher.write({"amount": 999.0})
        self.assertEqual(voucher.amount, 999.0)

    def test_lowering_the_amount_below_receipt_values_is_refused(self):
        """Receipt values MUST NOT end up above the voucher amount."""
        voucher = self._voucher(amount=100.0)
        self._allocate_with_value(voucher, 100.0)
        with self.assertRaises(ValidationError):
            voucher.write({"amount": 60.0})
        self.assertEqual(voucher.amount, 100.0)

    def test_review_correction_below_receipt_values_is_refused(self):
        """Approve cannot lower the amount under the voucher's receipt values."""
        voucher = self._voucher(amount=100.0)
        self._allocate_with_value(voucher, 100.0)
        with self.assertRaises(ValidationError):
            voucher.action_review_approve(self.sheet.id, {"amount": 60.0})
        self.assertEqual(voucher.amount, 100.0)
        self.assertEqual(voucher.state, "validated_seller")

    def test_lowering_the_amount_down_to_receipt_values_passes(self):
        """Triangulation: an amount equal to the receipt values is fine."""
        voucher = self._voucher(amount=100.0)
        self._allocate_with_value(voucher, 80.0)
        voucher.write({"amount": 80.0})
        self.assertEqual(voucher.amount, 80.0)

    def test_form_marks_money_fields_readonly_once_approved(self):
        """The form MUST mirror the lock instead of failing on save."""
        arch = self.env["collection.voucher"].get_view(
            self.env.ref("collection.view_collection_voucher_form").id, "form"
        )["arch"]
        root = etree.fromstring(arch)
        locked = (
            "partner_id",
            "document_type",
            "amount",
            "from_account",
            "to_account",
            "to_account_bank_id",
            "voucher_number",
            "voucher_date",
            "check_number",
            "check_bank",
            "check_type",
            "check_issue_date",
            "check_payment_date",
        )
        page = root.xpath("//page[@string='Current']")[0]
        for name in locked:
            with self.subTest(field=name):
                scope = root if name == "partner_id" else page
                node = scope.xpath(f".//field[@name='{name}']")[0]
                self.assertIn("validated_collections", node.get("readonly") or "", name)
