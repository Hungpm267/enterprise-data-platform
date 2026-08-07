CREATE SCHEMA IF NOT EXISTS marts;

DROP TABLE IF EXISTS marts.dim_customers;

CREATE TABLE marts.dim_customers AS
SELECT
    customer_id,
    INITCAP(TRIM(customer_city)) AS customer_city,
    UPPER(TRIM(customer_state)) AS customer_state
FROM staging.stg_raw_customers;
