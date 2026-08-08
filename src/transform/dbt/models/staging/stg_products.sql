SELECT
    product_id,
    product_category_name
FROM {{ source('staging', 'stg_raw_products') }}
