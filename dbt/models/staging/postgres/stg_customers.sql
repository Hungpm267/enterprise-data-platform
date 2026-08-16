SELECT
    customer_id,
    customer_city,
    customer_state
FROM {{ source('staging', 'stg_raw_customers') }}
