import unittest
from unittest.mock import MagicMock, Mock
from uuid import UUID

from api.model.gumroad_ping_payload import GumroadPingPayload
from db.crud.user import UserCRUD
from di.di import DI
from features.accounting.purchases.purchase_record import PurchaseRecord
from features.accounting.purchases.purchase_record_repo import PurchaseRecordRepository
from features.accounting.purchases.purchase_service import PurchaseService


class PurchaseServiceTest(unittest.TestCase):

    mock_di: DI
    user_id: UUID
    service: PurchaseService

    def setUp(self):
        self.user_id = UUID(int = 1)

        self.mock_di = Mock(spec = DI)

        mock_user = Mock()
        mock_user.id = self.user_id
        mock_user_crud = Mock(spec = UserCRUD)
        mock_user_crud.get = MagicMock(return_value = mock_user)
        self.mock_di.user_crud = mock_user_crud

        mock_repo = Mock(spec = PurchaseRecordRepository)
        mock_repo.save = MagicMock(side_effect = lambda x: x)
        mock_repo.get_by_user = MagicMock(return_value = [])
        mock_repo.get_aggregates_by_user = MagicMock(return_value = None)
        mock_repo.bind_license_key_to_user = MagicMock()
        self.mock_di.purchase_record_repo = mock_repo

        self.service = PurchaseService(self.mock_di)

    def _create_payload(
        self,
        sale_id = "sale-123",
        user_id_in_params = None,
        license_key = None,
        refunded = False,
    ) -> GumroadPingPayload:
        url_params = {}
        if user_id_in_params:
            url_params["user_id"] = user_id_in_params

        return GumroadPingPayload(
            seller_id = "seller-123",
            sale_id = sale_id,
            sale_timestamp = "2024-01-01T00:00:00Z",
            price = 1000,
            product_id = "product-123",
            product_name = "Test Product",
            product_permalink = "https://example.com/product",
            short_product_id = "short-123",
            license_key = license_key,
            quantity = 1,
            gumroad_fee = 100,
            affiliate_credit_amount_cents = 50,
            discover_fee_charge = False,
            url_params = url_params if url_params else None,
            custom_fields = {},
            test = False,
            is_preorder_authorization = False,
            refunded = refunded,
        )

    def test_record_purchase_success(self):
        payload = self._create_payload()
        record = self.service.record_purchase(payload)

        self.assertIsInstance(record, PurchaseRecord)
        self.assertEqual(record.sale_id, "sale-123")
        self.assertEqual(record.price, 1000)
        self.mock_di.purchase_record_repo.save.assert_called_once()

    def test_record_purchase_extracts_user_id_from_url_params(self):
        payload = self._create_payload(user_id_in_params = str(self.user_id))
        record = self.service.record_purchase(payload)

        self.assertEqual(record.user_id, self.user_id)
        self.mock_di.user_crud.get.assert_called_once_with(self.user_id)

    def test_record_purchase_handles_missing_user_id(self):
        payload = self._create_payload(user_id_in_params = None)
        record = self.service.record_purchase(payload)

        self.assertIsNone(record.user_id)

    def test_record_purchase_handles_invalid_user_id(self):
        payload = self._create_payload(user_id_in_params = "invalid-uuid")
        record = self.service.record_purchase(payload)

        self.assertIsNone(record.user_id)

    def test_record_purchase_handles_nonexistent_user(self):
        self.mock_di.user_crud.get.return_value = None
        payload = self._create_payload(user_id_in_params = str(self.user_id))
        record = self.service.record_purchase(payload)

        self.assertIsNone(record.user_id)

    def test_record_purchase_persists_to_repo(self):
        payload = self._create_payload()
        self.service.record_purchase(payload)

        self.mock_di.purchase_record_repo.save.assert_called_once()

    def test_bind_license_key_delegates_to_repo(self):
        self.service.bind_license_key(self.user_id, "LICENSE-123")

        self.mock_di.purchase_record_repo.bind_license_key_to_user.assert_called_once_with(
            "LICENSE-123",
            self.user_id,
        )

    def test_get_by_user_delegates_to_repo(self):
        self.service.get_by_user(self.user_id)

        self.mock_di.purchase_record_repo.get_by_user.assert_called_once_with(
            self.user_id,
            skip = 0,
            limit = 50,
            start_date = None,
            end_date = None,
            product_id = None,
        )

    def test_get_aggregates_by_user_delegates_to_repo(self):
        self.service.get_aggregates_by_user(self.user_id)

        self.mock_di.purchase_record_repo.get_aggregates_by_user.assert_called_once_with(
            self.user_id,
            start_date = None,
            end_date = None,
            product_id = None,
        )
