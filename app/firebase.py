import firebase_admin
from firebase_admin import credentials, firestore, auth, storage
import os
import sys

from dotenv import load_dotenv

# api secrets handled by gcloud
firebase_admin.initialize_app()

store = firestore.client()

load_dotenv()

if os.environ["DB_ENV"] == 'PRD':
    # https://firebase.google.com/docs/storage/admin/start
    bucket = storage.bucket("nowastemate.firebasestorage.app")
elif os.environ["DB_ENV"] == 'DEV':
    bucket = storage.bucket("nowastemate-dev.firebasestorage.app")
else:
    # if an incorrect environment variable is added.
    print("App shutdown cause no environment was specified.")
    sys.exit()

firebase_auth = auth # rename to avoid conflicts and add clarity

