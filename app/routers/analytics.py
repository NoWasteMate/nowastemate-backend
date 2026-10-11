from fastapi import APIRouter, Depends, Query

from app.models.Analytics import TrendPeriod, WasteTrend
from app.actions.authorization_actions import authorization_actions
from app.actions.analytics_actions import analytics_actions

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