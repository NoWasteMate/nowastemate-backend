from pydantic import BaseModel


class FamilyMember(BaseModel):
    member: str