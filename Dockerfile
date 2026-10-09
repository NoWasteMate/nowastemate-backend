# https://raw.githubusercontent.com/GoogleCloudPlatform/python-docs-samples/main/run/helloworld/Dockerfile
FROM python:3.14-slim

# https://firebase.google.com/docs/hosting/cloud-run, unbuffered so logs appear immediately in Cloud Logging
ENV PYTHONUNBUFFERED True

ENV APP_HOME /app
WORKDIR $APP_HOME

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# WordNet data for lemmatizing in app/vocabulary/normalize.py, downloaded here so Cloud Run never fetches it at runtime
# https://www.nltk.org/data.html#command-line-installation
RUN python -m nltk.downloader -d /usr/local/share/nltk_data wordnet

COPY . ./

# https://cloud.google.com/run/docs/container-contract#port
CMD exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
