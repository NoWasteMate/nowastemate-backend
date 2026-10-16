from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.firebase import store
from app.models.Analytics import TrendPeriod, WasteTrend, WasteTrendInformation, WasteRating, WasteScore
from app.models.Product import ProductOutcome, WasteReason

# references
# https://docs.python.org/3/library/zoneinfo.html
# https://docs.python.org/3/library/datetime.html#aware-and-naive-objects
# https://docs.python.org/3/library/datetime.html#datetime.datetime.astimezone
# https://docs.python.org/3/library/datetime.html#datetime.date.weekday
# https://docs.python.org/3/library/datetime.html#timedelta-objects

# Group by Toronto time so Sunday-evening / month-end items land in the right bar
ZONE = ZoneInfo("America/Toronto")

WASTE_RATE_POINTS = 60
AVOIDABLE_POINTS = 40

# Our chosen weight: 10 products at the average rate
BAYESIAN_WEIGHT = 10

class AnalyticsActions:

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

    # average_rate must be above 0
    def calculate_waste_score(self, marked: int, wasted: int, avoidable: int, average_rate: float):
        waste_rate = self.adjusted_waste_rate(marked, wasted, average_rate)

        waste_rate_points = WASTE_RATE_POINTS * (1 - waste_rate / (2 * average_rate))
        waste_rate_points = max(0, min(waste_rate_points, WASTE_RATE_POINTS))

        avoidable_points = AVOIDABLE_POINTS * (1 - avoidable / marked)

        # rounded once so the score matches the exact parts
        score = round(waste_rate_points + avoidable_points)

        return WasteScore(
            score=score,
            rating=self.get_waste_rating(score),
            wasteRatePoints=round(waste_rate_points),
            avoidablePoints=round(avoidable_points)
        )

    # Adapts the Bayesian average documented for predictive waste risk to the Waste Score
    # https://nowastemate.atlassian.net/wiki/spaces/NWM/pages/115376129
    # https://www.algolia.com/doc/guides/managing-results/must-do/custom-ranking/how-to/bayesian-average
    def adjusted_waste_rate(self, marked: int, wasted: int, average_rate: float):
        return (BAYESIAN_WEIGHT * average_rate + wasted) / (BAYESIAN_WEIGHT + marked)

    def get_waste_rating(self, score: int):
        # Thresholds follow Apple Watch Sleep Score bands
        if score <= 40:
            return WasteRating.needsWork
        if score <= 60:
            return WasteRating.fair
        if score <= 80:
            return WasteRating.good
        if score <= 95:
            return WasteRating.great
        return WasteRating.excellent

analytics_actions = AnalyticsActions()
