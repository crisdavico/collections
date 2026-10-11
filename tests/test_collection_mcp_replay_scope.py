# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from .common_connector import (
    install_bound_test_connector,
    install_test_connector_type,
    mcp_env_with_listable_customers,
)
from .test_collection_acl import TestCollectionAcl
from .test_collection_payment import (
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
)

TOOL_NAME = "create_collection_allocation"
IDENT = "20-11111111-1"
REQUEST_CONFLICT = "Allocation request conflict could not be resolved."
DOCUMENT_CONFLICT = "Payment document_id conflict could not be resolved."
INVOICE_OVERDUE = {
    "external_document_id": "inv-bound-overdue",
    "number": "A-0001",
    "balance_seen": 100.0,
}
INVOICE_OPEN = {
    "external_document_id": "inv-bound-open",
    "number": "A-0002",
    "balance_seen": 50.0,
}


class TestCollectionMcpReplayScope(TransactionCase):
    """request_id and document_id replays answer only the same seller and content."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        install_test_connector_type(cls)
        cls.tool_model = cls.env["muk_mcp.tool"]
        cls.caller = cls._create_user(
            "collection_replay_scope_caller", "collection.group_collection_user"
        )

    @classmethod
    def _partner_has_autopost_bills_column(cls):
        return TestCollectionAcl._partner_has_autopost_bills_column.__func__(cls)

    @classmethod
    def _create_user(cls, login, group_xmlid):
        return TestCollectionAcl._create_user.__func__(cls, login, group_xmlid)

    def setUp(self):
        super().setUp()
        self.seller = create_internal_seller(self.env, "collection_replay_seller_a")
        self.other = create_internal_seller(self.env, "collection_replay_seller_b")
        self.connector = install_bound_test_connector(self, self.seller)
        ensure_enabled_seller(self.env, self.other)
        partner = dummy_customer_partner(self.env, customer=IDENT)
        self.env["collection.connector.customer.binding"].create(
            {
                "connector_id": self.connector.id,
                "external_customer_id": "cust-bound-active",
                "identification": IDENT,
                "partner_id": partner.id,
                "customer_code": "C-BOUND-1",
            }
        )

    def _arguments(self, seller, request_id, payments, applications=()):
        """One invoice receipt funded in full by ``payments`` ({doc: amount})."""
        return {
            "seller_id": seller.id,
            "customer_identification": IDENT,
            "request_id": request_id,
            "payments": [
                {
                    "document_id": document_id,
                    "seller_confirmed": {
                        "document_type": "bank_transfer",
                        "amount": amount,
                    },
                }
                for document_id, amount in payments.items()
            ],
            "receipts": [
                {
                    "document_kind": "invoice",
                    "values": [
                        {"document_id": document_id, "amount": amount}
                        for document_id, amount in payments.items()
                    ],
                    "applications": [dict(row) for row in applications],
                }
            ],
        }

    def _call(self, arguments):
        env = mcp_env_with_listable_customers(
            self.env, arguments, self.caller, self.caller
        )
        text, _info = self.tool_model._call(TOOL_NAME, dict(arguments), env)
        return json.loads(text)

    def _counts(self):
        return {
            model: self.env[model].search_count([])
            for model in (
                "collection.voucher",
                "collection.allocation",
                "collection.allocation.line",
                "collection.allocation.revision",
                "collection.receipt",
            )
        }

    def _assert_conflict(self, arguments, message, *leaked):
        """The call fails with ``message`` exactly, writes nothing, names nothing."""
        before = self._counts()
        with self.assertRaises(UserError) as ctx:
            self._call(arguments)
        self.assertEqual(str(ctx.exception), message)
        self.assertEqual(self._counts(), before)
        for record in leaked:
            self.assertNotIn(record.name, str(ctx.exception))

    def _first_allocation(self, request_id="req-scope-a", document_id="SCOPE-A-1"):
        applied = {**INVOICE_OVERDUE, "amount_applied": 100.0}
        first = self._call(
            self._arguments(self.seller, request_id, {document_id: 100.0}, [applied])
        )
        allocation = self.env["collection.allocation"].browse(first["allocation"]["id"])
        return first, allocation

    def test_request_id_of_another_seller_is_a_generic_conflict(self):
        """Seller B reusing seller A's request_id never gets A's allocation back."""
        _first, allocation = self._first_allocation()
        for label, document_id in (
            ("own documents", "SCOPE-B-1"),
            ("seller A documents", "SCOPE-A-1"),
        ):
            with self.subTest(case=label):
                self._assert_conflict(
                    self._arguments(self.other, "req-scope-a", {document_id: 100.0}),
                    REQUEST_CONFLICT,
                    allocation,
                )

    def test_request_id_replay_with_other_documents_is_a_conflict(self):
        """Same seller, same request_id, other document_ids: conflict, not KeyError."""
        _first, allocation = self._first_allocation()
        self._assert_conflict(
            self._arguments(self.seller, "req-scope-a", {"SCOPE-A-2": 100.0}),
            REQUEST_CONFLICT,
            allocation,
        )

    def test_request_id_replay_with_changed_content_is_a_conflict(self):
        """Same request_id and documents but other receipts is not a replay."""
        _first, allocation = self._first_allocation()
        changed = self._arguments(
            self.seller,
            "req-scope-a",
            {"SCOPE-A-1": 100.0},
            [{**INVOICE_OPEN, "amount_applied": 50.0}],
        )
        self._assert_conflict(changed, REQUEST_CONFLICT, allocation)

    def test_request_id_replay_with_another_customer_is_a_conflict(self):
        """Same request_id and content under another customer string conflicts."""
        _first, allocation = self._first_allocation()
        changed = self._arguments(
            self.seller,
            "req-scope-a",
            {"SCOPE-A-1": 100.0},
            [{**INVOICE_OVERDUE, "amount_applied": 100.0}],
        )
        changed["customer_identification"] = "20-33333333-3"
        self._assert_conflict(changed, REQUEST_CONFLICT, allocation)

    def test_request_id_replay_with_identical_content_replays(self):
        """An identical retry replays the first answer with zero writes."""
        first, _allocation = self._first_allocation()
        before = self._counts()
        again = self._call(
            self._arguments(
                self.seller,
                "req-scope-a",
                {"SCOPE-A-1": 100.0},
                [{**INVOICE_OVERDUE, "amount_applied": 100.0}],
            )
        )
        self.assertEqual(again, first)
        self.assertEqual(self._counts(), before)

    def test_document_ids_of_another_seller_are_a_generic_conflict(self):
        """Seller B naming seller A's documents gets the generic document conflict."""
        _first, allocation = self._first_allocation()
        voucher = allocation.voucher_ids
        self._assert_conflict(
            self._arguments(self.other, "req-scope-b", {"SCOPE-A-1": 100.0}),
            DOCUMENT_CONFLICT,
            allocation,
            voucher,
        )

    def test_document_id_reuse_with_changed_content_is_a_conflict(self):
        """Reusing a document_id with another amount or type is not the same payment."""
        _first, allocation = self._first_allocation()
        changed_amount = self._arguments(
            self.seller, "req-scope-amount", {"SCOPE-A-1": 90.0}
        )
        changed_type = self._arguments(
            self.seller, "req-scope-type", {"SCOPE-A-1": 100.0}
        )
        changed_type["payments"][0]["seller_confirmed"]["document_type"] = (
            "cash_deposit"
        )
        for label, arguments in (
            ("amount", changed_amount),
            ("document_type", changed_type),
        ):
            with self.subTest(case=label):
                self._assert_conflict(arguments, DOCUMENT_CONFLICT, allocation)

    def test_document_id_reuse_with_same_content_continues(self):
        """The same payment under a new request_id still amends the allocation."""
        first, allocation = self._first_allocation()
        amended = self._call(
            self._arguments(self.seller, "req-scope-amend", {"SCOPE-A-1": 100.0})
        )
        self.assertEqual(amended["allocation"]["id"], allocation.id)
        self.assertEqual(amended["vouchers"], first["vouchers"])
        self.assertEqual(amended["allocation"]["revision"], 2)
