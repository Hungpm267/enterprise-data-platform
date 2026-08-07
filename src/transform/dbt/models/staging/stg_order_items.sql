SELECT
    order_item_id,
    order_id,
    product_id,
    price,
    freight_value
FROM {{ source('raw_data', 'raw_order_items') }}
