from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, auth, firestore
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import FastAPI


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

    doc = doc_ref.get()

    if doc.exists:
        return {"message": "User already exists"}
    else: 
        doc_ref = store.collection('users').document(uid)
        doc_ref.set({
            'email': email,
            'createdAt': firestore.SERVER_TIMESTAMP,
        })

    return {'success': f"{email} user created"}

@app.get("/userInformation")
def get_user_information(user = Depends(get_current_user)):
    print(get_current_user)
    return {"uid": user["uid"], "email": user['email']}

