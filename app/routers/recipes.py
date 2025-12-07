from fastapi import APIRouter, Depends, Body

from app.models.Recipe import Recipe, Ingredient
from app.firebase import firestore, store
from app.auth import verify_user_token

from app.gemini import generate_recipe


router = APIRouter()

@router.post("/addRecipe", tags=['Recipes'])
def add_recipe(recipe: Recipe, user = Depends(verify_user_token)):
    save_recipe_for_user(recipe=recipe, user=user['uid'])

@router.get("/generateRecipe", description="Generate a recipe from users personal product list and adds to user collection", tags=['Recipes'])
def generate_recipe_from_products(user = Depends(verify_user_token)):
    uid = user["uid"]

    products_ref = (
        store.collection("users")
        .document(uid)
        .collection("products")
    )

    #https://firebase.google.com/docs/firestore/query-data/get-data
    #https://firebase.google.com/docs/firestore/query-data/get-data#get_all_documents_in_a_collection
    products_document = products_ref.stream()

    products = []
    for document in products_document:
        products.append({"id": document.id, **document.to_dict()})

    recipe_json: Recipe = generate_recipe(products)

    return save_recipe_for_user(recipe=recipe_json, uid=uid)    

@router.get("/getAllRecipes", description="Return a list of all recipe items from the user", tags=['Recipes'])
def get_all_recipes(user=Depends(verify_user_token)):
    uid = user["uid"]
    
    recipes_ref = (
        store.collection('users')
        .document(uid)
        .collection('recipes')
    )

    recipes_document = recipes_ref.stream()

    recipes_list = []
    for document in recipes_document:
        recipes_list.append({"id": document.id, **document.to_dict()})

    return recipes_list





# Helper function for saving recipe to firestore
def save_recipe_for_user(recipe: Recipe, uid: str):
    recipes_ref = (
        store.collection('users').document(uid).collection('recipes')
    )

    doc_ref = recipes_ref.document()
    
    doc_ref.set({
        **recipe.model_dump(),
        "createdAt": firestore.SERVER_TIMESTAMP
    })
    return {"id": doc_ref.id, "message": "Recipe added"}
