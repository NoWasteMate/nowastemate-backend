from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

from app.models.Product import WasteReason

class TrendPeriod(str, Enum):
    week = "week"
    month = "month"

class WasteTrendInformation(BaseModel):
    periodStart: datetime
    wastedCount: int = 0
    consumedCount: int = 0
    byReason: dict[WasteReason, int] = Field(default_factory=dict)

class WasteTrend(BaseModel):
    period: TrendPeriod
    buckets: list[WasteTrendInformation]