

  create or replace view `data-engineering-504901`.`staging`.`stg_reviews`
  OPTIONS()
  as SELECT
    review_id,
    order_id,
    SAFE_CAST(review_score AS INT64) AS review_score
FROM `data-engineering-504901`.`staging`.`stg_raw_reviews`;

