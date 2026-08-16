SELECT
    review_id,
    order_id,
    SAFE_CAST(review_score AS INT64) AS review_score
FROM {{ source('staging', 'stg_raw_reviews') }}
