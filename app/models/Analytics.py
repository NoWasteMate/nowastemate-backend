from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional

from app.models.Product import WasteReason

# Waste Trends Model

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


# Product Usage Model
# reference: https://docs.pydantic.dev/latest/api/fields/#pydantic.fields.Field
class ProductUsage(BaseModel):
    days: Optional[int] = None
    consumedCount: int = 0
    usedInRecipeCount: int = 0
    wastedCount: int = 0
    byReason: dict[WasteReason, int] = Field(default_factory=dict)
