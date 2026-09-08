from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.firebase import firebase_auth


class AuthorizationActions:

    # Verify that user's token is valid and decode user information
    def verify_user_token(self, cred: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        if not cred:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Credentials Config",
                headers={"WWW-Authenticate": "Bearer"}
            )
        try:
            # Code for verifying token
            #  https://firebase.google.com/docs/auth/admin/verify-id-tokens#verify_id_tokens_using_the_firebase_admin_sdk
            decoded_token = firebase_auth.verify_id_token(cred.credentials)

        except:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return decoded_token


authorization_actions = AuthorizationActions()
