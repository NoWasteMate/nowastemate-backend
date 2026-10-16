from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.firebase import store
from app.models.Analytics import TrendPeriod, WasteTrend, WasteTrendInformation, ProductUsage
from app.models.Product import ProductOutcome, WasteReason

from typing import Optional

# references
# https://docs.python.org/3/library/zoneinfo.html
# https://docs.python.org/3/library/datetime.html#aware-and-naive-objects
# https://docs.python.org/3/library/datetime.html#datetime.datetime.astimezone
# https://docs.python.org/3/library/datetime.html#datetime.date.weekday
# https://docs.python.org/3/library/datetime.html#timedelta-objects

# outcomes need to count as a finished product, active is left out
finished_outcomes = {
    ProductOutcome.consumed.value,
    ProductOutcome.usedInRecipe.value,
    ProductOutcome.wasted.value,
}

# Group by Toronto time so Sunday-evening / month-end items land in the right bar
ZONE = ZoneInfo("America/Toronto")

class AnalyticsActions:

    # Waste Trend methods section
    # start of the week (Monday 00:00) or month (1st 00:00) that a moment falls in, Toronto time
    def period_start(self, moment: datetime, period: TrendPeriod) -> datetime:
        local = moment.astimezone(ZONE)

        if period == TrendPeriod.week:
            monday = local.date() - timedelta(days=local.weekday())
            return datetime(monday.year, monday.month, monday.day, tzinfo=ZONE)

        return datetime(local.year, local.month, 1, tzinfo=ZONE)

    # moves a period start n weeks/months back
    def step_back(self, start: datetime, period: TrendPeriod, n: int) -> datetime:
        if period == TrendPeriod.week:
            day = start.date() - timedelta(weeks=n)
            return datetime(day.year, day.month, day.day, tzinfo=ZONE)

        month_index = start.year * 12 + (start.month - 1) - n
        return datetime(month_index // 12, month_index % 12 + 1, 1, tzinfo=ZONE)

    def get_waste_trend(self, uid: str, period: TrendPeriod, periods: int) -> WasteTrend:

        # every information group in the range, oldest first, so the chart has no gaps
        current_start = self.period_start(datetime.now(timezone.utc), period)
        starts = [self.step_back(current_start, period, n) for n in range(periods - 1, -1, -1)]
        buckets = {start: WasteTrendInformation(periodStart=start) for start in starts}

        products_ref = (
            store.collection("users")
            .document(uid)
            .collection("products")
        )

        for document in products_ref.stream():
            data = document.to_dict()
            outcome = data.get("outcome", ProductOutcome.active.value)
            outcome_at = data.get("outcomeAt")

            # active products and legacy products without outcomeAt are skipped
            if outcome == ProductOutcome.active.value or outcome_at is None:
                continue

            # older than the range (or in the future) has no bucket
            bucket = buckets.get(self.period_start(outcome_at, period))
            if bucket is None:
                continue

            if outcome == ProductOutcome.wasted.value:
                bucket.wastedCount += 1
                reason = data.get("wasteReason")
                if reason:
                    bucket.byReason[WasteReason(reason)] = bucket.byReason.get(WasteReason(reason), 0) + 1
            else:
                # consumed and usedInRecipe both count as consumed
                bucket.consumedCount += 1
        
        return WasteTrend(period=period, buckets=list(buckets.values()))

    def get_product_usage_overview(self, uid: str, days: Optional[int]) -> ProductUsage:

        # the cutoff time for when products finished at or after since are counted
        since = datetime.now(timezone.utc) - timedelta(days=days) if days is not None else None

        usage = ProductUsage(days=days)

        products_ref = (
            store.collection("users") 
            .document(uid) 
            .collection("products")
        )

        for document in products_ref.stream():
            data = document.to_dict()
            outcome = data.get("outcome", ProductOutcome.active.value)
            outcome_at = data.get("outcomeAt")
            reason = data.get("wasteReason")

            # active products are not finished yet
            if outcome not in finished_outcomes:
                continue

            # added by mistake was never real food so it doesn't count
            if reason == WasteReason.addedByMistake.value:
                continue

            # finding a specific timestamp for that time window
            if since is not None and (outcome_at is None or outcome_at < since):
                continue

            if outcome == ProductOutcome.consumed.value:
                usage.consumedCount += 1
            elif outcome == ProductOutcome.usedInRecipe.value:
                # only stored outcomes count, generated recipes never do
                usage.usedInRecipeCount += 1 
            else:
                usage.wastedCount += 1

                if reason: 
                    usage.byReason[WasteReason(reason)] = usage.byReason.get(WasteReason(reason), 0) + 1

        return usage

        

analytics_actions = AnalyticsActions()