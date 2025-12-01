# https://ai.google.dev/gemini-api/docs/quickstart

# ❯ pip install python-dotenv
# ❯ pip install -q -U google-genai

from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
google_api_key = os.environ["GEMINI_API_KEY"]

client = genai.Client(api_key=google_api_key)

response = client.models.generate_content(
    model="gemini-2.5-pro", 
    contents="Generate a recipe based on the following: Provide your response in JSON format"
)

response = client.models.generate_images(
    model='imagen-3.0-generate-002',
    prompt=f'response.text'
)
print(response.text)
