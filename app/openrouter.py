# https://openrouter.ai/docs/quickstart

from google import genai
from google.genai import types
import base64
import json
import os
import requests
from typing import Any
from dotenv import load_dotenv
from app.models.Recipe.Recipe import Recipe
from app.models.Recipe.GenerateRecipeRequest import GenerateRecipeRequest

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

# Recraft API lists WebP as the default image format
# https://www.recraft.ai/docs/api-reference/models/recraft-v4-1-flash.md
IMAGE_MODEL = "recraft/recraft-v4.1-flash-v2"

# Recraft Flash has no style option so the look comes from the prompt
# Opus 5.5 helped structure this prompt in an LLM friendly way similar to the image research Confluence doc prompts used for testing
IMAGE_STYLE = """
    Medium-wide editorial food photograph for a food magazine, from a 45 degree angle.
    Plated on a simple ceramic plate on a clean wooden or stone surface.
    Soft natural window light from the side, shallow depth of field, sharp focus on the food.
    Appetizing, fresh and neatly styled, with a few matching ingredients around the plate.
    Warm and true to life colours.
    Show the entire plate, including its complete rim, centered in the frame.
    The plate occupies roughly 70% of the image width, with visible tabletop on all four sides.
    Camera pulled back.
    No people, no hands, no text, no logos, no watermarks.
"""

# Adapted from my own cooking notes. Pushes the model toward flavour instead of only mixing the products
# A salad or drink won't need most of these
FLAVOUR_RULES = """
    - Brown meat and vegetables for flavour, then deglaze the fond into the sauce.
    - In cooked sauces, sweat or brown the onion before liquid goes in, and add garlic for the last minute so it doesn't burn.
    - Heat the oil until shimmering, then fry tomato, chile or curry pastes until they darken and the oil separates.
    - Toast whole spices, grains and nuts before liquid goes in. Bloom ground spices in fat for 10 to 15 seconds.
    - Concentrate flavour: reduce sauces, use stock instead of water, and add umami boosters where they fit.
    - Season in layers with salt at each stage, then finish with acid, fresh herbs or fat.
    - Account for the salt in stock, bouillon and spice blends before adding more.
    - Give temperatures and doneness cues in the instructions, not only times.
"""


# Profile restrictions that are a diet to follow. Everything else (Egg, Peanut, ...) is an ingredient to avoid
DIETS = {"Keto", "Paleo", "Pescetarian", "Raw", "Vegan", "Vegetarian"}


def build_generation_options_rules(options: GenerateRecipeRequest, dietary_restrictions: list[str]):
    avoided_ingredients = []
    diets = []
    for restriction in dietary_restrictions:
        if restriction in DIETS:
            diets.append(restriction)
        else:
            avoided_ingredients.append(restriction)

    rules = []

    if avoided_ingredients:
        rules.append(f"- The recipe must not contain {', '.join(avoided_ingredients)}, including in pantry staples and sauces. Leave out any product that does.")
    if diets:
        rules.append(f"- The recipe must follow these diets: {', '.join(diets)}.")
    if options.mealType:
        rules.append(f'- category must be "{options.mealType.value}". Only use the products that suit this kind of dish.')
    if options.difficulty:
        rules.append(f'- difficulty must be "{options.difficulty.value}".')
    if options.maxTotalTime:
        rules.append(f"- prepTime plus cookTime must be {options.maxTotalTime} minutes or less.")
    if options.servings:
        rules.append(f"- The recipe must make {options.servings} servings.")
    if options.expiringFirst:
        rules.append("- Prefer the products with the lowest daysUntilExpiry, but only when they suit the dish.")

    return "\n".join(rules)


def generate_recipe(products: list[dict[str, Any]], options: GenerateRecipeRequest, dietary_restrictions: list[str]):

    product_details =[]

    for p in products:
        detail = {
            "id": p['id'],
            "name": p['name'],
            "quantity": p['quantity']
        }
        if "daysUntilExpiry" in p:
            detail["daysUntilExpiry"] = p["daysUntilExpiry"]
        product_details.append(detail)

    options_rules = build_generation_options_rules(options, dietary_restrictions)

    contents = f'''
       Create a realistic recipe that a home cook would actually make, using some of these products: {product_details}.
       First pick a well-known dish from a real cuisine that suits some of the products, then use only the products that belong in that dish.
       It's fine to use only one or two products. Never force in a product that doesn't belong just to use it up.

        Return ONLY valid JSON representing the recipe.

        RULES:
        - Do NOT include ```json.
        - Do NOT include markdown.
        - Do NOT include explanation text.
        - Only output a single JSON object.
        - The ingredients list must include every ingredient used in the instructions, including pantry staples like oil, salt, garlic or soy sauce.
        {options_rules}

        COOKING FUNDAMENTALS (use the ones that fit the dish):
        {FLAVOUR_RULES}

        The JSON object must contain:
        - recipeName (string)
        - description (string, 1 sentence)
        - prepTime (integer)
        - cookTime (integer)
        - servings (integer)
        - difficulty (string, exactly one of: "easy", "medium", "hard")
        - ingredientsUsed(integer, how many ingredients used from products)
        - ingredients: list of objects with 'name'(str, the plain ingredient name with no brand, size or preparation, e.g. "chicken breast"), 'quantity'(int), 'unit' (str), and ONLY IF using provided product 'productId: string' otherwise 'productId: null'
        - instructions: list of strings
        - category (string, exactly one of: "soup", "salad", "pasta", "handheld", "breakfast", "dessert", "drink", "platedMain", "general". Pick "general" if nothing else fits)
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


def generate_recipe_image(recipe: Recipe):
    prompt = f'''
        {recipe.recipeName}, a {recipe.category.value} dish.
        {recipe.description}
        {IMAGE_STYLE}
    '''

    # From Step 2
    # https://openrouter.ai/blog/tutorials/image-generation/
    response = requests.post(
        url="https://openrouter.ai/api/v1/images",
        headers={
            "Authorization": f"Bearer {openrouter_api_key}",
            "Content-Type": "application/json"
        },
        # https://openrouter.ai/recraft/recraft-v4.1-flash-v2?view=api#api
        data=json.dumps({
            "model": IMAGE_MODEL,
            "prompt": prompt,
            "aspect_ratio": "3:4",
        })
    )
    response.raise_for_status()

    # From Step 3
    # https://openrouter.ai/blog/tutorials/image-generation/
    image_base64 = response.json()["data"][0]["b64_json"]

    return base64.b64decode(image_base64)
