from fastapi import APIRouter, Depends, HTTPException, status

from app.models.Recipe.Recipe import Recipe
from app.firebase import firestore, store
from app.auth import verify_user_token

from app.gemini import generate_recipe


router = APIRouter()

@router.post("/addRecipe", tags=['Recipes'])
def add_recipe(recipe: Recipe, user = Depends(verify_user_token)):
    save_recipe_for_user(recipe=recipe, user=user['uid'])

@router.post("/generateRecipe", description="Generate a recipe from users personal product list and adds to user collection", tags=['Recipes'])
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



@router.delete("/deleteRecipe/{recipe_id}", description="Remove recipe from user by ID", tags=['Recipes'])
def remove_recipe_by_id(recipe_id: str, user = Depends(verify_user_token)):
    uid = user["uid"]

    recipe_ref = (
        store.collection('users')
        .document(uid)
        .collection('recipes')
        .document(recipe_id)
    )
    # https://firebase.google.com/docs/firestore/query-data/get-data#get_a_document
    # Information for error handling, response was always stating success

    recipe_doc = recipe_ref.get()

    # Error handling if recipe can't be found
    if not recipe_doc.exists:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unable to find Recipe Id: {recipe_id}",
            headers={"WWW-Authenticate": "Bearer"}
        )

    recipe_ref.delete()
    return {"Success": f"Removed recipe with id {recipe_id}"}
    


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
