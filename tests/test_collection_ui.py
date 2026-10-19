# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast
import json

from lxml import etree

from odoo.tests import TransactionCase

from .test_collection_payment import (
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
)

BANK_TRANSFER_FIELDS = (
    "from_account",
    "to_account",
    "voucher_number",
    "voucher_date",
)
CHECK_FIELDS = (
    "check_number",
    "check_bank",
    "check_type",
    "check_issue_date",
    "check_payment_date",
)
SHARED_PAYMENT_FIELDS = ("document_type", "document_id", "amount")
CASH_DEPOSIT_KEYS = ("voucher_number", "voucher_date")
NOTEBOOK_CURRENT = "Current"
NOTEBOOK_RAW = "Raw OCR"
NOTEBOOK_SELLER = "Seller Confirmed"
NOTEBOOK_HISTORY = "History"
SHEET_NOTEBOOK_VOUCHERS = "Vouchers"
SHEET_NOTEBOOK_ALLOCATIONS = "Allocations"
SHEET_NOTEBOOK_DEBT = "Debt"
SHEET_ALLOCATION_COLUMNS = (
    "name",
    "partner_id",
    "total_debt",
    "total_vouchers",
    "residual",
)
SHEET_ALLOCATION_COLUMN_STRINGS = {
    "name": "Reference",
    "partner_id": "Customer",
    "total_debt": "Total Debt",
    "total_vouchers": "Total Vouchers Applied",
    "residual": "Residual",
}
ALLOCATION_NOTEBOOK_CUSTOMER_DEBT = "Customer Debt"
ALLOCATION_NOTEBOOK_RECEIPTS = "Receipts"
RECEIPT_NOTEBOOK_VALUES = "Values"
RECEIPT_NOTEBOOK_APPLIED_DEBT = "Applied Debt"
ALLOCATION_TOTAL_FIELDS = (
    "total_vouchers",
    "total_applied",
    "total_debt",
    "total_invoices",
    "total_quotations",
    "residual",
)
PROVENANCE_LAYERS = (
    (NOTEBOOK_RAW, "ocr_", "ocr_document_type"),
    (NOTEBOOK_SELLER, "seller_", "seller_document_type"),
)
REMOVED_PAYMENT_LINE_XMLIDS = (
    "collection.view_collection_voucher_line_list",
    "collection.view_collection_voucher_line_search",
    "collection.action_collection_voucher_line",
    "collection.menu_collection_voucher_line",
)


