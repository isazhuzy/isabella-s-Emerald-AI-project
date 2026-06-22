# Memo — Call/Meeting Transcription Tools for the Automated Sourcing Workflow

**Date:** June 2026
**Re:** Choosing the transcription layer that feeds the Emerald → Claude → Loxo pipeline
**Scope:** Tools usable for **both cell-phone calls and Zoom calls**, evaluated for
**automation fit** (i.e., can deliver a transcript to our pipeline via API/webhook).


---

## Bottom line

**Cell and Zoom are two different capture problems.** Zoom is captured by a
meeting bot that joins the call; a cell call has no bot to invite — it must be
captured by a mobile app, a dialer/telephony integration, or a recording forwarded
to a speech-to-text API. **No single one of the three requested tools does both
*and* is fully automation-ready** — but they rank clearly:

1. **Primary recommendation: Fireflies.ai** — the only one of the three that covers
   **Zoom (bot) + cell/business calls (dialer integrations) + a real API
   (GraphQL + webhooks)** to hand transcripts to Emerald. Best single-vendor "both."
2. **For cell calls that should land in Loxo automatically: add a Loxo-integrated
   dialer (Ringover).** Loxo natively ingests Ringover call summaries, so cell calls
   flow into the candidate record with zero glue code.
3. **Fathom** — excellent for Zoom, free, now has a clean public API/webhooks — but
   **no phone/cell capture**. Use only if cell is handled separately.
4. **Otter.ai** — solid Zoom + mobile/in-person capture, but its **API & webhooks
   are Enterprise-tier only**, which raises the cost/complexity of automating it.

---

## The two capture problems (read this first)

| | **Zoom / video call** | **Cell-phone call** |
|---|---|---|
| How it's captured | A bot joins the meeting and records | Mobile app, **dialer/VoIP integration**, or forward audio to an STT API |
| "Just works" tools | Otter, Fireflies, Fathom, Recall.ai | Fireflies (via dialer), Otter (mobile/Zoom Phone), Ringover/Aircall, Twilio+AssemblyAI |
| Gotcha | — | A bot **cannot** dial into an arbitrary personal cell call; you need the call to run through a recordable channel (business dialer, conference line, or recorded mobile app) |

> Practical implication: if recruiters take intake calls on **personal cell phones**,
> route them through a **business dialer** (Ringover/Aircall/OpenPhone) or a
> recording mobile app — otherwise there's nothing to automate.

---

## Side-by-side comparison

| Dimension | **Fireflies.ai** | **Otter.ai** | **Fathom** | **Recall.ai** *(infra)* |
|---|---|---|---|---|
| Zoom / Meet / Teams | ✅ bot auto-joins | ✅ bot auto-joins | ✅ bot auto-joins | ✅ widest platform coverage |
| **Cell / phone calls** | ✅ via dialer (ZoomPhone, RingCentral, OpenPhone, Aircall) + mobile app | ⚠️ mobile app (in-person) + Zoom Phone; not arbitrary cellular | ❌ none (no mobile app) | ⚠️ meeting-centric; pair w/ telephony |
| **API for automation** | ✅ GraphQL **+ webhooks** (paid tiers) | ⚠️ API + webhooks **Enterprise only** | ✅ REST **+ webhooks**, SDKs, MCP (all users) | ✅ built to be an API (its whole product) |
| Speaker diarization | ✅ | ✅ | ✅ | ✅ best (separate audio per speaker) |
| Feeds Emerald webhook | ✅ easy | ⚠️ Enterprise / S3-poll | ✅ easy | ✅ easy |
| Pricing (per user/mo, ann., **verify**) | Free / $10 / $19 / $39 | Free / paid; **API = Enterprise** | Free + paid; public API included | Usage-based (developer infra) |
| Best for | **Both cell + Zoom, automatable** | Teams already on Otter | Zoom-only, low cost, clean API | Building our own notetaker at scale |

---

## Per-tool analysis

### Fireflies.ai — *recommended primary*
- **Coverage:** Joins Zoom/Meet/Teams **and** captures phone calls through dialer
  integrations (ZoomPhone, RingCentral, OpenPhone, Aircall). Closest to a true
  "cell + Zoom" single vendor.
- **Automation:** Mature **GraphQL API + webhooks** — on "transcription complete,"
  fire a webhook → our `server.py /webhook/transcript` → `run_pipeline()`. This is
  the cleanest drop-in for Emerald.
- **Watch-outs:** Lower tiers meter "AI credits"; we only need the **raw transcript**
  (we do JD/booleans/outreach in Claude), so a mid tier likely suffices — **verify
  that transcript + webhook are available on the tier we buy.**

### Otter.ai
- **Coverage:** OtterPilot 3.0 auto-joins Zoom/Meet/Teams; mobile app records
  **in-person**; **Zoom Phone** calls auto-sync. Real cellular calls only if they run
  through Zoom Phone or are recorded in the mobile app.
