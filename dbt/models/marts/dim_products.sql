{{ config(materialized='table', schema='marts') }}

SELECT
    product_id,
    product_category_name
FROM {{ ref('stg_products') }}
