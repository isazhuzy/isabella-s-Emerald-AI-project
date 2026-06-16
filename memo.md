

# Vendor Memo — Recruiting Automation Stack

*Scope: tools for the intake-to-outreach pipeline (Emerald → Loxo). **Part 1** covers
sourcing / contact data; **Part 2** covers call/meeting transcription.*

---

## Part 1 — Sourcing & Contact Data

**These three are not true substitutes.**

**Loxo Source** is the only one purpose-built for recruiting/candidate sourcing and is the recommended primary. **Seamless.AI** is a strong *sales* contact-data engine that can complement, a sourcing workflow. 
**TruePeopleSearch** is a free consumer public-records tool and is **not appropriate** for recruiting decisions due to FCRA restrictions.

---

## Side-by-side comparison

| Dimension | Loxo Source | Seamless.AI | TruePeopleSearch |
|---|---|---|---|
| **Built for** | Recruiting / candidate sourcing | B2B sales prospecting | Consumer people lookup |
| **Database size** | ~1.2B people, 12M companies | ~1.3B contacts, 1.8B emails, 414M mobile | "Nearly every US adult" (public records) |
| **Search method** | Boolean + filters + AI best-fit matching | Real-time search engine, filter-based | Name / phone / address lookup |
| **Outreach built in** | Yes — multi-channel sequences in-platform | Limited (AI writer add-on; not full sequencing) | None |
| **ATS / CRM fit** | Native (unified ATS + CRM + sourcing) | Integrates w/ Salesforce, HubSpot, etc. | None |
| **Recruiting-legal use (FCRA)** | Yes — built for it | Yes (B2B contact data) | **No — prohibited for employment screening** |
| **Geographic strength** | Global | US-strongest; weaker international | US only |
| **Pricing model** | Quote-based (paid tiers)- need to contact sales to confirm, basic $169/month | Credit-metered — need to contact sales to confirm  | Free |

---

## Analysis

**Loxo Source** is the natural fit. It is candidate-centric, supports the "unified sourcing" model (searching its ~1.2B-profile proprietary database *and* your own internal ATS/CRM simultaneously), and folds contact lookup, pipelining, and outreach into one workflow. Its Open API (a paid feature) and Zapier support also make it the only one of the three that slots cleanly into an automated intake-to-outreach pipeline.

**Seamless.AI** has comparable raw data scale and arguably stronger US contact verification, but it is engineered for *sales* prospecting, not recruiting. It finds the right person and their contact details well; it does not manage candidate pipelines or recruiting workflow. Best treated as a supplementary data source — e.g., for business-development leads or hard-to-find direct dials — rather than the system of record.

**TruePeopleSearch** is free and useful for quick ad-hoc personal lookups, but its terms explicitly bar use for employment, tenant, or credit decisions under the Fair Credit Reporting Act. That single constraint disqualifies it as a sourcing solution for professional recruiting. (Note also: the `.com` is the legitimate site; `.io` and other TLDs are copycats/redirects to data brokers.)

---

## Recommendation

1. **Primary tool: Loxo Source** — fit-for-purpose, workflow-integrated, automation-ready.
2. **Optional complement: Seamless.AI** — only if the team also runs sales/BD outreach or needs deeper US contact verification.
3. **Do not adopt TruePeopleSearch** for sourcing — retain only for informal, non-decisioning lookups if at all.

---

## Part 2 — Call/Meeting Transcription Layer

Feeds the pipeline: a call/meeting transcript → Claude → JD / ad copy / outreach /
Boolean strings → Loxo. **Cell and Zoom are two different capture problems** — Zoom is
captured by a bot that joins the call; a cell call has no bot to invite and must be
captured by a mobile app, a dialer/VoIP integration, or audio forwarded to a
speech-to-text API.

### Capabilities

| Tool | Zoom | Cell / phone | API → pipeline | Best for |
|---|---|---|---|---|
| **Fireflies.ai** | ✅ bot | ✅ via dialer (ZoomPhone, RingCentral, OpenPhone, Aircall) + mobile | ✅ GraphQL + webhooks (paid) | **both cell + Zoom, automatable** |
| **Otter.ai** | ✅ bot | ⚠️ mobile / Zoom Phone only | ⚠️ API & webhooks **Enterprise-only** | teams already on Otter |
| **Fathom** | ✅ bot | ❌ none (no mobile app) | ✅ REST + webhooks (all tiers) | low-cost, **Zoom-only** |
| **Recall.ai** *(infra)* | ✅ widest coverage | ⚠️ pair with telephony | ✅ it *is* an API | building our own notetaker |
| **Ringover** *(cell dialer)* | — | ✅ recordable cell line | native Loxo integration | cell intake that lands in Loxo |

### Pricing (mid-2026, vendor-reported — verify)

**Per-seat** (per user / month, annual billing):

| Tool | Free | Entry | Business | Top | API on |
|---|---|---|---|---|---|
| **Fireflies** | $0 | $10 | **$19** | $39 | paid tiers ✅ |
| **Otter** | $0 | $8.33 | $19.99 | Enterprise (custom) | Enterprise only ⚠️ |
| **Fathom** | $0 | $15 | $19 | $29 | all tiers ✅ |
| **Ringover** (cell) | — | ~$21 | ~$44 | $64 / custom | native Loxo |

**Usage-based** (per min/hr — build-your-own / telephony path):

| Service | Rate |
|---|---|
| **Recall.ai** (meeting bot) | $0.50 / recording-hr + $0.15/hr transcription; no platform fee |
| **Deepgram** (STT) | ~$0.26 / hr (cheapest) |
| **AssemblyAI** (STT) | ~$0.37 / hr (batch from $0.15/hr) |
| **Twilio** (telephony) | voice ~$0.013/min; record $0.0025/min; its own transcription $0.05/min → use Deepgram instead |

**Illustrative — team of 5 recruiters:** **Fireflies Business (~$95/mo) + Ringover
(~$105/mo) ≈ ~$200/mo all-in**, covering cell + Zoom + automation with no custom
engineering. Fathom is cheaper (~$75/mo) but Zoom-only; Otter looks similar (~$100/mo)
but automating it forces the Enterprise (custom) tier.

### Recommendation — transcription

1. **Fireflies.ai** as primary capture — the only requested tool that does Zoom **and**
   phone (via dialer) **and** exposes a webhook to feed the pipeline. Confirm the chosen
   tier delivers the **full transcript via webhook**, not just a summary.
2. **Ringover** for cell intake — native Loxo integration lands calls on the candidate
   record automatically.
3. **Fathom** only as a low-cost Zoom-only fallback (does **not** cover cell).
4. **Recall.ai / Twilio + AssemblyAI** held in reserve for a fully headless,
   build-our-own path.

---

> **Assumptions / to verify before circulating:**
> - **Sourcing (Part 1):** Loxo & Seamless pricing is quote/credit-based — confirm
>   directly. Database-size figures are vendor-reported, not independently audited.
> - **Transcription (Part 2):** All pricing is vendor-reported (mid-2026); confirm the
>   *specific tier* that includes transcript export + webhooks. Confirm Fireflies'
>   webhook returns the **full transcript** on the plan purchased.
> - **Compliance:** Verify call-recording consent / two-party-consent laws for our
>   operating states before enabling automatic recording.
> - Replace bracketed placeholders and confirmed numbers before sending.