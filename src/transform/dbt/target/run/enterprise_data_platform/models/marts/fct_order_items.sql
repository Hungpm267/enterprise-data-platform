-- back compat for old kwarg name
  
  
        
            
            
            
            
        
    

    

    merge into `data-engineering-504901`.`marts`.`fct_order_items` as DBT_INTERNAL_DEST
        using (

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

        ) as DBT_INTERNAL_SOURCE
        on ((DBT_INTERNAL_SOURCE.order_item_id = DBT_INTERNAL_DEST.order_item_id))

    
    when matched then update set
        `order_item_id` = DBT_INTERNAL_SOURCE.`order_item_id`,`order_id` = DBT_INTERNAL_SOURCE.`order_id`,`product_id` = DBT_INTERNAL_SOURCE.`product_id`,`customer_id` = DBT_INTERNAL_SOURCE.`customer_id`,`price` = DBT_INTERNAL_SOURCE.`price`,`freight_value` = DBT_INTERNAL_SOURCE.`freight_value`
    

    when not matched then insert
        (`order_item_id`, `order_id`, `product_id`, `customer_id`, `price`, `freight_value`)
    values
        (`order_item_id`, `order_id`, `product_id`, `customer_id`, `price`, `freight_value`)


    