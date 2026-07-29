# Ranking & Success-Metrics — The Two Open Problems

*Written: July 29, 2026. Owner: Isabella Zhu.*

This note isolates the two places where the current build does **not** yet meet the
pilot spec, explains *why* each is a real gap (not just an unset flag), and lays out
the options to close them. Everything else in the spec — anonymized JD, ad copy,
Boolean strings, outreach drafts, the unpublished Loxo job — is built and verified.
These two are different: they need design decisions, not just wiring.

---

## Problem 1 — "75–150 **ranked** candidates"

### What the spec asks for
A long list of 75–150 candidates sitting in the Sourcing column, **ranked** best-to-worst
so the recruiter works top-down.

### What the system does today
The sourcing path (`emerald/seamless.py` → `source_candidates`) does three things:

1. **Searches** Seamless with the generated `search_criteria` (titles + state + seniority).
2. **Drops obvious execs** for IC roles (`_looks_exec` regex).
3. **Boolean pre-screens** — keep/drop against the generated Boolean (`filter_candidates`).

All three are **binary filters**: a candidate is kept or shot. What survives is delivered
**in whatever order Seamless returned it** (Seamless sorts by profile prominence, which
skews senior — the opposite of a fit ranking). We now pull up to 150 (see
[the sourcing-volume change](#note-volume-is-fixed-ranking-is-not)), but the list is
**unordered by fit**. There is no score, no "why this candidate," no top-of-list guarantee.

### Why this is a genuine gap
- The recruiter's whole time-saving premise is "work the list top-down." An unranked
  list of 150 forces them to re-triage all 150 by hand — the exact work we're trying to remove.
- "Ranked" is also what makes the **top 15–20 enrichment** meaningful. Right now we enrich
  the *first* 20 Seamless happened to return, not the *best* 20.

### Options to close it (in rough effort order)
1. **Deterministic fit score (recommended first step).** Score each candidate on
   overlap with `search_criteria` — title match, must-have/nice-to-have skill hits,
   seniority band, location match. Sort descending, enrich the true top-N. No model
   call, cheap, explainable, testable. Fits cleanly next to `filter_candidates` in
   `emerald/boolean_filter.py`.
2. **Model-assisted re-rank (phase 2).** After the deterministic sort, pass the top ~40
   to Claude with the JD and ask for a ranked shortlist + one-line rationale each. Higher
   quality, small cost, gives the recruiter the "why."
3. **Store the score on the Loxo record.** Write the rank/score into the pipeline note
   (already the channel we use) so the ordering survives into Loxo, where Seamless order is lost.

**Recommendation:** ship #1 now (it directly satisfies "ranked" and makes enrichment hit
the right people), layer #2 in during the pilot once we see real lists.

#### Note: volume is fixed, ranking is not
As of this change the long-list size is configurable and defaults to the spec's target:
`EMERALD_SOURCE_LIMIT=150` (was effectively capped at 50), and enrichment is now correctly
threaded to the top 20 (previously the brief promised 20 but the code silently enriched 10).
So **"75–150"** and **"top 15–20 enriched"** are met on volume. **"Ranked" is the part still open.**

---

## Problem 2 — the four success metrics are **not measured**

### What the spec asks for
- Time-to-fill under **45 days**
- Wrong contact-info rate under **30%**
- More than **10 connects per day** for the piloting recruiter
- A documented **SOP** and **Q4 rollout plan**

### What the system does today
Nothing measures any of the first three. The pipeline emits deliverables and writes JSON
artifacts, but there is **no counter, no log, no dashboard** for time-to-fill, contact
accuracy, or connects. We would not be able to report a single one of these numbers at the
end of the pilot from the system itself.

Worse, one of them is currently **blocked, not just unmeasured**: **no sending email account
is synced in Loxo**, so outreach cannot actually send — which means "connects per day" is
structurally zero until that one-time setup is done (see the rollout plan, Week 0).

### Why this is a genuine gap
The pilot is judged on these four numbers. "We built the tool" is not the deliverable;
"we hit <45 days / <30% / >10 connects, and here's the data" is. Without instrumentation
we're relying on the recruiter's memory, which won't survive a Q4 rollout review.

### Where each number actually lives, and how to capture it
| Metric | Source of truth | How to capture |
|---|---|---|
| **Time-to-fill** | Loxo job: created → placement date | Loxo already stores both; pull via `jobs`/`placements` API and compute. No new data entry. |
| **Wrong-contact rate** | Bounced emails + wrong-number call dispositions | Needs a lightweight tally: log enriched contacts, mark bounces/wrong-numbers. Start as a column in a shared sheet; graduate to a `/metrics` log. |
| **Connects per day** | Loxo activities (calls/replies logged by the recruiter) | Loxo person-events already record activity; count per day per user via the API. **Blocked until the sending email is synced.** |
| **SOP + rollout** | Docs | SOP: consolidate `prompt-sequence.md` + `STATUS.md` into one recruiter runbook. Rollout: see `q4-rollout-plan.md`. |

### Options to close it
1. **Minimal (pilot-grade):** a shared metrics sheet the recruiter updates daily +
   a weekly `jobs`/`placements`/`person-events` API pull to fill TTF and connects
   automatically. Enough to report all four at pilot end.
2. **Instrumented (rollout-grade):** an Emerald `/metrics` endpoint that reads Loxo
   activity + a bounce log and renders the four numbers live. Build during Q4 only if the
   pilot proves out — don't over-build before the workflow is validated.

**Recommendation:** do #1 for the pilot (fast, gets real data), decide on #2 at the Q4 gate.

---

## Summary

| | Volume | Ordering / Measurement | Blocker |
|---|---|---|---|
| **Candidates** | ✅ 75–150 (config) | ❌ not ranked by fit | — |
| **Enrichment** | ✅ top 20 (fixed) | ranked-ness depends on Problem 1 | — |
| **TTF / wrong-contact / connects** | — | ❌ not measured | connects also blocked: no sending email synced |
| **SOP / rollout** | 🟡 raw material exists | needs consolidation | — |

Two decisions unblock most of this: **(1)** approve a candidate fit-score (Problem 1, option 1),
and **(2)** approve the pilot metrics sheet + weekly Loxo pull (Problem 2, option 1). Both are
small and can land before the pilot's first live job order.
