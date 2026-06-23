# Emerald — Automation Progress & Vendor Research

*Prepared June 2026 · Recruiting automation initiative (Emerald → Loxo)*
*Google Doc–ready: in Google Drive choose **New → File upload** (this .md / its .docx)
or **paste** into a blank Doc; headings, tables, and bullets carry over.*

---

## Part 1 — Current Work Progress (Overview)

**What Emerald is:** an intake-call → recruiting-deliverables pipeline. A recruiter/HM
intake-call transcript goes in; out comes a ready-to-use, **confidential** sourcing
package, and (optionally) an unpublished job created directly in Loxo.

**What each run produces, automatically:**
- An **anonymized job description** in Emerald's house style (with a "Why Join" section).
- **Platform ad copy** (LinkedIn, Indeed, DocCafe).
- A **multi-step outreach sequence** (email → InMail → SMS).
- **Four Boolean variants** (generic, LinkedIn, Google X-ray, Loxo Source).
- A **Sourcing Brief** runbook for the recruiter.

**Status — built & verified:**

| Capability | Status |
|---|---|
| Intake → JD/ad/outreach/Boolean generation (Claude) | ✅ Live |
| Confidential anonymization (model + deterministic safety-net) | ✅ Verified (0 leaks in tests) |
| Loxo connection (keys, agency, required IDs) | ✅ Configured |
| Create **unpublished** Loxo job + post Sourcing Brief as a note | ✅ Verified live (job #3621461) |
| Mapped to real Loxo workflow (Long List → Short List stages) | ✅ Done |
| One-command wrapper (`emerald.sh`) + `--publish` flag | ✅ Done |
| Tested on real orders (Physician + Senior Accountant) | ✅ Done |

**Still to do (owner: us / Loxo admin):**
- Sync a sending email in Loxo (required before outreach actually sends).
- Pick & wire the transcription vendor (live call capture → pipeline).
- Decide voicemail-drop approach (see Part 3) and contact-enrichment trigger.
- Optional: publish-to-careers-page automation is built; needs a go/no-go policy.

**The human-in-the-loop steps** (by design): running the candidate search, and reviewing
before a job goes live or outreach sends. Everything else is generated.

---

## Part 2 — Transcription Bot Research

**The problem:** capture intake calls on **both Zoom and cell/phone**, get a **full
transcript**, and feed it to Emerald. Zoom is captured by a bot that joins the meeting;
a **cell call has no meeting to join**, so it needs a dialer/VoIP integration or a mobile
app.

| Tool | Zoom | Cell/phone | Feeds pipeline (API/webhook) | Best for |
|---|---|---|---|---|
| **Fireflies.ai** | ✅ bot | ✅ via dialer + mobile | ✅ webhook (paid tiers) | **Both Zoom + cell, automatable** |
| **Otter.ai** | ✅ bot | ⚠️ mobile / Zoom Phone | ⚠️ API Enterprise-only | teams already on Otter |
| **Fathom** | ✅ bot | ❌ none | ✅ all tiers | low-cost, **Zoom-only** |
| **Recall.ai** (infra) | ✅ widest | ⚠️ pair w/ telephony | ✅ it *is* an API | building our own notetaker |
| **Ringover** (cell dialer) | — | ✅ recordable line | **native Loxo** integration | cell intake into Loxo |

**Pricing (per seat/mo, annual — vendor-reported, verify):** Fireflies ~$10–$19 ·
Otter ~$8–$20 (API Enterprise-only) · Fathom ~$15–$29 · Ringover ~$21–$64.
**Build-your-own (usage):** Recall.ai ~$0.50/recording-hr + transcription · Deepgram
~$0.26/hr (cheapest speech-to-text) · AssemblyAI ~$0.37/hr.

**Recommendation:** **Fireflies.ai** as primary capture (only option that does Zoom *and*
phone *and* exposes a webhook) + **Ringover** for cell intake (native Loxo). Fathom as a
cheap Zoom-only fallback; Recall.ai/Deepgram in reserve for a fully custom notetaker.
**Verify first:** that the chosen Fireflies tier returns the **full transcript via
webhook** (not just a summary), and call-recording **consent** laws for our states.

---

## Part 3 — Voicemail Drop (Ringless Voicemail) Research

**What it is:** drop a pre-recorded voice memo straight into a candidate's voicemail
(no ring) as one channel in an outreach sequence.

### Key finding: Loxo already does this natively
**Loxo Outreach includes Voicemail drop as a built-in channel** (Email, Text, Phone call,
LinkedIn InMail, **Voicemail drop**, Task), available on Standard/Premium subscriptions —
confirmed both in our account and in Loxo's docs. **So the default recommendation is to
use Loxo's native voicemail step** inside the Confidential Outreach campaign — no extra
vendor, and it already lives in the outreach columns.

### If we want a dedicated platform with an API (≥2 compared)

| Platform | API | Cost | Connects to Loxo outreach columns? |
|---|---|---|---|
| **Slybroadcast** | ✅ REST API, **free with account** | Pay-as-you-go from **$10 / 100 delivered** (~$0.10/drop); monthly from $8/mo per 100 | No native Loxo connector; via **Zapier/Open-API webhook** (Loxo fires on stage change → Slybroadcast) |
| **Drop Cowboy** | ✅ REST API + webhooks + npm + **Zapier** | **~$0.004/msg + ~$0.0031 compliance fee** (≈ $0.007/drop) — cheapest; AI voice clone $0.005/100 chars | No native Loxo connector; **Zapier** no-code or Open-API webhook bridge |
| **Loxo native** | (in-platform) | Included in Loxo Standard/Premium | ✅ **Yes — it *is* the outreach column** |

**Can a third party connect to Loxo's outreach columns?** Not via a native connector —
neither Slybroadcast nor Drop Cowboy has one. The bridge is **Loxo's webhook (fires when a
candidate's stage/field changes) → Zapier → the voicemail API**. Drop Cowboy has
first-class Zapier + webhooks, making it the easier external integration of the two.

### Recommendation (ready for Wed June 25)
1. **Use Loxo's native voicemail drop** in the Confidential Outreach campaign — zero new
   spend, already in the outreach columns, simplest path.
2. **If we outgrow it** (higher volume, want ringless-to-cell at low per-drop cost), add
   **Drop Cowboy** via Zapier — cheapest per-drop (~$0.007) and the most API/Zapier-friendly.
   **Slybroadcast** is the simpler-pricing alternative (~$0.10/drop, free API).
3. **⚠️ Compliance (call this out):** ringless voicemail to **cell phones** is regulated
   under the **TCPA** — generally needs prior consent and honored opt-outs, and has drawn
   class actions. Legal/consent sign-off before launch.

---

## Sources
- [Slybroadcast pricing & API](https://www.slybroadcast.com/) · [Capterra](https://www.capterra.com/p/233942/Slybroadcast/)
- [Drop Cowboy API/developers](https://www.dropcowboy.com/developers) · [Pricing](https://www.dropcowboy.com/pricing/) · [Integrations](https://www.dropcowboy.com/integrations/)
- [Loxo Open API](https://help.loxo.co/en/articles/446640-loxo-s-open-api) · [Loxo Outreach (channels incl. voicemail drop)](https://recruitingdaily.com/loxo-outreach-a-completely-integrated-communication-platform/)
- [Seamless.AI API](https://seamless.ai/products/api) · [Seamless.AI pricing 2026](https://www.smarte.pro/blog/seamless-ai-pricing)