- **Automation:** **API & webhooks are Enterprise-only.** Without Enterprise, you're
  limited to S3/Drive export + polling — more brittle and slower for our pipeline.
- **Verdict:** Fine if the team already standardizes on Otter; otherwise the
  Enterprise gate makes it a heavier lift than Fireflies for the same outcome.

### Fathom
- **Coverage:** Zoom/Meet/Teams only. **No mobile app, no in-person/phone capture** —
  it **does not solve cell calls.**
- **Automation:** Now ships a proper **public REST API + webhooks + TS/Python SDKs +
  MCP server**, free to all users — genuinely nice to integrate.
- **Verdict:** Best-in-class for the **Zoom half** at the lowest cost and cleanest
  API. Pair it with a separate cell solution if we go this route.

### Recall.ai — *infrastructure option, not an app*
- A **universal meeting-bot API** (Zoom/Meet/Teams/Webex/GoTo/Slack huddles) with
  **separate per-speaker audio** (best diarization). It's how you'd build our *own*
  notetaker rather than buy one. Best if we outgrow off-the-shelf tools or want one
  uniform transcript format across every platform. Still meeting-centric — phone
  calls need a telephony pairing.

### Cell-call specifics (to actually close the "both" gap)
- **Ringover** *(recommended for cell)* — a dialer Loxo integrates natively; call
  recordings/summaries post straight onto the Loxo candidate/contact record. Lowest
  glue for *our* stack.
- **Aircall / RingCentral / OpenPhone** — business dialers Fireflies can transcribe.
- **Twilio + AssemblyAI/Deepgram** — fully programmatic: record the call leg, send
  audio to the STT API, get a transcript + diarization back. Most control, most build.

---

## How each plugs into Emerald (the integration seam)

Emerald already exposes `POST /webhook/transcript` (`server.py`). The job is simply
to get each vendor to call it with the transcript text:

| Source | Mechanism into Emerald |
|---|---|
| **Fireflies** | Webhook on "transcription complete" → our endpoint; or pull transcript via GraphQL on the event. |
| **Fathom** | REST webhook → our endpoint (subscribe to meeting-completed). |
| **Otter** | Enterprise webhook → endpoint, **or** S3/Drive export + a small poller. |
| **Recall.ai** | Webhook delivers transcript payload → endpoint. |
| **Ringover (cell)** | Native Loxo integration logs the call; optional webhook/Zapier → endpoint to also run the JD/sourcing pipeline. |
| **Twilio + AssemblyAI** | Our function receives the STT callback → calls `run_pipeline()`. |

In all cases we only need the **transcript text + speaker labels** — Claude does the
JD, ad copy, outreach, and Boolean generation downstream. Adapt
`extract_transcript()` in `server.py` to each vendor's payload shape.

---

## Recommendation

1. **Buy Fireflies.ai** as the primary capture tool (covers Zoom **and** phone via
   dialer, with a webhook that feeds Emerald directly). **Confirm transcript + webhook
   access on the chosen tier before purchase.**
2. **Standardize cell intake on a recordable channel** — recommend **Ringover** (native
   Loxo integration) so cell calls land in Loxo automatically and can also trigger the
   pipeline.
3. **Consider Fathom** as a low-cost/free Zoom-only fallback or for individual users —
   but do **not** rely on it for cell calls.
4. **Hold Recall.ai / Twilio+AssemblyAI in reserve** for when we want a single uniform
   transcript format across every platform or fully headless telephony (the B2-style,
   build-our-own path).

---

> **Assumptions / to verify before circulating:**
> - Pricing figures are vendor-reported (mid-2026) and **not yet confirmed** — verify
>   the *specific tier* that includes transcript export + webhooks for each tool.
> - Confirm Fireflies webhook fires the **full transcript** (not just a summary) on the
>   plan we buy.
> - Confirm our recruiters' cell intake calls can be routed through a recordable
>   channel (dialer/mobile app) — this is the make-or-break for cell coverage.
> - Verify call-recording **consent/2-party-consent** requirements for the states we
>   operate in before enabling automatic recording.

**Sources (vendor-reported; verify):**
[Otter API/webhooks (Enterprise) & Zoom Phone](https://help.otter.ai/hc/en-us/articles/24271600654871-Zoom-Phone-Integration) ·
[Fireflies API (GraphQL + webhooks)](https://fireflies.ai/api) ·
[Fireflies dialer integrations](https://fireflies.ai/integrations/dialer) ·
[Fathom Public API](https://developers.fathom.ai/) ·
[Recall.ai Meeting Bot API](https://www.recall.ai/product/meeting-bot-api) ·
[Deepgram phone-call transcription](https://developers.deepgram.com/docs/automatically-transcribing-and-summarizing-phone-calls)
