# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.service.model import get_public_method
from odoo.tests import TransactionCase

from .common_connector import TEST_CONNECTOR_TYPE, install_test_connector_type
from .test_collection_payment import create_internal_seller

# Called only server side (MCP tools, Import, allocation helpers): never over RPC.
INTERNAL_CONNECTOR_OPERATIONS = (
    "list_sellers",
    "list_customers",
    "get_customer_debt",
    "resolve_customer_partner",
    "create_receipt",
)


class TestCollectionConnectorAccess(TransactionCase):
    """Connector operations are not an RPC surface for ordinary users."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        install_test_connector_type(cls)
        cls.plain_user = create_internal_seller(cls.env, "connector_access_plain")
        cls.manager = create_internal_seller(cls.env, "connector_access_manager")
        cls.manager.write(
            {
                "group_ids": [
                    Command.link(cls.env.ref("collection.group_collection_manager").id)
                ]
            }
        )
        cls.admin_user = create_internal_seller(cls.env, "connector_access_admin")
        cls.admin_user.write(
            {"group_ids": [Command.link(cls.env.ref("base.group_system").id)]}
        )

    def setUp(self):
        super().setUp()
        install_test_connector_type(self)
        self.connector = self.env["collection.connector"].create(
            {"name": "Access Connector", "type": TEST_CONNECTOR_TYPE}
        )

    def test_internal_operations_are_not_rpc_callable(self):
        for name in INTERNAL_CONNECTOR_OPERATIONS:
            with self.subTest(method=name), self.assertRaises(AccessError):
                get_public_method(self.connector, name)

    def test_test_connection_stays_a_public_button_method(self):
        self.assertTrue(get_public_method(self.connector, "test_connection"))

    def test_test_connection_refuses_users_who_cannot_manage_the_connector(self):
        with self.assertRaises(AccessError):
            self.connector.with_user(self.plain_user).test_connection()

    def test_test_connection_allowed_for_manager_and_admin(self):
        for user in (self.manager, self.admin_user):
            with self.subTest(user=user.login):
                action = self.connector.with_user(user).test_connection()
                self.assertEqual(action["params"]["type"], "success")