class TestCollectionUi(TransactionCase):
    """Registry/arch coverage for Menu and form behaviors (no browser E2E)."""

    REQUIRED_LIST_SEARCH_FIELDS = (
        "name",
        "partner_id",
        "create_date",
        "state",
        "document_type",
        "amount",
    )
    VIEW_XMLIDS = (
        "collection.view_collection_voucher_list",
        "collection.view_collection_voucher_search",
        "collection.view_collection_voucher_form",
    )
    VISIBLE_LIST_FIELDS = (
        "name",
        "create_date",
        "sheet_id",
        "seller_id",
        "document_type",
        "amount",
        "state",
    )
    OPTIONAL_HIDE_LIST_FIELDS = (
        "partner_id",
        "company_id",
        "document_id",
        "reviewed_by",
        "reviewed_at",
    )
    DOCUMENT_TYPE_FILTERS = (
        "bank_transfer",
        "check",
        "cash_deposit",
        "seller_deposit",
    )
    ATTACHMENT_ACCEPT = "image/*,.pdf"

    def _arch_root(self, xmlid):
        view = self.env.ref(xmlid)
        return etree.fromstring(view.arch)

    def _field_names(self, root, xpath=".//field"):
        return [node.get("name") for node in root.xpath(xpath) if node.get("name")]

    def _field_nodes(self, root, field_name):
        return root.xpath(f'//field[@name="{field_name}"]')

    def _list_visible_field_names(self, root):
        """Direct list columns that are neither hidden nor optional-hide."""
        names = []
        for node in root.xpath("./field"):
            if (node.get("column_invisible") or "").lower() in ("1", "true"):
                continue
            if node.get("optional") == "hide":
                continue
            if (node.get("invisible") or "").lower() in ("1", "true"):
                continue
            names.append(node.get("name"))
        return names

    def _assert_create_date_readonly(self, root, context):
        nodes = self._field_nodes(root, "create_date")
        self.assertTrue(nodes, f"{context} must include create_date")
        for node in nodes:
            self.assertIn(
                node.get("readonly"),
                ("1", "True", "true"),
                (
                    f"{context} create_date must be readonly "
                    f"(got {node.get('readonly')!r})"
                ),
            )

    def _assert_create_edit_enabled(self, root, context):
        self.assertNotEqual(
            (root.get("create") or "").lower(),
            "false",
            f"{context} must keep create enabled",
        )
        self.assertNotEqual(
            (root.get("edit") or "").lower(),
            "false",
            f"{context} must keep edit enabled",
        )

    def _assert_no_attachment_binary_widgets(self, root, context):
        """Assert arch has no Binary attachment/filename widgets."""
        attachment_nodes = root.xpath('.//field[@name="attachment"]')
        self.assertFalse(
            attachment_nodes,
            f"{context} must not declare a Binary attachment field",
        )
        filename_nodes = root.xpath('.//field[@name="attachment_filename"]')
        self.assertFalse(
            filename_nodes,
            f"{context} must not declare attachment_filename",
        )
        for node in root.xpath(".//field[@widget='binary']"):
            options = node.get("options") or ""
            self.assertIn("image/*", options, f"{context} accept must allow image/*")
            self.assertIn(".pdf", options, f"{context} accept must allow PDF (.pdf)")
            self.assertIn(
                self.ATTACHMENT_ACCEPT,
                options.replace(" ", ""),
                (
                    f"{context} leftover file picker accept must be "
                    f"{self.ATTACHMENT_ACCEPT!r} (got {options!r})"
                ),
            )

    def _assert_form_chatter_open_attachments(self, root):
        chatter = root.xpath(".//chatter")
        self.assertTrue(chatter, "form must keep chatter for attaching after save")
        self.assertEqual(
            (chatter[0].get("open_attachments") or "").lower(),
            "true",
            "form chatter must set open_attachments=True",
        )
        self.assertEqual(
            (chatter[0].get("reload_on_attachment") or "").lower(),
            "true",
            "form chatter must reload when designated proof is attached",
        )

    def _assert_form_attachment_preview(self, root):
        preview = root.xpath('./div[contains(@class, "o_attachment_preview")]')
        self.assertTrue(
            preview,
            "form must include o_attachment_preview like vendor bills",
        )
        self.assertEqual(
            preview[0].getparent().tag,
            "form",
            "attachment preview must be a form sibling of sheet/chatter",
        )

    def _assert_invisible_for_document_type(self, node, expected_type, field_name):
        invisible = node.get("invisible") or ""
        self.assertIn(
            "document_type",
            invisible,
            f"{field_name} must use typed invisible= (got {invisible!r})",
        )
        self.assertIn(
            expected_type,
            invisible,
            f"{field_name} invisible= must mention {expected_type}",
        )
        self.assertNotIn(
            "attrs",
            node.attrib,
            f"{field_name} must use Odoo 19 invisible=, not attrs",
        )

    def _notebook_page(self, root, string):
        pages = root.xpath(f'//notebook/page[@string="{string}"]')
        self.assertTrue(pages, f"form notebook must include page {string!r}")
        self.assertEqual(
            len(pages),
            1,
            f"form notebook page {string!r} must appear once",
        )
        return pages[0]

    def _assert_readonly_field(self, node, field_name):
        self.assertIn(
            node.get("readonly"),
            ("1", "True", "true"),
            f"{field_name} must be readonly (got {node.get('readonly')!r})",
        )

    def _parse_view_options(self, raw):
        text = (raw or "").strip()
        if not text:
            return {}
        try:
            return ast.literal_eval(text)
        except (ValueError, SyntaxError):
            return json.loads(text.replace("'", '"'))

    def _attr_is_false(self, value):
        return (value or "").lower() in ("0", "false")

    def test_menu_and_action_xmlids(self):
        """Collections → Payment Vouchers menu must wire the voucher act_window."""
        root_menu = self.env.ref("collection.menu_collection_root")
        voucher_menu = self.env.ref("collection.menu_collection_voucher")
        action = self.env.ref("collection.action_collection_voucher")

        self.assertEqual(root_menu.name, "Collections")
        self.assertFalse(root_menu.parent_id)
        self.assertEqual(voucher_menu.name, "Payment Vouchers")
        self.assertEqual(voucher_menu.parent_id, root_menu)
        self.assertEqual(voucher_menu.action, action)
        self.assertEqual(action.res_model, "collection.voucher")
        self.assertEqual(action.view_mode, "list,form")
        self.assertNotIn("kanban", action.view_mode)
        self.assertEqual(voucher_menu.sequence, 10)
        self.assertEqual(
            self.env.ref("collection.menu_collection_config").sequence,
            100,
        )
        self.assertLess(
            voucher_menu.sequence,
            self.env.ref("collection.menu_collection_config").sequence,
            "Payment Vouchers must appear before Configuration",
        )
        self.assertEqual(
            action.search_view_id,
            self.env.ref("collection.view_collection_voucher_search"),
        )
        self.assertEqual(action.path, "collection-vouchers")

    def test_payment_line_xmlids_removed(self):
        """Payment Lines list/search/action/menu xmlids MUST be gone."""
        for xmlid in REMOVED_PAYMENT_LINE_XMLIDS:
            self.assertFalse(
                self.env.ref(xmlid, raise_if_not_found=False),
                f"{xmlid} must be removed",
            )

    def test_load_menus_omits_payment_lines(self):
        """Collections → Payment Lines MUST NOT appear in load_menus."""
        root_menu = self.env.ref("collection.menu_collection_root")
        voucher_menu = self.env.ref("collection.menu_collection_voucher")
        leftover = self.env["ir.ui.menu"].search([("name", "=", "Payment Lines")])
        self.assertFalse(
            leftover,
            "Payment Lines menu record must not exist",
        )
        menus = self.env["ir.ui.menu"].load_menus(False)
        self.assertIn("root", menus)
        self.assertIn(root_menu.id, menus)
        self.assertIn(voucher_menu.id, menus)
        for menu_id, data in menus.items():
            if menu_id == "root" or not isinstance(data, dict):
                continue
            self.assertNotEqual(
                data.get("name"),
                "Payment Lines",
                "load_menus must omit Payment Lines",
            )

    def test_list_and_search_show_required_fields(self):
        """List and search arches must expose reference, ID, create_date, status."""
        list_root = self._arch_root("collection.view_collection_voucher_list")
        search_root = self._arch_root("collection.view_collection_voucher_search")

        self.assertEqual(list_root.tag, "list")
        self.assertNotEqual(list_root.tag, "tree")
        self.assertEqual(search_root.tag, "search")

        list_fields = self._field_names(list_root)
        search_fields = self._field_names(search_root)
        for field_name in self.REQUIRED_LIST_SEARCH_FIELDS:
            self.assertIn(
                field_name,
                list_fields,
                f"list view must show field {field_name}",
            )
            self.assertIn(
                field_name,
                search_fields,
                f"search view must show field {field_name}",
            )
        self._assert_create_date_readonly(list_root, "list")
        self.assertEqual(
            self._list_visible_field_names(list_root),
            list(self.VISIBLE_LIST_FIELDS),
            "Payment Vouchers list visible columns must match spec order",
        )
        group_create = search_root.xpath('//filter[contains(@context, "create_date")]')
        self.assertTrue(
            group_create,
            "search view must offer group_by create_date",
        )

    def test_search_filters_draft_validated_seller_collections(self):
        """Payment Vouchers search MUST filter each voucher state."""
        search_root = self._arch_root("collection.view_collection_voucher_search")
        for value in ("draft", "validated_seller", "validated_collections"):
            filters = search_root.xpath(f'//filter[contains(@domain, "{value}")]')
            matching = [
                node for node in filters if "state" in (node.get("domain") or "")
            ]
            self.assertTrue(
                matching,
                f"Payment Vouchers search must filter state={value}",
            )

    def test_list_hides_optional_and_currency_columns(self):
        """partner_id/company_id/document_id optional-hide; currency_id invisible."""
        list_root = self._arch_root("collection.view_collection_voucher_list")
        for field_name in self.OPTIONAL_HIDE_LIST_FIELDS:
            nodes = self._field_nodes(list_root, field_name)
            self.assertEqual(
                len(nodes),
                1,
                f"list must declare {field_name} once as optional hide",
            )
            self.assertEqual(
                nodes[0].get("optional"),
                "hide",
                f"list {field_name} must be optional=hide",
            )
        currency = self._field_nodes(list_root, "currency_id")
        self.assertEqual(len(currency), 1, "list must declare currency_id once")
        self.assertEqual(
            (currency[0].get("column_invisible") or "").lower(),
            "1",
            "list currency_id must be column-invisible",
        )

    def test_search_filters_each_document_type(self):
        """Payment Vouchers search MUST filter each document_type."""
        search_root = self._arch_root("collection.view_collection_voucher_search")
        for value in self.DOCUMENT_TYPE_FILTERS:
            filters = search_root.xpath(f'//filter[contains(@domain, "{value}")]')
            matching = [
                node
                for node in filters
                if "document_type" in (node.get("domain") or "")
            ]
            self.assertTrue(
                matching,
                f"Payment Vouchers search must filter document_type={value}",
            )

    def test_search_created_on_is_date_filter(self):
        """Created On MUST be a date filter on create_date, not only group_by."""
        search_root = self._arch_root("collection.view_collection_voucher_search")
        date_filters = search_root.xpath('//filter[@date="create_date"]')
        self.assertTrue(
            date_filters,
            "Payment Vouchers search must include date=create_date filter",
        )
        self.assertEqual(
            date_filters[0].get("date"),
            "create_date",
        )

    def test_stages_kanban_deleted_action_is_list_form(self):
        """Stages kanban MUST be deleted; Payment Vouchers view_mode is list,form."""
        self.assertFalse(
            self.env.ref(
                "collection.view_collection_voucher_kanban",
                raise_if_not_found=False,
            ),
            "stages kanban xmlid must be deleted",
        )
        leftover = self.env["ir.ui.view"].search(
            [
                ("name", "=", "collection.voucher.kanban"),
                ("model", "=", "collection.voucher"),
            ]
        )
        self.assertFalse(
            leftover,
            "leftover stages kanban ir.ui.view must be deleted",
        )
        action = self.env.ref("collection.action_collection_voucher")
        self.assertEqual(action.view_mode, "list,form")
        self.assertNotIn("kanban", action.view_mode)
        self.assertFalse(
            self.env.ref(
                "collection.view_collection_voucher_reassign_kanban",
                raise_if_not_found=False,
            ),
            "Reassign Customers kanban MUST NOT remain",
        )

    def test_reassign_kanban_xmlid_deleted(self):
        """Reassign Customers kanban XMLID and leftover ir.ui.view MUST be gone."""
        self.assertFalse(
            self.env.ref(
                "collection.view_collection_voucher_reassign_kanban",
                raise_if_not_found=False,
            ),
            "reassign kanban xmlid must be deleted",
        )
        leftover = self.env["ir.ui.view"].search(
            [
                ("name", "=", "collection.voucher.reassign.kanban"),
                ("model", "=", "collection.voucher"),
            ]
        )
        self.assertFalse(
            leftover,
            "leftover reassign kanban ir.ui.view must be deleted",
        )
        form_root = self._arch_root("collection.view_collection_sheet_form")
        self.assertFalse(
            form_root.xpath('./header/button[@name="action_open_voucher_reassign"]'),
            "sheet form header must not expose Reassign Customers",
        )

    def test_remove_from_sheet_shows_only_on_open_or_submitted_sheets(self):
        voucher_form = self._arch_root("collection.view_collection_voucher_form")
        button = voucher_form.xpath(
            './/header/button[@name="action_remove_from_sheet"]'
        )
        self.assertEqual(len(button), 1, "voucher form must offer Remove from Sheet")
        self.assertEqual(button[0].get("string"), "Remove from Sheet")
        self.assertEqual(
            button[0].get("invisible"),
            "not sheet_id or sheet_state not in ('open', 'submitted')",
        )
        self.assertEqual(button[0].get("groups"), "collection.group_collection_user")
        sheet_form = self._arch_root("collection.view_collection_sheet_form")
        row = sheet_form.xpath(
            './/field[@name="voucher_ids"]/list/button'
            '[@name="action_remove_from_sheet"]'
        )
        self.assertEqual(len(row), 1, "sheet Vouchers tab must offer Remove")
        self.assertEqual(row[0].get("icon"), "fa-trash-o")
        self.assertEqual(row[0].get("title"), "Remove from Sheet")
        self.assertFalse(row[0].get("string"), "the row shows only the trash icon")
        self.assertEqual(
            row[0].get("column_invisible"),
            "parent.state not in ('open', 'submitted')",
        )
        self.assertEqual(row[0].get("groups"), "collection.group_collection_user")

    def test_customer_field_is_partner_id_without_domain(self):
        """Payment Vouchers list, search, and form use unbound partner_id."""
        expected_counts = {
            "collection.view_collection_voucher_list": 1,
            "collection.view_collection_voucher_search": 1,
            "collection.view_collection_voucher_form": 1,
        }
        for xmlid, count in expected_counts.items():
            root = self._arch_root(xmlid)
            ident_nodes = self._field_nodes(root, "customer_identification")
            self.assertFalse(
                ident_nodes,
                f"{xmlid} must not declare customer_identification",
            )
            nodes = self._field_nodes(root, "partner_id")
            self.assertEqual(
                len(nodes),
                count,
                f"{xmlid} must declare partner_id {count} time(s)",
            )
            for node in nodes:
                self.assertFalse(
                    node.get("domain"),
                    (
                        f"{xmlid} partner_id must have no domain "
                        f"(got {node.get('domain')!r})"
                    ),
                )

    def test_views_have_no_received_date(self):
        """Triangulation: no voucher view arch may mention received_date."""
        for xmlid in self.VIEW_XMLIDS:
            root = self._arch_root(xmlid)
            arch = etree.tostring(root, encoding="unicode")
            self.assertNotIn(
                "received_date",
                arch,
                f"{xmlid} must not reference received_date",
            )
            self.assertFalse(
                self._field_nodes(root, "received_date"),
                f"{xmlid} must not declare received_date fields",
            )

    def test_state_group_expand_dropped(self):
        """Stages kanban group_expand on state MUST be off."""
        Voucher = self.env["collection.voucher"]
        self.assertFalse(
            Voucher._fields["state"].group_expand,
            "state must not group_expand after dropping stages kanban",
        )

    def test_partner_group_expand_dropped(self):
        """partner_id MUST NOT group_expand after dropping Reassign kanban."""
        Voucher = self.env["collection.voucher"]
        self.assertFalse(
            Voucher._fields["partner_id"].group_expand,
            "partner_id must not group_expand after dropping Reassign kanban",
        )
        self.assertFalse(
            hasattr(Voucher, "_read_group_partner_ids"),
            "_read_group_partner_ids MUST be removed with Reassign kanban",
        )
        self.assertNotEqual(
            Voucher._fields["partner_id"].group_expand,
            True,
            "Many2one group_expand MUST NOT be boolean True",
        )

    def test_form_statusbar_validate_seller_when_draft(self):
        """Form must show statusbar and Validate by Seller only when draft."""
        voucher = self.env["collection.voucher"].create(
            {
                "partner_id": dummy_customer_partner(
                    self.env, customer="UI-MENU-001"
                ).id,
                "document_type": "cash_deposit",
                "seller_id": ensure_enabled_seller(self.env).id,
                "amount": 100.0,
            }
        )
        self.assertEqual(voucher.state, "draft")

        form_root = self._arch_root("collection.view_collection_voucher_form")
        self.assertEqual(form_root.tag, "form")

        statusbar = form_root.xpath(
            '//header/field[@name="state" and @widget="statusbar"]'
        )
        self.assertTrue(statusbar, "form must include state statusbar in header")
        options = statusbar[0].get("options") or ""
        self.assertIn("clickable", options)
        self.assertIn("False", options)

        validate = form_root.xpath(
            '//header/button[@name="action_validate_seller" and @type="object"]'
        )
        self.assertTrue(validate, "form must include Validate by Seller button")
        self.assertIn(
            "state != 'draft'",
            validate[0].get("invisible", ""),
            "Validate by Seller must be invisible when not draft",
        )
        self.assertFalse(
            form_root.xpath('//header/button[@name="action_approve"]'),
            "form must not keep action_approve",
        )
        self.assertFalse(
            form_root.xpath('//header/button[@name="action_reject"]'),
            "form must not keep action_reject",
        )
        self.assertFalse(
            form_root.xpath('//header/button[@name="action_validate"]'),
            "form must not keep action_validate",
        )

        self._assert_create_date_readonly(form_root, "form")
        form_fields = self._field_names(form_root)
        self.assertIn("create_date", form_fields)
        self.assertNotIn("received_date", form_fields)

        chatter = form_root.xpath("//chatter")
        self.assertTrue(
            chatter, "form must include <chatter/> for messaging/activities"
        )

    def test_form_has_no_typed_payment_ids_tables(self):
        """Standalone form MUST NOT embed payment_ids or History snapshot lists."""
        form_root = self._arch_root("collection.view_collection_voucher_form")
        self.assertFalse(
            form_root.xpath('//field[@name="payment_ids"]'),
            "form must not declare payment_ids",
        )
        self.assertFalse(
            form_root.xpath('//field[@name="review_snapshot_ids"]'),
            "form must not declare review_snapshot_ids after dropping History",
        )
        self.assertFalse(
            form_root.xpath(".//list"),
            "form must not embed leftover history/payment <list>",
        )

    def test_form_typed_invisible_payment_fields(self):
        """Form MUST show type-specific payment fields via invisible=."""
        form_root = self._arch_root("collection.view_collection_voucher_form")
        for field_name in SHARED_PAYMENT_FIELDS:
            nodes = self._field_nodes(form_root, field_name)
            self.assertTrue(nodes, f"form must include shared field {field_name}")

        amount = self._field_nodes(form_root, "amount")[0]
        self.assertIsNone(
            amount.get("invisible"),
            "every document type owns an amount, so it is never hidden",
        )

        for field_name in BANK_TRANSFER_FIELDS:
            nodes = self._field_nodes(form_root, field_name)
            self.assertTrue(nodes, f"form must include bank field {field_name}")
            self._assert_invisible_for_document_type(
                nodes[0], "bank_transfer", field_name
            )

        for field_name in CHECK_FIELDS:
            nodes = self._field_nodes(form_root, field_name)
            self.assertTrue(nodes, f"form must include check field {field_name}")
            self._assert_invisible_for_document_type(nodes[0], "check", field_name)

        bank_only = set(BANK_TRANSFER_FIELDS)
        check_only = set(CHECK_FIELDS)
        self.assertFalse(bank_only & check_only)

    def test_form_notebook_current_raw_seller_pages(self):
        """Form MUST notebook Current, Raw OCR, and Seller Confirmed (no History)."""
        form_root = self._arch_root("collection.view_collection_voucher_form")
        notebook = form_root.xpath("//notebook")
        self.assertTrue(notebook, "form must wrap payment layers in a notebook")
        page_strings = [page.get("string") for page in notebook[0].xpath("./page")]
        self.assertEqual(
            page_strings,
            [NOTEBOOK_CURRENT, NOTEBOOK_RAW, NOTEBOOK_SELLER],
            "form notebook must keep Current / Raw OCR / Seller Confirmed only",
        )
        self.assertNotIn(
            NOTEBOOK_HISTORY,
            page_strings,
            "form notebook must not include a History page",
        )
        for expected in (NOTEBOOK_CURRENT, NOTEBOOK_RAW, NOTEBOOK_SELLER):
            self.assertIn(
                expected,
                page_strings,
                f"form notebook must include page {expected!r}",
            )
        current = self._notebook_page(form_root, NOTEBOOK_CURRENT)
        current_fields = self._field_names(current)
        self.assertIn("document_type", current_fields)
        self.assertIn("amount", current_fields)
        self.assertIn("document_id", current_fields)
        amount = current.xpath('.//field[@name="amount"]')[0]
        self.assertNotIn(
            amount.get("readonly"),
            ("1", "True", "true"),
            "Current amount must stay editable",
        )

    def test_form_provenance_pages_hide_document_id(self):
        """Raw OCR and Seller Confirmed MUST hide document_id and proof bytes."""
        form_root = self._arch_root("collection.view_collection_voucher_form")
        current = self._notebook_page(form_root, NOTEBOOK_CURRENT)
        self.assertTrue(
            current.xpath('.//field[@name="document_id"]'),
            "Current page may keep document_id as identity",
        )
        for page_string, _prefix, _type_field in PROVENANCE_LAYERS:
            page = self._notebook_page(form_root, page_string)
            names = self._field_names(page)
            self.assertNotIn(
                "document_id",
                names,
                f"{page_string} must not show document_id",
            )
            self.assertNotIn("ocr_document_id", names)
            self.assertNotIn("seller_document_id", names)
            arch = etree.tostring(page, encoding="unicode")
            self.assertNotIn("document_id", arch)
            self.assertNotIn("attachment", arch)
            self.assertNotIn("datas", arch)
            self.assertNotIn("base64", arch)

    def test_form_typed_invisible_on_all_provenance_layers(self):
        """Type-specific invisible= MUST apply to Raw OCR and Seller Confirmed."""
        form_root = self._arch_root("collection.view_collection_voucher_form")
        current = self._notebook_page(form_root, NOTEBOOK_CURRENT)
        current_amount = current.xpath('.//field[@name="amount"]')[0]
        self.assertIsNone(current_amount.get("invisible"), "amount is never hidden")
        for page_string, prefix, type_field in PROVENANCE_LAYERS:
            page = self._notebook_page(form_root, page_string)
            amount_name = f"{prefix}amount"
            amount_nodes = page.xpath(f'.//field[@name="{amount_name}"]')
            self.assertTrue(
                amount_nodes,
                f"{page_string} must include {amount_name}",
            )
            self.assertIsNone(
                amount_nodes[0].get("invisible"),
                f"{amount_name} is owned by every type, so it is never hidden",
            )
            self._assert_readonly_field(amount_nodes[0], amount_name)
            for field_name in BANK_TRANSFER_FIELDS:
                layered = f"{prefix}{field_name}"
                nodes = page.xpath(f'.//field[@name="{layered}"]')
                self.assertTrue(nodes, f"{page_string} must include {layered}")
                invisible = nodes[0].get("invisible") or ""
                self.assertIn(
                    type_field,
                    invisible,
                    f"{layered} invisible= must use {type_field}",
                )
                self.assertIn(
                    " and document_type !=",
                    invisible,
                    f"{layered} must stay visible when Current is bank_transfer",
                )
                self._assert_invisible_for_document_type(
                    nodes[0], "bank_transfer", layered
                )
                self._assert_readonly_field(nodes[0], layered)
            for field_name in CHECK_FIELDS:
                layered = f"{prefix}{field_name}"
                nodes = page.xpath(f'.//field[@name="{layered}"]')
                self.assertTrue(nodes, f"{page_string} must include {layered}")
                invisible = nodes[0].get("invisible") or ""
                self.assertIn(
                    type_field,
                    invisible,
                    f"{layered} invisible= must use {type_field}",
                )
                self.assertIn(
                    " and document_type !=",
                    invisible,
                    f"{layered} must stay visible when Current is check",
                )
                self._assert_invisible_for_document_type(nodes[0], "check", layered)
                self._assert_readonly_field(nodes[0], layered)

    def test_form_cash_deposit_keys_present_on_all_layers(self):
        """voucher_number/voucher_date MUST exist on all layers; UI MAY hide them."""
        form_root = self._arch_root("collection.view_collection_voucher_form")
        current = self._notebook_page(form_root, NOTEBOOK_CURRENT)
        for field_name in CASH_DEPOSIT_KEYS:
            nodes = current.xpath(f'.//field[@name="{field_name}"]')
            self.assertTrue(
                nodes,
                f"Current page must declare stored {field_name}",
            )
            self._assert_invisible_for_document_type(
                nodes[0], "bank_transfer", field_name
            )
        for page_string, prefix, type_field in PROVENANCE_LAYERS:
            page = self._notebook_page(form_root, page_string)
            for field_name in CASH_DEPOSIT_KEYS:
                layered = f"{prefix}{field_name}"
                nodes = page.xpath(f'.//field[@name="{layered}"]')
                self.assertTrue(
                    nodes,
                    f"{page_string} must declare stored {layered}",
                )
                invisible = nodes[0].get("invisible") or ""
                self.assertIn(
                    type_field,
                    invisible,
                    f"{layered} invisible= must use {type_field}",
                )
                self.assertIn(
                    " and document_type !=",
                    invisible,
                    f"{layered} must stay visible when Current is bank_transfer",
                )
                self._assert_invisible_for_document_type(
                    nodes[0], "bank_transfer", layered
                )

    def test_form_seller_deposit_number_and_date_visible(self):
        """voucher_number and voucher_date MUST be visible for seller_deposit."""
        form_root = self._arch_root("collection.view_collection_voucher_form")
        current = self._notebook_page(form_root, NOTEBOOK_CURRENT)
        for field_name in CASH_DEPOSIT_KEYS:
            nodes = current.xpath(f'.//field[@name="{field_name}"]')
            self.assertTrue(
                nodes,
                f"Current page must declare stored {field_name}",
            )
            self._assert_invisible_for_document_type(
                nodes[0], "seller_deposit", field_name
            )
        for page_string, prefix, type_field in PROVENANCE_LAYERS:
            page = self._notebook_page(form_root, page_string)
            for field_name in CASH_DEPOSIT_KEYS:
                layered = f"{prefix}{field_name}"
                nodes = page.xpath(f'.//field[@name="{layered}"]')
                self.assertTrue(
                    nodes,
                    f"{page_string} must declare stored {layered}",
                )
                invisible = nodes[0].get("invisible") or ""
                self.assertIn(
                    type_field,
                    invisible,
                    f"{layered} invisible= must use {type_field}",
                )
                self._assert_invisible_for_document_type(
                    nodes[0], "seller_deposit", layered
                )

    def test_form_has_no_history_page(self):
        """History page and review_snapshot_ids MUST be gone from the form."""
        form_root = self._arch_root("collection.view_collection_voucher_form")
        self.assertFalse(
            form_root.xpath(f'//notebook/page[@string="{NOTEBOOK_HISTORY}"]'),
            "form must not include a History notebook page",
        )
        self.assertFalse(
            form_root.xpath('//field[@name="review_snapshot_ids"]'),
            "form must not declare review_snapshot_ids",
        )
        chatter = form_root.xpath("//chatter")
        self.assertTrue(
            chatter,
            "form must keep chatter after dropping History",
        )

    def test_payment_vouchers_views_omit_binary_widgets(self):
        """Form and list MUST omit Binary widgets; form chatter remains."""
        for xmlid, label in (
            ("collection.view_collection_voucher_form", "form"),
            ("collection.view_collection_voucher_list", "list"),
        ):
            root = self._arch_root(xmlid)
            self._assert_no_attachment_binary_widgets(root, label)
        form_root = self._arch_root("collection.view_collection_voucher_form")
        self._assert_form_chatter_open_attachments(form_root)
        self._assert_form_attachment_preview(form_root)

    def test_form_shows_large_attachment_preview(self):
        """Form MUST use the side-panel previewer used on vendor bills."""
        form_root = self._arch_root("collection.view_collection_voucher_form")
        self._assert_form_attachment_preview(form_root)
        self._assert_form_chatter_open_attachments(form_root)

    def test_create_and_edit_enabled_on_payment_vouchers(self):
        """Payment Vouchers list/form and action MUST allow create and edit."""
        action = self.env.ref("collection.action_collection_voucher")
        context = action.context or {}
        if isinstance(context, str):
            context_repr = context.replace('"', "'")
            self.assertNotIn("'create': False", context_repr)
            self.assertNotIn("'edit': False", context_repr)
        else:
            self.assertIsNot(context.get("create"), False)
            self.assertIsNot(context.get("edit"), False)

        for xmlid, label in (
            ("collection.view_collection_voucher_list", "list"),
            ("collection.view_collection_voucher_form", "form"),
        ):
            self._assert_create_edit_enabled(self._arch_root(xmlid), label)

    def test_no_view_mentions_unsupported(self):
        """The removed ``unsupported`` kind MUST leave no filter or invisible=."""
        for xmlid in (
            "collection.view_collection_voucher_search",
            "collection.view_collection_voucher_form",
            "collection.view_collection_voucher_list",
        ):
            arch = self.env.ref(xmlid).arch
            self.assertNotIn("unsupported", arch, f"{xmlid} still mentions it")

    def test_ui_create_may_omit_document_id(self):
        """UI-style create may omit document_id on a standalone voucher."""
        voucher = self.env["collection.voucher"].create(
            {
                "partner_id": dummy_customer_partner(
                    self.env, customer="UI-TYPED-DEFAULT-002"
                ).id,
                "document_type": "cash_deposit",
                "seller_id": ensure_enabled_seller(self.env).id,
                "amount": 100.0,
            }
        )
        self.assertEqual(voucher.document_type, "cash_deposit")
        self.assertFalse(voucher.document_id)

    def test_form_seller_id_is_required(self):
        """Payment Vouchers form MUST require seller_id (field stays nullable)."""
        form_root = self._arch_root("collection.view_collection_voucher_form")
        nodes = self._field_nodes(form_root, "seller_id")
        self.assertTrue(nodes, "form must include seller_id")
        required = nodes[0].get("required")
        self.assertIn(
            required,
            ("1", "True", "true"),
            f"form seller_id must be required (got {required!r})",
        )

    def _assert_enabled_seller_domain(self, node, context):
        domain = node.get("domain") or ""
        self.assertIn(
            "enabled_seller_ids",
            domain,
            f"{context} seller_id domain must use company enabled "
            f"sellers (got {domain!r})",
        )
        self.assertIn(
            "company_id",
            domain,
            f"{context} seller_id domain must be scoped to company_id (got {domain!r})",
        )

    def test_voucher_form_seller_domain_is_company_enabled_list(self):
        form_root = self._arch_root("collection.view_collection_voucher_form")
        seller = self._field_nodes(form_root, "seller_id")[0]
        self._assert_enabled_seller_domain(seller, "voucher form")

    def test_voucher_list_seller_domain_is_company_enabled_list(self):
        """Triangulation: list seller_id uses the same enabled-seller domain."""
        list_root = self._arch_root("collection.view_collection_voucher_list")
        self.assertEqual(list_root.tag, "list")
        seller = self._field_nodes(list_root, "seller_id")[0]
        self._assert_enabled_seller_domain(seller, "voucher list")

    def test_sheet_form_seller_domain_is_company_enabled_list(self):
        form_root = self._arch_root("collection.view_collection_sheet_form")
        seller = self._field_nodes(form_root, "seller_id")[0]
        self._assert_enabled_seller_domain(seller, "sheet form")

    def test_voucher_views_keep_list_tag(self):
        list_root = self._arch_root("collection.view_collection_voucher_list")
        self.assertEqual(list_root.tag, "list")
        self.assertNotEqual(list_root.tag, "tree")

    def test_list_form_search_expose_seller_id(self):
        """Triangulation: list, form, and search MUST show seller_id."""
        for xmlid, label in (
            ("collection.view_collection_voucher_list", "list"),
            ("collection.view_collection_voucher_form", "form"),
            ("collection.view_collection_voucher_search", "search"),
        ):
            root = self._arch_root(xmlid)
            names = self._field_names(root)
            self.assertIn("seller_id", names, f"{label} view must expose seller_id")

    def test_voucher_list_form_search_expose_sheet_id(self):
        """List visible sheet_id, form editable after seller_id, search+groupby."""
        list_root = self._arch_root("collection.view_collection_voucher_list")
        list_nodes = self._field_nodes(list_root, "sheet_id")
        self.assertEqual(len(list_nodes), 1, "voucher list must declare sheet_id once")
        self.assertNotEqual(
            list_nodes[0].get("optional"),
            "hide",
            "voucher list sheet_id must be visible, not optional=hide",
        )
        self.assertEqual(
            self._list_visible_field_names(list_root)[2],
            "sheet_id",
            "visible list column 3 must be sheet_id",
        )

        form_root = self._arch_root("collection.view_collection_voucher_form")
        form_nodes = self._field_nodes(form_root, "sheet_id")
        self.assertEqual(len(form_nodes), 1, "voucher form must declare sheet_id once")
        self.assertFalse(
            form_nodes[0].get("readonly"),
            (
                "form sheet_id must be editable with no extra readonly "
                f"(got {form_nodes[0].get('readonly')!r})"
            ),
        )
        left_group = form_root.xpath("./sheet/group/group")[0]
        seller = left_group.xpath('./field[@name="seller_id"]')
        self.assertTrue(seller, "voucher form left group must include seller_id")
        following = seller[0].xpath("./following-sibling::field")
        self.assertTrue(
            following,
            "voucher form must declare a field after seller_id",
        )
        self.assertEqual(
            following[0].get("name"),
            "sheet_id",
            "form sheet_id must follow seller_id in the left group",
        )

        search_root = self._arch_root("collection.view_collection_voucher_search")
        self.assertIn("sheet_id", self._field_names(search_root))
        group_sheet = [
            node
            for node in search_root.xpath("//group/filter")
            if "group_by" in (node.get("context") or "")
            and "sheet_id" in (node.get("context") or "")
        ]
        self.assertTrue(group_sheet, "search view must offer group_by sheet_id")

    def test_collection_sheets_menu_list_form_search(self):
        """Collections → Collection Sheets MUST wire list, form, and search."""
        root_menu = self.env.ref("collection.menu_collection_root")
        sheet_menu = self.env.ref("collection.menu_collection_sheet")
        action = self.env.ref("collection.action_collection_sheet")
        create_action = self.env.ref("collection.action_create_collection_sheet")

        self.assertEqual(sheet_menu.name, "Collection Sheets")
        self.assertEqual(sheet_menu.parent_id, root_menu)
        self.assertEqual(sheet_menu.action, action)
        self.assertEqual(action.res_model, "collection.sheet")
        self.assertIn("list", action.view_mode)
        self.assertIn("form", action.view_mode)
        self.assertEqual(
            action.search_view_id,
            self.env.ref("collection.view_collection_sheet_search"),
        )
        self.assertEqual(create_action.type, "ir.actions.server")
        self.assertEqual(create_action.binding_view_types, "list")

        list_root = self._arch_root("collection.view_collection_sheet_list")
        search_root = self._arch_root("collection.view_collection_sheet_search")
        self.assertEqual(list_root.tag, "list")
        self.assertNotEqual(list_root.tag, "tree")
        self.assertEqual(search_root.tag, "search")
        list_fields = self._field_names(list_root)
        search_fields = self._field_names(search_root)
        for field_name in ("name", "seller_id", "date_from", "date_to", "state"):
            self.assertIn(field_name, list_fields, f"list must show {field_name}")
            self.assertIn(field_name, search_fields, f"search must show {field_name}")
        self._assert_create_edit_enabled(list_root, "sheet list")

    def test_collection_sheets_form_statusbar_five_states(self):
        """Sheet form: five-state statusbar and header actions by state; no Reopen."""
        form_root = self._arch_root("collection.view_collection_sheet_form")
        self.assertEqual(form_root.tag, "form")
        self._assert_create_edit_enabled(form_root, "sheet form")
        names = self._field_names(form_root)
        for field_name in ("name", "seller_id", "date_from", "date_to"):
            self.assertIn(field_name, names, f"form must show {field_name}")

        seller = self._field_nodes(form_root, "seller_id")[0]
        self.assertIn(
            seller.get("required"),
            ("1", "True", "true"),
            f"form seller_id must be required (got {seller.get('required')!r})",
        )
        readonly = seller.get("readonly") or ""
        self.assertIn("id", readonly, "seller_id must be readonly after create")
        self.assertNotIn(
            readonly.lower(),
            ("1", "true"),
            "seller_id must stay editable on create",
        )
        statusbar = form_root.xpath(
            '//header/field[@name="state" and @widget="statusbar"]'
        )
        self.assertTrue(statusbar, "sheet form must include state statusbar in header")
        self.assertEqual(
            statusbar[0].get("statusbar_visible"),
            "open,submitted,proposal,closed,cancelled",
        )
        options = statusbar[0].get("options") or ""
        self.assertIn("clickable", options)
        self.assertIn("False", options)

        def _header_button(name):
            return form_root.xpath(
                f'./header/button[@name="{name}" and @type="object"]'
            )

        seller_close = _header_button("action_seller_close")
        confirm = _header_button("action_confirm")
        close = _header_button("action_close")
        cancel = _header_button("action_cancel")
        reinstate = _header_button("action_reinstate")
        review = _header_button("action_open_document_review")
        xlsx = _header_button("action_print_xlsx")
        self.assertTrue(seller_close, "form must include Seller Close button")
        self.assertEqual(
            seller_close[0].getnext().get("name"),
            "action_confirm",
            "Seller Close must sit immediately before Confirm",
        )
        seller_close_invisible = seller_close[0].get("invisible", "")
        self.assertIn("open", seller_close_invisible)
        self.assertIn("not id", seller_close_invisible)
        self.assertTrue(confirm, "form must include Confirm button")
        self.assertTrue(close, "form must include Close button")
        self.assertTrue(cancel, "form must include Cancel button")
        self.assertTrue(reinstate, "form must include Reinstate button")
        self.assertTrue(review, "Document Review header button must remain")
        self.assertTrue(xlsx, "Collection Sheet XLSX must remain on the sheet form")
        self.assertFalse(
            _header_button("action_reopen"),
            "Reopen MUST NOT appear on the sheet form",
        )
        self.assertFalse(
            _header_button("action_open"),
            "Open MUST NOT appear on the sheet form",
        )
        # action_confirm accepts submitted sheets only; showing it on an open
        # sheet offers a button that always fails.
        self.assertEqual(
            confirm[0].get("invisible"),
            "not id or state != 'submitted'",
        )
        declare = _header_button("action_declare_cash")
        self.assertTrue(declare, "form must include Declare Cash button")
        self.assertEqual(declare[0].get("string"), "Declare Cash")
        self.assertEqual(
            declare[0].get("invisible"),
            "not id or state != 'submitted'",
        )
        self.assertEqual(
            confirm[0].getnext(),
            declare[0],
            "Declare Cash must sit immediately after Confirm",
        )
        self.assertIn(
            "state != 'proposal'",
            close[0].get("invisible", ""),
            "Close must be invisible when not proposal",
        )
        cancel_invisible = cancel[0].get("invisible", "")
        self.assertIn("submitted", cancel_invisible)
        self.assertIn("proposal", cancel_invisible)
        self.assertIn("closed", cancel_invisible)
        self.assertIn(
            "state != 'cancelled'",
            reinstate[0].get("invisible", ""),
            "Reinstate must be invisible when not cancelled",
        )
        review_invisible = review[0].get("invisible", "")
        self.assertIn("not in", review_invisible)
        self.assertIn("open", review_invisible)
        self.assertIn("submitted", review_invisible)
        self.assertIn("document_review_enabled", review_invisible)
        header_buttons = [
            node for node in form_root.xpath("./header/*") if node.tag == "button"
        ]
        # One primary action per state: Seller Close on open, Confirm on
        # submitted, Close on proposal.
        highlighted = [
            node.get("name")
            for node in header_buttons
            if "oe_highlight" in (node.get("class") or "")
        ]
        self.assertEqual(
            highlighted, ["action_seller_close", "action_confirm", "action_close"]
        )
        self.assertTrue(
            cancel[0].get("confirm"), "Cancel must ask before it undoes the sheet"
        )
        unmark = _header_button("action_unmark_erp_entered")
        self.assertTrue(unmark and unmark[0].get("confirm"))
        self.assertEqual(header_buttons[-1].get("name"), "action_print_xlsx")
        self.assertEqual(header_buttons[-1].get("invisible"), "not id")
        self.assertEqual(
            header_buttons[-1].get("groups"), "collection.group_collection_user"
        )
        self.assertEqual(header_buttons[-1].getnext().get("name"), "state")
        percent = form_root.xpath('.//field[@name="commission_percent"]')
        cash = form_root.xpath('.//field[@name="cash_on_hand"]')
        withheld = form_root.xpath('.//field[@name="commission_withheld"]')
        self.assertTrue(percent and cash and withheld, "form must show recon inputs")
        self.assertIn("closed", percent[0].get("readonly") or "")
        self.assertIn("cancelled", percent[0].get("readonly") or "")
        self.assertEqual(cash[0].get("readonly"), "1")
        self.assertIn("submitted", withheld[0].get("readonly") or "")
        self.assertNotIn("open", withheld[0].get("readonly") or "")
        collected = form_root.xpath('.//field[@name="cash_collected"]')
        banked = form_root.xpath('.//field[@name="cash_banked"]')
        self.assertTrue(collected and banked, "form must show the cash_on_hand terms")
        self.assertNotIn(
            "received_date",
            etree.tostring(form_root, encoding="unicode"),
        )
        chatter = form_root.xpath("//chatter")
        self.assertTrue(
            chatter, "sheet form must include <chatter/> for messaging/activities"
        )

    def test_collection_allocations_menu_list_form_search(self):
        """Collections → Collection Allocations MUST wire list, form, and search."""
        root_menu = self.env.ref("collection.menu_collection_root")
        sheet_menu = self.env.ref("collection.menu_collection_sheet")
        alloc_menu = self.env.ref("collection.menu_collection_allocation")
        action = self.env.ref("collection.action_collection_allocation")

        self.assertEqual(alloc_menu.name, "Collection Allocations")
        self.assertEqual(alloc_menu.parent_id, root_menu)
        self.assertEqual(alloc_menu.action, action)
        self.assertEqual(alloc_menu.sequence, 30)
        self.assertEqual(sheet_menu.sequence, 20)
        self.assertGreater(
            alloc_menu.sequence,
            sheet_menu.sequence,
            "Allocations menu must come after Collection Sheets",
        )
        self.assertEqual(action.res_model, "collection.allocation")
        self.assertEqual(action.type, "ir.actions.act_window")
        self.assertIn("list", action.view_mode)
        self.assertIn("form", action.view_mode)
        self.assertEqual(
            action.search_view_id,
            self.env.ref("collection.view_collection_allocation_search"),
        )
        self.assertTrue(action.path, "allocation act_window must set path (Odoo 19)")
        self.assertEqual(action.path, "collection-allocations")

        list_root = self._arch_root("collection.view_collection_allocation_list")
        search_root = self._arch_root("collection.view_collection_allocation_search")
        self.assertEqual(list_root.tag, "list")
        self.assertNotEqual(list_root.tag, "tree")
        self.assertEqual(search_root.tag, "search")
        self.assertFalse(
            list_root.xpath("//tree"),
            "allocation list arch must not use deprecated <tree>",
        )
        list_fields = self._field_names(list_root)
        search_fields = self._field_names(search_root)
        for field_name in ("name", "partner_id", "sheet_id", "seller_id", "state"):
            self.assertIn(field_name, list_fields, f"list must show {field_name}")
            self.assertIn(field_name, search_fields, f"search must show {field_name}")
        self._assert_create_edit_enabled(list_root, "allocation list")
        for node in self._field_nodes(list_root, "partner_id"):
            self.assertFalse(
                node.get("domain"),
                (
                    "allocation list partner_id must have no domain "
                    f"(got {node.get('domain')!r})"
                ),
            )

    def test_collection_allocations_form_statusbar_no_validate_reject(self):
        """Allocation form: list not tree; freeze when confirmed; no Validate/Reject."""
        form_root = self._arch_root("collection.view_collection_allocation_form")
        self.assertEqual(form_root.tag, "form")
        self._assert_create_edit_enabled(form_root, "allocation form")
        names = self._field_names(form_root)
        for field_name in (
            "name",
            "partner_id",
            "sheet_id",
            "seller_id",
            "voucher_ids",
            "line_ids",
        ):
            self.assertIn(field_name, names, f"form must show {field_name}")
        self.assertNotIn("reviewed_by", names)
        self.assertNotIn("reviewed_at", names)
        self.assertFalse(
            form_root.xpath("//tree"),
            "allocation form arch must not use deprecated <tree>",
        )
        nested_lists = form_root.xpath(".//list")
        self.assertTrue(nested_lists, "allocation form must embed at least one <list>")
        for list_node in nested_lists:
            self.assertEqual(list_node.tag, "list")
            self.assertNotEqual(list_node.tag, "tree")

        partner = self._field_nodes(form_root, "partner_id")[0]
        self.assertFalse(
            partner.get("domain"),
            "allocation form partner_id must have no domain",
        )
        partner_readonly = partner.get("readonly") or ""
        self.assertIn(
            "sheet_id.state",
            partner_readonly,
            "allocation form partner_id must freeze from sheet_id.state",
        )
        self.assertIn("closed", partner_readonly)
        self.assertIn("cancelled", partner_readonly)
        sheet = self._field_nodes(form_root, "sheet_id")[0]
        sheet_readonly = sheet.get("readonly") or ""
        self.assertIn("sheet_id.state", sheet_readonly)
        self.assertIn("closed", sheet_readonly)
        self.assertIn("cancelled", sheet_readonly)
        line_fields = [
            node
            for node in self._field_nodes(form_root, "line_ids")
            if node.getparent() is not None
        ]
        self.assertTrue(line_fields, "allocation form must expose line_ids")
        line_readonly = line_fields[0].get("readonly") or ""
        self.assertIn("sheet_id.state", line_readonly)
        self.assertIn("closed", line_readonly)
        self.assertIn("cancelled", line_readonly)
        statusbar = form_root.xpath(
            '//header/field[@name="state" and @widget="statusbar"]'
        )
        self.assertTrue(
            statusbar, "allocation form must include state statusbar in header"
        )
        self.assertEqual(statusbar[0].get("statusbar_visible"), "draft,confirmed")
        self.assertFalse(
            form_root.xpath('//header/button[@name="action_validate"]'),
            "form must not keep action_validate",
        )
        self.assertFalse(
            form_root.xpath('//header/button[@name="action_reject"]'),
            "form must not keep action_reject",
        )
        self.assertFalse(
            form_root.xpath('//notebook/page[@string="Revisions"]'),
            "form must not keep the dropped Revisions page",
        )
        chatter = form_root.xpath("//chatter")
        self.assertTrue(
            chatter,
            "allocation form must include <chatter/> for messaging/activities",
        )

        search_root = self._arch_root("collection.view_collection_allocation_search")
        filter_names = [node.get("name") for node in search_root.xpath(".//filter")]
        self.assertIn("filter_draft", filter_names)
        self.assertIn("filter_confirmed", filter_names)
        self.assertNotIn("filter_validated", filter_names)
        self.assertNotIn("filter_rejected", filter_names)

    def test_allocation_form_vouchers_existing_only_many2many(self):
        """Vouchers tab MUST be existing-only many2many with document_type."""
        form_root = self._arch_root("collection.view_collection_allocation_form")
        voucher_fields = form_root.xpath('//notebook//field[@name="voucher_ids"]')
        self.assertEqual(
            len(voucher_fields),
            1,
            "allocation form must expose voucher_ids once in the notebook",
        )
        voucher_field = voucher_fields[0]
        self.assertEqual(voucher_field.get("widget"), "many2many")
        options = self._parse_view_options(voucher_field.get("options"))
        self.assertTrue(options.get("no_create"), "voucher_ids must set no_create")
        self.assertTrue(
            options.get("no_create_edit"),
            "voucher_ids must set no_create_edit",
        )
        voucher_readonly = voucher_field.get("readonly") or ""
        self.assertIn(
            "sheet_id.state",
            voucher_readonly,
            "allocation voucher M2M must freeze from sheet_id.state",
        )
        self.assertIn("not in", voucher_readonly)
        self.assertIn("open", voucher_readonly)
        self.assertIn("submitted", voucher_readonly)
        self.assertNotIn(
            "confirmed",
            voucher_readonly,
            "allocation voucher M2M must be Open-only, not confirmed-state",
        )
        domain = voucher_field.get("domain") or ""
        self.assertIn("partner_id", domain)
        self.assertIn("sheet_id", domain)
        self.assertIn("allocation_id", domain)
        self.assertIn("False", domain)
        lists = voucher_field.xpath("./list")
        self.assertTrue(lists, "voucher_ids must embed a <list>")
        list_names = self._field_names(lists[0], xpath="./field")
        self.assertIn("document_type", list_names)
        self.assertIn("name", list_names)
        self.assertIn("amount", list_names)

    def test_allocation_form_customer_debt_helpers_no_residual_reason(self):
        """Notebook MUST be Customer Debt; six totals have help; no Residual Reason."""
        form_root = self._arch_root("collection.view_collection_allocation_form")
        notebooks = form_root.xpath("//notebook")
        self.assertTrue(notebooks, "allocation form must include a notebook")
        page_strings = [page.get("string") for page in notebooks[0].xpath("./page")]
        self.assertIn(ALLOCATION_NOTEBOOK_CUSTOMER_DEBT, page_strings)
        self.assertNotIn(
            "Invoices",
            page_strings,
            "allocation form must rename Invoices to Customer Debt",
        )
        self._notebook_page(form_root, ALLOCATION_NOTEBOOK_CUSTOMER_DEBT)
        arch_text = etree.tostring(form_root, encoding="unicode")
        self.assertNotIn("residual_reason", arch_text)
        self.assertNotIn("Residual Reason", arch_text)
        names = self._field_names(form_root)
        self.assertNotIn("residual_reason", names)
        for field_name in ALLOCATION_TOTAL_FIELDS:
            nodes = [
                node
                for node in self._field_nodes(form_root, field_name)
                if node.getparent() is not None
                and "notebook" not in node.getparent().tag
            ]
            if not nodes:
                nodes = self._field_nodes(form_root, field_name)
            self.assertTrue(nodes, f"allocation form must show {field_name}")
            self.assertTrue(
                (nodes[0].get("help") or "").strip(),
                f"{field_name} must have a help tooltip",
            )

    def test_allocation_form_customer_debt_add_debt_picker(self):
        """Customer Debt MUST disable inline create and expose Add Debt."""
        form_root = self._arch_root("collection.view_collection_allocation_form")
        page = self._notebook_page(form_root, ALLOCATION_NOTEBOOK_CUSTOMER_DEBT)
        buttons = page.xpath(
            './button[@name="action_open_debt_picker" and @type="object"]'
        )
        self.assertEqual(len(buttons), 1, "Customer Debt must expose Add Debt once")
        self.assertEqual(buttons[0].get("string"), "Add Debt")
        invisible = buttons[0].get("invisible") or ""
        self.assertIn("not id", invisible)
        self.assertIn("closed", invisible)
        self.assertIn("cancelled", invisible)
        line_fields = page.xpath('./field[@name="line_ids"]')
        self.assertEqual(len(line_fields), 1)
        lists = line_fields[0].xpath("./list")
        self.assertTrue(lists, "line_ids must embed a <list>")
        self.assertTrue(
            self._attr_is_false(lists[0].get("create")),
            "Customer Debt list must disable arbitrary inline create",
        )
        readonly_identity = (
            "document_kind",
            "invoice_number",
            "external_invoice_id",
            "due_date",
            "invoice_balance",
        )
        for field_name in readonly_identity:
            nodes = [
                node
                for node in lists[0].xpath("./field")
                if node.get("name") == field_name
            ]
            self.assertTrue(nodes, f"Customer Debt list must show {field_name}")
            self._assert_readonly_field(nodes[0], field_name)
        applied = [
            node
            for node in lists[0].xpath("./field")
            if node.get("name") == "amount_applied"
        ]
        self.assertTrue(applied, "Customer Debt list must show amount_applied")
        self.assertNotIn(
            (applied[0].get("readonly") or "").lower(),
            ("1", "true"),
            "amount_applied must remain editable",
        )
        picker_form = self._arch_root(
            "collection.view_collection_allocation_debt_picker_form"
        )
        selected = picker_form.xpath('//field[@name="selected_ids"]')
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].get("widget"), "many2many")
        options = self._parse_view_options(selected[0].get("options"))
        self.assertTrue(
            options.get("no_create"),
            "picker selected_ids must set no_create",
        )
        self.assertTrue(
            options.get("no_create_edit"),
            "picker selected_ids must set no_create_edit",
        )
        candidate_list = self._arch_root(
            "collection.view_collection_allocation_debt_candidate_list"
        )
        self.assertTrue(
            self._attr_is_false(candidate_list.get("create")),
            "candidate list must disable create",
        )

    def test_allocation_form_stat_button_opens_vouchers(self):
        """Allocation form MUST copy the sheet Vouchers smart-button box."""
        form_root = self._arch_root("collection.view_collection_allocation_form")
        sheet_nodes = form_root.xpath("./sheet")
        self.assertTrue(sheet_nodes, "allocation form must include a <sheet>")
        first_child = sheet_nodes[0][0]
        self.assertEqual(
            first_child.tag,
            "div",
            "first child inside <sheet> must be the smart-button box",
        )
        self.assertEqual(first_child.get("class"), "oe_button_box")
        self.assertEqual(first_child.get("name"), "button_box")
        buttons = first_child.xpath(
            './button[@name="action_open_vouchers" and @type="object"]'
        )
        self.assertEqual(
            len(buttons),
            1,
            "button box must expose action_open_vouchers once",
        )
        button = buttons[0]
        self.assertIn("oe_stat_button", (button.get("class") or "").split())
        self.assertEqual(button.get("invisible"), "not id")
        count_fields = button.xpath('.//field[@name="voucher_count"]')
        self.assertTrue(count_fields, "stat button must show voucher_count")
        self.assertEqual(count_fields[0].get("widget"), "statinfo")
        self.assertEqual(count_fields[0].get("string"), "Vouchers")

    def test_sheet_form_notebook_three_pages_allocations_columns(self):
        """Sheet form MUST notebook Allocations, Vouchers, Debt with new columns."""
        form_root = self._arch_root("collection.view_collection_sheet_form")
        notebooks = form_root.xpath("//notebook")
        self.assertTrue(notebooks, "sheet form must wrap pages in a notebook")
        self.assertEqual(
            len(notebooks),
            1,
            "sheet form must have a single notebook",
        )
        page_strings = [page.get("string") for page in notebooks[0].xpath("./page")]
        self.assertEqual(
            page_strings,
            [
                SHEET_NOTEBOOK_ALLOCATIONS,
                SHEET_NOTEBOOK_VOUCHERS,
                SHEET_NOTEBOOK_DEBT,
            ],
            "sheet form notebook must show Allocations, Vouchers, and Debt",
        )
        for page_string in page_strings:
            page = self._notebook_page(form_root, page_string)
            self.assertFalse(
                page.get("invisible"),
                f"{page_string} notebook page must not be hidden",
            )

        allocations_page = self._notebook_page(form_root, SHEET_NOTEBOOK_ALLOCATIONS)
        allocation_fields = allocations_page.xpath('.//field[@name="allocation_ids"]')
        self.assertTrue(
            allocation_fields,
            "Allocations notebook page must contain allocation_ids",
        )
        allocation_field = allocation_fields[0]
        allocation_readonly = allocation_field.get("readonly") or ""
        self.assertIn("open", allocation_readonly)
        self.assertIn("submitted", allocation_readonly)
        self.assertIn("proposal", allocation_readonly)
        allocation_lists = allocation_field.xpath("./list")
        self.assertTrue(allocation_lists, "allocation_ids must embed a <list>")
        list_node = allocation_lists[0]
        self.assertEqual(list_node.tag, "list")
        self.assertNotEqual(list_node.tag, "tree")
        self.assertFalse(
            self._attr_is_false(list_node.get("create")),
            "allocations list must stay addable when the sheet is open or proposal",
        )
        self.assertFalse(
            self._attr_is_false(list_node.get("delete")),
            "allocations list must stay deletable when the sheet is open or proposal",
        )
        visible = self._list_visible_field_names(list_node)
        self.assertEqual(
            visible,
            list(SHEET_ALLOCATION_COLUMNS),
            "allocations must show Reference, Customer, Total Debt, "
            "Total Vouchers Applied, Residual",
        )
        self.assertNotIn("state", visible)
        self.assertNotIn("total_applied", visible)
        by_name = {
            node.get("name"): node
            for node in list_node.xpath("./field")
            if node.get("name")
        }
        for field_name, expected_string in SHEET_ALLOCATION_COLUMN_STRINGS.items():
            self.assertEqual(
                by_name[field_name].get("string"),
                expected_string,
                f"{field_name} column must be labeled {expected_string!r}",
            )
        form_names = self._field_names(form_root)
        self.assertIn("allocation_ids", form_names)
        self.assertIn("voucher_ids", form_names)
        self.assertIn("debt_line_ids", form_names)
        self.assertFalse(
            form_root.xpath("//tree"),
            "sheet form must not use deprecated <tree>",
        )

    def test_sheet_form_vouchers_tab_existing_only_in_open(self):
        """Vouchers tab MUST list voucher_ids without create/remove; Open-only edit."""
        form_root = self._arch_root("collection.view_collection_sheet_form")
        vouchers_page = self._notebook_page(form_root, SHEET_NOTEBOOK_VOUCHERS)
        voucher_fields = vouchers_page.xpath('.//field[@name="voucher_ids"]')
        self.assertEqual(
            len(voucher_fields),
            1,
            "Vouchers page must expose voucher_ids once",
        )
        voucher_field = voucher_fields[0]
        self.assertTrue(
            self._attr_is_false(voucher_field.get("create")),
            "Vouchers tab must not create from the sheet",
        )
        self.assertTrue(
            self._attr_is_false(voucher_field.get("delete")),
            "Vouchers tab must not delete from the sheet",
        )
        lists = voucher_field.xpath("./list")
        self.assertTrue(lists, "voucher_ids must embed a <list>")
        self.assertEqual(lists[0].tag, "list")
        self.assertTrue(
            self._attr_is_false(lists[0].get("create")),
            "Vouchers list must disable create",
        )
        self.assertTrue(
            self._attr_is_false(lists[0].get("delete")),
            "Vouchers list must disable delete",
        )
        readonly = voucher_field.get("readonly") or ""
        self.assertIn("state", readonly)
        self.assertIn("open", readonly)
        self.assertIn("submitted", readonly)
        self.assertIn("not in", readonly)

    def test_sheet_form_debt_tab_amount_applied_only(self):
        """Debt tab MUST list lines; only amount_applied editable in Open/Proposal."""
        form_root = self._arch_root("collection.view_collection_sheet_form")
        debt_page = self._notebook_page(form_root, SHEET_NOTEBOOK_DEBT)
        debt_fields = debt_page.xpath('.//field[@name="debt_line_ids"]')
        self.assertEqual(
            len(debt_fields),
            1,
            "Debt page must expose debt_line_ids once",
        )
        debt_field = debt_fields[0]
        self.assertTrue(
            self._attr_is_false(debt_field.get("create")),
            "Debt tab must disable create",
        )
        self.assertTrue(
            self._attr_is_false(debt_field.get("delete")),
            "Debt tab must disable delete",
        )
        lists = debt_field.xpath("./list")
        self.assertTrue(lists, "debt_line_ids must embed a <list>")
        list_node = lists[0]
        self.assertEqual(list_node.tag, "list")
        self.assertTrue(
            self._attr_is_false(list_node.get("create")),
            "Debt list must disable create",
        )
        self.assertTrue(
            self._attr_is_false(list_node.get("delete")),
            "Debt list must disable delete",
        )
        applied = [
            node
            for node in list_node.xpath("./field")
            if node.get("name") == "amount_applied"
        ]
        self.assertTrue(applied, "Debt list must include amount_applied")
        applied_readonly = applied[0].get("readonly") or ""
        self.assertIn("open", applied_readonly)
        self.assertIn("submitted", applied_readonly)
        self.assertIn("proposal", applied_readonly)
        for node in list_node.xpath("./field"):
            name = node.get("name")
            if name == "amount_applied":
                continue
            if (node.get("column_invisible") or "").lower() in ("1", "true"):
                continue
            readonly = (node.get("readonly") or "").lower()
            self.assertIn(
                readonly,
                ("1", "true"),
                f"Debt column {name} must be readonly (got {node.get('readonly')!r})",
            )

    def test_sheet_form_stat_button_opens_vouchers(self):
        """Sheet form MUST expose a counted Vouchers stat button hidden when unsaved."""
        form_root = self._arch_root("collection.view_collection_sheet_form")
        sheet_nodes = form_root.xpath("./sheet")
        self.assertTrue(sheet_nodes, "sheet form must include a <sheet>")
        first_child = sheet_nodes[0][0]
        self.assertEqual(
            first_child.tag,
            "div",
            "first child inside <sheet> must be the smart-button box",
        )
        self.assertEqual(first_child.get("class"), "oe_button_box")
        self.assertEqual(first_child.get("name"), "button_box")
        buttons = first_child.xpath(
            './button[@name="action_open_vouchers" and @type="object"]'
        )
        self.assertEqual(
            len(buttons),
            1,
            "button box must expose action_open_vouchers once",
        )
        button = buttons[0]
        self.assertIn("oe_stat_button", (button.get("class") or "").split())
        self.assertEqual(button.get("invisible"), "not id")
        count_fields = button.xpath('.//field[@name="voucher_count"]')
        self.assertTrue(count_fields, "stat button must show voucher_count")
        self.assertEqual(count_fields[0].get("widget"), "statinfo")
        self.assertEqual(count_fields[0].get("string"), "Vouchers")

    def test_sheet_form_header_document_review_visible_when_saved_and_flag_on(self):
        """Header object action is available when the sheet is saved and flag is ON."""
        form_root = self._arch_root("collection.view_collection_sheet_form")
        buttons = form_root.xpath(
            './header/button[@name="action_open_document_review"]'
        )
        self.assertEqual(
            len(buttons),
            1,
            "sheet form header must expose Document Review object action",
        )
        button = buttons[0]
        self.assertEqual(button.get("type"), "object")
        self.assertEqual(
            button.get("invisible"),
            "not id or not document_review_enabled or "
            "state not in ('open', 'submitted')",
        )
        helpers = form_root.xpath('.//field[@name="document_review_enabled"]')
        self.assertTrue(
            helpers,
            "sheet form must include document_review_enabled for the header modifier",
        )
        self.assertIn(
            helpers[0].get("invisible"),
            ("1", "True", "true"),
            "document_review_enabled helper must stay invisible on the sheet form",
        )
        self.env.company.write({"document_review_enabled": True})
        sheet = self.env["collection.sheet"].create(
            {"seller_id": ensure_enabled_seller(self.env).id}
        )
        self.assertIsInstance(sheet.id, int)
        self.assertGreater(sheet.id, 0)
        self.assertTrue(sheet.document_review_enabled)

    def test_sheet_form_header_document_review_hidden_when_flag_off_or_unsaved(self):
        """Header stays hidden when the flag is OFF or the sheet is unsaved."""
        form_root = self._arch_root("collection.view_collection_sheet_form")
        buttons = form_root.xpath(
            './header/button[@name="action_open_document_review"]'
        )
        self.assertEqual(len(buttons), 1)
        self.assertEqual(
            buttons[0].get("invisible"),
            "not id or not document_review_enabled or "
            "state not in ('open', 'submitted')",
        )
        self.env.company.write({"document_review_enabled": False})
        saved = self.env["collection.sheet"].create(
            {"seller_id": ensure_enabled_seller(self.env).id}
        )
        self.assertFalse(saved.document_review_enabled)
        self.env.company.write({"document_review_enabled": True})
        unsaved = self.env["collection.sheet"].new({"seller_id": self.env.user.id})
        self.assertFalse(bool(unsaved.id))
        self.assertTrue(unsaved.document_review_enabled)

    def test_sheet_form_header_has_no_reassign(self):
        """Sheet header MUST NOT expose Reassign Customers after dropping the kanban."""
        form_root = self._arch_root("collection.view_collection_sheet_form")
        header_buttons = [
            node for node in form_root.xpath("./header/*") if node.tag == "button"
        ]
        header_names = [node.get("name") for node in header_buttons]
        self.assertIn("action_open_document_review", header_names)
        self.assertNotIn(
            "action_open_voucher_reassign",
            header_names,
            "Reassign Customers MUST NOT remain on the sheet header",
        )
        self.assertFalse(
            form_root.xpath('./header/button[@string="Reassign Customers"]'),
            "sheet form header must not label any button Reassign Customers",
        )

    # --- Document Review client action (sheet-scoped; no Collections menu) ---

    def test_document_review_menu_and_client_action(self):
        """Client action xmlid stays; Document Review menu xmlid MUST be gone."""
        action = self.env.ref("collection.action_collection_document_review")
        self.assertFalse(
            self.env.ref(
                "collection.menu_collection_document_review",
                raise_if_not_found=False,
            ),
            "Document Review menu xmlid must be removed",
        )
        leftover = self.env["ir.ui.menu"].search([("name", "=", "Document Review")])
        self.assertFalse(
            leftover,
            "Document Review menu record must not exist",
        )
        self.assertEqual(action.type, "ir.actions.client")
        self.assertEqual(action.tag, "collection.document_review")

    def test_document_review_client_action_path_and_name(self):
        """Client action keeps its name/tag and has a collection-scoped URL."""
        action = self.env.ref("collection.action_collection_document_review")
        self.assertEqual(action.name, "Document Review")
        self.assertEqual(action.tag, "collection.document_review")
        self.assertEqual(action.path, "collection-document-review")
        self.assertNotEqual(action._name, "ir.actions.act_window")
        self.assertEqual(action._name, "ir.actions.client")
        self.assertFalse(getattr(action, "res_model", False))

    SETTINGS_FIELD_NAMES = (
        "document_review_enabled",
        "enabled_seller_ids",
        "auto_create_sheet",
        "allowed_document_type_ids",
        "collection_connector_id",
        "seller_binding_ids",
    )

    def test_configuration_settings_menu_and_action(self):
        """Configuration opens the company page; legacy XMLIDs stay inactive."""
        root_menu = self.env.ref("collection.menu_collection_root")
        config_menu = self.env.ref("collection.menu_collection_config")
        settings_menu = self.env.ref("collection.menu_collection_settings")
        action = self.env.ref("collection.action_collection_config_settings")
        system = self.env.ref("base.group_system")

        self.assertEqual(config_menu.name, "Configuration")
        self.assertEqual(config_menu.parent_id, root_menu)
        self.assertEqual(
            config_menu.action,
            self.env.ref("collection.action_collection_company_settings"),
        )
        self.assertEqual(config_menu.action.path, "collection-settings")
        self.assertIn(system, config_menu.group_ids)

        self.assertEqual(settings_menu.name, "Collection Settings")
        self.assertEqual(settings_menu.parent_id, config_menu)
        self.assertFalse(settings_menu.active)
        self.assertEqual(settings_menu.action, action)
        self.assertIn(system, settings_menu.group_ids)

        self.assertEqual(action.type, "ir.actions.act_window")
        self.assertEqual(action.name, "Collection Settings")
        self.assertEqual(action.res_model, "res.config.settings")
        self.assertEqual(action.path, "collection-system-settings")
        self.assertEqual(action.view_mode, "form")
        context = action.context or {}
        if isinstance(context, str):
            self.assertIn("collections", context)
            self.assertIn("module", context)
        else:
            self.assertEqual(context.get("module"), "collections")

    def test_load_menus_includes_configuration_settings(self):
        """Admin navigation exposes one Configuration entry without children."""
        root_menu = self.env.ref("collection.menu_collection_root")
        config_menu = self.env.ref("collection.menu_collection_config")
        settings_menu = self.env.ref("collection.menu_collection_settings")
        menus = self.env["ir.ui.menu"].load_menus(False)
        self.assertIn("root", menus)
        self.assertIn(root_menu.id, menus)
        self.assertIn(
            config_menu.id,
            menus,
            "Configuration menu must be present in load_menus for admin",
        )
        self.assertNotIn(settings_menu.id, menus)
        self.assertEqual(menus[config_menu.id].get("name"), "Configuration")
        self.assertFalse(menus[config_menu.id]["children"])
        self.assertEqual(
            menus[config_menu.id].get("action_model"),
            "ir.actions.act_window",
        )
        self.assertEqual(
            menus[config_menu.id].get("action_id"),
            self.env.ref("collection.action_collection_company_settings").id,
        )

    def test_settings_arch_has_collections_app_and_flag_field(self):
        """Settings inherit MUST expose Collections app and Collection Settings."""
        root = self._arch_root("collection.res_config_settings_view_form")
        apps = root.xpath("//app[@name='collections']")
        self.assertEqual(
            len(apps),
            1,
            "Settings inherit must declare <app name='collections'>",
        )
        for field_name in self.SETTINGS_FIELD_NAMES:
            fields = apps[0].xpath(f".//field[@name='{field_name}']")
            self.assertEqual(
                len(fields),
                1,
                f"Collections settings app must include {field_name}",
            )

    def test_settings_import_button_is_system_only_and_hidden_without_connector(self):
        """Import MUST sit next to Enabled Sellers, system-only, hidden if none."""
        root = self._arch_root("collection.res_config_settings_view_form")
        buttons = root.xpath("//button[@name='action_import_enabled_sellers']")
        self.assertEqual(len(buttons), 1, "Collection Settings must expose Import")
        button = buttons[0]
        self.assertEqual(button.get("type"), "object")
        invisible = button.get("invisible") or ""
        self.assertIn(
            "collection_connector_id",
            invisible,
            f"Import must be hidden without a connector (got {invisible!r})",
        )
        groups = button.get("groups") or ""
        app = root.xpath("//app[@name='collections']")[0]
        app_groups = app.get("groups") or ""
        self.assertTrue(
            "base.group_system" in groups or "base.group_system" in app_groups,
            "Import must be restricted to Settings users",
        )
        setting = button.xpath("ancestor::setting[@id='enabled_seller_ids_setting']")
        self.assertTrue(
            setting,
            "Import must sit next to Enabled Sellers",
        )

    def test_settings_seller_binding_ids_is_readonly_and_hidden_without_connector(
        self,
    ):
        """Seller-binding O2M MUST be readonly and hidden without a connector."""
        root = self._arch_root("collection.res_config_settings_view_form")
        fields = root.xpath(
            "//app[@name='collections']//field[@name='seller_binding_ids']"
        )
        self.assertEqual(
            len(fields),
            1,
            "Collection Settings must expose seller_binding_ids next to Import",
        )
        field = fields[0]
        setting = field.xpath("ancestor::setting[@id='enabled_seller_ids_setting']")
        self.assertTrue(
            setting,
            "seller_binding_ids must sit next to Enabled Sellers / Import",
        )
        invisible = field.get("invisible") or ""
        self.assertIn(
            "collection_connector_id",
            invisible,
            f"seller_binding_ids must hide without a connector (got {invisible!r})",
        )
        readonly = (field.get("readonly") or "").lower()
        self.assertIn(
            readonly,
            ("1", "true"),
            f"seller_binding_ids must be readonly (got {field.get('readonly')!r})",
        )
        nested = {
            node.get("name") for node in field.xpath(".//field") if node.get("name")
        }
        self.assertIn("user_id", nested)
        self.assertIn("commission_percent", nested)
        lists = field.xpath("./list")
        self.assertEqual(len(lists), 1, "Settings O2M must use Odoo 19 <list>")
        self.assertFalse(field.xpath("./tree"), "Settings O2M must not use <tree>")
        for name in ("user_id", "commission_percent"):
            nodes = field.xpath(f".//field[@name='{name}']")
            self.assertEqual(len(nodes), 1, f"Settings O2M must list {name}")
            nested_readonly = (nodes[0].get("readonly") or "").lower()
            self.assertIn(
                nested_readonly,
                ("1", "true"),
                f"{name} must be readonly (got {nodes[0].get('readonly')!r})",
            )

    def test_settings_seller_binding_ids_shows_stored_rates(self):
        """Triangulation: Settings O2M MUST show imported commission rates."""
        field = self.env["res.config.settings"]._fields["seller_binding_ids"]
        self.assertEqual(field.type, "one2many")
        self.assertEqual(
            field.related,
            "collection_connector_id.seller_binding_ids",
        )
        self.assertTrue(field.readonly)
        connector = self.env["collection.connector"].create(
            {"name": "Settings Commission Connector"}
        )
        seller = create_internal_seller(self.env, "settings_commission_seller")
        binding = self.env["collection.connector.seller.binding"].create(
            {
                "connector_id": connector.id,
                "external_seller_id": "EXT-RATE",
                "user_id": seller.id,
                "commission_percent": 5.0,
            }
        )
        self.env.company.write({"collection_connector_id": connector.id})
        settings = self.env["res.config.settings"].create({})
        self.assertEqual(settings.seller_binding_ids, binding)
        self.assertEqual(settings.seller_binding_ids.user_id, seller)
        self.assertAlmostEqual(settings.seller_binding_ids.commission_percent, 5.0)

    def test_settings_seller_binding_ids_empty_without_connector(self):
        """Triangulation: no active connector MUST yield an empty O2M."""
        field = self.env["res.config.settings"]._fields["seller_binding_ids"]
        self.assertTrue(field.readonly)
        self.env.company.write({"collection_connector_id": False})
        self.assertFalse(self.env.company.collection_connector_id)
        settings = self.env["res.config.settings"].create({})
        self.assertFalse(settings.seller_binding_ids)

    def test_settings_combined_view_exposes_collections_flag(self):
        """Triangulation: combined Settings form includes Collection Settings."""
        result = self.env["res.config.settings"].get_view(view_type="form")
        arch = etree.fromstring(result["arch"])
        apps = arch.xpath("//app[@name='collections']")
        self.assertTrue(
            apps,
            "combined Settings view must include app name=collections",
        )
        for field_name in self.SETTINGS_FIELD_NAMES:
            fields = apps[0].xpath(f".//field[@name='{field_name}']")
            self.assertTrue(
                fields,
                f"combined Settings view must include {field_name}",
            )

    def test_load_menus_omits_document_review_when_flag_off(self):
        """When Document Review is OFF, load_menus MUST omit the review menu."""
        self.env.company.write({"document_review_enabled": False})
        self.assertFalse(self.env.company.document_review_enabled)
        self.assertFalse(
            self.env.ref(
                "collection.menu_collection_document_review",
                raise_if_not_found=False,
            ),
            "Document Review menu xmlid must be gone",
        )
        root_menu = self.env.ref("collection.menu_collection_root")
        voucher_menu = self.env.ref("collection.menu_collection_voucher")
        leftover = self.env["ir.ui.menu"].search([("name", "=", "Document Review")])
        self.assertFalse(
            leftover,
            "Document Review menu record must not exist when flag is OFF",
        )
        menus = self.env["ir.ui.menu"].load_menus(False)
        self.assertIn("root", menus)
        self.assertIn(root_menu.id, menus)
        self.assertIn(voucher_menu.id, menus)
        for menu_id, data in menus.items():
            if menu_id == "root" or not isinstance(data, dict):
                continue
            self.assertNotEqual(
                data.get("name"),
                "Document Review",
                "load_menus must omit Document Review when flag is OFF",
            )

    def test_load_menus_includes_document_review_when_flag_on(self):
        """When Document Review is ON, load_menus MUST still omit the review menu."""
        self.env.company.write({"document_review_enabled": True})
        self.assertTrue(self.env.company.document_review_enabled)
        self.assertFalse(
            self.env.ref(
                "collection.menu_collection_document_review",
                raise_if_not_found=False,
            ),
            "Document Review menu xmlid must be gone",
        )
        leftover = self.env["ir.ui.menu"].search([("name", "=", "Document Review")])
        self.assertFalse(
            leftover,
            "Document Review menu record must not exist when flag is ON",
        )
        menus = self.env["ir.ui.menu"].load_menus(False)
        self.assertIn("root", menus)
        for menu_id, data in menus.items():
            if menu_id == "root" or not isinstance(data, dict):
                continue
            self.assertNotEqual(
                data.get("name"),
                "Document Review",
                "load_menus must omit Document Review when flag is ON",
            )

    def test_connector_list_view_uses_list_tag(self):
        list_root = self._arch_root("collection.view_collection_connector_list")
        self.assertEqual(list_root.tag, "list")
        self.assertNotEqual(list_root.tag, "tree")

    def test_legacy_connector_menu_is_inactive_and_retains_action(self):
        """Legacy connector links stay available without a navigation entry."""
        config_menu = self.env.ref("collection.menu_collection_config")
        menu = self.env.ref("collection.menu_collection_connector")
        action = self.env.ref("collection.action_collection_connector")
        system = self.env.ref("base.group_system")
        self.assertEqual(menu.parent_id, config_menu)
        self.assertFalse(menu.active)
        self.assertEqual(menu.action, action)
        self.assertIn(system, menu.group_ids)
        self.assertEqual(action.res_model, "collection.connector")
        self.assertEqual(action.path, "collection-connectors")
        self.assertEqual(action.type, "ir.actions.act_window")

    def test_receipt_views_use_list_and_form_does_not_issue(self):
        """Receipt UI MUST use <list> and MUST keep issuance fields readonly."""
        list_root = self._arch_root("collection.view_collection_receipt_list")
        form_root = self._arch_root("collection.view_collection_receipt_form")
        search_root = self._arch_root("collection.view_collection_receipt_search")
        self.assertEqual(list_root.tag, "list")
        self.assertNotEqual(list_root.tag, "tree")
        self.assertFalse(
            list_root.xpath("//tree"),
            "receipt list arch must not use deprecated <tree>",
        )
        self.assertFalse(
            form_root.xpath("//tree"),
            "receipt form arch must not use deprecated <tree>",
        )
        self.assertEqual(search_root.tag, "search")
        filter_names = [node.get("name") for node in search_root.xpath(".//filter")]
        self.assertIn("filter_draft", filter_names)
        self.assertIn("filter_closed", filter_names)
        self.assertIn("filter_issued", filter_names)
        nested_lists = form_root.xpath(".//list")
        self.assertTrue(nested_lists, "receipt form must embed at least one <list>")
        for list_node in nested_lists:
            self.assertEqual(list_node.tag, "list")
        state_nodes = [
            node
            for node in self._field_nodes(form_root, "state")
            if node.get("widget") != "statusbar"
        ]
        self.assertTrue(state_nodes, "receipt form must expose state as a field")
        self._assert_readonly_field(state_nodes[0], "state")
        self.assertFalse(
            self._field_nodes(form_root, "external_receipt_id"),
            "receipt form must not expose external_receipt_id",
        )
        self.assertFalse(
            self._field_nodes(list_root, "external_receipt_id"),
            "receipt list must not expose external_receipt_id",
        )
        self.assertFalse(
            self._field_nodes(search_root, "external_receipt_id"),
            "receipt search must not expose external_receipt_id",
        )
        self.assertFalse(
            form_root.xpath("//header/button"),
            "receipt form must not expose an issuance button",
        )
        action = self.env.ref("collection.action_collection_receipt")
        menu = self.env.ref("collection.menu_collection_receipt")
        root_menu = self.env.ref("collection.menu_collection_root")
        alloc_menu = self.env.ref("collection.menu_collection_allocation")
        self.assertEqual(action.res_model, "collection.receipt")
        self.assertIn("list", action.view_mode)
        self.assertIn("form", action.view_mode)
        self.assertEqual(menu.parent_id, root_menu)
        self.assertEqual(menu.action, action)
        self.assertGreater(menu.sequence, alloc_menu.sequence)

    def test_receipt_form_applied_debt_page(self):
        """Receipt form MUST notebook a read-only Applied Debt page with <list>."""
        form_root = self._arch_root("collection.view_collection_receipt_form")
        self.assertFalse(
            form_root.xpath("//tree"),
            "receipt form arch must not use deprecated <tree>",
        )
        page_strings = [
            node.get("string") for node in form_root.xpath("//notebook/page")
        ]
        self.assertEqual(
            page_strings,
            [RECEIPT_NOTEBOOK_VALUES, RECEIPT_NOTEBOOK_APPLIED_DEBT],
        )
        values_page = self._notebook_page(form_root, RECEIPT_NOTEBOOK_VALUES)
        self.assertTrue(
            values_page.xpath('./field[@name="value_ids"]/list'),
            "Values page must expose value_ids as a <list>",
        )
        page = self._notebook_page(form_root, RECEIPT_NOTEBOOK_APPLIED_DEBT)
        line_fields = page.xpath('.//field[@name="line_ids"]')
        self.assertEqual(
            len(line_fields),
            1,
            "Applied Debt page must expose line_ids once",
        )
        line_field = line_fields[0]
        self._assert_readonly_field(line_field, "line_ids")
        lists = line_field.xpath("./list")
        self.assertTrue(lists, "line_ids must embed a <list>")
        self.assertTrue(
            self._attr_is_false(lists[0].get("create")),
            "Applied Debt list must disable inline create",
        )
        self.assertTrue(
            self._attr_is_false(lists[0].get("delete")),
            "Applied Debt list must disable inline delete",
        )
        self.assertTrue(
            self._attr_is_false(lists[0].get("edit")),
            "Applied Debt list must disable inline edit",
        )
        list_names = self._field_names(lists[0], xpath="./field")
        for field_name in (
            "invoice_number",
            "due_date",
            "invoice_amount",
            "invoice_balance",
            "amount_applied",
        ):
            self.assertIn(
                field_name, list_names, f"Applied Debt list must show {field_name}"
            )
        self.assertNotIn(
            "external_receipt_id",
            list_names,
            "Applied Debt list must not show external_receipt_id",
        )
        self.assertFalse(
            page.xpath(".//tree"),
            "Applied Debt page must use <list>, not <tree>",
        )

    def test_allocation_form_receipts_page(self):
        """Allocation form MUST notebook a read-mostly Receipts page with <list>."""
        form_root = self._arch_root("collection.view_collection_allocation_form")
        self.assertFalse(
            form_root.xpath("//tree"),
            "allocation form arch must not use deprecated <tree>",
        )
        page = self._notebook_page(form_root, ALLOCATION_NOTEBOOK_RECEIPTS)
        receipt_fields = page.xpath('.//field[@name="receipt_ids"]')
        self.assertEqual(
            len(receipt_fields),
            1,
            "Receipts page must expose receipt_ids once",
        )
        receipt_field = receipt_fields[0]
        self.assertIn(
            receipt_field.get("readonly"),
            ("1", "True", "true"),
            "allocation receipt_ids must be readonly so the form does not issue",
        )
        lists = receipt_field.xpath("./list")
        self.assertTrue(lists, "receipt_ids must embed a <list>")
        self.assertEqual(lists[0].get("create"), "false")
        self.assertEqual(lists[0].get("delete"), "false")
        list_names = self._field_names(lists[0], xpath="./field")
        for field_name in (
            "document_kind",
            "state",
            "total_values",
            "total_applied",
            "amount_on_account",
        ):
            self.assertIn(
                field_name, list_names, f"Receipts list must show {field_name}"
            )
        self.assertNotIn(
            "external_receipt_id",
            list_names,
            "Receipts list must not show external_receipt_id",
        )
        self.assertFalse(
            page.xpath(".//tree"),
            "Receipts page must use <list>, not <tree>",
        )


