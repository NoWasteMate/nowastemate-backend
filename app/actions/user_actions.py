from app.firebase import firestore, store


class UserActions:

    # Synchronizes user auth data with db
    def sync_user_info(self, uid: str, email: str):

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

    def get_user_information(self, uid: str, email: str):
        return {"uid": uid, "email": email}


user_actions = UserActions()
