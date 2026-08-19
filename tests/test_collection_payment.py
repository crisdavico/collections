# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from base64 import b64decode

from psycopg2 import IntegrityError

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

# Minimal valid payloads (base64) for MIME triangulation.
PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQ"
    "DJ/pLvAAAAAElFTkSuQmCC"
)
PDF_B64 = "JVBERi0xLjEKMSAwIG9iajw8Pj5lbmRvYmoKdHJhaWxlcjw8Pj4KJSVFT0YK"
TXT_B64 = "aGVsbG8gd29ybGQ="
INVALID_B64 = "!!!not-base64!!!"


def ensure_enabled_seller(env, seller=None, company=None):
    """Enable a seller on a company so NEW-work helper tests can create rows.

    SUPERUSER is not a valid M2M target (share domain). Default to Administrator.
    Also enable on env.company so auto-created sheets (no company_id in vals)
    pass the same helper.
    """
    seller = seller or env.ref("base.user_admin")
    company = company or env.company
    targets = company
    if company != env.company:
        targets = company | env.company
    for target in targets:
        _link_enabled_seller(env, target, seller)
    return seller


def _link_enabled_seller(env, company, seller):
    if seller in company.enabled_seller_ids:
        return
    company.write({"enabled_seller_ids": [Command.link(seller.id)]})
    company.flush_recordset(["enabled_seller_ids"])
    company.invalidate_recordset(["enabled_seller_ids"])
    if seller in company.enabled_seller_ids:
        return
    env.cr.execute(
        """
        SELECT 1
          FROM res_company_collection_enabled_seller_rel
         WHERE company_id = %s AND user_id = %s
        """,
        (company.id, seller.id),
    )
    if not env.cr.fetchone():
        env.cr.execute(
            """
            INSERT INTO res_company_collection_enabled_seller_rel
                (company_id, user_id)
            VALUES (%s, %s)
            """,
            (company.id, seller.id),
        )
    company.invalidate_recordset(["enabled_seller_ids"])


