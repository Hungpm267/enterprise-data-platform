-- back compat for old kwarg name
  
  
        
            
            
            
            
        
    

    

    merge into `data-engineering-504901`.`marts`.`fct_orders` as DBT_INTERNAL_DEST
        using (

WITH orders AS (
    SELECT * FROM `data-engineering-504901`.`staging`.`stg_orders`
    
    WHERE order_purchase_timestamp >= (
        SELECT TIMESTAMP_SUB(MAX(order_purchase_timestamp), INTERVAL 3 DAY)
        FROM `data-engineering-504901`.`marts`.`fct_orders`
    )
    
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
        ) as DBT_INTERNAL_SOURCE
        on ((DBT_INTERNAL_SOURCE.order_id = DBT_INTERNAL_DEST.order_id))

    
    when matched then update set
        `order_id` = DBT_INTERNAL_SOURCE.`order_id`,`customer_id` = DBT_INTERNAL_SOURCE.`customer_id`,`order_status` = DBT_INTERNAL_SOURCE.`order_status`,`order_purchase_timestamp` = DBT_INTERNAL_SOURCE.`order_purchase_timestamp`,`total_items` = DBT_INTERNAL_SOURCE.`total_items`,`total_order_value` = DBT_INTERNAL_SOURCE.`total_order_value`,`total_freight_value` = DBT_INTERNAL_SOURCE.`total_freight_value`
    

    when not matched then insert
        (`order_id`, `customer_id`, `order_status`, `order_purchase_timestamp`, `total_items`, `total_order_value`, `total_freight_value`)
    values
        (`order_id`, `customer_id`, `order_status`, `order_purchase_timestamp`, `total_items`, `total_order_value`, `total_freight_value`)


    