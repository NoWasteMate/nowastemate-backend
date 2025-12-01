# ❯ pip install "fastapi[standard]"
# ❯ pip install firebase_admin
# ❯ pip install pydantic
from fastapi import APIRouter, HTTPException, Depends, status, Body
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, auth, firestore
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import FastAPI
from models.Family import Family
from models.FamilyJoinCode import FamilyJoinCode
from app.routers import families

app = FastAPI()

cred = credentials.Certificate('firebase-admin.json')
firebase_admin.initialize_app(cred)


store = firestore.client()


# Verify that user's token is valid -> decoded user information
# https://medium.com/@yonaakio/understanding-firebase-id-token-verification-in-python-with-fastapi-18967b78a5b8
def auth_user_token(cred: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
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
def sync_user_info(user = Depends(auth_user_token)):

    uid = user['uid']
    email = user['email']

    doc_ref = store.collection("users").document(uid)

    doc_ref.set({
        'email': email,
        'createdAt': firestore.SERVER_TIMESTAMP,
    })

    return {'success': f"{email} user created"}


@app.get("/userInformation")
def get_user_information(user = Depends(auth_user_token)):
    print(auth_user_token)
    return {"uid": user["uid"], "email": user['email']}

app.include_router(families.router)

