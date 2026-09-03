# https://ai.google.dev/gemini-api/docs/quickstart

from google import genai
from google.genai import types
from google.genai.errors import ServerError
import os
from typing import Any
from dotenv import load_dotenv
from app.models.Recipe.Recipe import Recipe

load_dotenv()
google_api_key = os.environ["GEMINI_API_KEY"]

client = genai.Client(api_key=google_api_key)

# Different models (in order of preference) tried if there's a 503 ServerError
MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]

def generate_recipe(products: list[dict[str, Any]]):

    product_details =[]

    for p in products:
        product_details.append({
            "id": p['id'],
            "name": p['name'],
            "quantity": p['quantity']
        })

    contents = f'''
       Use the following products to create a creative recipe: {product_details}.
       Make sure this single recipe is distinct, always use at least 1 product

        Return ONLY valid JSON representing the recipe.

        RULES:
        - Do NOT include ```json.
        - Do NOT include markdown.
        - Do NOT include explanation text.
        - Only output a single JSON object.

        The JSON object must contain:
        - recipeName (string)
        - description (string, 1 sentence)
        - prepTime (integer)
        - cookTime (integer)
        - servings (integer)
        - difficulty (string)
        - ingredientsUsed(integer, how many ingredients used from products)
        - ingredients: list of objects with 'name'(str), 'quantity'(int), 'unit' (str), and ONLY IF using provided product 'productId: string' otherwise 'productId: null'
        - instructions: list of strings
    '''

    last_error = None

    #for/else only runs if the loop finishes without break, need loop to iterate through models.
    for model in MODELS:
        try:
            response = client.models.generate_content(
                model=model,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                ),
                contents=contents
            )
            break
        except ServerError as e:
            #Only fall back to the next model on 503 (service unavailable)
            if e.code != 503:
                raise
            last_error = e
    else:
        raise last_error or RuntimeError("MODELS list is empty")

    # when "None" there is no text google treats as optional, so double check it exists before validating
    if response.text is None:
        raise ValueError("Gemini response contained no text content")

    # Retrieved from pydantic documentation: https://docs.pydantic.dev/latest/concepts/json/#json-parsing
    recipe = Recipe.model_validate_json(response.text)

    return recipe
