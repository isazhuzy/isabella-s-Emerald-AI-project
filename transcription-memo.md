# Memo — Call/Meeting Transcription Tools for the Automated Sourcing Workflow

**Date:** June 2026
**Re:** Choosing the transcription layer that feeds the Emerald → Claude → Loxo pipeline
**Scope:** Tools usable for **both cell-phone calls and Zoom calls**, evaluated for
**automation fit** (i.e., can deliver a transcript to our pipeline via API/webhook).
**Tools required in scope:** Otter.ai, Fireflies.ai, Fathom (+ automation-grade
alternatives needed to truly cover cell calls headlessly).

---

## Decision at a glance

| | |
|---|---|
| **Recommended capture tool** | **Fireflies.ai — Business (~$19/user/mo)** |
| **Recommended cell channel** | **Ringover** (native Loxo integration) |
| **All-in cost, 5 recruiters** | **~$200/mo**, no custom engineering |
| **Why** | Only requested tool that does Zoom **+** cell **+** a webhook to feed Emerald |
| **Don't rely on** | Fathom for cell (it has none); Otter unless on Enterprise (API-gated) |
| **Decide before buying** | tier includes a **full-transcript webhook**; call-recording consent laws |

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
| Pricing (per user/mo, ann., **verify**) | Free / $10 / $19 / $39 | Free / $8.33 / $19.99 / **Enterprise (custom) for API** | Free / $15 / ~$19 / ~$29 | $0.50/recording-hr + $0.15/hr transcription |
| Best for | **Both cell + Zoom, automatable** | Teams already on Otter | Zoom-only, low cost, clean API | Building our own notetaker at scale |

---

## Decision matrix (weighted)

Scored 1–5 per criterion; weights reflect what matters for *our* pipeline (cell
coverage and automation weigh most, since Zoom is solved by everyone).

| Criterion (weight) | Fireflies | Otter | Fathom | Recall.ai |
|---|:--:|:--:|:--:|:--:|
| Cell / phone coverage (30%) | 4 | 2 | 1 | 2 |
| Zoom coverage (20%) | 5 | 5 | 5 | 5 |
| Automation / API fit (25%) | 5 | 2 | 5 | 5 |
| Cost (15%) | 4 | 3 | 5 | 4 |
| Diarization / quality (10%) | 4 | 4 | 4 | 5 |
| **Weighted total** | **4.45** | **2.95** | **3.70** | **3.95** |

**Read:** Fireflies wins on the combination that matters (cell + automation). Recall.ai
scores well but is build-your-own infrastructure, not an off-the-shelf tool. Fathom is
strong but its cell score (1) caps it. Otter trails mainly on the Enterprise API gate.

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

## Pricing (mid-2026 — vendor-reported, **verify before purchase**)

### Per-seat tools (priced per user / month)

| Tool | Free | Entry paid | Mid / "Business" | Top tier | API/webhook on… |
|---|---|---|---|---|---|
| **Fireflies.ai** | $0 | **Pro $10** | **Business $19** | Enterprise $39 | **paid tiers** ✅ |
| **Otter.ai** | $0 (300 min/mo) | Pro $8.33 ($16.99 mo) | Business $19.99 ($30 mo) | Enterprise (custom, ~mid-4-figures/yr) | **Enterprise only** ⚠️ |
| **Fathom** | $0 (unltd recordings, 5 summaries/mo) | Premium $15 ($19 mo) | Team $19 ($29 mo) | Team Pro $29 ($39 mo) | **all tiers, incl. free** ✅ |
| **Ringover** *(cell dialer)* | — | Smart ~$21 ($29 mo) | Power ~$44 ($54 mo) | Advanced $64 / custom | native Loxo integration; AI may be add-on |

*Annual-billing rate shown first; monthly in parentheses. Lower Fireflies/Otter tiers
meter "AI credits" — we only need the raw transcript, so confirm transcript + webhook
are included on the tier bought.*

### Usage-based (pay per minute/hour — for the build-your-own / telephony path)

