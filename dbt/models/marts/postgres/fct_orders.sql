{{ config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key=['tenant_slug', 'order_id'],
    schema='marts',
    partition_by={
      "field": "order_purchase_timestamp",
      "data_type": "timestamp",
      "granularity": "day"
    },
    cluster_by=["tenant_slug", "order_status", "customer_id"]
) }}

WITH orders AS (
    SELECT * FROM {{ ref('stg_orders') }} AS so
    {% if is_incremental() %}
        {% if var('start_date', none) and var('end_date', none) %}
            WHERE order_purchase_timestamp >= '{{ var("start_date") }}'
              AND order_purchase_timestamp <= '{{ var("end_date") }}'
        {% elif var('start_date', none) %}
            WHERE order_purchase_timestamp >= '{{ var("start_date") }}'
        {% else %}
            -- Per-tenant watermark: each tenant's cutoff is derived only from
            -- that tenant's own max timestamp in {{ this }}, never the global
            -- max, so a lagging tenant's new rows are never silently skipped.
            -- A brand-new tenant (no rows yet in {{ this }}) has no watermark
            -- row at all, so the correlated subquery returns NULL and
            -- COALESCE falls back to an epoch sentinel, letting its first
            -- load land unconditionally instead of being excluded forever.
            WHERE so.order_purchase_timestamp >= COALESCE(
                (
                    SELECT TIMESTAMP_SUB(MAX(t.order_purchase_timestamp), INTERVAL 3 DAY)
                    FROM {{ this }} AS t
                    WHERE t.tenant_slug = so.tenant_slug
                ),
                TIMESTAMP('1970-01-01')
            )
        {% endif %}
    {% endif %}
),
items AS (
    SELECT
        tenant_slug,
        order_id,
        COUNT(order_item_id) AS total_items,
        SUM(price) AS total_order_value,
        SUM(freight_value) AS total_freight_value
    FROM {{ ref('stg_order_items') }}
    GROUP BY tenant_slug, order_id
)

SELECT
    o.tenant_slug,
    o.order_id,
    o.customer_id,
    o.order_status,
    o.order_purchase_timestamp,
    COALESCE(i.total_items, 0) AS total_items,
    COALESCE(i.total_order_value, 0.0) AS total_order_value,
    COALESCE(i.total_freight_value, 0.0) AS total_freight_value
FROM orders o
LEFT JOIN items i
    ON o.order_id = i.order_id
   AND o.tenant_slug = i.tenant_slug
