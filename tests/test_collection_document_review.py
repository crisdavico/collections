# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import inspect
from base64 import b64decode
from datetime import date
from pathlib import Path

from lxml import etree

from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from .common_connector import force_sheet_state
from .test_collection_payment import (
    PDF_B64,
    PNG_B64,
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
    post_voucher_proof,
)

_DOCUMENT_REVIEW_DIR = (
    Path(__file__).resolve().parents[1] / "static" / "src" / "document_review"
)


class TestCollectionDocumentReview(TransactionCase):
    """RED/GREEN: document review queue, approve, no reject RPC."""

    def setUp(self):
        super().setUp()
        self.env.company.write({"document_review_enabled": True})
        self.review_sheet = self._create_sheet()

    def _seller(self):
        return ensure_enabled_seller(self.env)

    def _voucher_vals(self, customer=None, **extra):
        seller = extra.get("seller_id") or self._seller().id
        ensure_enabled_seller(self.env, self.env["res.users"].browse(seller))
        partner = dummy_customer_partner(
            self.env, customer=customer, extra=extra, default="CUST-REV"
        )
        vals = {
            "partner_id": partner.id,
            "document_type": "bank_transfer",
            "amount": 100.0,
            "seller_id": seller,
        }
        vals.update(extra)
        if "document_id" not in vals:
            count = self.env["collection.voucher"].search_count([])
            vals["document_id"] = f"DOC-REV-{count}"
        return vals

    def _create_sheet(self, **extra):
        seller_id = extra.get("seller_id", self._seller().id)
        ensure_enabled_seller(self.env, self.env["res.users"].browse(seller_id))
        vals = {"seller_id": seller_id, **extra}
        return self.env["collection.sheet"].create(vals)

    def _other_internal_seller(self):
        return create_internal_seller(self.env, f"review_other_{self._testMethodName}")

    def _close_open_sheets(self, seller=None):
        seller_id = (seller or self._seller()).id
        opens = self.env["collection.sheet"].search(
            [("seller_id", "=", seller_id), ("state", "=", "open")]
        )
        if opens:
            force_sheet_state(opens, "closed")

    def _create_attached_voucher(self, **extra):
        extra.setdefault("attachment_filename", "proof.png")
        datas = extra.pop("attachment", PNG_B64)
        filename = extra.pop("attachment_filename")
        extra.setdefault("seller_id", self._seller().id)
        extra.setdefault("sheet_id", self.review_sheet.id)
        voucher = self.env["collection.voucher"].create(self._voucher_vals(**extra))
        post_voucher_proof(voucher, filename, datas)
        return voucher

    def _create_review_eligible_voucher(self, **extra):
        """Attached draft that seller-validates into the Document Review queue."""
        voucher = self._create_attached_voucher(**extra)
        voucher.action_validate_seller()
        return voucher

    def _replace_proof(self, voucher, name, datas_b64):
        replacement = self.env["ir.attachment"].create(
            {
                "name": name,
                "raw": b64decode(datas_b64),
                "res_model": "collection.voucher",
                "res_id": voucher.id,
            }
        )
        voucher.write({"message_main_attachment_id": replacement.id})
        return replacement

    def _neutralize_preexisting_queue(self, sheet_id=None):
        """Make pre-existing devel rows ineligible so this transaction is isolated."""
        domain = [
            ("state", "=", "validated_seller"),
            ("message_main_attachment_id", "!=", False),
            ("sheet_id", "=", sheet_id or self.review_sheet.id),
        ]
        queued = self.env["collection.voucher"].search(domain)
        if queued:
            queued.with_context(collection_audited_state=True).write(
                {"state": "validated_collections"}
            )

    def _assert_no_binary_in_payload(self, item):
        self.assertIsInstance(item, dict)
        self.assertNotIn("datas", item)
        self.assertNotIn("attachment", item)
        url = item.get("attachment_url")
        self.assertIsInstance(url, str)
        self.assertTrue(
            url.startswith("/web/content/"),
            f"attachment_url must be /web/content/{{id}}, got {url!r}",
        )
        self.assertFalse(
            url.startswith("/web/content?"),
            f"attachment_url must not use query-style Binary serving, got {url!r}",
        )
        self.assertNotIn("field=", url)
        self.assertNotIn("model=", url)
        self.assertNotIn("collection.voucher.line", url)
        self.assertNotIn("datas", url)
        self.assertNotIn("base64", url.lower())
        self.assertFalse(url.startswith("data:"))
        for value in item.values():
            rendered = str(value)
            self.assertNotIn(PNG_B64, rendered)
            self.assertNotIn(PDF_B64, rendered)
            self.assertNotIn("data:image", rendered)
            self.assertNotIn("data:application/pdf", rendered)

    def _expected_content_url(self, voucher):
        attachment = voucher.message_main_attachment_id
        self.assertTrue(attachment, "expected designated proof for content URL")
        return f"/web/content/{attachment.id}"

    def _assert_payload_from_ir_attachment(self, payload, voucher):
        attachment = voucher.message_main_attachment_id
        self.assertTrue(attachment, "queue payload requires designated proof")
        self.assertEqual(payload["attachment_filename"], attachment.name)
        self.assertEqual(payload["mimetype"], attachment.mimetype)
        self.assertEqual(payload["attachment_url"], self._expected_content_url(voucher))
        self._assert_no_binary_in_payload(payload)

    def _assert_payload_layer(self, payload, voucher, prefix):
        for name in voucher._REVIEW_EDITABLE_FIELDS:
            key = f"{prefix}_{name}"
            self.assertIn(key, payload, key)
            actual = payload[key]
            expected = voucher[key]
            if name == "amount":
                self.assertAlmostEqual(actual, expected, places=2, msg=key)
            else:
                self.assertEqual(actual, expected, key)

    def _assert_empty_payload_provenance(self, payload, voucher):
        for name in voucher._REVIEW_EDITABLE_FIELDS:
            ocr_key = f"ocr_{name}"
            seller_key = f"seller_{name}"
            self.assertIn(ocr_key, payload, ocr_key)
            self.assertIn(seller_key, payload, seller_key)
            if name == "amount":
                self.assertEqual(payload[ocr_key], 0.0, ocr_key)
                self.assertEqual(payload[seller_key], 0.0, seller_key)
            else:
                self.assertFalse(payload[ocr_key], ocr_key)
                self.assertFalse(payload[seller_key], seller_key)
            self.assertIn(name, payload, name)
            current = payload[name]
            if name == "amount" or current:
                self.assertNotEqual(
                    payload[ocr_key],
                    current,
                    f"{ocr_key} must stay empty, not copy current {name}",
                )
                self.assertNotEqual(
                    payload[seller_key],
                    current,
                    f"{seller_key} must stay empty, not copy current {name}",
                )

    def _viewer_template_xml(self):
        path = _DOCUMENT_REVIEW_DIR / "document_review_action.xml"
        return path.read_text(encoding="utf-8")

    def _viewer_template_root(self):
        return etree.fromstring(self._viewer_template_xml().encode())

    def _viewer_class_tokens(self, node):
        return " ".join(
            filter(
                None,
                [
                    node.get("class"),
                    node.get("t-attf-class"),
                    node.get("t-att-class"),
                ],
            )
        )

    def _viewer_tray_nodes(self, root):
        return [
            node
            for node in root.xpath(".//*")
            if "tray" in self._viewer_class_tokens(node).split()
        ]

    def _viewer_event_handler(self, node, *names):
        for name in names:
            value = node.get(name)
            if value:
                return value
        return ""

    def _helpers_js(self):
        return (_DOCUMENT_REVIEW_DIR / "document_review_helpers.esm.js").read_text(
            encoding="utf-8"
        )

    def _action_js(self):
        return (_DOCUMENT_REVIEW_DIR / "document_review_action.esm.js").read_text(
            encoding="utf-8"
        )

    def _validation_panel_xml(self):
        xml = self._viewer_template_xml()
        marker = 'aria-label="Validación de campos"'
        self.assertIn(marker, xml)
        return xml.split(marker, 1)[1]

    def _queue_item(self, voucher, sheet_id=None):
        payload = next(
            (
                item
                for item in self.env["collection.voucher"].get_review_queue(
                    sheet_id or self.review_sheet.id
                )
                if item["id"] == voucher.id
            ),
            None,
        )
        self.assertIsNotNone(payload, "expected voucher in review queue")
        return payload

    def _assert_seller_changed_fields(self, payload, voucher, expected):
        self.assertIn("seller_changed_fields", payload)
        changed = payload["seller_changed_fields"]
        self.assertIsInstance(changed, dict)
        self.assertEqual(changed, expected)
        order = voucher._REVIEW_EDITABLE_FIELD_ORDER
        self.assertIsInstance(order, tuple)
        self.assertEqual(set(order), set(voucher._REVIEW_EDITABLE_FIELDS))
        self.assertEqual(
            list(changed),
            [name for name in order if name in changed],
        )
        return changed

    # --- Queue eligibility + empty queue ---

    def test_queue_is_isolated_to_requested_sheet(self):
        """Queue for sheet A must not include sheet B's eligible vouchers."""
        other = self._other_internal_seller()
        self._close_open_sheets()
        sheet_a = self._create_sheet()
        sheet_b = self._create_sheet(seller_id=other.id)
        voucher_a = self._create_review_eligible_voucher(
            customer_identification="CUST-SHEET-A",
            document_id="DOC-SHEET-A",
            seller_id=self._seller().id,
            sheet_id=sheet_a.id,
        )
        voucher_b = self._create_review_eligible_voucher(
            customer_identification="CUST-SHEET-B",
            document_id="DOC-SHEET-B",
            seller_id=other.id,
            sheet_id=sheet_b.id,
        )
        queue_a = self.env["collection.voucher"].get_review_queue(sheet_a.id)
        queued_ids = [item["id"] for item in queue_a]
        self.assertEqual(queued_ids, [voucher_a.id])
        self.assertNotIn(voucher_b.id, queued_ids)
        queue_b = self.env["collection.voucher"].get_review_queue(sheet_b.id)
        self.assertEqual([item["id"] for item in queue_b], [voucher_b.id])

    def test_queue_empty_for_sheet_with_no_eligible_members(self):
        """Empty or ineligible-only OPEN sheet must return [] and ignore other
        sheets."""
        empty_sheet = self.review_sheet
        other = create_internal_seller(
            self.env, f"review_inelig_{self._testMethodName}"
        )
        ineligible_sheet = self._create_sheet(seller_id=other.id)
        unattached = self.env["collection.voucher"].create(
            self._voucher_vals(
                customer_identification="CUST-SHEET-NONE",
                document_id="DOC-SHEET-NONE",
                seller_id=other.id,
                sheet_id=ineligible_sheet.id,
            )
        )
        approved = self._create_attached_voucher(
            customer_identification="CUST-SHEET-APPR",
            document_id="DOC-SHEET-APPR",
            seller_id=other.id,
            sheet_id=ineligible_sheet.id,
        )
        approved.with_context(collection_audited_state=True).write(
            {"state": "validated_collections"}
        )
        draft_attached = self._create_attached_voucher(
            customer_identification="CUST-SHEET-DRAFT",
            document_id="DOC-SHEET-DRAFT",
            seller_id=other.id,
            sheet_id=ineligible_sheet.id,
        )
        third = create_internal_seller(self.env, f"review_third_{self._testMethodName}")
        other_sheet = self._create_sheet(seller_id=third.id)
        other_eligible = self._create_review_eligible_voucher(
            customer_identification="CUST-SHEET-OTHER",
            document_id="DOC-SHEET-OTHER",
            seller_id=third.id,
            sheet_id=other_sheet.id,
        )
        Voucher = self.env["collection.voucher"]
        self.assertEqual(empty_sheet.state, "open")
        self.assertEqual(ineligible_sheet.state, "open")
        self.assertEqual(Voucher.get_review_queue(empty_sheet.id), [])
        ineligible_queue = Voucher.get_review_queue(ineligible_sheet.id)
        self.assertEqual(ineligible_queue, [])
        self.assertNotIn(unattached.id, [item["id"] for item in ineligible_queue])
        self.assertNotIn(approved.id, [item["id"] for item in ineligible_queue])
        self.assertNotIn(draft_attached.id, [item["id"] for item in ineligible_queue])
        self.assertNotIn(other_eligible.id, [item["id"] for item in ineligible_queue])
        other_queue = Voucher.get_review_queue(other_sheet.id)
        self.assertEqual([item["id"] for item in other_queue], [other_eligible.id])

    def test_review_queue_refuses_missing_or_invalid_sheet_id(self):
        """Missing, 0, False, or unknown sheet ids must UserError, not return []."""
        Voucher = self.env["collection.voucher"]
        self._close_open_sheets()
        valid_sheet = self._create_sheet()
        self._create_review_eligible_voucher(
            customer_identification="CUST-SHEET-VALID-Q",
            document_id="DOC-SHEET-VALID-Q",
            seller_id=self._seller().id,
            sheet_id=valid_sheet.id,
        )
        with self.assertRaises(UserError):
            Voucher.get_review_queue()
        for invalid_id in (None, 0, False, valid_sheet.id + 10**6):
            with self.subTest(sheet_id=invalid_id):
                with self.assertRaises(UserError):
                    Voucher.get_review_queue(invalid_id)

    def test_review_mutations_refuse_missing_or_invalid_sheet_id(self):
        """Mutations with missing/0/False/bad sheet id must UserError without writes."""
        self._close_open_sheets()
        sheet = self._create_sheet()
        voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-SHEET-VALID-M",
            document_id="DOC-SHEET-VALID-M",
            seller_id=self._seller().id,
            sheet_id=sheet.id,
        )
        for invalid_id in (None, 0, False, sheet.id + 10**6):
            with self.subTest(sheet_id=invalid_id):
                with self.assertRaises(UserError):
                    voucher.action_review_approve(invalid_id, {"amount": 1.0})
                with self.assertRaises(UserError):
                    voucher.action_review_set_rotation(invalid_id, 90)
        self.assertFalse(hasattr(voucher, "action_review_reject"))
        self.assertEqual(voucher.state, "validated_seller")
        self.assertEqual(voucher.attachment_rotation, 0)
        self.assertAlmostEqual(voucher.amount, 100.0, places=2)

    def test_review_rpcs_refuse_non_open_sheet(self):
        """Proposal, closed, or cancelled identifiers MUST refuse, not empty-queue."""
        Voucher = self.env["collection.voucher"]
        sheet = self.review_sheet
        voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-NONOPEN",
            document_id="DOC-REV-NONOPEN",
            sheet_id=sheet.id,
        )
        for state in ("proposal", "closed", "cancelled"):
            with self.subTest(state=state):
                force_sheet_state(sheet, state)
                with self.assertRaises(UserError):
                    Voucher.get_review_queue(sheet.id)
                with self.assertRaises(UserError):
                    voucher.action_review_approve(sheet.id, {"amount": 1.0})
                with self.assertRaises(UserError):
                    voucher.action_review_set_rotation(sheet.id, 90)
                self.assertEqual(voucher.state, "validated_seller")
                self.assertEqual(voucher.attachment_rotation, 0)

    def test_review_rpcs_succeed_on_submitted_sheet(self):
        """Inverse of the 3-state freeze: submitted identifiers MUST review."""
        Voucher = self.env["collection.voucher"]
        self._close_open_sheets()
        sheet = self._create_sheet()
        rotatable = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-SUB-ROT",
            document_id="DOC-REV-SUB-ROT",
            seller_id=self._seller().id,
            sheet_id=sheet.id,
        )
        approved = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-SUB-APPR",
            document_id="DOC-REV-SUB-APPR",
            seller_id=self._seller().id,
            sheet_id=sheet.id,
        )
        force_sheet_state(sheet, "submitted")
        self.assertEqual(sheet.state, "submitted")
        queue = Voucher.get_review_queue(sheet.id)
        self.assertEqual(len(queue), 2)
        self.assertEqual({item["id"] for item in queue}, {rotatable.id, approved.id})
        rotatable.action_review_set_rotation(sheet.id, 90)
        self.assertEqual(rotatable.attachment_rotation, 90)
        approved.action_review_approve(sheet.id, {"amount": 41.0})
        self.assertEqual(approved.state, "validated_collections")
        self.assertAlmostEqual(approved.amount, 41.0, places=2)

    def test_review_queue_empty_on_submitted_sheet(self):
        """Triangulation: empty submitted queue MUST succeed, not refuse."""
        Voucher = self.env["collection.voucher"]
        self._close_open_sheets()
        sheet = self._create_sheet()
        force_sheet_state(sheet, "submitted")
        self.assertEqual(sheet.state, "submitted")
        self.assertEqual(Voucher.get_review_queue(sheet.id), [])

    def test_review_rpcs_still_succeed_on_open_sheet(self):
        """Triangulation: an open sheet identifier MUST still load the queue."""
        Voucher = self.env["collection.voucher"]
        self.assertEqual(self.review_sheet.state, "open")
        self.assertEqual(Voucher.get_review_queue(self.review_sheet.id), [])

        """Approve and rotation of a sheet B voucher with sheet A must fail."""
        other = self._other_internal_seller()
        self._close_open_sheets()
        sheet_a = self._create_sheet()
        sheet_b = self._create_sheet(seller_id=other.id)
        voucher_b = self._create_review_eligible_voucher(
            customer_identification="CUST-XSHEET-B",
            document_id="DOC-XSHEET-B",
            seller_id=other.id,
            sheet_id=sheet_b.id,
        )
        with self.assertRaises(UserError):
            voucher_b.action_review_approve(sheet_a.id, {"amount": 1.0})
        with self.assertRaises(UserError):
            voucher_b.action_review_set_rotation(sheet_a.id, 90)
        self.assertFalse(hasattr(voucher_b, "action_review_reject"))
        self.assertEqual(voucher_b.state, "validated_seller")
        self.assertEqual(voucher_b.attachment_rotation, 0)
        self.assertAlmostEqual(voucher_b.amount, 100.0, places=2)

    def test_stale_sheet_membership_mutations_are_refused(self):
        """Mutations must refuse a voucher that is no longer a member of the sheet."""
        self._close_open_sheets()
        sheet = self._create_sheet()
        voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-STALE-SHEET",
            document_id="DOC-STALE-SHEET",
            seller_id=self._seller().id,
            sheet_id=sheet.id,
        )
        voucher.write({"sheet_id": False})
        self.assertFalse(voucher.sheet_id)
        with self.assertRaises(UserError):
            voucher.action_review_approve(sheet.id, {"amount": 1.0})
        with self.assertRaises(UserError):
            voucher.action_review_set_rotation(sheet.id, 90)
        self.assertFalse(hasattr(voucher, "action_review_reject"))
        self.assertEqual(voucher.state, "validated_seller")
        self.assertEqual(voucher.attachment_rotation, 0)
        self.assertAlmostEqual(voucher.amount, 100.0, places=2)

    def test_same_sheet_mutations_succeed(self):
        """Approve and rotation succeed for a voucher on the sheet; reject is gone."""
        self._close_open_sheets()
        sheet = self._create_sheet()
        rotatable = self._create_review_eligible_voucher(
            customer_identification="CUST-SAME-ROT",
            document_id="DOC-SAME-ROT",
            seller_id=self._seller().id,
            sheet_id=sheet.id,
        )
        rotatable.action_review_set_rotation(sheet.id, 90)
        self.assertEqual(rotatable.attachment_rotation, 90)
        approved = self._create_review_eligible_voucher(
            customer_identification="CUST-SAME-APPR",
            document_id="DOC-SAME-APPR",
            seller_id=self._seller().id,
            sheet_id=sheet.id,
        )
        approved.action_review_approve(sheet.id, {"amount": 55.0})
        self.assertEqual(approved.state, "validated_collections")
        self.assertAlmostEqual(approved.amount, 55.0, places=2)
        snaps = self.env["collection.voucher.review.snapshot"].search(
            [("voucher_id", "=", approved.id)]
        )
        self.assertEqual(snaps.decision, "approved")
        self.assertNotEqual(approved.state, snaps.decision)
        leftover = self._create_review_eligible_voucher(
            customer_identification="CUST-SAME-REJ",
            document_id="DOC-SAME-REJ",
            seller_id=self._seller().id,
            sheet_id=sheet.id,
        )
        self.assertFalse(hasattr(leftover, "action_review_reject"))
        self.assertEqual(leftover.state, "validated_seller")

    def test_review_rpcs_live_on_collection_voucher(self):
        Voucher = self.env["collection.voucher"]
        self.assertTrue(hasattr(Voucher, "get_review_queue"))
        self.assertTrue(hasattr(Voucher, "action_review_approve"))
        self.assertFalse(hasattr(Voucher, "action_review_reject"))
        self.assertTrue(hasattr(Voucher, "action_review_set_rotation"))
        self.assertNotIn("collection.voucher.line", self.env)

    def test_queue_includes_only_pending_attached_vouchers(self):
        """Eligible: validated_seller AND designated proof (draft+proof is not)."""
        self._neutralize_preexisting_queue()
        Voucher = self.env["collection.voucher"]
        eligible = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-ELIG",
            document_id="DOC-REV-ELIG",
            from_account="ACC-FROM",
            to_account="ACC-TO",
            voucher_number="TRF-1",
            voucher_date=date(2026, 3, 15),
        )
        draft_attached = self._create_attached_voucher(
            customer_identification="CUST-REV-DRAFT",
            document_id="DOC-REV-DRAFT",
        )
        unattached = Voucher.create(
            self._voucher_vals(
                customer_identification="CUST-REV-NONE",
                document_id="DOC-REV-NONE",
                seller_id=self._seller().id,
                sheet_id=self.review_sheet.id,
            )
        )
        approved = self._create_attached_voucher(
            customer_identification="CUST-REV-APPR",
            document_id="DOC-REV-APPR-INELIG",
        )
        approved.with_context(collection_audited_state=True).write(
            {"state": "validated_collections"}
        )
        decided = self._create_attached_voucher(
            customer_identification="CUST-REV-DEC",
            document_id="DOC-REV-DEC",
        )
        decided.with_context(collection_audited_state=True).write(
            {"state": "validated_collections"}
        )

        queue = Voucher.get_review_queue(self.review_sheet.id)
        queued_ids = [item["id"] for item in queue]
        self.assertIn(eligible.id, queued_ids)
        self.assertNotIn(draft_attached.id, queued_ids)
        self.assertEqual(draft_attached.state, "draft")
        self.assertTrue(draft_attached.message_main_attachment_id)
        self.assertNotIn(unattached.id, queued_ids)
        self.assertNotIn(approved.id, queued_ids)
        self.assertNotIn(decided.id, queued_ids)
        state_keys = {key for key, _label in Voucher._fields["state"].selection}
        self.assertNotIn("new", state_keys)

        payload = next(item for item in queue if item["id"] == eligible.id)
        self.assertEqual(payload["voucher_id"], eligible.id)
        self.assertEqual(payload["voucher_name"], eligible.name)
        self.assertEqual(payload["document_id"], "DOC-REV-ELIG")
        self.assertEqual(payload["document_type"], "bank_transfer")
        self.assertAlmostEqual(payload["amount"], 100.0, places=2)
        self.assertEqual(payload["from_account"], "ACC-FROM")
        self.assertEqual(payload["to_account"], "ACC-TO")
        self.assertEqual(payload["voucher_number"], "TRF-1")
        self.assertEqual(payload["voucher_date"], date(2026, 3, 15))
        self.assertEqual(payload["attachment_rotation"], 0)
        self.assertEqual(payload["position"], 1)
        self.assertEqual(payload["total"], 1)
        self._assert_payload_from_ir_attachment(payload, eligible)

    def test_queue_includes_to_account_mismatch_flag(self):
        """T5: the review payload exposes to_account_mismatch for a reviewer.

        The rule that used to block saving a mismatched to_account is gone
        (OCR misreads a CBU digit; blocking would stop a real payment from
        being recorded). Document Review is where a human now checks it, so
        the flag must reach the queue payload.
        """
        self._neutralize_preexisting_queue()
        self.env["res.partner.bank"].create(
            {
                "acc_number": "0000-9999-9",
                "partner_id": self.env.company.partner_id.id,
            }
        )
        mismatched = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-MISMATCH",
            document_id="DOC-REV-MISMATCH",
            to_account="1111-0000-0",
        )
        matched = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-MATCH",
            document_id="DOC-REV-MATCH",
            to_account="0000-9999-9",
        )
        queue = self.env["collection.voucher"].get_review_queue(self.review_sheet.id)
        payloads = {item["id"]: item for item in queue}
        self.assertTrue(payloads[mismatched.id]["to_account_mismatch"])
        self.assertFalse(payloads[matched.id]["to_account_mismatch"])

    def test_queue_empty_when_no_eligible_vouchers(self):
        """Triangulation: ineligible-only setup yields an empty queue."""
        self._neutralize_preexisting_queue()
        Voucher = self.env["collection.voucher"]
        Voucher.create(
            self._voucher_vals(
                customer_identification="CUST-REV-EMPTY",
                document_id="DOC-REV-EMPTY-NONE",
                seller_id=self._seller().id,
                sheet_id=self.review_sheet.id,
            )
        )
        attached = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-EMPTY-ATT",
            document_id="DOC-REV-EMPTY-ATT",
        )
        attached.with_context(collection_audited_state=True).write(
            {"state": "validated_collections"}
        )
        draft_attached = self._create_attached_voucher(
            customer_identification="CUST-REV-EMPTY-DRAFT",
            document_id="DOC-REV-EMPTY-DRAFT",
        )
        rejected = self._create_attached_voucher(
            customer_identification="CUST-REV-EMPTY-REJ",
            document_id="DOC-REV-EMPTY-REJ",
        )
        rejected.with_context(collection_audited_state=True).write(
            {"state": "validated_collections"}
        )

        queue = Voucher.get_review_queue(self.review_sheet.id)
        self.assertEqual(queue, [])
        self.assertNotIn(draft_attached.id, [item["id"] for item in queue])

    def test_queue_orders_pdf_and_png_without_base64(self):
        """Triangulation: PDF and PNG proofs both queue with content URLs only."""
        self._neutralize_preexisting_queue()
        Voucher = self.env["collection.voucher"]
        png_voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-PNG",
            document_id="DOC-REV-PNG",
            attachment=PNG_B64,
            attachment_filename="a.png",
        )
        pdf_voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-PDF",
            document_id="DOC-REV-PDF",
            document_type="check",
            amount=50.0,
            check_number="CHK-1",
            check_bank="Banco Nación",
            check_type="common",
            check_issue_date=date(2026, 1, 10),
            check_payment_date=date(2026, 2, 10),
            attachment=PDF_B64,
            attachment_filename="b.pdf",
        )
        queue = Voucher.get_review_queue(self.review_sheet.id)
        self.assertEqual(
            [item["id"] for item in queue], [png_voucher.id, pdf_voucher.id]
        )
        self.assertEqual(queue[0]["position"], 1)
        self.assertEqual(queue[1]["position"], 2)
        self.assertEqual(queue[0]["total"], 2)
        self.assertEqual(queue[1]["total"], 2)
        self.assertEqual(queue[1]["document_type"], "check")
        self.assertEqual(queue[1]["check_number"], "CHK-1")
        self.assertEqual(queue[1]["check_bank"], "Banco Nación")
        self.assertEqual(queue[1]["check_type"], "common")
        self.assertEqual(queue[0]["voucher_id"], png_voucher.id)
        self.assertEqual(queue[0]["voucher_name"], png_voucher.name)
        self.assertEqual(queue[1]["voucher_id"], pdf_voucher.id)
        self.assertEqual(queue[1]["voucher_name"], pdf_voucher.name)
        self._assert_payload_from_ir_attachment(queue[0], png_voucher)
        self._assert_payload_from_ir_attachment(queue[1], pdf_voucher)

    def test_queue_image_payload_is_web_content_url_only(self):
        """Image proofs expose /web/content URLs, never datas/base64."""
        self._neutralize_preexisting_queue()
        Voucher = self.env["collection.voucher"]
        png_voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-IMG-PNG",
            document_id="DOC-REV-IMG-PNG",
            attachment=PNG_B64,
            attachment_filename="proof.png",
        )
        jpg_voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-IMG-JPG",
            document_id="DOC-REV-IMG-JPG",
            attachment=PNG_B64,
            attachment_filename="proof.jpg",
        )
        queue = {
            item["id"]: item for item in Voucher.get_review_queue(self.review_sheet.id)
        }
        for voucher, filename in (
            (png_voucher, "proof.png"),
            (jpg_voucher, "proof.jpg"),
        ):
            payload = queue[voucher.id]
            self.assertEqual(payload["attachment_filename"], filename)
            self.assertIn(
                f"/web/content/{voucher.message_main_attachment_id.id}",
                payload["attachment_url"],
            )
            self.assertNotIn(f"id={voucher.id}", payload["attachment_url"])
            self.assertNotIn("field=", payload["attachment_url"])
            self.assertTrue(payload["mimetype"].startswith("image/"))
            self._assert_payload_from_ir_attachment(payload, voucher)

    def test_queue_pdf_payload_is_web_content_url_only(self):
        """Triangulation: PDF proofs use the same content route, never base64."""
        self._neutralize_preexisting_queue()
        pdf_voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-PDF-URL",
            document_id="DOC-REV-PDF-URL",
            attachment=PDF_B64,
            attachment_filename="comprobante.pdf",
        )
        payload = next(
            item
            for item in self.env["collection.voucher"].get_review_queue(
                self.review_sheet.id
            )
            if item["id"] == pdf_voucher.id
        )
        self.assertEqual(payload["attachment_filename"], "comprobante.pdf")
        self.assertIn(
            f"/web/content/{pdf_voucher.message_main_attachment_id.id}",
            payload["attachment_url"],
        )
        self.assertNotIn(f"id={pdf_voucher.id}", payload["attachment_url"])
        self.assertNotIn("field=", payload["attachment_url"])
        self.assertEqual(payload["mimetype"], "application/pdf")
        self.assertNotEqual(payload["attachment_url"], PNG_B64)
        self._assert_payload_from_ir_attachment(payload, pdf_voucher)

    def test_owl_line_model_is_collection_voucher(self):
        """OWL must call review RPCs on collection.voucher, not the dropped line."""
        helpers_js = self._helpers_js()
        action_js = self._action_js()
        self.assertIn('LINE_MODEL = "collection.voucher"', helpers_js)
        self.assertNotIn("collection.voucher.line", helpers_js)
        self.assertNotIn("collection.voucher.line", action_js)
        self.assertIn("LINE_MODEL", action_js)
        self.assertIn("get_review_queue", action_js)
        self.assertIn("action_review_approve", action_js)
        self.assertNotIn("action_review_reject", action_js)
        self.assertNotIn("async reject()", action_js)
        self.assertIn("action_review_set_rotation", action_js)

    def test_owl_review_rpcs_pass_sheet_id_from_action_params(self):
        """OWL must send params.sheet_id on queue, approve, and rotation RPCs."""
        action_js = self._action_js()
        compact = "".join(action_js.split())
        self.assertIn("params.sheet_id", action_js)
        self.assertNotIn("active_id", action_js)
        self.assertIn('get_review_queue",[sheetId]', compact)
        self.assertRegex(
            compact,
            r'action_review_approve",\[\[this\.current\.id\],sheetId,buildApproveVals\(',
        )
        self.assertIn("buildApproveVals", compact)
        self.assertNotIn("action_review_reject", compact)
        self.assertRegex(
            compact,
            r'action_review_set_rotation",\[\[this\.current\.id\],sheetId,next,?\]',
        )
        self.assertIn("Number.isInteger(sheetId)", action_js)
        load_queue = action_js.split("async loadQueue")[1].split("goPrev()")[0]
        self.assertIn("sheetId", load_queue)
        self.assertIn("get_review_queue", load_queue)
        self.assertLess(
            load_queue.find("sheetId"),
            load_queue.find("get_review_queue"),
            "loadQueue must resolve sheetId before calling get_review_queue",
        )

    def test_document_review_copy_targets_vouchers_not_lines(self):
        xml = self._viewer_template_xml()
        action_js = self._action_js()
        self.assertNotIn("líneas", xml)
        self.assertNotIn("lineas", xml.lower())
        self.assertNotIn("Payment line", action_js)
        self.assertIn("Payment voucher approved.", action_js)
        self.assertNotIn("Payment voucher rejected.", action_js)
        self.assertNotIn("Rechazar", xml)
        self.assertNotIn('t-on-click="reject"', xml)
        self.assertIn("Aprobar y seguir", xml)
        self.assertIn('t-on-click="approve"', xml)
        self.assertIn("No quedan comprobantes elegibles para revisar.", xml)

    def test_review_lock_uses_for_update_on_collection_voucher(self):
        source = inspect.getsource(
            type(self.env["collection.voucher"])._lock_and_ensure_review_eligible
        )
        self.assertIn("FOR UPDATE", source)
        self.assertIn("collection_voucher", source)
        self.assertNotIn("collection_voucher_line", source)

    def test_document_review_viewer_binds_web_content_for_image_and_pdf(self):
        """OWL viewer must bind /web/content URLs on img and iframe/embed."""
        xml = self._viewer_template_xml()
        root = self._viewer_template_root()
        self.assertNotIn("viewer-placeholder", xml)
        self.assertNotIn("datas", xml)
        self.assertNotIn("base64", xml.lower())
        self.assertNotIn("data:image", xml)
        self.assertNotIn("data:application/pdf", xml)
        images = root.xpath(".//img")
        self.assertTrue(images, "image proofs must render via <img>")
        self.assertTrue(
            any(node.get("t-att-src") == "current.attachment_url" for node in images),
            "image viewer must bind current.attachment_url",
        )
        pdf_nodes = root.xpath(".//iframe") + root.xpath(".//embed")
        self.assertTrue(pdf_nodes, "PDF proofs must render via <iframe> or <embed>")
        self.assertTrue(
            any(
                node.get("t-att-src") == "current.attachment_url"
                or "current.attachment_url" in (node.get("t-attf-src") or "")
                for node in pdf_nodes
            ),
            "PDF viewer must bind current.attachment_url",
        )

    def test_document_review_viewer_has_loading_error_empty_attachment_states(
        self,
    ):
        """Viewer loading, error, and empty-attachment must be distinct."""
        xml = self._viewer_template_xml()
        self.assertIn("viewer-loading", xml)
        self.assertIn("viewer-error", xml)
        self.assertIn("viewer-empty", xml)
        self.assertIn("Cargando documento", xml)
        self.assertIn("No se pudo cargar el documento", xml)
        self.assertIn("No hay archivo adjunto para mostrar", xml)
        self.assertIn("No hay comprobantes pendientes", xml)
        self.assertNotIn("Traceback", xml)
        self.assertNotIn("viewer-placeholder", xml)

    def test_document_review_viewer_fit_button_and_wheel_zoom(self):
        """Viewer must expose fit-to-pane and cursor-anchored wheel zoom."""
        xml = self._viewer_template_xml()
        root = self._viewer_template_root()
        self.assertIn("Ajustar al visor", xml)
        self.assertIn("fitViewer", xml)
        self.assertIn("onViewerWheel", xml)
        self.assertIn("viewer-pdf-hitbox", xml)
        self.assertNotIn("datas", xml)
        self.assertNotIn("base64", xml.lower())
        self.assertNotIn("data:image", xml)
        self.assertNotIn("data:application/pdf", xml)

        fit_buttons = root.xpath(".//button[@aria-label='Ajustar al visor']")
        self.assertTrue(
            fit_buttons, "fit control must be a button labeled Ajustar al visor"
        )
        self.assertTrue(
            any("fitViewer" in (node.get("t-on-click") or "") for node in fit_buttons),
            "fit button must call fitViewer",
        )

        trays = self._viewer_tray_nodes(root)
        self.assertTrue(trays, "viewer tray must exist")
        self.assertTrue(
            any(
                "onViewerWheel" in (node.get("t-on-wheel.prevent") or "")
                or "onViewerWheel" in (node.get("t-on-wheel") or "")
                for node in trays
            ),
            "tray must bind wheel zoom via onViewerWheel",
        )

        scss = (_DOCUMENT_REVIEW_DIR / "document_review_action.scss").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "cursor: zoom-in",
            scss,
            "hovering the document viewer must show a zoom cursor",
        )

        hitboxes = [
            node
            for node in root.xpath(".//*")
            if "viewer-pdf-hitbox" in (node.get("class") or "")
            or "viewer-pdf-hitbox" in (node.get("t-attf-class") or "")
            or "viewer-pdf-hitbox" in (node.get("t-att-class") or "")
        ]
        self.assertTrue(hitboxes, "PDF viewer must include a wheel hitbox")
        images = root.xpath(".//img")
        self.assertTrue(
            any(node.get("t-att-src") == "current.attachment_url" for node in images),
            "image viewer must still bind current.attachment_url",
        )
        pdf_nodes = root.xpath(".//iframe") + root.xpath(".//embed")
        self.assertTrue(
            any(
                "current.attachment_url" in (node.get("t-att-src") or "")
                or "current.attachment_url" in (node.get("t-attf-src") or "")
                for node in pdf_nodes
            ),
            "PDF viewer must still bind current.attachment_url",
        )

    def test_document_review_viewer_pointer_pan_while_zoomed(self):
        """Zoomed proofs must pan on left-button drag; PDF hitbox must keep the drag."""
        xml = self._viewer_template_xml()
        root = self._viewer_template_root()
        self.assertIn("onViewerPointerDown", xml)
        self.assertIn("onViewerPointerMove", xml)
        self.assertIn("onViewerPointerUp", xml)
        self.assertIn("is-panning", xml)
        self.assertIn("is-zoom-pannable", xml)
        self.assertIn("viewer-pdf-hitbox", xml)
        self.assertNotIn("datas", xml)
        self.assertNotIn("base64", xml.lower())
        self.assertNotIn("data:image", xml)
        self.assertNotIn("data:application/pdf", xml)

        trays = self._viewer_tray_nodes(root)
        self.assertTrue(trays, "viewer tray must exist")
        self.assertTrue(
            any(
                "onViewerPointerDown"
                in self._viewer_event_handler(node, "t-on-pointerdown")
                for node in trays
            ),
            "tray must start pan via onViewerPointerDown",
        )
        self.assertTrue(
            any(
                "onViewerPointerMove"
                in self._viewer_event_handler(node, "t-on-pointermove")
                for node in trays
            ),
            "tray must pan via onViewerPointerMove",
        )
        self.assertTrue(
            any(
                "onViewerPointerUp"
                in self._viewer_event_handler(
                    node, "t-on-pointerup", "t-on-pointercancel"
                )
                or "onViewerPointerUp"
                in self._viewer_event_handler(node, "t-on-lostpointercapture")
                for node in trays
            ),
            "tray must end pan via onViewerPointerUp",
        )

        scss = (_DOCUMENT_REVIEW_DIR / "document_review_action.scss").read_text(
            encoding="utf-8"
        )
        self.assertIn("cursor: grab", scss)
        self.assertIn("cursor: grabbing", scss)
        self.assertIn("is-zoom-pannable", scss)
        self.assertIn("is-panning", scss)

        action_js = self._action_js()
        helpers_js = self._helpers_js()
        self.assertIn("applyViewerPan", helpers_js)
        self.assertIn("isViewerZoomIdentity", helpers_js)
        self.assertIn("applyViewerPan", action_js)
        self.assertIn("onViewerPointerDown", action_js)
        self.assertIn("onViewerPointerMove", action_js)
        self.assertIn("onViewerPointerUp", action_js)
        self.assertIn("setPointerCapture", action_js)

        hitboxes = [
            node
            for node in root.xpath(".//*")
            if "viewer-pdf-hitbox" in self._viewer_class_tokens(node)
        ]
        self.assertTrue(hitboxes, "PDF viewer must keep a pointer hitbox for pan")
        images = root.xpath(".//img")
        self.assertTrue(
            any(node.get("t-att-src") == "current.attachment_url" for node in images),
            "image viewer must still bind current.attachment_url",
        )
        self.assertTrue(
            any(
                node.get("draggable") == "false"
                or node.get("t-att-draggable") == "false"
                for node in images
            ),
            "image proofs must not use native drag",
        )
        pdf_nodes = root.xpath(".//iframe") + root.xpath(".//embed")
        self.assertTrue(
            any(
                "current.attachment_url" in (node.get("t-att-src") or "")
                or "current.attachment_url" in (node.get("t-attf-src") or "")
                for node in pdf_nodes
            ),
            "PDF viewer must still bind current.attachment_url",
        )

    def test_document_review_viewer_rotate_buttons(self):
        """Viewer must expose clockwise and counterclockwise rotation."""
        xml = self._viewer_template_xml()
        root = self._viewer_template_root()
        self.assertIn("Rotar a la izquierda", xml)
        self.assertIn("Rotar a la derecha", xml)
        self.assertIn("rotateViewerLeft", xml)
        self.assertIn("rotateViewerRight", xml)
        self.assertIn("viewer-rotate", xml)
        self.assertNotIn("datas", xml)
        self.assertNotIn("base64", xml.lower())
        self.assertNotIn("data:image", xml)
        self.assertNotIn("data:application/pdf", xml)

        left_buttons = root.xpath(".//button[@aria-label='Rotar a la izquierda']")
        right_buttons = root.xpath(".//button[@aria-label='Rotar a la derecha']")
        self.assertTrue(left_buttons, "rotate-left control must be labeled")
        self.assertTrue(right_buttons, "rotate-right control must be labeled")
        self.assertTrue(
            any(
                "rotateViewerLeft" in (node.get("t-on-click") or "")
                for node in left_buttons
            ),
            "rotate-left button must call rotateViewerLeft",
        )
        self.assertTrue(
            any(
                "rotateViewerRight" in (node.get("t-on-click") or "")
                for node in right_buttons
            ),
            "rotate-right button must call rotateViewerRight",
        )

        rotate_wraps = [
            node
            for node in root.xpath(".//*")
            if "viewer-rotate" in (node.get("class") or "")
            or "viewer-rotate" in (node.get("t-attf-class") or "")
            or "viewer-rotate" in (node.get("t-att-class") or "")
        ]
        self.assertTrue(rotate_wraps, "viewer must wrap proofs in a rotate layer")
        images = root.xpath(".//img")
        self.assertTrue(
            any(node.get("t-att-src") == "current.attachment_url" for node in images),
            "image viewer must still bind current.attachment_url",
        )
        pdf_nodes = root.xpath(".//iframe") + root.xpath(".//embed")
        self.assertTrue(
            any(
                "current.attachment_url" in (node.get("t-att-src") or "")
                or "current.attachment_url" in (node.get("t-attf-src") or "")
                for node in pdf_nodes
            ),
            "PDF viewer must still bind current.attachment_url",
        )

        action_js = self._action_js()
        helpers_js = self._helpers_js()
        self.assertIn("nextViewerRotation", helpers_js)
        self.assertIn("storedViewerRotation", helpers_js)
        self.assertIn("storedViewerRotation", action_js)
        self.assertIn("action_review_set_rotation", action_js)
        self.assertIn("rotateViewerLeft", action_js)
        self.assertIn("rotateViewerRight", action_js)

    def test_attachment_rotation_defaults_zero_and_copy_false(self):
        voucher = self._create_attached_voucher(
            customer_identification="CUST-REV-ROT-DEF",
            document_id="DOC-REV-ROT-DEF",
        )
        self.assertEqual(voucher.attachment_rotation, 0)
        voucher.write({"attachment_rotation": 90})
        clone = voucher.copy({"document_id": "DOC-REV-ROT-DEF-CLONE"})
        self.assertEqual(clone.attachment_rotation, 0)
        self.assertEqual(voucher.attachment_rotation, 90)

    def test_set_rotation_persists_and_returns_in_queue(self):
        self._neutralize_preexisting_queue()
        voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-ROT-SAVE",
            document_id="DOC-REV-ROT-SAVE",
        )
        voucher.action_review_set_rotation(self.review_sheet.id, 90)
        self.assertEqual(voucher.attachment_rotation, 90)
        payload = next(
            item
            for item in voucher.get_review_queue(self.review_sheet.id)
            if item["id"] == voucher.id
        )
        self.assertEqual(payload["attachment_rotation"], 90)
        self._assert_payload_from_ir_attachment(payload, voucher)
        voucher.action_review_set_rotation(self.review_sheet.id, 270)
        self.assertEqual(voucher.attachment_rotation, 270)
        voucher.action_review_set_rotation(self.review_sheet.id, 0)
        self.assertEqual(voucher.attachment_rotation, 0)

    def test_set_rotation_refuses_invalid_and_ineligible(self):
        """Triangulation: invalid angles and ineligible vouchers must not persist."""
        voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-ROT-BAD",
            document_id="DOC-REV-ROT-BAD",
        )
        with self.assertRaises(UserError):
            voucher.action_review_set_rotation(self.review_sheet.id, 45)
        with self.assertRaises(UserError):
            voucher.action_review_set_rotation(self.review_sheet.id, -90)
        self.assertEqual(voucher.attachment_rotation, 0)
        voucher.action_review_approve(self.review_sheet.id)
        with self.assertRaises(UserError):
            voucher.action_review_set_rotation(self.review_sheet.id, 90)
        self.assertEqual(voucher.attachment_rotation, 0)

    def test_attachment_write_resets_rotation(self):
        voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-ROT-RESET",
            document_id="DOC-REV-ROT-RESET",
        )
        voucher.action_review_set_rotation(self.review_sheet.id, 180)
        self.assertEqual(voucher.attachment_rotation, 180)
        stored_id = voucher.message_main_attachment_id.id
        self._replace_proof(voucher, "rotated-reset.pdf", PDF_B64)
        self.assertEqual(voucher.attachment_rotation, 0)
        self.assertEqual(voucher.message_main_attachment_id.name, "rotated-reset.pdf")
        self.assertNotEqual(voucher.message_main_attachment_id.id, stored_id)

    def test_extra_chatter_files_do_not_reset_rotation(self):
        """Extra chatter files MUST NOT reset saved rotation or designated proof."""
        self._neutralize_preexisting_queue()
        voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-ROT-EXTRA",
            document_id="DOC-REV-ROT-EXTRA",
        )
        voucher.action_review_set_rotation(self.review_sheet.id, 90)
        proof = voucher.message_main_attachment_id
        extra = self.env["ir.attachment"].create(
            {
                "name": "notes.txt",
                "raw": b"hello world",
                "res_model": "collection.voucher",
                "res_id": voucher.id,
            }
        )
        extra._post_add_create()
        voucher.invalidate_recordset()
        self.assertEqual(voucher.attachment_rotation, 90)
        self.assertEqual(voucher.message_main_attachment_id, proof)
        payload = next(
            item
            for item in voucher.get_review_queue(self.review_sheet.id)
            if item["id"] == voucher.id
        )
        self.assertEqual(payload["attachment_rotation"], 90)
        self._assert_payload_from_ir_attachment(payload, voucher)

    def test_clear_designated_proof_resets_rotation(self):
        """Clearing message_main_attachment_id MUST reset rotation to 0."""
        self._neutralize_preexisting_queue()
        voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-ROT-CLEAR",
            document_id="DOC-REV-ROT-CLEAR",
        )
        voucher.action_review_set_rotation(self.review_sheet.id, 270)
        self.assertEqual(voucher.attachment_rotation, 270)
        voucher.write({"message_main_attachment_id": False})
        self.assertEqual(voucher.attachment_rotation, 0)
        self.assertFalse(voucher.message_main_attachment_id)
        queue = self.env["collection.voucher"].get_review_queue(self.review_sheet.id)
        self.assertNotIn(voucher.id, [item["id"] for item in queue])

    def test_stale_review_when_designated_proof_missing(self):
        """Mutations MUST refuse a seller-validated voucher after proof is cleared."""
        voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-STALE-PROOF",
            document_id="DOC-REV-STALE-PROOF",
        )
        voucher.write({"attachment_rotation": 90})
        voucher.write({"message_main_attachment_id": False})
        self.assertEqual(voucher.state, "validated_seller")
        self.assertFalse(voucher.message_main_attachment_id)
        with self.assertRaises(UserError):
            voucher.action_review_approve(self.review_sheet.id, {"amount": 1.0})
        with self.assertRaises(UserError):
            voucher.action_review_set_rotation(self.review_sheet.id, 180)
        self.assertFalse(hasattr(voucher, "action_review_reject"))
        self.assertEqual(voucher.state, "validated_seller")
        self.assertAlmostEqual(voucher.amount, 100.0, places=2)
        self.assertEqual(voucher.attachment_rotation, 0)

    def test_document_review_hides_document_id(self):
        """Reviewer UI must not show document_id; voucher and position stay visible."""
        xml = self._viewer_template_xml()
        root = self._viewer_template_root()
        self.assertNotIn("ID de documento", xml)
        self.assertNotIn("collection_review_document_id", xml)
        self.assertNotIn("current.document_id", xml)
        self.assertFalse(
            root.xpath(".//*[@id='collection_review_document_id']"),
            "document_id input must not be in the review template",
        )
        self.assertIn("current.voucher_name", xml)
        self.assertIn("current.position", xml)
        self.assertIn("current.total", xml)

    # --- Defaults, approve, no reject RPC ---

    def test_state_defaults_pending_and_copy_false(self):
        voucher = self._create_attached_voucher(
            customer_identification="CUST-REV-DEF",
            document_id="DOC-REV-DEF",
        )
        self.assertEqual(voucher.state, "draft")
        self.assertFalse(voucher.reviewed_by)
        self.assertFalse(voucher.reviewed_at)
        voucher.with_context(collection_audited_state=True).write(
            {
                "state": "validated_collections",
                "reviewed_by": self.env.user.id,
            }
        )
        clone = voucher.copy({"document_id": "DOC-REV-DEF-CLONE"})
        self.assertEqual(clone.state, "draft")
        self.assertFalse(clone.reviewed_by)
        self.assertFalse(clone.reviewed_at)

    def test_approve_persists_edits_and_records_audit(self):
        """Non-empty current vals MUST rewrite current; forged keys MUST be ignored."""
        voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-APPR",
            document_id="DOC-REV-APPR",
            amount=100.0,
            from_account="OLD-FROM",
            ocr_amount=90.0,
            ocr_from_account="OCR-FROM",
            ocr_document_type="bank_transfer",
            seller_amount=100.0,
            seller_from_account="OLD-FROM",
            seller_document_type="bank_transfer",
        )
        voucher.action_review_approve(
            self.review_sheet.id,
            {
                "document_id": "HACKED-ID",
                "ocr_amount": 1.0,
                "seller_from_account": "HACKED-SELLER",
                "amount": 250.75,
                "from_account": "NEW-FROM",
                "to_account": "NEW-TO",
                "voucher_number": "TRF-EDIT",
                "voucher_date": date(2026, 5, 1),
            },
        )
        self.assertEqual(voucher.document_id, "DOC-REV-APPR")
        self.assertAlmostEqual(voucher.amount, 250.75, places=2)
        self.assertEqual(voucher.from_account, "NEW-FROM")
        self.assertEqual(voucher.to_account, "NEW-TO")
        self.assertEqual(voucher.voucher_number, "TRF-EDIT")
        self.assertEqual(voucher.voucher_date, date(2026, 5, 1))
        self.assertAlmostEqual(voucher.ocr_amount, 90.0, places=2)
        self.assertEqual(voucher.ocr_from_account, "OCR-FROM")
        self.assertAlmostEqual(voucher.seller_amount, 100.0, places=2)
        self.assertEqual(voucher.seller_from_account, "OLD-FROM")
        self.assertEqual(voucher.state, "validated_collections")
        self.assertEqual(voucher.reviewed_by, self.env.user)
        self.assertTrue(voucher.reviewed_at)
        snaps = self._snapshots(voucher)
        self.assertEqual(snaps.decision, "approved")
        self.assertAlmostEqual(snaps.amount, 250.75, places=2)
        self.assertEqual(snaps.from_account, "NEW-FROM")
        self.assertNotEqual(voucher.state, snaps.decision)

    def test_approve_persists_check_fields(self):
        """Triangulation: nonempty check vals MUST persist onto current check fields."""
        voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-CHK",
            document_id="DOC-REV-CHK",
            document_type="check",
            amount=10.0,
            check_number="CHK-CUR",
            check_bank="Banco Galicia",
            check_type="common",
            check_issue_date=date(2026, 1, 1),
            check_payment_date=date(2026, 1, 15),
            ocr_document_type="check",
            ocr_amount=10.0,
            ocr_check_number="CHK-OCR",
        )
        voucher.action_review_approve(
            self.review_sheet.id,
            {
                "document_type": "check",
                "amount": 80.0,
                "check_number": "CHK-9",
                "check_bank": "Banco Nación",
                "check_type": "deferred",
                "check_issue_date": date(2026, 1, 10),
                "check_payment_date": date(2026, 2, 10),
            },
        )
        self.assertEqual(voucher.check_number, "CHK-9")
        self.assertEqual(voucher.check_bank, "Banco Nación")
        self.assertEqual(voucher.check_type, "deferred")
        self.assertEqual(voucher.check_issue_date, date(2026, 1, 10))
        self.assertEqual(voucher.check_payment_date, date(2026, 2, 10))
        self.assertAlmostEqual(voucher.amount, 80.0, places=2)
        self.assertEqual(voucher.ocr_check_number, "CHK-OCR")
        self.assertEqual(voucher.state, "validated_collections")
        snaps = self._snapshots(voucher)
        self.assertEqual(snaps.decision, "approved")
        self.assertEqual(snaps.check_number, voucher.check_number)
        self.assertAlmostEqual(snaps.amount, voucher.amount, places=2)

    def test_approve_persists_cash_deposit_fields(self):
        """Triangulation: empty dict vals MUST leave current unchanged."""
        voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-CASH",
            document_id="DOC-REV-CASH",
            document_type="cash_deposit",
            amount=15.0,
        )
        voucher.action_review_approve(self.review_sheet.id, {})
        self.assertEqual(voucher.document_type, "cash_deposit")
        self.assertAlmostEqual(voucher.amount, 15.0, places=2)
        self.assertEqual(voucher.state, "validated_collections")
        snaps = self._snapshots(voucher)
        self.assertEqual(snaps.decision, "approved")
        self.assertAlmostEqual(snaps.amount, 15.0, places=2)
        self.assertEqual(snaps.document_type, "cash_deposit")

    def test_review_reject_rpc_does_not_exist(self):
        """Reject MUST NOT exist; eligible voucher stays validated_seller."""
        voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-REJ",
            document_id="DOC-REV-REJ",
        )
        self.assertFalse(hasattr(voucher, "action_review_reject"))
        Voucher = self.env["collection.voucher"]
        self.assertFalse(hasattr(Voucher, "action_review_reject"))
        self.assertEqual(voucher.state, "validated_seller")
        self.assertFalse(voucher.reviewed_by)
        self.assertFalse(self._snapshots(voucher))

    # --- Stale/concurrent, attachment reset ---

    def test_stale_approve_and_reject_refuse_without_corruption(self):
        voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-STALE",
            document_id="DOC-REV-STALE",
        )
        voucher.action_review_approve(self.review_sheet.id, {"amount": 40.0})
        self.assertEqual(voucher.state, "validated_collections")
        with self.assertRaises(UserError):
            voucher.action_review_approve(self.review_sheet.id, {"amount": 1.0})
        self.assertFalse(hasattr(voucher, "action_review_reject"))
        self.assertEqual(voucher.state, "validated_collections")
        self.assertAlmostEqual(voucher.amount, 40.0, places=2)

    def test_stale_review_when_not_pending_or_unattached(self):
        """Triangulation: ineligible state/attachment refuses approve."""
        attached = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-STALE2",
            document_id="DOC-REV-STALE2",
        )
        attached.with_context(collection_audited_state=True).write(
            {"state": "validated_collections"}
        )
        with self.assertRaises(UserError):
            attached.action_review_approve(self.review_sheet.id)
        self.assertFalse(hasattr(attached, "action_review_reject"))
        self.assertEqual(attached.state, "validated_collections")

        unattached = self.env["collection.voucher"].create(
            self._voucher_vals(
                customer_identification="CUST-REV-STALE3",
                document_id="DOC-REV-STALE3",
                seller_id=self._seller().id,
                sheet_id=self.review_sheet.id,
            )
        )
        with self.assertRaises(UserError):
            unattached.action_review_approve(self.review_sheet.id)
        self.assertFalse(hasattr(unattached, "action_review_reject"))
        self.assertEqual(unattached.state, "draft")

        draft_attached = self._create_attached_voucher(
            customer_identification="CUST-REV-STALE-DRAFT",
            document_id="DOC-REV-STALE-DRAFT",
        )
        with self.assertRaises(UserError):
            draft_attached.action_review_approve(self.review_sheet.id)
        self.assertEqual(draft_attached.state, "draft")

    def test_attachment_write_resets_pending_and_clears_audit(self):
        voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-REV-RESET",
            document_id="DOC-REV-RESET",
        )
        voucher.action_review_approve(self.review_sheet.id)
        self.assertEqual(voucher.state, "validated_collections")
        self.assertTrue(voucher.reviewed_by)
        self.assertTrue(voucher.reviewed_at)
        self._replace_proof(voucher, "replaced.pdf", PDF_B64)
        self.assertEqual(voucher.state, "validated_seller")
        self.assertFalse(voucher.reviewed_by)
        self.assertFalse(voucher.reviewed_at)
        self.assertEqual(voucher.message_main_attachment_id.name, "replaced.pdf")

    def test_attachment_write_resets_rejected_voucher(self):
        """Triangulation: replacing a draft voucher's proof reopens to seller."""
        voucher = self._create_attached_voucher(
            customer_identification="CUST-REV-RESET-REJ",
            document_id="DOC-REV-RESET-REJ",
        )
        self.assertEqual(voucher.state, "draft")
        self.assertFalse(hasattr(voucher, "action_review_reject"))
        self._replace_proof(voucher, "again.png", PNG_B64)
        self.assertEqual(voucher.state, "validated_seller")
        self.assertFalse(voucher.reviewed_by)
        self.assertFalse(voucher.reviewed_at)

    def _snapshots(self, voucher):
        return self.env["collection.voucher.review.snapshot"].search(
            [("voucher_id", "=", voucher.id)],
            order="revision",
        )

    def test_document_review_approve_empty_vals_snapshots_current(self):
        """Approve with empty vals MUST snapshot current payment fields."""
        voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-SNAP-EMPTY",
            document_id="DOC-SNAP-EMPTY",
            amount=100.0,
            from_account="FROM-EMPTY",
            ocr_amount=90.0,
            ocr_from_account="OCR-FROM",
            ocr_document_type="bank_transfer",
            seller_amount=100.0,
            seller_from_account="FROM-EMPTY",
            seller_document_type="bank_transfer",
        )
        voucher.action_review_approve(self.review_sheet.id)
        self.assertEqual(voucher.state, "validated_collections")
        self.assertAlmostEqual(voucher.amount, 100.0, places=2)
        self.assertEqual(voucher.from_account, "FROM-EMPTY")
        snaps = self._snapshots(voucher)
        self.assertEqual(len(snaps), 1)
        self.assertEqual(snaps.revision, 1)
        self.assertEqual(snaps.decision, "approved")
        self.assertEqual(snaps.reviewer_id, self.env.user)
        self.assertEqual(snaps.reviewed_at, voucher.reviewed_at)
        self.assertAlmostEqual(snaps.amount, 100.0, places=2)
        self.assertEqual(snaps.from_account, "FROM-EMPTY")
        self.assertEqual(snaps.document_type, "bank_transfer")
        self.assertNotEqual(voucher.state, snaps.decision)
        self.assertAlmostEqual(voucher.ocr_amount, 90.0, places=2)
        self.assertEqual(voucher.ocr_from_account, "OCR-FROM")
        self.assertAlmostEqual(voucher.seller_amount, 100.0, places=2)

    def test_document_review_reject_appends_snapshot(self):
        """Document Review reject MUST NOT exist and MUST NOT append a snapshot."""
        voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-SNAP-REJ",
            document_id="DOC-SNAP-REJ",
            amount=55.0,
            ocr_amount=55.0,
            ocr_document_type="bank_transfer",
            seller_amount=55.0,
            seller_document_type="bank_transfer",
        )
        self.assertFalse(hasattr(voucher, "action_review_reject"))
        self.assertEqual(voucher.state, "validated_seller")
        self.assertFalse(self._snapshots(voucher))

    def test_form_approve_and_reject_do_not_append_snapshots(self):
        """Form Validate by Seller MUST change state and MUST NOT append snapshots."""
        approved = self._create_attached_voucher(
            customer_identification="CUST-SNAP-FORM-APPR",
            document_id="DOC-SNAP-FORM-APPR",
            ocr_amount=10.0,
            ocr_document_type="bank_transfer",
            seller_amount=100.0,
            seller_document_type="bank_transfer",
        )
        approved.action_validate_seller()
        self.assertEqual(approved.state, "validated_seller")
        self.assertFalse(self._snapshots(approved))

        rejected = self._create_attached_voucher(
            customer_identification="CUST-SNAP-FORM-REJ",
            document_id="DOC-SNAP-FORM-REJ",
        )
        self.assertFalse(hasattr(rejected, "action_reject"))
        rejected.action_validate_seller()
        self.assertEqual(rejected.state, "validated_seller")
        self.assertFalse(self._snapshots(rejected))

    def test_reopen_then_review_appends_another_revision(self):
        """A later Document Review after reopen MUST append revision 2."""
        voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-SNAP-REOPEN",
            document_id="DOC-SNAP-REOPEN",
            amount=40.0,
            ocr_amount=40.0,
            ocr_document_type="bank_transfer",
            seller_amount=40.0,
            seller_document_type="bank_transfer",
        )
        voucher.action_review_approve(self.review_sheet.id)
        first = self._snapshots(voucher)
        self.assertEqual(len(first), 1)
        first_id = first.id
        first_amount = first.amount
        self.assertEqual(first.decision, "approved")
        self._replace_proof(voucher, "reopened.png", PNG_B64)
        self.assertEqual(voucher.state, "validated_seller")
        voucher.action_review_approve(self.review_sheet.id)
        snaps = self._snapshots(voucher)
        self.assertEqual(len(snaps), 2)
        self.assertEqual(snaps[0].id, first_id)
        self.assertEqual(snaps[0].revision, 1)
        self.assertAlmostEqual(snaps[0].amount, first_amount, places=2)
        self.assertEqual(snaps[0].decision, "approved")
        self.assertEqual(snaps[1].revision, 2)
        self.assertEqual(snaps[1].decision, "approved")
        self.assertEqual(voucher.state, "validated_collections")
        self.assertNotEqual(voucher.state, snaps[1].decision)

    def test_reviewer_correction_matches_snapshot_current_only(self):
        """Non-empty approve vals MUST rewrite current; snapshot matches; raw/seller
        stay."""
        voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-SNAP-EDIT",
            document_id="DOC-SNAP-EDIT",
            amount=100.0,
            from_account="OLD-FROM",
            ocr_amount=80.0,
            ocr_from_account="OCR-FROM",
            ocr_document_type="bank_transfer",
            seller_amount=100.0,
            seller_from_account="OLD-FROM",
            seller_document_type="bank_transfer",
        )
        voucher.action_review_approve(
            self.review_sheet.id,
            {"amount": 250.75, "from_account": "NEW-FROM"},
        )
        self.assertAlmostEqual(voucher.amount, 250.75, places=2)
        self.assertEqual(voucher.from_account, "NEW-FROM")
        self.assertAlmostEqual(voucher.ocr_amount, 80.0, places=2)
        self.assertEqual(voucher.ocr_from_account, "OCR-FROM")
        self.assertAlmostEqual(voucher.seller_amount, 100.0, places=2)
        self.assertEqual(voucher.seller_from_account, "OLD-FROM")
        snaps = self._snapshots(voucher)
        self.assertEqual(len(snaps), 1)
        self.assertAlmostEqual(snaps.amount, 250.75, places=2)
        self.assertEqual(snaps.from_account, "NEW-FROM")
        self.assertEqual(snaps.decision, "approved")

    # --- Phase 3: queue provenance + OWL three-way ---

    def test_queue_includes_readonly_provenance_without_fabricating(self):
        """Queue MUST expose stored ocr_*/seller_*; empty MUST stay empty."""
        self._neutralize_preexisting_queue()
        stamped = self._create_review_eligible_voucher(
            customer_identification="CUST-Q-PROV",
            document_id="DOC-Q-PROV",
            amount=100.0,
            from_account="CUR-FROM",
            to_account="CUR-TO",
            voucher_number="TRF-CUR",
            voucher_date=date(2026, 5, 1),
            ocr_document_type="bank_transfer",
            ocr_amount=90.0,
            ocr_from_account="OCR-FROM",
            ocr_to_account="OCR-TO",
            ocr_voucher_number="TRF-OCR",
            ocr_voucher_date=date(2026, 4, 1),
            seller_document_type="bank_transfer",
            seller_amount=100.0,
            seller_from_account="CUR-FROM",
            seller_to_account="CUR-TO",
            seller_voucher_number="TRF-CUR",
            seller_voucher_date=date(2026, 5, 1),
        )
        empty = self._create_review_eligible_voucher(
            customer_identification="CUST-Q-EMPTY",
            document_id="DOC-Q-EMPTY",
            amount=175.5,
            from_account="EMPTY-FROM",
            to_account="EMPTY-TO",
            voucher_number="TRF-EMPTY",
            voucher_date=date(2026, 6, 2),
        )
        queue = {
            item["id"]: item
            for item in self.env["collection.voucher"].get_review_queue(
                self.review_sheet.id
            )
        }
        stamped_payload = queue[stamped.id]
        empty_payload = queue[empty.id]
        self.assertAlmostEqual(stamped_payload["amount"], 100.0, places=2)
        self.assertEqual(stamped_payload["from_account"], "CUR-FROM")
        self._assert_payload_layer(stamped_payload, stamped, "ocr")
        self._assert_payload_layer(stamped_payload, stamped, "seller")
        self._assert_no_binary_in_payload(stamped_payload)
        self.assertAlmostEqual(empty_payload["amount"], 175.5, places=2)
        self.assertEqual(empty_payload["from_account"], "EMPTY-FROM")
        self._assert_empty_payload_provenance(empty_payload, empty)
        self._assert_no_binary_in_payload(empty_payload)

    def test_queue_provenance_excludes_datas_identity_and_document_id_copies(self):
        """Triangulation: provenance keys MUST omit datas, identity, and document_id."""
        self._neutralize_preexisting_queue()
        voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-Q-NOBIN",
            document_id="DOC-Q-NOBIN",
            amount=40.0,
            ocr_amount=11.0,
            ocr_document_type="bank_transfer",
            seller_amount=40.0,
            seller_document_type="bank_transfer",
        )
        payload = next(
            item
            for item in self.env["collection.voucher"].get_review_queue(
                self.review_sheet.id
            )
            if item["id"] == voucher.id
        )
        self.assertEqual(payload["document_id"], "DOC-Q-NOBIN")
        forbidden = (
            "ocr_document_id",
            "seller_document_id",
            "ocr_customer_identification",
            "seller_customer_identification",
            "ocr_seller_id",
            "seller_seller_id",
            "ocr_attachment",
            "seller_attachment",
            "ocr_datas",
            "seller_datas",
            "datas",
        )
        for key in forbidden:
            self.assertNotIn(key, payload, key)
        self._assert_no_binary_in_payload(payload)
        for name in voucher._REVIEW_EDITABLE_FIELDS:
            ocr_key = f"ocr_{name}"
            seller_key = f"seller_{name}"
            self.assertIn(ocr_key, payload, ocr_key)
            self.assertIn(seller_key, payload, seller_key)
            rendered = str(payload[ocr_key]) + str(payload[seller_key])
            self.assertNotIn(PNG_B64, rendered)
            self.assertNotIn(PDF_B64, rendered)

    def test_queue_check_and_cash_deposit_provenance_keys(self):
        """Triangulation: type-specific provenance keys stay stored, not invented."""
        self._neutralize_preexisting_queue()
        check = self._create_review_eligible_voucher(
            customer_identification="CUST-Q-CHK",
            document_id="DOC-Q-CHK",
            document_type="check",
            amount=20.0,
            check_number="CHK-CUR",
            check_bank="Banco Nación",
            check_type="deferred",
            check_issue_date=date(2026, 1, 10),
            check_payment_date=date(2026, 2, 10),
            ocr_document_type="check",
            ocr_amount=10.0,
            ocr_check_number="CHK-OCR",
            ocr_check_bank="OCR Bank",
            ocr_check_type="common",
            ocr_check_issue_date=date(2026, 1, 1),
            ocr_check_payment_date=date(2026, 1, 15),
            seller_document_type="check",
            seller_amount=20.0,
            seller_check_number="CHK-CUR",
            seller_check_bank="Banco Nación",
            seller_check_type="deferred",
            seller_check_issue_date=date(2026, 1, 10),
            seller_check_payment_date=date(2026, 2, 10),
        )
        cash = self._create_review_eligible_voucher(
            customer_identification="CUST-Q-CASH",
            document_id="DOC-Q-CASH",
            document_type="cash_deposit",
            amount=42.5,
            voucher_number="CASH-CUR",
            voucher_date=date(2026, 4, 1),
            ocr_document_type="cash_deposit",
            ocr_amount=40.0,
            ocr_voucher_number="CASH-OCR",
            ocr_voucher_date=date(2026, 3, 1),
            seller_document_type="cash_deposit",
            seller_amount=42.5,
            seller_voucher_number="CASH-SEL",
            seller_voucher_date=date(2026, 4, 1),
        )
        queue = {
            item["id"]: item
            for item in self.env["collection.voucher"].get_review_queue(
                self.review_sheet.id
            )
        }
        check_payload = queue[check.id]
        cash_payload = queue[cash.id]
        self.assertIn("ocr_check_number", check_payload)
        self.assertEqual(check_payload["ocr_check_number"], "CHK-OCR")
        self.assertEqual(check_payload["seller_check_number"], "CHK-CUR")
        self.assertEqual(check_payload["check_number"], "CHK-CUR")
        self._assert_payload_layer(check_payload, check, "ocr")
        self._assert_payload_layer(check_payload, check, "seller")
        self.assertEqual(cash_payload["ocr_voucher_number"], "CASH-OCR")
        self.assertEqual(cash_payload["seller_voucher_number"], "CASH-SEL")
        self.assertEqual(cash_payload["voucher_number"], "CASH-CUR")
        self.assertEqual(cash_payload["ocr_voucher_date"], date(2026, 3, 1))
        self.assertEqual(cash_payload["seller_voucher_date"], date(2026, 4, 1))
        self._assert_payload_layer(cash_payload, cash, "ocr")
        self._assert_payload_layer(cash_payload, cash, "seller")
        self._assert_no_binary_in_payload(check_payload)
        self._assert_no_binary_in_payload(cash_payload)

    def test_review_editable_field_order_is_stable_tuple(self):
        """Queue diffs MUST iterate `_REVIEW_EDITABLE_FIELD_ORDER`, not the
        frozenset."""
        Voucher = self.env["collection.voucher"]
        order = Voucher._REVIEW_EDITABLE_FIELD_ORDER
        self.assertIsInstance(order, tuple)
        self.assertEqual(set(order), set(Voucher._REVIEW_EDITABLE_FIELDS))
        self.assertEqual(len(order), len(set(order)))

    def test_queue_seller_changed_fields_omits_empty_empty(self):
        """Empty OCR and seller copies MUST omit the field from
        seller_changed_fields."""
        self._neutralize_preexisting_queue()
        voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-Q-DIFF-EMPTY",
            document_id="DOC-Q-DIFF-EMPTY",
            amount=175.5,
            from_account="EMPTY-FROM",
            to_account="EMPTY-TO",
            voucher_number="TRF-EMPTY",
            voucher_date=date(2026, 6, 2),
        )
        payload = self._queue_item(voucher)
        self._assert_seller_changed_fields(payload, voucher, {})
        self.assertAlmostEqual(payload["amount"], 175.5, places=2)
        self.assertEqual(payload["from_account"], "EMPTY-FROM")

    def test_queue_seller_changed_fields_emptied_seller_is_explicit(self):
        """Emptied seller Char MUST be False and emptied amount MUST be 0.0, not
        omitted."""
        self._neutralize_preexisting_queue()
        char_voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-Q-DIFF-EMPTY-CHAR",
            document_id="DOC-Q-DIFF-EMPTY-CHAR",
            amount=100.0,
            from_account="CUR-FROM",
            ocr_document_type="bank_transfer",
            ocr_amount=100.0,
            ocr_from_account="OCR-FROM",
            seller_document_type="bank_transfer",
            seller_amount=100.0,
            seller_from_account=False,
        )
        amount_voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-Q-DIFF-EMPTY-AMT",
            document_id="DOC-Q-DIFF-EMPTY-AMT",
            amount=100.0,
            ocr_document_type="bank_transfer",
            ocr_amount=90.0,
            seller_document_type="bank_transfer",
            seller_amount=0.0,
        )
        char_changed = self._assert_seller_changed_fields(
            self._queue_item(char_voucher),
            char_voucher,
            {"from_account": False},
        )
        self.assertIs(char_changed["from_account"], False)
        amount_changed = self._assert_seller_changed_fields(
            self._queue_item(amount_voucher),
            amount_voucher,
            {"amount": 0.0},
        )
        self.assertIsInstance(amount_changed["amount"], float)
        self.assertEqual(amount_changed["amount"], 0.0)

    def test_queue_seller_changed_fields_typed_diffs_follow_field_order(self):
        """Char, Date, Selection, and Monetary diffs MUST use seller values in
        field order."""
        self._neutralize_preexisting_queue()
        voucher = self._create_review_eligible_voucher(
            customer_identification="CUST-Q-DIFF-TYPED",
            document_id="DOC-Q-DIFF-TYPED",
            document_type="bank_transfer",
            amount=175.5,
            from_account="CUR-FROM",
            to_account="CUR-TO",
            voucher_number="TRF-SAME",
            voucher_date=date(2026, 5, 1),
            ocr_document_type="bank_transfer",
            ocr_amount=90.0,
            ocr_from_account="OCR-FROM",
            ocr_to_account="OCR-TO",
            ocr_voucher_number="TRF-SAME",
            ocr_voucher_date=date(2026, 4, 1),
            ocr_check_type="common",
            seller_document_type="check",
            seller_amount=100.0,
            seller_from_account="SEL-FROM",
            seller_to_account=False,
            seller_voucher_number="TRF-SAME",
            seller_voucher_date=date(2026, 5, 1),
            seller_check_type="deferred",
        )
        payload = self._queue_item(voucher)
        changed = self._assert_seller_changed_fields(
            payload,
            voucher,
            {
                "document_type": "check",
                "amount": 100.0,
                "from_account": "SEL-FROM",
                "to_account": False,
                "voucher_date": date(2026, 5, 1),
                "check_type": "deferred",
            },
        )
        self.assertIsInstance(changed["amount"], float)
        self.assertIs(changed["to_account"], False)
        self.assertNotIn("voucher_number", changed)
        self.assertNotIn("check_number", changed)
        self.assertNotIn("check_bank", changed)

    def test_owl_keeps_type_visibility_hides_document_id_and_shows_provenance(self):
        """OWL MUST show one editable draft control; type groups from draft; no
        document_id."""
        xml = self._viewer_template_xml()
        action_js = self._action_js()
        helpers = self._helpers_js()
        panel = self._validation_panel_xml()
        root = self._viewer_template_root()
        self.assertIn("get isBankTransfer()", action_js)
        self.assertIn("get isCheck()", action_js)
        self.assertIn("_layerHasDocumentType", action_js)
        layer_fn = action_js.split("_layerHasDocumentType(documentType)")[1].split(
            "get viewerKind"
        )[0]
        self.assertIn("current.draft.document_type", layer_fn)
        self.assertNotIn("current.ocr_document_type", layer_fn)
        self.assertNotIn("current.seller_document_type", layer_fn)
        self.assertIn('t-if="isBankTransfer"', xml)
        self.assertIn('t-if="isCheck"', xml)
        bank_block = xml.split('t-if="isBankTransfer"')[1].split('t-if="isCheck"')[0]
        self.assertIn("current.draft.from_account", bank_block)
        self.assertIn("current.draft.to_account", bank_block)
        self.assertIn("current.draft.voucher_number", bank_block)
        self.assertIn("current.draft.voucher_date", bank_block)
        self.assertNotIn("current.ocr_from_account", bank_block)
        self.assertNotIn("current.seller_from_account", bank_block)
        check_block = xml.split('t-if="isCheck"')[1]
        self.assertIn("current.draft.check_number", check_block)
        self.assertIn("current.draft.check_bank", check_block)
        self.assertIn("current.draft.check_type", check_block)
        self.assertIn("current.draft.check_issue_date", check_block)
        self.assertIn("current.draft.check_payment_date", check_block)
        self.assertNotIn("current.ocr_check_number", check_block)
        self.assertNotIn("current.seller_check_number", check_block)
        draft_bindings = (
            "current.draft.document_type",
            "current.draft.amount",
            "current.draft.from_account",
            "current.draft.to_account",
            "current.draft.voucher_number",
            "current.draft.voucher_date",
            "current.draft.check_number",
            "current.draft.check_bank",
            "current.draft.check_type",
            "current.draft.check_issue_date",
            "current.draft.check_payment_date",
        )
        for binding in draft_bindings:
            nodes = root.xpath(f".//*[@t-att-value='{binding}']")
            self.assertTrue(nodes, f"editable draft control missing for {binding}")
            for node in nodes:
                self.assertFalse(
                    node.get("readonly") or node.get("disabled"),
                    f"{binding} must be editable",
                )
                self.assertTrue(
                    any(key.startswith("t-on-") for key in node.attrib),
                    f"{binding} must have input handlers",
                )
        self.assertFalse(
            root.xpath(".//*[@t-att-value='current.ocr_amount']"),
            "readonly OCR widgets must not remain in Document Review",
        )
        self.assertFalse(
            root.xpath(".//*[@t-att-value='current.seller_amount']"),
            "seller widgets must not remain in Document Review",
        )
        self.assertIn("t-on-input", panel)
        self.assertIn("onFieldInput", panel)
        self.assertIn("onFieldInput", action_js)
        self.assertIn("initDraftFromOcr", helpers)
        self.assertIn("buildApproveVals", helpers)
        self.assertIn("buildApproveVals", action_js)
        self.assertIn("isEmptyReviewValue", helpers)
        self.assertNotIn("seller-warning", xml)
        self.assertNotIn("seller_changed_fields", xml)
        self.assertNotIn("current.document_id", xml)
        self.assertNotIn("ocr_document_id", xml)
        self.assertNotIn("seller_document_id", xml)
        self.assertNotIn("collection_review_document_id", xml)
        self.assertNotIn("t-esc", xml)

    def test_owl_empty_provenance_still_loads(self):
        """Empty provenance MUST still bind the draft; OWL MUST NOT gate the panel on
        OCR."""
        xml = self._viewer_template_xml()
        helpers = self._helpers_js()
        self.assertIn("current.draft.amount", xml)
        self.assertIn("current.draft.document_type", xml)
        self.assertIn("initDraftFromOcr", helpers)
        self.assertNotIn('t-if="current.ocr_document_type"', xml)
        self.assertNotIn('t-if="current.ocr_amount"', xml)
        self.assertNotIn('t-if="current.draft.amount"', xml)
        self.assertNotIn("t-esc", xml)

    def test_build_approve_vals_sends_current_keys_only(self):
        """Approve RPC MUST send [[id], sheetId, current-only vals]."""
        helpers = self._helpers_js()
        action_js = self._action_js()
        self.assertIn("export function buildApproveVals", helpers)
        self.assertIn("export function initDraftFromOcr", helpers)
        self.assertIn("ocr_${name}", helpers.replace(" ", ""))
        self.assertIn("buildApproveVals", action_js)
        compact_action = "".join(action_js.split())
        self.assertRegex(
            compact_action,
            r'action_review_approve",\[\[this\.current\.id\],sheetId,buildApproveVals\(',
        )
        self.assertIn("REVIEW_EDITABLE_FIELDS", helpers)
        for name in (
            "document_type",
            "amount",
            "from_account",
            "to_account",
            "voucher_number",
            "voucher_date",
            "check_number",
            "check_bank",
            "check_type",
            "check_issue_date",
            "check_payment_date",
        ):
            self.assertIn(f'"{name}"', helpers)
