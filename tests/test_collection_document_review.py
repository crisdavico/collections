# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date
from pathlib import Path

from lxml import etree

from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from .test_collection_payment import PDF_B64, PNG_B64

_DOCUMENT_REVIEW_DIR = (
    Path(__file__).resolve().parents[1] / "static" / "src" / "document_review"
)


class TestCollectionDocumentReview(TransactionCase):
    """RED/GREEN: document review queue, approve/reject, and validate guard."""

    def _create_voucher(self, customer_identification="CUST-REV"):
        return self.env["collection.voucher"].create(
            {"customer_identification": customer_identification}
        )

    def _line_vals(self, voucher, **extra):
        vals = {
            "voucher_id": voucher.id,
            "document_type": "bank_transfer",
            "amount": 100.0,
        }
        vals.update(extra)
        if "document_id" not in vals:
            count = self.env["collection.voucher.line"].search_count([])
            vals["document_id"] = f"DOC-REV-{count}"
        return vals

    def _create_attached_line(self, voucher, **extra):
        extra.setdefault("attachment", PNG_B64)
        extra.setdefault("attachment_filename", "proof.png")
        return self.env["collection.voucher.line"].create(
            self._line_vals(voucher, **extra)
        )

    def _neutralize_preexisting_queue(self):
        """Make pre-existing devel rows ineligible so this transaction is isolated."""
        Line = self.env["collection.voucher.line"]
        queued = Line.get_review_queue()
        if not queued:
            return
        Line.browse([item["id"] for item in queued]).write(
            {"review_status": "rejected"}
        )

    def _assert_no_binary_in_payload(self, item):
        self.assertIsInstance(item, dict)
        self.assertNotIn("datas", item)
        self.assertNotIn("attachment", item)
        url = item.get("attachment_url")
        self.assertIsInstance(url, str)
        self.assertTrue(
            url.startswith("/web/content?"),
            f"attachment_url must be a /web/content route, got {url!r}",
        )
        self.assertIn("model=collection.voucher.line", url)
        self.assertIn("field=attachment", url)
        self.assertNotIn("datas", url)
        self.assertNotIn("base64", url.lower())
        self.assertFalse(url.startswith("data:"))
        for value in item.values():
            rendered = str(value)
            self.assertNotIn(PNG_B64, rendered)
            self.assertNotIn(PDF_B64, rendered)
            self.assertNotIn("data:image", rendered)
            self.assertNotIn("data:application/pdf", rendered)

    def _expected_content_url(self, line):
        return (
            "/web/content?model=collection.voucher.line"
            f"&id={line.id}&field=attachment"
            f"&filename={line.attachment_filename}"
        )

    def _viewer_template_xml(self):
        path = _DOCUMENT_REVIEW_DIR / "document_review_action.xml"
        return path.read_text(encoding="utf-8")

    def _viewer_template_root(self):
        return etree.fromstring(self._viewer_template_xml().encode())

    # --- 1.1 Queue eligibility + empty queue ---

    def test_queue_includes_only_eligible_pending_attached_new(self):
        """Eligible: voucher new, review pending, attachment present."""
        self._neutralize_preexisting_queue()
        Line = self.env["collection.voucher.line"]
        eligible_voucher = self._create_voucher("CUST-REV-ELIG")
        eligible = self._create_attached_line(
            eligible_voucher,
            document_id="DOC-REV-ELIG",
            from_account="ACC-FROM",
            to_account="ACC-TO",
            voucher_number="TRF-1",
            voucher_date=date(2026, 3, 15),
        )
        unattached = Line.create(
            self._line_vals(
                eligible_voucher,
                document_id="DOC-REV-NONE",
            )
        )
        validated_voucher = self._create_voucher("CUST-REV-VAL")
        validated_line = self._create_attached_line(
            validated_voucher, document_id="DOC-REV-VAL"
        )
        validated_voucher.write({"state": "validated"})
        decided = self._create_attached_line(
            self._create_voucher("CUST-REV-DEC"),
            document_id="DOC-REV-DEC",
        )
        decided.write({"review_status": "approved"})

        queue = Line.get_review_queue()
        queued_ids = [item["id"] for item in queue]
        self.assertIn(eligible.id, queued_ids)
        self.assertNotIn(unattached.id, queued_ids)
        self.assertNotIn(validated_line.id, queued_ids)
        self.assertNotIn(decided.id, queued_ids)

        payload = next(item for item in queue if item["id"] == eligible.id)
        self.assertEqual(payload["voucher_id"], eligible_voucher.id)
        self.assertEqual(payload["voucher_name"], eligible_voucher.name)
        self.assertEqual(payload["document_id"], "DOC-REV-ELIG")
        self.assertEqual(payload["document_type"], "bank_transfer")
        self.assertAlmostEqual(payload["amount"], 100.0, places=2)
        self.assertEqual(payload["from_account"], "ACC-FROM")
        self.assertEqual(payload["to_account"], "ACC-TO")
        self.assertEqual(payload["voucher_number"], "TRF-1")
        self.assertEqual(payload["voucher_date"], date(2026, 3, 15))
        self.assertEqual(payload["attachment_filename"], "proof.png")
        self.assertEqual(payload["position"], 1)
        self.assertEqual(payload["total"], 1)
        self.assertEqual(
            payload["attachment_url"],
            self._expected_content_url(eligible),
        )
        self._assert_no_binary_in_payload(payload)

    def test_queue_empty_when_no_eligible_lines(self):
        """Triangulation: ineligible-only setup yields an empty queue."""
        self._neutralize_preexisting_queue()
        Line = self.env["collection.voucher.line"]
        voucher = self._create_voucher("CUST-REV-EMPTY")
        Line.create(self._line_vals(voucher, document_id="DOC-REV-EMPTY-NONE"))
        attached = self._create_attached_line(
            voucher, document_id="DOC-REV-EMPTY-ATT"
        )
        attached.write({"review_status": "approved"})
        rejected_voucher = self._create_voucher("CUST-REV-EMPTY-REJ")
        self._create_attached_line(
            rejected_voucher, document_id="DOC-REV-EMPTY-REJ"
        )
        rejected_voucher.write({"state": "rejected"})

        queue = Line.get_review_queue()
        self.assertEqual(queue, [])

    def test_queue_orders_pdf_and_png_without_base64(self):
        """Triangulation: PDF and PNG proofs both queue with content URLs only."""
        self._neutralize_preexisting_queue()
        Line = self.env["collection.voucher.line"]
        first_voucher = self._create_voucher("CUST-REV-PNG")
        png_line = self._create_attached_line(
            first_voucher,
            document_id="DOC-REV-PNG",
            attachment=PNG_B64,
            attachment_filename="a.png",
        )
        second_voucher = self._create_voucher("CUST-REV-PDF")
        pdf_line = self._create_attached_line(
            second_voucher,
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
        queue = Line.get_review_queue()
        self.assertEqual([item["id"] for item in queue], [png_line.id, pdf_line.id])
        self.assertEqual(queue[0]["position"], 1)
        self.assertEqual(queue[1]["position"], 2)
        self.assertEqual(queue[0]["total"], 2)
        self.assertEqual(queue[1]["total"], 2)
        self.assertEqual(queue[1]["document_type"], "check")
        self.assertEqual(queue[1]["check_number"], "CHK-1")
        self.assertEqual(queue[1]["check_bank"], "Banco Nación")
        self.assertEqual(queue[1]["check_type"], "common")
        self.assertEqual(queue[1]["attachment_filename"], "b.pdf")
        self.assertEqual(
            queue[0]["attachment_url"],
            self._expected_content_url(png_line),
        )
        self.assertEqual(
            queue[1]["attachment_url"],
            self._expected_content_url(pdf_line),
        )
        for item in queue:
            self._assert_no_binary_in_payload(item)

    def test_queue_image_payload_is_web_content_url_only(self):
        """Image proofs expose /web/content URLs, never datas/base64."""
        self._neutralize_preexisting_queue()
        Line = self.env["collection.voucher.line"]
        png_line = self._create_attached_line(
            self._create_voucher("CUST-REV-IMG-PNG"),
            document_id="DOC-REV-IMG-PNG",
            attachment=PNG_B64,
            attachment_filename="proof.png",
        )
        jpg_line = self._create_attached_line(
            self._create_voucher("CUST-REV-IMG-JPG"),
            document_id="DOC-REV-IMG-JPG",
            attachment=PNG_B64,
            attachment_filename="proof.jpg",
        )
        queue = {item["id"]: item for item in Line.get_review_queue()}
        for line, filename in (
            (png_line, "proof.png"),
            (jpg_line, "proof.jpg"),
        ):
            payload = queue[line.id]
            self.assertEqual(payload["attachment_filename"], filename)
            self.assertEqual(
                payload["attachment_url"],
                self._expected_content_url(line),
            )
            self.assertIn(f"id={line.id}", payload["attachment_url"])
            self.assertIn(f"filename={filename}", payload["attachment_url"])
            self._assert_no_binary_in_payload(payload)

    def test_queue_pdf_payload_is_web_content_url_only(self):
        """Triangulation: PDF proofs use the same content route, never base64."""
        self._neutralize_preexisting_queue()
        Line = self.env["collection.voucher.line"]
        pdf_line = self._create_attached_line(
            self._create_voucher("CUST-REV-PDF-URL"),
            document_id="DOC-REV-PDF-URL",
            attachment=PDF_B64,
            attachment_filename="comprobante.pdf",
        )
        payload = next(
            item
            for item in Line.get_review_queue()
            if item["id"] == pdf_line.id
        )
        self.assertEqual(payload["attachment_filename"], "comprobante.pdf")
        self.assertEqual(
            payload["attachment_url"],
            self._expected_content_url(pdf_line),
        )
        self.assertIn(f"id={pdf_line.id}", payload["attachment_url"])
        self.assertIn("filename=comprobante.pdf", payload["attachment_url"])
        self.assertNotEqual(payload["attachment_url"], PNG_B64)
        self._assert_no_binary_in_payload(payload)

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
            any(
                node.get("t-att-src") == "current.attachment_url" for node in images
            ),
            "image viewer must bind current.attachment_url",
        )
        pdf_nodes = root.xpath(".//iframe") + root.xpath(".//embed")
        self.assertTrue(pdf_nodes, "PDF proofs must render via <iframe> or <embed>")
        self.assertTrue(
            any(
                node.get("t-att-src") == "current.attachment_url"
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

    # --- 1.2 Default pending/audit, approve, reject, aggregate ---

    def test_review_status_defaults_pending_and_copy_false(self):
        voucher = self._create_voucher("CUST-REV-DEF")
        line = self._create_attached_line(voucher, document_id="DOC-REV-DEF")
        self.assertEqual(line.review_status, "pending")
        self.assertFalse(line.reviewed_by)
        self.assertFalse(line.reviewed_at)
        line.write(
            {
                "review_status": "approved",
                "reviewed_by": self.env.user.id,
            }
        )
        clone = line.copy({"document_id": "DOC-REV-DEF-CLONE"})
        self.assertEqual(clone.review_status, "pending")
        self.assertFalse(clone.reviewed_by)
        self.assertFalse(clone.reviewed_at)

    def test_approve_persists_edits_and_records_audit(self):
        voucher = self._create_voucher("CUST-REV-APPR")
        line = self._create_attached_line(
            voucher,
            document_id="DOC-REV-APPR",
            amount=100.0,
            from_account="OLD-FROM",
        )
        line.action_review_approve(
            {
                "document_id": "HACKED-ID",
                "amount": 250.75,
                "from_account": "NEW-FROM",
                "to_account": "NEW-TO",
                "voucher_number": "TRF-EDIT",
                "voucher_date": date(2026, 5, 1),
            }
        )
        self.assertEqual(line.document_id, "DOC-REV-APPR")
        self.assertAlmostEqual(line.amount, 250.75, places=2)
        self.assertEqual(line.from_account, "NEW-FROM")
        self.assertEqual(line.to_account, "NEW-TO")
        self.assertEqual(line.voucher_number, "TRF-EDIT")
        self.assertEqual(line.voucher_date, date(2026, 5, 1))
        self.assertEqual(line.review_status, "approved")
        self.assertEqual(line.reviewed_by, self.env.user)
        self.assertTrue(line.reviewed_at)

    def test_approve_persists_check_fields(self):
        """Triangulation: check type-specific fields persist on approve."""
        voucher = self._create_voucher("CUST-REV-CHK")
        line = self._create_attached_line(
            voucher,
            document_id="DOC-REV-CHK",
            document_type="check",
            amount=10.0,
        )
        line.action_review_approve(
            {
                "document_type": "check",
                "amount": 80.0,
                "check_number": "CHK-9",
                "check_bank": "Banco Nación",
                "check_type": "deferred",
                "check_issue_date": date(2026, 1, 10),
                "check_payment_date": date(2026, 2, 10),
            }
        )
        self.assertEqual(line.check_number, "CHK-9")
        self.assertEqual(line.check_bank, "Banco Nación")
        self.assertEqual(line.check_type, "deferred")
        self.assertEqual(line.check_issue_date, date(2026, 1, 10))
        self.assertEqual(line.check_payment_date, date(2026, 2, 10))
        self.assertAlmostEqual(line.amount, 80.0, places=2)
        self.assertEqual(line.review_status, "approved")

    def test_reject_sets_rejected_and_records_audit(self):
        voucher = self._create_voucher("CUST-REV-REJ")
        line = self._create_attached_line(voucher, document_id="DOC-REV-REJ")
        line.action_review_reject()
        self.assertEqual(line.review_status, "rejected")
        self.assertEqual(line.reviewed_by, self.env.user)
        self.assertTrue(line.reviewed_at)
        self.assertEqual(voucher.state, "rejected")

    def test_aggregate_validate_when_all_attached_approved(self):
        voucher = self._create_voucher("CUST-REV-AGG")
        first = self._create_attached_line(voucher, document_id="DOC-REV-AGG-1")
        second = self._create_attached_line(
            voucher,
            document_id="DOC-REV-AGG-2",
            attachment=PDF_B64,
            attachment_filename="two.pdf",
        )
        unattached = self.env["collection.voucher.line"].create(
            self._line_vals(voucher, document_id="DOC-REV-AGG-NONE")
        )
        first.action_review_approve()
        self.assertEqual(first.review_status, "approved")
        self.assertEqual(voucher.state, "new")
        self.assertEqual(unattached.review_status, "pending")
        second.action_review_approve({"amount": 120.0})
        self.assertEqual(second.review_status, "approved")
        self.assertAlmostEqual(second.amount, 120.0, places=2)
        self.assertEqual(voucher.state, "validated")
        self.assertEqual(unattached.review_status, "pending")

    def test_line_reject_rejects_voucher_immediately(self):
        """Triangulation: rejecting one attached line rejects the voucher."""
        voucher = self._create_voucher("CUST-REV-REJ-V")
        pending = self._create_attached_line(voucher, document_id="DOC-REV-REJ-V1")
        sibling = self._create_attached_line(voucher, document_id="DOC-REV-REJ-V2")
        pending.action_review_reject()
        self.assertEqual(pending.review_status, "rejected")
        self.assertEqual(voucher.state, "rejected")
        self.assertEqual(sibling.review_status, "pending")

    # --- 1.3 Stale/concurrent, attachment reset, validate guard ---

    def test_stale_approve_and_reject_refuse_without_corruption(self):
        voucher = self._create_voucher("CUST-REV-STALE")
        line = self._create_attached_line(voucher, document_id="DOC-REV-STALE")
        line.action_review_approve({"amount": 40.0})
        self.assertEqual(line.review_status, "approved")
        self.assertEqual(voucher.state, "validated")
        with self.assertRaises(UserError):
            line.action_review_approve({"amount": 1.0})
        with self.assertRaises(UserError):
            line.action_review_reject()
        self.assertEqual(line.review_status, "approved")
        self.assertAlmostEqual(line.amount, 40.0, places=2)
        self.assertEqual(voucher.state, "validated")

    def test_stale_review_when_voucher_not_new_or_unattached(self):
        """Triangulation: ineligible voucher/attachment refuses both actions."""
        voucher = self._create_voucher("CUST-REV-STALE2")
        attached = self._create_attached_line(voucher, document_id="DOC-REV-STALE2")
        voucher.write({"state": "rejected"})
        with self.assertRaises(UserError):
            attached.action_review_approve()
        with self.assertRaises(UserError):
            attached.action_review_reject()
        self.assertEqual(attached.review_status, "pending")
        self.assertEqual(voucher.state, "rejected")

        open_voucher = self._create_voucher("CUST-REV-STALE3")
        unattached = self.env["collection.voucher.line"].create(
            self._line_vals(open_voucher, document_id="DOC-REV-STALE3")
        )
        with self.assertRaises(UserError):
            unattached.action_review_approve()
        with self.assertRaises(UserError):
            unattached.action_review_reject()
        self.assertEqual(unattached.review_status, "pending")
        self.assertEqual(open_voucher.state, "new")

    def test_attachment_write_resets_pending_and_clears_audit(self):
        voucher = self._create_voucher("CUST-REV-RESET")
        line = self._create_attached_line(voucher, document_id="DOC-REV-RESET")
        line.action_review_approve()
        self.assertEqual(line.review_status, "approved")
        self.assertTrue(line.reviewed_by)
        self.assertTrue(line.reviewed_at)
        line.write(
            {
                "attachment": PDF_B64,
                "attachment_filename": "replaced.pdf",
            }
        )
        self.assertEqual(line.review_status, "pending")
        self.assertFalse(line.reviewed_by)
        self.assertFalse(line.reviewed_at)
        self.assertEqual(line.attachment_filename, "replaced.pdf")

    def test_attachment_write_resets_rejected_line(self):
        """Triangulation: replacing a rejected line's file also reopens review."""
        voucher = self._create_voucher("CUST-REV-RESET-REJ")
        line = self._create_attached_line(voucher, document_id="DOC-REV-RESET-REJ")
        line.action_review_reject()
        self.assertEqual(line.review_status, "rejected")
        line.write(
            {
                "attachment": PNG_B64,
                "attachment_filename": "again.png",
            }
        )
        self.assertEqual(line.review_status, "pending")
        self.assertFalse(line.reviewed_by)
        self.assertFalse(line.reviewed_at)

    def test_action_validate_blocked_while_attached_pending(self):
        voucher = self._create_voucher("CUST-REV-GUARD")
        self._create_attached_line(voucher, document_id="DOC-REV-GUARD")
        with self.assertRaises(UserError):
            voucher.action_validate()
        self.assertEqual(voucher.state, "new")

    def test_action_validate_allows_unattached_pending_lines(self):
        """Unattached lines must not block validate; no-line vouchers stay valid."""
        voucher = self._create_voucher("CUST-REV-UNATT")
        self.env["collection.voucher.line"].create(
            self._line_vals(voucher, document_id="DOC-REV-UNATT")
        )
        voucher.action_validate()
        self.assertEqual(voucher.state, "validated")

        empty = self._create_voucher("CUST-REV-NOLINES")
        empty.action_validate()
        self.assertEqual(empty.state, "validated")
