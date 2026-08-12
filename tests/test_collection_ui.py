# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.tests import TransactionCase

TYPED_PAYMENT_LIST_SPECS = (
    (
        "bank_transfer",
        (
            "document_id",
            "amount",
            "from_account",
            "to_account",
            "voucher_number",
            "voucher_date",
        ),
    ),
    (
        "check",
        (
            "document_id",
            "amount",
            "check_number",
            "check_bank",
            "check_type",
            "check_issue_date",
            "check_payment_date",
        ),
    ),
    (
        "cash_deposit",
        (
            "document_id",
            "amount",
        ),
    ),
)


class TestCollectionUi(TransactionCase):
    """Registry/arch coverage for Menu and form behaviors (no browser E2E)."""

    REQUIRED_LIST_SEARCH_FIELDS = (
        "name",
        "customer_identification",
        "create_date",
        "state",
    )
    VIEW_XMLIDS = (
        "collection.view_collection_voucher_list",
        "collection.view_collection_voucher_search",
        "collection.view_collection_voucher_kanban",
        "collection.view_collection_voucher_form",
    )

    def _arch_root(self, xmlid):
        view = self.env.ref(xmlid)
        return etree.fromstring(view.arch)

    def _field_names(self, root, xpath=".//field"):
        return [node.get("name") for node in root.xpath(xpath) if node.get("name")]

    def _field_nodes(self, root, field_name):
        return root.xpath(f'//field[@name="{field_name}"]')

    def _typed_payment_field_nodes(self, form_root):
        """Return payment_ids field nodes that declare a document_type domain."""
        nodes = []
        for node in form_root.xpath('//field[@name="payment_ids"]'):
            domain = node.get("domain") or ""
            if "document_type" in domain:
                nodes.append(node)
        return nodes

    def _typed_list_by_document_type(self, form_root):
        """Map document_type → (field node, editable list) for typed embeds."""
        by_type = {}
        for node in self._typed_payment_field_nodes(form_root):
            domain = node.get("domain") or ""
            lists = node.xpath('./list[@editable="bottom"]')
            self.assertTrue(
                lists,
                f"typed payment_ids embed must have editable list (domain={domain!r})",
            )
            matched = None
            for doc_type, _fields in TYPED_PAYMENT_LIST_SPECS:
                if f"'{doc_type}'" in domain or f'"{doc_type}"' in domain:
                    matched = doc_type
                    break
            self.assertIsNotNone(
                matched,
                f"typed payment_ids domain must target a known type: {domain!r}",
            )
            self.assertNotIn(
                matched,
                by_type,
                f"duplicate typed list for document_type={matched}",
            )
            by_type[matched] = (node, lists[0])
        return by_type

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

    def test_list_and_search_show_required_fields(self):
        """List and search arches must expose reference, ID, create_date, status."""
        list_root = self._arch_root("collection.view_collection_voucher_list")
        search_root = self._arch_root("collection.view_collection_voucher_search")

        self.assertEqual(list_root.tag, "list")
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
        """Kanban grouping must return New/Validated/Rejected even when empty."""
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
            ["new", "validated", "rejected"],
        )

    def test_form_statusbar_buttons_lines_and_chatter(self):
        """Form must show statusbar, Validate/Reject, typed editable lines, chatter."""
        voucher = self.env["collection.voucher"].create(
            {"customer_identification": "UI-MENU-001"}
        )
        self.assertEqual(voucher.state, "new")

        form_root = self._arch_root("collection.view_collection_voucher_form")
        self.assertEqual(form_root.tag, "form")

        statusbar = form_root.xpath(
            '//header/field[@name="state" and @widget="statusbar"]'
        )
        self.assertTrue(statusbar, "form must include state statusbar in header")

        validate = form_root.xpath(
            '//header/button[@name="action_validate" and @type="object"]'
        )
        reject = form_root.xpath(
            '//header/button[@name="action_reject" and @type="object"]'
        )
        self.assertTrue(validate, "form must include Validate button")
        self.assertTrue(reject, "form must include Reject button")
        self.assertIn(
            "state != 'new'",
            validate[0].get("invisible", ""),
            "Validate must be invisible when not new",
        )
        self.assertIn(
            "state != 'new'",
            reject[0].get("invisible", ""),
            "Reject must be invisible when not new",
        )

        typed_lists = self._typed_list_by_document_type(form_root)
        self.assertEqual(
            list(typed_lists),
            [doc_type for doc_type, _fields in TYPED_PAYMENT_LIST_SPECS],
            "form must include three stacked typed editable payment lists",
        )
        for _doc_type, (field_node, list_node) in typed_lists.items():
            line_fields = self._field_names(list_node)
            self.assertIn("amount", line_fields)
            self.assertIn("document_id", line_fields)
            self.assertNotIn("document_type", line_fields)
            self.assertIn(
                "default_document_type",
                field_node.get("context") or "",
                "typed list must set default_document_type context",
            )

        self._assert_create_date_readonly(form_root, "form")
        form_fields = self._field_names(form_root)
        self.assertIn("create_date", form_fields)
        self.assertNotIn("received_date", form_fields)

        chatter = form_root.xpath("//chatter")
        self.assertTrue(
            chatter, "form must include <chatter/> for messaging/activities"
        )

    def test_form_has_three_stacked_typed_payment_lists(self):
        """Form MUST expose typed bank/check/cash lists and MUST NOT keep mono list."""
        form_root = self._arch_root("collection.view_collection_voucher_form")
        typed_lists = self._typed_list_by_document_type(form_root)
        expected_order = [doc_type for doc_type, _fields in TYPED_PAYMENT_LIST_SPECS]

        self.assertEqual(
            list(typed_lists),
            expected_order,
            "typed lists must appear as bank_transfer, check, cash_deposit",
        )

        # Mono all-type list: payment_ids without a document_type domain.
        mono_lists = []
        for node in form_root.xpath('//field[@name="payment_ids"]'):
            domain = node.get("domain") or ""
            if "document_type" not in domain:
                mono_lists.extend(node.xpath("./list"))
        self.assertFalse(
            mono_lists,
            "form must not keep a mono all-type payment_ids list",
        )

        for doc_type, required_fields in TYPED_PAYMENT_LIST_SPECS:
            field_node, list_node = typed_lists[doc_type]
            line_fields = self._field_names(list_node)
            for field_name in required_fields:
                self.assertIn(
                    field_name,
                    line_fields,
                    f"{doc_type} list must include field {field_name}",
                )
            self.assertNotIn(
                "document_type",
                line_fields,
                f"{doc_type} list must hide document_type column",
            )
            context = field_node.get("context") or ""
            self.assertIn(
                f"'default_document_type': '{doc_type}'",
                context.replace('"', "'"),
                f"{doc_type} list must default document_type via context",
            )
            domain = field_node.get("domain") or ""
            self.assertIn(
                doc_type,
                domain,
                f"{doc_type} list domain must filter document_type",
            )

    def test_form_typed_lists_field_sets_differ_by_type(self):
        """Triangulation: each typed list exposes only its type-specific columns."""
        form_root = self._arch_root("collection.view_collection_voucher_form")
        typed_lists = self._typed_list_by_document_type(form_root)

        bank_fields = set(self._field_names(typed_lists["bank_transfer"][1]))
        check_fields = set(self._field_names(typed_lists["check"][1]))
        cash_fields = set(self._field_names(typed_lists["cash_deposit"][1]))

        self.assertTrue({"from_account", "to_account"} <= bank_fields)
        self.assertFalse({"from_account", "to_account"} & check_fields)
        self.assertFalse({"from_account", "to_account"} & cash_fields)

        self.assertTrue({"check_number", "check_bank", "check_type"} <= check_fields)
        self.assertFalse({"check_number", "check_bank", "check_type"} & bank_fields)
        self.assertFalse({"check_number", "check_bank", "check_type"} & cash_fields)

        self.assertEqual(
            cash_fields & {"document_id", "amount"},
            {"document_id", "amount"},
        )
        self.assertFalse(
            {"voucher_number", "voucher_date", "check_number"} & cash_fields,
            "cash_deposit list must not show bank/check-only columns",
        )

    def test_typed_list_default_document_type_persists(self):
        """Creating a line with each table's arch context MUST set document_type."""
        form_root = self._arch_root("collection.view_collection_voucher_form")
        typed_lists = self._typed_list_by_document_type(form_root)
        self.assertEqual(
            len(typed_lists),
            3,
            "typed lists with default_document_type context must exist",
        )

        voucher = self.env["collection.voucher"].create(
            {"customer_identification": "UI-TYPED-DEFAULT-001"}
        )
        Line = self.env["collection.voucher.line"]

        for doc_type, (field_node, _list_node) in typed_lists.items():
            context = field_node.get("context") or ""
            self.assertIn(
                f"'default_document_type': '{doc_type}'",
                context.replace('"', "'"),
                f"{doc_type} arch context must declare default_document_type",
            )
            line = Line.with_context(default_document_type=doc_type).create(
                {
                    "voucher_id": voucher.id,
                    "amount": 10.0,
                }
            )
            self.assertEqual(
                line.document_type,
                doc_type,
                f"default_document_type={doc_type!r} must persist on create",
            )

    def test_typed_list_default_document_type_without_document_id(self):
        """UI-style create may omit document_id and still default type."""
        form_root = self._arch_root("collection.view_collection_voucher_form")
        typed_lists = self._typed_list_by_document_type(form_root)
        self.assertIn("cash_deposit", typed_lists)

        voucher = self.env["collection.voucher"].create(
            {"customer_identification": "UI-TYPED-DEFAULT-002"}
        )
        line = (
            self.env["collection.voucher.line"]
            .with_context(default_document_type="cash_deposit")
            .create({"voucher_id": voucher.id})
        )
        self.assertEqual(line.document_type, "cash_deposit")
        self.assertFalse(line.document_id)

    # --- Phase 2: Payment Lines menu (Unit 2) ---

    PAYMENT_LINE_SEARCH_FIELDS = (
        "document_type",
        "document_id",
        "amount",
        "voucher_id",
        "from_account",
        "to_account",
        "voucher_number",
        "voucher_date",
        "check_number",
        "check_bank",
        "check_type",
        "check_issue_date",
        "check_payment_date",
    )

    def test_payment_lines_menu_and_action_read_only(self):
        """Collections → Payment Lines must open read-only line act_window."""
        root_menu = self.env.ref("collection.menu_collection_root")
        lines_menu = self.env.ref("collection.menu_collection_voucher_line")
        action = self.env.ref("collection.action_collection_voucher_line")

        self.assertEqual(lines_menu.name, "Payment Lines")
        self.assertEqual(lines_menu.parent_id, root_menu)
        self.assertEqual(lines_menu.action, action)
        self.assertEqual(action.res_model, "collection.voucher.line")
        self.assertIn("list", action.view_mode)

        context = action.context or ""
        if isinstance(context, dict):
            context_repr = repr(context)
            create_disabled = context.get("create") is False
            edit_disabled = context.get("edit") is False
        else:
            context_repr = str(context).replace('"', "'")
            create_disabled = "'create': False" in context_repr or "'create':False" in (
                context_repr.replace(" ", "")
            )
            edit_disabled = "'edit': False" in context_repr or "'edit':False" in (
                context_repr.replace(" ", "")
            )
        self.assertTrue(
            create_disabled,
            f"Payment Lines action must disable create (context={context_repr!r})",
        )
        self.assertTrue(
            edit_disabled,
            f"Payment Lines action must disable edit (context={context_repr!r})",
        )

        self.assertEqual(
            action.search_view_id,
            self.env.ref("collection.view_collection_voucher_line_search"),
        )
        list_view = self.env.ref("collection.view_collection_voucher_line_list")
        self.assertEqual(list_view.model, "collection.voucher.line")

    def test_payment_lines_search_exposes_filter_fields(self):
        """Payment Lines search MUST allow filtering by line and voucher fields."""
        search_root = self._arch_root("collection.view_collection_voucher_line_search")
        self.assertEqual(search_root.tag, "search")
        search_fields = self._field_names(search_root)
        for field_name in self.PAYMENT_LINE_SEARCH_FIELDS:
            self.assertIn(
                field_name,
                search_fields,
                f"Payment Lines search must include field {field_name}",
            )

        list_root = self._arch_root("collection.view_collection_voucher_line_list")
        self.assertEqual(list_root.tag, "list")
        list_fields = self._field_names(list_root)
        for field_name in (
            "document_type",
            "document_id",
            "amount",
            "voucher_id",
        ):
            self.assertIn(
                field_name,
                list_fields,
                f"Payment Lines list must show field {field_name}",
            )

    def test_unsupported_absent_from_typed_form_tables(self):
        """unsupported lines MUST NOT match any typed form list domain."""
        form_root = self._arch_root("collection.view_collection_voucher_form")
        typed_lists = self._typed_list_by_document_type(form_root)
        self.assertEqual(len(typed_lists), 3)
        for doc_type, (field_node, _list_node) in typed_lists.items():
            domain = field_node.get("domain") or ""
            self.assertNotIn(
                "unsupported",
                domain,
                f"{doc_type} typed list must not include unsupported",
            )

        voucher = self.env["collection.voucher"].create(
            {"customer_identification": "UI-UNSUPPORTED-FORM-001"}
        )
        unsupported = self.env["collection.voucher.line"].create(
            {
                "voucher_id": voucher.id,
                "document_type": "unsupported",
                "document_id": "UI-UNSUP-DOC-001",
                "amount": 1.0,
            }
        )
        for doc_type in ("bank_transfer", "check", "cash_deposit"):
            matched = self.env["collection.voucher.line"].search(
                [
                    ("voucher_id", "=", voucher.id),
                    ("document_type", "=", doc_type),
                    ("id", "=", unsupported.id),
                ]
            )
            self.assertFalse(
                matched,
                f"unsupported line must not appear under {doc_type} domain",
            )

    def test_unsupported_findable_via_payment_lines_filter(self):
        """Payment Lines search MUST offer an unsupported document_type filter."""
        search_root = self._arch_root("collection.view_collection_voucher_line_search")
        unsupported_filters = search_root.xpath(
            '//filter[contains(@domain, "unsupported")]'
        )
        self.assertTrue(
            unsupported_filters,
            "Payment Lines search must include a filter for document_type=unsupported",
        )
        domain = unsupported_filters[0].get("domain") or ""
        self.assertIn("document_type", domain)
        self.assertIn("unsupported", domain)

        voucher = self.env["collection.voucher"].create(
            {"customer_identification": "UI-UNSUPPORTED-MENU-001"}
        )
        unsupported = self.env["collection.voucher.line"].create(
            {
                "voucher_id": voucher.id,
                "document_type": "unsupported",
                "document_id": "UI-UNSUP-DOC-002",
                "amount": 2.0,
            }
        )
        found = self.env["collection.voucher.line"].search(
            [("document_type", "=", "unsupported"), ("id", "=", unsupported.id)]
        )
        self.assertEqual(found, unsupported)

    # --- Phase 2: Line attachment binary widgets (Unit 2) ---

    ATTACHMENT_ACCEPT = "image/*,.pdf"

    def _assert_attachment_binary_widget(self, list_node, context):
        """Assert list has one binary attachment widget with filename + accept."""
        attachment_nodes = list_node.xpath('./field[@name="attachment"]')
        self.assertEqual(
            len(attachment_nodes),
            1,
            f"{context} must declare exactly one attachment field",
        )
        node = attachment_nodes[0]
        self.assertEqual(
            node.get("widget"),
            "binary",
            f"{context} attachment must use widget=binary",
        )
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
        self.assertIn(
            "image/*",
            options,
            f"{context} accept must allow image/*",
        )
        self.assertIn(
            ".pdf",
            options,
            f"{context} accept must allow PDF (.pdf)",
        )
        self.assertIn(
            self.ATTACHMENT_ACCEPT,
            options.replace(" ", ""),
            (
                f"{context} accepted_file_extensions must be "
                f"{self.ATTACHMENT_ACCEPT!r} (got {options!r})"
            ),
        )
        filename_nodes = list_node.xpath('./field[@name="attachment_filename"]')
        self.assertEqual(
            len(filename_nodes),
            1,
            f"{context} must declare attachment_filename field",
        )

    def test_typed_lists_include_attachment_binary_widgets(self):
        """Each typed payment list MUST expose Binary attachment + filename widgets."""
        form_root = self._arch_root("collection.view_collection_voucher_form")
        typed_lists = self._typed_list_by_document_type(form_root)
        self.assertEqual(
            len(typed_lists),
            3,
            "typed lists must exist before attachment widget checks",
        )
        for doc_type, (_field_node, list_node) in typed_lists.items():
            self._assert_attachment_binary_widget(list_node, f"typed {doc_type} list")

    def test_payment_lines_list_includes_attachment_binary_widget(self):
        """Payment Lines list MUST expose Binary attachment + filename widgets."""
        list_root = self._arch_root("collection.view_collection_voucher_line_list")
        self.assertEqual(list_root.tag, "list")
        self._assert_attachment_binary_widget(list_root, "Payment Lines list")

    def test_typed_and_payment_lists_attachment_accept_is_image_and_pdf(self):
        """Triangulation: accept filter must allow image/* and PDF on all four lists."""
        form_root = self._arch_root("collection.view_collection_voucher_form")
        typed_lists = self._typed_list_by_document_type(form_root)
        payment_list = self._arch_root("collection.view_collection_voucher_line_list")
        targets = [
            (f"typed {doc_type}", list_node)
            for doc_type, (_field_node, list_node) in typed_lists.items()
        ]
        targets.append(("Payment Lines list", payment_list))
        self.assertEqual(len(targets), 4)

        for label, list_node in targets:
            attachment_nodes = list_node.xpath('./field[@name="attachment"]')
            self.assertEqual(
                len(attachment_nodes),
                1,
                f"{label} must declare attachment for accept triangulation",
            )
            options = attachment_nodes[0].get("options") or ""
            self.assertIn("image/*", options, f"{label} must accept image/*")
            self.assertIn(".pdf", options, f"{label} must accept .pdf")
            self.assertNotIn(
                ".doc",
                options,
                f"{label} must not advertise non-image/PDF extensions",
            )

    # --- Phase 2: Document Review client action (PR 2) ---

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
