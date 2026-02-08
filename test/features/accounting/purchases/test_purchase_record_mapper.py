import unittest
import uuid
from datetime import datetime, timezone

from db.model.purchase_record import PurchaseRecordDB
from features.accounting.purchases.purchase_record import PurchaseRecord
from features.accounting.purchases.purchase_record_mapper import db, domain


class PurchaseRecordMapperTest(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

        self.db_record = PurchaseRecordDB(
            id = uuid.uuid4(),
            user_id = uuid.uuid4(),
            seller_id = "seller-123",
            sale_id = "sale-456",
            sale_timestamp = datetime.now(timezone.utc),
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
            url_params = {"user_id": "test-user"},
            custom_fields = {"field1": "value1"},
            test = False,
            is_preorder_authorization = False,
            refunded = False,
        )

        self.domain_record = PurchaseRecord(
            id = self.db_record.id,
            user_id = self.db_record.user_id,
            seller_id = "seller-123",
            sale_id = "sale-456",
            sale_timestamp = self.db_record.sale_timestamp,
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
            url_params = {"user_id": "test-user"},
            custom_fields = {"field1": "value1"},
            test = False,
            is_preorder_authorization = False,
            refunded = False,
        )

    def test_domain_to_db_none(self):
        db_obj = db(None)
        self.assertIsNone(db_obj)

    def test_domain_to_db(self):
        db_obj = db(self.domain_record)

        self.assertIsInstance(db_obj, PurchaseRecordDB)
        self.assertEqual(db_obj.id, self.domain_record.id)
        self.assertEqual(db_obj.user_id, self.domain_record.user_id)
        self.assertEqual(db_obj.seller_id, "seller-123")
        self.assertEqual(db_obj.sale_id, "sale-456")
        self.assertEqual(db_obj.sale_timestamp, self.domain_record.sale_timestamp)
        self.assertEqual(db_obj.price, 1000)
        self.assertEqual(db_obj.product_id, "product-789")
        self.assertEqual(db_obj.product_name, "Test Product")
        self.assertEqual(db_obj.product_permalink, "https://example.com/product")
        self.assertEqual(db_obj.short_product_id, "short-123")
        self.assertEqual(db_obj.license_key, "LICENSE-KEY-ABC")
        self.assertEqual(db_obj.quantity, 1)
        self.assertEqual(db_obj.gumroad_fee, 100)
        self.assertEqual(db_obj.affiliate_credit_amount_cents, 50)
        self.assertEqual(db_obj.discover_fee_charge, False)
        self.assertEqual(db_obj.url_params, {"user_id": "test-user"})
        self.assertEqual(db_obj.custom_fields, {"field1": "value1"})
        self.assertEqual(db_obj.test, False)
        self.assertEqual(db_obj.is_preorder_authorization, False)
        self.assertEqual(db_obj.refunded, False)

    def test_db_to_domain(self):
        domain_obj = domain(self.db_record)

        self.assertIsInstance(domain_obj, PurchaseRecord)
        self.assertEqual(domain_obj.id, self.db_record.id)
        self.assertEqual(domain_obj.user_id, self.db_record.user_id)
        self.assertEqual(domain_obj.seller_id, "seller-123")
        self.assertEqual(domain_obj.sale_id, "sale-456")
        self.assertEqual(domain_obj.sale_timestamp, self.db_record.sale_timestamp)
        self.assertEqual(domain_obj.price, 1000)
        self.assertEqual(domain_obj.product_id, "product-789")
        self.assertEqual(domain_obj.product_name, "Test Product")
        self.assertEqual(domain_obj.product_permalink, "https://example.com/product")
        self.assertEqual(domain_obj.short_product_id, "short-123")
        self.assertEqual(domain_obj.license_key, "LICENSE-KEY-ABC")
        self.assertEqual(domain_obj.quantity, 1)
        self.assertEqual(domain_obj.gumroad_fee, 100)
        self.assertEqual(domain_obj.affiliate_credit_amount_cents, 50)
        self.assertEqual(domain_obj.discover_fee_charge, False)
        self.assertEqual(domain_obj.url_params, {"user_id": "test-user"})
        self.assertEqual(domain_obj.custom_fields, {"field1": "value1"})
        self.assertEqual(domain_obj.test, False)
        self.assertEqual(domain_obj.is_preorder_authorization, False)
        self.assertEqual(domain_obj.refunded, False)

    def test_db_to_domain_none(self):
        domain_obj = domain(None)
        self.assertIsNone(domain_obj)
