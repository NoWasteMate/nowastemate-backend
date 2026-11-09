from fastapi import HTTPException, status
from urllib.parse import quote, unquote
from uuid import uuid4

from app.models.Recipe.Recipe import Recipe
from app.models.Product import ProductOutcome
from app.firebase import bucket, firestore, store

from app.openrouter import generate_recipe, generate_recipe_image
from app.vocabulary.normalize import normalize_name
from app.vocabulary.product_types import PRODUCT_TYPES
from app.actions.family_actions import family_actions
from app.actions.product_actions import product_actions

MAX_MISSING = 2
MAX_SUGGESTIONS = 3


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

    def generate_recipe_from_products(self, uid: str, product_ids: list[str]):
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

            # only use the products the user picked
            if document.id not in product_ids:
                continue

            products.append({"id": document.id, **data})

        recipe_json: Recipe = generate_recipe(products)

        products_by_id = {}
        for product in products:
            products_by_id[product["id"]] = product

        # copies the type from the product the model used, otherwise matches the ingredient name
        for ingredient in recipe_json.ingredients:
            product = products_by_id.get(ingredient.productId)
            if product:
                ingredient.productType = product.get("productType")
            else:
                # The model sometimes makes up ids that aren't the user's products
                ingredient.productId = None

            if not ingredient.productType:
                product_type, _product_type_source = normalize_name(ingredient.name)
                ingredient.productType = product_type

        saved = self.save_recipe_for_user(recipe=recipe_json, uid=uid)

        # The recipe is already saved, so a failed image just leaves imageUrl empty
        try:
            image_url = self.add_recipe_image(uid=uid, recipe_id=saved["id"], recipe=recipe_json)
            recipe_json.imageUrl = image_url
        except Exception as e:
            print(f"Recipe image failed for {saved['id']}: {e}")

        # A failed pool write only keeps this recipe out of the pool
        try:
            pool_id = self.add_recipe_to_pool(recipe=recipe_json)
            if pool_id:
                recipe_ref = (
                    store.collection('users')
                    .document(uid)
                    .collection('recipes')
                    .document(saved["id"])
                )
                recipe_ref.update({"poolId": pool_id})
        except Exception as e:
            print(f"Recipe pool write failed for {saved['id']}: {e}")

        return saved

    def add_recipe_to_pool(self, recipe: Recipe, is_curated: bool = False):
        # Suggestions match on product types and can't use an ingredient without one
        product_types = []
        for ingredient in recipe.ingredients:
            if not ingredient.productType:
                return None
            product_types.append(ingredient.productType)

        # Sorted with no repeats so the same types in any order give the same key
        sorted_types = sorted(set(product_types))
        clean_name = recipe.recipeName.strip().lower()
        types_text = ",".join(sorted_types)
        pool_key = f"{clean_name}|{types_text}"

        pool_ref = store.collection("recipePool")

        # https://firebase.google.com/docs/firestore/query-data/queries#simple_queries
        # https://firebase.google.com/docs/firestore/query-data/order-limit-data
        duplicate_query = pool_ref.where(filter=firestore.FieldFilter("poolKey", "==", pool_key)).limit(1)
        duplicates = duplicate_query.get()
        if duplicates:
            return None

        # ingredientsUsed is kept so pool docs still read back as a Recip
        pool_recipe = recipe.model_dump(exclude={"poolId"})
        for ingredient in pool_recipe["ingredients"]:
            # productId points into the generating user's products so it shouldn't be copied. del as per pydantic docs.
            del ingredient["productId"]

        doc_ref = pool_ref.document()
        doc_ref.set({
            **pool_recipe,
            "productTypes": sorted_types,
            "poolKey": pool_key,
            "isCurated": is_curated,
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        return doc_ref.id

    def add_recipe_image(self, uid: str, recipe_id: str, recipe: Recipe):
        image = generate_recipe_image(recipe)
        # https://docs.cloud.google.com/storage/docs/uploading-objects-from-memory#storage-upload-object-from-memory-python
        # Not under the uid because the pool copy of the recipe shares this file
        filename = f"recipeImages/{recipe_id}.webp"
        blob = bucket.blob(filename)

        # Store a random download token which follows the Node upload example
        # https://www.sentinelstand.com/article/guide-to-firebase-storage-download-urls-tokens
        token = str(uuid4())
        blob.metadata = {"firebaseStorageDownloadTokens": token}

        blob.upload_from_string(image, content_type="image/webp")

        # The article encodes the full filename with "encodeURIComponent"
        # I had to find a python equivalence so I used Python's quote() for this, with safe="" to encode slashes too
        # The result is recipeImages/id.webp -> recipeImages%2Fid.webp
        # https://www.sentinelstand.com/article/guide-to-firebase-storage-download-urls-tokens
        # https://docs.python.org/3/library/urllib.parse.html#urllib.parse.quote
        encoded_name = quote(filename, safe="")
        image_url = (f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/{encoded_name}?alt=media&token={token}")

        recipe_ref = (
            store.collection('users')
            .document(uid)
            .collection('recipes')
            .document(recipe_id)
        )
        recipe_ref.update({"imageUrl": image_url})
        return image_url

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

        recipe = recipe_doc.to_dict()
        image_url = recipe.get("imageUrl")
        storage_prefix = f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/"

        # Pool recipes share the image, so only delete it when nothing else uses it
        is_our_file = image_url and image_url.startswith(storage_prefix)
        if is_our_file and not recipe.get("poolId"):
            # Older images are under recipes/{uid}/, so read the path from the URL
            path_and_query = image_url.removeprefix(storage_prefix)
            encoded_name = path_and_query.split("?")[0]
            # https://docs.python.org/3/library/urllib.parse.html#urllib.parse.unquote
            filename = unquote(encoded_name)

            # Clients can set imageUrl through /addRecipe, so it could point at someone else's file
            own_image_paths = [f"recipeImages/{recipe_id}.webp", f"recipes/{uid}/{recipe_id}.webp"]
            if filename in own_image_paths:
                # https://docs.cloud.google.com/storage/docs/deleting-objects#storage-delete-object-python
                bucket.blob(filename).delete()

        recipe_ref.delete()
        return {"Success": f"Removed recipe with id {recipe_id}"}

    def get_suggested_recipes(self, uid: str):
        if family_actions.get_family_uids(uid) is None:
            products = product_actions.get_products(uid)
        else:
            products = product_actions.get_family_products(uid)
        owned_types = self.get_owned_product_types(products)

        saved_pool_ids = []
        for saved_recipe in self.get_all_recipes(uid):
            saved_pool_ids.append(saved_recipe.get("poolId"))

        suggestions = []
        for document in store.collection("recipePool").stream():
            if document.id in saved_pool_ids:
                continue

            data = document.to_dict()
            missing = 0
            owned = 0
            for ingredient in data["ingredients"]:
                product_type = ingredient.get("productType")
                if product_type in owned_types:
                    owned += 1
                else:
                    missing += 1

            if missing > MAX_MISSING:
                continue

            # Pydantic ignores extra fields like poolKey
            # https://pydantic.dev/docs/validation/latest/concepts/models/#extra-data
            #
            suggestion = Recipe.model_validate(data).model_dump()
            suggestion["id"] = document.id
            suggestion["poolId"] = document.id
            # Not on the Recipe model but the app needs it to decode
            suggestion["createdAt"] = data["createdAt"]
            suggestion["ingredientsUsed"] = owned
            suggestion["missingCount"] = missing
            suggestions.append(suggestion)

        # Ties keep their order from the first sort. Used helper functions to get counts.
        suggestions.sort(key=self.get_suggestion_owned_count, reverse=True)
        suggestions.sort(key=self.get_suggestion_missing_count)

        return suggestions[:MAX_SUGGESTIONS]

    def save_suggested_recipe(self, uid: str, pool_id: str):
        pool_doc = store.collection("recipePool").document(pool_id).get()
        if not pool_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unable to find pool recipe Id: {pool_id}"
            )

        recipe = Recipe.model_validate(pool_doc.to_dict())
        recipe.poolId = pool_id

        return self.save_recipe_for_user(recipe=recipe, uid=uid)

    def get_suggestion_owned_count(self, suggestion: dict):
        return suggestion["ingredientsUsed"]

    def get_suggestion_missing_count(self, suggestion: dict):
        return suggestion["missingCount"]

    def get_owned_product_types(self, products: list[dict]):
        owned_types = set()
        to_visit = []
        for product in products:
            to_visit.append(product.get("productType"))

        # A type only lists its direct parents so keep adding them until none are left.
        # chicken-breast adds chicken-meat then chicken, so it counts for a recipe needing just "chicken"
        while to_visit:
            product_type = to_visit.pop()
            if product_type is None or product_type in owned_types:
                continue
            owned_types.add(product_type)
            parent_types = PRODUCT_TYPES.get(product_type, {}).get("parents", [])
            to_visit.extend(parent_types)
        return owned_types

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
