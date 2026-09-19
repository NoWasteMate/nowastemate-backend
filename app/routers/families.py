from fastapi import APIRouter, Depends

from app.models.Family import Family
from app.models.FamilyJoinCode import FamilyJoinCode
from app.models.FamilyMember import FamilyMember
from app.actions.authorization_actions import authorization_actions
from app.actions.family_actions import family_actions

router = APIRouter()

@router.post("/family", tags=['Families'])
def post_family(family: Family, user = Depends(authorization_actions.verify_user_token)):
    return family_actions.create_family(user["uid"], family)

@router.get("/family", tags=['Families'])
def get_family_by_id(user = Depends(authorization_actions.verify_user_token)):
    return family_actions.get_family(user["uid"])

@router.post("/family/join", tags=['Families'])
def join_family(family_join_code: FamilyJoinCode, user = Depends(authorization_actions.verify_user_token)):
    return family_actions.join_family(user["uid"], family_join_code)

@router.get("/family_id", tags=['Families'])
def get_family_id(user = Depends(authorization_actions.verify_user_token)):
    return family_actions.get_family_id(user["uid"])

#retrieves all family member email for display
@router.get("/family_members", tags=['Families'])
def get_family_members(user = Depends(authorization_actions.verify_user_token)):
    return family_actions.get_family_members(user["uid"])

@router.put("/family_name", tags=['Families'])
def update_family_name(family: Family, user = Depends(authorization_actions.verify_user_token)):
    return family_actions.edit_family_name(user["uid"], family)

@router.put("/family_owner", tags=['Families'])
def update_family_owner(member: FamilyMember, user = Depends(authorization_actions.verify_user_token)):
    return family_actions.edit_family_owner(user["uid"], member)

@router.delete("/family_member", tags=['Families'])
def remove_family_member(member: FamilyMember, user = Depends(authorization_actions.verify_user_token)):
    return family_actions.delete_family_member(user["uid"], member)

