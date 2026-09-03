# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import inspect
import json
from datetime import date
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from .common_connector import (
    install_bound_test_connector,
    mcp_env_with_listable_customers,
)
from .test_collection_payment import (
    dummy_customer_partner,
    ensure_enabled_seller,
)

TOOL_NAME = "create_collection_allocation"

# Minimal valid payloads (base64) for MCP attachment triangulation.
PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQ"
    "DJ/pLvAAAAAElFTkSuQmCC"
)
PDF_B64 = "JVBERi0xLjEKMSAwIG9iajw8Pj5lbmRvYmoKdHJhaWxlcjw8Pj4KJSVFT0YK"
TXT_B64 = "aGVsbG8gd29ybGQ="
INVALID_B64 = "!!!not-base64!!!"


class TestCollectionMcpAttachment(TransactionCase):
    """RED/GREEN: optional nested MCP attachment on create; exact-retry ignore."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tool_model = cls.env["muk_mcp.tool"]
        cls.internal_user = cls.env.ref("base.user_admin")
        ensure_enabled_seller(cls.env, cls.internal_user)

    def setUp(self):
        super().setUp()
        install_bound_test_connector(self, self.internal_user)

    def _call(self, arguments, user=None):
        arguments = dict(arguments)
        arguments.setdefault("seller_id", self.internal_user.id)
        payments = list(arguments.get("payments") or [])
        ident = arguments.get("customer_identification")
        if not ident:
            for payment in payments:
                if isinstance(payment, dict) and payment.get("customer_identification"):
                    ident = payment["customer_identification"]
                    break
        if ident:
            arguments["customer_identification"] = ident
        cleaned = []
        for payment in payments:
            if not isinstance(payment, dict):
                cleaned.append(payment)
                continue
            item = dict(payment)
            item.pop("customer_identification", None)
            cleaned.append(item)
        arguments["payments"] = cleaned
        arguments.setdefault("request_id", f"req-{self._testMethodName}")
        arguments.setdefault("invoices", [])
        arguments.setdefault("residual_reason", "on_account")
        echo_args = dict(arguments)
        if ident:
            echoed = []
            for payment in arguments.get("payments") or [{}]:
                item = dict(payment) if isinstance(payment, dict) else {}
                item.setdefault("customer_identification", ident)
                echoed.append(item)
            echo_args = {**arguments, "payments": echoed}
        env = mcp_env_with_listable_customers(
            self.env, echo_args, user, self.internal_user
        )
        text, _info = self.tool_model._call(TOOL_NAME, arguments, env)
        return json.loads(text)

    def _voucher_attachments(self, voucher):
        return self.env["ir.attachment"].search(
            [
                ("res_model", "=", "collection.voucher"),
                ("res_id", "=", voucher.id),
                ("res_field", "=", False),
            ]
        )

    def _field_attachments(self, voucher):
        """Binary-field leftovers (`res_field=attachment`) must not exist."""
        return self.env["ir.attachment"].search(
            [
                ("res_model", "=", "collection.voucher"),
                ("res_id", "=", voucher.id),
                ("res_field", "=", "attachment"),
            ]
        )

    def _chatter_attachment_count(self):
        return self.env["ir.attachment"].search_count(
            [
                ("res_model", "=", "collection.voucher"),
                ("res_field", "=", False),
            ]
        )

    def _nest(self, name, mimetype, datas):
        return {"name": name, "mimetype": mimetype, "datas": datas}

    def test_create_with_valid_png_nest_becomes_chatter_proof(self):
        """All-new create with valid nested PNG becomes chatter designated proof."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_atts = self._chatter_attachment_count()
        result = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-PNG",
                        "document_id": "MCP-DOC-ATT-PNG",
                        "document_type": "bank_transfer",
                        "amount": 12.0,
                        "attachment": self._nest("proof.png", "image/png", PNG_B64),
                    }
                ],
            },
        )
        self.assertEqual(len(result["vouchers"]), 1)
        voucher = self.env["collection.voucher"].browse(result["vouchers"][0]["id"])
        self.assertTrue(voucher.exists())
        self.assertEqual(result["vouchers"][0]["document_id"], "MCP-DOC-ATT-PNG")
        self.assertEqual(voucher.message_main_attachment_id.name, "proof.png")
        self.assertTrue(voucher.message_main_attachment_id)
        self.assertEqual(voucher.state, "validated_seller")
        self.assertEqual(result["vouchers"][0]["state"], "validated_seller")
        attachments = self._voucher_attachments(voucher)
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments.datas, PNG_B64.encode())
        self.assertFalse(attachments.res_field)
        self.assertFalse(
            self._field_attachments(voucher),
            "MCP nest must not persist as Binary res_field=attachment",
        )
        self.assertNotIn("attachment", voucher._fields)
        self.assertNotIn("attachment_filename", voucher._fields)
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers + 1,
        )
        self.assertEqual(self._chatter_attachment_count(), before_atts + 1)

    def test_create_with_valid_pdf_nest_persists(self):
        """Triangulation: valid nested PDF also persists via ir.attachment."""
        result = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-PDF",
                        "document_id": "MCP-DOC-ATT-PDF",
                        "document_type": "cash_deposit",
                        "amount": 8.0,
                        "attachment": self._nest(
                            "receipt.pdf", "application/pdf", PDF_B64
                        ),
                    }
                ],
            },
        )
        voucher = self.env["collection.voucher"].browse(result["vouchers"][0]["id"])
        self.assertEqual(voucher.message_main_attachment_id.name, "receipt.pdf")
        self.assertEqual(len(self._voucher_attachments(voucher)), 1)
        self.assertEqual(self._voucher_attachments(voucher).datas, PDF_B64.encode())

    def test_create_omitting_nest_still_creates(self):
        """Omit nest remains valid and creates a voucher without a file."""
        result = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-OMIT",
                        "document_id": "MCP-DOC-ATT-OMIT",
                        "document_type": "check",
                        "amount": 3.0,
                        "check_type": "common",
                    }
                ],
            },
        )
        voucher = self.env["collection.voucher"].browse(result["vouchers"][0]["id"])
        self.assertTrue(voucher.exists())
        self.assertEqual(voucher.state, "validated_seller")
        self.assertEqual(result["vouchers"][0]["state"], "validated_seller")
        self.assertFalse(voucher.message_main_attachment_id)
        self.assertFalse(self._voucher_attachments(voucher))
        self.assertFalse(self._field_attachments(voucher))

    def test_create_mime_mismatch_rejects_no_writes(self):
        """Declared MIME mismatch / non-allow-list must UserError with no writes."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_atts = self._chatter_attachment_count()
        with self.assertRaises(UserError) as err:
            self._call(
                {
                    "payments": [
                        {
                            "customer_identification": "MCP-ATT-MIME",
                            "document_id": "MCP-DOC-ATT-MIME",
                            "document_type": "bank_transfer",
                            "amount": 1.0,
                            # PNG bytes but declared as PDF → mismatch.
                            "attachment": self._nest(
                                "fake.pdf", "application/pdf", PNG_B64
                            ),
                        }
                    ],
                },
            )
        self.assertNotIn("tool not found", str(err.exception).lower())
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertEqual(
            self._chatter_attachment_count(),
            before_atts,
        )
        self.assertFalse(
            self.env["collection.voucher"].search(
                [("document_id", "=", "MCP-DOC-ATT-MIME")]
            ),
        )
        leftover = self.env["collection.voucher"].search(
            [("document_id", "=", "MCP-DOC-ATT-MIME")]
        )
        self.assertFalse(leftover)
        self.assertFalse(
            self.env["ir.attachment"].search(
                [
                    ("res_model", "=", "collection.voucher"),
                    ("res_field", "=", "attachment"),
                    ("name", "=", "fake.pdf"),
                ]
            ),
        )

    def test_create_bad_base64_rejects_no_writes(self):
        """Triangulation: bad base64 nest must UserError with no writes."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError) as err:
            self._call(
                {
                    "payments": [
                        {
                            "customer_identification": "MCP-ATT-B64",
                            "document_id": "MCP-DOC-ATT-B64",
                            "document_type": "bank_transfer",
                            "amount": 1.0,
                            "attachment": self._nest(
                                "bad.bin", "image/png", INVALID_B64
                            ),
                        }
                    ],
                },
            )
        self.assertNotIn("tool not found", str(err.exception).lower())
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertFalse(
            self.env["collection.voucher"].search(
                [("document_id", "=", "MCP-DOC-ATT-B64")]
            ),
        )

    def test_create_text_mime_rejects_no_writes(self):
        """Triangulation: text content with text/plain declared must reject."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError):
            self._call(
                {
                    "payments": [
                        {
                            "customer_identification": "MCP-ATT-TXT",
                            "document_id": "MCP-DOC-ATT-TXT",
                            "document_type": "bank_transfer",
                            "amount": 1.0,
                            "attachment": self._nest(
                                "notes.txt", "text/plain", TXT_B64
                            ),
                        }
                    ],
                },
            )
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertFalse(
            self.env["collection.voucher"].search(
                [("document_id", "=", "MCP-DOC-ATT-TXT")]
            ),
        )

    def test_create_batch_invalid_nest_writes_nothing(self):
        """Fail-closed: invalid nest MUST reject the whole batch before writes."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_atts = self._chatter_attachment_count()
        with self.assertRaises(UserError) as err:
            self._call(
                {
                    "payments": [
                        {
                            "customer_identification": "MCP-ATT-BATCH-FAIL",
                            "document_id": "MCP-DOC-ATT-BATCH-OK",
                            "document_type": "bank_transfer",
                            "amount": 10.0,
                            "attachment": self._nest("ok.png", "image/png", PNG_B64),
                        },
                        {
                            "customer_identification": "MCP-ATT-BATCH-FAIL",
                            "document_id": "MCP-DOC-ATT-BATCH-BAD",
                            "document_type": "cash_deposit",
                            "amount": 11.0,
                            "attachment": self._nest(
                                "fake.pdf", "application/pdf", PNG_B64
                            ),
                        },
                    ],
                },
            )
        self.assertNotIn("tool not found", str(err.exception).lower())
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertEqual(self._chatter_attachment_count(), before_atts)
        self.assertFalse(
            self.env["collection.voucher"].search(
                [
                    (
                        "document_id",
                        "in",
                        ["MCP-DOC-ATT-BATCH-OK", "MCP-DOC-ATT-BATCH-BAD"],
                    )
                ]
            ),
        )

    def test_create_incomplete_nest_rejects_no_writes(self):
        """Triangulation: nest missing datas MUST UserError with no writes."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_atts = self._chatter_attachment_count()
        with self.assertRaises(UserError) as err:
            self._call(
                {
                    "payments": [
                        {
                            "customer_identification": "MCP-ATT-INCOMPLETE",
                            "document_id": "MCP-DOC-ATT-INCOMPLETE",
                            "document_type": "bank_transfer",
                            "amount": 1.0,
                            "attachment": {
                                "name": "proof.png",
                                "mimetype": "image/png",
                            },
                        }
                    ],
                },
            )
        message = str(err.exception).lower()
        self.assertNotIn("tool not found", message)
        self.assertTrue(
            "datas" in message or "attachment" in message,
            f"Expected nest datas validation, got: {err.exception}",
        )
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertEqual(self._chatter_attachment_count(), before_atts)
        self.assertFalse(
            self.env["collection.voucher"].search(
                [("document_id", "=", "MCP-DOC-ATT-INCOMPLETE")]
            ),
        )

    def test_exact_retry_with_nest_does_not_replace_attachment(self):
        """Exact-retry with a different nest must leave stored attachment unchanged."""
        first = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-RETRY",
                        "document_id": "MCP-DOC-ATT-RETRY",
                        "document_type": "bank_transfer",
                        "amount": 5.0,
                        "attachment": self._nest("original.png", "image/png", PNG_B64),
                    }
                ],
            },
        )
        voucher = self.env["collection.voucher"].browse(first["vouchers"][0]["id"])
        original_att_ids = self._voucher_attachments(voucher).ids
        self.assertEqual(len(original_att_ids), 1)
        self.assertEqual(voucher.message_main_attachment_id.name, "original.png")
        self.assertEqual(voucher.message_main_attachment_id.datas, PNG_B64.encode())
        before_atts = self._chatter_attachment_count()

        second = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-RETRY-OTHER",
                        "document_id": "MCP-DOC-ATT-RETRY",
                        "document_type": "bank_transfer",
                        "amount": 999.0,
                        "attachment": self._nest(
                            "replacement.pdf", "application/pdf", PDF_B64
                        ),
                    }
                ],
            },
        )
        self.assertEqual(second["vouchers"][0]["id"], first["vouchers"][0]["id"])
        voucher.invalidate_recordset()
        self.assertEqual(voucher.message_main_attachment_id.name, "original.png")
        self.assertEqual(voucher.message_main_attachment_id.datas, PNG_B64.encode())
        self.assertEqual(self._voucher_attachments(voucher).ids, original_att_ids)
        self.assertEqual(
            self._chatter_attachment_count(),
            before_atts,
        )

    def test_exact_retry_with_nest_does_not_add_when_voucher_has_none(self):
        """Exact-retry nest MUST NOT add an attachment when the voucher has none."""
        first = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-RETRY-EMPTY",
                        "document_id": "MCP-DOC-ATT-RETRY-EMPTY",
                        "document_type": "cash_deposit",
                        "amount": 4.0,
                    }
                ],
            },
        )
        voucher = self.env["collection.voucher"].browse(first["vouchers"][0]["id"])
        self.assertFalse(voucher.message_main_attachment_id)
        before_atts = self._chatter_attachment_count()

        second = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-RETRY-EMPTY-OTHER",
                        "document_id": "MCP-DOC-ATT-RETRY-EMPTY",
                        "document_type": "cash_deposit",
                        "amount": 4.0,
                        "attachment": self._nest("late.png", "image/png", PNG_B64),
                    }
                ],
            },
        )
        self.assertEqual(second["vouchers"][0]["id"], first["vouchers"][0]["id"])
        voucher.invalidate_recordset()
        self.assertFalse(voucher.message_main_attachment_id)
        self.assertFalse(self._voucher_attachments(voucher))
        self.assertEqual(
            self._chatter_attachment_count(),
            before_atts,
        )

    def test_exact_retry_without_nest_leaves_existing_attachment(self):
        """Triangulation: exact-retry omitting nest must not clear existing file."""
        first = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-RETRY-OMIT",
                        "document_id": "MCP-DOC-ATT-RETRY-OMIT",
                        "document_type": "check",
                        "amount": 6.0,
                        "check_type": "common",
                        "attachment": self._nest(
                            "keep.pdf", "application/pdf", PDF_B64
                        ),
                    }
                ],
            },
        )
        voucher = self.env["collection.voucher"].browse(first["vouchers"][0]["id"])
        second = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-RETRY-OMIT-OTHER",
                        "document_id": "MCP-DOC-ATT-RETRY-OMIT",
                        "document_type": "check",
                        "amount": 6.0,
                        "check_type": "common",
                    }
                ],
            },
        )
        self.assertEqual(second["vouchers"][0]["id"], first["vouchers"][0]["id"])
        voucher.invalidate_recordset()
        self.assertEqual(voucher.message_main_attachment_id.name, "keep.pdf")
        self.assertEqual(voucher.message_main_attachment_id.datas, PDF_B64.encode())
        self.assertEqual(len(self._voucher_attachments(voucher)), 1)

    def _patch_voucher_search_miss_once(self, document_ids):
        """Simulate a race: first document_id lookup misses rows that already exist."""
        Voucher = self.env["collection.voucher"]
        empty = Voucher.browse()
        real_search = type(Voucher).search
        calls = {"n": 0}

        def search_proxy(model_self, domain=None, *args, **kwargs):
            domain = domain or []
            is_doc_lookup = any(
                isinstance(term, (list, tuple))
                and len(term) >= 3
                and term[0] == "document_id"
                and term[1] == "in"
                and set(term[2]) == set(document_ids)
                for term in domain
            )
            if model_self._name == "collection.voucher" and is_doc_lookup:
                calls["n"] += 1
                if calls["n"] == 1:
                    return empty
            return real_search(model_self, domain, *args, **kwargs)

        return patch("odoo.models.Model.search", search_proxy), calls

    def test_exact_retry_ignores_invalid_nest(self):
        """Exact-retry MUST NOT compare nests: invalid MIME still replays."""
        first = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-RETRY-IGN",
                        "document_id": "MCP-DOC-ATT-RETRY-IGN",
                        "document_type": "bank_transfer",
                        "amount": 7.0,
                        "attachment": self._nest("keep.png", "image/png", PNG_B64),
                    }
                ],
            },
        )
        voucher = self.env["collection.voucher"].browse(first["vouchers"][0]["id"])
        original_att_ids = self._voucher_attachments(voucher).ids
        before_atts = self._chatter_attachment_count()

        second = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-RETRY-IGN-OTHER",
                        "document_id": "MCP-DOC-ATT-RETRY-IGN",
                        "document_type": "bank_transfer",
                        "amount": 7.0,
                        "attachment": self._nest("bad.bin", "image/png", INVALID_B64),
                    }
                ],
            },
        )
        self.assertEqual(second["vouchers"], first["vouchers"])
        voucher.invalidate_recordset()
        self.assertEqual(voucher.message_main_attachment_id.name, "keep.png")
        self.assertEqual(self._voucher_attachments(voucher).ids, original_att_ids)
        self.assertEqual(self._chatter_attachment_count(), before_atts)
        self.assertFalse(self._field_attachments(voucher))

    def test_exact_retry_returns_all_with_mixed_nests(self):
        """Exact-retry of a two-payment set MUST return all and ignore mixed nests."""
        first = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-RETRY-ALL",
                        "document_id": "MCP-DOC-ATT-RETRY-ALL-A",
                        "document_type": "bank_transfer",
                        "amount": 1.0,
                        "attachment": self._nest("a.png", "image/png", PNG_B64),
                    },
                    {
                        "customer_identification": "MCP-ATT-RETRY-ALL",
                        "document_id": "MCP-DOC-ATT-RETRY-ALL-B",
                        "document_type": "cash_deposit",
                        "amount": 2.0,
                    },
                ],
            },
        )
        self.assertEqual(len(first["vouchers"]), 2)
        voucher_a = self.env["collection.voucher"].browse(first["vouchers"][0]["id"])
        voucher_b = self.env["collection.voucher"].browse(first["vouchers"][1]["id"])
        a_att_ids = self._voucher_attachments(voucher_a).ids
        before_atts = self._chatter_attachment_count()

        second = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-RETRY-ALL-OTHER",
                        "document_id": "MCP-DOC-ATT-RETRY-ALL-A",
                        "document_type": "bank_transfer",
                        "amount": 99.0,
                    },
                    {
                        "customer_identification": "MCP-ATT-RETRY-ALL-OTHER",
                        "document_id": "MCP-DOC-ATT-RETRY-ALL-B",
                        "document_type": "cash_deposit",
                        "amount": 99.0,
                        "attachment": self._nest(
                            "late.pdf", "application/pdf", PDF_B64
                        ),
                    },
                ],
            },
        )
        self.assertEqual(second["vouchers"], first["vouchers"])
        voucher_a.invalidate_recordset()
        voucher_b.invalidate_recordset()
        self.assertEqual(voucher_a.message_main_attachment_id.name, "a.png")
        self.assertEqual(self._voucher_attachments(voucher_a).ids, a_att_ids)
        self.assertFalse(voucher_b.message_main_attachment_id)
        self.assertFalse(self._voucher_attachments(voucher_b))
        self.assertEqual(self._chatter_attachment_count(), before_atts)

    def test_unique_violation_replay_with_nest_does_not_post(self):
        """UniqueViolation exact-set replay MUST NOT message_post a nested proof."""
        first = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-UV",
                        "document_id": "MCP-DOC-ATT-UV",
                        "document_type": "bank_transfer",
                        "amount": 13.0,
                    }
                ],
            },
        )
        voucher = self.env["collection.voucher"].browse(first["vouchers"][0]["id"])
        self.assertFalse(voucher.message_main_attachment_id)
        before_atts = self._chatter_attachment_count()
        doc_ids = ["MCP-DOC-ATT-UV"]
        search_patch, calls = self._patch_voucher_search_miss_once(doc_ids)

        with mute_logger("odoo.sql_db"), search_patch:
            second = self._call(
                {
                    "request_id": f"req-{self._testMethodName}-race",
                    "payments": [
                        {
                            "customer_identification": "MCP-ATT-UV",
                            "document_id": "MCP-DOC-ATT-UV",
                            "document_type": "bank_transfer",
                            "amount": 13.0,
                            "attachment": self._nest("race.png", "image/png", PNG_B64),
                        }
                    ],
                },
            )

        self.assertGreaterEqual(
            calls["n"],
            2,
            "Expected initial miss + post-UniqueViolation re-lookup",
        )
        self.assertEqual(second["vouchers"], first["vouchers"])
        voucher.invalidate_recordset()
        self.assertFalse(voucher.message_main_attachment_id)
        self.assertFalse(self._voucher_attachments(voucher))
        self.assertEqual(self._chatter_attachment_count(), before_atts)

    def test_unique_violation_replay_does_not_replace_existing_proof(self):
        """Triangulation: UniqueViolation replay MUST NOT replace stored proof."""
        first = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-ATT-UV-KEEP",
                        "document_id": "MCP-DOC-ATT-UV-KEEP",
                        "document_type": "cash_deposit",
                        "amount": 4.0,
                        "attachment": self._nest("orig.png", "image/png", PNG_B64),
                    }
                ],
            },
        )
        voucher = self.env["collection.voucher"].browse(first["vouchers"][0]["id"])
        original_att_ids = self._voucher_attachments(voucher).ids
        before_atts = self._chatter_attachment_count()
        doc_ids = ["MCP-DOC-ATT-UV-KEEP"]
        search_patch, calls = self._patch_voucher_search_miss_once(doc_ids)

        with mute_logger("odoo.sql_db"), search_patch:
            second = self._call(
                {
                    "request_id": f"req-{self._testMethodName}-race",
                    "payments": [
                        {
                            "customer_identification": "MCP-ATT-UV-KEEP",
                            "document_id": "MCP-DOC-ATT-UV-KEEP",
                            "document_type": "cash_deposit",
                            "amount": 4.0,
                            "attachment": self._nest(
                                "race.pdf", "application/pdf", PDF_B64
                            ),
                        }
                    ],
                },
            )

        self.assertGreaterEqual(calls["n"], 2)
        self.assertEqual(second["vouchers"], first["vouchers"])
        voucher.invalidate_recordset()
        self.assertEqual(voucher.message_main_attachment_id.name, "orig.png")
        self.assertEqual(voucher.message_main_attachment_id.datas, PNG_B64.encode())
        self.assertEqual(self._voucher_attachments(voucher).ids, original_att_ids)
        self.assertEqual(self._chatter_attachment_count(), before_atts)
        self.assertFalse(self._field_attachments(voucher))


class TestCollectionMcpProvenance(TransactionCase):
    """RED/GREEN: nested raw_ocr + seller_confirmed on all-new MCP create."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tool_model = cls.env["muk_mcp.tool"]
        cls.internal_user = cls.env.ref("base.user_admin")
        ensure_enabled_seller(cls.env, cls.internal_user)

    def setUp(self):
        super().setUp()
        install_bound_test_connector(self, self.internal_user)

    def _call(self, arguments, user=None):
        arguments = dict(arguments)
        arguments.setdefault("seller_id", self.internal_user.id)
        payments = list(arguments.get("payments") or [])
        ident = arguments.get("customer_identification")
        if not ident:
            for payment in payments:
                if isinstance(payment, dict) and payment.get("customer_identification"):
                    ident = payment["customer_identification"]
                    break
        if ident:
            arguments["customer_identification"] = ident
        cleaned = []
        for payment in payments:
            if not isinstance(payment, dict):
                cleaned.append(payment)
                continue
            item = dict(payment)
            item.pop("customer_identification", None)
            cleaned.append(item)
        arguments["payments"] = cleaned
        arguments.setdefault("request_id", f"req-{self._testMethodName}")
        arguments.setdefault("invoices", [])
        arguments.setdefault("residual_reason", "on_account")
        echo_args = dict(arguments)
        if ident:
            echoed = []
            for payment in arguments.get("payments") or [{}]:
                item = dict(payment) if isinstance(payment, dict) else {}
                item.setdefault("customer_identification", ident)
                echoed.append(item)
            echo_args = {**arguments, "payments": echoed}
        env = mcp_env_with_listable_customers(
            self.env, echo_args, user, self.internal_user
        )
        text, _info = self.tool_model._call(TOOL_NAME, arguments, env)
        return json.loads(text)

    def _voucher(self, result):
        return self.env["collection.voucher"].browse(result["vouchers"][0]["id"])

    def _snapshot_count(self, voucher):
        Snapshot = self.env["collection.voucher.review.snapshot"]
        return Snapshot.search_count([("voucher_id", "=", voucher.id)])

    def _assert_empty_provenance(self, voucher):
        for name in voucher._REVIEW_EDITABLE_FIELDS:
            ocr_value = voucher[f"ocr_{name}"]
            seller_value = voucher[f"seller_{name}"]
            if name == "amount":
                self.assertEqual(ocr_value, 0.0, f"ocr_{name}")
                self.assertEqual(seller_value, 0.0, f"seller_{name}")
            else:
                self.assertFalse(ocr_value, f"ocr_{name}")
                self.assertFalse(seller_value, f"seller_{name}")

    def _assert_layer_matches(self, voucher, prefix, expected):
        for name in voucher._REVIEW_EDITABLE_FIELDS:
            field_name = f"{prefix}_{name}" if prefix else name
            actual = voucher[field_name]
            if name not in expected:
                if name == "amount":
                    self.assertEqual(actual, 0.0, field_name)
                else:
                    self.assertFalse(actual, field_name)
                continue
            if name == "amount":
                self.assertAlmostEqual(actual, expected[name], places=2, msg=field_name)
            else:
                self.assertEqual(actual, expected[name], field_name)

    def _assert_no_base64_in_provenance(self, voucher):
        for name in voucher._REVIEW_EDITABLE_FIELDS:
            for prefix in ("ocr", "seller"):
                rendered = str(voucher[f"{prefix}_{name}"])
                self.assertNotIn(PNG_B64, rendered)
                self.assertNotIn(PDF_B64, rendered)
                self.assertNotIn("base64", rendered.lower())

    def _patch_voucher_search_miss_once(self, document_ids):
        Voucher = self.env["collection.voucher"]
        empty = Voucher.browse()
        real_search = type(Voucher).search
        calls = {"n": 0}

        def search_proxy(model_self, domain=None, *args, **kwargs):
            domain = domain or []
            is_doc_lookup = any(
                isinstance(term, (list, tuple))
                and len(term) >= 3
                and term[0] == "document_id"
                and term[1] == "in"
                and set(term[2]) == set(document_ids)
                for term in domain
            )
            if model_self._name == "collection.voucher" and is_doc_lookup:
                calls["n"] += 1
                if calls["n"] == 1:
                    return empty
            return real_search(model_self, domain, *args, **kwargs)

        return patch("odoo.models.Model.search", search_proxy), calls

    def test_schema_exposes_nests_without_identity_or_base64(self):
        """MCP payment schema nests typed provenance; identity stays outside."""
        by_name = {
            entry["name"]: entry for entry in self.tool_model.get_tools(registry="mcp")
        }
        payment_schema = by_name[TOOL_NAME]["inputSchema"]["properties"]["payments"][
            "items"
        ]
        properties = payment_schema["properties"]
        schema = by_name[TOOL_NAME]["inputSchema"]
        self.assertIn("customer_identification", schema["required"])
        self.assertIn("raw_ocr", properties)
        self.assertIn("seller_confirmed", properties)
        self.assertIn("document_id", properties)
        self.assertNotIn("customer_identification", properties)
        self.assertNotIn(
            "customer_identification",
            payment_schema.get("required", []),
        )
        self.assertIn("attachment", properties)
        for nest_key in ("raw_ocr", "seller_confirmed"):
            nest_props = properties[nest_key].get("properties", {})
            self.assertIn("document_type", nest_props)
            self.assertIn("document_type", properties[nest_key].get("required", []))
            for forbidden in (
                "datas",
                "attachment",
                "document_id",
                "customer_identification",
                "seller_id",
            ):
                self.assertNotIn(forbidden, nest_props)

    def test_omitted_nests_leave_null_provenance(self):
        """Both nests omitted MUST leave empty provenance on all-new create."""
        result = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-PROV-OMIT",
                        "document_id": "MCP-DOC-PROV-OMIT",
                        "document_type": "bank_transfer",
                        "amount": 40.0,
                        "from_account": "FROM-OMIT",
                    }
                ],
            }
        )
        voucher = self._voucher(result)
        self.assertAlmostEqual(voucher.amount, 40.0, places=2)
        self.assertEqual(voucher.from_account, "FROM-OMIT")
        self._assert_empty_provenance(voucher)
        self.assertEqual(self._snapshot_count(voucher), 0)

    def test_orm_create_without_nests_leaves_null_provenance(self):
        """Triangulation: UI/ORM create MUST remain allowed with empty provenance."""
        voucher = self.env["collection.voucher"].create(
            {
                "partner_id": dummy_customer_partner(
                    self.env, customer="ORM-PROV-OMIT"
                ).id,
                "document_type": "check",
                "amount": 12.0,
                "check_number": "CHK-ORM",
                "seller_id": ensure_enabled_seller(self.env, self.internal_user).id,
            }
        )
        self.assertTrue(voucher.id)
        self.assertEqual(voucher.document_type, "check")
        self.assertEqual(voucher.check_number, "CHK-ORM")
        self._assert_empty_provenance(voucher)
        self.assertEqual(self._snapshot_count(voucher), 0)

    def test_omitted_nests_with_attachment_keep_base64_out_of_provenance(self):
        """Attachment + omitted nests MUST NOT copy base64 into provenance fields."""
        result = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-PROV-ATT-OMIT",
                        "document_id": "MCP-DOC-PROV-ATT-OMIT",
                        "document_type": "bank_transfer",
                        "amount": 5.0,
                        "attachment": {
                            "name": "proof.png",
                            "mimetype": "image/png",
                            "datas": PNG_B64,
                        },
                    }
                ],
            }
        )
        voucher = self._voucher(result)
        self.assertTrue(voucher.message_main_attachment_id)
        self._assert_empty_provenance(voucher)
        self._assert_no_base64_in_provenance(voucher)

    def test_unchanged_seller_stamps_all_three_layers_equal(self):
        """When both nests equal top-level, raw, seller, and current MUST match."""
        fields_vals = {
            "document_type": "bank_transfer",
            "amount": 100.0,
            "from_account": "FROM-1",
            "to_account": "TO-1",
        }
        result = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-PROV-EQUAL",
                        "document_id": "MCP-DOC-PROV-EQUAL",
                        **fields_vals,
                        "raw_ocr": dict(fields_vals),
                        "seller_confirmed": dict(fields_vals),
                    }
                ],
            }
        )
        voucher = self._voucher(result)
        self._assert_layer_matches(voucher, "", fields_vals)
        self._assert_layer_matches(voucher, "ocr", fields_vals)
        self._assert_layer_matches(voucher, "seller", fields_vals)

    def test_seller_correction_keeps_raw_and_aligns_current(self):
        """Raw MAY differ; seller-confirmed MUST equal top-level and current."""
        raw_vals = {
            "document_type": "bank_transfer",
            "amount": 80.0,
            "from_account": "OCR-FROM",
            "to_account": "OCR-TO",
        }
        seller_vals = {
            "document_type": "bank_transfer",
            "amount": 125.5,
            "from_account": "SELLER-FROM",
            "to_account": "SELLER-TO",
        }
        result = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-PROV-CORR",
                        "document_id": "MCP-DOC-PROV-CORR",
                        **seller_vals,
                        "raw_ocr": dict(raw_vals),
                        "seller_confirmed": dict(seller_vals),
                    }
                ],
            }
        )
        voucher = self._voucher(result)
        self._assert_layer_matches(voucher, "", seller_vals)
        self._assert_layer_matches(voucher, "seller", seller_vals)
        self._assert_layer_matches(voucher, "ocr", raw_vals)

    def test_cash_deposit_stores_voucher_number_and_date_in_all_layers(self):
        """Cash-deposit voucher_number/voucher_date MUST persist in all three layers."""
        fields_vals = {
            "document_type": "cash_deposit",
            "amount": 30.0,
            "voucher_number": "CASH-99",
            "voucher_date": date(2026, 4, 1),
        }
        nest = {
            "document_type": "cash_deposit",
            "amount": 30.0,
            "voucher_number": "CASH-99",
            "voucher_date": "2026-04-01",
        }
        result = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-PROV-CASH",
                        "document_id": "MCP-DOC-PROV-CASH",
                        "document_type": "cash_deposit",
                        "amount": 30.0,
                        "voucher_number": "CASH-99",
                        "voucher_date": "2026-04-01",
                        "raw_ocr": dict(nest),
                        "seller_confirmed": dict(nest),
                    }
                ],
            }
        )
        voucher = self._voucher(result)
        self._assert_layer_matches(voucher, "", fields_vals)
        self._assert_layer_matches(voucher, "ocr", fields_vals)
        self._assert_layer_matches(voucher, "seller", fields_vals)
        self.assertNotIn("ocr_document_id", voucher._fields)
        self.assertNotIn("seller_document_id", voucher._fields)
        self.assertNotIn("ocr_attachment", voucher._fields)
        self.assertNotIn("seller_seller_id", voucher._fields)

    def test_one_sided_nests_reject_with_no_writes(self):
        """Only one of raw_ocr/seller_confirmed MUST fail the batch before write."""
        before = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError) as err:
            self._call(
                {
                    "payments": [
                        {
                            "customer_identification": "MCP-PROV-ONE",
                            "document_id": "MCP-DOC-PROV-ONE",
                            "document_type": "bank_transfer",
                            "amount": 10.0,
                            "raw_ocr": {
                                "document_type": "bank_transfer",
                                "amount": 10.0,
                            },
                        }
                    ],
                }
            )
        self.assertNotIn("tool not found", str(err.exception).lower())
        self.assertEqual(self.env["collection.voucher"].search_count([]), before)
        self.assertFalse(
            self.env["collection.voucher"].search(
                [("document_id", "=", "MCP-DOC-PROV-ONE")]
            )
        )

    def test_malformed_and_mismatch_nests_reject_with_no_writes(self):
        """Triangulation: malformed, missing nest type, or mismatch write nothing."""
        before = self.env["collection.voucher"].search_count([])
        cases = [
            (
                "MCP-DOC-PROV-BAD-OBJ",
                {
                    "document_id": "MCP-DOC-PROV-BAD-OBJ",
                    "document_type": "bank_transfer",
                    "amount": 1.0,
                    "raw_ocr": "not-an-object",
                    "seller_confirmed": {
                        "document_type": "bank_transfer",
                        "amount": 1.0,
                    },
                },
            ),
            (
                "MCP-DOC-PROV-BAD-TYPE",
                {
                    "document_id": "MCP-DOC-PROV-BAD-TYPE",
                    "document_type": "bank_transfer",
                    "amount": 2.0,
                    "raw_ocr": {"amount": 2.0},
                    "seller_confirmed": {
                        "document_type": "bank_transfer",
                        "amount": 2.0,
                    },
                },
            ),
            (
                "MCP-DOC-PROV-MISMATCH",
                {
                    "document_id": "MCP-DOC-PROV-MISMATCH",
                    "document_type": "bank_transfer",
                    "amount": 3.0,
                    "raw_ocr": {
                        "document_type": "bank_transfer",
                        "amount": 3.0,
                    },
                    "seller_confirmed": {
                        "document_type": "bank_transfer",
                        "amount": 99.0,
                    },
                },
            ),
            (
                "MCP-DOC-PROV-NEST-ID",
                {
                    "document_id": "MCP-DOC-PROV-NEST-ID",
                    "document_type": "bank_transfer",
                    "amount": 4.0,
                    "raw_ocr": {
                        "document_type": "bank_transfer",
                        "amount": 4.0,
                        "document_id": "LEAKED",
                    },
                    "seller_confirmed": {
                        "document_type": "bank_transfer",
                        "amount": 4.0,
                    },
                },
            ),
        ]
        for document_id, payment in cases:
            with self.subTest(document_id=document_id):
                with self.assertRaises(UserError):
                    self._call(
                        {
                            "payments": [
                                dict(
                                    payment,
                                    customer_identification="MCP-PROV-BAD",
                                )
                            ],
                        }
                    )
                self.assertFalse(
                    self.env["collection.voucher"].search(
                        [("document_id", "=", document_id)]
                    )
                )
        self.assertEqual(self.env["collection.voucher"].search_count([]), before)

    def test_optional_omit_null_empty_nests_are_equal(self):
        """Reuse optional-field equality: omit/null/'' MUST match and stamp."""
        nest = {
            "document_type": "bank_transfer",
            "amount": 15.0,
            "from_account": None,
            "to_account": "",
        }
        result = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-PROV-OPT",
                        "document_id": "MCP-DOC-PROV-OPT",
                        "document_type": "bank_transfer",
                        "amount": 15.0,
                        "raw_ocr": dict(nest),
                        "seller_confirmed": dict(nest),
                    }
                ],
            }
        )
        voucher = self._voucher(result)
        expected = {"document_type": "bank_transfer", "amount": 15.0}
        self._assert_layer_matches(voucher, "", expected)
        self._assert_layer_matches(voucher, "ocr", expected)
        self._assert_layer_matches(voucher, "seller", expected)

    def test_batch_one_sided_second_payment_writes_nothing(self):
        """Fail-closed: a later bad nest MUST reject the whole batch."""
        before = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError):
            self._call(
                {
                    "payments": [
                        {
                            "customer_identification": "MCP-PROV-BATCH",
                            "document_id": "MCP-DOC-PROV-BATCH-OK",
                            "document_type": "bank_transfer",
                            "amount": 8.0,
                            "raw_ocr": {
                                "document_type": "bank_transfer",
                                "amount": 8.0,
                            },
                            "seller_confirmed": {
                                "document_type": "bank_transfer",
                                "amount": 8.0,
                            },
                        },
                        {
                            "customer_identification": "MCP-PROV-BATCH",
                            "document_id": "MCP-DOC-PROV-BATCH-BAD",
                            "document_type": "cash_deposit",
                            "amount": 9.0,
                            "seller_confirmed": {
                                "document_type": "cash_deposit",
                                "amount": 9.0,
                            },
                        },
                    ],
                }
            )
        self.assertEqual(self.env["collection.voucher"].search_count([]), before)
        self.assertFalse(
            self.env["collection.voucher"].search(
                [
                    (
                        "document_id",
                        "in",
                        ["MCP-DOC-PROV-BATCH-OK", "MCP-DOC-PROV-BATCH-BAD"],
                    )
                ]
            )
        )

    def test_provenance_parsed_on_create_path_not_in_payment_vals(self):
        """Parse nests after existing-document check, never in payment vals helper."""
        mixin_cls = type(self.env["muk_mcp.mixin"])
        parse_vals_src = inspect.getsource(mixin_cls._collection_parse_payment_vals)
        self.assertNotIn("raw_ocr", parse_vals_src)
        self.assertNotIn("seller_confirmed", parse_vals_src)
        self.assertTrue(
            hasattr(mixin_cls, "_collection_parse_payment_provenance"),
            "provenance MUST be parsed by a dedicated create-path helper",
        )
        write_src = inspect.getsource(mixin_cls._collection_allocation_write)
        idx_existing = write_src.index("_collection_vouchers_by_document_ids")
        idx_parse = write_src.index("_collection_parse_payment_provenance")
        idx_create = write_src.index("_collection_create_vouchers")
        self.assertGreater(idx_parse, idx_existing)
        self.assertGreater(idx_create, idx_parse)

    def test_exact_replay_ignores_different_and_omitted_nests(self):
        """Exact replay MUST NOT write, backfill, or mutate provenance or snapshots."""
        fields_vals = {
            "document_type": "bank_transfer",
            "amount": 22.0,
            "from_account": "KEEP-FROM",
        }
        first = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-PROV-REPLAY",
                        "document_id": "MCP-DOC-PROV-REPLAY",
                        **fields_vals,
                        "raw_ocr": dict(fields_vals),
                        "seller_confirmed": dict(fields_vals),
                    }
                ],
            }
        )
        voucher = self._voucher(first)
        self._assert_layer_matches(voucher, "ocr", fields_vals)
        before_snaps = self._snapshot_count(voucher)
        write_date = voucher.write_date

        second = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-PROV-REPLAY-OTHER",
                        "document_id": "MCP-DOC-PROV-REPLAY",
                        "document_type": "bank_transfer",
                        "amount": 999.0,
                        "raw_ocr": {
                            "document_type": "bank_transfer",
                            "amount": 1.0,
                        },
                        "seller_confirmed": {
                            "document_type": "bank_transfer",
                            "amount": 999.0,
                        },
                    }
                ],
            }
        )
        self.assertEqual(second["vouchers"], first["vouchers"])
        voucher.invalidate_recordset()
        self._assert_layer_matches(voucher, "", fields_vals)
        self._assert_layer_matches(voucher, "ocr", fields_vals)
        self._assert_layer_matches(voucher, "seller", fields_vals)
        self.assertEqual(self._snapshot_count(voucher), before_snaps)
        self.assertEqual(voucher.write_date, write_date)

        empty_ident = "MCP-PROV-REPLAY-EMPTY"
        partner = dummy_customer_partner(self.env, customer=empty_ident)
        connector = self.env.company.collection_connector_id
        self.env["collection.connector.customer.binding"].create(
            {
                "connector_id": connector.id,
                "external_customer_id": "echo-MCP-PROV-REPLAY-EMPTY",
                "identification": empty_ident,
                "partner_id": partner.id,
                "customer_code": empty_ident,
            }
        )
        empty = self.env["collection.voucher"].create(
            {
                "partner_id": partner.id,
                "document_type": "cash_deposit",
                "document_id": "MCP-DOC-PROV-REPLAY-EMPTY",
                "amount": 4.0,
                "seller_id": ensure_enabled_seller(self.env, self.internal_user).id,
            }
        )
        self._assert_empty_provenance(empty)
        retried = self._call(
            {
                "request_id": f"req-{self._testMethodName}-empty",
                "customer_identification": empty_ident,
                "payments": [
                    {
                        "customer_identification": empty_ident,
                        "document_id": "MCP-DOC-PROV-REPLAY-EMPTY",
                        "document_type": "cash_deposit",
                        "amount": 4.0,
                        "raw_ocr": {
                            "document_type": "cash_deposit",
                            "amount": 4.0,
                        },
                        "seller_confirmed": {
                            "document_type": "cash_deposit",
                            "amount": 4.0,
                        },
                    }
                ],
            }
        )
        self.assertEqual(retried["vouchers"][0]["id"], empty.id)
        empty.invalidate_recordset()
        self._assert_empty_provenance(empty)
        self.assertEqual(self._snapshot_count(empty), 0)

    def test_exact_replay_ignores_malformed_nests(self):
        """Triangulation: exact-retry MUST ignore malformed nests and still replay."""
        first = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-PROV-REPLAY-BAD",
                        "document_id": "MCP-DOC-PROV-REPLAY-BAD",
                        "document_type": "check",
                        "amount": 6.0,
                        "check_type": "common",
                    }
                ],
            }
        )
        voucher = self._voucher(first)
        second = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-PROV-REPLAY-BAD-OTHER",
                        "document_id": "MCP-DOC-PROV-REPLAY-BAD",
                        "document_type": "check",
                        "amount": 6.0,
                        "check_type": "common",
                        "raw_ocr": "not-an-object",
                        "seller_confirmed": {"amount": 6.0},
                    }
                ],
            }
        )
        self.assertEqual(second["vouchers"], first["vouchers"])
        voucher.invalidate_recordset()
        self._assert_empty_provenance(voucher)

    def test_unique_violation_replay_ignores_nests_no_backfill(self):
        """UniqueViolation exact-set replay MUST ignore nests and not backfill."""
        first = self._call(
            {
                "payments": [
                    {
                        "customer_identification": "MCP-PROV-UV",
                        "document_id": "MCP-DOC-PROV-UV",
                        "document_type": "bank_transfer",
                        "amount": 13.0,
                    }
                ],
            }
        )
        voucher = self._voucher(first)
        self._assert_empty_provenance(voucher)
        doc_ids = ["MCP-DOC-PROV-UV"]
        search_patch, calls = self._patch_voucher_search_miss_once(doc_ids)
        with mute_logger("odoo.sql_db"), search_patch:
            second = self._call(
                {
                    "request_id": f"req-{self._testMethodName}-race",
                    "payments": [
                        {
                            "customer_identification": "MCP-PROV-UV",
                            "document_id": "MCP-DOC-PROV-UV",
                            "document_type": "bank_transfer",
                            "amount": 13.0,
                            "raw_ocr": {
                                "document_type": "bank_transfer",
                                "amount": 13.0,
                            },
                            "seller_confirmed": {
                                "document_type": "bank_transfer",
                                "amount": 13.0,
                            },
                        }
                    ],
                }
            )
        self.assertGreaterEqual(calls["n"], 2)
        self.assertEqual(second["vouchers"], first["vouchers"])
        voucher.invalidate_recordset()
        self._assert_empty_provenance(voucher)
        self.assertEqual(self._snapshot_count(voucher), 0)