| Service | Rate | Notes |
|---|---|---|
| **Recall.ai** (meeting bot) | **$0.50 / recording-hr** + $0.15/hr transcription | No platform fee; prorated to the second; Calendar API free |
| **Deepgram** (STT) | **~$0.26 / hr** ($0.0043/min) pre-recorded | Cheapest for pure transcription |
| **AssemblyAI** (STT) | **~$0.37 / hr** ($0.0061/min); batch as low as $0.15/hr | Cheaper speaker-ID + PII redaction features |
| **Twilio** (telephony) | Voice ~$0.013–0.014/min; recording $0.0025/min + storage $0.0025/min; **its own** transcription $0.05/min | Use Deepgram/AssemblyAI for STT, not Twilio's, to save ~7–10× |

### Illustrative monthly cost — team of 5 recruiters, ~40 calls each (~30 min)

| Stack | Rough monthly | What it covers |
|---|---|---|
| **Fireflies Business × 5** | **~$95** | Zoom **+** phone (via dialer) + webhooks → Emerald |
| **+ Ringover Smart × 5** (cell line) | **+~$105** | recordable cell intake that also lands in Loxo |
| Fathom Premium × 5 (Zoom-only fallback) | ~$75 | Zoom only — no cell |
| Otter Business × 5 | ~$100 | but **API needs Enterprise** (custom quote) |
| Recall.ai (build-your-own, ~100 hrs) | **~$65 usage** | Zoom capture; you build the integration |
| Twilio + AssemblyAI (DIY cell, ~100 hrs) | **~$135 usage** | fully programmatic cell; you build it |

> **Cheapest path that actually covers cell + Zoom + automation:** **Fireflies
> Business (~$95/mo)** as the capture tool, **+ Ringover (~$105/mo)** for recordable
> cell intake → **~$200/mo all-in for a 5-person team**, no custom engineering.

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

## Recommended stack & 30-day rollout

**Buy:** Fireflies.ai (Business) + Ringover for cell — ~$200/mo for 5 seats.

| Week | Action |
|---|---|
| **1** | **Procure & verify.** Confirm with Fireflies that Business returns the **full transcript via webhook** (not just a summary) and supports our dialer. Confirm per-state recording-consent rules. |
| **1–2** | **Connect capture.** Install the Fireflies notetaker for Zoom; connect **Ringover** as the cell dialer and link it to Loxo. |
| **2** | **Wire the webhook.** Point Fireflies' *"transcription complete"* webhook at Emerald's `POST /webhook/transcript`; map its payload in `extract_transcript()`. |
| **3** | **Pilot.** Run 5–10 real intake calls (mix of Zoom + cell) end-to-end → JD / ad copy / outreach / Booleans in Loxo. Spot-check transcript quality + anonymization. |
| **4** | **Decide & scale.** If quality holds, roll out to all recruiters. Revisit Recall.ai / Twilio only if you later need a uniform transcript format or fully headless cell. |

**Definition of done:** an intake call (cell *or* Zoom) auto-produces a transcript that
flows into Emerald and lands an anonymized JD + sourcing brief on the Loxo job — no
manual copy-paste.

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
*Capabilities —*
[Otter API/webhooks (Enterprise) & Zoom Phone](https://help.otter.ai/hc/en-us/articles/24271600654871-Zoom-Phone-Integration) ·
[Fireflies API (GraphQL + webhooks)](https://fireflies.ai/api) ·
[Fireflies dialer integrations](https://fireflies.ai/integrations/dialer) ·
[Fathom Public API](https://developers.fathom.ai/) ·
[Recall.ai Meeting Bot API](https://www.recall.ai/product/meeting-bot-api) ·
[Deepgram phone-call transcription](https://developers.deepgram.com/docs/automatically-transcribing-and-summarizing-phone-calls)
*Pricing —*
[Otter pricing](https://costbench.com/software/ai-meeting-assistants/otter-ai/) ·
[Fireflies pricing](https://www.outdoo.ai/blog/fireflies-ai-pricing) ·
[Fathom pricing](https://www.g2.com/products/fathom-video/pricing) ·
[Recall.ai 2026 pricing ($0.50/hr)](https://www.recall.ai/blog/new-recall-ai-pricing-for-2026) ·
[Ringover pricing](https://www.cloudtalk.io/blog/ringover-pricing/) ·
[AssemblyAI vs Deepgram pricing](https://www.buildmvpfast.com/api-costs/transcription) ·
[Twilio voice/recording pricing](https://www.twilio.com/en-us/voice/pricing/us)
