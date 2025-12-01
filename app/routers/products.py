from fastapi import APIRouter
from models.Product import Product, ProductList

router = APIRouter()

# seedProducts is used to seed the user different kinds of products for testing.
# Reference: https://firebase.google.com/docs/firestore/manage-data/transactions#batched-writes
# Body from: https://fastapi.tiangolo.com/tutorial/body-fields/#import-field
@router.post("/seedProducts")
def seed_products(
    products: list[Product] = Body(...),
    user = Depends(get_current_user)
):
    user_uid = user["uid"]

    doc_ref = store.collection("users").document(user_uid).collection("products")
    
    batch = store.batch()

    for product in products:
        prod_ref = doc_ref.collection(products).document()

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

@router.post("/products")
def add_product(product: Product, user = Depends(get_current_user)):
    uid = user["uid"]

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
    })

    return {"id": doc_ref.id, "message": "Product added"}

# Want to make a get request to get the information of all products
# https://stackoverflow.com/questions/62203845/firestore-list-subcollections-of-a-document-using-python
@router.get("/getProducts")
def get_product(user = Depends(get_current_user)):
    uid = user["uid"]

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

# PRODUCTS 
#TODO adds an empty product list to user object (does not work at the moment)
# @app.post("/addProductList")
# def add_product_list(user = Depends(get_current_user)):

#     uid = user['uid']
#     email = user['email']

#     product_ref = store.collection("users").document(uid)

#     product_db = product_ref.get()

#     if product_db.exists:
#         return {"message": "User already exists"}
#     else: 
#         product_ref = store.collection('users').document(uid)
#         product_ref.add({
#             'email': email,
#             'createdAt': firestore.SERVER_TIMESTAMP,
#         })

#     return