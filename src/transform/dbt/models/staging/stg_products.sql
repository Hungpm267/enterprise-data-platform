SELECT
    product_id,
    product_category_name
FROM {{ source('raw_data', 'raw_products') }}
