from pydantic import BaseModel

class Ingredient(BaseModel):
    name: str
    quantity: float
    unit: str

class Recipe(BaseModel):
    recipeName: str
    prepTime: int
    cookTime: int
    servings: int
    ingredients: list[Ingredient]
    instructions: list[str]
