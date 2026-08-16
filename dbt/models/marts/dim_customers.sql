{{ config(materialized='table', schema='marts') }}

SELECT
    customer_id,
    customer_city,
    customer_state
FROM {{ ref('stg_customers') }}
