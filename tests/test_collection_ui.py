# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.tests import TransactionCase

from .test_collection_payment import ensure_enabled_seller

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
        "customer_identification",
        "create_date",
        "state",
        "document_type",
        "amount",
    )
    VIEW_XMLIDS = (
        "collection.view_collection_voucher_list",
        "collection.view_collection_voucher_search",
        "collection.view_collection_voucher_kanban",
        "collection.view_collection_voucher_form",
    )
    ATTACHMENT_ACCEPT = "image/*,.pdf"

    def _arch_root(self, xmlid):
        view = self.env.ref(xmlid)
        return etree.fromstring(view.arch)

    def _field_names(self, root, xpath=".//field"):
        return [node.get("name") for node in root.xpath(xpath) if node.get("name")]

    def _field_nodes(self, root, field_name):
        return root.xpath(f'//field[@name="{field_name}"]')

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
        self.assertIn("kanban", action.view_mode)
        self.assertIn("list", action.view_mode)
        self.assertIn("form", action.view_mode)
        self.assertEqual(
            action.search_view_id,
            self.env.ref("collection.view_collection_voucher_search"),
        )
        self.assertEqual(action.path, "payment-vouchers")

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
        group_create = search_root.xpath('//filter[contains(@context, "create_date")]')
        self.assertTrue(
            group_create,
            "search view must offer group_by create_date",
        )

    def test_search_filters_pending_approved_rejected(self):
        """Payment Vouchers search MUST filter pending, approved, and rejected."""
        search_root = self._arch_root("collection.view_collection_voucher_search")
        for value in ("pending", "approved", "rejected"):
            filters = search_root.xpath(f'//filter[contains(@domain, "{value}")]')
            matching = [
                node for node in filters if "state" in (node.get("domain") or "")
            ]
            self.assertTrue(
                matching,
                f"Payment Vouchers search must filter state={value}",
            )

    def test_kanban_groups_by_state_and_shows_card_fields(self):
        """Kanban must group by state and show reference, ID, and create_date."""
        kanban_root = self._arch_root("collection.view_collection_voucher_kanban")
        self.assertEqual(kanban_root.tag, "kanban")
        self.assertEqual(kanban_root.get("default_group_by"), "state")
        self.assertEqual(
            kanban_root.get("records_draggable"),
            "1",
            "kanban cards must be draggable between columns",
        )

        card = kanban_root.xpath('//templates/t[@t-name="card"]')
        self.assertTrue(card, "kanban must define a card template")
        self.assertFalse(
            kanban_root.xpath('//templates/t[@t-name="kanban-box"]'),
            "kanban must not use deprecated t-name=kanban-box",
        )
        card_fields = self._field_names(card[0])
        for field_name in ("name", "customer_identification", "create_date"):
            self.assertIn(
                field_name,
                card_fields,
                f"kanban card must show field {field_name}",
            )
        self._assert_create_date_readonly(kanban_root, "kanban")

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

    def test_state_group_expand_shows_all_columns(self):
        """Kanban grouping must return Pending/Approved/Rejected even when empty."""
        Voucher = self.env["collection.voucher"]
        self.assertTrue(
            Voucher._fields["state"].group_expand,
            "state must enable group_expand so empty columns stay visible",
        )
        groups = Voucher.with_context(read_group_expand=True).formatted_read_group(
            domain=[],
            groupby=["state"],
            aggregates=["__count"],
        )
        self.assertEqual(
            [group["state"] for group in groups],
            ["pending", "approved", "rejected"],
        )

    def test_form_statusbar_approve_reject_when_pending(self):
        """Form must show statusbar and Approve/Reject only when pending."""
        voucher = self.env["collection.voucher"].create(
            {
                "customer_identification": "UI-MENU-001",
                "document_type": "cash_deposit",
                "seller_id": ensure_enabled_seller(self.env).id,
            }
        )
        self.assertEqual(voucher.state, "pending")

        form_root = self._arch_root("collection.view_collection_voucher_form")
        self.assertEqual(form_root.tag, "form")

        statusbar = form_root.xpath(
            '//header/field[@name="state" and @widget="statusbar"]'
        )
        self.assertTrue(statusbar, "form must include state statusbar in header")

        approve = form_root.xpath(
            '//header/button[@name="action_approve" and @type="object"]'
        )
        reject = form_root.xpath(
            '//header/button[@name="action_reject" and @type="object"]'
        )
        self.assertTrue(approve, "form must include Approve button")
        self.assertTrue(reject, "form must include Reject button")
        self.assertIn(
            "state != 'pending'",
            approve[0].get("invisible", ""),
            "Approve must be invisible when not pending",
        )
        self.assertIn(
            "state != 'pending'",
            reject[0].get("invisible", ""),
            "Reject must be invisible when not pending",
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
        """Standalone form MUST NOT embed payment_ids; history <list> is allowed."""
        form_root = self._arch_root("collection.view_collection_voucher_form")
        self.assertFalse(
            form_root.xpath('//field[@name="payment_ids"]'),
            "form must not declare payment_ids",
        )
        history_lists = form_root.xpath('//field[@name="review_snapshot_ids"]//list')
        self.assertTrue(
            history_lists,
            "form must embed a review history One2many <list>",
        )
        self.assertEqual(history_lists[0].tag, "list")
        self.assertNotEqual(history_lists[0].tag, "tree")
        for list_node in form_root.xpath(".//list"):
            ancestor_names = [
                node.get("name") for node in list_node.xpath("ancestor::field[@name]")
            ]
            self.assertIn(
                "review_snapshot_ids",
                ancestor_names,
                "form <list> must be the history One2many, not payment_ids",
            )

    def test_form_typed_invisible_payment_fields(self):
        """Form MUST show type-specific payment fields via invisible=."""
        form_root = self._arch_root("collection.view_collection_voucher_form")
        for field_name in SHARED_PAYMENT_FIELDS:
            nodes = self._field_nodes(form_root, field_name)
            self.assertTrue(nodes, f"form must include shared field {field_name}")

        amount = self._field_nodes(form_root, "amount")[0]
        self._assert_invisible_for_document_type(amount, "unsupported", "amount")

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
        """Form MUST notebook Current, Raw OCR, Seller Confirmed, and History."""
        form_root = self._arch_root("collection.view_collection_voucher_form")
        notebook = form_root.xpath("//notebook")
        self.assertTrue(notebook, "form must wrap payment layers in a notebook")
        page_strings = [page.get("string") for page in notebook[0].xpath("./page")]
        for expected in (
            NOTEBOOK_CURRENT,
            NOTEBOOK_RAW,
            NOTEBOOK_SELLER,
            NOTEBOOK_HISTORY,
        ):
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
        self._assert_invisible_for_document_type(
            current_amount, "unsupported", "amount"
        )
        for page_string, prefix, type_field in PROVENANCE_LAYERS:
            page = self._notebook_page(form_root, page_string)
            amount_name = f"{prefix}amount"
            amount_nodes = page.xpath(f'.//field[@name="{amount_name}"]')
            self.assertTrue(
                amount_nodes,
                f"{page_string} must include {amount_name}",
            )
            amount_invisible = amount_nodes[0].get("invisible") or ""
            self.assertIn(
                type_field,
                amount_invisible,
                f"{amount_name} invisible= must use {type_field}",
            )
            self.assertIn(
                " and document_type ==",
                amount_invisible,
                f"{amount_name} must stay visible when Current type is not unsupported",
            )
            self._assert_invisible_for_document_type(
                amount_nodes[0], "unsupported", amount_name
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

    def test_form_review_history_list_readonly_by_revision(self):
        """History page MUST list snapshots readonly, ordered by revision."""
        form_root = self._arch_root("collection.view_collection_voucher_form")
        history = self._notebook_page(form_root, NOTEBOOK_HISTORY)
        fields = history.xpath('.//field[@name="review_snapshot_ids"]')
        self.assertTrue(
            fields,
            "History page must declare review_snapshot_ids",
        )
        node = fields[0]
        self._assert_readonly_field(node, "review_snapshot_ids")
        lists = node.xpath("./list")
        self.assertTrue(lists, "review_snapshot_ids must embed a <list>")
        history_list = lists[0]
        self.assertEqual(history_list.tag, "list")
        self.assertNotEqual(history_list.tag, "tree")
        default_order = history_list.get("default_order") or ""
        self.assertIn(
            "revision",
            default_order,
            f"history list default_order must include revision (got {default_order!r})",
        )
        list_fields = self._field_names(history_list)
        self.assertIn("revision", list_fields)
        for attr in ("create", "delete", "edit"):
            self.assertEqual(
                (history_list.get(attr) or "").lower(),
                "false",
                f"history list must set {attr}=false",
            )
        arch = etree.tostring(history, encoding="unicode")
        self.assertNotIn("payment_ids", arch)
        self.assertNotIn("attachment", arch)
        self.assertNotIn("datas", arch)
        self.assertNotIn("base64", arch)

    def test_payment_vouchers_views_omit_binary_widgets(self):
        """Form, list, and kanban MUST omit Binary widgets; form chatter remains."""
        for xmlid, label in (
            ("collection.view_collection_voucher_form", "form"),
            ("collection.view_collection_voucher_list", "list"),
            ("collection.view_collection_voucher_kanban", "kanban"),
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
        """Payment Vouchers kanban/list/form and action MUST allow create and edit."""
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
            ("collection.view_collection_voucher_kanban", "kanban"),
            ("collection.view_collection_voucher_form", "form"),
        ):
            self._assert_create_edit_enabled(self._arch_root(xmlid), label)

    def test_unsupported_filter_lists_unsupported_vouchers(self):
        """Payment Vouchers search MUST list unsupported via document_type filter."""
        search_root = self._arch_root("collection.view_collection_voucher_search")
        unsupported_filters = search_root.xpath(
            '//filter[contains(@domain, "unsupported")]'
        )
        self.assertTrue(
            unsupported_filters,
            "Payment Vouchers search must filter document_type=unsupported",
        )
        domain = unsupported_filters[0].get("domain") or ""
        self.assertIn("document_type", domain)
        self.assertIn("unsupported", domain)

        voucher = self.env["collection.voucher"].create(
            {
                "customer_identification": "UI-UNSUPPORTED-MENU-001",
                "document_type": "unsupported",
                "document_id": "UI-UNSUP-DOC-002",
                "seller_id": ensure_enabled_seller(self.env).id,
            }
        )
        found = self.env["collection.voucher"].search(
            [("document_type", "=", "unsupported"), ("id", "=", voucher.id)]
        )
        self.assertEqual(found, voucher)

    def test_ui_create_may_omit_document_id(self):
        """UI-style create may omit document_id on a standalone voucher."""
        voucher = self.env["collection.voucher"].create(
            {
                "customer_identification": "UI-TYPED-DEFAULT-002",
                "document_type": "cash_deposit",
                "seller_id": ensure_enabled_seller(self.env).id,
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

    def test_collection_sheets_form_statusbar_close_reopen(self):
        """Sheet form: required seller, dates, non-clickable statusbar, Close/Reopen."""
        form_root = self._arch_root("collection.view_collection_sheet_form")
        self.assertEqual(form_root.tag, "form")
        self._assert_create_edit_enabled(form_root, "sheet form")
        names = self._field_names(form_root)
        for field_name in ("name", "seller_id", "date_from", "date_to", "voucher_ids"):
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
        membership = self._field_nodes(form_root, "voucher_ids")[0]
        self.assertEqual(membership.get("widget"), "many2many")
        self.assertIn(
            "state == 'closed'",
            membership.get("readonly") or "",
            "membership must be readonly when the sheet is closed",
        )
        statusbar = form_root.xpath(
            '//header/field[@name="state" and @widget="statusbar"]'
        )
        self.assertTrue(statusbar, "sheet form must include state statusbar in header")
        self.assertEqual(statusbar[0].get("statusbar_visible"), "open,closed")
        options = statusbar[0].get("options") or ""
        self.assertIn("clickable", options)
        self.assertIn("False", options)
        close = form_root.xpath(
            '//header/button[@name="action_close" and @type="object"]'
        )
        reopen = form_root.xpath(
            '//header/button[@name="action_reopen" and @type="object"]'
        )
        self.assertTrue(close, "form must include Close button")
        self.assertTrue(reopen, "form must include Reopen button")
        self.assertIn(
            "state != 'open'",
            close[0].get("invisible", ""),
            "Close must be invisible when not open",
        )
        self.assertIn(
            "state != 'closed'",
            reopen[0].get("invisible", ""),
            "Reopen must be invisible when not closed",
        )
        self.assertTrue(
            form_root.xpath('./header/button[@name="action_open_document_review"]'),
            "Document Review header button must remain on the sheet form",
        )
        self.assertNotIn(
            "received_date",
            etree.tostring(form_root, encoding="unicode"),
        )
        chatter = form_root.xpath("//chatter")
        self.assertTrue(
            chatter, "sheet form must include <chatter/> for messaging/activities"
        )

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
            "not id or not document_review_enabled",
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
            "not id or not document_review_enabled",
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
        """Triangulation: client action keeps English name/tag and clears path."""
        action = self.env.ref("collection.action_collection_document_review")
        self.assertEqual(action.name, "Document Review")
        self.assertEqual(action.tag, "collection.document_review")
        self.assertFalse(
            action.path,
            "client action path must be cleared (no /odoo/document-review shortcut)",
        )
        self.assertNotEqual(action._name, "ir.actions.act_window")
        self.assertEqual(action._name, "ir.actions.client")
        self.assertFalse(getattr(action, "res_model", False))

    SETTINGS_FIELD_NAMES = (
        "document_review_enabled",
        "enabled_seller_ids",
        "auto_create_sheet",
        "allowed_document_type_ids",
    )

    def test_configuration_settings_menu_and_action(self):
        """Collections → Configuration → Collection Settings must keep XMLID."""
        root_menu = self.env.ref("collection.menu_collection_root")
        config_menu = self.env.ref("collection.menu_collection_config")
        settings_menu = self.env.ref("collection.menu_collection_settings")
        action = self.env.ref("collection.action_collection_config_settings")
        system = self.env.ref("base.group_system")

        self.assertEqual(config_menu.name, "Configuration")
        self.assertEqual(config_menu.parent_id, root_menu)
        self.assertFalse(config_menu.action)
        self.assertIn(system, config_menu.group_ids)

        self.assertEqual(settings_menu.name, "Collection Settings")
        self.assertEqual(settings_menu.parent_id, config_menu)
        self.assertEqual(settings_menu.action, action)
        self.assertIn(system, settings_menu.group_ids)

        self.assertEqual(action.type, "ir.actions.act_window")
        self.assertEqual(action.name, "Collection Settings")
        self.assertEqual(action.res_model, "res.config.settings")
        self.assertEqual(action.view_mode, "form")
        context = action.context or {}
        if isinstance(context, str):
            self.assertIn("collections", context)
            self.assertIn("module", context)
        else:
            self.assertEqual(context.get("module"), "collections")

    def test_load_menus_includes_configuration_settings(self):
        """Admin load_menus MUST include Collections → Collection Settings."""
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
        self.assertIn(
            settings_menu.id,
            menus,
            "Collection Settings menu must be present in load_menus for admin",
        )
        self.assertEqual(menus[config_menu.id].get("name"), "Configuration")
        self.assertEqual(menus[settings_menu.id].get("name"), "Collection Settings")
        self.assertEqual(
            menus[settings_menu.id].get("action_model"),
            "ir.actions.act_window",
        )
        self.assertEqual(
            menus[settings_menu.id].get("action_id"),
            self.env.ref("collection.action_collection_config_settings").id,
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
