# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.tests import TransactionCase


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

    def _field_names(self, root, xpath="//field"):
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
        """Form must show statusbar, Validate/Reject, editable lines, chatter."""
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

        payment_lists = form_root.xpath(
            '//field[@name="payment_ids"]/list[@editable="bottom"]'
        )
        self.assertTrue(
            payment_lists,
            "form must include editable payment_ids list",
        )
        line_fields = self._field_names(payment_lists[0])
        self.assertIn("document_type", line_fields)
        self.assertIn("amount", line_fields)

        self._assert_create_date_readonly(form_root, "form")
        form_fields = self._field_names(form_root)
        self.assertIn("create_date", form_fields)
        self.assertNotIn("received_date", form_fields)

        chatter = form_root.xpath("//chatter")
        self.assertTrue(
            chatter, "form must include <chatter/> for messaging/activities"
        )
