from fastapi import FastAPI
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.firebase import firebase_auth

app = FastAPI()

# Verify that user's token is valid -> decoded user information
# https://medium.com/@yonaakio/understanding-firebase-id-token-verification-in-python-with-fastapi-18967b78a5b8
def verify_user_token(cred: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    if not cred:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Credentials Config",
            headers={"WWW-Authenticate": "Bearer"}
        )
    try: 
        # Code for verifying token 
        #  https://firebase.google.com/docs/auth/admin/verify-id-tokens#verify_id_tokens_using_the_firebase_admin_sdk

        decode = firebase_auth.verify_id_token(cred.credentials)

    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )    
    return decode



