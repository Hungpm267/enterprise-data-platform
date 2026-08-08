{{ config(materialized='table') }}

WITH orders AS (
    SELECT * FROM {{ source('staging', 'stg_raw_orders') }}
),
items AS (
    SELECT
        order_id,
        COUNT(item_id) AS total_items,
        SUM(SAFE_CAST(price AS NUMERIC)) AS total_order_value,
        SUM(SAFE_CAST(freight_value AS NUMERIC)) AS total_freight_value
    FROM {{ source('staging', 'stg_raw_order_items') }}
    GROUP BY order_id
)

SELECT
    o.order_id,
    o.customer_id,
    o.order_status,
    o.order_purchase_timestamp,
    COALESCE(i.total_items, 0) AS total_items,
    COALESCE(i.total_order_value, 0.0) AS total_order_value,
    COALESCE(i.total_freight_value, 0.0) AS total_freight_value
FROM orders o
LEFT JOIN items i ON o.order_id = i.order_id
