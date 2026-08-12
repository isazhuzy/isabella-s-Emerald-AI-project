# Make.com → Loxo — Push a Job + its Candidates

*How to take the candidate JSON your Make.com scenario builds and push both the **job**
and the **candidates** into Loxo, using Make's HTTP module against the Loxo Open API.*

## TL;DR

You have two routes. Pick one:

- **A) Let Emerald do it (recommended, least to maintain).** Make just POSTs the intake
  transcript to Emerald's `/webhook/transcript`, and the Python pipeline creates the job
  (JD in the Description tab), sources candidates, gathers contacts, and pushes people +
  contacts to Loxo. One HTTP module in Make, everything else is already built.
- **B) Make calls Loxo directly.** Three HTTP modules — create the job, create each
  person, attach each person to the job. Use this if the candidate JSON originates in
  Make and never touches Emerald.

Both hit the same Loxo Open API. Fill these in from your `.env`:

| Placeholder | Value (Emerald Resource Group) |
|---|---|
| `{BASE}` | `https://app.loxo.co/api/emerald-resource-group` |
| `{LOXO_API_KEY}` | your Loxo bearer token (Settings → API Keys) |
| `job_type_id` | `9774` (Full Time) |
| `company_id` | `8431133` (Emerald Resource Group) |
| pipeline `activity_type_id` | `87305` (Sourced stage) |

**Auth on every call:** header `Authorization: Bearer {LOXO_API_KEY}`.
**Body encoding:** Loxo expects bracketed form fields (`job[title]`, `person[name]`, …).
In Make's HTTP module set **Body type = application/x-www-form-urlencoded** and add the
fields below. (Do **not** send JSON — the Open API reads form params.)

---

## Route A — Make → Emerald webhook (recommended)

One module. Everything downstream (job, JD, sourcing, contacts, Loxo push) is already
wired in the pipeline and gated by the `EMERALD_WEBHOOK_*` flags.

**HTTP → Make a request**
- **URL:** `https://isabella-s-emerald-ai-project-1.onrender.com/webhook/transcript`
- **Method:** `POST`
- **Body type:** `application/json`
- **Body:**
  ```json
  { "transcript": "{{the full intake transcript}}", "client_name": "{{client}}" }
  ```
  (Or send `{ "meetingId": "{{fireflies id}}" }` and Emerald fetches the transcript.)

Then, in the Render dashboard, turn on the stages you want:
`EMERALD_WEBHOOK_PUSH=true`, `EMERALD_WEBHOOK_SOURCE=true`, `EMERALD_WEBHOOK_ENRICH=true`
(leave `EMERALD_WEBHOOK_PUBLISH=false` unless you want jobs to go live automatically).

That's it — no per-record Make modules.

---

## Route B — Make → Loxo directly

### Module 1 — Create the job

**HTTP → Make a request**
- **URL:** `{BASE}/jobs`
- **Method:** `POST`
- **Headers:** `Authorization: Bearer {LOXO_API_KEY}`
- **Body type:** `application/x-www-form-urlencoded`
- **Fields:**

| Field | Value |
|---|---|
| `job[title]` | `{{title}}` |
| `job[description]` | `{{jd_html}}` — send HTML so it renders in the Description tab |
| `job[job_type_id]` | `9774` |
| `job[company_id]` | `8431133` |
| `job[published]` | `false` (or `true` to publish to the careers page) |
| `job[owner_emails][]` | `mark@emeraldresourcegroup.com` (repeat the field for co-owners) |

**Capture** `{{1.body.job.id}}` — Loxo returns the job nested as `{"job":{"id":…}}`. You
need this id for Module 3.

### Module 2 — Create each person (candidate)

Put this inside a Make **Iterator** over your candidate array, so it runs once per
candidate.

- **URL:** `{BASE}/people`
- **Method:** `POST` · **Auth:** same bearer header · **Body:** `x-www-form-urlencoded`
- **Fields:**

| Field | Value | Notes |
|---|---|---|
| `person[name]` | `{{name}}` | required |
| `person[emails][][value]` | `{{email}}` | the contact — carries into Loxo |
| `person[phones][][value]` | `{{phone}}` | the contact — carries into Loxo |
| `person[linkedin_url]` | `{{linkedin}}` | helps Loxo auto-merge duplicates |
| `person[location]` | `{{location}}` | optional |

**Capture** `{{2.body.person.id}}` for Module 3. Loxo auto-merges duplicates by
email/LinkedIn, so re-running folds into the existing record instead of duplicating.
(Title/company aren't settable on the person — Loxo derives them from work history; keep
them in the pipeline note instead.)

### Module 3 — Attach the person to the job pipeline

- **URL:** `{BASE}/person_events`
- **Method:** `POST` · **Auth:** same bearer header · **Body:** `x-www-form-urlencoded`
- **Fields:**

| Field | Value |
|---|---|
| `person_event[person_id]` | `{{2.body.person.id}}` |
| `person_event[job_id]` | `{{1.body.job.id}}` |
| `person_event[activity_type_id]` | `87305` (Sourced stage) |
| `person_event[notes]` | `Sourced via Make — {{title}} @ {{company}}` (optional) |

### Scenario shape

```
[Trigger / your candidate JSON]
      │
   Module 1  Create job ─────────────► capture job.id
      │
   Iterator over candidates
      │
   Module 2  Create person ─────────► capture person.id
      │
   Module 3  Attach person → job (person_events)
```

**Pacing:** Loxo rate-limits bursts. For a long list, add a short delay (e.g. Make's
Sleep, ~0.5s) between iterations, or cap batch size — the same reason the Python pusher
paces ~0.6s/person.

---

## Which route?

- Candidate JSON comes from Emerald's own sourcing → **Route A** (already built; contacts,
  dedupe, JD-in-Description all handled).
- Candidate JSON is assembled entirely in Make from another source → **Route B**.
- You can also mix: Route A to create the job + JD, then Route B Modules 2–3 to push a
  candidate list Make built separately (reuse the `job.id` from Emerald's webhook
  response, which returns `job_url`).
