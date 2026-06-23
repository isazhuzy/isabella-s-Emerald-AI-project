# Emerald — AI Prompt Sequence (Intake → JD → Boolean → Loxo Job)

**Task:** turn the step-by-step process into a working AI prompt sequence, write out
each prompt, test on a real job order, document what worked / what didn't.

This is the **logical prompt sequence**. Emerald runs it in Claude (model
`claude-opus-4-8`). For speed, cost, and consistency the production code compresses
Steps 1–5 into **one cached Claude call** that returns a single JSON object
([emerald/generate.py](../emerald/generate.py)); the prompts below are the discrete
"thinking steps" that one call performs. The final Loxo write (Step 6) is a
**deterministic API call**, not an AI step.

---

## Step 0 — System role + hard rules (always in context)

> You are a senior recruiting operations assistant at Emerald Resource Group. From a
> recruiter/hiring-manager intake-call transcript you produce a complete, ready-to-use
> sourcing package.
>
> HARD RULES:
> - CONFIDENTIAL / ANONYMOUS output. Never name the employer, its products, named
>   people, or an exact street address. Generalize identifying details
>   (e.g. "a Series B fintech", "a regional health system"). Keep the role vivid.
> - Output MUST be a single JSON object. No prose, no markdown fences.

*Why:* the anonymization rule is the compliance backbone (confidential searches); the
JSON rule makes the output machine-parseable for the Loxo step.

## Step 1 — Extract structured intake

> From the transcript, extract: role title (generic), location + radius, seniority,
> required skills/credentials (must-have), nice-to-haves, and comp range. Return as
> `search_criteria` + `comp`.

## Step 2 — Write the anonymized JD (Emerald house style)

> Write a JD with: an energizing **summary** that frames the employer generically and
> sells the opportunity; **responsibilities** as punchy action bullets ("What You'll Be
> Doing"); **requirements** as concrete must-haves ("What We're Looking For"); and
> **why_join** — 4–7 candidate-facing selling points ("Why Consider This Opportunity").
> For clinicians, lead comp with earning potential and include CME/malpractice/schedule.

*(Few-shot anchored on three real Emerald JDs: Senior Accountant, Pulmonologist, OB/GYN.)*

## Step 3 — Platform ad copy + outreach sequence

> Produce `ad_copy` tailored to LinkedIn (concise, first-person), Indeed (structured,
> keyword-rich), and DocCafe (clinician audience only). Produce a 3–4 step `outreach`
> sequence (email → InMail → SMS) with merge-friendly bodies.

## Step 4 — Boolean strings

> Produce Boolean variants (`generic`, `linkedin`, `google_xray`, `loxo_source`).
> Expand credentials (`"Board Certified" OR "Board Eligible" OR BC OR BE`), enumerate
> the geography as an OR-list, group titles/skills in AND-clauses, and use `NOT` to
> exclude obvious mismatches (interns/residents/locums; auditors for accounting).

## Step 5 — Emit one JSON object

The single object: `title, jd{summary,responsibilities,requirements,why_join}, comp,
ad_copy, outreach, boolean_strings, search_criteria`.

## Step 6 — Loxo job creation (deterministic, not AI)

1. **Redaction safety-net** ([redact.py](../emerald/redact.py)) scrubs any leaked client
   name/emails — belt-and-suspenders behind the model's anonymization.
2. `render_description()` builds the JD markdown.
3. `LoxoClient.create_job(..., published=False)` → **unpublished** job.
4. The Sourcing Brief is posted as a **note** on the job.

---

## Test results — real job orders

### Test A — Pulmonary/Family Medicine Physician (pushed to Loxo)
- **Result:** ✅ created **unpublished Loxo job #3621461**, brief posted as a note
  (person_event #1266320452), confirmed live in the Loxo UI. Redaction clean (0 hits).
- Booleans came out with full BC/BE expansion, DFW geo OR-list, and `NOT (resident OR
  intern OR locum…)` — matching the house exemplars.

### Test B — Senior Accountant / "Merrymeeting Group" (real order, preview)
Transcript: [transcripts/merrymeeting-senior-accountant.txt](../transcripts/merrymeeting-senior-accountant.txt)
- **Result:** ✅ JD, Why-Join, and 4 Boolean variants generated. `"Merrymeeting Group"`
  fully anonymized to *"an entrepreneurial, multi-industry holding company."* (0 hits).
- The generic Boolean closely matched the human-written exemplar, incl.
  `NOT (audit OR auditor OR assurance OR internship OR "Big Four")` and a Cleveland-metro
  geo expansion for the "within 30 miles" radius.

### What worked
- **One call, full package** — JD + ad copy + outreach + 4 Booleans + criteria, every time.
- **Anonymization held** in both tests (0 redaction hits; the safety-net never had to fire).
- **House style transferred** — the Why-Join section and Boolean shape match the exemplars.
- **Loxo creation is reliable** once the response-unwrap bug was fixed.

### What didn't / caveats
- **Occasional invalid JSON** from the model (an unescaped quote in a long field). Fixed
  with a **3× auto-retry** in `generate.py`; if it ever exhausts retries it errors clearly.
- **DocCafe ad copy is empty for non-clinical roles** (correct — DocCafe is a physician
  board) but worth knowing: for the Accountant, only LinkedIn + Indeed copy is useful.
- **Comp is only as good as the transcript** — if the HM doesn't state numbers, comp is null.
- Opus 4.8 **rejects `temperature` and assistant-prefill** — both removed; don't re-add.
