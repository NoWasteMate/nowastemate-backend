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
            
            current_category = i["category"]
            #add 1 to the overall no matter what
            overall[current_category] = overall.get(current_category, 0) + 1
            #also add 1 to the wasted amount if product was wasted
            if i.get("outcome") == "wasted":
                wasted[current_category] = wasted.get(current_category, 0) + 1

        #https://www.geeksforgeeks.org/python/iterate-over-a-dictionary-in-python/
        #we need to check that the key exists in cases where there
        #we take amount of wasted items, divide by total number of items, then multiply by 100 to represent the percentage
        for key, value in overall.items():
            result[key] =  round(wasted.get(key, 0) / value * 100, 1)

        return result

        
                    
            


        




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