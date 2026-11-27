from fastapi import APIRouter, Depends, Body, Path, Query
from typing import Optional

from app.models.Product import Product, ProductList, ProductUpdate, ProductOutcomeUpdate, ProductCreate
from app.actions.authorization_actions import authorization_actions
from app.actions.product_actions import product_actions


router = APIRouter()

# seedProducts is used to seed the user different kinds of products for testing.
# Reference: https://firebase.google.com/docs/firestore/manage-data/transactions#batched-writes
# Body from: https://fastapi.tiangolo.com/tutorial/body-fields/#import-field
@router.post("/seedProducts", tags=['Products'])
def seed_products(
    products: list[Product] = Body(...),
    user = Depends(authorization_actions.verify_user_token)
):
    return product_actions.seed_products(user["uid"], products)

@router.post("/products", tags=['Products'])
def add_product(product: ProductCreate, user = Depends(authorization_actions.verify_user_token)):
    return product_actions.add_product(user["uid"], product)

# Want to make a get request to get the information of all products
# https://stackoverflow.com/questions/62203845/firestore-list-subcollections-of-a-document-using-python
@router.get("/getProducts", tags=['Products'])
def get_product(user = Depends(authorization_actions.verify_user_token)):
    return product_actions.get_products(user["uid"])

# returns active products from every member of the caller's family
@router.get("/getFamilyProducts", tags=['Products'])
def get_family_products(user = Depends(authorization_actions.verify_user_token)):
    return product_actions.get_family_products(user["uid"])

# making a user delete a product based on its id
# reference: https://firebase.google.com/docs/firestore/manage-data/delete-data#python_2
@router.delete("/deleteProduct/{product_id}", tags=['Products'])
def delete_product(product_id: str, user = Depends(authorization_actions.verify_user_token)):
    return product_actions.delete_product(user["uid"], product_id)

# making a user update a product based on its id
# reference: https://firebase.google.com/docs/firestore/manage-data/add-data#update-data
@router.put("/putProduct/{product_id}", tags=['Products'])
def update_product(product_id: str, product: ProductUpdate, user = Depends(authorization_actions.verify_user_token)):
    return product_actions.update_product(user["uid"], product_id, product)

# marks all or part of a product as consumed or wasted; without quantity the whole product is marked
# reference: https://firebase.google.com/docs/firestore/manage-data/add-data#update-data
# reference: https://firebase.google.com/docs/firestore/manage-data/transactions#transactions
@router.put("/markProductOutcome/{product_id}", tags=['Products'])
def mark_product_outcome(product_id: str, body: ProductOutcomeUpdate, user = Depends(authorization_actions.verify_user_token)):
    return product_actions.mark_product_outcome(user["uid"], product_id, body.outcome, body.wasteReason, body.quantity)

# looks a barcode up on OpenFoodFacts and returns it as a Product without saving it.
# path validations: https://fastapi.tiangolo.com/tutorial/path-params-numeric-validations/
# pattern (regex): https://fastapi.tiangolo.com/tutorial/query-params-str-validations/
@router.get("/getBarcodeDetails/{barcode}", tags=['Products'], response_model=Product)
def get_barcode_details(
    barcode: str = Path(pattern=r"^\d{8,14}$"),
    user = Depends(authorization_actions.verify_user_token)
):
    return product_actions.get_barcode_details(barcode)

# returns the Product Type list unless the app already has this version
# query params: https://fastapi.tiangolo.com/tutorial/query-params/#optional-parameters
@router.get("/productTypes", tags=['Products'])
def get_product_types(version: Optional[int] = None, user = Depends(authorization_actions.verify_user_token)):
    return product_actions.get_product_types(version)

# resolves a name to a Product Type without saving
# Query(None) makes repeated ?tags= params parse as a query list instead of a body
# https://fastapi.tiangolo.com/tutorial/query-params-str-validations/#query-parameter-list-multiple-values
@router.get("/resolveProductType", tags=['Products'])
def resolve_product_type(
    name: str,
    tags: Optional[list[str]] = Query(None),
    user = Depends(authorization_actions.verify_user_token)
):
    return product_actions.resolve_product_type(name, tags)



@router.get("/get_waste_diagnostic/{product_id}", tags=['Products'])
def get_product(product_id: str, user = Depends(authorization_actions.verify_user_token)):
    return product_actions.get_waste_diagnostic(user["uid"], product_id)

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
