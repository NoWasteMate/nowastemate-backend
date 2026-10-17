from fastapi import APIRouter, Depends, Query

from app.models.Analytics import TrendPeriod, WasteTrend, WasteScoreSummary, ProductUsage
from app.actions.authorization_actions import authorization_actions
from app.actions.analytics_actions import analytics_actions

from typing import Optional

router = APIRouter()

# returns wasted/consumed counts per week or month for the signed-in user
# query param validation: https://fastapi.tiangolo.com/tutorial/query-params-str-validations/
@router.get("/analytics/wasteTrend", tags=['Analytics'], response_model=WasteTrend)
def get_waste_trend(
    period: TrendPeriod = TrendPeriod.week,
    periods: int = Query(6, ge=1, le=24),
    user = Depends(authorization_actions.verify_user_token)
):
    return analytics_actions.get_waste_trend(user["uid"], period, periods)

@router.get("/analytics/wasteScore", tags=['Analytics'], response_model=WasteScoreSummary)
def get_waste_score(user = Depends(authorization_actions.verify_user_token)):
    return analytics_actions.get_waste_score(user["uid"])

# returns consumed / usedInRecipe / wasted counts for the signed-in user; no days means all time
@router.get("/analytics/productUsage", tags=['Analytics'], response_model=ProductUsage)
def product_usage_overview(days: Optional[int] = Query(None, ge=1, le=3650), user = Depends(authorization_actions.verify_user_token)):
    return analytics_actions.get_product_usage_overview(user["uid"], days)

#https://realpython.com/python-optional-arguments/
#https://fastapi.tiangolo.com/tutorial/query-params/
@router.get("/analytics/categoryWaste", tags=['Analytics'])
def categories_wasted(familyId: str = "", user = Depends(authorization_actions.verify_user_token)):
    return analytics_actions.get_categories_wasted(user["uid"], familyId)
