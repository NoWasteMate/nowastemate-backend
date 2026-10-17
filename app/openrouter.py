# https://openrouter.ai/docs/quickstart

from google import genai
from google.genai import types
import json
import os
import requests
from typing import Any
from dotenv import load_dotenv
from app.models.Recipe.Recipe import Recipe

load_dotenv()
openrouter_api_key = os.environ["OPENROUTER_API_KEY"]
google_api_key = os.environ["GEMINI_API_KEY"]

gemini_client = genai.Client(api_key=google_api_key)

# OpenRouter tries the next model when one is down or rate limited
# https://openrouter.ai/docs/guides/routing/model-fallbacks
MODELS = ["deepseek/deepseek-v4.1-flash", "google/gemini-3.1-flash-lite"]

# Called straight through Google only if OpenRouter itself fails
# https://ai.google.dev/gemini-api/docs/quickstart
GEMINI_FALLBACK_MODEL = "gemini-3.5-flash"

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
       Make sure this single recipe is distinct, and use as many of these products as make sense together

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
        - ingredients: list of objects with 'name'(str, the plain ingredient name with no brand, size or preparation, e.g. "chicken breast"), 'quantity'(int), 'unit' (str), and ONLY IF using provided product 'productId: string' otherwise 'productId: null'
        - instructions: list of strings
        - category (string, exactly one of: "soup", "salad", "pasta", "handheld", "breakfast", "dessert", "drink", "platedMain", "general" — pick "general" if nothing else fits)
    '''

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openrouter_api_key}"
            },
            data=json.dumps({
                "models": MODELS,
                "messages": [
                    {
                        "role": "user",
                        "content": contents
                    }
                ],
                # Gemini 3.5 Flash isn't a fallback because it can't turn thinking off
                # https://openrouter.ai/docs/guides/best-practices/reasoning-tokens
                "reasoning": {"effort": "none"}
            })
        )
        response.raise_for_status()

        text = response.json()["choices"][0]["message"]["content"]
    except requests.RequestException:
        gemini_response = gemini_client.models.generate_content(
            model=GEMINI_FALLBACK_MODEL,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0)
            ),
            contents=contents
        )
        text = gemini_response.text

    # content can be null, so double check it exists before validating
    if text is None:
        raise ValueError("Model response contained no text content")

    # Retrieved from pydantic documentation: https://docs.pydantic.dev/latest/concepts/json/#json-parsing
    recipe = Recipe.model_validate_json(text)

    return recipe
