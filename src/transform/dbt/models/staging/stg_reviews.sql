SELECT
    review_id,
    order_id,
    review_score
FROM {{ source('raw_data', 'raw_reviews') }}
