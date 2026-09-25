from fastapi import HTTPException, status

from app.models.Recipe.Recipe import Recipe
from app.models.Product import ProductOutcome
from app.firebase import firestore, store

from app.gemini import generate_recipe


class RecipeActions:

    def seed_recipes(self, uid: str, recipes: list[Recipe]):
        recipes_ref = (
            store.collection("users")
            .document(uid)
            .collection("recipes")
        )

        batch = store.batch()

        for recipe in recipes:
            recipe_ref = recipes_ref.document()
            batch.set(recipe_ref, {
                **recipe.model_dump(),
                "createdAt": firestore.SERVER_TIMESTAMP
            })

        batch.commit()

        return {
            "message": "seed complete"
        }

    def add_recipe(self, uid: str, recipe: Recipe):
        return self.save_recipe_for_user(recipe=recipe, uid=uid)

    def generate_recipe_from_products(self, uid: str):
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
            data = document.to_dict()

            # only use active products
            if data.get("outcome", ProductOutcome.active.value) != ProductOutcome.active.value:
                continue

            products.append({"id": document.id, **data})

        recipe_json: Recipe = generate_recipe(products)

        return self.save_recipe_for_user(recipe=recipe_json, uid=uid)

    def get_all_recipes(self, uid: str):
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

    def remove_recipe_by_id(self, uid: str, recipe_id: str):
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

    # Helper for saving recipe to firestore
    def save_recipe_for_user(self, recipe: Recipe, uid: str):
        recipes_ref = (
            store.collection('users').document(uid).collection('recipes')
        )

        doc_ref = recipes_ref.document()

        doc_ref.set({
            **recipe.model_dump(),
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        return {"id": doc_ref.id, "message": "Recipe added"}


recipe_actions = RecipeActions()
