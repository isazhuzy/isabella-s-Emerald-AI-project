# Indeed Integration — What's Possible & What We Need

*Prepared July 2026.*

## TL;DR
**Don't build a custom Indeed integration — Loxo already ships one.** Loxo posts jobs to
Indeed and receives Indeed "Easy Apply" applications natively. Emerald already **generates
Indeed-tailored ad copy** in every run, so the pieces line up: Emerald writes the ad → the
job lives in Loxo → Loxo publishes it to Indeed → applicants flow back into Loxo. The only
real work is **flipping the right toggles in Loxo** and (for paid/sponsored posts) **having a
paid Indeed employer account.** A DIY Indeed API integration would require becoming an Indeed
**partner** — not worth it.

## What Emerald already produces
Each pipeline run emits `ad_copy.indeed` — Indeed-formatted ad copy tuned per job family
(and, for finance/tech, tuned to also suit eFinancialCareers/Dice). That's the content side.
Distribution is Loxo's job, below.

## The supported path: Loxo → Indeed (native)
Loxo has a first-party Indeed integration. To turn it on (in the Loxo recruiter app):

1. **Settings → Sources → Indeed → ON**, and set **Publish → ON.** Loxo then exposes an XML
   feed of all *active + published* jobs, which Indeed ingests.
2. **Settings → Integrations → "Easy Apply" / Indeed Apply → ON**, so applicants apply on
   Indeed and the applications land back in Loxo.
3. Publish the Emerald-created job in Loxo (our pipeline can create it; publish is gated for
   human review). New posts appear on Indeed within ~24h; edits sync in ~1–2h.

**Account requirement:** a recruiting agency needs a **paid Indeed employer account** to post
(internal/enterprise hiring may not). Organic (free) listings exist but see the deprecation
note below. Sponsored/promoted jobs are pay-per-application/pay-per-click on Indeed's side.

## Why NOT to build our own Indeed API integration
- **Indeed's Job Sync API is partner-gated.** It's a GraphQL API for **ATS partners**; access
  requires becoming an Indeed partner, an OAuth app provisioned by Indeed (2- or 3-legged),
  and is **explicitly not available to direct employers.** Loxo *is* that ATS partner — so we
  inherit the integration by using Loxo, instead of qualifying as a partner ourselves.
- **Building it ourselves duplicates** what Loxo already maintains, and we'd own the OAuth,
  job upsert/expire logic, and Indeed's compliance requirements for no benefit.

## ⚠️ The one thing to watch: Indeed's XML-feed deprecation
Indeed is **retiring single-source XML feeds**: organic (free) postings via such feeds stop
being collected after **March 31, 2026**, and sponsored delivery by end of 2026. ATS partners
are told to migrate from XML feeds to the **Job Sync API**.

- **This is Loxo's migration to do, not Emerald's.** Loxo's current Indeed hook is described
  as an XML feed, so **confirm with Loxo that they've migrated (or will) to Indeed's Job Sync
  API** before relying on organic Indeed distribution past that date. If Loxo has migrated,
  nothing changes for us. If not, organic Indeed reach could lapse.
- **Action item:** ask Loxo support "Is your Indeed integration on the Job Sync API or the
  legacy XML feed, and are our organic postings safe after March 31, 2026?"

## What we need — checklist
- [ ] **Paid Indeed employer account** linked in Loxo (for agency posting / sponsored).
- [ ] Loxo **Sources → Indeed = ON + Publish**, and **Indeed Easy Apply = ON**.
- [ ] Confirm Loxo is on **Indeed's Job Sync API** (not just legacy XML) — deprecation date.
- [ ] Decide organic vs **sponsored** budget (sponsored = pay-per-click/application on Indeed).
- [ ] (Already done) Emerald generates the Indeed ad copy per run.

## Recommendation
Use **Loxo's native Indeed integration** — enable the toggles, attach a paid Indeed account,
and confirm Loxo's Job Sync API migration. No custom code. Emerald's role stays "write the
best Indeed ad and create the job"; Loxo handles distribution and apply-back.

## Sources
- [Loxo & Job Boards](https://help.loxo.co/en/articles/5904294-loxo-job-boards) ·
  [Publish jobs to job boards (Loxo)](https://help.loxo.co/en/articles/446682-how-do-i-publish-my-jobs-to-job-boards)
- [Indeed Job Sync API guide](https://docs.indeed.com/job-sync-api/job-sync-api-guide) ·
  [ATS integration with Indeed Apply](https://docs.indeed.com/indeed-apply/ats)
- [Indeed's move away from XML feeds (HR Dive)](https://www.hrdive.com/news/visibility-ends-for-certain-free-single-source-xml-feeds-on-indeed/816209/)
