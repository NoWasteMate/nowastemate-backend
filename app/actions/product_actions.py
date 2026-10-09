from app.models.Product import Product, ProductUpdate, ProductCategory, ProductOutcome, WasteReason
from app.firebase import firestore, store

from typing import Optional

from datetime import datetime, timezone

from fastapi import HTTPException

from app import openfoodfacts
from app.vocabulary.normalize import normalize_name
from app.vocabulary.product_types import PRODUCT_TYPES, VERSION


# since OFF tags are vocabulary mis-matched.
# set literals: https://docs.python.org/3/tutorial/datastructures.html#sets
category_priority = [
    (ProductCategory.frozen,   {"frozen-foods"}),
    (ProductCategory.canned,   {"canned-foods"}),
    (ProductCategory.beverage, {"beverages", "waters", "juices", "sodas"}),
    (ProductCategory.dairy,    {"dairies", "milks", "cheeses", "yogurts", "butters"}),
    (ProductCategory.meat,     {"meats", "poultry", "fishes", "seafood"}),
    (ProductCategory.produce,  {"fruits", "vegetables", "fresh-plant-based"}),
    (ProductCategory.grains,   {"cereals-and-potatoes", "cereals", "breads", "pastas", "rices"}),
]

class ProductActions:

    # seed_products is used to seed the user different kinds of products for testing.
    # (Subject to change)
    # Reference: https://firebase.google.com/docs/firestore/manage-data/transactions#batched-writes
    def seed_products(self, uid: str, products: list[Product]):

        doc_ref = store.collection("users").document(uid).collection("products")

        batch = store.batch()

        for product in products:
            prod_ref = doc_ref.document()
            product_type, product_type_source = normalize_name(product.name)
            category = self.pick_category(product_type, None)

            batch.set(prod_ref, {
                "name": product.name,
                "quantity": product.quantity,
                "createdAt": firestore.SERVER_TIMESTAMP,
                "category": category.value,
                "productType": product_type,
                "productTypeSource": product_type_source,
                "outcome": ProductOutcome.active.value
            })

        batch.commit()

        return {
            "message": "seed complete"
        }

    def add_product(self, uid: str, product: Product):

        # this is used to make the collection
        products_ref = (
            store.collection("users")
            .document(uid)
            .collection("products")
        )

        doc_ref = products_ref.document()

        product.productType, product.productTypeSource = normalize_name(product.name, product.categoryTags)
        product.category = self.pick_category(product.productType, product.categoryTags)

        doc_ref.set({
            **product.model_dump(exclude={"categoryTags"}),
            "createdAt": firestore.SERVER_TIMESTAMP,
            "createdBy": uid
        })

        return {"id": doc_ref.id, "message": "Product added"}

    # Want to make a get request to get the information of all products
    # https://stackoverflow.com/questions/62203845/firestore-list-subcollections-of-a-document-using-python
    def get_products(self, uid: str):
        products_ref = (
            store.collection("users")
            .document(uid)
            .collection("products")
        )

        #https://firebase.google.com/docs/firestore/query-data/get-data
        #https://firebase.google.com/docs/firestore/query-data/get-data#get_all_documents_in_a_collection
        products_document = products_ref.stream()

        products = []
        for document in products_document:
            data = document.to_dict()

            if data.get("outcome", ProductOutcome.active.value) != ProductOutcome.active.value:
                continue

            products.append({"id": document.id, **data})

        return products

    # making a user delete a product based on its id
    # reference: https://firebase.google.com/docs/firestore/manage-data/delete-data#python_2
    def delete_product(self, uid: str, product_id: str):
        products_ref = (
            store.collection("users")
            .document(uid)
            .collection("products")
            .document(product_id)
        )

        product = products_ref.get()
        print(product)

        products_ref.delete()

        return {"message": "Product of that id has been deleted"}

    # making a user update a product based on its id
    # reference: https://firebase.google.com/docs/firestore/manage-data/add-data#update-data
    def update_product(self, uid: str, product_id: str, product: ProductUpdate):
        products_ref = (
            store.collection("users")
            .document(uid)
            .collection("products")
            .document(product_id)
        )

        update_data = product.model_dump(exclude_unset=True)

        # keeps the category picked in Edit
        if product.name is not None:
            product_type, product_type_source = normalize_name(product.name)
            update_data["productType"] = product_type
            update_data["productTypeSource"] = product_type_source

        products_ref.update(update_data)

        return {"id": product_id, "message": "Product updated"}

    # marking a product as consumed or wasted (analytics)
    # reference: https://firebase.google.com/docs/firestore/manage-data/add-data#server_timestamp
    def mark_product_outcome(self, uid: str, product_id: str, outcome: ProductOutcome, waste_reason: Optional[WasteReason] = None):

        # user can only mark consumed or wasted
        if outcome not in (ProductOutcome.consumed, ProductOutcome.wasted):
            raise HTTPException(status_code=422, detail="Outcome must be consumed or wasted")

        # a wasted product error checking
        if outcome == ProductOutcome.wasted and waste_reason is None:
            raise HTTPException(status_code=422, detail="Waste reason is required when marking wasted")

        if outcome == ProductOutcome.consumed and waste_reason is not None:
            raise HTTPException(status_code=422, detail="Waste reason is only allowed when marking wasted")

        product_ref = (
            store.collection("users")
            .document(uid)
            .collection("products")
            .document(product_id)
        )

        product = product_ref.get()

        if not product.exists:
            raise HTTPException(status_code=404, detail="Product Not Found")

        # the product's outcome can only be changed once
        if product.to_dict().get("outcome", ProductOutcome.active.value) != ProductOutcome.active.value:
            raise HTTPException(status_code=409, detail="Product Already Marked")

        product_ref.update({
            "outcome": outcome.value,
            "outcomeAt": firestore.SERVER_TIMESTAMP,
            "wasteReason": waste_reason.value if waste_reason else None
        })

        return {"id": product_id, "outcome": outcome.value, "wasteReason": waste_reason.value if waste_reason else None, "message": "Product Marked"}

    # barcode methods
    # maps OFF's categories_tags to one of our ProductCategory values.
    # tags are (en:Petit-déjeuners, fr:Nutella) for example
    # set intersection (&): https://docs.python.org/3/library/stdtypes.html#frozenset.intersection
    def map_category(self, tags: list[str] | None) -> ProductCategory:
        if not tags:
            return ProductCategory.other

        en_tags = {tag.lower()[3:] for tag in tags if tag.lower().startswith("en:")}

        for category, keywords in category_priority:
            if en_tags & keywords:
                return category

        return ProductCategory.other

    # falls back to the barcode tags when the type is "other"
    def pick_category(self, product_type: Optional[str], category_tags: Optional[list[str]]) -> ProductCategory:
        if product_type:
            category = PRODUCT_TYPES[product_type]["category"]
            if category != "other":
                return ProductCategory(category)

        return self.map_category(category_tags)

    def get_barcode_details(self, barcode: str) -> Product:

        try:
            raw = openfoodfacts.fetch_product(barcode)
        except openfoodfacts.BarcodeNotFoundError:
            raise HTTPException(status_code=404, detail="Product not found, add manually")
        except openfoodfacts.BarcodeOverloadedError:
            raise HTTPException(status_code=503, detail="Barcode service busy, try again")
        except openfoodfacts.BarcodeTimeoutError:
            raise HTTPException(status_code=504, detail="Barcode service timed out")
        except openfoodfacts.BarcodeUpstreamError:
            raise HTTPException(status_code=502, detail="Barcode service unavailable")

        return Product(
            name=raw.get("product_name") or "",
            quantity=1,
            createdAt=datetime.now(timezone.utc).isoformat(),
            category=self.map_category(raw.get("categories_tags")),
            categoryTags=raw.get("categories_tags"),
        )

    # allergens and diet flags left out until the app needs them
    def get_product_types(self, version: Optional[int]):
        if version == VERSION:
            return {"upToDate": True}

        types = []
        for key, product_type in PRODUCT_TYPES.items():
            types.append({
                "key": key,
                "name": product_type["name"],
                "synonyms": product_type["synonyms"],
                "parents": product_type["parents"],
                "category": product_type["category"],
            })

        return {"version": VERSION, "types": types}
    


    def get_waste_diagnostic(self, uid: str, diagnosticProduct: Product):
            
            #using existing get_products() but removing the filter for outcomes
            products_ref = (
                store.collection("users")
                .document(uid)
                .collection("products")
            )

            products_document = products_ref.stream()

            products = []
            for document in products_document:
                data = document.to_dict()

                products.append({"id": document.id, **data})

            #if diagnosticProduct.createdAt < 

            if diagnosticProduct.dateExpiration < datetime.now():
                return WasteReason.expired
            
            


            
            #return products
    

product_actions = ProductActions()
