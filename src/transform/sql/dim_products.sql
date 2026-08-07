CREATE SCHEMA IF NOT EXISTS marts;

DROP TABLE IF EXISTS marts.dim_products;

CREATE TABLE marts.dim_products AS
SELECT
    product_id,
    COALESCE(product_category_name, 'Unknown') AS product_category_name
FROM staging.stg_raw_products;
