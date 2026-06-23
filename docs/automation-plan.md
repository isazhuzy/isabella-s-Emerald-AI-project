# Emerald — Full Automation Plan (Call → Transcript → JD → Candidates Sourced)

*How to take Emerald from "a tool you run" to a hands-off pipeline. Scope here is up to
**candidates sourced** — it deliberately does NOT auto-send outreach (that stays
human-approved).*

---

## The target pipeline

```
Intake call (Zoom or cell)
   └─ Transcription bot produces a transcript
        └─ Webhook → Emerald: anonymized JD + ad copy + Boolean + criteria
             └─ Unpublished job + Sourcing Brief created in Loxo (automatic)
                  └─ Candidates sourced into the Long List
                       └─ Shortlist enriched (Fetch Contacts) on Short List
                            └─ [HUMAN GATE] review → publish / start outreach
```

## Automation status, stage by stage

| Stage | Can it be automatic? | How |
|---|---|---|
| Call → transcript | ✅ Yes | Transcription vendor (Fireflies for Zoom+cell; Ringover for cell) |
| Transcript → JD/ad/Boolean/criteria | ✅ Yes (built) | `run_pipeline()` |
| → Create unpublished Loxo job + brief note | ✅ Yes (built, tested) | `push_to_loxo=True` |
| **Candidates sourced into Long List** | ⚠️ **Partial — the one real gate** | See below |
| Shortlist contact enrichment | ✅ Yes (buildable) | Webhook on stage move → enrich (see contact-prefetch-design.md) |
| Review / publish / send outreach | 🚫 Human (by design) | Unpublished gate; recruiter approves |

## The one real gate: sourcing candidates

**Loxo's AI candidate search (Loxo Source) cannot be triggered through the API** — we
verified this. So "candidates sourced, fully automatically" has two possible paths:

- **Path A — semi-auto (recommended, available today).** Emerald auto-creates the job +
  posts the Boolean in the Sourcing Brief. The recruiter opens the job, pastes the
  Boolean into Loxo Source (**one click**), selects the 75–150, and bulk-moves them to
  **Long List**. Everything before and after this click is automated. This is the
  realistic "near-hands-off" pipeline.
- **Path B — fully headless (bigger build, paid data).** Skip Loxo Source; pull
  candidates from an **external candidate-data API** (Apollo, PeopleDataLabs, or Seamless
  **Enterprise**) using the `search_criteria` Emerald already emits, then auto-push ranked
  candidates into the Loxo pipeline via `LoxoClient.add_to_pipeline()` (already stubbed in
  [loxo.py](../emerald/loxo.py)). Requires a paid data API, query-translation code, and
  compliance review. Only worth it if the one-click search becomes a bottleneck.

---

## What YOU need to do to turn it on

### Phase 1 — Auto: call → JD + job + brief in Loxo (no manual command)
1. **Pick + configure the transcription vendor** — Fireflies (Zoom + cell) and/or
   Ringover (cell, native Loxo). Confirm the plan returns the **full transcript via
   webhook**.
2. **Deploy `server.py`** to an always-on host (Render etc.) with the `.env` keys set as
   environment variables. *(See deploy steps in chat / can be added to docs.)*
3. **Map the vendor payload** in `server.py`: finish `extract_transcript()` and
   `extract_client_name()` for the vendor's JSON, and derive the **client name** (recommended:
   a meeting-title convention like `"Intake — <Client>"`) so anonymization knows what to remove.
4. **Add a webhook secret** so only the vendor can trigger the endpoint.
5. **Flip `push_to_loxo=True`** in the webhook handler (keep jobs **unpublished**).
6. **Point the vendor's webhook** at `https://<host>/webhook/transcript`.
→ Result: a call ends → seconds later an unpublished job + brief are in Loxo. Zero typing.

### Phase 2 — Near-hands-off through sourcing
7. Recruiter runs the **one-click Loxo Source search** from the brief → Long List (Path A).
8. **Automate shortlist enrichment**: build the stage-move webhook → enrich → write-back
   (see [contact-prefetch-design.md](./contact-prefetch-design.md)). Gate it to **Short List**
   so only the shortlist spends credits.

### Phase 3 — Optional fully headless sourcing (Path B)
9. Add an external candidate-data provider API; translate `search_criteria` → their query;
   auto-push ranked candidates via `add_to_pipeline()`. Compliance review first.

---

## Build checklist (engineering, small)
- [ ] `server.py`: vendor payload mapping + client-name parser + webhook-secret check
- [ ] `server.py`: set `push_to_loxo=True`; run generation async (queue) for reliability
- [ ] Deploy config (e.g. `render.yaml`) + env vars on host
- [ ] (Phase 2) `LoxoClient.update_person()` + `/webhook/stage-change` enrichment handler
- [ ] (Phase 3) external sourcing adapter → `add_to_pipeline()`

## Guardrails to keep
- Jobs land **unpublished**; nothing goes public or sends without a human.
- Enrichment is gated to the **Short List** (cost control).
- Webhook is secret-protected; `.env` lives on the host, never in git.
