from fastapi import HTTPException, status
from urllib.parse import quote
from uuid import uuid4

from app.models.Recipe.Recipe import Recipe
from app.models.Product import ProductOutcome
from app.firebase import bucket, firestore, store

from app.openrouter import generate_recipe, generate_recipe_image
from app.vocabulary.normalize import normalize_name


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
            self.add_recipe_image(uid=uid, recipe_id=saved["id"], recipe=recipe_json)
        except Exception as e:
            print(f"Recipe image failed for {saved['id']}: {e}")

        return saved

    def add_recipe_image(self, uid: str, recipe_id: str, recipe: Recipe):
        image = generate_recipe_image(recipe)
        # https://docs.cloud.google.com/storage/docs/uploading-objects-from-memory#storage-upload-object-from-memory-python
        filename = f"recipes/{uid}/{recipe_id}.webp"
        blob = bucket.blob(filename)

        # Store a random download token which follows the Node upload example
        # https://www.sentinelstand.com/article/guide-to-firebase-storage-download-urls-tokens
        token = str(uuid4())
        blob.metadata = {"firebaseStorageDownloadTokens": token}

        blob.upload_from_string(image, content_type="image/webp")

        # The article encodes the full filename with "encodeURIComponent"
        # I had to find a python equivalence so I used Python's quote() for this, with safe="" to encode slashes too
        # The result is recipes/user/id.webp -> recipes%2Fuser%2Fid.webp
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

        # Only generated recipes get to have an image
        if recipe_doc.to_dict().get("imageUrl"):
            # https://docs.cloud.google.com/storage/docs/deleting-objects#storage-delete-object-python
            bucket.blob(f"recipes/{uid}/{recipe_id}.webp").delete()

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
