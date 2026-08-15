

  create or replace view `data-engineering-504901`.`staging`.`stg_orders`
  OPTIONS()
  as SELECT
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp,
    order_estimated_delivery_date
FROM `data-engineering-504901`.`staging`.`stg_raw_orders`;

