import firebase_admin

from firebase_admin import credentials, firestore, auth


# TODO: consider reading path 'firebase-admin.json' from environment variable instead
cred = credentials.Certificate('firebase-admin.json')
firebase_admin.initialize_app(cred)

store = firestore.client()
firebase_auth = auth # rename to avoid conflicts and add clarity
