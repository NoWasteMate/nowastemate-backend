from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, auth, firestore
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import FastAPI
from models.Product import Product, ProductList
from models.Family import Family

app = FastAPI()

cred = credentials.Certificate('firebase-admin.json')
firebase_admin.initialize_app(cred)


store = firestore.client()


# Verify that user's token is valid -> decoded user information
# https://medium.com/@yonaakio/understanding-firebase-id-token-verification-in-python-with-fastapi-18967b78a5b8
def get_current_user(cred: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    if not cred:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Credentials Config",
            headers={"WWW-Authenticate": "Bearer"}
        )
    try: 
        # Code for verifying token 
        #  https://firebase.google.com/docs/auth/admin/verify-id-tokens#verify_id_tokens_using_the_firebase_admin_sdk

        decode = auth.verify_id_token(cred.credentials)

    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )    
    return decode

# Synchronizes user auth data with db
@app.post("/syncUser")
def sync_user_info(user = Depends(get_current_user)):

    uid = user['uid']
    email = user['email']

    doc_ref = store.collection("users").document(uid)
    # TODO (nesting a collection with our user's document (still need to set it))
    # products_ref = store.collection("users").document(uid).collection("products")

    doc = doc_ref.get()


    # if doc.exists:
    #     return {"message": "User already exists"}
    # else: 
    #     #doc_ref = store.collection('users').document(uid)
    #     doc_ref.set({
    #         'email': email,
    #         'createdAt': firestore.SERVER_TIMESTAMP,
    #     })
    #     products_ref.set({
    #         'products': [],
    #         'createdAt': firestore.SERVER_TIMESTAMP
    #     })

    doc_ref.set({
        'email': email,
        'createdAt': firestore.SERVER_TIMESTAMP,
    })

    return {'success': f"{email} user created"}

@app.get("/userInformation")
def get_user_information(user = Depends(get_current_user)):
    print(get_current_user)
    return {"uid": user["uid"], "email": user['email']}

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

@app.post("/products")
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
@app.get("/getProducts")
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

@app.post("/family")
def post_family(family: Family, user = Depends(get_current_user)):

    doc_ref = store.collection("family").document()
    uid = user["uid"]

    doc_ref.set({
        "title": family.title,
        "createdBy": uid,
        "createdAt": firestore.SERVER_TIMESTAMP,
        "members": [uid]
    })

    user_doc_ref = store.collection("users").document(uid)

    #create the link to the family for the user - https://firebase.google.com/docs/firestore/manage-data/add-data#update-data
    user_doc_ref.update({
        "familyId": doc_ref.id
    })

    return {"success": f"{family.title} family created"}

@app.get("/family/{family_id}")
def get_family_by_id(family_id: str, user = Depends(get_current_user)):

    doc_ref = store.collection("family").document(family_id)

    #https://firebase.google.com/docs/firestore/query-data/get-data#get_a_document
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    else:
        print("Family does not exist!")


@app.post("/family/join/{family_id}")
def join_family(family_id: str, user = Depends(get_current_user)):

    doc_ref = store.collection("family").document(family_id)

    doc = doc_ref.get()

    json = doc.to_dict()

    members = json["members"]

    new_member = user["uid"]

    if new_member not in members:
        members.append(new_member)

        doc_ref.update({
        "members": members
        })

        user_doc_ref = store.collection("users").document(new_member)

        user_doc_ref.update({
        "familyId": doc_ref.id
        })
        return {"success": "User added to family"}
    else:
        return {"error": "User already in family"}
    
    



