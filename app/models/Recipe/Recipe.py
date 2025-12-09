from pydantic import BaseModel
from app.models.Recipe.Ingredient import Ingredient

class Recipe(BaseModel):
    recipeName: str
    description: str
    prepTime: int
    cookTime: int
    servings: int
    difficulty: str
    ingredientsUsed: int
    ingredients: list[Ingredient]
    instructions: list[str]
