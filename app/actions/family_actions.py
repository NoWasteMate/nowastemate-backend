from app.models.Family import Family
from app.models.FamilyJoinCode import FamilyJoinCode
from app.models.FamilyMember import FamilyMember
from app.firebase import firestore, store
from fastapi import HTTPException, status


class FamilyActions:

    def create_family(self, uid: str, family: Family):

        #TODO: remove user from old family

        doc_ref = store.collection("family").document()

        doc_ref.set({
            "title": family.title,
            "ownerId": uid,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "members": [uid]
        })

        user_doc_ref = store.collection("users").document(uid)

        #create the link to the family for the user - https://firebase.google.com/docs/firestore/manage-data/add-data#update-data
        user_doc_ref.update({
            "familyId": doc_ref.id
        })

        return {"success": f"{family.title} family created"}

    def get_family(self, uid: str):

        user_doc_ref = store.collection("users").document(uid)

        user_doc = user_doc_ref.get()

        if not user_doc.exists:
            return {"error": "User not found"}

        user_doc = user_doc.to_dict()

        fam_id = user_doc.get("familyId")

        if fam_id is not None:

            doc_ref = store.collection("family").document(fam_id)
            #https://firebase.google.com/docs/firestore/query-data/get-data#get_a_document
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            else:
                return {"error": "Family not found"}
        else:
            return {"error": "User does not not have a family"}

    def join_family(self, uid: str, family_join_code: FamilyJoinCode):

        user_doc_ref = store.collection("users").document(uid)

        user_doc = user_doc_ref.get()

        if not user_doc.exists:
            return {"error": "User not found"}

        json = user_doc.to_dict()


        #https://firebase.google.com/docs/firestore/query-data/get-data#get_a_document
        #realized i have been doing unsafe checking, will need to review the functions
        #kept breaking in cases and needs to be re-done
        prev_fam_id = json.get("familyId")

        if prev_fam_id != None:
            prev_fam_ref = store.collection("family").document(prev_fam_id)
            prev_fam_doc = prev_fam_ref.get()
            json = prev_fam_doc.to_dict()
            members = json.get("members")


            #https://stackoverflow.com/questions/4915920/how-to-delete-an-item-in-a-list-if-it-exists
            if uid in members:
                members.remove(uid)

            #delete reference to old family from the family document
            prev_fam_ref.update({
                "members": members
            })


            #re-check the old family, if it no longer has members, delete
            prev_fam_doc = prev_fam_ref.get()
            json = prev_fam_doc.to_dict()
            members = json["members"]

            if members == []:
                prev_fam_ref.delete()


        doc_ref = store.collection("family").document(family_join_code.code)

        doc = doc_ref.get()

        if not doc.exists:
            return {"error": "Code not found"}

        json = doc.to_dict()

        members = json["members"]

        new_member = uid

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

    def get_family_id(self, uid: str):
        user_doc_ref = store.collection("users").document(uid)

        user_doc = user_doc_ref.get()

        user_doc = user_doc.to_dict()

        if user_doc.get("familyId"):
            fam_id = user_doc["familyId"]
            return {fam_id}
        else:
            return {"error: Family not found"}

    #retrieves all family member email for display
    def get_family_members(self, uid: str):

        user_doc_ref = store.collection("users").document(uid)

        user_check = user_doc_ref.get()
        #https://stackoverflow.com/questions/51483234/how-to-know-if-document-exists-in-firestore-python
        if not user_check.exists:
            return "error"

        user_doc = user_check.to_dict()

        fam_id = user_doc.get("familyId")

        if fam_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not have a family")

        fam_doc_ref = store.collection("family").document(fam_id)

        family = fam_doc_ref.get()

        family = family.to_dict()

        arr = []

        for i in family["members"]:
            user_doc_ref = store.collection("users").document(i)

            doc = user_doc_ref.get()

            json = doc.to_dict()

            if json != None:
                email = json["email"]
                #send id and email
                arr.append(
                    {
                        "member": i,
                        "email": email,
                        "firstName" : json.get("firstName")
                    }
                )

        return arr
    
    def edit_family_name(self, uid: str, newTitle: Family):
        user_doc_ref = store.collection("users").document(uid)

        user_check = user_doc_ref.get()
        #https://stackoverflow.com/questions/51483234/how-to-know-if-document-exists-in-firestore-python
        if not user_check.exists:
            return "error"

        user_doc = user_check.to_dict()

        fam_id = user_doc["familyId"]

        fam_doc_ref = store.collection("family").document(fam_id)

        fam_doc = fam_doc_ref.get()

        fam = fam_doc.to_dict()

        if uid == fam["ownerId"]:
            fam_doc_ref.update(
                {
                    'title': newTitle.title
                }
            )
            return {"success": "Family updated"}
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not the family owner")

    def edit_family_owner(self, uid: str, member: FamilyMember):
                
        user_doc_ref = store.collection("users").document(uid)

        user_check = user_doc_ref.get()
        #https://stackoverflow.com/questions/51483234/how-to-know-if-document-exists-in-firestore-python
        if not user_check.exists:
            return "error"

        user_doc = user_check.to_dict()

        fam_id = user_doc["familyId"]

        fam_doc_ref = store.collection("family").document(fam_id)

        fam_doc = fam_doc_ref.get()

        fam = fam_doc.to_dict()
        #https://fastapi.tiangolo.com/tutorial/response-status-code/#about-http-status-codes
        #https://fastapi.tiangolo.com/reference/status/

        if member.member not in fam["members"]:
            print(member)
            print(fam["members"])
            raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="New owner is not currently apart of the family")

        if uid == fam["ownerId"]:
            fam_doc_ref.update(
                {
                    'ownerId': member.member
                }
            )
            return {"success": "Family owner updated"}
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not the family owner")
        
    def delete_family_member(self, uid: str, member: FamilyMember):

        user_doc_ref = store.collection("users").document(uid)

        user_check = user_doc_ref.get()
        #https://stackoverflow.com/questions/51483234/how-to-know-if-document-exists-in-firestore-python
        if not user_check.exists:
            return "error"

        user_doc = user_check.to_dict()

        fam_id = user_doc["familyId"]

        fam_doc_ref = store.collection("family").document(fam_id)

        fam_doc = fam_doc_ref.get()

        fam = fam_doc.to_dict()

        members = fam["members"]

        if uid == fam["ownerId"]:
                if member.member in members:
                    members.remove(member.member)

                    fam_doc_ref.update({
                    "members": members
                    })

                    member_doc_ref = store.collection("users").document(member.member)
                    #https://firebase.google.com/docs/firestore/manage-data/delete-data#fields
                    member_doc_ref.update({
                        "familyId": firestore.DELETE_FIELD
                    })
                    return {"success": "Member removed"}
                else:
                    raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Member currently not apart of the family")
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not the family owner")

    def delete_own_membership(self, uid: str, member: FamilyMember):

        user_doc_ref = store.collection("users").document(uid)

        user_check = user_doc_ref.get()
        #https://stackoverflow.com/questions/51483234/how-to-know-if-document-exists-in-firestore-python
        if not user_check.exists:
            return "error"

        user_doc = user_check.to_dict()

        fam_id = user_doc["familyId"]

        fam_doc_ref = store.collection("family").document(fam_id)

        fam_doc = fam_doc_ref.get()

        fam = fam_doc.to_dict()

        members = fam["members"]

        if uid != fam["ownerId"] and member.member == uid:
                if member.member in members:
                    members.remove(member.member)

                    fam_doc_ref.update({
                    "members": members
                    })

                    member_doc_ref = store.collection("users").document(member.member)
                    #https://firebase.google.com/docs/firestore/manage-data/delete-data#fields
                    member_doc_ref.update({
                        "familyId": firestore.DELETE_FIELD
                    })
                    return {"success": "Member removed"}
                else:
                    raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Member currently not apart of the family")
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="family owner cannot leave, the owner must pass their ownership")     
        
    def delete_family(self, uid: str):

        user_doc_ref = store.collection("users").document(uid)

        user_check = user_doc_ref.get()
        #https://stackoverflow.com/questions/51483234/how-to-know-if-document-exists-in-firestore-python
        if not user_check.exists:
            return "error"

        user_doc = user_check.to_dict()

        fam_id = user_doc.get("familyId")

        if not fam_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Family not found")


        fam_doc_ref = store.collection("family").document(fam_id)

        fam_doc = fam_doc_ref.get()

        fam = fam_doc.to_dict()

        members = fam["members"]
        #is owner and only member
        if uid == fam["ownerId"] and members == [uid]:
            store.collection("family").document(fam_id).delete()

                    #https://firebase.google.com/docs/firestore/manage-data/delete-data#fields
            user_doc_ref.update({
                "familyId": firestore.DELETE_FIELD
            })

            return {"success": "Family removed"} 

        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not the family owner or family has multiple members")




            
        


        

 
        





family_actions = FamilyActions()
