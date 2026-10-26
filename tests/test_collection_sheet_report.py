# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date
from html import escape
from pathlib import Path
from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests import TransactionCase

from odoo.addons.collection.models.collection_common import privileged

from .test_collection_acl import TestCollectionAcl
from .test_collection_payment import (
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
    insert_company_like,
)

REPORT_XMLID = "collection.action_report_collection_sheet"
RENDER_MODEL = "report.collection.report_collection_sheet"
DOCUMENT_XMLID = "collection.report_collection_sheet_document"
WRAPPER_XMLID = "collection.report_collection_sheet"


class TestCollectionSheetReport(TransactionCase):
    """RED: bound qweb-pdf Planilla de Cobranza, HTML render, company ACL."""

    def setUp(self):
        super().setUp()
        self._doc_seq = 0
        self.seller = create_internal_seller(self.env, "planilla_seller_ana")
        self.seller.write({"name": "Planilla Seller Ana"})
        ensure_enabled_seller(self.env, self.seller)

    def _next_document_id(self, prefix="QWEB"):
        self._doc_seq += 1
        return f"{prefix}-{self._testMethodName}-{self._doc_seq}"

    def _create_sheet(self, *, seller=None, force_new=False, company=None, **extra):
        seller = seller or self.seller
        company = company or self.env.company
        ensure_enabled_seller(self.env, seller, company=company)
        extra.setdefault("company_id", company.id)
        if not force_new:
            existing = self.env["collection.sheet"].search(
                [
                    ("seller_id", "=", seller.id),
                    ("company_id", "=", extra["company_id"]),
                    ("state", "=", "open"),
                ],
                limit=1,
            )
            if existing:
                return existing
        return self.env["collection.sheet"].create({"seller_id": seller.id, **extra})

    def _create_voucher(self, partner, sheet, amount=100.0, **extra):
        ensure_enabled_seller(self.env, sheet.seller_id, company=sheet.company_id)
        vals = {
            "partner_id": partner.id,
            "document_type": extra.pop("document_type", "bank_transfer"),
            "document_id": extra.pop("document_id", self._next_document_id()),
            "seller_id": sheet.seller_id.id,
            "sheet_id": sheet.id,
            "company_id": sheet.company_id.id,
            "amount": amount,
        }
        vals.update(extra)
        return self.env["collection.voucher"].create(vals)

    def _line_vals(self, amount_applied=100.0, invoice_balance=100.0, **extra):
        vals = {
            "external_invoice_id": extra.pop(
                "external_invoice_id", self._next_document_id("INV")
            ),
            "invoice_number": extra.pop("invoice_number", "A-1"),
            "issue_date": extra.pop("issue_date", date(2026, 1, 1)),
            "due_date": extra.pop("due_date", date(2026, 1, 31)),
            "invoice_amount": extra.pop("invoice_amount", invoice_balance),
            "invoice_balance": invoice_balance,
            "invoice_state": extra.pop("invoice_state", "open"),
            "amount_applied": amount_applied,
            "document_kind": extra.pop("document_kind", "invoice"),
        }
        vals.update(extra)
        return vals

    def _create_allocation(self, sheet, partner, vouchers=None, lines=None, **extra):
        vals = {
            "sheet_id": sheet.id,
            "partner_id": partner.id,
        }
        if vouchers:
            vals["voucher_ids"] = [Command.set(vouchers.ids)]
        if lines is not None:
            vals["line_ids"] = [Command.create(line) for line in lines]
        vals.update(extra)
        return self.env["collection.allocation"].create(vals)

    def _populated_sheet(
        self,
        *,
        seller=None,
        partner_name="Cliente Norte SA",
        invoice_number="FAC-1001",
        amount=100.0,
    ):
        seller = seller or self.seller
        partner = dummy_customer_partner(self.env, customer=partner_name)
        sheet = self._create_sheet(seller=seller, force_new=True)
        voucher = self._create_voucher(partner, sheet, amount=amount)
        self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[
                self._line_vals(
                    amount_applied=amount,
                    invoice_balance=amount,
                    invoice_number=invoice_number,
                )
            ],
        )
        return sheet, partner

    def _second_seller(self, login):
        seller = create_internal_seller(self.env, login)
        ensure_enabled_seller(self.env, seller)
        return seller

    def _render_html(self, sheets):
        # devel's report_assets_common still lists website snippet SCSS while
        # website is not installed; skip asset nodes so HTML render stays in-process.
        with patch.object(
            type(self.env["ir.qweb"]), "_get_asset_nodes", return_value=[]
        ):
            html, report_type = (
                self.env["ir.actions.report"]
                .with_context(discard_logo_check=True)
                ._render_qweb_html(REPORT_XMLID, sheets.ids)
            )
        self.assertEqual(report_type, "html")
        if isinstance(html, bytes):
            self.assertFalse(html.startswith(b"%PDF"), html[:8])
            return html.decode()
        self.assertFalse(html.startswith("%PDF"), html[:8])
        return html

    def _create_partner(self, name):
        Partner = self.env["res.partner"].with_context(
            tracking_disable=True,
            mail_create_nolog=True,
            mail_notrack=True,
            mail_create_nosubscribe=True,
        )
        vals = {"name": name}
        if "autopost_bills" in Partner._fields:
            vals["autopost_bills"] = "ask"
            return Partner.create(vals)
        self.env.cr.execute(
            """
            SELECT 1
              FROM information_schema.columns
             WHERE table_name = 'res_partner'
               AND column_name = 'autopost_bills'
            """
        )
        if not self.env.cr.fetchone():
            return Partner.create(vals)
        self.env.cr.execute(
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
            (name, f"{name}@example.com", name),
        )
        return Partner.browse(self.env.cr.fetchone()[0])

    def _create_company(self, name):
        partner = self._create_partner(name)
        company = insert_company_like(self.env, name, partner.id)
        company._collection_copy_sequences()
        company._collection_enable_all_document_types()
        return company

    def _create_user(self, login, group_xmlid):
        return TestCollectionAcl._create_user.__func__(self, login, group_xmlid)

    def _partner_has_autopost_bills_column(self):
        return TestCollectionAcl._partner_has_autopost_bills_column.__func__(self)

    def _restrict_user_to_company(self, user, company):
        user.write({"company_ids": [Command.link(company.id)]})
        user.write(
            {
                "company_id": company.id,
                "company_ids": [Command.set([company.id])],
            }
        )

    def test_report_action_is_qweb_pdf_bound_a4_portrait(self):
        """Print menu XMLID MUST be qweb-pdf on collection.sheet with A4 portrait."""
        action = self.env.ref(REPORT_XMLID)
        self.assertEqual(action.report_type, "qweb-pdf")
        self.assertEqual(action.model, "collection.sheet")
        self.assertEqual(action.report_name, WRAPPER_XMLID)
        self.assertEqual(action.report_file, WRAPPER_XMLID)
        self.assertEqual(action.binding_type, "report")
        self.assertEqual(action.binding_model_id.model, "collection.sheet")
        self.assertIn("Planilla de Cobranza", action.print_report_name)
        paper = action.paperformat_id
        self.assertEqual(paper, self.env.ref("collection.paperformat_collection_sheet"))
        self.assertEqual(paper.format, "A4")
        self.assertEqual(paper.orientation, "Portrait")
        self.assertEqual(paper.margin_top, 20)
        self.assertEqual(paper.header_spacing, 5)
        self.assertEqual(paper.margin_bottom, 14)
        self.assertEqual(paper.margin_left, 6)
        self.assertEqual(paper.margin_right, 6)
        self.assertEqual(paper.dpi, 90)

    def _mark_validated_collections(self, vouchers):
        if vouchers:
            with privileged("collection_audited_state"):
                vouchers.write({"state": "validated_collections"})
        return vouchers

    def test_get_report_values_one_payload_per_doc(self):
        """`_get_report_values` MUST return one payload per sheet and set `o`."""
        sheet, _partner = self._populated_sheet()
        render = self.env[RENDER_MODEL]
        values = render._get_report_values(sheet.ids)
        self.assertEqual(len(values["payloads"]), 1)
        payload = values["payloads"][0]
        self.assertEqual(payload["sheet"], sheet)
        self.assertEqual(payload["reference"], sheet.name)
        self.assertEqual(values["o"], sheet)

        other_seller = self._second_seller("planilla_seller_beto")
        sheet_b, _partner_b = self._populated_sheet(
            seller=other_seller,
            partner_name="Cliente Sur SA",
            invoice_number="FAC-2002",
        )
        both = sheet | sheet_b
        values_both = render._get_report_values(both.ids)
        self.assertEqual(len(values_both["payloads"]), 2)
        self.assertEqual(
            [row["sheet"] for row in values_both["payloads"]],
            [sheet, sheet_b],
        )

    def test_pdf_in_all_five_states(self):
        """Bound PDF values MUST build for every legal sheet state."""
        sheet, _partner = self._populated_sheet()
        render = self.env[RENDER_MODEL]
        self._mark_validated_collections(sheet.voucher_ids)
        reference = sheet.name
        advances = (
            ("open", lambda: None),
            ("submitted", sheet.action_seller_close),
            ("proposal", sheet.action_confirm),
            ("closed", sheet.action_close),
            ("cancelled", sheet.action_cancel),
        )
        for target, advance in advances:
            with self.subTest(state=target):
                advance()
                self.assertEqual(sheet.state, target)
                values = render._get_report_values(sheet.ids)
                self.assertEqual(len(values["payloads"]), 1)
                payload = values["payloads"][0]
                self.assertEqual(payload["sheet"], sheet)
                self.assertEqual(payload["reference"], reference)
                self.assertEqual(payload["collected_total"], 100.0)

    def test_html_contains_reference_seller_partners_docs_banner(self):
        """HTML render MUST include reference, seller, partners, docs, banner."""
        sheet, partner_a = self._populated_sheet()
        partner_b = dummy_customer_partner(self.env, customer="Cliente Litoral SA")
        voucher_b = self._create_voucher(partner_b, sheet, amount=50.0)
        self._create_allocation(
            sheet,
            partner_b,
            vouchers=voucher_b,
            lines=[
                self._line_vals(
                    amount_applied=50.0,
                    invoice_balance=50.0,
                    invoice_number="FAC-1002",
                )
            ],
        )
        payload = sheet._collection_report_data()
        html = self._render_html(sheet)
        self.assertIn(sheet.name, html)
        self.assertIn("Planilla Seller Ana", html)
        self.assertIn(partner_a.name, html)
        self.assertIn(partner_b.name, html)
        self.assertIn("FAC-1001", html)
        self.assertIn("FAC-1002", html)
        self.assertIn(payload["recon"]["status_message"], html)
        self.assertNotIn("%PDF", html[:8])

    def test_two_sheets_render_two_page_divs(self):
        """Two sheets MUST render two `<div class="page">` in HTML."""
        sheet_a, _partner_a = self._populated_sheet()
        other_seller = self._second_seller("planilla_seller_cara")
        sheet_b, _partner_b = self._populated_sheet(
            seller=other_seller,
            partner_name="Cliente Patagonia SA",
            invoice_number="FAC-3003",
        )
        html = self._render_html(sheet_a | sheet_b)
        self.assertEqual(html.count('<div class="page">'), 2)
        self.assertIn(sheet_a.name, html)
        self.assertIn(sheet_b.name, html)

    def test_qweb_arch_has_no_company_layout_and_uses_t_out(self):
        """Report arch MUST NOT call company layouts and MUST NOT use t-esc."""
        wrapper = self.env.ref(WRAPPER_XMLID)
        document = self.env.ref(DOCUMENT_XMLID)
        combined = f"{wrapper.arch}{document.arch}"
        self.assertNotIn("web.external_layout", combined)
        self.assertNotIn("web.internal_layout", combined)
        self.assertNotIn("layout_document_title", combined)
        self.assertIn('class="article"', document.arch)
        self.assertIn("web.html_container", wrapper.arch)
        self.assertNotIn("t-esc", combined)
        self.assertIn("t-out", combined)
        self.assertIn("Datos de la Planilla", document.arch)
        self.assertIn("Totales", document.arch)
        self.assertIn("Clientes", document.arch)
        self.assertIn("Documentos Aplicados", document.arch)
        self.assertIn("Comprobantes", document.arch)
        self.assertIn("Conciliación del Vendedor", document.arch)
        self.assertIn("Moneda", document.arch)
        self.assertIn("Saldo Total", document.arch)
        self.assertIn("Saldo", document.arch)
        self.assertIn("o_cs_header_info", document.arch)
        self.assertIn("o_cs_date", document.arch)
        self.assertIn("o_cs_title", document.arch)
        self.assertIn("table-layout: fixed", document.arch)
        self.assertIn("Total Comisión Devengada", document.arch)

    def test_qweb_arch_uses_the_xlsx_vocabulary(self):
        """PDF labels MUST match the XLSX names; the old short forms MUST go."""
        document = self.env.ref(DOCUMENT_XMLID)
        for label in (
            "% Comisión Vendedor",
            "Cantidad de Clientes",
            "Cantidad de Comprobantes",
            "Documento",
            "Vencimiento",
            "Fecha de Emisión",
            "Fecha de Pago",
            "Nº Comprobante",
            "Composición de lo Entregado",
            "(−) Comisión Retenida por el Vendedor",
            "(=) A entregar por el Vendedor",
            "Entregado por el Vendedor",
            "(=) Diferencia",
            "Depósitos de clientes",
            "Depósitos del vendedor",
        ):
            with self.subTest(label=label):
                self.assertIn(label, document.arch)
        for old in (
            "Comisión %",
            "Motivo",
            "residual_reason",
            "<th>Número</th>",
            "Vto.",
            "<th>Emisión</th>",
            "<th>Pago</th>",
            "Nº Compr.",
            "<th>Retenido</th>",
            "Depósitos vendedor",
        ):
            with self.subTest(old=old):
                self.assertNotIn(old, document.arch)

    def test_html_footer_has_printed_date_and_pages_but_no_company(self):
        """Footer MUST show Impreso el and Página X de Y; never the company name."""
        sheet, _partner = self._populated_sheet()
        payload = sheet._collection_report_data()
        html = self._render_html(sheet)
        self.assertIn("o_cs_title", html)
        self.assertIn(f"Planilla de Cobranza — {sheet.name}", html)
        printed = payload["printed_on"].strftime("%d/%m/%Y")
        self.assertIn(f"Impreso el {printed}", html)
        self.assertIn('class="footer o_cs_footer"', html)
        self.assertIn("Página", html)
        self.assertIn('class="page"', html)
        self.assertIn('class="topage"', html)
        company_name = sheet.company_id.name
        self.assertNotIn(company_name, html)
        self.assertNotIn(escape(company_name), html)
        self.assertNotIn('class="header"', html)

    def test_html_verdict_comes_before_the_detail(self):
        """A entregar, Entregado, Diferencia and the banner MUST lead."""
        sheet, _partner = self._populated_sheet()
        payload = sheet._collection_report_data()
        html = self._render_html(sheet)
        verdict = html.index('class="o_cs_verdict"')
        for label in (
            "A entregar por el Vendedor",
            "Entregado por el Vendedor",
            "Diferencia",
        ):
            with self.subTest(label=label):
                self.assertLess(verdict, html.index(label, verdict))
        banner = html.index(payload["recon"]["status_message"])
        self.assertLess(verdict, banner)
        self.assertLess(banner, html.index("Datos de la Planilla"))
        self.assertLess(html.index("Datos de la Planilla"), html.index("Totales"))
        self.assertLess(html.index("Totales"), html.index('class="o_cs_customers"'))

    def test_html_has_grand_totals(self):
        """Clientes total, Total Aplicado across kinds, and Total Cobrado MUST print."""
        partner = dummy_customer_partner(self.env, customer="Grand Totals SA")
        sheet = self._create_sheet(force_new=True)
        transfer = self._create_voucher(partner, sheet, amount=111.25)
        check = self._create_voucher(
            partner,
            sheet,
            amount=222.5,
            document_type="check",
            check_number="CHK-GT",
            check_type="common",
            check_issue_date=date(2026, 3, 1),
            check_payment_date=date(2026, 3, 1),
        )
        self._create_allocation(
            sheet,
            partner,
            vouchers=transfer | check,
            lines=[
                self._line_vals(amount_applied=300.0, invoice_balance=300.0),
                self._line_vals(
                    amount_applied=33.75,
                    invoice_balance=40.0,
                    document_kind="quotation",
                ),
            ],
        )
        payload = sheet._collection_report_data()
        self.assertEqual(len(payload["document_blocks"]), 2)
        self.assertEqual(len(payload["voucher_blocks"]), 2)
        html = self._render_html(sheet)
        # 333.75 is neither block subtotal: only a grand total prints it.
        applied = html[html.index('class="o_cs_grand_applied') :]
        self.assertIn("333.75", applied[: applied.index("</tr>")])
        collected = html[html.index('class="o_cs_grand_collected') :]
        self.assertIn("333.75", collected[: collected.index("</tr>")])
        customers = html[html.index('class="o_cs_customers_total') :]
        self.assertIn("340.00", customers[: customers.index("</tr>")])

    def test_html_reconciliation_reads_as_a_calculation(self):
        """Recon MUST read Cobrado, Retenida, A entregar, Entregado, Diferencia."""
        sheet, _partner = self._populated_sheet()
        html = self._render_html(sheet)
        recon = html[html.index("Conciliación del Vendedor") :]
        positions = [
            recon.index(label)
            for label in (
                "Total Cobrado",
                "(−) Comisión Retenida por el Vendedor",
                "(=) A entregar por el Vendedor",
                "Entregado por el Vendedor",
                "(=) Diferencia",
                "Composición de lo Entregado",
            )
        ]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("el cliente depositó en la cuenta de la empresa", recon)
        self.assertIn("el vendedor depositó en el banco el efectivo cobrado", recon)

    def test_html_has_signature_lines(self):
        """The PDF MUST end with seller and receiver signature lines."""
        sheet, _partner = self._populated_sheet()
        html = self._render_html(sheet)
        self.assertIn("Firma del vendedor", html)
        self.assertIn("Recibió", html)
        self.assertLess(
            html.index("Conciliación del Vendedor"),
            html.index('class="o_cs_signatures"'),
        )

    def test_html_mismatch_names_both_amounts_and_gap(self):
        """Mismatch MUST print the allocated total, the voucher total and the gap."""
        sheet, partner = self._populated_sheet(amount=100.0)
        self._create_voucher(partner, sheet, amount=40.0)
        payload = sheet._collection_report_data()
        self.assertTrue(payload["mismatch"])
        self.assertEqual(payload["allocated_collected"], 100.0)
        self.assertEqual(payload["collected_total"], 140.0)
        html = self._render_html(sheet)
        warning = html[html.index('class="o_cs_mismatch"') :]
        warning = warning[: warning.index("</div>")]
        self.assertIn("100.00", warning)
        self.assertIn("140.00", warning)
        self.assertIn("40.00", warning)

    def test_html_prints_currency_saldo_and_comprobante_fields(self):
        """HTML MUST include Moneda, Facturas saldo, voucher/check numbers."""
        partner = dummy_customer_partner(self.env, customer="PDF-COMP")
        sheet = self._create_sheet(seller=self.seller, force_new=True)
        transfer = self._create_voucher(
            partner,
            sheet,
            amount=80.0,
            document_type="bank_transfer",
            voucher_number="TRF-PDF",
        )
        check = self._create_voucher(
            partner,
            sheet,
            amount=20.0,
            document_type="check",
            check_number="CHK-PDF",
            check_bank="Banco Nación",
            check_type="deferred",
            check_issue_date=date(2026, 3, 1),
            check_payment_date=date(2026, 4, 15),
        )
        self._create_allocation(
            sheet,
            partner,
            vouchers=transfer | check,
            lines=[
                self._line_vals(
                    amount_applied=100.0,
                    invoice_balance=432.25,
                    invoice_number="FAC-PDF",
                    due_date=date(2026, 8, 9),
                )
            ],
        )
        payload = sheet._collection_report_data()
        html = self._render_html(sheet)
        self.assertIn(payload["currency_name"], html)
        self.assertIn("Saldo Total", html)
        self.assertIn("Total Comisión", html)
        self.assertIn("432.25", html)
        self.assertIn("TRF-PDF", html)
        self.assertNotIn(transfer.name, html)
        self.assertIn("CHK-PDF", html)
        self.assertNotIn(check.name, html)
        self.assertIn("Banco Nación", html)
        self.assertIn("Diferido", html)
        self.assertIn("09/08/2026", html)
        self.assertIn("01/03/2026", html)
        self.assertIn("15/04/2026", html)
        self.assertIn("o_cs_header_info", html)
        self.assertIn("o_cs_date", html)

    def test_company_b_access_error_on_data_and_render(self):
        """Company-B users MUST get AccessError on payload data() and HTML render."""
        user_a = self._create_user("rpt_company_a", "collection.group_collection_user")
        self._restrict_user_to_company(user_a, self.env.company)

        company_b = self._create_company("Report Hidden Co B")
        seller_b = create_internal_seller(self.env, "planilla_hidden_seller")
        seller_b.write({"name": "Hidden Seller B"})
        sheet_b = self._create_sheet(seller=seller_b, force_new=True, company=company_b)
        partner = dummy_customer_partner(self.env, customer="Hidden Cliente SA")
        voucher = self._create_voucher(partner, sheet_b, amount=100.0)
        self._create_allocation(
            sheet_b,
            partner,
            vouchers=voucher,
            lines=[
                self._line_vals(
                    amount_applied=100.0,
                    invoice_balance=100.0,
                    invoice_number="FAC-B-1",
                )
            ],
        )

        hidden = self.env["collection.sheet"].with_user(user_a).browse(sheet_b.id)
        with self.assertRaises(AccessError):
            hidden._collection_report_data()

        render = self.env[RENDER_MODEL].with_user(user_a)
        with self.assertRaises(AccessError):
            render._get_report_values(sheet_b.ids)

        report = self.env["ir.actions.report"].with_user(user_a)
        with self.assertRaises(AccessError):
            report._render_qweb_html(REPORT_XMLID, sheet_b.ids)

        render_src = (
            Path(__file__).resolve().parents[1]
            / "report"
            / "collection_sheet_report_render.py"
        ).read_text(encoding="utf-8")
        code = "\n".join(
            line
            for line in render_src.splitlines()
            if not line.lstrip().startswith("#")
        )
        self.assertNotIn(".sudo(", code)
        self.assertNotIn("sudo()", code)
