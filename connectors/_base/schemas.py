from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

from src.utils.config import Config

class RunMode(str, Enum):
    INCREMENTAL = "incremental"
    FULL_REFRESH = "full_refresh"

class RunArgs(BaseModel):
    start_date: Optional[str] = Field(default=None, description="Start date filter (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="End date filter (YYYY-MM-DD)")
    mode: RunMode = Field(default=RunMode.INCREMENTAL, description="Execution mode (incremental vs full_refresh)")
    tables: Optional[List[str]] = Field(default=None, description="Specific tables to extract")
    clean_landing: bool = Field(default=True, description="Whether to clear landing zone before extract")
    tenant_slug: str = Field(
        default_factory=lambda: Config.DEFAULT_TENANT_SLUG,
        description="Tenant identifier stamped onto every extracted row"
    )