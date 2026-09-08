from pydantic import BaseModel


class UserInfo(BaseModel):
    firstName: str
    lastName: str
    dietaryRestrictions: str