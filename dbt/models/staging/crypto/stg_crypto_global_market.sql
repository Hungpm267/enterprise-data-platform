{{
    config(
        materialized='view',
        schema='staging',
        tags=['crypto']
    )
}}

SELECT
    snapshot_id,
    SAFE_CAST(active_cryptocurrencies AS INT64) AS active_cryptocurrencies,
    SAFE_CAST(upcoming_icos AS INT64) AS upcoming_icos,
    SAFE_CAST(ongoing_icos AS INT64) AS ongoing_icos,
    SAFE_CAST(ended_icos AS INT64) AS ended_icos,
    SAFE_CAST(markets AS INT64) AS markets_count,
    SAFE_CAST(total_market_cap_usd AS NUMERIC) AS total_market_cap_usd,
    SAFE_CAST(total_volume_24h_usd AS NUMERIC) AS total_volume_24h_usd,
    SAFE_CAST(btc_dominance_percentage AS FLOAT64) AS btc_dominance_percentage,
    SAFE_CAST(eth_dominance_percentage AS FLOAT64) AS eth_dominance_percentage,
    SAFE_CAST(usdt_dominance_percentage AS FLOAT64) AS usdt_dominance_percentage,
    SAFE_CAST(sol_dominance_percentage AS FLOAT64) AS sol_dominance_percentage,
    SAFE_CAST(market_cap_change_percentage_24h_usd AS FLOAT64) AS market_cap_change_percentage_24h,
    updated_at,
    extracted_at
FROM {{ source('staging', 'stg_raw_crypto_global_market') }}