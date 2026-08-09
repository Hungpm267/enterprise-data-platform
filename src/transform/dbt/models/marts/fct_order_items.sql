{{ config(materialized='table', schema='marts') }}

SELECT
    oi.order_item_id,
    oi.order_id,
    oi.product_id,
    o.customer_id,
    oi.price,
    oi.freight_value
FROM {{ ref('stg_order_items') }} oi
LEFT JOIN {{ ref('stg_orders') }} o ON oi.order_id = o.order_id
