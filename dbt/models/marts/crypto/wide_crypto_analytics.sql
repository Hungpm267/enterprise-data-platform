{{
    config(
        materialized='view',
        schema='marts',
        tags=['crypto']
    )
}}

SELECT
    -- Fact Metrics
    f.metric_id,
    f.recorded_at,
    f.market_cap_rank,
    f.current_price_usd,
    f.market_cap_usd,
    f.fully_diluted_valuation_usd,
    f.total_volume_24h_usd,
    f.high_24h_usd,
    f.low_24h_usd,
    f.price_change_percentage_1h,
    f.price_change_percentage_24h,
    f.price_change_percentage_7d,
    f.roi_percentage,

    -- Dimension Attributes
    d.coin_id,
    d.symbol,
    d.name AS coin_name,
    d.image_url,
    d.circulating_supply,
    d.total_supply,
    d.max_supply,
    d.ath_usd,
    d.ath_change_percentage,
    d.ath_date,
    d.atl_usd,
    d.atl_change_percentage,
    d.atl_date
FROM {{ ref('fct_crypto_market_metrics') }} f
LEFT JOIN {{ ref('dim_crypto_coins') }} d
    ON f.coin_id = d.coin_id