SELECT
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp,
    order_estimated_delivery_date
FROM {{ source('staging', 'stg_raw_orders') }}
