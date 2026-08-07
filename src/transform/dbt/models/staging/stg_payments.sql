SELECT
    payment_id,
    order_id,
    payment_type,
    payment_installments,
    payment_value
FROM {{ source('raw_data', 'raw_payments') }}
