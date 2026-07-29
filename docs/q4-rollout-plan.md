# Emerald — Q4 2026 Rollout Plan

*Written: July 29, 2026. Owner: Isabella Zhu.*

How Emerald goes from a one-recruiter summer pilot to the whole team in Q4. The pilot
premise (spec): within 30 minutes of an intake call, a Loxo job has an anonymized JD,
ad copy, outreach drafts, a 75–150 long list, enriched top 15–20, and reusable Booleans.
This plan assumes the pilot validates that against real job orders before we scale.

---

## Where we are entering Q4

**Built & verified:** anonymized JD (house style), ad copy (LinkedIn/Indeed/DocCafe),
4 Boolean variants, outreach draft sequence, unpublished Loxo job + sourcing-brief note
(live-verified on job #3621461), Boolean Workbench, Handshake CSV screen, Fireflies
webhook path, offline mock mode. Long-list volume now targets 75–150; enrichment targets
the top 20.

**Open before scale (see `ranking-and-metrics-gap.md`):**
1. Candidate **ranking** (list is unordered by fit).
2. **Metrics** are not measured (TTF / wrong-contact / connects).
3. **No sending email synced** in Loxo → outreach can't send yet (hard blocker).
4. Seamless API is **Enterprise-priced** → automated sourcing needs either that budget
   or the Loxo-Source manual fallback confirmed as the pilot's sourcing path.

---

## Gate before rollout (exit criteria for the pilot)

Do **not** roll out to the team until, on live job orders, the pilot recruiter has:
- [ ] Time-to-fill trending **< 45 days** (or on-track leading indicators).
- [ ] Wrong-contact rate **< 30%** on enriched contacts.
- [ ] **> 10 connects/day** sustained for a full week.
- [ ] A **documented SOP** the recruiter actually follows.
- [ ] Ranking + metrics gaps closed to at least "pilot-grade" (options 1 in the gap doc).

If any is red at the gate, extend the pilot rather than scale the problem to 8 desks.

---

## Timeline

### Week 0 (late Sept / pre-Q4) — unblock
- **Sync a sending email account in Loxo.** Nothing sends until this is done; it also
  unblocks the connects metric. *One-time, ~30 min, blocks everything downstream.*
- Decide the sourcing path: **budget Seamless API** *or* commit to **Loxo Source manual**
  as the pilot default. Set `EMERALD_SOURCE_LIMIT` (default 150) accordingly.
- Ship **candidate fit-score** (gap doc, Problem 1 / option 1) so lists arrive ranked.
- Stand up the **pilot metrics sheet** + weekly Loxo `jobs`/`placements`/`person-events`
  pull (gap doc, Problem 2 / option 1).

### Weeks 1–4 (Oct) — one recruiter, live orders
- Pilot recruiter runs **every** new intake through Emerald (target: 5–8 live orders).
- Daily: log connects; weekly: pull TTF + contact-accuracy from Loxo.
- Capture every friction point in a running list → this becomes the SOP.
- **Delete test job #3621461** once no longer a reference.
- Weekly 30-min review: what the tool got right, what the recruiter had to redo.

### Weeks 5–6 (early Nov) — harden & document
- Fix the top friction items from weeks 1–4 (most likely: ranking quality, ad-copy edits,
  Boolean tuning per family).
- Freeze the **recruiter SOP** (consolidate `prompt-sequence.md` + `STATUS.md` + the
  friction log into one runbook).
- Populate the **Confidential Outreach** campaign template from the generated drafts so
  enrollment is one click.
- Go/no-go **gate review** against the exit criteria above.

### Weeks 7–9 (mid–late Nov) — expand to 2–3 recruiters
- Add 2–3 recruiters. Each does a supervised first run with the pilot recruiter.
- Per-recruiter Loxo job ownership via `LOXO_DEFAULT_OWNER_EMAILS` (or per-run owner).
- Watch for multi-user issues: Loxo rate limits, credit burn, campaign collisions.
- Keep the metrics pull running per recruiter.

### Weeks 10–12 (Dec) — full team + steady state
- Roll to the remaining desks once 2–3-recruiter metrics hold.
- Move metrics from the sheet toward an instrumented `/metrics` view **only if** volume
  justifies it (gap doc, Problem 2 / option 2).
- Q4 retro: report the four success metrics with real data; decide 2027 investments
  (in-house enrichment vs. Seamless, deeper Loxo automation, voicemail drop).

---

## Roles
- **Pilot recruiter** — runs live orders, logs connects, flags friction, owns the SOP draft.
- **Isabella (build)** — ranking + metrics, Week-0 unblock, fixes from the friction log.
- **Manager sign-off** — Seamless budget decision, the Week-6 go/no-go gate, team scheduling.

## Risks & mitigations
| Risk | Mitigation |
|---|---|
| Sending email never gets synced | Week-0 blocker with a named owner; nothing ships without it. |
| Seamless cost not approved | Fall back to Loxo Source manual sourcing; the brief already supports it. |
| Unranked lists waste recruiter time | Ship fit-score in Week 0 (gate criterion). |
| Metrics unmeasured at gate | Pilot metrics sheet from Week 0; weekly Loxo pull. |
| Loxo rate limits / credit burn at multi-user | Stagger onboarding (2–3 before 8); watch credit usage; keep enrichment capped at top 20. |
| Confidentiality slip in a posting | Redaction safety-net already runs; spot-check every published JD during the pilot. |

## Rollout tracking
- [ ] Week 0 unblock complete (email synced, sourcing path chosen, ranking + metrics shipped)
- [ ] 5–8 live orders run through Emerald
- [ ] Four success metrics captured for the pilot recruiter
- [ ] SOP frozen
- [ ] Go/no-go gate passed
- [ ] 2–3 recruiters onboarded
- [ ] Full team live
- [ ] Q4 retro + 2027 plan
