from typing import Optional
from pydantic import BaseModel
from app.models.Recipe.Recipe import RecipeCategory, RecipeDifficulty


# The app leaves an option out when the user picks "Any"
class GenerateRecipeRequest(BaseModel):
    productIds: list[str]
    mealType: Optional[RecipeCategory] = None
    difficulty: Optional[RecipeDifficulty] = None
    maxTotalTime: Optional[int] = None
    servings: Optional[int] = None
    expiringFirst: bool = False
