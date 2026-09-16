from fastapi import APIRouter, Depends
from app.actions.authorization_actions import authorization_actions
from app.actions.user_actions import user_actions
from app.firebase import firestore, store
from app.auth import verify_user_token
from app.models.UserInfo import UserInfo


router = APIRouter()

# Synchronizes user auth data with db
@router.post("/syncUser", tags=['Users'])
def sync_user_info(user_info: UserInfo, user = Depends(verify_user_token)):
    return user_actions.sync_user_info(user_info, user)
    
@router.get("/userInformation", tags=['Users'])
def get_user_information(user = Depends(authorization_actions.verify_user_token)):
    return user_actions.get_user_information(user["uid"], user['email'])

@router.put("/editUser", tags=['Users'])
def edit_request(user_info: UserInfo, user = Depends(authorization_actions.verify_user_token)):
    return user_actions.edit_user(user_info, user)