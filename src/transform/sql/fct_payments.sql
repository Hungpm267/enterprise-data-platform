CREATE SCHEMA IF NOT EXISTS marts;

DROP TABLE IF EXISTS marts.fct_payments;

CREATE TABLE marts.fct_payments AS
SELECT
    payment_id,
    order_id,
    payment_type,
    payment_installments,
    payment_value
FROM staging.stg_raw_payments;
