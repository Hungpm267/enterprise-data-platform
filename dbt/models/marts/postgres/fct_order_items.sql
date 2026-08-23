-- depends_on: {{ ref('stg_order_items') }}
-- depends_on: {{ ref('stg_orders') }}
-- depends_on: {{ ref('fct_orders') }}

{{ config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key=['tenant_slug', 'order_item_id'],
    schema='marts'
) }}

WITH items AS (
    SELECT
        oi.tenant_slug,
        oi.order_item_id,
        oi.order_id,
        oi.product_id,
        o.customer_id,
        oi.price,
        oi.freight_value,
        o.order_purchase_timestamp
    FROM {{ ref('stg_order_items') }} oi
    LEFT JOIN {{ ref('stg_orders') }} o
        ON oi.order_id = o.order_id
       AND oi.tenant_slug = o.tenant_slug
)

SELECT
    tenant_slug,
    order_item_id,
    order_id,
    product_id,
    customer_id,
    price,
    freight_value
FROM items it
{% if is_incremental() %}
    {% if var('start_date', none) and var('end_date', none) %}
        WHERE order_purchase_timestamp >= '{{ var("start_date") }}'
          AND order_purchase_timestamp <= '{{ var("end_date") }}'
    {% elif var('start_date', none) %}
        WHERE order_purchase_timestamp >= '{{ var("start_date") }}'
    {% else %}
        -- Per-tenant watermark: each tenant's cutoff is derived only from
        -- that tenant's own max order_purchase_timestamp in fct_orders,
        -- never the global max, so a lagging tenant's new rows are never
        -- silently skipped. A brand-new tenant (no rows yet in fct_orders)
        -- has no watermark row at all, so the correlated subquery returns
        -- NULL and COALESCE falls back to an epoch sentinel, letting its
        -- first load land unconditionally instead of being excluded forever.
        WHERE it.order_purchase_timestamp >= COALESCE(
            (
                SELECT TIMESTAMP_SUB(MAX(fo.order_purchase_timestamp), INTERVAL 3 DAY)
                FROM {{ ref('fct_orders') }} AS fo
                WHERE fo.tenant_slug = it.tenant_slug
            ),
            TIMESTAMP('1970-01-01')
        )
    {% endif %}
{% endif %}
