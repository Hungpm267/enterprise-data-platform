SELECT
    payment_id,
    order_id,
    payment_type,
    payment_installments,
    SAFE_CAST(payment_value AS NUMERIC) AS payment_value
FROM {{ source('staging', 'stg_raw_payments') }}
