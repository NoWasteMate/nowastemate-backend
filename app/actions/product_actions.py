from app.models.Product import Product, ProductUpdate, ProductCategory
from app.firebase import firestore, store

from datetime import datetime, timezone

from fastapi import HTTPException

from app import openfoodfacts


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

            batch.set(prod_ref, {
                "name": product.name,
                "quantity": product.quantity,
                "createdAt": firestore.SERVER_TIMESTAMP,
                "category": product.category.value
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

        doc_ref.set({
            **product.model_dump(),
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
            products.append({"id": document.id, **document.to_dict()})

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
        products_ref.update(update_data)

        return {"id": product_id, "message": "Product updated"}


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
        )

product_actions = ProductActions()
