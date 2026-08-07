SELECT
    order_id,
    customer_id,
    order_estimated_delivery_date,
    order_purchase_timestamp,
    order_status
FROM {{ source('raw_data', 'raw_orders') }}
