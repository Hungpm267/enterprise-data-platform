{{ config(materialized='table', schema='marts') }}

SELECT
    tenant_slug,
    customer_id,
    customer_city,
    customer_state
FROM {{ ref('stg_customers') }}
