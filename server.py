import firebase_admin
from firebase_admin import credentials, firestore
# pip install firebase-admin
from fastapi import FastAPI
# fastapi dev server.py is needed in the terminal to run
from pydantic import BaseModel
import os
import uuid

app = FastAPI()

#https://fastapi.tiangolo.com/tutorial/first-steps/
@app.get("/")
async def root():
    return {""}

#Ref for setup https://medium.com/@cbrannen/importing-data-into-firestore-using-python-dce2d6d3cd51
#https://rollout.com/integration-guides/firestore/sdk/step-by-step-guide-to-building-a-firestore-api-integration-in-python
cred = credentials.Certificate("../nowastemate-firebase-firebase-adminsdk-fbsvc-260a57ac1d.json")

dbInit = firebase_admin.initialize_app(cred)

store = firestore.client()

class User(BaseModel):
    first: str
    last: str
    email: str
    password: str

#ref https://firebase.google.com/docs/firestore/query-data/get-data#python
@app.get("/users/{email}")
async def get_user(email: str):
    doc_ref = store.collection("users").document(email)

    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    else:
        return 404




@app.post("/users/")
async def create_user(user: User):

    doc_ref = store.collection("users").document(user.email)

    doc = doc_ref.get()

    if doc.exists:
        return {"message": "User already exists"}
    else: 
        doc_ref = store.collection('users').document(f'{user.email}')
        doc_ref.set({
            'first': user.first,
            'last': user.last,
            'email': user.email,
            'password': user.password,
            'items': []
        })

