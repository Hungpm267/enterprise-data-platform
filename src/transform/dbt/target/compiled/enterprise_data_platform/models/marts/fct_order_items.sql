

SELECT
    oi.order_item_id,
    oi.order_id,
    oi.product_id,
    o.customer_id,
    oi.price,
    oi.freight_value
FROM `data-engineering-504901`.`staging`.`stg_order_items` oi
LEFT JOIN `data-engineering-504901`.`staging`.`stg_orders` o ON oi.order_id = o.order_id

WHERE o.order_purchase_timestamp >= (
    SELECT TIMESTAMP_SUB(MAX(o_sub.order_purchase_timestamp), INTERVAL 3 DAY)
    FROM `data-engineering-504901`.`marts`.`fct_order_items` oi_sub
    LEFT JOIN `data-engineering-504901`.`staging`.`stg_orders` o_sub ON oi_sub.order_id = o_sub.order_id
)
