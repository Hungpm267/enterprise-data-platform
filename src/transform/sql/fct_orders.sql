CREATE SCHEMA IF NOT EXISTS marts;

DROP TABLE IF EXISTS marts.fct_orders;

CREATE TABLE marts.fct_orders AS
SELECT
    o.order_id,
    o.customer_id,
    o.order_status,
    CAST(o.order_purchase_timestamp AS TIMESTAMP) AS order_purchase_timestamp,
    CAST(o.order_estimated_delivery_date AS TIMESTAMP) AS order_estimated_delivery_date,
    COUNT(i.order_item_id) AS total_items,
    COALESCE(SUM(CAST(i.price AS NUMERIC)), 0) AS total_order_value,
    COALESCE(SUM(CAST(i.freight_value AS NUMERIC)), 0) AS total_freight_value
FROM staging.stg_raw_orders o
LEFT JOIN staging.stg_raw_order_items i ON o.order_id = i.order_id
GROUP BY o.order_id, o.customer_id, o.order_status, o.order_purchase_timestamp, o.order_estimated_delivery_date;
