"""Orchestrator: transcript -> deliverables -> (optional) Loxo write.

    run_pipeline(transcript, client_name, push_to_loxo=False) -> result dict
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from .config import settings
from .generate import generate_deliverables
from .handoff import build_sourcing_brief
from .redact import redact

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")


def render_description(d: dict[str, Any]) -> str:
    """Build a postable JD body (markdown) from the structured deliverables."""
    jd = d.get("jd", {})
    lines = [f"## {d.get('title', 'Open Role')}", "", jd.get("summary", ""), ""]
    if jd.get("responsibilities"):
        lines += ["### Responsibilities", *[f"- {r}" for r in jd["responsibilities"]], ""]
    if jd.get("requirements"):
        lines += ["### Requirements", *[f"- {r}" for r in jd["requirements"]], ""]
    if jd.get("why_join"):
        lines += ["### Why Join", *[f"- {w}" for w in jd["why_join"]], ""]
    comp = d.get("comp") or {}
    if comp.get("min") or comp.get("max"):
        cur = comp.get("currency", "USD")
        per = comp.get("period", "year")
        lines += [f"**Compensation:** {cur} {comp.get('min','?')}–{comp.get('max','?')} / {per}"]
    return "\n".join(lines).strip()


def _salary_str(comp: dict[str, Any] | None) -> str | None:
    comp = comp or {}
    if comp.get("min") and comp.get("max"):
        return f"{comp['min']}-{comp['max']}"
    return None


def run_pipeline(
    transcript: str,
    client_name: str = "",
    push_to_loxo: bool = False,
    publish: bool = False,
    save_artifact: bool = True,
) -> dict[str, Any]:
    """Run the full Phase 1 flow. Returns a result dict with all deliverables.

    publish=True creates the job live on the careers page instead of unpublished.
    The JD is already anonymized, but default stays unpublished for human review.
    """
    # 1) Generate (Claude, or offline mock if no key)
    deliverables = generate_deliverables(transcript, client_name)

    # 2) Anonymization safety-net
    deliverables, masked = redact(deliverables, client_name=client_name)

    description_md = render_description(deliverables)

    result: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "client_name_input": client_name,
        "redaction_hits": masked,
        "used_mock_generation": deliverables.get("_mock", False),
        "deliverables": deliverables,
        "job_description_markdown": description_md,
        "loxo": None,
    }

    # 3) Optional Loxo write (job created UNPUBLISHED for human review)
    job_id = None
    if push_to_loxo:
        from .loxo import LoxoClient  # imported lazily so dry-runs need no creds

        client = LoxoClient()
        job = client.create_job(
            title=deliverables.get("title", "Confidential Search"),
            description=description_md,
            salary=_salary_str(deliverables.get("comp")),
            published=publish,
        )
        result["loxo"] = {"job": job}
        # Loxo wraps the created job as {"job": {"id": ...}}; unwrap if needed.
        job_obj = job.get("job", job) if isinstance(job, dict) else {}
        job_id = job_obj.get("id") if isinstance(job_obj, dict) else None
        # Clickable Loxo UI link for the created job (the recruiter app, not the
        # API path). API jobs have no owner, so they're hard to find by browsing —
        # this direct link is the reliable way to open them.
        agency_id = job_obj.get("agency_id") if isinstance(job_obj, dict) else None
        if job_id and agency_id and settings.loxo_domain:
            result["loxo"]["job_url"] = (
                f"https://{settings.loxo_domain}/agencies/{agency_id}/jobs/{job_id}"
            )

    # 4) Build the B1 recruiter handoff (Sourcing Brief). Always produced.
    brief_md = build_sourcing_brief(deliverables, job_id=job_id)
    result["sourcing_brief_markdown"] = brief_md

    # On push, post the brief as a note on the job so recruiters have it in Loxo.
    if push_to_loxo and job_id and settings.loxo_note_activity_type_id:
        try:
            client.add_note(job_id, brief_md)  # type: ignore[union-attr]
            result["loxo"]["note_added"] = True
        except Exception as e:  # note schema varies by account; don't fail the run
            result["loxo"]["note_error"] = str(e)
    elif push_to_loxo and job_id:
        result["loxo"]["note_skipped"] = "set LOXO_NOTE_ACTIVITY_TYPE_ID to post the brief"

    # 5) Persist artifacts (JSON + the human-readable brief). Gitignored.
    if save_artifact:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        slug = "".join(c for c in deliverables.get("title", "job").lower()
                       if c.isalnum() or c in " -").strip().replace(" ", "-")[:40]
        base = os.path.join(OUTPUT_DIR, f"{stamp}_{slug}")
        with open(f"{base}.json", "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        with open(f"{base}_sourcing-brief.md", "w") as f:
            f.write(brief_md)
        result["artifact_path"] = f"{base}.json"
        result["brief_path"] = f"{base}_sourcing-brief.md"

    return result
