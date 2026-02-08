from db.model.purchase_record import PurchaseRecordDB
from features.accounting.purchases.purchase_record import PurchaseRecord


def domain(db_model: PurchaseRecordDB | None) -> PurchaseRecord | None:
    if db_model is None:
        return None

    return PurchaseRecord(
        id = db_model.id,
        user_id = db_model.user_id,
        seller_id = db_model.seller_id,
        sale_id = db_model.sale_id,
        sale_timestamp = db_model.sale_timestamp,
        price = db_model.price,
        product_id = db_model.product_id,
        product_name = db_model.product_name,
        product_permalink = db_model.product_permalink,
        short_product_id = db_model.short_product_id,
        license_key = db_model.license_key,
        quantity = db_model.quantity,
        gumroad_fee = db_model.gumroad_fee,
        affiliate_credit_amount_cents = db_model.affiliate_credit_amount_cents,
        discover_fee_charge = db_model.discover_fee_charge,
        url_params = db_model.url_params,
        custom_fields = db_model.custom_fields,
        test = db_model.test,
        is_preorder_authorization = db_model.is_preorder_authorization,
        refunded = db_model.refunded,
    )


def db(domain_model: PurchaseRecord | None) -> PurchaseRecordDB | None:
    if domain_model is None:
        return None

    return PurchaseRecordDB(
        id = domain_model.id,
        user_id = domain_model.user_id,
        seller_id = domain_model.seller_id,
        sale_id = domain_model.sale_id,
        sale_timestamp = domain_model.sale_timestamp,
        price = domain_model.price,
        product_id = domain_model.product_id,
        product_name = domain_model.product_name,
        product_permalink = domain_model.product_permalink,
        short_product_id = domain_model.short_product_id,
        license_key = domain_model.license_key,
        quantity = domain_model.quantity,
        gumroad_fee = domain_model.gumroad_fee,
        affiliate_credit_amount_cents = domain_model.affiliate_credit_amount_cents,
        discover_fee_charge = domain_model.discover_fee_charge,
        url_params = domain_model.url_params,
        custom_fields = domain_model.custom_fields,
        test = domain_model.test,
        is_preorder_authorization = domain_model.is_preorder_authorization,
        refunded = domain_model.refunded,
    )
