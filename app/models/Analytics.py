from pydantic import BaseModel, Field
from typing import Optional
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

class WasteRating(str, Enum):
    needsWork = "needsWork"
    fair = "fair"
    good = "good"
    great = "great"
    excellent = "excellent"

# score fields stay None until productsNeeded reaches 0
class WasteScore(BaseModel):
    score: Optional[int] = None
    rating: Optional[WasteRating] = None
    wasteRatePoints: Optional[int] = None
    avoidablePoints: Optional[int] = None
    # not shown in the app yet, kept for future analytics
    wasteRate: Optional[float] = None
    productsNeeded: int = 0

class WasteScoreSummary(BaseModel):
    user: WasteScore
    family: Optional[WasteScore] = None

