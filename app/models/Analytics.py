from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

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
    wasteRate: Optional[float] = None
    # shown in the app so the parts read as facts ("7 of 27 wasted items were preventable")
    wasted: Optional[int] = None
    avoidableWasted: Optional[int] = None
    averageWasteRate: Optional[float] = None
    averageScore: Optional[int] = None
    productsNeeded: int = 0

class WasteScoreSummary(BaseModel):
    user: WasteScore
    family: Optional[WasteScore] = None

# Product Usage Model
# reference: https://docs.pydantic.dev/latest/api/fields/#pydantic.fields.Field
class ProductUsage(BaseModel):
    days: Optional[int] = None
    consumedCount: int = 0
    usedInRecipeCount: int = 0
    wastedCount: int = 0
    byReason: dict[WasteReason, int] = Field(default_factory=dict)
