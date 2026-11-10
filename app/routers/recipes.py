from fastapi import APIRouter, Body, Depends

from app.models.Recipe.Recipe import Recipe
from app.models.Recipe.GenerateRecipeRequest import GenerateRecipeRequest
from app.actions.authorization_actions import authorization_actions
from app.actions.recipe_actions import recipe_actions


router = APIRouter()

@router.post("/seedRecipes", tags=['Recipes'])
def seed_recipes(
    recipes: list[Recipe] = Body(...),
    user = Depends(authorization_actions.verify_user_token)
):
    return recipe_actions.seed_recipes(user["uid"], recipes)

@router.post("/addRecipe", tags=['Recipes'])
def add_recipe(recipe: Recipe, user = Depends(authorization_actions.verify_user_token)):
    return recipe_actions.add_recipe(user["uid"], recipe)

@router.post("/generateRecipe", description="Generate a recipe from the users selected products and adds to user collection", tags=['Recipes'])
def generate_recipe_from_products(request: GenerateRecipeRequest, user = Depends(authorization_actions.verify_user_token)):
    return recipe_actions.generate_recipe_from_products(user["uid"], request.productIds)

@router.get("/getAllRecipes", description="Return a list of all recipe items from the user", tags=['Recipes'])
def get_all_recipes(user = Depends(authorization_actions.verify_user_token)):
    return recipe_actions.get_all_recipes(user["uid"])

@router.delete("/deleteRecipe/{recipe_id}", description="Remove recipe from user by ID", tags=['Recipes'])
def remove_recipe_by_id(recipe_id: str, user = Depends(authorization_actions.verify_user_token)):
    return recipe_actions.remove_recipe_by_id(user["uid"], recipe_id)

@router.get("/suggestedRecipes", description="Return up to 3 pool recipes the user nearly has the products for", tags=['Recipes'])
def get_suggested_recipes(user = Depends(authorization_actions.verify_user_token)):
    return recipe_actions.get_suggested_recipes(user["uid"])

@router.post("/saveSuggestedRecipe/{pool_id}", description="Save a copy of a suggested pool recipe to the user", tags=['Recipes'])
def save_suggested_recipe(pool_id: str, user = Depends(authorization_actions.verify_user_token)):
    return recipe_actions.save_suggested_recipe(user["uid"], pool_id)
