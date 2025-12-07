# https://ai.google.dev/gemini-api/docs/quickstart

from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
from app.models.Recipe import Recipe

products = ["Chicken", "Peppers", "Garlic", "Onion"]

load_dotenv()
google_api_key = os.environ["GEMINI_API_KEY"]

client = genai.Client(api_key=google_api_key)

def generate_recipe(products: list[dict]):

    product_names =[]

    for p in products:
        if "name" in p:
            product_names.append(p['name'])

    print(product_names)

    response = client.models.generate_content(
    model="gemini-2.5-flash", 
    config=types.GenerateContentConfig (
        thinking_config=types.ThinkingConfig(thinking_budget=0)
    ),
    contents=f'''
       Use the following products to create a recipe: {product_names}.

        Return ONLY valid JSON representing the recipe.

        RULES:
        - Do NOT include ```json or any code fences.
        - Do NOT include markdown.
        - Do NOT include explanation text.
        - Only output a single JSON object.

        The JSON object must contain:
        - recipeName (string)
        - prepTime (integer)
        - cookTime (integer)
        - servings (integer)
        - ingredients: list of objects with 'name'(str), 'quantity'(int), and 'unit' (str)
        - instructions: list of strings
    '''
    )

    recipe = Recipe.model_validate_json(response.text)

    return recipe
