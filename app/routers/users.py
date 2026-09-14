from fastapi import APIRouter, Depends
from app.firebase import firestore, store
from app.auth import verify_user_token
from app.models.UserInfo import UserInfo


router = APIRouter()

# Synchronizes user auth data with db
@router.post("/syncUser", tags=['Users'])
def sync_user_info(user_info: UserInfo, user = Depends(verify_user_token)):

    uid = user['uid']
    email = user['email']

    doc_ref = store.collection("users").document(uid)

    user_check = doc_ref.get()
    #https://stackoverflow.com/questions/51483234/how-to-know-if-document-exists-in-firestore-python
    if not user_check.exists:
        doc_ref.set({
            'email': email,
            'createdAt': firestore.SERVER_TIMESTAMP,
            'firstName': user_info.firstName,
            'lastName': user_info.lastName,
            'dietaryRestrictions': user_info.dietaryRestrictions
        })
        return {'success': f"{email} user created"}
    
    return {"message": "User already exists"}
    


@router.get("/userInformation", tags=['Users'])
def get_user_information(user = Depends(authorization_actions.verify_user_token)):
    return user_actions.get_user_information(user["uid"], user['email'])
