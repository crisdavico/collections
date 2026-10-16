# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from datetime import date
from pathlib import Path

from lxml import etree

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import TransactionCase

from odoo.addons.collection.tools.collection_allocation import _RECEIPT_ITEM_SCHEMA

from .common_connector import (
    install_bound_test_connector,
    install_test_connector_type,
    mcp_env_with_listable_customers,
)
from .test_collection_acl import TestCollectionAcl
from .test_collection_mcp_allocation import INVOICE_OVERDUE, TOOL_NAME
from .test_collection_mcp_allocation_lookup import TOOL_NAME as GET_TOOL_NAME
from .test_collection_mcp_tool import _nest_seller_confirmed
from .test_collection_payment import (
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
    with_voucher_files,
)

IDENT = "20-11111111-1"
INHERIT_VIEW = (
    Path(__file__).resolve().parents[1] / "views" / "collection_sheet_report_views.xml"
)
PARENT_VIEW = (
    Path(__file__).resolve().parents[1] / "views" / "collection_allocation_views.xml"
)


class TestCollectionAllocationDocumentKind(TransactionCase):
    """RED: allocation line document_kind default, selection, view, MCP omit."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        install_test_connector_type(cls)
        cls.tool_model = cls.env["muk_mcp.tool"]
        cls.internal_user = cls._create_user(
            "collection_kind_mcp_internal", "collection.group_collection_user"
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

    def _mcp_payment(self, document_id, amount=100.0):
        return _nest_seller_confirmed(
            {
                "document_id": document_id,
                "document_type": "bank_transfer",
                "amount": amount,
            }
        )

    def _mcp_receipt(self, payments, document_kind="invoice", amount_applied=100.0):
        return {
            "document_kind": document_kind,
            "values": [
                {
                    "document_id": payment["document_id"],
                    "amount": payment["seller_confirmed"]["amount"],
                }
                for payment in payments
            ],
            "applications": [
                {
                    "external_document_id": INVOICE_OVERDUE["external_invoice_id"],
                    "number": INVOICE_OVERDUE.get("number"),
                    "balance_seen": INVOICE_OVERDUE["balance"],
                    "amount_applied": amount_applied,
                }
            ],
        }

    def _mcp_call(self, arguments, user=None):
        uid = user or self.internal_user
        arguments = dict(arguments)
        arguments["payments"] = [
            _nest_seller_confirmed(payment)
            for payment in arguments.get("payments") or []
        ]
        echo_args = dict(arguments)
        ident = arguments.get("customer_identification")
        if ident:
            echoed = []
            for payment in arguments.get("payments") or [{}]:
                item = dict(payment) if isinstance(payment, dict) else {}
                item.setdefault("customer_identification", ident)
                echoed.append(item)
            echo_args = {**arguments, "payments": echoed}
        env = mcp_env_with_listable_customers(self.env, echo_args, uid, uid)
        text, _info = self.tool_model._call(
            TOOL_NAME, with_voucher_files(arguments), env
        )
        return json.loads(text)

    def _mcp_get(self, user=None):
        env = self.env(user=user or self.internal_user)
        text, _info = self.tool_model._call(
            GET_TOOL_NAME,
            {
                "seller_id": self.seller.id,
                "customer_identification": IDENT,
            },
            env,
        )
        return json.loads(text)

    def _next_document_id(self, prefix="KIND-MCP"):
        self._doc_seq += 1
        return f"{prefix}-{self._testMethodName}-{self._doc_seq}"

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
        self.assertEqual(
            field.default(self.env["collection.allocation.line"]),
            "invoice",
        )
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

    def test_parent_arch_document_kind_before_invoice_number(self):
        """Parent form line list MUST show document_kind before invoice_number."""
        self.assertFalse(
            INHERIT_VIEW.is_file(),
            "views/collection_sheet_report_views.xml MUST be deleted",
        )
        parent_root = etree.parse(str(PARENT_VIEW)).getroot()
        invoice_fields = parent_root.xpath(
            "//field[@name='line_ids']/list/field[@name='invoice_number']"
        )
        self.assertEqual(len(invoice_fields), 1)
        line_list = invoice_fields[0].getparent()
        self.assertEqual(line_list.tag, "list")
        names = [
            node.get("name") for node in line_list.xpath("./field") if node.get("name")
        ]
        self.assertIn("invoice_number", names)
        invoice_index = names.index("invoice_number")
        self.assertGreater(invoice_index, 0)
        self.assertEqual(names[invoice_index - 1], "document_kind")
        self.assertFalse(
            parent_root.xpath(".//tree"),
            "Parent line list MUST use <list>, not <tree>",
        )

    def test_get_invoices_include_document_kind(self):
        """GET invoice rows MUST include stored document_kind."""
        voucher = self._create_voucher(self.partner, self.sheet, amount=50.0)
        self._create_allocation(
            self.sheet,
            self.partner,
            vouchers=voucher,
            lines=[
                self._line_vals(
                    amount_applied=50.0,
                    invoice_balance=50.0,
                    document_kind="quotation",
                )
            ],
        )
        env = self.env(user=self.internal_user)
        text, _info = self.tool_model._call(
            GET_TOOL_NAME,
            {
                "seller_id": self.seller.id,
                "customer_identification": IDENT,
            },
            env,
        )
        result = json.loads(text)
        invoices = result["invoices"]
        self.assertTrue(invoices)
        kinds = {row["document_kind"] for row in invoices}
        self.assertEqual(kinds, {"quotation"})
        for row in invoices:
            self.assertIn("document_kind", row)

    def test_mcp_create_invoice_receipt_persists_invoice_kind(self):
        """MCP create invoice receipt MUST persist invoice document_kind."""
        self.assertIn("document_kind", _RECEIPT_ITEM_SCHEMA["properties"])
        self.assertIn("document_kind", _RECEIPT_ITEM_SCHEMA.get("required", []))
        kind_schema = _RECEIPT_ITEM_SCHEMA["properties"]["document_kind"]
        self.assertEqual(kind_schema.get("enum"), ["invoice", "quotation"])
        by_name = {
            entry["name"]: entry for entry in self.tool_model.get_tools(registry="mcp")
        }
        schema = by_name[TOOL_NAME]["inputSchema"]
        receipt_props = schema["properties"]["receipts"]["items"]["properties"]
        self.assertIn("document_kind", receipt_props)
        self.assertIn(
            "document_kind",
            schema["properties"]["receipts"]["items"].get("required", []),
        )
        self.assertNotIn("invoices", schema["properties"])
        self.assertNotIn("document_kind", schema["properties"])

        document_id = self._next_document_id()
        payments = [self._mcp_payment(document_id)]
        arguments = {
            "seller_id": self.seller.id,
            "customer_identification": IDENT,
            "request_id": f"req-{self._testMethodName}",
            "payments": payments,
            "receipts": [self._mcp_receipt(payments)],
        }
        result = self._mcp_call(arguments)
        self.assertNotIn("document_kind", json.dumps(result))
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        self.assertTrue(allocation.exists())
        self.assertGreater(len(allocation.line_ids), 0)
        overdue = allocation.line_ids.filtered(
            lambda line: line.external_invoice_id
            == INVOICE_OVERDUE["external_invoice_id"]
        )
        self.assertEqual(overdue.document_kind, "invoice")
        found = self._mcp_get()
        self.assertTrue(found["invoices"])
        kinds = {
            row["external_invoice_id"]: row["document_kind"]
            for row in found["invoices"]
        }
        self.assertEqual(kinds[INVOICE_OVERDUE["external_invoice_id"]], "invoice")

    def test_mcp_create_may_send_quotation_kind(self):
        """MCP create receipts[] MAY send document_kind quotation and persist it."""
        document_id = self._next_document_id()
        payments = [self._mcp_payment(document_id)]
        arguments = {
            "seller_id": self.seller.id,
            "customer_identification": IDENT,
            "request_id": f"req-{self._testMethodName}",
            "payments": payments,
            "receipts": [self._mcp_receipt(payments, document_kind="quotation")],
        }
        result = self._mcp_call(arguments)
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        overdue = allocation.line_ids.filtered(
            lambda line: line.external_invoice_id
            == INVOICE_OVERDUE["external_invoice_id"]
        )
        self.assertEqual(len(overdue), 1)
        self.assertEqual(overdue.document_kind, "quotation")
        found = self._mcp_get()
        kinds = {
            row["external_invoice_id"]: row["document_kind"]
            for row in found["invoices"]
        }
        self.assertEqual(kinds[INVOICE_OVERDUE["external_invoice_id"]], "quotation")

    def test_mcp_amend_omits_kind_keeps_stored_quotation(self):
        """Amend that does not re-apply an invoice MUST keep stored quotation."""
        first_doc = self._next_document_id()
        first_payments = [self._mcp_payment(first_doc)]
        first = self._mcp_call(
            {
                "seller_id": self.seller.id,
                "customer_identification": IDENT,
                "request_id": f"req-{self._testMethodName}-1",
                "payments": first_payments,
                "receipts": [
                    self._mcp_receipt(first_payments, document_kind="quotation")
                ],
            }
        )
        allocation = self.env["collection.allocation"].browse(first["allocation"]["id"])
        extra = self._create_voucher(
            self.partner,
            self.sheet,
            amount=50.0,
            document_id=self._next_document_id("KIND-EXTRA"),
        )
        first_voucher = self.env["collection.voucher"].search(
            [("document_id", "=", first_doc)]
        )
        combined = first_voucher | extra
        payments = [
            {
                "document_id": voucher.document_id,
                "document_type": voucher.document_type,
                "amount": voucher.amount,
            }
            for voucher in combined
        ]
        second = self._mcp_call(
            {
                "seller_id": self.seller.id,
                "customer_identification": IDENT,
                "request_id": f"req-{self._testMethodName}-2",
                "payments": payments,
                "receipts": [
                    {
                        "document_kind": "invoice",
                        "values": [
                            {
                                "document_id": payment["document_id"],
                                "amount": payment["amount"],
                            }
                            for payment in payments
                        ],
                        "applications": [],
                    }
                ],
            }
        )
        self.assertEqual(second["allocation"]["id"], first["allocation"]["id"])
        allocation.invalidate_recordset()
        overdue = allocation.line_ids.filtered(
            lambda line: line.external_invoice_id
            == INVOICE_OVERDUE["external_invoice_id"]
        )
        self.assertEqual(len(overdue), 1)
        self.assertEqual(overdue.document_kind, "quotation")

    def test_mcp_amend_payload_kind_wins(self):
        """Amend receipt document_kind MUST replace the stored kind."""
        first_doc = self._next_document_id()
        first_payments = [self._mcp_payment(first_doc)]
        first = self._mcp_call(
            {
                "seller_id": self.seller.id,
                "customer_identification": IDENT,
                "request_id": f"req-{self._testMethodName}-1",
                "payments": first_payments,
                "receipts": [self._mcp_receipt(first_payments)],
            }
        )
        allocation = self.env["collection.allocation"].browse(first["allocation"]["id"])
        extra = self._create_voucher(
            self.partner,
            self.sheet,
            amount=50.0,
            document_id=self._next_document_id("KIND-EXTRA"),
        )
        first_voucher = self.env["collection.voucher"].search(
            [("document_id", "=", first_doc)]
        )
        combined = first_voucher | extra
        payments = [
            {
                "document_id": voucher.document_id,
                "document_type": voucher.document_type,
                "amount": voucher.amount,
            }
            for voucher in combined
        ]
        self._mcp_call(
            {
                "seller_id": self.seller.id,
                "customer_identification": IDENT,
                "request_id": f"req-{self._testMethodName}-2",
                "payments": payments,
                "receipts": [
                    {
                        "document_kind": "quotation",
                        "values": [
                            {
                                "document_id": payment["document_id"],
                                "amount": payment["amount"],
                            }
                            for payment in payments
                        ],
                        "applications": [
                            {
                                "external_document_id": INVOICE_OVERDUE[
                                    "external_invoice_id"
                                ],
                                "number": INVOICE_OVERDUE.get("number"),
                                "balance_seen": INVOICE_OVERDUE["balance"],
                                "amount_applied": 100.0,
                            }
                        ],
                    }
                ],
            }
        )
        allocation.invalidate_recordset()
        overdue = allocation.line_ids.filtered(
            lambda line: line.external_invoice_id
            == INVOICE_OVERDUE["external_invoice_id"]
        )
        self.assertEqual(len(overdue), 1)
        self.assertEqual(overdue.document_kind, "quotation")

    def test_mcp_create_invalid_kind_refused(self):
        """document_kind other than invoice/quotation MUST raise with no persist."""
        before = self.env["collection.allocation"].search_count([])
        document_id = self._next_document_id()
        payments = [self._mcp_payment(document_id)]
        arguments = {
            "seller_id": self.seller.id,
            "customer_identification": IDENT,
            "request_id": f"req-{self._testMethodName}",
            "payments": payments,
            "receipts": [
                {
                    **self._mcp_receipt(payments),
                    "document_kind": "cash",
                }
            ],
        }
        with self.assertRaises(UserError):
            self._mcp_call(arguments)
        self.assertEqual(self.env["collection.allocation"].search_count([]), before)
