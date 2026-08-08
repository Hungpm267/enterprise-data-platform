{{ config(materialized='table') }}

SELECT
    product_id,
    product_category_name,
    SAFE_CAST(product_name_lenght AS INT64) AS product_name_length,
    SAFE_CAST(product_description_lenght AS INT64) AS product_description_length,
    SAFE_CAST(product_photos_qty AS INT64) AS product_photos_qty,
    SAFE_CAST(product_weight_g AS FLOAT64) AS product_weight_g
FROM {{ source('staging', 'stg_raw_products') }}
