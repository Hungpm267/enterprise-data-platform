SELECT
    customer_id,
    customer_city,
    customer_state
FROM {{ source('raw_data', 'raw_customers') }}
