

  create or replace view `data-engineering-504901`.`staging`.`stg_products`
  OPTIONS()
  as SELECT
    product_id,
    product_category_name
FROM `data-engineering-504901`.`staging`.`stg_raw_products`;

