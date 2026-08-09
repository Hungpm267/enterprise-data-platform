SELECT
    payment_id,
    order_id,
    payment_type,
    payment_installments,
    SAFE_CAST(payment_value AS NUMERIC) AS payment_value
FROM `data-engineering-504901`.`staging`.`stg_raw_payments`