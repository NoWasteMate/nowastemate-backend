from enum import Enum
from pydantic import BaseModel
from app.models.Recipe.Ingredient import Ingredient

class RecipeCategory(str, Enum):
    soup = "soup"
    salad = "salad"
    pasta = "pasta"
    handheld = "handheld"
    breakfast = "breakfast"
    dessert = "dessert"
    drink = "drink"
    platedMain = "platedMain"
    general = "general"

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
    category: RecipeCategory
