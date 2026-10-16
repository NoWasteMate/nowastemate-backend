from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.firebase import store, firestore
from app.models.Analytics import TrendPeriod, WasteTrend, WasteTrendInformation, WasteRating, WasteScore, WasteScoreSummary
from app.models.Product import ProductOutcome, WasteReason
from app.actions.product_actions import product_actions

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

MIN_MARKED = 5
MIN_ELIGIBLE = 5
SNAPSHOT_MAX_AGE = timedelta(days=1)
DEFAULT_WASTE_RATE = 0.15

AVOIDABLE_REASONS = [
    WasteReason.expired.value,
    WasteReason.forgot.value,
    WasteReason.boughtTooMuch.value,
    WasteReason.storedWrong.value
]

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

    def count_marked_products(self, uid: str):
        consumed = 0
        wasted = 0
        avoidable = 0

        products_ref = (
            store.collection("users")
            .document(uid)
            .collection("products")
        )

        for document in products_ref.stream():
            data = document.to_dict()
            outcome = data.get("outcome", ProductOutcome.active.value)
            reason = data.get("wasteReason")

            if outcome == ProductOutcome.active.value:
                continue
            if reason == WasteReason.addedByMistake.value:
                continue

            if outcome == ProductOutcome.wasted.value:
                wasted += 1
                if reason in AVOIDABLE_REASONS:
                    avoidable += 1
            else:
                consumed += 1

        return consumed, wasted, avoidable

    def get_waste_score(self, uid: str):
        snapshot = self.get_global_snapshot()

        consumed, wasted, avoidable = self.count_marked_products(uid)
        marked = consumed + wasted
        user_score = self.get_score_from_counts(marked, wasted, avoidable, snapshot["userWasteRate"])

        family_score = None
        family_uids = product_actions.get_family_uids(uid)

        # a family score needs 2 or more members
        if family_uids and len(family_uids) > 1:
            family_consumed = 0
            family_wasted = 0
            family_avoidable = 0

            for member in family_uids:
                member_consumed, member_wasted, member_avoidable = self.count_marked_products(member)
                family_consumed += member_consumed
                family_wasted += member_wasted
                family_avoidable += member_avoidable

            family_marked = family_consumed + family_wasted
            family_score = self.get_score_from_counts(family_marked, family_wasted, family_avoidable, snapshot["familyWasteRate"])

        return WasteScoreSummary(user=user_score, family=family_score)

    # rebuilt here until the nightly job exists
    def get_global_snapshot(self):
        document = store.collection("analytics").document("global").get()
        if document.exists:
            snapshot = document.to_dict()
            if datetime.now(timezone.utc) - snapshot["updatedAt"] < SNAPSHOT_MAX_AGE:
                return snapshot
        return self.build_global_snapshot()

    def build_global_snapshot(self):
        user_counts = {}
        user_rates = []

        for user in store.collection("users").stream():
            consumed, wasted, avoidable = self.count_marked_products(user.id)
            marked = consumed + wasted
            user_counts[user.id] = (marked, wasted)

            # pulled toward the default since the real average isn't known yet
            if marked >= MIN_MARKED:
                user_rates.append(self.adjusted_waste_rate(marked, wasted, DEFAULT_WASTE_RATE))

        family_rates = []

        for family in store.collection("family").stream():
            members = family.to_dict().get("members", [])
            if len(members) < 2:
                continue

            family_marked = 0
            family_wasted = 0

            # reuses the user counts so products aren't read twice
            for member in members:
                member_marked, member_wasted = user_counts.get(member, (0, 0))
                family_marked += member_marked
                family_wasted += member_wasted

            if family_marked >= MIN_MARKED:
                family_rates.append(self.adjusted_waste_rate(family_marked, family_wasted, DEFAULT_WASTE_RATE))

        snapshot = {
            "scope": "global",
            "userWasteRate": self.average_waste_rate(user_rates),
            "familyWasteRate": self.average_waste_rate(family_rates),
            "eligibleUsers": len(user_rates),
            "eligibleFamilies": len(family_rates),
            "updatedAt": firestore.SERVER_TIMESTAMP
        }
        store.collection("analytics").document("global").set(snapshot)
        return snapshot

    def average_waste_rate(self, rates: list[float]):
        if len(rates) < MIN_ELIGIBLE:
            return DEFAULT_WASTE_RATE

        average = sum(rates) / len(rates)
        if average == 0:
            return DEFAULT_WASTE_RATE
        return average

    def get_score_from_counts(self, marked: int, wasted: int, avoidable: int, average_rate: float):
        if marked < MIN_MARKED:
            return WasteScore(productsNeeded=MIN_MARKED - marked)
        return self.calculate_waste_score(marked, wasted, avoidable, average_rate)

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
            avoidablePoints=round(avoidable_points),
            wasteRate=wasted / marked
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
