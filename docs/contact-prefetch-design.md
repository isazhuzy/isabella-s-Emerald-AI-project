# Design Sketch — Pre-fetch Contact Info Before the Call Block

**Goal:** when a profile lands in a Loxo column (stage), automatically fetch the
candidate's phone + email **before** the recruiter's call block, so the recruiter
opens a fully-enriched shortlist. Prefer **Seamless.AI** as the data source.

---

## The trigger: "a profile lands in a column"

In Loxo, moving a candidate to a stage modifies a field on the record, and **Loxo
emits a webhook when fields are modified** (Open API feature — paid). That webhook is
our automation trigger. We gate it to a single column — the **pre-call / "Short List"**
stage — so only the shortlist is enriched (cost control).

## Flow

```
Recruiter moves candidate → "Short List" (pre-call column)
        │
        ▼
Loxo webhook  ──(person_id, job_id, new stage)──►  Middleware
        │                                          (Zapier "Webhooks", or a small
        │                                           Flask service — Emerald's
        │                                           server.py already does webhooks)
        ▼
Middleware calls  Seamless.AI Enrichment API
        │   input:  name + company + LinkedIn (from the Loxo person)
        │   output: mobile phone, work email, personal email, title
        ▼
Middleware writes back via Loxo Open API
        │   PATCH person → phone/email fields
        │   POST person_event → log "Enriched via Seamless" note
        ▼
Recruiter opens the column — contacts already populated, ready to dial
```

## Seamless.AI specifics (researched June 2026)

- **API capabilities:** contact search, company search, **enrichment** (phone, email,
  title, job-change), via REST. Auth: Persistent Key, OAuth, or Webhooks.
- **⚠️ Cost gate:** the Seamless **API is Enterprise-only** — roughly **$20k–$100k+/yr**.
  The per-user Pro plan (~$147–$299/user/mo) does **not** include API access.
  → *Recommendation:* only pursue the Seamless API path if we land an Enterprise
  contract; otherwise use the fallback below.

## Fallback if we're not on Seamless Enterprise

**Loxo's own "Contact Finding Agent" (Fetch Contacts)** already does enrichment on the
1.2B-profile graph and is callable in-app on a shortlist. Two ways to automate-ish it:
1. **Manual bulk** — recruiter bulk-selects the column and clicks **Fetch Contacts**
   (today's reality; cheapest; the cost gate is "only on the shortlist").
2. **Loxo continual enrichment** (Settings → Data enrichment) for always-on cleanup.

So the architecture is **source-agnostic**: same webhook → middleware → write-back
shape, swapping Seamless for Loxo's Contact Finding Agent as the enrichment call.

## Rejected source: TruePeopleSearch

Not viable for recruiting: it's a **consumer public-records** tool with **no real API**,
and its terms **prohibit use for employment decisions (FCRA)**. Keep out of the pipeline.

## What to build (incremental)

1. Add `LoxoClient.update_person(person_id, phone=…, email=…)` (a `PATCH /people/{id}`)
   — the only missing piece; `add_note`/pipeline reads already exist in [loxo.py](../emerald/loxo.py).
2. Add a webhook handler in [server.py](../emerald/server.py): `POST /webhook/stage-change`
   → enrich → write back.
3. Config: `ENRICH_PROVIDER = seamless | loxo`, `ENRICH_TRIGGER_STAGE = Short List`.
4. Compliance check: confirm Seamless B2B data use is fine for sourcing (it is); honor
   opt-outs; never use consumer/FCRA-restricted sources.
