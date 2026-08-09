

  create or replace view `data-engineering-504901`.`staging`.`stg_order_items`
  OPTIONS()
  as SELECT
    order_item_id,
    order_id,
    product_id,
    SAFE_CAST(price AS NUMERIC) AS price,
    SAFE_CAST(freight_value AS NUMERIC) AS freight_value
FROM `data-engineering-504901`.`staging`.`stg_raw_order_items`;

