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

These already exist in the Emerald Resource Group workflow — just confirm they're
present and used in this order:

| Stage | Who lands here | Enrichment? | Cost |
|---|---|---|---|
| **Long List** | the full **75–150** sourced across channels | ❌ no | free |
| **Short List** | the **top 15–20** you move forward | ✅ yes | Loxo Credits |

Keeping enrichment on the *second* stage is the **cost-control gate** — you only
spend credits on the shortlist, exactly matching the "enrich top 15–20" spec.

> Stage names must match your `.env`:
> `LOXO_SOURCING_STAGE_NAME=Long List`, `LOXO_OUTREACH_STAGE_NAME=Short List`.
> (Candidates are sourced via the channel stages — LinkedIn OW, LinkedIn Non-OW,
> Indeed Database, Loxo Source — then collected onto **Long List**.)

---

## B. Outreach campaign (Outreach → Campaigns)

Create a reusable campaign named to match `LOXO_OUTREACH_CAMPAIGN_NAME`
(default **"Confidential Outreach"**). Paste the steps from section 4 of any
generated Sourcing Brief as the starting template. You refresh this per-search
from the brief; the automation just enrolls people into it.

---

## C. The "Short List" actions (semi-manual — see reality note)

> ⚠️ **Reality check (verified in the live account, agency 3156):** Loxo does NOT
> have a single "on stage entry, enrich + enroll in campaign + AI highlights"
> automation. The Workflow **activities** feature only maps *activity → stage
> progression* (all built-in types); **Data enrichment** is the Contact Finding
> Agent invoked by a manual **Fetch Contacts** action; campaign enrollment is a
> manual **Add to Campaign** bulk action. So the cost gate is enforced by *where
> you click*, not by an automation. The steps below reflect what actually exists.

When the top 15–20 are on **Short List**, the recruiter does (bulk-select them):

1. **Fetch Contacts** (enrichment) — the Contact Finding Agent fetches phone /
   personal+work email and spends **Loxo Credits**. Doing this *only* on Short List
   is the cost-control gate. (Account-wide enrichment behavior: Settings → Data
   enrichment → Contact Finding Agent.)
2. **Add to Campaign** → select **Confidential Outreach** (the campaign must have
   stages with content + a synced sending email to actually send — see B).
3. **Generate AI highlights** (AI submittal summary) — via the candidate's AI
   actions, optional but recommended.

**Optional partial automation:** Settings → **Email Automation** → **Add** →
**Add Stage** → *Short List* will auto-send a *single* templated email to a
candidate's preferred email when they reach Short List. It does not enrich and is
not a multi-step sequence, and it only works once contacts are enriched + a sender
email is synced — so it's a nice-to-have, not the core flow.

---

## D. The recruiter runbook (per search)

1. Run Emerald on the intake transcript → it creates the **unpublished** Loxo job
   and prints a **Sourcing Brief** (also posted as a job note when
   `LOXO_NOTE_ACTIVITY_TYPE_ID` is set).
2. Open the job → run the channels (**Loxo Source**, **LinkedIn OW**, **LinkedIn
   Non-OW**, **Indeed Database**) → paste the matching Boolean from the brief.
3. Select the best **75–150** → bulk-move to **Long List**.
4. Move the **top 15–20** to **Short List**, then bulk-select them and:
   **Fetch Contacts** (enrich) → **Add to Campaign** (Confidential Outreach) →
   generate **AI highlights**. (These are manual clicks, not an automation — see C.)
5. Review enriched contacts, then publish the JD / let the campaign send.

Manual steps are the search (2) and the Short-List enrich/enroll clicks (4);
everything else (JD, brief, Booleans, criteria) is produced by Emerald.

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
