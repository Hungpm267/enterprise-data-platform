{{ config(materialized='table', schema='marts') }}

SELECT
    tenant_slug,
    product_id,
    product_category_name
FROM {{ ref('stg_products') }}
