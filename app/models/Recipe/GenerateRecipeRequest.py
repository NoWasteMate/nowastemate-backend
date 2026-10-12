from pydantic import BaseModel


class GenerateRecipeRequest(BaseModel):
    productIds: list[str]
