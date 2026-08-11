# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.muk_mcp.core.tool import get_tool_index

# Minimal valid payloads (base64) for MCP attachment triangulation.
PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQ"
    "DJ/pLvAAAAAElFTkSuQmCC"
)
PDF_B64 = "JVBERi0xLjEKMSAwIG9iajw8Pj5lbmRvYmoKdHJhaWxlcjw8Pj4KJSVFT0YK"
TXT_B64 = "aGVsbG8gd29ybGQ="
INVALID_B64 = "!!!not-base64!!!"


class TestCollectionMcpTool(TransactionCase):
    """RED/GREEN: create_collection_voucher MCP discover, create, schema, ACL."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tool_model = cls.env["muk_mcp.tool"]
        cls.internal_user = cls._create_user(
            "collection_mcp_internal", "base.group_user"
        )
        cls.portal_user = cls._create_user("collection_mcp_portal", "base.group_portal")

    @classmethod
    def _partner_has_autopost_bills_column(cls):
        cls.env.cr.execute(
            """
            SELECT 1
              FROM information_schema.columns
             WHERE table_name = 'res_partner'
               AND column_name = 'autopost_bills'
            """
        )
        return bool(cls.env.cr.fetchone())

    @classmethod
    def _create_user(cls, login, group_xmlid):
        """Create a user; satisfy account.autopost_bills when the DB column exists."""
        partner_vals = {
            "name": login,
            "email": f"{login}@example.com",
        }
        Partner = cls.env["res.partner"].with_context(
            tracking_disable=True,
            mail_create_nolog=True,
            mail_notrack=True,
            mail_create_nosubscribe=True,
        )
        if "autopost_bills" in Partner._fields:
            partner_vals["autopost_bills"] = "ask"
            partner = Partner.create(partner_vals)
        elif cls._partner_has_autopost_bills_column():
            cls.env.cr.execute(
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
                (login, partner_vals["email"], login),
            )
            partner = Partner.browse(cls.env.cr.fetchone()[0])
        else:
            partner = Partner.create(partner_vals)

        return (
            cls.env["res.users"]
            .with_context(no_reset_password=True, tracking_disable=True)
            .create(
                {
                    "name": login,
                    "login": login,
                    "email": partner_vals["email"],
                    "partner_id": partner.id,
                    "group_ids": [(6, 0, [cls.env.ref(group_xmlid).id])],
                }
            )
        )

    def _call(self, name, arguments, user=None):
        """Run an MCP tool in-process and return its decoded JSON result."""
        env = self.env(user=user) if user else self.env(user=self.internal_user)
        text, _info = self.tool_model._call(name, arguments, env)
        return json.loads(text)

    def _payload(self, customer="MCP-CUST-NEW", payments=None):
        if payments is None:
            payments = [
                {
                    "document_id": "MCP-DOC-A",
                    "document_type": "bank_transfer",
                    "amount": 100.0,
                    "from_account": "FROM-1",
                    "to_account": "TO-1",
                },
                {
                    "document_id": "MCP-DOC-B",
                    "document_type": "check",
                    "amount": 50.0,
                    "check_number": "CHK-1",
                    "check_type": "common",
                },
            ]
        return {
            "customer_identification": customer,
            "payments": payments,
        }

    # --- 3.1 Discover + schema + all-new create ---

    def test_tool_discovered_with_write_registry_and_schema(self):
        """Tool discovered via write/mcp; no received_date; document_id required."""
        by_name = {
            entry["name"]: entry for entry in self.tool_model.get_tools(registry="mcp")
        }
        self.assertIn(
            "create_collection_voucher",
            by_name,
            "create_collection_voucher must appear in MCP registry tools",
        )
        entry = get_tool_index(self.env, registry="mcp")["create_collection_voucher"]
        self.assertEqual(entry["category"], "write")
        self.assertEqual(entry["kind"], "method")
        self.assertNotEqual(entry.get("kind"), "db")

        schema = by_name["create_collection_voucher"]["inputSchema"]
        self.assertEqual(schema["type"], "object")
        self.assertIn("customer_identification", schema["required"])
        self.assertIn("payments", schema["required"])
        self.assertNotIn(
            "received_date",
            schema.get("properties", {}),
            "MCP schema must not accept received_date",
        )
        payment_schema = schema["properties"]["payments"]["items"]
        self.assertIn("document_id", payment_schema["required"])
        self.assertIn("document_type", payment_schema["required"])
        self.assertNotIn(
            "received_date",
            payment_schema.get("properties", {}),
        )

    def test_all_new_create_returns_voucher_and_payments(self):
        """All-new document_ids create one voucher + lines and return identities."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_payments = self.env["collection.voucher.line"].search_count([])
        result = self._call("create_collection_voucher", self._payload())

        self.assertIsInstance(result["id"], int)
        self.assertTrue(result["name"])
        self.assertEqual(result["state"], "new")
        self.assertEqual(len(result["payments"]), 2)
        returned_docs = {p["document_id"] for p in result["payments"]}
        self.assertEqual(returned_docs, {"MCP-DOC-A", "MCP-DOC-B"})
        self.assertTrue(all(isinstance(p["id"], int) for p in result["payments"]))

        voucher = self.env["collection.voucher"].browse(result["id"])
        self.assertTrue(voucher.exists())
        self.assertEqual(voucher.customer_identification, "MCP-CUST-NEW")
        self.assertEqual(voucher.state, "new")
        self.assertEqual(voucher.currency_id, self.env.company.currency_id)
        self.assertEqual(len(voucher.payment_ids), 2)
        self.assertEqual(
            set(voucher.payment_ids.mapped("document_id")),
            {"MCP-DOC-A", "MCP-DOC-B"},
        )
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers + 1,
        )
        self.assertEqual(
            self.env["collection.voucher.line"].search_count([]),
            before_payments + 2,
        )

    def test_create_rejects_missing_document_id(self):
        """Triangulation: MCP payments without document_id must be rejected."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_payments = self.env["collection.voucher.line"].search_count([])
        with self.assertRaises(UserError) as err:
            self._call(
                "create_collection_voucher",
                self._payload(
                    customer="MCP-CUST-NODOC",
                    payments=[
                        {
                            "document_type": "cash_deposit",
                            "amount": 10.0,
                        }
                    ],
                ),
            )
        self.assertIn("document_id", str(err.exception).lower())
        self.assertNotIn("tool not found", str(err.exception).lower())
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertEqual(
            self.env["collection.voucher.line"].search_count([]),
            before_payments,
        )

    def test_create_rejects_empty_document_id(self):
        """Triangulation: empty-string document_id must be rejected with no writes."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError) as err:
            self._call(
                "create_collection_voucher",
                self._payload(
                    customer="MCP-CUST-EMPTYDOC",
                    payments=[
                        {
                            "document_id": "  ",
                            "document_type": "unsupported",
                        }
                    ],
                ),
            )
        self.assertIn("document_id", str(err.exception).lower())
        self.assertNotIn("tool not found", str(err.exception).lower())
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )

    def test_create_rejects_empty_payments(self):
        """Triangulation: empty payments list must be rejected."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError) as err:
            self._call(
                "create_collection_voucher",
                {
                    "customer_identification": "MCP-CUST-NOPAY",
                    "payments": [],
                },
            )
        message = str(err.exception).lower()
        self.assertTrue(
            "payment" in message or "payments" in message,
            f"Expected payments validation message, got: {err.exception}",
        )
        self.assertNotIn("tool not found", message)
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )

    # --- 3.2 ACL denial ---

    def test_portal_user_denied_no_writes(self):
        """Non-permitted caller gets AccessError and writes no voucher/payment rows."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_payments = self.env["collection.voucher.line"].search_count([])
        with self.assertRaises(AccessError):
            self._call(
                "create_collection_voucher",
                self._payload(
                    customer="MCP-PORTAL-DENY",
                    payments=[
                        {
                            "document_id": "MCP-DOC-PORTAL",
                            "document_type": "bank_transfer",
                            "amount": 1.0,
                        }
                    ],
                ),
                user=self.portal_user,
            )
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
            "ACL denial must not create vouchers",
        )
        self.assertEqual(
            self.env["collection.voucher.line"].search_count([]),
            before_payments,
            "ACL denial must not create payments",
        )
        self.assertFalse(
            self.env["collection.voucher.line"].search(
                [("document_id", "=", "MCP-DOC-PORTAL")]
            ),
        )

    # --- 4.1 Exact-retry ---

    def test_exact_retry_returns_same_ids_no_new_rows(self):
        """Exact same document_id set must replay existing voucher with no new rows."""
        first = self._call(
            "create_collection_voucher",
            self._payload(
                customer="MCP-CUST-RETRY",
                payments=[
                    {
                        "document_id": "MCP-DOC-RETRY-A",
                        "document_type": "bank_transfer",
                        "amount": 10.0,
                    },
                    {
                        "document_id": "MCP-DOC-RETRY-B",
                        "document_type": "cash_deposit",
                        "amount": 20.0,
                    },
                ],
            ),
        )
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_payments = self.env["collection.voucher.line"].search_count([])

        # Customer mismatch must be ignored on document_id match (design).
        second = self._call(
            "create_collection_voucher",
            self._payload(
                customer="MCP-CUST-RETRY-OTHER",
                payments=[
                    {
                        "document_id": "MCP-DOC-RETRY-A",
                        "document_type": "bank_transfer",
                        "amount": 999.0,
                    },
                    {
                        "document_id": "MCP-DOC-RETRY-B",
                        "document_type": "cash_deposit",
                        "amount": 888.0,
                    },
                ],
            ),
        )

        self.assertEqual(second["id"], first["id"])
        self.assertEqual(second["name"], first["name"])
        self.assertEqual(second["state"], first["state"])
        self.assertEqual(
            sorted(second["payments"], key=lambda p: p["document_id"]),
            sorted(first["payments"], key=lambda p: p["document_id"]),
        )
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertEqual(
            self.env["collection.voucher.line"].search_count([]),
            before_payments,
        )
        voucher = self.env["collection.voucher"].browse(first["id"])
        self.assertEqual(voucher.customer_identification, "MCP-CUST-RETRY")

    # --- 4.2 In-call duplicate document_id ---

    def test_in_call_duplicate_document_id_rejects_no_writes(self):
        """Two payments sharing a document_id in one call must reject with no writes."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_payments = self.env["collection.voucher.line"].search_count([])
        with self.assertRaises(UserError) as err:
            self._call(
                "create_collection_voucher",
                self._payload(
                    customer="MCP-CUST-INCALL-DUP",
                    payments=[
                        {
                            "document_id": "MCP-DOC-DUP-SAME",
                            "document_type": "bank_transfer",
                            "amount": 1.0,
                        },
                        {
                            "document_id": "MCP-DOC-DUP-SAME",
                            "document_type": "check",
                            "amount": 2.0,
                        },
                    ],
                ),
            )
        message = str(err.exception).lower()
        self.assertTrue(
            "document_id" in message or "duplicate" in message,
            f"Expected duplicate document_id message, got: {err.exception}",
        )
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertEqual(
            self.env["collection.voucher.line"].search_count([]),
            before_payments,
        )
        self.assertFalse(
            self.env["collection.voucher.line"].search(
                [("document_id", "=", "MCP-DOC-DUP-SAME")]
            ),
        )

    # --- 4.3 Partial-conflict ---

    def test_partial_conflict_rejects_no_writes(self):
        """Some existing + some new document_ids must reject with no writes."""
        self._call(
            "create_collection_voucher",
            self._payload(
                customer="MCP-CUST-PARTIAL-SEED",
                payments=[
                    {
                        "document_id": "MCP-DOC-PARTIAL-EXIST",
                        "document_type": "bank_transfer",
                        "amount": 5.0,
                    }
                ],
            ),
        )
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_payments = self.env["collection.voucher.line"].search_count([])

        with self.assertRaises(UserError) as err:
            self._call(
                "create_collection_voucher",
                self._payload(
                    customer="MCP-CUST-PARTIAL",
                    payments=[
                        {
                            "document_id": "MCP-DOC-PARTIAL-EXIST",
                            "document_type": "bank_transfer",
                            "amount": 5.0,
                        },
                        {
                            "document_id": "MCP-DOC-PARTIAL-NEW",
                            "document_type": "cash_deposit",
                            "amount": 7.0,
                        },
                    ],
                ),
            )
        self.assertNotIn("tool not found", str(err.exception).lower())
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertEqual(
            self.env["collection.voucher.line"].search_count([]),
            before_payments,
        )
        self.assertFalse(
            self.env["collection.voucher.line"].search(
                [("document_id", "=", "MCP-DOC-PARTIAL-NEW")]
            ),
        )

    # --- 4.4 Cross-voucher-conflict ---

    def test_cross_voucher_conflict_rejects_no_writes(self):
        """document_ids spanning two vouchers must reject with no writes."""
        self._call(
            "create_collection_voucher",
            self._payload(
                customer="MCP-CUST-CROSS-A",
                payments=[
                    {
                        "document_id": "MCP-DOC-CROSS-A",
                        "document_type": "bank_transfer",
                        "amount": 1.0,
                    }
                ],
            ),
        )
        self._call(
            "create_collection_voucher",
            self._payload(
                customer="MCP-CUST-CROSS-B",
                payments=[
                    {
                        "document_id": "MCP-DOC-CROSS-B",
                        "document_type": "check",
                        "amount": 2.0,
                    }
                ],
            ),
        )
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_payments = self.env["collection.voucher.line"].search_count([])

        with self.assertRaises(UserError) as err:
            self._call(
                "create_collection_voucher",
                self._payload(
                    customer="MCP-CUST-CROSS-MERGE",
                    payments=[
                        {
                            "document_id": "MCP-DOC-CROSS-A",
                            "document_type": "bank_transfer",
                            "amount": 1.0,
                        },
                        {
                            "document_id": "MCP-DOC-CROSS-B",
                            "document_type": "check",
                            "amount": 2.0,
                        },
                    ],
                ),
            )
        self.assertNotIn("tool not found", str(err.exception).lower())
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertEqual(
            self.env["collection.voucher.line"].search_count([]),
            before_payments,
        )

    # --- 4.5 UniqueViolation → re-lookup replay / reject ---

    def _patch_payment_search_miss_once(self, document_ids):
        """Simulate a race: first document_id lookup misses rows that already exist."""
        Payment = self.env["collection.voucher.line"]
        empty = Payment.browse()
        real_search = type(Payment).search
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
            if model_self._name == "collection.voucher.line" and is_doc_lookup:
                calls["n"] += 1
                if calls["n"] == 1:
                    return empty
            return real_search(model_self, domain, *args, **kwargs)

        return patch("odoo.models.Model.search", search_proxy), calls

    def test_unique_violation_full_match_replays(self):
        """Race: UniqueViolation then full same-voucher re-lookup must replay."""
        first = self._call(
            "create_collection_voucher",
            self._payload(
                customer="MCP-CUST-UV-REPLAY",
                payments=[
                    {
                        "document_id": "MCP-DOC-UV-A",
                        "document_type": "bank_transfer",
                        "amount": 11.0,
                    },
                    {
                        "document_id": "MCP-DOC-UV-B",
                        "document_type": "cash_deposit",
                        "amount": 22.0,
                    },
                ],
            ),
        )
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_payments = self.env["collection.voucher.line"].search_count([])
        doc_ids = ["MCP-DOC-UV-A", "MCP-DOC-UV-B"]
        search_patch, calls = self._patch_payment_search_miss_once(doc_ids)

        with mute_logger("odoo.sql_db"), search_patch:
            second = self._call(
                "create_collection_voucher",
                self._payload(
                    customer="MCP-CUST-UV-REPLAY-OTHER",
                    payments=[
                        {
                            "document_id": "MCP-DOC-UV-A",
                            "document_type": "bank_transfer",
                            "amount": 11.0,
                        },
                        {
                            "document_id": "MCP-DOC-UV-B",
                            "document_type": "cash_deposit",
                            "amount": 22.0,
                        },
                    ],
                ),
            )

        self.assertGreaterEqual(
            calls["n"],
            2,
            "Expected initial miss + post-UniqueViolation re-lookup",
        )
        self.assertEqual(second["id"], first["id"])
        self.assertEqual(second["name"], first["name"])
        self.assertEqual(
            sorted(second["payments"], key=lambda p: p["document_id"]),
            sorted(first["payments"], key=lambda p: p["document_id"]),
        )
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertEqual(
            self.env["collection.voucher.line"].search_count([]),
            before_payments,
        )

    def test_unique_violation_partial_match_rejects(self):
        """Triangulation: UniqueViolation then incomplete re-lookup must UserError."""
        self._call(
            "create_collection_voucher",
            self._payload(
                customer="MCP-CUST-UV-PARTIAL",
                payments=[
                    {
                        "document_id": "MCP-DOC-UV-PARTIAL-EXIST",
                        "document_type": "bank_transfer",
                        "amount": 3.0,
                    }
                ],
            ),
        )
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_payments = self.env["collection.voucher.line"].search_count([])
        doc_ids = ["MCP-DOC-UV-PARTIAL-EXIST", "MCP-DOC-UV-PARTIAL-NEW"]
        search_patch, _calls = self._patch_payment_search_miss_once(doc_ids)

        with (
            mute_logger("odoo.sql_db"),
            search_patch,
            self.assertRaises(UserError) as err,
        ):
            self._call(
                "create_collection_voucher",
                self._payload(
                    customer="MCP-CUST-UV-PARTIAL-CALL",
                    payments=[
                        {
                            "document_id": "MCP-DOC-UV-PARTIAL-EXIST",
                            "document_type": "bank_transfer",
                            "amount": 3.0,
                        },
                        {
                            "document_id": "MCP-DOC-UV-PARTIAL-NEW",
                            "document_type": "check",
                            "amount": 4.0,
                        },
                    ],
                ),
            )
        self.assertNotIn("tool not found", str(err.exception).lower())
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers,
        )
        self.assertEqual(
            self.env["collection.voucher.line"].search_count([]),
            before_payments,
        )
        self.assertFalse(
            self.env["collection.voucher.line"].search(
                [("document_id", "=", "MCP-DOC-UV-PARTIAL-NEW")]
            ),
        )


class TestCollectionMcpAttachment(TransactionCase):
    """RED/GREEN: optional nested MCP attachment on create; exact-retry ignore."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tool_model = cls.env["muk_mcp.tool"]
        cls.internal_user = cls.env.ref("base.user_admin")

    def _call(self, name, arguments, user=None):
        env = self.env(user=user) if user else self.env(user=self.internal_user)
        text, _info = self.tool_model._call(name, arguments, env)
        return json.loads(text)

    def _line_attachments(self, line):
        return self.env["ir.attachment"].search(
            [
                ("res_model", "=", "collection.voucher.line"),
                ("res_id", "=", line.id),
                ("res_field", "=", "attachment"),
            ]
        )

    def _nest(self, name, mimetype, datas):
        return {"name": name, "mimetype": mimetype, "datas": datas}

    def test_create_with_valid_png_nest_persists_atomically(self):
        """All-new create with valid nested PNG persists voucher+line+file."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_payments = self.env["collection.voucher.line"].search_count([])
        before_atts = self.env["ir.attachment"].search_count(
            [
                ("res_model", "=", "collection.voucher.line"),
                ("res_field", "=", "attachment"),
            ]
        )
        result = self._call(
            "create_collection_voucher",
            {
                "customer_identification": "MCP-ATT-PNG",
                "payments": [
                    {
                        "document_id": "MCP-DOC-ATT-PNG",
                        "document_type": "bank_transfer",
                        "amount": 12.0,
                        "attachment": self._nest("proof.png", "image/png", PNG_B64),
                    }
                ],
            },
        )
        self.assertIsInstance(result["id"], int)
        self.assertEqual(len(result["payments"]), 1)
        line = self.env["collection.voucher.line"].browse(result["payments"][0]["id"])
        self.assertTrue(line.exists())
        self.assertEqual(line.attachment_filename, "proof.png")
        self.assertTrue(line.attachment)
        attachments = self._line_attachments(line)
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments.datas, PNG_B64.encode())
        self.assertEqual(
            self.env["collection.voucher"].search_count([]),
            before_vouchers + 1,
        )
        self.assertEqual(
            self.env["collection.voucher.line"].search_count([]),
            before_payments + 1,
        )
        self.assertEqual(
            self.env["ir.attachment"].search_count(
                [
                    ("res_model", "=", "collection.voucher.line"),
                    ("res_field", "=", "attachment"),
                ]
            ),
            before_atts + 1,
        )

    def test_create_with_valid_pdf_nest_persists(self):
        """Triangulation: valid nested PDF also persists via ir.attachment."""
        result = self._call(
            "create_collection_voucher",
            {
                "customer_identification": "MCP-ATT-PDF",
                "payments": [
                    {
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
        line = self.env["collection.voucher.line"].browse(result["payments"][0]["id"])
        self.assertEqual(line.attachment_filename, "receipt.pdf")
        self.assertEqual(len(self._line_attachments(line)), 1)
        self.assertEqual(self._line_attachments(line).datas, PDF_B64.encode())

    def test_create_omitting_nest_still_creates(self):
        """Omit nest remains backward-compatible and creates voucher+lines."""
        result = self._call(
            "create_collection_voucher",
            {
                "customer_identification": "MCP-ATT-OMIT",
                "payments": [
                    {
                        "document_id": "MCP-DOC-ATT-OMIT",
                        "document_type": "check",
                        "amount": 3.0,
                        "check_type": "common",
                    }
                ],
            },
        )
        line = self.env["collection.voucher.line"].browse(result["payments"][0]["id"])
        self.assertTrue(line.exists())
        self.assertFalse(line.attachment)
        self.assertFalse(line.attachment_filename)
        self.assertFalse(self._line_attachments(line))

    def test_create_mime_mismatch_rejects_no_writes(self):
        """Declared MIME mismatch / non-allow-list must UserError with no writes."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_payments = self.env["collection.voucher.line"].search_count([])
        before_atts = self.env["ir.attachment"].search_count(
            [
                ("res_model", "=", "collection.voucher.line"),
                ("res_field", "=", "attachment"),
            ]
        )
        with self.assertRaises(UserError) as err:
            self._call(
                "create_collection_voucher",
                {
                    "customer_identification": "MCP-ATT-MIME",
                    "payments": [
                        {
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
            self.env["collection.voucher.line"].search_count([]),
            before_payments,
        )
        self.assertEqual(
            self.env["ir.attachment"].search_count(
                [
                    ("res_model", "=", "collection.voucher.line"),
                    ("res_field", "=", "attachment"),
                ]
            ),
            before_atts,
        )
        self.assertFalse(
            self.env["collection.voucher.line"].search(
                [("document_id", "=", "MCP-DOC-ATT-MIME")]
            ),
        )

    def test_create_bad_base64_rejects_no_writes(self):
        """Triangulation: bad base64 nest must UserError with no writes."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_payments = self.env["collection.voucher.line"].search_count([])
        with self.assertRaises(UserError) as err:
            self._call(
                "create_collection_voucher",
                {
                    "customer_identification": "MCP-ATT-B64",
                    "payments": [
                        {
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
        self.assertEqual(
            self.env["collection.voucher.line"].search_count([]),
            before_payments,
        )
        self.assertFalse(
            self.env["collection.voucher.line"].search(
                [("document_id", "=", "MCP-DOC-ATT-B64")]
            ),
        )

    def test_create_text_mime_rejects_no_writes(self):
        """Triangulation: text content with text/plain declared must reject."""
        before_vouchers = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError):
            self._call(
                "create_collection_voucher",
                {
                    "customer_identification": "MCP-ATT-TXT",
                    "payments": [
                        {
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
            self.env["collection.voucher.line"].search(
                [("document_id", "=", "MCP-DOC-ATT-TXT")]
            ),
        )

    def test_exact_retry_with_nest_does_not_replace_attachment(self):
        """Exact-retry with a different nest must leave stored attachment unchanged."""
        first = self._call(
            "create_collection_voucher",
            {
                "customer_identification": "MCP-ATT-RETRY",
                "payments": [
                    {
                        "document_id": "MCP-DOC-ATT-RETRY",
                        "document_type": "bank_transfer",
                        "amount": 5.0,
                        "attachment": self._nest("original.png", "image/png", PNG_B64),
                    }
                ],
            },
        )
        line = self.env["collection.voucher.line"].browse(first["payments"][0]["id"])
        original_att_ids = self._line_attachments(line).ids
        self.assertEqual(len(original_att_ids), 1)
        self.assertEqual(line.attachment_filename, "original.png")
        self.assertEqual(line.attachment, PNG_B64.encode())
        before_atts = self.env["ir.attachment"].search_count(
            [
                ("res_model", "=", "collection.voucher.line"),
                ("res_field", "=", "attachment"),
            ]
        )

        second = self._call(
            "create_collection_voucher",
            {
                "customer_identification": "MCP-ATT-RETRY-OTHER",
                "payments": [
                    {
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
        self.assertEqual(second["id"], first["id"])
        line.invalidate_recordset()
        self.assertEqual(line.attachment_filename, "original.png")
        self.assertEqual(line.attachment, PNG_B64.encode())
        self.assertEqual(self._line_attachments(line).ids, original_att_ids)
        self.assertEqual(
            self.env["ir.attachment"].search_count(
                [
                    ("res_model", "=", "collection.voucher.line"),
                    ("res_field", "=", "attachment"),
                ]
            ),
            before_atts,
        )

    def test_exact_retry_with_nest_does_not_add_when_line_has_none(self):
        """Exact-retry nest MUST NOT add an attachment when the line has none."""
        first = self._call(
            "create_collection_voucher",
            {
                "customer_identification": "MCP-ATT-RETRY-EMPTY",
                "payments": [
                    {
                        "document_id": "MCP-DOC-ATT-RETRY-EMPTY",
                        "document_type": "cash_deposit",
                        "amount": 4.0,
                    }
                ],
            },
        )
        line = self.env["collection.voucher.line"].browse(first["payments"][0]["id"])
        self.assertFalse(line.attachment)
        before_atts = self.env["ir.attachment"].search_count(
            [
                ("res_model", "=", "collection.voucher.line"),
                ("res_field", "=", "attachment"),
            ]
        )

        second = self._call(
            "create_collection_voucher",
            {
                "customer_identification": "MCP-ATT-RETRY-EMPTY-OTHER",
                "payments": [
                    {
                        "document_id": "MCP-DOC-ATT-RETRY-EMPTY",
                        "document_type": "cash_deposit",
                        "amount": 4.0,
                        "attachment": self._nest("late.png", "image/png", PNG_B64),
                    }
                ],
            },
        )
        self.assertEqual(second["id"], first["id"])
        line.invalidate_recordset()
        self.assertFalse(line.attachment)
        self.assertFalse(line.attachment_filename)
        self.assertFalse(self._line_attachments(line))
        self.assertEqual(
            self.env["ir.attachment"].search_count(
                [
                    ("res_model", "=", "collection.voucher.line"),
                    ("res_field", "=", "attachment"),
                ]
            ),
            before_atts,
        )

    def test_exact_retry_without_nest_leaves_existing_attachment(self):
        """Triangulation: exact-retry omitting nest must not clear existing file."""
        first = self._call(
            "create_collection_voucher",
            {
                "customer_identification": "MCP-ATT-RETRY-OMIT",
                "payments": [
                    {
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
        line = self.env["collection.voucher.line"].browse(first["payments"][0]["id"])
        second = self._call(
            "create_collection_voucher",
            {
                "customer_identification": "MCP-ATT-RETRY-OMIT-OTHER",
                "payments": [
                    {
                        "document_id": "MCP-DOC-ATT-RETRY-OMIT",
                        "document_type": "check",
                        "amount": 6.0,
                        "check_type": "common",
                    }
                ],
            },
        )
        self.assertEqual(second["id"], first["id"])
        line.invalidate_recordset()
        self.assertEqual(line.attachment_filename, "keep.pdf")
        self.assertEqual(line.attachment, PDF_B64.encode())
        self.assertEqual(len(self._line_attachments(line)), 1)
