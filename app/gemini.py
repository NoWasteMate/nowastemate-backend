# https://ai.google.dev/gemini-api/docs/quickstart

from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
from app.models.Recipe.Recipe import Recipe

load_dotenv()
google_api_key = os.environ["GEMINI_API_KEY"]

client = genai.Client(api_key=google_api_key)

def generate_recipe(products: list[dict]):

    product_details =[]

    for p in products:
        product_details.append({
            "id": p['id'],
            "name": p['name'],
            "quantity": p['quantity']
        })

    response = client.models.generate_content(
    model="gemini-2.5-flash", 
    config=types.GenerateContentConfig (
        thinking_config=types.ThinkingConfig(thinking_budget=0)
    ),
    contents=f'''
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
        - category (string, exactly one of: "soup", "salad", "pasta", "handheld", "breakfast", "dessert", "drink", "platedMain", "general" — pick "general" if nothing else fits)
    '''
    )

    # Retrieved from pydantic documentation: https://docs.pydantic.dev/latest/concepts/json/#json-parsing
    recipe = Recipe.model_validate_json(response.text)

    return recipe
