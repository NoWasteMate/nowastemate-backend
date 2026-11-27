from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.firebase import store, firestore
from app.models.Analytics import TrendPeriod, WasteTrend, WasteTrendInformation, WasteRating, WasteScore, WasteScoreSummary, ProductUsage, WasteRisk
from app.models.Product import ProductOutcome, WasteReason
from app.models.ProduceItem import ProduceItem
from app.actions.family_actions import family_actions

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

# Our chosen cutoffs in days left before expiry
HIGH_RISK_DAYS = 2
MEDIUM_RISK_DAYS = 5
# Our chosen rule for an often wasted category: well above the user's own waste rate
CATEGORY_ABOVE_AVERAGE_FACTOR = 1.5
# and high enough to matter, so careful users aren't flagged over small numbers
CATEGORY_MIN_WASTE_PERCENT = 25

AVOIDABLE_REASONS = [
    WasteReason.expired.value,
    WasteReason.forgot.value,
    WasteReason.boughtTooMuch.value,
    WasteReason.storedWrong.value
]

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

    # getting family uids function
    def get_scope_uids(self, uid: str, family: bool) -> list[str]:
        if not family:
            return [uid]

        uids = family_actions.get_family_uids(uid)

        if uids is None or len(uids) < 2:
            raise HTTPException(status_code=404, detail="User does not have a family")
        return uids

    def get_waste_trend(self, uid: str, period: TrendPeriod, periods: int, family: bool = False) -> WasteTrend:

        uids = self.get_scope_uids(uid, family)

        # every information group in the range, oldest first, so the chart has no gaps
        current_start = self.period_start(datetime.now(timezone.utc), period)
        starts = [self.step_back(current_start, period, n) for n in range(periods - 1, -1, -1)]
        buckets = {start: WasteTrendInformation(periodStart=start) for start in starts}

        for member in uids:
            products_ref = (
                store.collection("users")
                .document(member)
                .collection("products")
            )

            for document in products_ref.stream():
                data = document.to_dict()
                outcome = data.get("outcome", ProductOutcome.active.value)
                outcome_at = data.get("outcomeAt")
                reason = data.get("wasteReason")

                # a finished product counts as its quantity
                items = data.get("quantity") or 1

                # active products and legacy products without outcomeAt are skipped
                if outcome == ProductOutcome.active.value or outcome_at is None:
                    continue

                # added by mistake doesn't count
                if reason == WasteReason.addedByMistake.value:
                    continue

                # older than the range (or in the future) has no bucket
                bucket = buckets.get(self.period_start(outcome_at, period))
                if bucket is None:
                    continue

                if outcome == ProductOutcome.wasted.value:
                    bucket.wastedCount += items
                    #reason = data.get("wasteReason")
                    if reason:
                        bucket.byReason[WasteReason(reason)] = bucket.byReason.get(WasteReason(reason), 0) + items
                else:
                    # consumed and usedInRecipe both count as consumed
                    bucket.consumedCount += items

        return WasteTrend(period=period, buckets=list(buckets.values()))

    def get_categories_wasted(self, uid: str,familyId: str = ""):

        category_products = []


        #user scenario
        if familyId == "":
            products_ref = (
                store.collection("users")
                .document(uid)
                .collection("products")
                )

            products_document = products_ref.stream()


            for document in products_document:
                data = document.to_dict()
                #we only want products either consumed or wasted, as this is historical
                if data.get("wasteReason") != "addedByMistake" and data.get("outcome") != "active":
                        category_products.append(data)
        #family scenario
        else:
            user_doc_ref = store.collection("users").document(uid)

            user_check = user_doc_ref.get()
            #https://stackoverflow.com/questions/51483234/how-to-know-if-document-exists-in-firestore-python
            if not user_check.exists:
                return "error"

            user_doc = user_check.to_dict()

            fam_id = user_doc["familyId"]

            fam_doc_ref = store.collection("family").document(fam_id)

            family = fam_doc_ref.get()

            family = family.to_dict()
            #same procedure as the user scenario, but we instead iterate through each family member
            for i in family["members"]:
                products_ref = (
                store.collection("users")
                .document(i)
                .collection("products")
                )
                products_document = products_ref.stream()
                for document in products_document:
                    data = document.to_dict()

                    if data.get("wasteReason") != "addedByMistake" and data.get("outcome") != "active":
                            category_products.append(data)
        #for later calc
        result = {}

        #overall products logged both consumed and wasted
        overall = {}
        #only wasted
        wasted = {}

        #https://www.geeksforgeeks.org/python/python-increment-value-in-dictionary/
        #looping through all the products, each time it will add one to the overall, and one to wasted if it is wasted
        for i in category_products:

            current_category = i.get("category")
            # found while reusing this for waste risk: a product without a category crashed here with a KeyError
            if current_category is None:
                continue
            # a finished product counts as its quantity
            items = i.get("quantity") or 1
            #add 1 to the overall no matter what
            overall[current_category] = overall.get(current_category, 0) + items
            #also add 1 to the wasted amount if product was wasted
            if i.get("outcome") == "wasted":
                wasted[current_category] = wasted.get(current_category, 0) + items

        #https://www.geeksforgeeks.org/python/iterate-over-a-dictionary-in-python/
        #we need to check that the key exists in cases where there
        #we take amount of wasted items, divide by total number of items, then multiply by 100 to represent the percentage
        for key, value in overall.items():
            result[key] =  round(wasted.get(key, 0) / value * 100, 1)

        return result











    def get_product_usage_overview(self, uid: str, days: Optional[int], family: bool = False) -> ProductUsage:

        # the cutoff time for when products finished at or after since are counted
        since = datetime.now(timezone.utc) - timedelta(days=days) if days is not None else None

        # checking if the user is a part of a family
        uids = self.get_scope_uids(uid, family)

        usage = ProductUsage(days=days)

        # products_ref = (
        #     store.collection("users")
        #     .document(uid)
        #     .collection("products")
        # )

        for member in uids:
            products_ref = (
                store.collection("users")
                .document(member)
                .collection("products")
            )

            for document in products_ref.stream():
                data = document.to_dict()
                outcome = data.get("outcome", ProductOutcome.active.value)
                outcome_at = data.get("outcomeAt")
                reason = data.get("wasteReason")
                items = data.get("quantity" or 1)

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
                    usage.consumedCount += items
                elif outcome == ProductOutcome.usedInRecipe.value:
                    # only stored outcomes count, generated recipes never do
                    usage.usedInRecipeCount += items
                else:
                    usage.wastedCount += items

                    if reason:
                        usage.byReason[WasteReason(reason)] = usage.byReason.get(WasteReason(reason), 0) + items

        return usage



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
            items = data.get("quantity") or 1

            if outcome == ProductOutcome.active.value:
                continue
            if reason == WasteReason.addedByMistake.value:
                continue

            if outcome == ProductOutcome.wasted.value:
                wasted += items
                if reason in AVOIDABLE_REASONS:
                    avoidable += items
            else:
                consumed += items

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
        user_score.averageWasteRate = snapshot["userWasteRate"]

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
            family_score.averageWasteRate = snapshot["familyWasteRate"]

        return WasteScoreSummary(user=user_score, family=family_score)

    def get_family_leaderboard(self, uid: str):
        snapshot = self.get_global_snapshot()
        user = store.collection("users").document(uid).get().to_dict() or {}
        family_id = user.get("familyId")
        members = []

        result = []

        if family_id:
            family = store.collection("family").document(family_id).get()
            if family.exists:
                members = family.to_dict().get("members", [])

                for member in members:
                    #setup
                    member_result = {}
                    member_marked = 0
                    member_wasted = 0
                    member_avoidable = 0
                    member_score = None

                    member_user = store.collection("users").document(member).get().to_dict() or {}
                    first = member_user["firstName"]
                    last = member_user["lastName"]

                    member_counts = self.get_user_counts(member, member_user)
                    member_marked = member_counts["marked"]
                    member_wasted = member_counts["wasted"]
                    member_avoidable = member_counts["avoidableWasted"]
                    member_score = self.get_score_from_counts(member_marked, member_wasted, member_avoidable, snapshot["userWasteRate"])

                    member_result["id"] = member
                    member_result["firstName"] = first
                    member_result["lastName"] = last
                    member_result["score"] = member_score.score

                    result.append(member_result)

                return result
        else:
            return []


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
            wasteRate=wasted / marked,
            wasted=wasted,
            avoidableWasted=avoidable
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
    
    #ref https://firebase.google.com/docs/firestore/manage-data/add-data#python_14
    def post_picked_produce(self, uid: str, produceItem: ProduceItem):
        #navigate to the specific predicted item, autocreates if missing
        doc_ref = store.collection("analytics").document("produceList").collection(produceItem.predictedProduce)
        #set up object to add
        #track user and timestamps
        #this way we can filter after a period where we made a fix, or filter out/delete any bad data inserted by a specific user
        obj = {
                    "chosenProduce": produceItem.chosenProduce,
                    "createdAt": firestore.SERVER_TIMESTAMP,
                    "createdBy": uid
        }
        #add to collection
        doc_ref.add(obj)

        return {"success": "Entry added"}




    # Waste Risk methods section
    def calculate_product_waste_risk(self, product: dict):
        date_expiration = product.get("dateExpiration")
        # no date to compare against yet
        if date_expiration is None:
            return WasteRisk.low

        # .days drops the leftover hours, 1 day 23 hours is 1
        # https://docs.python.org/3/library/datetime.html#timedelta-objects
        time_until_expiry = date_expiration - datetime.now(timezone.utc)
        days_until_expiry = time_until_expiry.days

        # expired products have negative days and count as high
        if days_until_expiry <= HIGH_RISK_DAYS:
            return WasteRisk.high
        if days_until_expiry <= MEDIUM_RISK_DAYS:
            return WasteRisk.medium
        return WasteRisk.low

    def get_waste_risks(self, uid: str, family: bool = False):
        uids = self.get_scope_uids(uid, family)
        risks = []

        for member in uids:
            category_waste = self.get_categories_wasted(member)

            # same counts the Waste Score uses
            consumed, wasted, avoidable = self.count_marked_products(member)
            marked = consumed + wasted
            overall_waste_percent = wasted / marked * 100 if marked > 0 else 0
            above_average_percent = overall_waste_percent * CATEGORY_ABOVE_AVERAGE_FACTOR

            products_ref = (
                store.collection("users")
                .document(member)
                .collection("products")
            )

            for document in products_ref.stream():
                data = document.to_dict()

                outcome = data.get("outcome", ProductOutcome.active.value)

                # skip the products already marked consumed or wasted because their outcome is already decided.
                if outcome != ProductOutcome.active.value:
                    continue

                risk = self.calculate_product_waste_risk(data)

                # same percentages as the category waste chart, so the user can see why
                category_waste_percent = category_waste.get(data.get("category"), 0)
                is_above_average = category_waste_percent > above_average_percent
                is_high_enough = category_waste_percent >= CATEGORY_MIN_WASTE_PERCENT
                category_often_wasted = is_above_average and is_high_enough
                if category_often_wasted:
                    risk = self.raise_waste_risk(risk)

                product_risk = {
                    "id": document.id,
                    "name": data.get("name"),
                    "productType": data.get("productType"),
                    "dateExpiration": data.get("dateExpiration"),
                    "risk": risk,
                    "categoryOftenWasted": category_often_wasted
                }
                risks.append(product_risk)

        return risks

    def raise_waste_risk(self, risk: WasteRisk):
        if risk == WasteRisk.low:
            return WasteRisk.medium
        return WasteRisk.high

analytics_actions = AnalyticsActions()
