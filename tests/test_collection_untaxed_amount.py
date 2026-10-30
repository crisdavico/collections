# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from lxml import etree

from odoo.fields import Command
from odoo.tests import Form, TransactionCase

from .common_connector import (
    TEST_INVOICES,
    install_bound_test_connector,
    install_test_connector_type,
)
from .test_collection_payment import dummy_customer_partner, ensure_enabled_seller

ERP_CUSTOMER_IDENT = "20-11111111-1"


class TestCollectionUntaxedAmount(TransactionCase):
    """The connector's `amount_untaxed` reaches every allocation line."""

    def setUp(self):
        super().setUp()
        self.seller = ensure_enabled_seller(self.env)
        self.partner = dummy_customer_partner(self.env, customer=ERP_CUSTOMER_IDENT)
        install_test_connector_type(self)
        self.connector = install_bound_test_connector(self, self.seller)
        self.env["collection.connector.customer.binding"].create(
            {
                "connector_id": self.connector.id,
                "external_customer_id": "cust-bound-active",
                "identification": ERP_CUSTOMER_IDENT,
                "partner_id": self.partner.id,
                "customer_code": "C-BOUND-1",
            }
        )
        invoices = [dict(row) for row in TEST_INVOICES]
        invoices[0]["amount_untaxed"] = 82.64
        self.env = self.env(
            context={**self.env.context, "collection_test_invoices": invoices}
        )
        self.sheet = self.env["collection.sheet"].create({"seller_id": self.seller.id})

    def test_customer_debt_gives_amount_untaxed_or_the_amount(self):
        """A connector without an untaxed amount gives the amount itself."""
        debt = self.connector.with_env(self.env).get_customer_debt(
            self.seller.id, ERP_CUSTOMER_IDENT
        )
        by_id = {row["external_invoice_id"]: row for row in debt["invoices"]}
        self.assertEqual(by_id["inv-bound-overdue"]["amount_untaxed"], 82.64)
        self.assertEqual(by_id["inv-bound-open"]["amount_untaxed"], 50.0)

    def test_mcp_customer_debt_does_not_expose_amount_untaxed(self):
        """The agent's `customer_debt` answer keeps its invoice keys."""
        result = self.env["muk_mcp.mixin"].customer_debt(
            self.seller.id, ERP_CUSTOMER_IDENT
        )
        self.assertTrue(result["invoices"])
        for row in result["invoices"]:
            self.assertNotIn("amount_untaxed", row)

    def test_debt_lines_and_picked_debt_keep_amount_untaxed(self):
        """Lines from the customer's debt and from the picker snapshot it."""
        Allocation = self.env["collection.allocation"]
        vals = {
            row["external_invoice_id"]: row["invoice_amount_untaxed"]
            for row in Allocation._prepare_customer_debt_lines(self.sheet, self.partner)
        }
        self.assertEqual(vals, {"inv-bound-overdue": 82.64, "inv-bound-open": 50.0})

        allocation = Allocation.create(
            {"sheet_id": self.sheet.id, "partner_id": self.partner.id, "line_ids": []}
        )
        self.assertFalse(allocation.line_ids)
        action = allocation.action_open_debt_picker()
        picker = self.env["collection.allocation.debt.picker"].browse(action["res_id"])
        picker.selected_ids = picker.candidate_ids
        picker.action_add_debts()
        lines = {
            line.external_invoice_id: line.invoice_amount_untaxed
            for line in allocation.line_ids
        }
        self.assertEqual(lines, {"inv-bound-overdue": 82.64, "inv-bound-open": 50.0})

    def test_allocation_form_keeps_invoice_amounts(self):
        """Debt lines saved from the allocation form keep both invoice amounts.

        Like the web client: the onchange only returns the line fields the
        form view loads, and the save only sends those. Without both amounts
        the commission falls back to the applied total, VAT included.
        """
        Allocation = self.env["collection.allocation"]
        views = Allocation.get_views([(False, "form")])
        line_fields = views["models"]["collection.allocation.line"]["fields"]
        # The web client drops read-only columns from the save unless they
        # are force-saved.
        arch = etree.fromstring(views["views"]["form"]["arch"])
        sent = {
            node.get("name")
            for node in arch.xpath('//field[@name="line_ids"]/list/field')
            if node.get("readonly") not in ("1", "True")
            or node.get("force_save") in ("1", "True")
        }
        spec = {
            "sheet_id": {},
            "partner_id": {},
            "line_ids": {"fields": {name: {} for name in line_fields}},
        }
        values = {"sheet_id": self.sheet.id, "partner_id": self.partner.id}
        result = Allocation.onchange(values, ["partner_id"], spec)
        line_commands = [
            Command.create(
                {key: value for key, value in command[2].items() if key in sent}
            )
            for command in result["value"]["line_ids"]
            if command[0] == Command.CREATE
        ]
        self.assertTrue(line_commands, "the onchange must load the customer debt")
        Allocation.web_save(dict(values, line_ids=line_commands), {})
        allocation = Allocation.search(
            [("sheet_id", "=", self.sheet.id), ("partner_id", "=", self.partner.id)]
        )
        expected = Allocation._prepare_customer_debt_lines(self.sheet, self.partner)
        self.assertEqual(
            {
                line["external_invoice_id"]: line["invoice_amount_untaxed"]
                for line in expected
            },
            {"inv-bound-overdue": 82.64, "inv-bound-open": 50.0},
        )
        saved = {line.external_invoice_id: line for line in allocation.line_ids}
        self.assertEqual(set(saved), {line["external_invoice_id"] for line in expected})
        for vals in expected:
            line = saved[vals["external_invoice_id"]]
            for name, value in vals.items():
                field = line._fields[name]
                self.assertEqual(
                    field.convert_to_cache(line[name], line),
                    field.convert_to_cache(value, line),
                    f"{vals['external_invoice_id']} {name}",
                )

    def test_allocation_form_attaches_vouchers_while_sheet_open(self):
        """The Vouchers tab is editable on an open sheet, as the view says."""
        voucher = self.env["collection.voucher"].create(
            {
                "partner_id": self.partner.id,
                "seller_id": self.seller.id,
                "sheet_id": self.sheet.id,
                "document_type": "bank_transfer",
                "amount": 50.0,
            }
        )
        allocation = self.env["collection.allocation"].create(
            {"sheet_id": self.sheet.id, "partner_id": self.partner.id}
        )
        with Form(allocation) as form:
            form.voucher_ids.add(voucher)
        self.assertEqual(allocation.voucher_ids, voucher)
