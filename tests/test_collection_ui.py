# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.tests import TransactionCase

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

    def _assert_attachment_binary_widget(self, root, context):
        """Assert arch has Binary attachment + filename with image/PDF accept."""
        attachment_nodes = root.xpath('.//field[@name="attachment"]')
        self.assertTrue(
            attachment_nodes,
            f"{context} must declare an attachment field",
        )
        binary_nodes = [
            node for node in attachment_nodes if node.get("widget") == "binary"
        ]
        self.assertTrue(
            binary_nodes,
            f"{context} attachment must use widget=binary",
        )
        node = binary_nodes[0]
        self.assertEqual(
            node.get("filename"),
            "attachment_filename",
            f"{context} attachment must set filename=attachment_filename",
        )
        options = node.get("options") or ""
        self.assertIn(
            "accepted_file_extensions",
            options,
            f"{context} attachment must set accepted_file_extensions",
        )
        self.assertIn("image/*", options, f"{context} accept must allow image/*")
        self.assertIn(".pdf", options, f"{context} accept must allow PDF (.pdf)")
        self.assertIn(
            self.ATTACHMENT_ACCEPT,
            options.replace(" ", ""),
            (
                f"{context} accepted_file_extensions must be "
                f"{self.ATTACHMENT_ACCEPT!r} (got {options!r})"
            ),
        )
        self.assertNotIn(
            ".doc",
            options,
            f"{context} must not advertise non-image/PDF extensions",
        )
        filename_nodes = root.xpath('.//field[@name="attachment_filename"]')
        self.assertTrue(
            filename_nodes,
            f"{context} must declare attachment_filename field",
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
        """Standalone form MUST NOT embed typed payment_ids lists."""
        form_root = self._arch_root("collection.view_collection_voucher_form")
        self.assertFalse(
            form_root.xpath('//field[@name="payment_ids"]'),
            "form must not declare payment_ids",
        )
        self.assertFalse(
            form_root.xpath(".//list"),
            "form must not embed typed payment-line tables",
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

    def test_payment_vouchers_views_include_attachment_binary_widgets(self):
        """Form, list, and kanban MUST expose Binary attachment + filename widgets."""
        for xmlid, label in (
            ("collection.view_collection_voucher_form", "form"),
            ("collection.view_collection_voucher_list", "list"),
            ("collection.view_collection_voucher_kanban", "kanban"),
        ):
            root = self._arch_root(xmlid)
            self._assert_attachment_binary_widget(root, label)

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
            }
        )
        self.assertEqual(voucher.document_type, "cash_deposit")
        self.assertFalse(voucher.document_id)

    def test_form_seller_id_is_required(self):
        """Payment Vouchers form MUST require seller_id (ORM stays nullable)."""
        form_root = self._arch_root("collection.view_collection_voucher_form")
        nodes = self._field_nodes(form_root, "seller_id")
        self.assertTrue(nodes, "form must include seller_id")
        required = nodes[0].get("required")
        self.assertIn(
            required,
            ("1", "True", "true"),
            f"form seller_id must be required (got {required!r})",
        )

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
        for field_name in ("name", "seller_id", "date_from", "date_to"):
            self.assertIn(field_name, list_fields, f"list must show {field_name}")
            self.assertIn(field_name, search_fields, f"search must show {field_name}")
        self._assert_create_edit_enabled(list_root, "sheet list")

    def test_collection_sheets_form_without_statusbar(self):
        """Sheet form: required seller readonly after create, dates, membership."""
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
        self.assertFalse(
            form_root.xpath('//field[@widget="statusbar"]'),
            "sheet form must not include a workflow statusbar",
        )
        self.assertNotIn(
            "received_date",
            etree.tostring(form_root, encoding="unicode"),
        )

    # --- Document Review client action (kept; OWL retarget is Phase 3) ---

    def test_document_review_menu_and_client_action(self):
        """Collections → Document Review must keep the client action tag."""
        root_menu = self.env.ref("collection.menu_collection_root")
        review_menu = self.env.ref("collection.menu_collection_document_review")
        action = self.env.ref("collection.action_collection_document_review")

        self.assertEqual(review_menu.name, "Document Review")
        self.assertEqual(review_menu.parent_id, root_menu)
        self.assertEqual(review_menu.action, action)
        self.assertEqual(action.type, "ir.actions.client")
        self.assertEqual(action.tag, "collection.document_review")

    def test_document_review_client_action_path_and_name(self):
        """Triangulation: client action keeps English name and document-review path."""
        action = self.env.ref("collection.action_collection_document_review")
        self.assertEqual(action.name, "Document Review")
        self.assertEqual(action.path, "document-review")
        self.assertNotEqual(action._name, "ir.actions.act_window")
        self.assertEqual(action._name, "ir.actions.client")
        self.assertFalse(getattr(action, "res_model", False))

    def test_settings_arch_has_collections_app_and_flag_field(self):
        """Settings inherit MUST expose app name=collections and the related flag."""
        root = self._arch_root("collection.res_config_settings_view_form")
        apps = root.xpath("//app[@name='collections']")
        self.assertEqual(
            len(apps),
            1,
            "Settings inherit must declare <app name='collections'>",
        )
        fields = apps[0].xpath(".//field[@name='document_review_enabled']")
        self.assertEqual(
            len(fields),
            1,
            "Collections settings app must include document_review_enabled",
        )

    def test_settings_combined_view_exposes_collections_flag(self):
        """Triangulation: combined Settings form via get_view includes the flag."""
        result = self.env["res.config.settings"].get_view(view_type="form")
        arch = etree.fromstring(result["arch"])
        apps = arch.xpath("//app[@name='collections']")
        self.assertTrue(
            apps,
            "combined Settings view must include app name=collections",
        )
        fields = apps[0].xpath(".//field[@name='document_review_enabled']")
        self.assertTrue(
            fields,
            "combined Settings view must include document_review_enabled",
        )

    def test_load_menus_omits_document_review_when_flag_off(self):
        """When Document Review is OFF, load_menus MUST omit the review menu."""
        self.env.company.write({"document_review_enabled": False})
        self.assertFalse(self.env.company.document_review_enabled)
        review_menu = self.env.ref("collection.menu_collection_document_review")
        root_menu = self.env.ref("collection.menu_collection_root")
        voucher_menu = self.env.ref("collection.menu_collection_voucher")
        menus = self.env["ir.ui.menu"].load_menus(False)
        self.assertIn("root", menus)
        self.assertIn(root_menu.id, menus)
        self.assertIn(voucher_menu.id, menus)
        self.assertNotIn(
            review_menu.id,
            menus,
            "Document Review menu must be absent from load_menus when flag is OFF",
        )

    def test_load_menus_includes_document_review_when_flag_on(self):
        """When Document Review is ON, load_menus MUST include the review menu."""
        self.env.company.write({"document_review_enabled": True})
        self.assertTrue(self.env.company.document_review_enabled)
        review_menu = self.env.ref("collection.menu_collection_document_review")
        menus = self.env["ir.ui.menu"].load_menus(False)
        self.assertIn("root", menus)
        self.assertIn(
            review_menu.id,
            menus,
            "Document Review menu must be present in load_menus when flag is ON",
        )
