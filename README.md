<img width="121" height="121" alt="Image" src="https://github.com/user-attachments/assets/25fc2caf-6bfe-4179-9a6b-614779a6fba3" />

# NoWasteMate Backend

FastAPI backend for NoWasteMate. Uses Firebase (Auth, Firestore, Storage) and OpenRouter/Gemini for recipes.

## Requirements

- Python 3.14
- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install)
- Access to the `nowastemate` Firebase project
- An [OpenRouter API key](https://openrouter.ai/settings/keys) and a [Gemini API key](https://aistudio.google.com/apikey)

## Run locally

1. Install the packages:
   ```sh
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Download the WordNet data used by `app/vocabulary/normalize.py`:
   ```sh
   python -m nltk.downloader wordnet
   ```
3. Sign in to Google Cloud. The Firebase Admin SDK uses these credentials, so no key file is needed:
   ```sh
   gcloud auth application-default login
   gcloud config set project nowastemate
   gcloud auth application-default set-quota-project nowastemate
   ```
4. Create a `.env` file in the repo root:
   ```
   OPENROUTER_API_KEY=...
   GEMINI_API_KEY=...
   ```
5. Start the server:
   ```sh
   fastapi dev app/main.py
   ```

The API runs at `http://127.0.0.1:8000`, with docs at `http://127.0.0.1:8000/docs`.

## Using it from the app

To test on a real iPhone on the same Wi-Fi, start the server with `fastapi dev app/main.py --host 0.0.0.0`, then point the app at it. See [Using a local backend](https://github.com/NoWasteMate/nowastemate-app#using-a-local-backend).

## Deployment

Every merge to `main` deploys to Cloud Run (`nowastemate-backend-git`, `northamerica-northeast2`) using the `Dockerfile`. API keys come from Secret Manager there, not `.env`.

Make sure to never commit `.env`!
