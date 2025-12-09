from fastapi import APIRouter, Depends
from app.firebase import firestore, store
from app.auth import verify_user_token

router = APIRouter()

# Synchronizes user auth data with db
@router.post("/syncUser", tags=['Users'])
def sync_user_info(user = Depends(verify_user_token)):

    uid = user['uid']
    email = user['email']

    doc_ref = store.collection("users").document(uid)

    doc_ref.set({
        'email': email,
        'createdAt': firestore.SERVER_TIMESTAMP,
    })

    return {'success': f"{email} user created"}


@router.get("/userInformation", tags=['Users'])
def get_user_information(user = Depends(verify_user_token)):
    print(verify_user_token)
    return {"uid": user["uid"], "email": user['email']}