class TestCollectionResidualBanner(TransactionCase):
    """Focused sheet-form residual banner (do not gate on TestCollectionUi)."""

    def _arch_root(self, xmlid):
        view = self.env.ref(xmlid)
        return etree.fromstring(view.arch)

    def test_sheet_form_residual_banner_outside_open_submitted(self):
        """Banner MUST warn residual cash only outside open and submitted."""
        form_root = self._arch_root("collection.view_collection_sheet_form")
        fields = form_root.xpath('.//field[@name="residual_cash_value_total"]')
        self.assertTrue(
            fields, "sheet form must expose residual_cash_value_total for the banner"
        )
        alerts = form_root.xpath('.//*[@role="alert"]')
        self.assertTrue(alerts, "sheet form must surface a residual-cash warning")
        invisible = alerts[0].get("invisible") or ""
        self.assertIn("open", invisible)
        self.assertIn("submitted", invisible)
        self.assertIn("residual_cash_value_total", invisible)
        self.assertNotIn("attrs", alerts[0].attrib)
        self.assertFalse(alerts[0].get("attrs"))
        arch = etree.tostring(form_root, encoding="unicode")
        self.assertNotIn("attrs=", arch.split("residual_cash_value_total", 1)[-1][:400])

    def test_sheet_form_residual_banner_does_not_block_buttons(self):
        """Residual warning MUST NOT disable Confirm or Close."""
        form_root = self._arch_root("collection.view_collection_sheet_form")
        confirm = form_root.xpath('.//header/button[@name="action_confirm"]')
        close = form_root.xpath('.//header/button[@name="action_close"]')
        self.assertTrue(confirm and close)
        for button in (confirm[0], close[0]):
            invisible = button.get("invisible") or ""
            self.assertNotIn(
                "residual_cash_value_total",
                invisible,
                f"{button.get('name')} must not key off residual cash",
            )
            self.assertNotEqual((button.get("disabled") or "").lower(), "1")
