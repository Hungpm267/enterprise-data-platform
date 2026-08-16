from abc import ABC, abstractmethod
from typing import List
from connectors._base.schemas import RunArgs

class BaseConnector(ABC):
    """
    Abstract Base Class defining the standard contract for all platform data connectors.
    """
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def extract(self, args: RunArgs) -> List[str]:
        """
        Extract raw data from source system and save as Parquet files in the local landing zone.
        Returns a list of generated file paths.
        """
        pass

    def run(self, args: RunArgs) -> List[str]:
        """
        Standard execution entry point for the connector.
        """
        return self.extract(args)