# Emerald

Intake-call → recruiting deliverables pipeline.

Takes a meeting/call **transcript** and produces a ready-to-use sourcing package:

- ✅ **Anonymous (confidential) JD** — written to Loxo as an *unpublished* job
- ✅ **Ad copy** tailored for **LinkedIn, Indeed, and DocCafe**
- ✅ **Outreach campaign drafts** (email/InMail/SMS sequence)
- ✅ **Boolean strings** (generic + LinkedIn + Google X-ray + Loxo Source), saved for re-use
- ✅ **Search criteria** extracted from the call (feeds sourcing)

```
transcript ──▶ Claude (structured JSON) ──▶ redaction safety-net ──▶ Loxo (unpublished job + notes)
                 JD · ad copy ×3 · outreach · booleans · criteria
```

## What this does / doesn't do

This is **Phase 1** — everything that's 100% buildable through the Loxo **Open API**:
generating the text deliverables and writing the job + assets into Loxo.

**Not** in Phase 1 (by design): sourcing 75–150 candidates, AI ranking, and contact
enrichment. Loxo's Open API can't search its external 1.2B-profile graph or run
enrichment — those are **Loxo-native** features driven by **Stage Automations**.
The `search_criteria` this pipeline emits is what you feed into Loxo Source to kick
that off. See "Phase 2" below.

## Quick start

```bash
# 0. (optional) virtualenv
python3 -m venv .venv && source .venv/bin/activate

# 1. runs out of the box in MOCK mode — no keys, no installs needed:
python3 run.py examples/sample_transcript.txt --client "Acme Health System"

# 2. real generation: install deps + set keys
pip install -r requirements.txt
cp .env.example .env        # then fill in ANTHROPIC_API_KEY (+ Loxo creds)
python3 run.py examples/sample_transcript.txt --client "Acme Health System"

# 3. also create the (unpublished) job in Loxo:
python3 run.py examples/sample_transcript.txt --client "Acme Health System" --push
```

Every run drops a full JSON artifact in `output/` (gitignored).

## Configuration (`.env`)

| Var | Needed for | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | real generation | else falls back to mock output |
| `EMERALD_MODEL` | generation | set to a current model id you can access |
| `LOXO_DOMAIN`, `LOXO_SLUG` | `--push` | base URL is `https://{DOMAIN}/api/{SLUG}` |
| `LOXO_API_KEY` | `--push` | Loxo → **Settings → API Keys** (admin only) |
| `LOXO_DEFAULT_JOB_TYPE_ID` | `--push` | Loxo requires it; discover via `client.job_types()` |
| `LOXO_DEFAULT_COMPANY_ID` | `--push` | Loxo requires a company assignment |

> ⚠️ The Open API lives under `/api/{slug}`. The `/api/v1/...` path is **not** part
> of the Open API and returns **403** — the client guards against this.

To discover the IDs Loxo requires:

```python
from emerald.loxo import LoxoClient
c = LoxoClient()
print(c.job_types())          # -> pick a job_type_id
print(c.compensation_types()) # -> valid salary types
print(c.companies("Acme"))    # -> find/confirm a company_id
```

## Layout

```
run.py                  CLI entrypoint
server.py               optional FastAPI webhook (transcription provider -> pipeline)
emerald/
  config.py             env settings (+ Loxo base-url / 403 guard)
  generate.py           Claude call -> structured deliverables (+ offline mock)
  redact.py             deterministic anonymization safety-net
  loxo.py               Loxo Open API client (create job, notes, discovery)
  pipeline.py           orchestrator: generate -> redact -> (optional) Loxo -> artifact
examples/
  sample_transcript.txt
output/                 generated artifacts (gitignored)
```

## Wiring in live transcription

`server.py` exposes `POST /webhook/transcript`. Point a transcription vendor at it
(Recall.ai bot, AssemblyAI, Fireflies, etc.) and adapt `extract_transcript()` to the
provider's payload shape.

```bash
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
```

## Phase 2 / B1 — Loxo-native sourcing (implemented)

B1 leans on Loxo's own AI search + **Stage Automations** instead of rebuilding
sourcing/enrichment. Emerald creates the job and emits a **Sourcing Brief**; Loxo
does the rest.

**Flow:**
```
Emerald: create job (unpublished) + Sourcing Brief
   └─ recruiter: paste Boolean → Loxo Source → select 75–150 → "Sourcing" stage
        └─ move top 15–20 → "Outreach" stage
             └─ Stage Automation: enrich contacts + enroll campaign + AI highlights
```

- Every run writes `output/<job>_sourcing-brief.md` — the recruiter's runbook
  (Boolean to paste, target stages, outreach content).
- On `--push`, the brief is also posted as a **note on the Loxo job** (needs
  `LOXO_NOTE_ACTIVITY_TYPE_ID`).
- **Cost control:** enrichment runs only on the "Outreach" stage, so only the top
  `EMERALD_ENRICH_TOP_N` (default 20) consume Loxo Credits.

➡️ **One-time Loxo config is in [`LOXO_SETUP.md`](./LOXO_SETUP.md)** — pipeline
stages, the outreach campaign, and the Stage Automation.

### Later: B2 (fully headless)

If you outgrow the one-click search, the `LoxoClient.add_to_pipeline()` /
`get_job_pipeline()` methods are already in place to push externally-sourced,
ranked candidates (Clay / Apollo / PDL) straight into the pipeline. Not built yet.

## Safety / compliance notes

- Jobs are created **unpublished** — review before going live (confidential searches).
- Redaction is two-layer: the model is instructed to anonymize **and** `redact.py`
  scrubs known identifiers as a backstop. Check `redaction_hits` in the artifact.
- Don't scrape LinkedIn. Use licensed data (Loxo's graph / compliant providers).
- Loxo Open API access is a **paid** feature.
