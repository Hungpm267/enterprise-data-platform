{{ config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='order_id',
    schema='marts',
    partition_by={
      "field": "order_purchase_timestamp",
      "data_type": "timestamp",
      "granularity": "day"
    },
    cluster_by=["order_status", "customer_id"]
) }}

WITH orders AS (
    SELECT * FROM {{ ref('stg_orders') }}
    {% if is_incremental() %}
    WHERE order_purchase_timestamp >= (
        SELECT TIMESTAMP_SUB(MAX(order_purchase_timestamp), INTERVAL 3 DAY)
        FROM {{ this }}
    )
    {% endif %}
),
items AS (
    SELECT
        order_id,
        COUNT(order_item_id) AS total_items,
        SUM(price) AS total_order_value,
        SUM(freight_value) AS total_freight_value
    FROM {{ ref('stg_order_items') }}
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
