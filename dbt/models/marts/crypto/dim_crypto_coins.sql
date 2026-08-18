{{
    config(
        materialized='table',
        cluster_by=["symbol", "coin_id"]
    )
}}

SELECT
    coin_id,
    symbol,
    name,
    image_url,
    circulating_supply,
    total_supply,
    max_supply,
    ath_usd,
    ath_change_percentage,
    ath_date,
    atl_usd,
    atl_change_percentage,
    atl_date
FROM {{ ref('stg_crypto_market_coins') }}