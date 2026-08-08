SELECT
    order_id,
    item_id,
    product_id,
    seller_id,
    SAFE_CAST(price AS NUMERIC) AS price,
    SAFE_CAST(freight_value AS NUMERIC) AS freight_value
FROM {{ source('staging', 'stg_raw_order_items') }}
