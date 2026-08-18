{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        unique_key=['metric_id'],
        partition_by={
            "field": "recorded_at",
            "data_type": "timestamp",
            "granularity": "day"
        },
        cluster_by=["coin_id", "market_cap_rank"]
    )
}}

SELECT
    FARM_FINGERPRINT(CONCAT(coin_id, '_', CAST(last_updated AS STRING))) AS metric_id,
    coin_id,
    symbol,
    market_cap_rank,
    current_price_usd,
    market_cap_usd,
    fully_diluted_valuation_usd,
    total_volume_24h_usd,
    high_24h_usd,
    low_24h_usd,
    price_change_24h_usd,
    price_change_percentage_24h,
    price_change_percentage_1h,
    price_change_percentage_7d,
    roi_percentage,
    last_updated AS recorded_at
FROM {{ ref('stg_crypto_market_coins') }}
{% if is_incremental() %}
    WHERE last_updated >= TIMESTAMP_SUB(
        (SELECT COALESCE(MAX(recorded_at), TIMESTAMP('1970-01-01')) FROM {{ this }}),
        INTERVAL 1 DAY
    )
{% endif %}