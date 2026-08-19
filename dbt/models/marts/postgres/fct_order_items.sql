-- depends_on: {{ ref('stg_order_items') }}
-- depends_on: {{ ref('stg_orders') }}
-- depends_on: {{ ref('fct_orders') }}

{{ config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='order_item_id',
    schema='marts'
) }}

WITH items AS (
    SELECT
        oi.order_item_id,
        oi.order_id,
        oi.product_id,
        o.customer_id,
        oi.price,
        oi.freight_value,
        o.order_purchase_timestamp
    FROM {{ ref('stg_order_items') }} oi
    LEFT JOIN {{ ref('stg_orders') }} o ON oi.order_id = o.order_id
)

SELECT
    order_item_id,
    order_id,
    product_id,
    customer_id,
    price,
    freight_value
FROM items
{% if is_incremental() %}
    {% if var('start_date', none) and var('end_date', none) %}
        WHERE order_purchase_timestamp >= '{{ var("start_date") }}'
          AND order_purchase_timestamp <= '{{ var("end_date") }}'
    {% elif var('start_date', none) %}
        WHERE order_purchase_timestamp >= '{{ var("start_date") }}'
    {% else %}
        WHERE order_purchase_timestamp >= (
            SELECT TIMESTAMP_SUB(MAX(order_purchase_timestamp), INTERVAL 3 DAY)
            FROM {{ ref('fct_orders') }}
        )
    {% endif %}
{% endif %}