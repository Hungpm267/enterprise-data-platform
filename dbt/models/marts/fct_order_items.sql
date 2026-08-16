{{ config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='order_item_id',
    schema='marts',
    cluster_by=["product_id"]
) }}

SELECT
    oi.order_item_id,
    oi.order_id,
    oi.product_id,
    o.customer_id,
    oi.price,
    oi.freight_value
FROM {{ ref('stg_order_items') }} oi
LEFT JOIN {{ ref('stg_orders') }} o ON oi.order_id = o.order_id
{% if is_incremental() %}
WHERE o.order_purchase_timestamp >= (
    SELECT TIMESTAMP_SUB(MAX(o_sub.order_purchase_timestamp), INTERVAL 3 DAY)
    FROM {{ this }} oi_sub
    LEFT JOIN {{ ref('stg_orders') }} o_sub ON oi_sub.order_id = o_sub.order_id
)
{% endif %}
