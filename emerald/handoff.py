"""B1 handoff: turn generated deliverables into a recruiter "Sourcing Brief".

B1 is Loxo-native: the heavy lifting (Loxo Source AI search, ranking, enrichment,
outreach) happens *inside Loxo*, driven by Stage Automations (see LOXO_SETUP.md).
This module produces the one-click handoff a recruiter executes:

  - the exact Boolean string to paste into each sourcing channel
  - the target pipeline stages (long list -> shortlist) the automations key off
  - the outreach campaign content to enroll the shortlist in
  - a step-by-step runbook

The same text is saved locally and (on --push) posted as a note on the Loxo job.
"""
from __future__ import annotations

from typing import Any

from .config import settings


def _criteria_block(c: dict[str, Any]) -> str:
    if not c:
        return "_(none extracted)_"
    rows = [
        ("Titles", ", ".join(c.get("titles", []) or [])),
        ("Location", c.get("location", "")),
        ("Seniority", c.get("seniority", "")),
        ("Skills", ", ".join(c.get("skills", []) or [])),
        ("Must-have", "; ".join(c.get("must_have", []) or [])),
        ("Nice-to-have", "; ".join(c.get("nice_to_have", []) or [])),
    ]
    return "\n".join(f"- **{k}:** {v}" for k, v in rows if v)


def _outreach_block(steps: list[dict[str, Any]]) -> str:
    if not steps:
        return "_(no outreach steps generated)_"
    out = []
    for i, s in enumerate(steps, 1):
        out.append(
            f"**Step {i} — {s.get('channel', 'email')} · day {s.get('day', 0)}**\n"
            f"Subject: {s.get('subject', '')}\n\n{s.get('body', '')}\n"
        )
    return "\n---\n".join(out)


def build_sourcing_brief(
    deliverables: dict[str, Any],
    job_id: str | int | None = None,
    target_count: str = "75–150",
) -> str:
    """Render the recruiter-facing Sourcing Brief (markdown)."""
    title = deliverables.get("title", "Confidential Search")
    booleans = deliverables.get("boolean_strings", {})
    loxo_bool = booleans.get("loxo_source") or booleans.get("generic", "")
    n = settings.enrich_top_n
    job_ref = f" (Loxo job #{job_id})" if job_id else ""

    return f"""\
# Sourcing Brief — {title}{job_ref}

> Confidential search. Do not expose the client name in any posting or outreach.

## 1. Boolean by sourcing channel
Paste the matching variant into each channel you work:

- **Loxo Source:** `{loxo_bool}`
- **LinkedIn OW / LinkedIn Non-OW:** `{booleans.get('linkedin', '')}`
- **Indeed Database:** `{booleans.get('generic', '')}`
- **Google X-ray (re-use):** `{booleans.get('google_xray', '')}`

## 2. Target search criteria
{_criteria_block(deliverables.get('search_criteria', {}))}

## 3. Runbook (the one manual step is the search itself)
1. Open this job in Loxo and run each channel — **Loxo Source**, **LinkedIn OW**,
   **LinkedIn Non-OW (more passive)**, **Indeed Database** — using the matching
   Boolean above (or Loxo AI search with the criteria).
2. Review results; select the best **{target_count}** candidates across channels.
3. **Bulk-move them to the `{settings.sourcing_stage_name}` stage.** (No enrichment
   here — keeps it free for the long list.)
4. Pick the top **{n}** and move them to the `{settings.outreach_stage_name}` stage.
   → Stage Automation fires: **find contact details (enrich)** + **add to the
   `{settings.outreach_campaign_name}` campaign** + **AI highlights**.
5. Review enriched contacts + AI highlights, then let the campaign send.

_Enrichment is capped to the top {n} by only moving them into
`{settings.outreach_stage_name}` — this is the cost-control gate._

## 4. Outreach campaign content ({settings.outreach_campaign_name})
Use this to build/refresh the reusable campaign template once.

{_outreach_block(deliverables.get('outreach', []))}
"""
