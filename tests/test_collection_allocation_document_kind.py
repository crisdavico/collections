# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from datetime import date
from pathlib import Path

from lxml import etree

from odoo.fields import Command
from odoo.tests import TransactionCase

from odoo.addons.collection.tools.collection_allocation import _INVOICE_ITEM_SCHEMA

from .common_connector import (
    install_bound_test_connector,
    install_test_connector_type,
    mcp_env_with_listable_customers,
)
from .test_collection_acl import TestCollectionAcl
from .test_collection_mcp_allocation import INVOICE_OVERDUE, TOOL_NAME
from .test_collection_payment import (
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
)

IDENT = "20-11111111-1"
INHERIT_VIEW = (
    Path(__file__).resolve().parents[1]
    / "views"
    / "collection_sheet_report_views.xml"
)
PARENT_VIEW = (
    Path(__file__).resolve().parents[1]
    / "views"
    / "collection_allocation_views.xml"
)


class TestCollectionAllocationDocumentKind(TransactionCase):
    """RED: allocation line document_kind default, selection, view, MCP omit."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        install_test_connector_type(cls)
        cls.tool_model = cls.env["muk_mcp.tool"]
        cls.internal_user = cls._create_user(
            "collection_kind_mcp_internal", "base.group_user"
        )
        cls.seller = create_internal_seller(cls.env, "collection_kind_mcp_seller")

    def setUp(self):
        super().setUp()
        install_test_connector_type(self)
        self.connector = install_bound_test_connector(self, self.seller)
        self.partner = dummy_customer_partner(self.env, customer=IDENT)
        self.env["collection.connector.customer.binding"].create(
            {
                "connector_id": self.connector.id,
                "external_customer_id": "cust-bound-active",
                "identification": IDENT,
                "partner_id": self.partner.id,
                "customer_code": "C-BOUND-1",
            }
        )
        self.sheet = self._create_sheet()
        self._doc_seq = 0

    @classmethod
    def _partner_has_autopost_bills_column(cls):
        return TestCollectionAcl._partner_has_autopost_bills_column.__func__(cls)

    @classmethod
    def _create_user(cls, login, group_xmlid):
        return TestCollectionAcl._create_user.__func__(cls, login, group_xmlid)

    def _create_sheet(self):
        ensure_enabled_seller(self.env, self.seller)
        existing = self.env["collection.sheet"].search(
            [
                ("seller_id", "=", self.seller.id),
                ("company_id", "=", self.env.company.id),
                ("state", "=", "open"),
            ],
            limit=1,
        )
        if existing:
            return existing
        return self.env["collection.sheet"].create(
            {"seller_id": self.seller.id, "company_id": self.env.company.id}
        )

    def _create_voucher(self, partner, sheet, amount=100.0, **extra):
        ensure_enabled_seller(self.env, sheet.seller_id, company=sheet.company_id)
        vals = {
            "partner_id": partner.id,
            "document_type": extra.pop("document_type", "bank_transfer"),
            "seller_id": sheet.seller_id.id,
            "sheet_id": sheet.id,
            "company_id": sheet.company_id.id,
            "amount": amount,
        }
        vals.update(extra)
        return self.env["collection.voucher"].create(vals)

    def _line_vals(self, amount_applied=100.0, invoice_balance=100.0, **extra):
        vals = {
            "external_invoice_id": extra.pop("external_invoice_id", "INV-KIND-1"),
            "invoice_number": extra.pop("invoice_number", "A-KIND-1"),
            "issue_date": extra.pop("issue_date", date(2026, 1, 1)),
            "due_date": extra.pop("due_date", date(2026, 1, 31)),
            "invoice_amount": extra.pop("invoice_amount", invoice_balance),
            "invoice_balance": invoice_balance,
            "invoice_state": extra.pop("invoice_state", "open"),
            "amount_applied": amount_applied,
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

    def test_default_invoice(self):
        """A new line with no document_kind MUST persist invoice."""
        partner = dummy_customer_partner(self.env, customer="KIND-DEFAULT")
        sheet = self._create_sheet()
        voucher = self._create_voucher(partner, sheet, amount=100.0)
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[self._line_vals()],
        )
        line = allocation.line_ids
        self.assertEqual(len(line), 1)
        self.assertEqual(line.document_kind, "invoice")
        self.assertNotIn("document_kind", self._line_vals())

    def test_required_selection(self):
        """document_kind MUST be required invoice/quotation only."""
        field = self.env["collection.allocation.line"]._fields["document_kind"]
        self.assertTrue(field.required)
        self.assertEqual(field.type, "selection")
        self.assertEqual(field.default(self.env["collection.allocation.line"]), "invoice")
        keys = [value for value, _label in field.selection]
        self.assertEqual(keys, ["invoice", "quotation"])

    def test_quotation_round_trip_on_draft(self):
        """Writing quotation on a draft line MUST persist quotation."""
        partner = dummy_customer_partner(self.env, customer="KIND-QUOTE")
        sheet = self._create_sheet()
        voucher = self._create_voucher(partner, sheet, amount=50.0)
        allocation = self._create_allocation(
            sheet,
            partner,
            vouchers=voucher,
            lines=[self._line_vals(amount_applied=50.0, invoice_balance=50.0)],
        )
        self.assertEqual(allocation.state, "draft")
        line = allocation.line_ids
        line.write({"document_kind": "quotation"})
        line.invalidate_recordset(["document_kind"])
        self.assertEqual(line.document_kind, "quotation")

    def test_inherited_view_before_invoice_number(self):
        """Inherited view MUST inject document_kind immediately before invoice_number."""
        self.assertTrue(INHERIT_VIEW.is_file(), INHERIT_VIEW)
        inherit_root = etree.parse(str(INHERIT_VIEW)).getroot()
        records = inherit_root.xpath(".//record[@model='ir.ui.view']")
        self.assertEqual(len(records), 1)
        inherit_id = records[0].xpath("./field[@name='inherit_id']/@ref")
        self.assertEqual(inherit_id, ["collection.view_collection_allocation_form"])
        xpath_nodes = records[0].xpath(".//xpath")
        self.assertEqual(len(xpath_nodes), 1)
        expr = xpath_nodes[0].get("expr")
        self.assertEqual(
            expr,
            "//field[@name='line_ids']/list/field[@name='invoice_number']",
        )
        self.assertEqual(xpath_nodes[0].get("position"), "before")
        kind_fields = xpath_nodes[0].xpath("./field[@name='document_kind']")
        self.assertEqual(len(kind_fields), 1)
        self.assertFalse(
            inherit_root.xpath(".//tree"),
            "Inherited line list MUST use <list>, not <tree>",
        )

        parent_root = etree.parse(str(PARENT_VIEW)).getroot()
        parent_lists = parent_root.xpath(
            "//field[@name='line_ids']/list/field[@name='invoice_number']"
        )
        self.assertEqual(len(parent_lists), 1)
        self.assertEqual(parent_lists[0].getparent().tag, "list")

        combined_names = [
            node.get("name")
            for node in parent_lists[0].getparent().xpath("./field")
            if node.get("name")
        ]
        invoice_index = combined_names.index("invoice_number")
        injected = etree.Element("field", name="document_kind")
        parent_lists[0].addprevious(injected)
        merged_names = [
            node.get("name")
            for node in parent_lists[0].getparent().xpath("./field")
            if node.get("name")
        ]
        self.assertEqual(merged_names[invoice_index], "document_kind")
        self.assertEqual(merged_names[invoice_index + 1], "invoice_number")

    def test_mcp_create_omits_kind_defaults_invoice(self):
        """MCP create MUST omit document_kind and persist the invoice default."""
        self.assertNotIn("document_kind", _INVOICE_ITEM_SCHEMA["properties"])
        self.assertNotIn("document_kind", _INVOICE_ITEM_SCHEMA.get("required", []))
        by_name = {
            entry["name"]: entry for entry in self.tool_model.get_tools(registry="mcp")
        }
        schema = by_name[TOOL_NAME]["inputSchema"]
        invoice_props = schema["properties"]["invoices"]["items"]["properties"]
        self.assertNotIn("document_kind", invoice_props)
        self.assertNotIn("document_kind", schema["properties"])

        self._doc_seq += 1
        document_id = f"KIND-MCP-{self._testMethodName}-{self._doc_seq}"
        arguments = {
            "seller_id": self.seller.id,
            "customer_identification": IDENT,
            "request_id": f"req-{self._testMethodName}",
            "payments": [
                {
                    "document_id": document_id,
                    "document_type": "bank_transfer",
                    "amount": 100.0,
                }
            ],
            "invoices": [
                {
                    **INVOICE_OVERDUE,
                    "amount_applied": 100.0,
                }
            ],
        }
        self.assertNotIn("document_kind", json.dumps(arguments))
        echo_args = dict(arguments)
        echoed = []
        for payment in arguments["payments"]:
            item = dict(payment)
            item.setdefault("customer_identification", IDENT)
            echoed.append(item)
        echo_args = {**arguments, "payments": echoed}
        env = mcp_env_with_listable_customers(
            self.env, echo_args, self.internal_user, self.internal_user
        )
        text, _info = self.tool_model._call(TOOL_NAME, arguments, env)
        result = json.loads(text)
        self.assertNotIn("document_kind", json.dumps(result))
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        self.assertTrue(allocation.exists())
        self.assertGreater(len(allocation.line_ids), 0)
        self.assertEqual(set(allocation.line_ids.mapped("document_kind")), {"invoice"})
