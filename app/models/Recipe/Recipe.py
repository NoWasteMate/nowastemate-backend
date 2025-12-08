from pydantic import BaseModel
from app.models.Recipe.Ingredient import Ingredient

class Recipe(BaseModel):
    recipeName: str
    prepTime: int
    cookTime: int
    servings: int
    ingredients: list[Ingredient]
    instructions: list[str]
