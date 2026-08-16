{{ config(materialized='table', schema='marts') }}

SELECT
    payment_id,
    order_id,
    payment_type,
    payment_installments,
    payment_value
FROM {{ ref('stg_payments') }}
