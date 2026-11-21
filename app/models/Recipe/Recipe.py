from enum import Enum
from typing import Optional
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

# Request only. Recipe.difficulty stays a str since older recipes say "Moderate"
class RecipeDifficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"

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
    imageUrl: Optional[str] = None
    poolId: Optional[str] = None
    rating: Optional[int] = None
