from fastapi import APIRouter, Depends

from app.actions.authorization_actions import authorization_actions
from app.actions.user_actions import user_actions

router = APIRouter()

# Synchronizes user auth data with db
@router.post("/syncUser", tags=['Users'])
def sync_user_info(user = Depends(authorization_actions.verify_user_token)):
    return user_actions.sync_user_info(user['uid'], user['email'])


@router.get("/userInformation", tags=['Users'])
def get_user_information(user = Depends(authorization_actions.verify_user_token)):
    return user_actions.get_user_information(user["uid"], user['email'])
