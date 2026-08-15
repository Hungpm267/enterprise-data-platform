

  create or replace view `data-engineering-504901`.`marts`.`wide_orders_analytics`
  OPTIONS()
  as 

SELECT
    -- Order Header Info
    o.order_id,
    o.customer_id,
    o.order_status,
    o.order_purchase_timestamp,
    o.total_items AS order_total_items,
    o.total_order_value,
    o.total_freight_value,

    -- Customer Dimension Info
    c.customer_city,
    c.customer_state,

    -- Order Item Detail Info
    oi.order_item_id,
    oi.product_id,
    oi.price AS item_price,
    oi.freight_value AS item_freight_value,

    -- Product Dimension Info
    p.product_category_name

FROM `data-engineering-504901`.`marts`.`fct_orders` o
LEFT JOIN `data-engineering-504901`.`marts`.`dim_customers` c ON o.customer_id = c.customer_id
LEFT JOIN `data-engineering-504901`.`marts`.`fct_order_items` oi ON o.order_id = oi.order_id
LEFT JOIN `data-engineering-504901`.`marts`.`dim_products` p ON oi.product_id = p.product_id;

