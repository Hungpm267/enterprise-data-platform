{{
    config(
        materialized='incremental',
        schema='marts',
        tags=['crypto'],
        unique_key='metric_id',
        incremental_strategy='merge',
        partition_by={
            "field": "recorded_at",
            "data_type": "timestamp",
            "granularity": "day"
        },
        cluster_by=["coin_id", "market_cap_rank"]
    )
}}

WITH source_data AS (
    SELECT
        FARM_FINGERPRINT(CONCAT(coin_id, CAST(last_updated AS STRING))) AS metric_id,
        coin_id,
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
        last_updated AS recorded_at,
        extracted_at
    FROM {{ ref('stg_crypto_market_coins') }}
)

SELECT * FROM source_data
{% if is_incremental() %}
    WHERE recorded_at > (SELECT MAX(recorded_at) FROM {{ this }})
{% endif %}