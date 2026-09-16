from app.firebase import firestore, store
from app.models.UserInfo import UserInfo


class UserActions:

    # Synchronizes user auth data with db
    def sync_user_info(self, user_info: UserInfo, user):

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

    def get_user_information(self, uid: str, email: str):
        return {"uid": uid, "email": email}
    
    def edit_user(self, user_info, user):
        uid = user['uid']
        email = user['email']
        doc_ref = store.collection("users").document(uid)
        user_check = doc_ref.get()

        if user_check.exists:
            doc_ref.update(
                {
                    'email': email,
                    'firstName': user_info.firstName,
                    'lastName': user_info.lastName,
                    'dietaryRestrictions': user_info.dietaryRestrictions
                }
            )
            return {'success': f"{uid} updated"} 
        else:
            return {'message': f"user not found"} 


user_actions = UserActions()
