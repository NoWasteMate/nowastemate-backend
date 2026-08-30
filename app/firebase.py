import firebase_admin
from firebase_admin import credentials, firestore, auth

# api secrets handled by gcloud
firebase_admin.initialize_app()

store = firestore.client()
firebase_auth = auth # rename to avoid conflicts and add clarity
