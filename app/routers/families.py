from fastapi import APIRouter, Depends, Body

from app.models.Family import Family
from app.models.FamilyJoinCode import FamilyJoinCode
from app.auth import verify_user_token
from app.firebase import firestore, store 

router = APIRouter()

@router.post("/family", tags=['Families'])
def post_family(family: Family, user = Depends(verify_user_token)):

    doc_ref = store.collection("family").document()
    uid = user["uid"]

    doc_ref.set({
        "title": family.title,
        "createdBy": uid,
        "createdAt": firestore.SERVER_TIMESTAMP,
        "members": [uid]
    })

    user_doc_ref = store.collection("users").document(uid)

    #create the link to the family for the user - https://firebase.google.com/docs/firestore/manage-data/add-data#update-data
    user_doc_ref.update({
        "familyId": doc_ref.id
    })

    return {"success": f"{family.title} family created"}

@router.get("/family", tags=['Families'])
def get_family_by_id(user = Depends(verify_user_token)):

    uid = user["uid"]

    user_doc_ref = store.collection("users").document(uid)

    user_doc = user_doc_ref.get()

    user_doc = user_doc.to_dict()

    if user_doc["familyId"] is not None:
        fam_id = user_doc["familyId"]

        doc_ref = store.collection("family").document(fam_id)

        #https://firebase.google.com/docs/firestore/query-data/get-data#get_a_document
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            return {"error": "Family not found"}
    else:
        return {"error": "User does not not have a family"}


@router.post("/family/join", tags=['Families'])
def join_family(family_join_code: FamilyJoinCode, user = Depends(verify_user_token)):

    print(family_join_code.code)

    doc_ref = store.collection("family").document(family_join_code.code)

    doc = doc_ref.get()

    json = doc.to_dict()

    members = json["members"]

    new_member = user["uid"]

    if new_member not in members:
        members.append(new_member)

        doc_ref.update({
        "members": members
        })

        user_doc_ref = store.collection("users").document(new_member)

        user_doc_ref.update({
        "familyId": doc_ref.id
        })
        return {"success": "User added to family"}
    else:
        return {"error": "User already in family"}
    

    
@router.get("/family_id", tags=['Families'])
def get_family_id(user = Depends(verify_user_token)):
    uid = user["uid"]

    user_doc_ref = store.collection("users").document(uid)

    user_doc = user_doc_ref.get()

    user_doc = user_doc.to_dict()

    if user_doc["familyId"] is not None:
        fam_id = user_doc["familyId"]
        return {fam_id}
    else:
        return None

#retrieves all family member email for display
@router.get("/family_members", tags=['Families'])
def get_family_members(user = Depends(verify_user_token)):

    family = get_family_by_id(user)

    members = family["members"]

    arr = []

    for i in members:
        user_doc_ref = store.collection("users").document(i)

        doc = user_doc_ref.get()

        json = doc.to_dict()

        if json != None:
            json = json["email"]
            
            arr.append(json)

    return arr

