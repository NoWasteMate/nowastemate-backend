from app.models.Product import Product
from app.firebase import firestore, store


class ProductActions:

    # seed_products is used to seed the user different kinds of products for testing.
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
                "category": product.category
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
    def update_product(self, uid: str, product_id: str, product: Product):
        products_ref = (
            store.collection("users")
            .document(uid)
            .collection("products")
            .document(product_id)
        )

        products_ref.update({
            **product.model_dump()
        })

        return {"that id has been updated"}


product_actions = ProductActions()
