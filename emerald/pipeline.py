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
    job_type: str | None = None,
    source: bool = False,
    source_limit: int = 50,
    enrich_contacts: bool = False,
    push_candidates: bool = False,
    filter_boolean: str | None = None,
) -> dict[str, Any]:
    """Run the full Phase 1 flow. Returns a result dict with all deliverables.

    job_type selects a family profile (physician/finance/tech/lab/general); None
    auto-detects from the transcript. publish=True creates the job live on the
    careers page instead of unpublished (JD is already anonymized, but default stays
    unpublished for human review).
    """
    # 1) Generate (Claude, or offline mock if no key)
    deliverables = generate_deliverables(transcript, client_name, job_type=job_type)

    # 2) Anonymization safety-net
    deliverables, masked = redact(deliverables, client_name=client_name)

    description_md = render_description(deliverables)

    result: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "client_name_input": client_name,
        "redaction_hits": masked,
        "used_mock_generation": deliverables.get("_mock", False),
        "job_type": deliverables.get("_job_type", "general"),
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
        # API path). Jobs auto-belong to LOXO_DEFAULT_OWNER_EMAILS when set (so they
        # show under that recruiter's My Jobs); this direct link opens them either way.
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

    # 4b) Optional candidate sourcing via Seamless.AI (once the JD/Booleans exist).
    #     Maps the generated search_criteria -> Seamless filters -> candidates.
    #     Never fails the run: errors are captured on the result.
    if source:
        if not settings.has_seamless:
            result["sourcing"] = {"error": "SEAMLESS_API_KEY not set (Enterprise API)."}
        else:
            from .seamless import source_candidates  # lazy import

            try:
                result["sourcing"] = source_candidates(
                    deliverables.get("search_criteria", {}),
                    limit=source_limit,
                    enrich=enrich_contacts,
                    job_type=deliverables.get("_job_type"),
                )
            except Exception as e:  # don't let sourcing crash the pipeline
                result["sourcing"] = {"error": str(e)}

        # 4c) Boolean pre-screen: keep only candidates matching the filter and drop
        #     ("shoot") the rest BEFORE anything reaches Loxo. `auto` uses the
        #     generated generic Boolean; otherwise pass an explicit expression.
        if filter_boolean and (result.get("sourcing") or {}).get("candidates"):
            from .boolean_filter import filter_candidates

            expr = filter_boolean
            if expr.strip().lower() == "auto":
                expr = (deliverables.get("boolean_strings") or {}).get("generic", "")
            kept, dropped = filter_candidates(result["sourcing"]["candidates"], expr)
            result["sourcing"]["candidates"] = kept
            result["sourcing"]["filter"] = {
                "expression": expr, "kept": len(kept), "dropped": len(dropped),
            }

        # Optionally push sourced candidates into the Loxo job pipeline (B2 headless):
        # create each as a Loxo person, then add to the job. Needs a created job_id.
        cands = (result.get("sourcing") or {}).get("candidates") or []
        if push_candidates and cands:
            if not job_id:
                result["sourcing"]["push_error"] = "need --push (a Loxo job) to attach candidates"
            else:
                import time
                pushed, errors = 0, []
                for i, cand in enumerate(cands):
                    if i:
                        time.sleep(0.6)  # gentle pacing — Loxo rate-limits bursts
                    try:
                        person = client.create_person(  # type: ignore[union-attr]
                            name=cand.get("name") or "Unknown",
                            current_title=cand.get("title"),
                            current_company=cand.get("company"),
                            location=cand.get("location"),
                            linkedin_url=cand.get("linkedin"),
                            emails=[cand["email"]] if cand.get("email") else None,
                            phones=[cand["phone"]] if cand.get("phone") else None,
                        )
                        pobj = person.get("person", person) if isinstance(person, dict) else {}
                        pid = pobj.get("id") if isinstance(pobj, dict) else None
                        if pid:
                            # title/company can't live on the person; surface them
                            # (and the source) as the pipeline note for the recruiter.
                            ctx = " ".join(
                                x for x in (cand.get("title"),
                                            f"@ {cand['company']}" if cand.get("company") else "")
                                if x
                            )
                            note = f"Sourced via Seamless — {ctx}".strip(" —") or None
                            client.add_to_pipeline(job_id, pid, notes=note)  # type: ignore[union-attr]
                            pushed += 1
                    except Exception as e:
                        errors.append(f"{cand.get('name')}: {e}")
                result["sourcing"]["pushed_to_loxo"] = {"created": pushed, "errors": errors}

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
        # Candidate list as a CSV the recruiter can work from.
        cands = (result.get("sourcing") or {}).get("candidates")
        if cands:
            import csv
            cand_path = f"{base}_candidates.csv"
            with open(cand_path, "w", newline="") as f:
                w = csv.DictWriter(
                    f, fieldnames=["name", "title", "company", "location",
                                   "linkedin", "email", "phone"]
                )
                w.writeheader()
                for c in cands:
                    w.writerow({k: c.get(k, "") for k in w.fieldnames})
            result["candidates_path"] = cand_path

    return result
