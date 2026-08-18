from typing import List
from connectors._base.base_connector import BaseConnector
from connectors._base.schemas import RunArgs
from connectors.crypto_api.extract import extract_crypto_tables

class CryptoConnector(BaseConnector):
    """
    CoinGecko Crypto Market REST API Source Connector.
    Extracts Top 100 Cryptocurrencies and Global Market Snapshot.
    """
    def __init__(self):
        super().__init__(name="crypto_api")

    def extract(self, args: RunArgs) -> List[str]:
        return extract_crypto_tables(args)