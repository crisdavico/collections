# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import zipfile
from datetime import date
from io import BytesIO
from pathlib import Path

from lxml import etree
from openpyxl import load_workbook

from odoo.exceptions import AccessError, UserError
from odoo.fields import Command
from odoo.tests import TransactionCase

from .test_collection_acl import TestCollectionAcl
from .test_collection_payment import (
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
)

XLSX_MODEL = "collection.sheet.xlsx"
XLSX_MIMETYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
HEADER_MERGES = {
    "A1:E1",
    "F1:H1",
    "A2:E2",
    "F2:H2",
    "A3:H3",
    "A4:H4",
    "A6:H6",
    "A7:B7",
    "C7:D7",
    "E7:F7",
    "G7:H7",
}
BANNER_FILLS = {
    "balanced": "C6EFCE",
    "in_favor": "FFEB9C",
    "outstanding": "FFC7CE",
}
SHEET_FORM_XML = Path(__file__).resolve().parents[1] / "views" / "collection_views.xml"
XLSX_SOURCE = (
    Path(__file__).resolve().parents[1] / "report" / "collection_sheet_xlsx.py"
)
ACTION_SOURCE = (
    Path(__file__).resolve().parents[1] / "models" / "collection_sheet_report.py"
)


def _code_without_comments(path):
    source = path.read_text(encoding="utf-8")
    return "\n".join(
        line for line in source.splitlines() if not line.lstrip().startswith("#")
    )


def _fill_rgb(cell):
    color = cell.fill.fgColor
    rgb = getattr(color, "rgb", None)
    if rgb is None:
        theme = getattr(color, "theme", None)
        return "" if theme is None else f"theme:{theme}"
    return str(rgb).upper()


def _is_same_date(value, expected):
    if value == expected:
        return True
    if getattr(value, "date", None) and callable(value.date):
        try:
            return value.date() == expected
        except TypeError:
            return False
    year = getattr(value, "year", None)
    month = getattr(value, "month", None)
    day = getattr(value, "day", None)
    return (year, month, day) == (expected.year, expected.month, expected.day)


