
  
    

    create or replace table `data-engineering-504901`.`marts`.`fct_orders`
      
    
    

    
    OPTIONS()
    as (
      

WITH orders AS (
    SELECT * FROM `data-engineering-504901`.`staging`.`stg_orders`
),
items AS (
    SELECT
        order_id,
        COUNT(order_item_id) AS total_items,
        SUM(price) AS total_order_value,
        SUM(freight_value) AS total_freight_value
    FROM `data-engineering-504901`.`staging`.`stg_order_items`
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
    );
  