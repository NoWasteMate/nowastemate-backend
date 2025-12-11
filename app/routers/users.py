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

    user_check = doc_ref.get()
    #https://stackoverflow.com/questions/51483234/how-to-know-if-document-exists-in-firestore-python
    if not user_check.exists:

        doc_ref.set({
            'email': email,
            'createdAt': firestore.SERVER_TIMESTAMP,
        })
        return {'success': f"{email} user created"}
    
    return {"message": "User already exists"}
    


@router.get("/userInformation", tags=['Users'])
def get_user_information(user = Depends(verify_user_token)):
    print(verify_user_token)
    return {"uid": user["uid"], "email": user['email']}
