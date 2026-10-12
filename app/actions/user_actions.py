from app.firebase import firestore, store
from app.models.UserInfo import UserInfo
from app.firebase import auth
from fastapi import HTTPException

#https://fastapi.tiangolo.com/tutorial/handling-errors/
#https://firebase.google.com/docs/auth/admin/errors
#https://stackoverflow.com/questions/3825990/http-response-code-for-post-when-resource-already-exists


class UserActions:

    # Synchronizes user auth data with db
    def sync_user_info(self, user_info: UserInfo, user):

        uid = user['uid']

        doc_ref = store.collection("users").document(uid)

        user_check = doc_ref.get()
        #https://stackoverflow.com/questions/51483234/how-to-know-if-document-exists-in-firestore-python
        if not user_check.exists:
            doc_ref.set({
                'email': user_info.email,
                'createdAt': firestore.SERVER_TIMESTAMP,
                'firstName': user_info.firstName,
                'lastName': user_info.lastName,
                'dietaryRestrictions': user_info.dietaryRestrictions
            })
            return {'success': f"{user_info.email} user created"}
        
        return {"message": "User already exists"}

    def get_user_information(self, uid: str, email: str):
        return {"uid": uid, "email": email}
    
    def edit_user(self, user_info, user):
        uid = user['uid']
        doc_ref = store.collection("users").document(uid)
        user_check = doc_ref.get()

        if user_check.exists:

            try:
                #https://firebase.google.com/docs/auth/admin/manage-users#update_a_user
                auth.update_user(uid, email=user_info.email)
                
                doc_ref.update(
                {
                    'email': user_info.email,
                    'firstName': user_info.firstName,
                    'lastName': user_info.lastName,
                    'dietaryRestrictions': user_info.dietaryRestrictions
                }
                )
                return {'success': f"{uid} updated"} 
            except auth.EmailAlreadyExistsError:
                raise HTTPException(status_code=409, detail="Email exists already")
        else:
            return {'message': f"user not found"} 
        
    def get_current_user_info(self, uid):
        
        doc_ref = store.collection("users").document(uid)

        user = doc_ref.get()
        
        #https://stackoverflow.com/questions/51483234/how-to-know-if-document-exists-in-firestore-python
        if user.exists:
            user = user.to_dict()
            return user
        else: raise HTTPException(status_code=404, detail="User not found")


user_actions = UserActions()
