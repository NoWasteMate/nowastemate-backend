# https://ai.google.dev/gemini-api/docs/quickstart

from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

products = ["Chicken", "Peppers", "Garlic", "Onion"]

load_dotenv()
google_api_key = os.environ["GEMINI_API_KEY"]

client = genai.Client(api_key=google_api_key)

response = client.models.generate_content(
    model="gemini-2.5-flash", 
    config=types.GenerateContentConfig (
        thinking_config=types.ThinkingConfig(thinking_budget=0)
    ),
    contents=f'''
        I have the following products: {products}.

        Please provide a recipe in JSON format that uses these products.

        The JSON should include the following fields:

        recipeName (string)

        prepTime (integer in minutes)

        cookTime (integer in minutes)

        servings (integer)

        ingredients (an array of objects, each with name and quantity)

        instructions (an array of strings for each step)

        ** JUST OUTPUT AS PLAIN TEXT ***
    '''
)

print(response.text)
