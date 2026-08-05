# Voicemail Drop — Is It Buildable? (Yes)

*Prepared July 2026. Extends Part 3 of `Emerald-Progress-and-Vendor-Research.md`.*

## Short answer
**Yes — and mostly without writing much code.** There are three viable paths, in
increasing order of build effort. The right one depends on whether you want **ringless**
voicemail (drop straight into voicemail, no ring) or **agent-attended** drop (recruiter on
the call clicks a button when they hit voicemail).

| # | Path | Ringless? | Build effort | Cost |
|---|---|---|---|---|
| 1 | **Loxo native voicemail-drop** channel | Yes | **~none** (turn it on in the Outreach campaign) | included in Loxo Standard/Premium |
| 2 | **Drop Cowboy / Slybroadcast** via Loxo webhook → Zapier | Yes | **low** (no-code Zap, or a small Emerald webhook) | ~$0.007 (Drop Cowboy) / ~$0.10 (Slybroadcast) per drop |
| 3 | **RingCX** agent voicemail-drop button | No (agent-attended) | medium (new phone system) | $65+/agent/mo |

## Path 1 — Loxo already does it (recommended default)
Loxo Outreach ships **Voicemail drop as a built-in channel** (alongside Email, Text, Phone,
InMail, Task) on Standard/Premium — confirmed in our account. **So the fastest "feature" is
zero-build:** add a Voicemail-drop step to the Confidential Outreach campaign and record the
audio. Nothing to develop.

## Path 2 — Dedicated ringless vendor (if we outgrow Loxo's, or want it programmatic)
Neither **Drop Cowboy** nor **Slybroadcast** has a native Loxo connector, so the bridge is:

```
Loxo webhook (candidate hits a stage / field flips)
        → Zapier (no-code)  ── or ──  Emerald /webhook endpoint
                → Drop Cowboy REST API  (POST a ringless drop)
```

- **Drop Cowboy** — cheapest (~$0.007/drop), first-class REST API + webhooks + Zapier + npm.
- **Slybroadcast** — simpler pricing (~$0.10/drop), free REST API.

**How we'd build it inside Emerald (if you don't want to use Zapier):** add a small
`emerald/voicemail.py` client (same mock-first pattern as `seamless.py`/`loxo.py`) that
takes `{phone, audio_id}` and POSTs to Drop Cowboy, plus one FastAPI route in `server.py`
(`POST /webhook/voicemail`) that Loxo's stage-change webhook calls. **~half a day of work.**
I've *not* built it yet because it needs (a) a vendor pick, (b) an account + API key, and
(c) a recorded/uploaded voicemail audio asset — say the word and I'll scaffold the module in
mock mode so it's ready to drop keys into.

## Path 3 — RingCX (only if we're already going contact-center)
RingCX has an agent **"Drop Voicemail"** button during outbound dialing — but it's
**agent-attended** (a recruiter is on the call), not ringless, and it means adopting a
$65+/agent/mo phone system. See `ringcx-price-check.md`. Not worth it *just* for voicemail.

## ⚠️ Compliance — do not skip
Ringless voicemail to **cell phones** is regulated under the **TCPA**: generally needs prior
consent and honored opt-outs, and has drawn class-action suits. Get legal/consent sign-off
before any ringless campaign, regardless of vendor.

## Recommendation
1. **Launch on Loxo's native voicemail drop** — zero build, already in the outreach columns.
2. If volume/cost or automation demands more, **add Drop Cowboy via Zapier** (or let me build
   the `voicemail.py` + `/webhook/voicemail` bridge into Emerald).
3. Clear TCPA consent first.

## Sources
- [Drop Cowboy API/developers](https://www.dropcowboy.com/developers) · [pricing](https://www.dropcowboy.com/pricing/)
- [Slybroadcast pricing & API](https://www.slybroadcast.com/)
- [Loxo Open API](https://help.loxo.co/en/articles/446640-loxo-s-open-api)
