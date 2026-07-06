# Deploy Emerald to Google Cloud Run

Cloud Run runs the container from the repo's [`Dockerfile`](../Dockerfile) and scales it
automatically — including **down to zero** when idle (you pay only while it's handling
requests). Same app as `render.yaml`, different host; pick one.

## One-time setup
1. Install the gcloud CLI and log in: `gcloud auth login`
2. Pick/create a project: `gcloud config set project <PROJECT_ID>`
3. Enable the APIs: `gcloud services enable run.googleapis.com cloudbuild.googleapis.com`

## Store secrets (Secret Manager — don't put keys on the command line)
```bash
printf '%s' 'sk-ant-...'    | gcloud secrets create ANTHROPIC_API_KEY --data-file=-
printf '%s' '<seamless>'    | gcloud secrets create SEAMLESS_API_KEY  --data-file=-
printf '%s' '<loxo-token>'  | gcloud secrets create LOXO_API_KEY      --data-file=-
# ...repeat for FIREFLIES_API_KEY, FIREFLIES_WEBHOOK_SECRET
```

## Deploy (builds the Dockerfile, then runs it)
```bash
gcloud run deploy emerald \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-secrets 'ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest,SEAMLESS_API_KEY=SEAMLESS_API_KEY:latest,LOXO_API_KEY=LOXO_API_KEY:latest,FIREFLIES_API_KEY=FIREFLIES_API_KEY:latest,FIREFLIES_WEBHOOK_SECRET=FIREFLIES_WEBHOOK_SECRET:latest' \
  --set-env-vars 'EMERALD_MODEL=claude-opus-4-8,EMERALD_UI_PASSWORD=emerald,LOXO_DOMAIN=app.loxo.co,LOXO_SLUG=emerald-resource-group,LOXO_DEFAULT_JOB_TYPE_ID=9774,LOXO_DEFAULT_COMPANY_ID=8431133,LOXO_NOTE_ACTIVITY_TYPE_ID=87302'
```
You get an HTTPS URL like `https://emerald-xxxxx-uc.a.run.app`.

## Tuning for the long-running pipeline
A pipeline run can take 30–60s, so bump the request timeout and give it a little RAM:
```bash
gcloud run services update emerald --region us-central1 \
  --timeout 300 --memory 1Gi --concurrency 4 --min-instances 0
```
- `--timeout 300` — allow up to 5 min per request (default 300 is usually fine).
- `--min-instances 0` — scale to zero (cheapest; first hit cold-starts). Set `1` to keep it warm (small always-on cost).
- `--concurrency` — requests per instance; Cloud Run adds instances beyond that.

## Cost shape
- **Idle:** ~$0 with `--min-instances 0` (scales to zero).
- **In use:** billed per request-time (vCPU/memory-seconds); low for this workload.
- Headcount doesn't matter — it's per compute, and it auto-scales for concurrent users.
