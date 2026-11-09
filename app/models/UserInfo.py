from pydantic import BaseModel


class UserInfo(BaseModel):
    email: str
    firstName: str
    lastName: str
    dietaryRestrictions: list[str]
    #https://fastapi.tiangolo.com/tutorial/body/#create-your-data-model
    #giving default values, this way we can create with set values, but also update later
    notificationDays: int = 1
    notificationHour: int = 9