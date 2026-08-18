import os
import glob
import time
import requests
import pandas as pd
from typing import List, Optional, Dict, Any
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from src.utils.config import Config
from src.utils.logger import logger
from src.utils.timezone import get_vietnam_now
from connectors._base.schemas import RunArgs

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

def get_session_with_retries() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def fetch_top_crypto_markets(api_key: Optional[str] = None) -> pd.DataFrame:
    """
    Fetches Top 100 Cryptocurrencies by market capitalization with real-time price changes.
    API Endpoint: GET /coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=1&sparkline=false&price_change_percentage=1h,24h,7d
    """
    url = f"{COINGECKO_BASE_URL}/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "1h,24h,7d"
    }
    
    headers = {"Accept": "application/json"}
    if api_key:
        headers["x-cg-demo-api-key"] = api_key

    session = get_session_with_retries()
    logger.info(f"Calling CoinGecko API: {url} with params: {params}...")
    
    response = session.get(url, params=params, headers=headers, timeout=20)
    response.raise_for_status()
    
    data = response.json()
    logger.info(f"Successfully received {len(data)} coin records from CoinGecko API.")
    
    records = []
    current_time = get_vietnam_now()
    
    for item in data:
        roi = item.get("roi")
        roi_percentage = roi.get("percentage") if isinstance(roi, dict) else None
        
        record = {
            "coin_id": str(item.get("id", "")),
            "symbol": str(item.get("symbol", "")).upper(),
            "name": str(item.get("name", "")),
            "image_url": str(item.get("image", "")),
            "current_price": float(item.get("current_price") or 0.0),
            "market_cap": float(item.get("market_cap") or 0.0),
            "market_cap_rank": int(item.get("market_cap_rank") or 0),
            "fully_diluted_valuation": float(item.get("fully_diluted_valuation") or 0.0),
            "total_volume": float(item.get("total_volume") or 0.0),
            "high_24h": float(item.get("high_24h") or 0.0),
            "low_24h": float(item.get("low_24h") or 0.0),
            "price_change_24h": float(item.get("price_change_24h") or 0.0),
            "price_change_percentage_24h": float(item.get("price_change_percentage_24h") or 0.0),
            "price_change_percentage_1h_in_currency": float(item.get("price_change_percentage_1h_in_currency") or 0.0),
            "price_change_percentage_24h_in_currency": float(item.get("price_change_percentage_24h_in_currency") or 0.0),
            "price_change_percentage_7d_in_currency": float(item.get("price_change_percentage_7d_in_currency") or 0.0),
            "market_cap_change_24h": float(item.get("market_cap_change_24h") or 0.0),
            "market_cap_change_percentage_24h": float(item.get("market_cap_change_percentage_24h") or 0.0),
            "circulating_supply": float(item.get("circulating_supply") or 0.0),
            "total_supply": float(item.get("total_supply") or 0.0),
            "max_supply": float(item.get("max_supply") or 0.0) if item.get("max_supply") is not None else None,
            "ath": float(item.get("ath") or 0.0),
            "ath_change_percentage": float(item.get("ath_change_percentage") or 0.0),
            "ath_date": pd.to_datetime(item.get("ath_date")) if item.get("ath_date") else None,
            "atl": float(item.get("atl") or 0.0),
            "atl_change_percentage": float(item.get("atl_change_percentage") or 0.0),
            "atl_date": pd.to_datetime(item.get("atl_date")) if item.get("atl_date") else None,
            "roi_percentage": float(roi_percentage) if roi_percentage is not None else None,
            "last_updated": pd.to_datetime(item.get("last_updated")) if item.get("last_updated") else current_time,
            "extracted_at": current_time
        }
        records.append(record)
        
    df = pd.DataFrame(records)
    return df

def fetch_global_crypto_market(api_key: Optional[str] = None) -> pd.DataFrame:
    """
    Fetches global crypto market overview (active cryptos, total market cap, 24h volume, dominance).
    API Endpoint: GET /global
    """
    url = f"{COINGECKO_BASE_URL}/global"
    headers = {"Accept": "application/json"}
    if api_key:
        headers["x-cg-demo-api-key"] = api_key

    session = get_session_with_retries()
    logger.info(f"Calling CoinGecko Global API: {url}...")
    
    response = session.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    
    data = response.json().get("data", {})
    current_time = get_vietnam_now()
    
    total_market_cap_usd = float(data.get("total_market_cap", {}).get("usd", 0.0))
    total_volume_usd = float(data.get("total_volume", {}).get("usd", 0.0))
    market_cap_percentage = data.get("market_cap_percentage", {})
    
    record = {
        "snapshot_id": f"global_{int(current_time.timestamp())}",
        "active_cryptocurrencies": int(data.get("active_cryptocurrencies", 0)),
        "upcoming_icos": int(data.get("upcoming_icos", 0)),
        "ongoing_icos": int(data.get("ongoing_icos", 0)),
        "ended_icos": int(data.get("ended_icos", 0)),
        "markets": int(data.get("markets", 0)),
        "total_market_cap_usd": total_market_cap_usd,
        "total_volume_24h_usd": total_volume_usd,
        "btc_dominance_percentage": float(market_cap_percentage.get("btc", 0.0)),
        "eth_dominance_percentage": float(market_cap_percentage.get("eth", 0.0)),
        "usdt_dominance_percentage": float(market_cap_percentage.get("usdt", 0.0)),
        "sol_dominance_percentage": float(market_cap_percentage.get("sol", 0.0)),
        "market_cap_change_percentage_24h_usd": float(data.get("market_cap_change_percentage_24h_usd", 0.0)),
        "updated_at": pd.to_datetime(data.get("updated_at"), unit="s") if data.get("updated_at") else current_time,
        "extracted_at": current_time
    }
    
    df = pd.DataFrame([record])
    return df

def extract_crypto_tables(args: RunArgs) -> List[str]:
    api_key = os.getenv("COINGECKO_API_KEY")
    target_dir = os.path.join(Config.LANDING_DIR, "crypto_api")
    os.makedirs(target_dir, exist_ok=True)
    
    extracted_files = []
    
    # 1. Extract Top 100 Coins Market Data
    try:
        df_coins = fetch_top_crypto_markets(api_key=api_key)
        coins_path = os.path.join(target_dir, "crypto_market_coins.parquet")
        df_coins.to_parquet(coins_path, index=False)
        logger.info(f"Saved: {coins_path} ({len(df_coins)} rows)")
        extracted_files.append(coins_path)
    except Exception as e:
        logger.error(f"Error fetching crypto markets: {e}")
        raise e

    # Small delay between public API calls to prevent 429
    time.sleep(1.5)

    # 2. Extract Global Market Snapshot
    try:
        df_global = fetch_global_crypto_market(api_key=api_key)
        global_path = os.path.join(target_dir, "crypto_global_market.parquet")
        df_global.to_parquet(global_path, index=False)
        logger.info(f"Saved: {global_path} ({len(df_global)} rows)")
        extracted_files.append(global_path)
    except Exception as e:
        logger.error(f"Error fetching global crypto market: {e}")
        raise e

    logger.info(f"Crypto API extraction completed. {len(extracted_files)} files in landing zone.")
    return extracted_files