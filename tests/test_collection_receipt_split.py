# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from odoo.addons.collection.tools.collection_allocation import (
    _CREATE_COLLECTION_ALLOCATION_SCHEMA,
)

from .common_connector import (
    install_bound_test_connector,
    install_test_connector_type,
    mcp_env_with_listable_customers,
)
from .test_collection_acl import TestCollectionAcl
from .test_collection_mcp_allocation import (
    IDENT,
    INVOICE_OPEN,
    INVOICE_OVERDUE,
    TOOL_NAME,
)
from .test_collection_payment import (
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
)


class TestCollectionReceiptSplit(TransactionCase):
    """MCP splits, FIFO compat grouping, over-split, and amend rebuild."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        install_test_connector_type(cls)
        cls.tool_model = cls.env["muk_mcp.tool"]
        cls.internal_user = cls._create_user(
            "collection_receipt_split_internal", "base.group_user"
        )
        cls.seller = create_internal_seller(cls.env, "collection_receipt_split_seller")

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

    def _create_voucher(self, amount=50.0, **extra):
        ensure_enabled_seller(self.env, self.seller)
        vals = {
            "partner_id": self.partner.id,
            "document_type": extra.pop("document_type", "bank_transfer"),
            "document_id": extra.pop("document_id", self._next_document_id()),
            "seller_id": self.seller.id,
            "sheet_id": self.sheet.id,
            "company_id": self.env.company.id,
            "amount": amount,
        }
        vals.update(extra)
        return self.env["collection.voucher"].create(vals)

    def _next_document_id(self, prefix="SPLIT-DOC"):
        self._doc_seq += 1
        return f"{prefix}-{self._testMethodName}-{self._doc_seq}"

    def _mcp_call(self, arguments, user=None):
        uid = user or self.internal_user
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
        text, _info = self.tool_model._call(TOOL_NAME, arguments, env)
        return json.loads(text)

    def _payload(self, payments, invoices, **extra):
        arguments = {
            "seller_id": extra.pop("seller_id", self.seller.id),
            "customer_identification": extra.pop("customer_identification", IDENT),
            "request_id": extra.pop("request_id", f"req-{self._testMethodName}"),
            "payments": payments,
            "invoices": invoices,
        }
        arguments.update(extra)
        return arguments

    def _payment(self, amount, document_id=None, **extra):
        payment = {
            "document_id": document_id or self._next_document_id(),
            "document_type": extra.pop("document_type", "bank_transfer"),
            "amount": amount,
        }
        payment.update(extra)
        return payment

    def _applied(self, invoice, amount_applied):
        row = dict(invoice)
        row["amount_applied"] = amount_applied
        return row

    def test_splits_optional_in_create_schema(self):
        """splits MUST be optional on create_collection_allocation."""
        properties = _CREATE_COLLECTION_ALLOCATION_SCHEMA["properties"]
        self.assertIn("splits", properties)
        self.assertNotIn("splits", _CREATE_COLLECTION_ALLOCATION_SCHEMA["required"])
        self.assertEqual(properties["splits"]["type"], "array")
        item = properties["splits"]["items"]
        self.assertEqual(
            set(item["required"]), {"document_id", "document_kind", "amount"}
        )
        self.assertEqual(
            item["properties"]["document_kind"].get("enum"), ["invoice", "quotation"]
        )

    def test_omitted_splits_compat_one_invoice_receipt(self):
        """Non-empty invoices and no splits MUST persist exactly one invoice receipt."""
        payment = self._payment(100.0)
        result = self._mcp_call(
            self._payload(
                [payment],
                [self._applied(INVOICE_OVERDUE, 70.0)],
            )
        )
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        receipts = allocation.receipt_ids
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts.document_kind, "invoice")
        self.assertEqual(len(receipts.value_ids), 1)
        self.assertEqual(receipts.value_ids.amount, 70.0)
        voucher = self.env["collection.voucher"].search(
            [("document_id", "=", payment["document_id"])]
        )
        self.assertEqual(receipts.value_ids.voucher_id, voucher)
        self.assertEqual(voucher.amount, 100.0)

    def test_empty_invoices_no_splits_zero_receipts(self):
        """Empty invoices[] and no splits MUST persist zero receipts."""
        payment = self._payment(80.0)
        result = self._mcp_call(
            self._payload([payment], [], residual_reason="on_account")
        )
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        self.assertFalse(allocation.receipt_ids)

    def test_fifo_second_voucher_partial_value(self):
        """FIFO MUST consume submit order: 60 then 40 of 50, leaving 10 unsplit."""
        first = self._payment(60.0)
        second = self._payment(50.0)
        result = self._mcp_call(
            self._payload(
                [first, second],
                [
                    self._applied(INVOICE_OVERDUE, 100.0),
                    self._applied(INVOICE_OPEN, 0.0),
                ],
            )
        )
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        receipt = allocation.receipt_ids
        self.assertEqual(len(receipt), 1)
        self.assertEqual(receipt.document_kind, "invoice")
        values = {
            value.voucher_id.document_id: value.amount for value in receipt.value_ids
        }
        self.assertEqual(values[first["document_id"]], 60.0)
        self.assertEqual(values[second["document_id"]], 40.0)
        self.assertEqual(len(receipt.value_ids), 2)

    def test_split_one_voucher_two_kinds(self):
        """Payment 100 MAY split 40 invoice + 60 quotation onto matching receipts."""
        payment = self._payment(100.0)
        result = self._mcp_call(
            self._payload(
                [payment],
                [self._applied(INVOICE_OVERDUE, 40.0)],
                splits=[
                    {
                        "document_id": payment["document_id"],
                        "document_kind": "invoice",
                        "amount": 40.0,
                    },
                    {
                        "document_id": payment["document_id"],
                        "document_kind": "quotation",
                        "amount": 60.0,
                    },
                ],
            )
        )
        allocation = self.env["collection.allocation"].browse(
            result["allocation"]["id"]
        )
        receipts = allocation.receipt_ids
        self.assertEqual(len(receipts), 2)
        invoice = receipts.filtered(lambda rec: rec.document_kind == "invoice")
        quotation = receipts.filtered(lambda rec: rec.document_kind == "quotation")
        self.assertEqual(len(invoice), 1)
        self.assertEqual(len(quotation), 1)
        self.assertEqual(invoice.value_ids.amount, 40.0)
        self.assertEqual(quotation.value_ids.amount, 60.0)
        voucher = self.env["collection.voucher"].search(
            [("document_id", "=", payment["document_id"])]
        )
        self.assertEqual(invoice.value_ids.voucher_id, voucher)
        self.assertEqual(quotation.value_ids.voucher_id, voucher)

    def test_over_split_refused_no_allocation(self):
        """Splits summing above the payment amount MUST raise with no persist."""
        before = self.env["collection.allocation"].search_count([])
        payment = self._payment(50.0)
        with self.assertRaises(UserError) as ctx:
            self._mcp_call(
                self._payload(
                    [payment],
                    [self._applied(INVOICE_OVERDUE, 50.0)],
                    splits=[
                        {
                            "document_id": payment["document_id"],
                            "document_kind": "invoice",
                            "amount": 30.0,
                        },
                        {
                            "document_id": payment["document_id"],
                            "document_kind": "quotation",
                            "amount": 21.0,
                        },
                    ],
                )
            )
        message = str(ctx.exception).lower()
        self.assertNotIn("unexpected keyword", message)
        self.assertIn("split", message)
        self.assertEqual(self.env["collection.allocation"].search_count([]), before)

    def test_duplicate_split_kind_refused(self):
        """Duplicate (document_id, document_kind) splits MUST raise."""
        before = self.env["collection.allocation"].search_count([])
        payment = self._payment(100.0)
        with self.assertRaises(UserError) as ctx:
            self._mcp_call(
                self._payload(
                    [payment],
                    [self._applied(INVOICE_OVERDUE, 80.0)],
                    splits=[
                        {
                            "document_id": payment["document_id"],
                            "document_kind": "invoice",
                            "amount": 40.0,
                        },
                        {
                            "document_id": payment["document_id"],
                            "document_kind": "invoice",
                            "amount": 40.0,
                        },
                    ],
                )
            )
        message = str(ctx.exception).lower()
        self.assertNotIn("unexpected keyword", message)
        self.assertIn("split", message)
        self.assertEqual(self.env["collection.allocation"].search_count([]), before)

    def test_amend_splits_rebuild_adds_quotation_keeps_one_invoice(self):
        """Amend from compat to splits MUST add a quotation receipt uniquely."""
        payment = self._payment(100.0)
        first = self._mcp_call(
            self._payload(
                [payment],
                [self._applied(INVOICE_OVERDUE, 40.0)],
                request_id=f"req-{self._testMethodName}-1",
            )
        )
        extra = self._create_voucher(amount=50.0)
        first_voucher = self.env["collection.voucher"].search(
            [("document_id", "=", payment["document_id"])]
        )
        first_allocation = self.env["collection.allocation"].browse(
            first["allocation"]["id"]
        )
        old_receipt_ids = first_allocation.receipt_ids.ids
        self.assertEqual(len(old_receipt_ids), 1)
        combined = first_voucher | extra
        second = self._mcp_call(
            self._payload(
                [
                    {
                        "document_id": voucher.document_id,
                        "document_type": voucher.document_type,
                        "amount": voucher.amount,
                    }
                    for voucher in combined
                ],
                [
                    self._applied(INVOICE_OVERDUE, 40.0),
                    {**self._applied(INVOICE_OPEN, 50.0), "document_kind": "quotation"},
                ],
                request_id=f"req-{self._testMethodName}-2",
                splits=[
                    {
                        "document_id": payment["document_id"],
                        "document_kind": "invoice",
                        "amount": 40.0,
                    },
                    {
                        "document_id": extra.document_id,
                        "document_kind": "quotation",
                        "amount": 50.0,
                    },
                ],
            )
        )
        self.assertEqual(second["allocation"]["id"], first["allocation"]["id"])
        allocation = self.env["collection.allocation"].browse(
            second["allocation"]["id"]
        )
        kinds = set(allocation.receipt_ids.mapped("document_kind"))
        self.assertEqual(kinds, {"invoice", "quotation"})
        self.assertEqual(len(allocation.receipt_ids), 2)
        invoice = allocation.receipt_ids.filtered(
            lambda rec: rec.document_kind == "invoice"
        )
        quotation = allocation.receipt_ids.filtered(
            lambda rec: rec.document_kind == "quotation"
        )
        self.assertEqual(len(invoice), 1)
        self.assertEqual(len(quotation), 1)
        self.assertEqual(invoice.value_ids.voucher_id, first_voucher)
        self.assertEqual(quotation.value_ids.voucher_id, extra)
        self.assertFalse(
            self.env["collection.receipt"].browse(old_receipt_ids).exists()
        )

    def test_amend_without_splits_keeps_compat_one_invoice_receipt(self):
        """Amend voucher superset without splits MUST keep one invoice receipt."""
        payment = self._payment(100.0)
        first = self._mcp_call(
            self._payload(
                [payment],
                [self._applied(INVOICE_OVERDUE, 70.0)],
                request_id=f"req-{self._testMethodName}-1",
            )
        )
        extra = self._create_voucher(amount=50.0)
        first_voucher = self.env["collection.voucher"].search(
            [("document_id", "=", payment["document_id"])]
        )
        first_allocation = self.env["collection.allocation"].browse(
            first["allocation"]["id"]
        )
        old_receipt_ids = first_allocation.receipt_ids.ids
        self.assertEqual(len(old_receipt_ids), 1)
        self.assertEqual(first_allocation.receipt_ids.document_kind, "invoice")
        combined = first_voucher | extra
        second = self._mcp_call(
            self._payload(
                [
                    {
                        "document_id": voucher.document_id,
                        "document_type": voucher.document_type,
                        "amount": voucher.amount,
                    }
                    for voucher in combined
                ],
                [self._applied(INVOICE_OVERDUE, 70.0)],
                request_id=f"req-{self._testMethodName}-2",
            )
        )
        self.assertEqual(second["allocation"]["id"], first["allocation"]["id"])
        allocation = self.env["collection.allocation"].browse(
            second["allocation"]["id"]
        )
        receipts = allocation.receipt_ids
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts.document_kind, "invoice")
        self.assertEqual(len(receipts.value_ids), 1)
        self.assertEqual(receipts.value_ids.voucher_id, first_voucher)
        self.assertEqual(receipts.value_ids.amount, 70.0)
        extra_values = self.env["collection.receipt.value"].search(
            [("voucher_id", "=", extra.id)]
        )
        self.assertFalse(extra_values)
        self.assertFalse(
            self.env["collection.receipt"].browse(old_receipt_ids).exists()
        )

    def test_splits_prevent_hash_replay(self):
        """Adding splits to otherwise identical content MUST not replay."""
        payment = self._payment(100.0)
        invoices = [self._applied(INVOICE_OVERDUE, 40.0)]
        first = self._mcp_call(
            self._payload(
                [payment],
                invoices,
                request_id=f"req-{self._testMethodName}-1",
            )
        )
        second = self._mcp_call(
            self._payload(
                [payment],
                invoices,
                request_id=f"req-{self._testMethodName}-2",
                splits=[
                    {
                        "document_id": payment["document_id"],
                        "document_kind": "invoice",
                        "amount": 40.0,
                    }
                ],
            )
        )
        self.assertEqual(second["allocation"]["id"], first["allocation"]["id"])
        self.assertEqual(second["allocation"]["revision"], 2)
        allocation = self.env["collection.allocation"].browse(
            second["allocation"]["id"]
        )
        self.assertEqual(len(allocation.revision_ids), 2)
