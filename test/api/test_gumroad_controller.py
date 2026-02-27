import unittest
from unittest.mock import MagicMock, patch

from api.gumroad_controller import GumroadController
from api.model.gumroad_ping_payload import GumroadPingPayload
from di.di import DI
from features.accounting.purchases.purchase_service import PurchaseService
from util.errors import AuthorizationError


class GumroadControllerTest(unittest.TestCase):

    mock_di: DI
    mock_purchase_service: PurchaseService
    controller: GumroadController

    def setUp(self):
        self.mock_di = MagicMock(spec = DI)
        self.mock_purchase_service = MagicMock(spec = PurchaseService)
        self.mock_di.purchase_service = self.mock_purchase_service
        self.controller = GumroadController(self.mock_di)

    def _create_payload(self, seller_id = "seller-123") -> GumroadPingPayload:
        return GumroadPingPayload(
            seller_id = seller_id,
            sale_id = "sale-456",
            sale_timestamp = "2024-01-01T00:00:00Z",
            price = 1000,
            product_id = "product-789",
            product_name = "Test Product",
            product_permalink = "https://example.com/product",
            short_product_id = "short-123",
            license_key = "LICENSE-KEY-ABC",
            quantity = 1,
            gumroad_fee = 100,
            affiliate_credit_amount_cents = 50,
            discover_fee_charge = False,
            url_params = {},
            custom_fields = {},
            test = False,
            is_preorder_authorization = False,
            refunded = False,
        )

    @patch("api.gumroad_controller.config")
    def test_handle_ping_success(self, mock_config):
        mock_config.gumroad_seller_id_check = False
        payload = self._create_payload()

        self.controller.handle_ping(payload)

        self.mock_purchase_service.record_purchase.assert_called_once_with(payload)

    @patch("api.gumroad_controller.config")
    def test_handle_ping_with_seller_id_check_disabled(self, mock_config):
        mock_config.gumroad_seller_id_check = False
        payload = self._create_payload(seller_id = "wrong-seller")

        self.controller.handle_ping(payload)

        self.mock_purchase_service.record_purchase.assert_called_once_with(payload)

    @patch("api.gumroad_controller.config")
    def test_handle_ping_with_seller_id_check_valid(self, mock_config):
        mock_config.gumroad_seller_id_check = True
        mock_config.gumroad_seller_id = "seller-123"
        payload = self._create_payload(seller_id = "seller-123")

        self.controller.handle_ping(payload)

        self.mock_purchase_service.record_purchase.assert_called_once_with(payload)

    @patch("api.gumroad_controller.config")
    def test_handle_ping_with_seller_id_check_invalid(self, mock_config):
        mock_config.gumroad_seller_id_check = True
        mock_config.gumroad_seller_id = "seller-123"
        payload = self._create_payload(seller_id = "wrong-seller")

        with self.assertRaises(AuthorizationError) as context:
            self.controller.handle_ping(payload)

        self.assertIn("Unauthorized seller ID", str(context.exception))
        self.assertIn("wrong-seller", str(context.exception))
        self.mock_purchase_service.record_purchase.assert_not_called()
