from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.firebase import store, firestore
from app.models.Analytics import TrendPeriod, WasteTrend, WasteTrendInformation, WasteRating, WasteScore, WasteScoreSummary
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

MIN_MARKED = 5
MIN_ELIGIBLE = 5
SNAPSHOT_MAX_AGE = timedelta(days=1)
DEFAULT_WASTE_RATE = 0.15
# Based on the share of household food waste that could have been eaten
DEFAULT_AVOIDABLE_SHARE = 0.63

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

    # counts are rebuilt from products each time instead of kept as counters
    def refresh_user_counts(self, uid: str):
        consumed, wasted, avoidable = self.count_marked_products(uid)
        marked = consumed + wasted

        counts = {
            "marked": marked,
            "wasted": wasted,
            "avoidableWasted": avoidable,
            "updatedAt": firestore.SERVER_TIMESTAMP
        }

        store.collection("users").document(uid).update({"wasteCounts": counts})
        return counts

    def get_user_counts(self, uid: str, user: dict):
        counts = user.get("wasteCounts")
        if counts is None:
            # users who haven't marked anything since wasteCounts was added
            counts = self.refresh_user_counts(uid)
        return counts

    def get_waste_score(self, uid: str):
        snapshot = self.get_global_snapshot()

        user = store.collection("users").document(uid).get().to_dict() or {}
        user_counts = self.get_user_counts(uid, user)
        marked = user_counts["marked"]
        wasted = user_counts["wasted"]
        avoidable = user_counts["avoidableWasted"]
        user_score = self.get_score_from_counts(marked, wasted, avoidable, snapshot["userWasteRate"])
        user_score.averageScore = snapshot["userAverageScore"]

        family_score = None
        family_id = user.get("familyId")

        members = []
        if family_id:
            family = store.collection("family").document(family_id).get()
            if family.exists:
                members = family.to_dict().get("members", [])

        # a family score needs 2 or more members
        # family counts aren't stored, they're added up from the current members like family products
        if len(members) > 1:
            family_marked = 0
            family_wasted = 0
            family_avoidable = 0

            for member in members:
                member_user = store.collection("users").document(member).get().to_dict() or {}
                member_counts = self.get_user_counts(member, member_user)
                family_marked += member_counts["marked"]
                family_wasted += member_counts["wasted"]
                family_avoidable += member_counts["avoidableWasted"]

            family_score = self.get_score_from_counts(family_marked, family_wasted, family_avoidable, snapshot["familyWasteRate"])
            family_score.averageScore = snapshot["familyAverageScore"]

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
        eligible_users = []

        for user in store.collection("users").stream():
            consumed, wasted, avoidable = self.count_marked_products(user.id)
            marked = consumed + wasted
            user_counts[user.id] = (marked, wasted, avoidable)

            if marked >= MIN_MARKED:
                eligible_users.append((marked, wasted, avoidable))

        eligible_families = []

        for family in store.collection("family").stream():
            members = family.to_dict().get("members", [])
            if len(members) < 2:
                continue

            family_marked = 0
            family_wasted = 0
            family_avoidable = 0

            # reuses the user counts so products aren't read twice
            for member in members:
                member_marked, member_wasted, member_avoidable = user_counts.get(member, (0, 0, 0))
                family_marked += member_marked
                family_wasted += member_wasted
                family_avoidable += member_avoidable

            if family_marked >= MIN_MARKED:
                eligible_families.append((family_marked, family_wasted, family_avoidable))

        user_rate = self.average_waste_rate(eligible_users)
        family_rate = self.average_waste_rate(eligible_families)

        snapshot = {
            "userWasteRate": user_rate,
            "familyWasteRate": family_rate,
            "userAverageScore": self.average_waste_score(eligible_users, user_rate),
            "familyAverageScore": self.average_waste_score(eligible_families, family_rate),
            "eligibleUsers": len(eligible_users),
            "eligibleFamilies": len(eligible_families),
            "updatedAt": firestore.SERVER_TIMESTAMP
        }
        store.collection("analytics").document("global").set(snapshot)
        return snapshot

    def average_waste_rate(self, eligible: list[tuple]):
        if len(eligible) < MIN_ELIGIBLE:
            return DEFAULT_WASTE_RATE

        rates = []
        for marked, wasted, avoidable in eligible:
            # pulled toward the default since the real average isn't known yet
            rates.append(self.adjusted_waste_rate(marked, wasted, DEFAULT_WASTE_RATE))

        average = sum(rates) / len(rates)
        if average == 0:
            return DEFAULT_WASTE_RATE
        return average

    def average_waste_score(self, eligible: list[tuple], average_rate: float):
        if len(eligible) < MIN_ELIGIBLE:
            return self.default_average_score()

        scores = []
        for marked, wasted, avoidable in eligible:
            scores.append(self.calculate_waste_score(marked, wasted, avoidable, average_rate).score)

        return round(sum(scores) / len(scores))

    # someone wasting exactly the default rate gets half the waste-rate points
    def default_average_score(self):
        avoidable_share = DEFAULT_WASTE_RATE * DEFAULT_AVOIDABLE_SHARE
        return round(WASTE_RATE_POINTS / 2 + AVOIDABLE_POINTS * (1 - avoidable_share))

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
