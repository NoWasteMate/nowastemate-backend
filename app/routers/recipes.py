from fastapi import APIRouter, Depends, Body

from app.models.Recipe import Recipe, Ingredient
from app.firebase import firestore, store
from app.auth import verify_user_token


router = APIRouter()

@router.post("/addRecipe")
def add_recipe(recipe: Recipe, user = Depends(verify_user_token)):
    uid = user["uid"]

    recipes_ref = (
        store.collection('users').document(uid).collection('recipes')
    )

    doc_ref = recipes_ref().document()

    doc_ref.set({
        **recipe.model_dump(),
        "createdAt": firestore.SERVER_TIMESTAMP,
    })

    return {"id": doc_ref.id, "message": "Recipe added"}
