from pydantic import BaseModel


class Family(BaseModel):
    family_name: str
    members: list[str]