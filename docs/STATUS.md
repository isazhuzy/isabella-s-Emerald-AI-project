# Emerald — Project Status Overview

*Last updated: June 23, 2026*

A running summary of what's been built, what's verified, and what's left. For the
boss-facing writeup with vendor research, see
[Emerald-Progress-and-Vendor-Research.md](./Emerald-Progress-and-Vendor-Research.md).

---

## What Emerald is
An intake-call → recruiting-deliverables pipeline. A recruiter/hiring-manager intake-call
transcript goes in; out comes a **confidential** sourcing package, and (optionally) an
unpublished job created directly in **Loxo**.

Each run produces: an anonymized **JD** (house style, with a "Why Join" section),
**ad copy** (LinkedIn/Indeed/DocCafe), a multi-step **outreach** sequence,
**4 Boolean** variants, and a recruiter **Sourcing Brief**.

---

## Done & verified ✅

| Area | Status |
|---|---|
| Anthropic + Loxo configured (`.env`: keys, agency, required IDs) | ✅ |
| Model set to `claude-opus-4-8` | ✅ |
| Generation: JD / ad copy / outreach / Boolean / criteria (one cached Claude call) | ✅ |
| Confidential anonymization (model + deterministic safety-net) | ✅ 0 leaks in tests |
| JD writer upgraded to Emerald house style + 3 real exemplars + "Why Join" | ✅ |
| Stage mapping to real Loxo workflow: **Long List → Short List** | ✅ |
| Sourcing brief is **multi-channel** (Loxo Source / LinkedIn OW+Non-OW / Indeed) | ✅ |
| `emerald.sh` wrapper + `--publish` flag (push live to careers page) | ✅ |
| **Real `--push` test:** unpublished Loxo job **#3621461** + brief posted as a note | ✅ verified live |
| Tested prompt sequence on a **real order** (Merrymeeting Senior Accountant) | ✅ |
| Two generation bugs fixed (JSON retry; Loxo job-id unwrap so notes post) | ✅ |

### Key Loxo reality (verified in-app)
Loxo (this plan) has **no single "on stage entry → enrich + enroll + AI highlights"
automation**. Enrichment = manual **Fetch Contacts**; campaign enrollment = manual
**Add to Campaign**. The cost gate holds by *only enriching the Short List*. Docs were
corrected to this reality. The **Confidential Outreach** campaign already exists (empty).

---

## Deliverables written (in `docs/`)
- **[prompt-sequence.md](./prompt-sequence.md)** — the AI prompt sequence (Intake → JD →
  Boolean → Loxo), with test results (what worked / what didn't).
- **[contact-prefetch-design.md](./contact-prefetch-design.md)** — auto-enrich-on-stage
  design (Loxo webhook → middleware → Seamless/Loxo enrichment → write-back).
- **[Emerald-Progress-and-Vendor-Research.md](./Emerald-Progress-and-Vendor-Research.md)**
  — Google-Doc-ready: progress + transcription bots + voicemail drop research.
- **[DEMO.md](./DEMO.md)** — live demo script for the presentation.

### Research highlights
- **Transcription:** Fireflies (Zoom + cell + webhook) + Ringover (cell, native Loxo).
- **Voicemail drop:** Loxo has it **natively** (use first). API options: Drop Cowboy
  (~$0.007/drop, Zapier-friendly) and Slybroadcast (~$0.10/drop, free API); bridge to
  Loxo via webhook→Zapier. **TCPA consent** required.
- **Contact enrichment:** Seamless.AI API is **Enterprise-only ($20k–$100k+/yr)**;
  TruePeopleSearch is out (no API + FCRA). Loxo's Contact Finding Agent is the fallback.

---

## Outstanding / next steps
1. **Convert docs to `.docx`** (real Word tables) — *in progress; pandoc install was
   stopped, needs to be finished or done via docx-js.*
2. **Commit + push** `docs/` + `transcripts/` + the `.docx` files to `origin/main`.
   *(Earlier code edits are already committed.)*
3. **Sync a sending email** in Loxo — required before any outreach actually sends.
4. *(Optional)* Populate the Confidential Outreach campaign steps.
5. **Wire live transcription** ([server.py](../server.py) webhook) once a vendor is picked.
6. **Delete test job #3621461** when no longer needed.
7. Decide voicemail approach (Loxo native vs Drop Cowboy) and the contact-prefetch trigger.

---

## Handy commands
```bash
# Preview only (no Loxo):
./emerald.sh transcripts/merrymeeting-senior-accountant.txt "Merrymeeting Group"
# Create unpublished Loxo job + post brief as a note:
./emerald.sh transcripts/merrymeeting-senior-accountant.txt "Merrymeeting Group" --push
# Publish live on the careers page (already anonymized — use intentionally):
./emerald.sh transcripts/merrymeeting-senior-accountant.txt "Merrymeeting Group" --publish
```