class TestCollectionSheetXlsx(TransactionCase):
    """RED: Planilla XLSX zip, freeze, cached SUM, act_url, ACL."""

    def setUp(self):
        super().setUp()
        self._doc_seq = 0
        self.seller = create_internal_seller(self.env, "xlsx_seller_ana")
        self.seller.write({"name": "XLSX Seller Ana"})
        ensure_enabled_seller(self.env, self.seller)

    def _next_document_id(self, prefix="XLSX"):
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
        extra.setdefault("seller_id", seller.id)
        return self.env["collection.sheet"].create(extra)

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
        company=None,
        partner_name="Cliente Norte SA",
        invoice_number="FAC-1001",
        amount=100.0,
        document_type="bank_transfer",
        commission_percent=0.0,
        cash_on_hand=0.0,
        commission_withheld=0.0,
    ):
        seller = seller or self.seller
        partner = dummy_customer_partner(self.env, customer=partner_name)
        sheet = self._create_sheet(
            seller=seller,
            force_new=True,
            company=company,
            commission_percent=commission_percent,
            cash_on_hand=cash_on_hand,
            commission_withheld=commission_withheld,
        )
        voucher = self._create_voucher(
            partner, sheet, amount=amount, document_type=document_type
        )
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

    def _render_xlsx(self, sheet):
        self.assertIn(XLSX_MODEL, self.env)
        payload = sheet._collection_report_data()
        content = self.env[XLSX_MODEL]._render_xlsx(payload)
        self.assertIsInstance(content, (bytes, bytearray), type(content))
        return bytes(content), payload

    def _load(self, content, data_only=False):
        return load_workbook(BytesIO(content), data_only=data_only)

    def _sheet_form_root(self):
        tree = etree.parse(str(SHEET_FORM_XML))
        records = tree.xpath("//record[@id='view_collection_sheet_form']")
        self.assertTrue(records, "view_collection_sheet_form must exist")
        forms = records[0].xpath(".//form")
        self.assertTrue(forms, "sheet form arch must contain <form>")
        return forms[0]

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
        self.env.cr.execute(
            """
            INSERT INTO res_company (
                name, partner_id, currency_id,
                fiscalyear_last_day, fiscalyear_last_month,
                account_price_include, cost_method, horizon_days,
                inventory_period, layout_background, security_lead
            )
            SELECT
                %s, %s, currency_id,
                fiscalyear_last_day, fiscalyear_last_month,
                account_price_include, cost_method, horizon_days,
                inventory_period, layout_background, security_lead
            FROM res_company
            WHERE id = %s
            RETURNING id
            """,
            (name, partner.id, self.env.company.id),
        )
        company = self.env["res.company"].browse(self.env.cr.fetchone()[0])
        company.invalidate_recordset()
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

    def test_xlsx_bytes_are_zip_with_workbook(self):
        """XLSX bytes MUST start PK and the zip MUST contain xl/workbook.xml."""
        sheet, _partner = self._populated_sheet()
        content, _payload = self._render_xlsx(sheet)
        self.assertTrue(content.startswith(b"PK"), content[:8])
        with zipfile.ZipFile(BytesIO(content)) as zipped:
            names = zipped.namelist()
        self.assertIn("xl/workbook.xml", names)

    def test_xlsx_print_setup_freeze_and_column_width(self):
        """Worksheet MUST freeze A6, landscape paper 9, fit width, titles 1:4."""
        sheet, _partner = self._populated_sheet()
        content, _payload = self._render_xlsx(sheet)
        workbook = self._load(content)
        worksheet = workbook.active
        self.assertEqual(worksheet.title, "Planilla de Cobranza")
        self.assertEqual(worksheet.freeze_panes, "A6")
        self.assertEqual(worksheet.page_setup.orientation, "landscape")
        self.assertEqual(worksheet.page_setup.paperSize, 9)
        self.assertEqual(worksheet.page_setup.fitToWidth, 1)
        title_rows = (worksheet.print_title_rows or "").replace("$", "")
        self.assertEqual(title_rows, "1:4")
        self.assertEqual(worksheet.column_dimensions["B"].width, 32)

    def test_xlsx_merges_and_number_formats(self):
        """Header merges and money/percent formats MUST match the template."""
        sheet, _partner = self._populated_sheet(commission_percent=4.5)
        content, _payload = self._render_xlsx(sheet)
        worksheet = self._load(content).active
        merges = {str(item) for item in worksheet.merged_cells.ranges}
        missing = HEADER_MERGES - merges
        self.assertFalse(missing, f"missing merges: {sorted(missing)}")
        formats = {
            cell.number_format
            for row in worksheet.iter_rows()
            for cell in row
            if cell.number_format and cell.number_format != "General"
        }
        self.assertTrue(
            any("#,##0.00" in (fmt or "") for fmt in formats),
            formats,
        )
        self.assertTrue(
            any("0.0%" in (fmt or "") for fmt in formats),
            formats,
        )
        self.assertTrue(
            any("$" in (fmt or "") for fmt in formats),
            formats,
        )

    def test_xlsx_cached_subtotals_match_payload(self):
        """data_only cached SUM cells MUST equal payload totals and not be None."""
        sheet, _partner = self._populated_sheet(amount=125.5, commission_percent=4.5)
        content, payload = self._render_xlsx(sheet)
        formulas = self._load(content).active
        cached = self._load(content, data_only=True).active
        formula_coords = []
        for row in formulas.iter_rows():
            for cell in row:
                value = cell.value
                if isinstance(value, str) and "SUM" in value.upper():
                    formula_coords.append(cell.coordinate)
                    cached_value = cached[cell.coordinate].value
                    self.assertIsNotNone(
                        cached_value,
                        f"{cell.coordinate} formula {value} cached None",
                    )
        self.assertTrue(formula_coords, "workbook MUST contain SUM formulas")
        cached_numbers = []
        for row in cached.iter_rows():
            for cell in row:
                if isinstance(cell.value, (int, float)):
                    cached_numbers.append(float(cell.value))

        def _assert_cached(amount, label):
            matches = [
                number for number in cached_numbers if abs(number - amount) < 0.0001
            ]
            self.assertTrue(matches, f"{label}={amount} missing from cached cells")

        _assert_cached(payload["collected_total"], "collected_total")
        _assert_cached(payload["applied_total"], "applied_total")
        _assert_cached(payload["customer_totals"]["debt"], "customer debt")
        _assert_cached(payload["customer_totals"]["collected"], "customer collected")
        _assert_cached(payload["recon"]["difference"], "recon difference")
        _assert_cached(payload["tendered"]["total"], "tendered total")

    def test_xlsx_percent_scale_4_5_is_excel_fraction(self):
        """Odoo commission_percent 4.5 MUST be stored as 0.045 with 0.0% format."""
        sheet, _partner = self._populated_sheet(commission_percent=4.5)
        content, payload = self._render_xlsx(sheet)
        self.assertEqual(payload["commission_percent"], 4.5)
        worksheet = self._load(content).active
        percent_cells = []
        for row in worksheet.iter_rows():
            for cell in row:
                fmt = cell.number_format or ""
                if "0.0%" in fmt and cell.value is not None:
                    percent_cells.append(cell)
        self.assertTrue(percent_cells, "workbook MUST contain a 0.0% cell")
        for cell in percent_cells:
            self.assertAlmostEqual(cell.value, 0.045, places=6, msg=cell.coordinate)

    def test_xlsx_banner_text_and_fill_all_three_statuses(self):
        """Banner text and fill MUST follow recon.status for all three states."""
        cases = (
            ("xlsx_banner_bal", "bank_transfer", 0.0, "balanced"),
            ("xlsx_banner_fav", "bank_transfer", 50.0, "in_favor"),
            ("xlsx_banner_out", "unsupported", 0.0, "outstanding"),
        )
        for login, document_type, cash, status in cases:
            seller = create_internal_seller(self.env, login)
            ensure_enabled_seller(self.env, seller)
            sheet, _partner = self._populated_sheet(
                seller=seller,
                partner_name=f"Banner {status}",
                document_type=document_type,
                cash_on_hand=cash,
            )
            content, payload = self._render_xlsx(sheet)
            self.assertEqual(payload["recon"]["status"], status)
            message = payload["recon"]["status_message"]
            self.assertTrue(message)
            worksheet = self._load(content).active
            banner = None
            for row in worksheet.iter_rows():
                for cell in row:
                    value = cell.value
                    if isinstance(value, str) and message in value:
                        banner = cell
                        break
                if banner is not None:
                    break
            self.assertIsNotNone(banner, f"{status}: banner text {message!r} missing")
            rgb = _fill_rgb(banner)
            self.assertIn(
                BANNER_FILLS[status],
                rgb,
                f"{status} fill {rgb} must include {BANNER_FILLS[status]}",
            )

    def test_action_print_xlsx_act_url_and_attachment(self):
        """action_print_xlsx MUST return act_url download and one xlsx attachment."""
        sheet, _partner = self._populated_sheet()
        action = sheet.action_print_xlsx()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertEqual(action["target"], "download")
        self.assertTrue(action["url"].startswith("/web/content/"))
        self.assertTrue(action["url"].endswith("?download=true"))
        attachment_id = int(action["url"].split("/")[3].split("?")[0])
        attachment = self.env["ir.attachment"].browse(attachment_id)
        self.assertTrue(attachment.exists())
        self.assertEqual(attachment.res_model, "collection.sheet")
        self.assertEqual(attachment.res_id, sheet.id)
        self.assertEqual(attachment.mimetype, XLSX_MIMETYPE)
        self.assertTrue(attachment.name.endswith(".xlsx"))
        self.assertNotIn("/", attachment.name)
        raw = attachment.raw or b""
        self.assertTrue(raw.startswith(b"PK"), raw[:8])

    def test_xlsx_in_all_four_states(self):
        """Export XLSX MUST download in every sheet state without a state UserError."""
        sheet, _partner = self._populated_sheet()
        if sheet.voucher_ids:
            sheet.voucher_ids.with_context(collection_audited_state=True).write(
                {"state": "validated_collections"}
            )
        advances = (
            ("open", lambda: None),
            ("proposal", sheet.action_confirm),
            ("closed", sheet.action_close),
            ("cancelled", sheet.action_cancel),
        )
        for target, advance in advances:
            with self.subTest(state=target):
                advance()
                self.assertEqual(sheet.state, target)
                action = sheet.action_print_xlsx()
                self.assertEqual(action["type"], "ir.actions.act_url")
                self.assertTrue(action["url"].endswith("?download=true"))
                attachment_id = int(action["url"].split("/")[3].split("?")[0])
                raw = self.env["ir.attachment"].browse(attachment_id).raw or b""
                self.assertTrue(raw.startswith(b"PK"), raw[:8])

    def test_unsaved_xlsx_refused(self):
        """Unsaved sheets MUST raise UserError and MUST NOT emit an XLSX download."""
        sheet = self.env["collection.sheet"].new(
            {"seller_id": self.seller.id, "company_id": self.env.company.id}
        )
        with self.assertRaises(UserError) as error:
            sheet.action_print_xlsx()
        self.assertIn("saved", str(error.exception).lower())

    def test_action_print_xlsx_second_call_replaces_attachment(self):
        """A second Export MUST replace the same-name attachment, not duplicate."""
        sheet, _partner = self._populated_sheet()
        first = sheet.action_print_xlsx()
        second = sheet.action_print_xlsx()
        filename = f"{(sheet.name or '').replace('/', '-')}.xlsx"
        attachments = self.env["ir.attachment"].search(
            [
                ("res_model", "=", "collection.sheet"),
                ("res_id", "=", sheet.id),
                ("name", "=", filename),
            ]
        )
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments.mimetype, XLSX_MIMETYPE)
        first_id = int(first["url"].split("/")[3].split("?")[0])
        second_id = int(second["url"].split("/")[3].split("?")[0])
        self.assertEqual(attachments.id, second_id)
        self.assertFalse(self.env["ir.attachment"].browse(first_id).exists())

    def test_header_xlsx_button_last_before_state(self):
        """Export XLSX MUST be the last header object button before state."""
        form = self._sheet_form_root()
        header = form.xpath("./header")
        self.assertTrue(header, "sheet form must have a header")
        buttons = [node for node in header[0].xpath("./*") if node.tag == "button"]
        names = [node.get("name") for node in buttons]
        self.assertIn("action_open_document_review", names)
        self.assertNotIn("action_open_voucher_reassign", names)
        self.assertNotIn("action_reopen", names)
        self.assertEqual(names[-1], "action_print_xlsx")
        xlsx = buttons[-1]
        self.assertEqual(xlsx.get("type"), "object")
        self.assertEqual(xlsx.get("string"), "Export XLSX")
        following = xlsx.getnext()
        self.assertIsNotNone(following)
        self.assertEqual(following.tag, "field")
        self.assertEqual(following.get("name"), "state")

    def test_sheet_form_three_notebook_pages_recon_second_group(self):
        """Notebook MUST have three pages; recon fields stay in a second inner group."""
        form = self._sheet_form_root()
        notebooks = form.xpath(".//notebook")
        self.assertEqual(len(notebooks), 1)
        pages = notebooks[0].xpath("./page")
        self.assertEqual(
            [page.get("string") for page in pages],
            ["Allocations", "Vouchers", "Debt"],
        )
        groups = form.xpath("./sheet/group")
        self.assertTrue(groups, "sheet body must have an outer group")
        inner = groups[0].xpath("./group")
        self.assertGreaterEqual(
            len(inner),
            2,
            "recon fields MUST live in a second inner group, not a new page",
        )
        recon_names = [node.get("name") for node in inner[1].xpath("./field")]
        for field_name in (
            "commission_percent",
            "cash_on_hand",
            "commission_withheld",
        ):
            self.assertIn(field_name, recon_names, field_name)

    def test_company_b_access_error_on_xlsx(self):
        """Company-B users MUST get AccessError on action_print_xlsx with no file."""
        user_a = self._create_user("xlsx_company_a", "base.group_user")
        self._restrict_user_to_company(user_a, self.env.company)

        company_b = self._create_company("XLSX Hidden Co B")
        seller_b = create_internal_seller(self.env, "xlsx_hidden_seller")
        seller_b.write({"name": "Hidden Seller B"})
        sheet_b, _partner = self._populated_sheet(
            seller=seller_b,
            company=company_b,
            partner_name="Hidden Cliente XLSX",
        )
        hidden = self.env["collection.sheet"].with_user(user_a).browse(sheet_b.id)
        before = self.env["ir.attachment"].search(
            [
                ("res_model", "=", "collection.sheet"),
                ("res_id", "=", sheet_b.id),
            ]
        )
        with self.assertRaises(AccessError):
            hidden.action_print_xlsx()
        after = self.env["ir.attachment"].search(
            [
                ("res_model", "=", "collection.sheet"),
                ("res_id", "=", sheet_b.id),
            ]
        )
        self.assertEqual(after, before)

    def test_xlsx_sources_have_no_sudo(self):
        """XLSX writer and action_print_xlsx MUST NOT call sudo()."""
        self.assertTrue(XLSX_SOURCE.is_file(), XLSX_SOURCE)
        xlsx_code = _code_without_comments(XLSX_SOURCE)
        self.assertNotIn(".sudo(", xlsx_code)
        self.assertNotIn("sudo()", xlsx_code)
        action_code = _code_without_comments(ACTION_SOURCE)
        self.assertNotIn(".sudo(", action_code)
        self.assertNotIn("sudo()", action_code)

    def _cell_with_value(self, worksheet, expected):
        for row in worksheet.iter_rows():
            for cell in row:
                if cell.value == expected:
                    return cell
        return None

    def _cell_with_date(self, worksheet, expected):
        for row in worksheet.iter_rows():
            for cell in row:
                if expected and _is_same_date(cell.value, expected):
                    return cell
        return None

    def test_xlsx_header_currency_and_invoice_balance(self):
        """XLSX MUST print currency_name next to Moneda and invoice saldo."""
        partner = dummy_customer_partner(self.env, customer="XLSX-SALDO")
        sheet = self._create_sheet(force_new=True)
        voucher = self._create_voucher(partner, sheet, amount=80.0)
        self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[
                self._line_vals(
                    amount_applied=80.0,
                    invoice_balance=321.5,
                    invoice_number="FAC-SALDO",
                    due_date=date(2026, 6, 15),
                )
            ],
        )
        content, payload = self._render_xlsx(sheet)
        worksheet = self._load(content).active
        moneda = self._cell_with_value(worksheet, "Moneda")
        self.assertIsNotNone(moneda)
        currency_cell = self._cell_with_value(worksheet, payload["currency_name"])
        self.assertIsNotNone(currency_cell)
        self.assertEqual(currency_cell.row, moneda.row)
        saldo_header = self._cell_with_value(worksheet, "Saldo")
        self.assertIsNotNone(saldo_header)
        saldo = worksheet.cell(saldo_header.row + 1, saldo_header.column)
        self.assertAlmostEqual(float(saldo.value), 321.5, places=2)
        debt_header = self._cell_with_value(worksheet, "Saldo Total")
        self.assertIsNotNone(debt_header)
        cobrado_header = self._cell_with_value(worksheet, "Cobrado")
        self.assertIsNotNone(cobrado_header)
        self.assertEqual(debt_header.row, cobrado_header.row)
        self.assertEqual(debt_header.column, cobrado_header.column - 1)
        debt = worksheet.cell(debt_header.row + 1, debt_header.column)
        cobrado = worksheet.cell(debt_header.row + 1, debt_header.column + 1)
        aplicado = worksheet.cell(debt_header.row + 1, debt_header.column + 2)
        remanente = worksheet.cell(debt_header.row + 1, debt_header.column + 3)
        self.assertIn("SUMIF", str(debt.value).upper())
        self.assertIn("SUMIF", str(cobrado.value).upper())
        self.assertIn("SUMIF", str(aplicado.value).upper())
        self.assertRegex(str(remanente.value).replace("$", ""), r"^=C\d+-E\d+$")
        invoice_number = self._cell_with_value(worksheet, "FAC-SALDO")
        self.assertIsNotNone(invoice_number)
        self.assertIn(str(invoice_number.row), str(debt.value))
        self.assertIn("$E$", str(debt.value).upper())
        self.assertIn("$H$", str(cobrado.value).upper())
        self.assertIn("$F$", str(aplicado.value).upper())
        cached = self._load(content, data_only=True).active
        self.assertAlmostEqual(
            float(cached.cell(debt.row, debt.column).value), 321.5, places=2
        )
        self.assertAlmostEqual(
            float(cached.cell(cobrado.row, cobrado.column).value), 80.0, places=2
        )
        self.assertAlmostEqual(
            float(cached.cell(aplicado.row, aplicado.column).value), 80.0, places=2
        )
        self.assertAlmostEqual(
            float(cached.cell(remanente.row, remanente.column).value), 241.5, places=2
        )
        resumen_rem = self._cell_with_value(worksheet, "Remanente")
        self.assertIsNotNone(resumen_rem)
        resumen_formula = str(
            worksheet.cell(resumen_rem.row, resumen_rem.column + 2).value or ""
        )
        self.assertNotIn("C11-G11", resumen_formula.replace("$", ""))
        self.assertIn("=", resumen_formula)

    def test_xlsx_transfer_and_check_comprobante_fields(self):
        """XLSX MUST print voucher_number / check details, never the COL name."""
        partner = dummy_customer_partner(self.env, customer="XLSX-COMP")
        sheet = self._create_sheet(force_new=True)
        transfer = self._create_voucher(
            partner,
            sheet,
            amount=10.0,
            document_type="bank_transfer",
            voucher_number="TRF-XLSX",
        )
        check = self._create_voucher(
            partner,
            sheet,
            amount=20.0,
            document_type="check",
            check_number="CHK-XLSX",
            check_bank="Banco Galicia",
            check_type="common",
            check_issue_date=date(2026, 3, 1),
            check_payment_date=date(2026, 4, 15),
        )
        self._create_allocation(
            sheet,
            partner,
            vouchers=transfer | check,
            lines=[self._line_vals(amount_applied=30.0, invoice_balance=30.0)],
        )
        content, _payload = self._render_xlsx(sheet)
        worksheet = self._load(content).active
        self.assertIsNotNone(self._cell_with_value(worksheet, "TRF-XLSX"))
        self.assertIsNone(self._cell_with_value(worksheet, transfer.name))
        self.assertIsNotNone(self._cell_with_value(worksheet, "CHK-XLSX"))
        self.assertIsNone(self._cell_with_value(worksheet, check.name))
        self.assertIsNotNone(self._cell_with_value(worksheet, "Banco Galicia"))
        self.assertIsNotNone(self._cell_with_value(worksheet, "Común"))
        self.assertIsNotNone(self._cell_with_date(worksheet, date(2026, 4, 15)))

    def test_xlsx_header_values_right_and_table_dates_centered(self):
        """Header field values MUST be right-aligned; table dates centered."""
        partner = dummy_customer_partner(self.env, customer="XLSX-ALIGN")
        sheet = self._create_sheet(force_new=True)
        voucher = self._create_voucher(
            partner,
            sheet,
            amount=50.0,
            document_type="bank_transfer",
            voucher_number="TRF-ALIGN",
        )
        self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[
                self._line_vals(
                    amount_applied=50.0,
                    invoice_balance=50.0,
                    due_date=date(2026, 7, 20),
                )
            ],
        )
        content, payload = self._render_xlsx(sheet)
        worksheet = self._load(content).active
        moneda_value = self._cell_with_value(worksheet, payload["currency_name"])
        self.assertIsNotNone(moneda_value)
        self.assertEqual(moneda_value.alignment.horizontal, "right")
        seller = self._cell_with_value(worksheet, payload["seller_name"])
        self.assertIsNotNone(seller)
        self.assertEqual(seller.alignment.horizontal, "right")
        due = self._cell_with_date(worksheet, date(2026, 7, 20))
        self.assertIsNotNone(due)
        self.assertEqual(due.alignment.horizontal, "center")
        voucher_date = payload["voucher_blocks"][0]["rows"][0]["date"]
        date_cell = self._cell_with_date(worksheet, voucher_date)
        self.assertIsNotNone(date_cell)
        self.assertEqual(date_cell.alignment.horizontal, "center")
