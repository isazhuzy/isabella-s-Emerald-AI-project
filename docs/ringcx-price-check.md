# RingCX — Price Check (for Emerald)

*Prepared July 2026 · verify final numbers with a RingCentral quote before committing.*

## TL;DR
**RingCX is RingCentral's AI contact-center product (CCaaS)** — a separate license from
RingEX (the business phone system) and RingSense (the AI add-on we priced earlier). It is
built for **teams of agents running inbound/outbound call queues with a dialer**, not for a
boutique intake-call workflow. It **does include an outbound dialer and a voicemail-drop
button** (relevant to the voicemail-drop question — see that doc), but it is *agent-attended*,
not ringless.

**Pricing: ~$65 / $95 / $145 per agent/mo** (annual). For Emerald's actual need — capturing
intake calls and feeding transcripts to the pipeline — **RingCX is overkill and the priciest
option.** It only pays off if Emerald stands up a **high-volume outbound candidate-calling
desk** with multiple agents.

## Pricing (per **agent** / month)

| Tier | Annual | Monthly (~15% more) | What you get |
|---|---|---|---|
| **RingCX Standard** | **$65** | ~$75 | Inbound + outbound voice, IVR, ACD/skills-based routing, **call recording**, **predictive/outbound dialer** |
| **RingCX Professional** | **$95** | ~$109 | Standard **+ digital/omnichannel** (chat, email, social), quality management, more reporting |
| **RingCX Elite** | **$145** | ~$167 | Professional **+ WFM/workforce optimization** and the richest analytics |

**Notes / gotchas (verify in the quote):**
- **Priced per *agent*, not per user** — only the people staffing queues need a seat, which
  can keep the count small.
- **AI is largely extra.** RingCX AI (AI agents/virtual agents, real-time transcription,
  agent assist) is add-on/consumption-priced on top of the seat. Don't assume transcription
  is included at the Standard tier.
- **Separate license from RingEX.** If Emerald also wants RingCentral as its phone system,
  that's a *second* subscription. RingCX ≠ your desk phones.
- **Usage/telephony minutes and number fees** may be metered depending on the plan/region.
- **Likely a seat minimum and an annual commit** for contact-center plans — ask.
- **No native Loxo connector** (same as RingEX/RingSense). Integration would be via
  RingCentral's contact-center/RingSense **APIs → Emerald**, or a Zapier bridge.

## Is RingCX the right tool for Emerald?
**Probably not for the intake-call use case.** RingCX solves "many agents, high call volume,
queues, dialer campaigns." Emerald's core need is **record an intake call → transcript →
pipeline**, which is served far more cheaply by what we already recommended:

- **Intake capture:** Fireflies (~$10–19) for Zoom + phone with a webhook, and/or **Ringover
  (~$21, native Loxo)** for cell intake. See the vendor-research doc.
- If Emerald ever runs an **outbound candidate-calling desk** (recruiters dialing lists all
  day, leaving pre-recorded voicemails), **then** RingCX Standard ($65/agent) becomes
  relevant for its **predictive dialer + voicemail drop** — but weigh it against a standalone
  ringless-voicemail vendor (Drop Cowboy/Slybroadcast) which is a fraction of the cost.

## Recommendation
1. **Don't buy RingCX for intake calls** — use Fireflies/Ringover as already scoped.
2. **Only consider RingCX Standard ($65/agent, annual)** if/when Emerald commits to a
   multi-recruiter outbound calling operation; then get a written quote that spells out
   **AI/transcription add-on cost, minute fees, and any seat minimum**, and compare against
   RingEX-Advanced + RingSense (~$85/user all-in) and Ringover.
3. For the **voicemail-drop** question specifically, RingCX's drop is agent-attended; if the
   goal is *ringless* voicemail at scale, see `voicemail-drop-feasibility.md`.

## Sources
- [RingCX plans & pricing](https://www.ringcentral.com/pricing/contact-center.html) ·
  [RingCentral pricing breakdown 2026 (Nextiva)](https://www.nextiva.com/blog/ringcentral-pricing.html) ·
  [RingCentral pricing (CloudTalk)](https://www.cloudtalk.io/blog/ringcentral-pricing/)
- [Intro to outbound dialing in RingCX](https://support.ringcentral.com/article-v2/Intro-to-outbound-dialing-in-RingCX.html) ·
  [RingCX outbound solutions](https://www.ringcentral.com/ringcx/outbound.html)