def create_internal_seller(env, login):
    """Create an internal user suitable as an enabled-seller M2M target."""
    Partner = env["res.partner"].with_context(
        tracking_disable=True,
        mail_create_nolog=True,
        mail_notrack=True,
        mail_create_nosubscribe=True,
    )
    partner_vals = {"name": login, "email": f"{login}@example.com"}
    if "autopost_bills" in Partner._fields:
        partner_vals["autopost_bills"] = "ask"
        partner = Partner.create(partner_vals)
    else:
        env.cr.execute(
            """
            SELECT 1
              FROM information_schema.columns
             WHERE table_name = 'res_partner'
               AND column_name = 'autopost_bills'
            """
        )
        if env.cr.fetchone():
            env.cr.execute(
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
            partner = Partner.browse(env.cr.fetchone()[0])
        else:
            partner = Partner.create(partner_vals)
    return (
        env["res.users"]
        .with_context(no_reset_password=True, tracking_disable=True)
        .create(
            {
                "name": login,
                "login": login,
                "email": partner_vals["email"],
                "partner_id": partner.id,
                "group_ids": [(6, 0, [env.ref("base.group_user").id])],
            }
        )
    )


def post_voucher_proof(voucher, name, datas_b64, body="Proof"):
    """Post a chatter proof file onto a voucher (designated-proof path)."""
    voucher.message_post(
        body=body,
        message_type="notification",
        attachments=[(name, b64decode(datas_b64))],
    )
    voucher.invalidate_recordset()
    return voucher.message_main_attachment_id


class TestCollectionPaymentDocumentId(TransactionCase):
    """RED/GREEN: nullable unique document_id on standalone vouchers."""

    def _voucher_vals(self, **extra):
        seller = ensure_enabled_seller(self.env)
        vals = {
            "customer_identification": "CUST-DOC",
            "document_type": "bank_transfer",
            "amount": 100.0,
            "seller_id": seller.id,
        }
        vals.update(extra)
        return vals

    def test_payment_without_document_id_ok(self):
        """UI vouchers must persist when document_id is omitted."""
        voucher = self.env["collection.voucher"].create(self._voucher_vals())
        self.assertTrue(voucher.id)
        self.assertFalse(
            voucher.document_id,
            "document_id must remain empty when not provided",
        )

    def test_multiple_payments_without_document_id_ok(self):
        """Triangulation: several NULL document_id values must coexist (PG UNIQUE)."""
        Voucher = self.env["collection.voucher"]
        first = Voucher.create(
            self._voucher_vals(customer_identification="CUST-DOC-NULL-1", amount=10.0)
        )
        second = Voucher.create(
            self._voucher_vals(customer_identification="CUST-DOC-NULL-2", amount=20.0)
        )
        self.assertTrue(first.id)
        self.assertTrue(second.id)
        self.assertFalse(first.document_id)
        self.assertFalse(second.document_id)
        self.assertNotEqual(first.id, second.id)

    def test_duplicate_non_null_document_id_raises_integrity_error(self):
        """Non-null document_id values must be unique across vouchers."""
        Voucher = self.env["collection.voucher"]
        Voucher.create(
            self._voucher_vals(
                customer_identification="CUST-DOC-DUP-1",
                document_id="DOC-UNIQUE-1",
                amount=50.0,
            )
        )
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                Voucher.create(
                    self._voucher_vals(
                        customer_identification="CUST-DOC-DUP-2",
                        document_id="DOC-UNIQUE-1",
                        amount=75.0,
                    )
                )

    def test_distinct_document_ids_ok(self):
        """Triangulation: different non-null document_id values must both persist."""
        Voucher = self.env["collection.voucher"]
        first = Voucher.create(
            self._voucher_vals(
                customer_identification="CUST-DOC-OK-A",
                document_id="DOC-A",
                amount=1.0,
            )
        )
        second = Voucher.create(
            self._voucher_vals(
                customer_identification="CUST-DOC-OK-B",
                document_id="DOC-B",
                amount=2.0,
            )
        )
        self.assertEqual(first.document_id, "DOC-A")
        self.assertEqual(second.document_id, "DOC-B")


class TestCollectionPaymentAttachment(TransactionCase):
    """RED/GREEN: optional chatter designated proof on standalone vouchers."""

    def _voucher_vals(self, **extra):
        seller = ensure_enabled_seller(self.env)
        vals = {
            "customer_identification": "CUST-ATT",
            "document_type": "bank_transfer",
            "amount": 100.0,
            "seller_id": seller.id,
        }
        vals.update(extra)
        return vals

    def _voucher_attachments(self, voucher):
        return self.env["ir.attachment"].search(
            [
                ("res_model", "=", "collection.voucher"),
                ("res_id", "=", voucher.id),
                ("res_field", "=", False),
            ]
        )

    def test_omit_attachment_persists(self):
        """Omit attachment remains valid and persists the voucher."""
        voucher = self.env["collection.voucher"].create(self._voucher_vals())
        self.assertTrue(voucher.id)
        self.assertFalse(voucher.message_main_attachment_id)
        self.assertFalse(self._voucher_attachments(voucher))

    def test_valid_png_persists_via_ir_attachment(self):
        """Valid PNG posted on chatter stores as designated proof."""
        voucher = self.env["collection.voucher"].create(
            self._voucher_vals(customer_identification="CUST-ATT-PNG")
        )
        proof = post_voucher_proof(voucher, "proof.png", PNG_B64)
        self.assertEqual(voucher.message_main_attachment_id, proof)
        self.assertEqual(proof.name, "proof.png")
        self.assertFalse(proof.res_field)
        attachments = self._voucher_attachments(voucher)
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments.datas, PNG_B64.encode())

    def test_valid_pdf_persists_via_ir_attachment(self):
        """Triangulation: valid PDF also persists as designated chatter proof."""
        voucher = self.env["collection.voucher"].create(
            self._voucher_vals(customer_identification="CUST-ATT-PDF")
        )
        proof = post_voucher_proof(voucher, "receipt.pdf", PDF_B64)
        self.assertEqual(voucher.message_main_attachment_id, proof)
        self.assertEqual(proof.name, "receipt.pdf")
        attachments = self._voucher_attachments(voucher)
        self.assertEqual(len(attachments), 1)

    def test_invalid_base64_raises_and_does_not_persist(self):
        """Invalid base64 must raise UserError and not persist a designated proof."""
        Voucher = self.env["collection.voucher"]
        before = Voucher.search_count([])
        with self.assertRaises(UserError):
            Voucher._validate_attachment_payload(INVALID_B64)
        self.assertEqual(Voucher.search_count([]), before)

    def test_non_image_non_pdf_mime_raises_and_does_not_persist(self):
        """Non-image/non-PDF detected MIME must raise UserError."""
        Voucher = self.env["collection.voucher"]
        before = Voucher.search_count([])
        with self.assertRaises(UserError):
            Voucher._validate_attachment_payload(TXT_B64)
        self.assertEqual(Voucher.search_count([]), before)

    def test_write_replace_updates_attachment(self):
        """Writing a new main attachment replaces designated proof."""
        voucher = self.env["collection.voucher"].create(
            self._voucher_vals(customer_identification="CUST-ATT-REP")
        )
        post_voucher_proof(voucher, "old.png", PNG_B64)
        replacement = self.env["ir.attachment"].create(
            {
                "name": "new.pdf",
                "raw": b64decode(PDF_B64),
                "res_model": "collection.voucher",
                "res_id": voucher.id,
            }
        )
        voucher.write({"message_main_attachment_id": replacement.id})
        self.assertEqual(voucher.message_main_attachment_id, replacement)
        self.assertEqual(voucher.message_main_attachment_id.name, "new.pdf")

    def test_write_replace_resets_approved_review_to_pending(self):
        """Replacing designated proof must reopen review and clear audit."""
        voucher = self.env["collection.voucher"].create(
            self._voucher_vals(
                customer_identification="CUST-ATT-RST",
                document_id="DOC-ATT-RST",
            )
        )
        post_voucher_proof(voucher, "old.png", PNG_B64)
        voucher.action_approve()
        self.assertEqual(voucher.state, "approved")
        replacement = self.env["ir.attachment"].create(
            {
                "name": "new.pdf",
                "raw": b64decode(PDF_B64),
                "res_model": "collection.voucher",
                "res_id": voucher.id,
            }
        )
        voucher.write({"message_main_attachment_id": replacement.id})
        self.assertEqual(voucher.state, "pending")
        self.assertFalse(voucher.reviewed_by)
        self.assertFalse(voucher.reviewed_at)
        self.assertEqual(voucher.message_main_attachment_id.name, "new.pdf")

    def test_write_replace_resets_rejected_review_to_pending(self):
        """Triangulation: replacing a rejected voucher's proof also reopens review."""
        voucher = self.env["collection.voucher"].create(
            self._voucher_vals(
                customer_identification="CUST-ATT-RST-REJ",
                document_id="DOC-ATT-RST-REJ",
            )
        )
        post_voucher_proof(voucher, "rej.png", PNG_B64)
        voucher.action_reject()
        replacement = self.env["ir.attachment"].create(
            {
                "name": "again.png",
                "raw": b64decode(PNG_B64),
                "res_model": "collection.voucher",
                "res_id": voucher.id,
            }
        )
        voucher.write({"message_main_attachment_id": replacement.id})
        self.assertEqual(voucher.state, "pending")
        self.assertFalse(voucher.reviewed_by)
        self.assertFalse(voucher.reviewed_at)

    def test_clear_attachment_empties_designated_proof(self):
        """Clearing designated proof empties message_main_attachment_id."""
        voucher = self.env["collection.voucher"].create(
            self._voucher_vals(customer_identification="CUST-ATT-CLR")
        )
        post_voucher_proof(voucher, "clear-me.png", PNG_B64)
        voucher.write({"message_main_attachment_id": False})
        self.assertFalse(voucher.message_main_attachment_id)

    def test_unlink_voucher_cascades_attachment_cleanup(self):
        """Unlinking a voucher must remove its stored attachment row."""
        voucher = self.env["collection.voucher"].create(
            self._voucher_vals(customer_identification="CUST-ATT-UNL")
        )
        proof = post_voucher_proof(voucher, "gone.png", PNG_B64)
        att_id = proof.id
        voucher.unlink()
        self.assertFalse(self.env["ir.attachment"].browse(att_id).exists())

    def test_copy_does_not_copy_attachment(self):
        """copy=False: duplicated voucher must not inherit designated proof."""
        voucher = self.env["collection.voucher"].create(
            self._voucher_vals(
                customer_identification="CUST-ATT-CPY",
                document_id="DOC-ATT-SRC",
            )
        )
        post_voucher_proof(voucher, "source.png", PNG_B64)
        clone = voucher.copy({"document_id": "DOC-ATT-CLONE"})
        self.assertTrue(clone.id)
        self.assertNotEqual(clone.id, voucher.id)
        self.assertFalse(clone.message_main_attachment_id)
        self.assertTrue(voucher.message_main_attachment_id)
        self.assertEqual(len(self._voucher_attachments(voucher)), 1)
