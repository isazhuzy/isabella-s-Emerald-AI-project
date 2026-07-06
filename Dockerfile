# Container image for the Emerald web UI — used by Google Cloud Run (or any container
# host: Fly.io, AWS App Runner, Azure Container Apps, a plain Docker VM).
#
# Cloud Run sends requests to the port named in $PORT (default 8080); the app must
# listen on 0.0.0.0:$PORT. Secrets (API keys) are injected as env vars at deploy time,
# NOT baked into the image.
FROM python:3.12-slim

WORKDIR /app

# Install deps first so this layer caches across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code.
COPY . .

# Cloud Run provides PORT; default to 8080 for local `docker run`.
ENV PORT=8080
EXPOSE 8080

# Shell form so ${PORT} is expanded at runtime.
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8080}
