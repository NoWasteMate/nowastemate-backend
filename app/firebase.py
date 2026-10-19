import firebase_admin
from firebase_admin import credentials, firestore, auth, storage

# api secrets handled by gcloud
firebase_admin.initialize_app()

store = firestore.client()

# https://firebase.google.com/docs/storage/admin/start
bucket = storage.bucket("nowastemate.firebasestorage.app")
firebase_auth = auth # rename to avoid conflicts and add clarity
