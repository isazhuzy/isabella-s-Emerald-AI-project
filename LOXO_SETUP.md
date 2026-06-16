# Loxo Setup — B1 (Loxo-native sourcing + enrichment + outreach)

This is the **one-time configuration** inside Loxo that makes the sourcing brief
"just work." Emerald (the code) creates the job and the brief; Loxo's **Stage
Automations** do the sourcing-adjacent work: enrich contacts, enroll outreach,
generate AI highlights.

> Why this design: the Open API can't trigger Loxo Source's external search, but
> Loxo's in-app AI search + Stage Automations already do sourcing, ranking,
> enrichment, and outreach. B1 leans on those instead of rebuilding them.

---

## A. Pipeline stages (Settings → Workflow)

Create (or confirm) these two stages in the job pipeline, in order:

| Stage | Who lands here | Enrichment? | Cost |
|---|---|---|---|
| **Sourcing** | the full **75–150** from Loxo Source | ❌ no | free |
| **Outreach** | the **top 15–20** you move forward | ✅ yes | Loxo Credits |

Keeping enrichment on the *second* stage is the **cost-control gate** — you only
spend credits on the shortlist, exactly matching the "enrich top 15–20" spec.

> Stage names must match your `.env`:
> `LOXO_SOURCING_STAGE_NAME=Sourcing`, `LOXO_OUTREACH_STAGE_NAME=Outreach`.

---

## B. Outreach campaign (Outreach → Campaigns)

Create a reusable campaign named to match `LOXO_OUTREACH_CAMPAIGN_NAME`
(default **"Confidential Outreach"**). Paste the steps from section 4 of any
generated Sourcing Brief as the starting template. You refresh this per-search
from the brief; the automation just enrolls people into it.

---

## C. Stage Automation — on entry to "Outreach"

Settings → Workflow → **Outreach** stage → **Automations** → add, triggered by
*"when a candidate enters this stage"*:

1. **Find contact details** (enrichment) — fetches phone/personal+work email via
   Loxo Credits.
2. **Add to campaign** → select the **Confidential Outreach** campaign.
3. **Generate AI highlights** (AI submittal summary) — optional but recommended.

(Optionally add a lighter automation on **Sourcing** entry — e.g. AI highlights
only, no enrichment — if you want highlights on the long list.)

---

## D. The recruiter runbook (per search)

1. Run Emerald on the intake transcript → it creates the **unpublished** Loxo job
   and prints a **Sourcing Brief** (also posted as a job note when
   `LOXO_NOTE_ACTIVITY_TYPE_ID` is set).
2. Open the job → **Loxo Source** → paste the Boolean from the brief → run search.
3. Select the best **75–150** → bulk-move to **Sourcing**.
4. Move the **top 15–20** to **Outreach** → automations enrich + enroll + summarize.
5. Review, then publish the JD / let the campaign send.

The only manual step is step 2 (running the search) — everything after the
stage move is automated.

---

## E. One-time IDs to capture for `.env`

Run these once and copy the IDs into `.env`:

```python
from emerald.loxo import LoxoClient
c = LoxoClient()
print(c.job_types())          # -> LOXO_DEFAULT_JOB_TYPE_ID
print(c.companies("Acme"))    # -> LOXO_DEFAULT_COMPANY_ID
print(c.activity_types())     # -> LOXO_NOTE_ACTIVITY_TYPE_ID (pick a "Note" type)
print(c.compensation_types()) # -> valid salary types
```

| `.env` var | From |
|---|---|
| `LOXO_DEFAULT_JOB_TYPE_ID` | `job_types()` |
| `LOXO_DEFAULT_COMPANY_ID` | `companies(...)` |
| `LOXO_NOTE_ACTIVITY_TYPE_ID` | `activity_types()` — a "Note" type |
| `LOXO_SOURCING_STAGE_NAME` / `LOXO_OUTREACH_STAGE_NAME` | must match section A |
| `LOXO_OUTREACH_CAMPAIGN_NAME` | must match section B |

---

## What's still manual / out of scope (would be B2)

- Triggering the Loxo Source search itself (no API) → recruiter clicks once.
- Fully headless sourcing from external providers (Clay / Apollo / PDL) →
  the `add_to_pipeline()` client method is already in place for that pivot.
